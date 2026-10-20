"""Separate guardian evidence, student agreement and per-recording sharing scope."""
import hashlib
import json
from pathlib import Path
import time


def version():
    import policy_service
    return json.loads((Path(__file__).parent/'policies'/'manifest.json').read_text())['recording_scope_version']+'.'+policy_service.digest()


def covers(permitted,requested):
    return (set(requested.get('storage',[]))<=set(permitted.get('storage',[]))
            and not (requested.get('sharing') and not permitted.get('sharing'))
            and not (requested.get('download') and not permitted.get('download'))
            and type(permitted.get('retention_days')) is int and requested.get('retention_days',31)<=permitted['retention_days'])


def active(features,table,uid,scope):
    if table not in ('guardian_scopes','standing_scopes'):raise ValueError('Invalid authorization type.')
    with features.db() as c:row=c.execute('SELECT * FROM '+table+' WHERE user_id=?',(uid,)).fetchone()
    return bool(row and not row['revoked'] and row['expires']>time.time() and row['version']==version() and covers(json.loads(row['scope']),scope))


def guardian(features,uid,scope):return active(features,'guardian_scopes',uid,scope)


def standing(features,person,scope):
    return (person['role']=='student' and guardian(features,person['uid'],scope) and active(features,'standing_scopes',person['uid'],scope))


def record_subjects(features,rid,people,scope):
    with features.db() as c:
        for p in people:
            if p['role']=='student':c.execute('INSERT INTO recording_subjects(recording_id,user_id,scope,at) VALUES (?,?,?,?)',(rid,p['uid'],json.dumps({**scope,'version':version()}),time.time()))


def sharing_allowed(features,row,download):
    scope=json.loads(row['scope'])
    if not scope.get('sharing') or (download and not scope.get('download')):return False
    with features.db() as c:subjects=c.execute('SELECT * FROM recording_subjects WHERE recording_id=?',(row['id'],)).fetchall()
    original=[p['uid'] for p in json.loads(row['subjects']) if p['role']=='student']
    if set(original)!={p['user_id'] for p in subjects}:return False
    for subject in subjects:
        agreed=json.loads(subject['scope'])
        if subject['revoked'] or agreed.get('version')!=version() or not covers(agreed,{**scope,'download':download}) or not guardian(features,subject['user_id'],scope):return False
    return True


def validate_scope(scope):
    return (isinstance(scope,dict) and set(scope)=={'storage','sharing','download','retention_days'}
            and isinstance(scope['storage'],list) and bool(scope['storage']) and all(isinstance(x,str) for x in scope['storage']) and set(scope['storage'])<= {'local','cloud'}
            and type(scope['sharing']) is bool and type(scope['download']) is bool
            and (not scope['download'] or scope['sharing']) and type(scope['retention_days']) is int and 1<=scope['retention_days']<=30)


def agree(features,uid,data,error):
    if data.get('action')=='withdraw':
        with features.db() as c:
            c.execute('UPDATE standing_scopes SET revoked=1 WHERE user_id=?',(uid,))
            c.execute('UPDATE recording_subjects SET revoked=1 WHERE user_id=?',(uid,))
        features.audit('withdraw_authorization',uid);return {'ok':True}
    import policy_service
    if policy_service.due(features,uid):raise error('Review the current account policies before recording authorization.',403)
    scope=data.get('scope');expiry=data.get('expires')
    if (data.get('accepted') is not True or data.get('version')!=version() or not validate_scope(scope)
        or type(expiry) not in (int,float) or not time.time()<expiry<=time.time()+365*86400):raise error('Review and explicitly approve the current recording scope.',400)
    if not guardian(features,uid,scope):raise error('OWNER-verified guardian authorization must cover this scope first.',403)
    with features.db() as c:c.execute('INSERT OR REPLACE INTO standing_scopes VALUES (?,?,?,?,?,0)',(uid,json.dumps(scope),version(),expiry,time.time()))
    features.audit('standing_authorization',uid);return {'ok':True}


def status(features,uid):
    result={'version':version()}
    with features.db() as c:
        for key,table in [('guardian','guardian_scopes'),('standing','standing_scopes')]:
            row=c.execute('SELECT scope,version,expires,revoked FROM '+table+' WHERE user_id=?',(uid,)).fetchone()
            result[key]=dict(row) if row else None
    return result


def storage_allowed(features,row,mode):
    scope=json.loads(row['scope']);requested={**scope,'storage':[mode]}
    if mode not in scope.get('storage',[]):return False
    with features.db() as c:subjects=c.execute('SELECT * FROM recording_subjects WHERE recording_id=?',(row['id'],)).fetchall()
    people=[p['uid'] for p in json.loads(row['subjects']) if p['role']=='student']
    return set(people)=={p['user_id'] for p in subjects} and all(not p['revoked'] and json.loads(p['scope']).get('version')==version() and guardian(features,p['user_id'],requested) for p in subjects)
