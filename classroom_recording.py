"""OWNER recording consent, durable bounded spool and asynchronous private R2 delivery."""
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
import weakref
from review_features import Features,GB,MAX_BYTES,MAX_SECONDS,PART_BYTES


class Store:
    def __init__(self,data,db,error,cloud):
        self.data=Path(data);self.db=db;self.error=error;self.locks=weakref.WeakValueDictionary();self.locks_guard=threading.Lock();self.activity={}
        self.features=Features(data);self.recovery_before=time.time();self.folder=self.data/'recordings';self.cloud=cloud;self.wake=threading.Event();self.closed=threading.Event();self.worker=None
        with db() as c:c.execute('''CREATE TABLE IF NOT EXISTS recordings(
            id TEXT PRIMARY KEY, owner INTEGER NOT NULL, class_id INTEGER NOT NULL,
            created REAL NOT NULL, expires REAL NOT NULL, mime TEXT NOT NULL,
            state TEXT NOT NULL, bytes INTEGER NOT NULL DEFAULT 0,
            sequence INTEGER NOT NULL DEFAULT 0, last_hash TEXT NOT NULL DEFAULT '', duration REAL NOT NULL DEFAULT 0,
            upload_id TEXT NOT NULL DEFAULT '',parts TEXT NOT NULL DEFAULT '[]',
            interrupted INTEGER NOT NULL DEFAULT 0)''')

    def record_lock(self,record_id):
        # Active operations retain their lock; completed/invalid IDs cannot grow
        # a permanent dictionary, and different recordings never share a lock.
        with self.locks_guard:
            return self.locks.setdefault(record_id,threading.RLock())

    @staticmethod
    def quota_used(c):
        total,count=c.execute('SELECT COALESCE(SUM(bytes),0),COUNT(*) FROM recordings WHERE bytes>0').fetchone()
        return 2*total+count*PART_BYTES

    def require(self,condition,message,status=409):
        if not condition:raise self.error(message,status)

    def policy(self,mode="cloud"):
        path=self.data/'recording-policy.json'
        try:
            self.require(not path.is_symlink() and path.stat().st_size<=65536,'Invalid recording policy.')
            value=json.loads(path.read_text(encoding='utf-8'))
            self.require(mode=='local' or (value.get('private_cloud_approved') is True and self.cloud.ready()),'OWNER must confirm private R2 storage before recording.')
            self.require(value.get('enabled') is True and value.get('policy_approved') is True,'OWNER has not enabled an approved recording policy.')
            self.require(isinstance(value.get('notice'),str) and 20<=len(value['notice'])<=2000,'Recording policy needs a participant notice.')
            days=value.get('retention_days',7);self.require(type(days) is int and 1<=days<=30,'Invalid recording retention.')
            self.require(isinstance(value.get('guardian_authorizations',{}),dict),'Invalid guardian authorizations.')
            quota=value.get('retained_quota_gb',25);self.require(type(quota) is int and 12<=quota<=1000,'Retained quota must be 12–1000 decimal GB.')
            value['quota_bytes']=quota*GB
            return value
        except (OSError,ValueError,TypeError):raise self.error('Recording is disabled. OWNER must configure its local policy first.',409) from None

    def eligible(self,person,policy,scope=None):
        if person['role']=='admin':return True
        # Guests cannot establish verified guardian/adult authorization.
        if person['role']!='student':return False
        if scope:
            from recording_authorization import guardian
            if guardian(self.features,person['uid'],scope):return True
            if scope.get('sharing') or scope.get('download') or scope.get('storage')!=['cloud']:return False
        expiry=policy.get('guardian_authorizations',{}).get(str(person['uid']))
        return type(expiry) in (float,int) and expiry>time.time()

    def status(self,room,peer):
        rec=room.get('recording')
        if not rec:return {'phase':'off'}
        if rec['phase']=='pending' and time.monotonic()>=rec['pending_until']:self.stop(room,ack=True)
        if rec['phase'] in ('active','paused') and (rec['members']!=set(room['peers']) or time.monotonic()>=rec['lease']):self.stop(room)
        return {'id':rec['id'],'phase':rec['phase'],'notice':rec['notice'],
                'consented':peer in rec['consents'],'consent_count':len(rec['consents']),
                'participants':len(room['peers']),'owner':rec['owner']==peer,'scope':rec.get('scope',{}),'mode':rec.get('mode','cloud')}

    def request(self,room,peer,consent,mode="cloud",sharing=False,download=False,future_upload=False):
        self.require(consent is True,'Explicit teacher consent is required.',403)
        self.require(room['peers'][peer]['role']=='admin','Teacher access required.',403)
        self.require(not room.get('recording') or room['recording']['phase'] in ('off','stopped'),'A recording request is already open.')
        self.require(mode in ('cloud','local') and all(type(v) is bool for v in (sharing,download,future_upload)),'Invalid recording options.',400)
        policy=self.policy(mode)
        scope={'storage':['local','cloud'] if mode=='local' and future_upload else [mode],'sharing':sharing,'download':download,'retention_days':policy['retention_days']}
        self.require(all(self.eligible(p,policy,scope) for p in room['peers'].values()),'Every student needs unexpired OWNER-recorded guardian authorization. Guests cannot be recorded.',403)
        from recording_authorization import standing,version
        approved={key for key,p in room['peers'].items() if standing(self.features,p,scope)}
        room['recording']={'scope_version':version(),'standing_members':approved,'id':secrets.token_hex(16),'owner':peer,'phase':'pending','notice':policy['notice'],
                           'mode':mode,'scope':scope,'consents':{peer}|approved,'members':set(room['peers']),'lease':0,'block_until':0,'pending_until':time.monotonic()+120}
        return self.status(room,peer)

    def consent(self,room,peer,record_id,accepted):
        rec=room.get('recording');self.require(rec and rec['id']==record_id and rec['phase']=='pending','Recording request expired.')
        self.require(time.monotonic()<rec['pending_until'],'Recording request expired.')
        self.require(type(accepted) is bool,'Choose consent or decline.',400)
        if not accepted:self.stop(room);return self.status(room,peer)
        self.require(self.eligible(room['peers'][peer],self.policy(rec.get('mode','cloud')),rec['scope']),'Guardian authorization is missing or expired.',403)
        rec['consents'].add(peer);return self.status(room,peer)

    def start(self,room,peer,uid,cid,mime):
        rec=room.get('recording');self.require(rec and rec['owner']==peer and rec['phase']=='pending','No recording request is ready.')
        self.require(time.monotonic()<rec['pending_until'],'Recording request expired.')
        self.require(rec['members']==set(room['peers'])==rec['consents'],'Every connected participant must affirmatively consent.',403)
        policy=self.policy(rec.get('mode','cloud'));self.require(all(self.eligible(p,policy,rec['scope']) for p in room['peers'].values()),'Guardian authorization expired.',403)
        self.require(mime in ('video/webm','video/mp4'),'Unsupported recording container.',400)
        self.folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.require(not self.folder.is_symlink(),'Recording storage cannot be linked.')
        self.require(shutil.disk_usage(self.folder).free>=512*1024**2,'Not enough free disk space for recording.',507)
        with self.db() as c:
            self.require(self.quota_used(c)+2*MAX_BYTES+PART_BYTES<=policy['quota_bytes'],'Recording storage quota reached.',507)
            c.execute('INSERT INTO recordings(id,owner,class_id,created,expires,mime,state) VALUES (?,?,?,?,?,?,?)',
                      (rec['id'],uid,cid,time.time(),time.time()+policy['retention_days']*86400,mime,'capturing'))
        with self.db() as c:
            lesson=c.execute('SELECT class_kind,start,title FROM classes WHERE id=?',(cid,)).fetchone()
            roster=[r[0] for r in c.execute('SELECT user_id FROM bookings WHERE class_id=?',(cid,))]
        with self.features.db() as c:c.execute('INSERT INTO recording_options(id,mode,scope,subjects) VALUES (?,?,?,?)',(rec['id'],rec.get('mode','cloud'),json.dumps(rec.get('scope',{})),json.dumps([{'uid':p['uid'],'role':p['role']} for p in room['peers'].values()])))
        with self.features.db() as c:c.execute('INSERT INTO recording_context VALUES (?,?,?,?,?)',(rec['id'],lesson['class_kind'],lesson['start'],lesson['title'],json.dumps(roster)))
        from recording_authorization import record_subjects
        record_subjects(self.features,rec['id'],room['peers'].values(),rec['scope'])
        rec['created']=time.time()
        rec['phase']='active';rec['lease']=time.monotonic()+2;self.activity[rec['id']]=time.time()
        return {'id':rec['id'],'lease_ms':1500,'allowed':sorted(rec['consents'])}

    def heartbeat(self,room,peer,record_id):
        rec=room.get('recording');self.status(room,peer)
        self.require(rec and rec['id']==record_id and rec['owner']==peer and rec['phase'] in ('active','paused'),'Recording authorization ended.',403)
        policy=self.policy(rec.get('mode','cloud'))
        self.require(time.time()<rec.get('created',time.time())+MAX_SECONDS,'Recording duration limit reached.')
        self.require(all(self.eligible(p,policy,rec['scope']) for p in room['peers'].values()),'Recording authorization expired.',403)
        from recording_authorization import version,standing
        self.require(rec['scope_version']==version() and all(standing(self.features,room['peers'][key],rec['scope']) for key in rec['standing_members']),'Standing authorization changed or expired.',403)
        with self.features.db() as c:withdrawn=c.execute('SELECT 1 FROM recording_subjects WHERE recording_id=? AND revoked=1',(record_id,)).fetchone()
        self.require(not withdrawn,'Recording authorization withdrawn.',403)
        rec['lease']=time.monotonic()+2;self.activity[rec['id']]=time.time()
        return {'lease_ms':1500,'allowed':sorted(rec['consents'])}

    def stop(self,room,ack=False):
        rec=room.get('recording')
        if rec:
            rec['block_until']=max(rec.get('block_until',0),rec.get('lease',0)+2)
            rec['phase']='stopped' if ack or rec['phase']=='pending' else 'stopping'

    def before_join(self,room):
        rec=room.get('recording')
        if not rec:return
        if rec['phase']=='pending':self.stop(room,ack=True);return
        if rec['phase'] in ('active','paused'):self.stop(room)
        if rec['phase']=='stopping':
            self.require(time.monotonic()>=rec['block_until'],'Recording is stopping before a participant joins. Retry in a moment.')
            rec['phase']='stopped'

    def row(self,record_id,uid):
        self.require(isinstance(record_id,str) and re.fullmatch('[0-9a-f]{32}',record_id),'Invalid recording.',404)
        with self.db() as c:row=c.execute('SELECT * FROM recordings WHERE id=? AND owner=?',(record_id,uid)).fetchone()
        self.require(row,'Recording unavailable.',404);return {**dict(row),**self.features.options(record_id)}

    def chunk(self,record_id,uid,sequence,data):
        with self.record_lock(record_id):
            row=self.row(record_id,uid);self.require(row['state'] in ('capturing','importing'),'Recording is no longer accepting chunks.')
            self.require(time.time()<min(json.loads(row['metrics']).get('imported_at',row['created'])+MAX_SECONDS+120,row['expires']),'Recording duration limit reached.')
            digest=hashlib.sha256(data).hexdigest()
            if json.loads(row['metrics']).get('imported_at'):
                with self.features.db() as c:original=c.execute('SELECT size,digest FROM local_chunks WHERE id=? AND sequence=?',(record_id,sequence)).fetchone()
                self.require(original and original['size']==len(data) and original['digest']==digest,'Selected local file does not match this authorized recording.',403)
            if sequence==row['sequence']-1 and digest==row['last_hash']:return {'ok':True,'sequence':row['sequence']}
            self.require(type(sequence) is int and sequence==row['sequence'],'Recording chunk is out of order.')
            self.require(0<len(data)<=8*1024**2,'Recording chunk too large.',413)
            if not sequence:self.require(data.startswith(b'\x1aE\xdf\xa3') if row['mime']=='video/webm' else data[4:8]==b'ftyp','Invalid recording container.',415)
            self.require(row['bytes']+len(data)<=MAX_BYTES,'Recording size limit reached.',507)
            self.require(shutil.disk_usage(self.folder).free>len(data)+128*1024**2,'Not enough recording disk space.',507)
            with self.db() as c:self.require(self.quota_used(c)+2*len(data)+(PART_BYTES if not row['bytes'] else 0)<=self.policy(row['mode'])['quota_bytes'],'Recording quota reached.',507)
            path=self.folder/(record_id+'.part');self.require(not path.is_symlink(),'Invalid storage path.')
            with path.open('a+b') as stream:
                stream.truncate(row['bytes']);stream.write(data);stream.flush()
                import os;os.fsync(stream.fileno())
            with self.db() as c:c.execute('UPDATE recordings SET bytes=?,sequence=?,last_hash=? WHERE id=?',(row['bytes']+len(data),sequence+1,digest,record_id))
            self.wake.set()
            return {'ok':True,'sequence':sequence+1}

    def finish(self,record_id,uid,complete):
        with self.record_lock(record_id):
            row=self.row(record_id,uid);source=self.folder/(record_id+'.part')
            if row['state'] not in ('capturing','importing'):return {'ok':True,'state':row['state']}
            self.require(type(complete) is bool,'Invalid finalization.',400)
            if complete and json.loads(row['metrics']).get('imported_at'):
                with self.features.db() as c:expected=c.execute('SELECT COALESCE(SUM(size),0) FROM local_chunks WHERE id=?',(record_id,)).fetchone()[0]
                self.require(row['bytes']==expected and expected>0,'Local recording upload is incomplete.')
            state=('local' if complete else 'failed') if row['mode']=='local' else ('processing' if row['bytes'] else 'failed')
            if source.exists():
                with source.open('r+b') as stream:stream.truncate(row['bytes'])
                source.replace(self.folder/(record_id+('.mp4' if row['mime']=='video/mp4' else '.webm')))
            with self.db() as c:c.execute('UPDATE recordings SET state=?,interrupted=? WHERE id=?',(state,int(not complete),record_id))
            self.wake.set()
            return {'ok':True,'state':state}

    def delete(self,record_id,uid,opportunistic=False):
        cloud_lock=self.record_lock('cloud:'+record_id)
        if not cloud_lock.acquire(blocking=not opportunistic):return False
        try:
            self._delete_locked(record_id,uid)
        finally:cloud_lock.release()

    def _delete_locked(self,record_id,uid):
        with self.record_lock(record_id):
            row=self.row(record_id,uid)
            self.require(row['state']!='capturing','Stop this recording before deleting it.')
            with self.db() as c:c.execute("UPDATE recordings SET state='deleting' WHERE id=?",(record_id,))
            if row['mode']=='cloud':
                self.cloud.remove(row)
                with self.features.db() as c:job=c.execute('SELECT * FROM recording_playback WHERE id=?',(record_id,)).fetchone()
                if job:self.cloud.remove({**dict(job),'id':record_id+'_playback'})
            for ext in ('.part','.webm','.mp4'):(self.folder/(record_id+ext)).unlink(missing_ok=True)
            for suffix in ('.indexed.webm','.indexed.mp4','.indexing.webm','.indexing.mp4'):(self.folder/(record_id+suffix)).unlink(missing_ok=True)
            with self.features.db() as c:
                c.execute('DELETE FROM recording_playback WHERE id=?',(record_id,))
                c.execute('DELETE FROM recording_options WHERE id=?',(record_id,));c.execute('DELETE FROM local_chunks WHERE id=?',(record_id,));c.execute('DELETE FROM recording_context WHERE id=?',(record_id,))
            with self.db() as c:c.execute('DELETE FROM recordings WHERE id=?',(record_id,))

    def cleanup(self):
        with self.features.db() as c:c.execute('DELETE FROM audit WHERE at<?',(time.time()-90*86400,))
        with self.db() as c:expired=c.execute("SELECT id,owner FROM recordings WHERE expires<=? OR state='deleting'",(time.time(),)).fetchall()
        for item in expired:self.delete(item['id'],item['owner'],opportunistic=True)

    def recover(self):
        with self.db() as c:rows=c.execute("SELECT id,owner FROM recordings WHERE state='capturing' AND created<?",(self.recovery_before,)).fetchall()
        for row in rows:self.finish(row['id'],row['owner'],False)
        self.cleanup()


    def pause(self,room,peer,paused):
        rec=room.get('recording')
        self.require(rec and rec['owner']==peer and rec['phase'] in ('active','paused'),'Recording is not active.',403)
        self.require(type(paused) is bool,'Invalid pause state.',400)
        rec['phase']='paused' if paused else 'active'
        return self.status(room,peer)

    def listing(self,uid):
        with self.db() as c:
            rows=c.execute("SELECT r.id,r.created,r.expires,r.mime,r.state,r.bytes,r.duration,r.interrupted,cl.title AS meeting FROM recordings r LEFT JOIN classes cl ON cl.id=r.class_id WHERE r.owner=? AND r.expires>? ORDER BY r.created DESC LIMIT 200",(uid,time.time())).fetchall()
        return {'recordings':[{**dict(row),**{k:v for k,v in self.features.options(row['id']).items() if k!='subjects'}} for row in rows]}

    def finalize(self,record_id,uid,complete,duration):
        self.require(type(duration) in (float,int) and 0<=duration<=MAX_SECONDS,'Invalid recording duration.',400)
        result=self.finish(record_id,uid,complete)
        with self.db() as c:c.execute('UPDATE recordings SET duration=? WHERE id=? AND owner=?',(duration,record_id,uid))
        return result

    def launch(self):
        # Called only after a successful server bind. Never on a duplicate launch.
        if self.worker and self.worker.is_alive():return
        def run():
            try:self.recover()
            except Exception:print('Recording recovery pending; check private storage.',flush=True)
            while not self.closed.is_set():
                self.wake.clear()
                try:
                    self.cleanup()
                    with self.db() as c:stale=c.execute("SELECT id,owner,created FROM recordings WHERE state='capturing'").fetchall()
                    for row in stale:
                        if time.time()-self.activity.get(row['id'],row['created'])>60:self.finish(row['id'],row['owner'],False)
                    with self.db() as c:rows=c.execute("SELECT * FROM recordings WHERE state IN ('capturing','importing','processing','uploading') AND bytes>0 AND expires>? ORDER BY created LIMIT 50",(time.time(),)).fetchall()
                    for item in rows:
                        if self.closed.is_set():break
                        with self.record_lock('cloud:'+item['id']):
                            row=self.row(item['id'],item['owner'])
                            if row['mode']!='cloud':continue
                            complete=row['state'] not in ('capturing','importing')
                            if not complete and row['bytes']<PART_BYTES:continue
                            path=self.folder/(row['id']+('.part' if not complete else ('.mp4' if row['mime']=='video/mp4' else '.webm')))
                            def checkpoint(upload,parts):
                                with self.db() as c:c.execute('UPDATE recordings SET upload_id=?,parts=? WHERE id=?',(upload,json.dumps(parts),row['id']))
                            try:
                                if complete:
                                    with self.db() as c:c.execute("UPDATE recordings SET state='uploading' WHERE id=?",(row['id'],))
                                acknowledged=self.cloud.upload(row,path,checkpoint,complete=complete,maximum=row['bytes'],max_parts=1)
                                if complete and acknowledged:
                                    with self.db() as c:c.execute("UPDATE recordings SET state='ready' WHERE id=?",(row['id'],))
                                    self.activity.pop(row['id'],None)
                                    from recording_media import configured
                                    if not configured(self.data):path.unlink(missing_ok=True)
                                with self.features.db() as c:c.execute("UPDATE recording_options SET error='' WHERE id=?",(row['id'],))
                            except Exception:
                                with self.features.db() as c:c.execute("UPDATE recording_options SET error='Private cloud transfer interrupted; retry pending.' WHERE id=?",(row['id'],))
                                print('Private recording transfer retry pending.',flush=True)
                except Exception:
                    # Never log object IDs, credentials, paths or user/media content.
                    print('Recording cloud transfer pending; check private storage configuration and persistent disk.',flush=True)
                self.wake.wait(5)
        def processing():
            from recording_media import configured,process
            while not self.closed.wait(2):
                if not configured(self.data):continue
                with self.db() as c:ready=c.execute("SELECT id,owner FROM recordings WHERE state='ready' AND expires>? LIMIT 50",(time.time(),)).fetchall()
                for item in ready:
                    if self.closed.is_set():break
                    with self.record_lock('cloud:'+item['id']):
                        try:
                            row=self.row(item['id'],item['owner'])
                            if row['state']=='ready':process(self,row)
                        except Exception:pass
        self.worker=threading.Thread(target=run,daemon=True);self.worker.start()
        self.processor=threading.Thread(target=processing,daemon=True);self.processor.start()

    def close(self):self.closed.set();self.wake.set()


    def import_local(self,record_id,uid):
        with self.record_lock(record_id):
            row=self.row(record_id,uid)
            if row['mode']=='cloud' and row['state']=='importing':return {'ok':True,'id':record_id,'sequence':row['sequence']}
            self.require(row['mode']=='local' and row['state']=='local','Only a completed local recording can be uploaded.')
            self.require('cloud' in json.loads(row['scope']).get('storage',[]),'This recording was not authorized for cloud storage.',403)
            self.require(row['expires']>time.time(),'Recording retention expired.',403)
            from recording_authorization import storage_allowed
            self.require(storage_allowed(self.features,row,'cloud'),'Cloud upload authorization is expired, changed or withdrawn.',403)
            self.policy('cloud')
            with self.features.db() as c:c.execute("UPDATE recording_options SET mode='cloud',metrics=? WHERE id=?",(json.dumps({'imported_at':time.time()}),record_id))
            with self.db() as c:c.execute("UPDATE recordings SET state='importing',bytes=0,sequence=0,last_hash='',upload_id='',parts='[]' WHERE id=?",(record_id,))
            self.activity[record_id]=time.time()
            return {'ok':True,'id':record_id,'sequence':0}


    def local_checkpoint(self,rid,uid,sequence,size,digest):
        with self.record_lock(rid):
            row=self.row(rid,uid)
            self.require(row['mode']=='local' and row['state']=='capturing','Local recording is not active.')
            self.require(type(sequence) is int and 0<=sequence<=15000 and type(size) is int and 0<size<=PART_BYTES and isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest),'Invalid local checkpoint.',400)
            with self.features.db() as c:
                c.execute('BEGIN IMMEDIATE')
                old=c.execute('SELECT size,digest FROM local_chunks WHERE id=? AND sequence=?',(rid,sequence)).fetchone()
                if old:self.require(old['size']==size and old['digest']==digest,'Local checkpoint mismatch.')
                else:
                    count,total=c.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM local_chunks WHERE id=?',(rid,)).fetchone()
                    self.require(count==sequence and total+size<=MAX_BYTES,'Local recording limit or ordering error.')
                    c.execute('INSERT INTO local_chunks VALUES (?,?,?,?)',(rid,sequence,size,digest))
            return {'sequence':sequence+1}

    def local_manifest(self,rid,uid):
        self.row(rid,uid)
        with self.features.db() as c:return {'chunks':[dict(r) for r in c.execute('SELECT sequence,size,digest FROM local_chunks WHERE id=? ORDER BY sequence',(rid,))]}


    def request_delete(self,rid,uid):
        with self.record_lock(rid):
            row=self.row(rid,uid);self.require(row['state']!='capturing','Stop this recording before deleting it.')
            with self.db() as c:c.execute("UPDATE recordings SET state='deleting' WHERE id=?",(rid,))
        self.features.audit('delete_requested',uid,rid);self.wake.set()
        return {'ok':True,'state':'deleting'}
