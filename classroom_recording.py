"""OWNER recording consent, durable bounded spool and asynchronous private R2 delivery."""
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import threading
import time


class Store:
    def __init__(self,data,db,error,cloud):
        self.data=Path(data);self.db=db;self.error=error;self.locks=[threading.RLock() for _ in range(16)];self.activity={}
        self.recovery_before=time.time();self.folder=self.data/'recordings';self.cloud=cloud;self.wake=threading.Event();self.closed=threading.Event();self.worker=None
        with db() as c:c.execute('''CREATE TABLE IF NOT EXISTS recordings(
            id TEXT PRIMARY KEY, owner INTEGER NOT NULL, class_id INTEGER NOT NULL,
            created REAL NOT NULL, expires REAL NOT NULL, mime TEXT NOT NULL,
            state TEXT NOT NULL, bytes INTEGER NOT NULL DEFAULT 0,
            sequence INTEGER NOT NULL DEFAULT 0, last_hash TEXT NOT NULL DEFAULT '', duration REAL NOT NULL DEFAULT 0,
            upload_id TEXT NOT NULL DEFAULT '',parts TEXT NOT NULL DEFAULT '[]',
            interrupted INTEGER NOT NULL DEFAULT 0)''')

    def record_lock(self,record_id):return self.locks[int(hashlib.sha256(str(record_id).encode()).hexdigest()[:2],16)%16]

    def require(self,condition,message,status=409):
        if not condition:raise self.error(message,status)

    def policy(self):
        path=self.data/'recording-policy.json'
        try:
            self.require(not path.is_symlink() and path.stat().st_size<=65536,'Invalid recording policy.')
            value=json.loads(path.read_text(encoding='utf-8'))
            self.require(value.get('private_cloud_approved') is True and self.cloud.ready(),'OWNER must confirm private R2 storage before recording.')
            self.require(value.get('enabled') is True and value.get('policy_approved') is True,'OWNER has not enabled an approved recording policy.')
            self.require(isinstance(value.get('notice'),str) and 20<=len(value['notice'])<=2000,'Recording policy needs a participant notice.')
            days=value.get('retention_days',7);self.require(type(days) is int and 1<=days<=30,'Invalid recording retention.')
            self.require(isinstance(value.get('guardian_authorizations',{}),dict),'Invalid guardian authorizations.')
            return value
        except (OSError,ValueError,TypeError):raise self.error('Recording is disabled. OWNER must configure its local policy first.',409) from None

    def eligible(self,person,policy):
        if person['role']=='admin':return True
        # Guests cannot establish verified guardian/adult authorization.
        if person['role']!='student':return False
        expiry=policy.get('guardian_authorizations',{}).get(str(person['uid']))
        return type(expiry) in (float,int) and expiry>time.time()

    def status(self,room,peer):
        rec=room.get('recording')
        if not rec:return {'phase':'off'}
        if rec['phase']=='pending' and time.monotonic()>=rec['pending_until']:self.stop(room,ack=True)
        if rec['phase'] in ('active','paused') and (rec['members']!=set(room['peers']) or time.monotonic()>=rec['lease']):self.stop(room)
        return {'id':rec['id'],'phase':rec['phase'],'notice':rec['notice'],
                'consented':peer in rec['consents'],'consent_count':len(rec['consents']),
                'participants':len(room['peers']),'owner':rec['owner']==peer}

    def request(self,room,peer,consent):
        self.require(consent is True,'Explicit teacher consent is required.',403)
        self.require(room['peers'][peer]['role']=='admin','Teacher access required.',403)
        self.require(not room.get('recording') or room['recording']['phase'] in ('off','stopped'),'A recording request is already open.')
        policy=self.policy()
        self.require(all(self.eligible(p,policy) for p in room['peers'].values()),'Every student needs unexpired OWNER-recorded guardian authorization. Guests cannot be recorded.',403)
        room['recording']={'id':secrets.token_hex(16),'owner':peer,'phase':'pending','notice':policy['notice'],
                           'consents':{peer},'members':set(room['peers']),'lease':0,'block_until':0,'pending_until':time.monotonic()+120}
        return self.status(room,peer)

    def consent(self,room,peer,record_id,accepted):
        rec=room.get('recording');self.require(rec and rec['id']==record_id and rec['phase']=='pending','Recording request expired.')
        self.require(time.monotonic()<rec['pending_until'],'Recording request expired.')
        self.require(type(accepted) is bool,'Choose consent or decline.',400)
        if not accepted:self.stop(room);return self.status(room,peer)
        self.require(self.eligible(room['peers'][peer],self.policy()),'Guardian authorization is missing or expired.',403)
        rec['consents'].add(peer);return self.status(room,peer)

    def start(self,room,peer,uid,cid,mime):
        rec=room.get('recording');self.require(rec and rec['owner']==peer and rec['phase']=='pending','No recording request is ready.')
        self.require(time.monotonic()<rec['pending_until'],'Recording request expired.')
        self.require(rec['members']==set(room['peers'])==rec['consents'],'Every connected participant must affirmatively consent.',403)
        policy=self.policy();self.require(all(self.eligible(p,policy) for p in room['peers'].values()),'Guardian authorization expired.',403)
        self.require(mime in ('video/webm','video/mp4'),'Unsupported recording container.',400)
        self.folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.require(not self.folder.is_symlink(),'Recording storage cannot be linked.')
        self.require(shutil.disk_usage(self.folder).free>=512*1024**2,'Not enough free disk space for recording.',507)
        with self.db() as c:
            self.require(c.execute('SELECT COALESCE(SUM(bytes),0) FROM recordings').fetchone()[0]<5*1024**3,'Recording storage quota reached.',507)
            c.execute('INSERT INTO recordings(id,owner,class_id,created,expires,mime,state) VALUES (?,?,?,?,?,?,?)',
                      (rec['id'],uid,cid,time.time(),time.time()+policy['retention_days']*86400,mime,'capturing'))
        rec['phase']='active';rec['lease']=time.monotonic()+2;self.activity[rec['id']]=time.time()
        return {'id':rec['id'],'lease_ms':1500,'allowed':sorted(rec['consents'])}

    def heartbeat(self,room,peer,record_id):
        rec=room.get('recording');self.status(room,peer)
        self.require(rec and rec['id']==record_id and rec['owner']==peer and rec['phase'] in ('active','paused'),'Recording authorization ended.',403)
        policy=self.policy()
        self.require(all(self.eligible(p,policy) for p in room['peers'].values()),'Recording authorization expired.',403)
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
        self.require(row,'Recording unavailable.',404);return dict(row)

    def chunk(self,record_id,uid,sequence,data):
        with self.record_lock(record_id):
            row=self.row(record_id,uid);self.require(row['state']=='capturing','Recording is no longer accepting chunks.')
            self.require(time.time()<min(row['created']+7200,row['expires']),'Recording duration limit reached.')
            digest=hashlib.sha256(data).hexdigest()
            if sequence==row['sequence']-1 and digest==row['last_hash']:return {'ok':True,'sequence':row['sequence']}
            self.require(type(sequence) is int and sequence==row['sequence'],'Recording chunk is out of order.')
            self.require(0<len(data)<=8*1024**2,'Recording chunk too large.',413)
            if not sequence:self.require(data.startswith(b'\x1aE\xdf\xa3') if row['mime']=='video/webm' else data[4:8]==b'ftyp','Invalid recording container.',415)
            self.require(row['bytes']+len(data)<=2*1024**3,'Recording size limit reached.',507)
            self.require(shutil.disk_usage(self.folder).free>len(data)+128*1024**2,'Not enough recording disk space.',507)
            with self.db() as c:self.require(c.execute('SELECT COALESCE(SUM(bytes),0) FROM recordings').fetchone()[0]+len(data)<=5*1024**3,'Recording quota reached.',507)
            path=self.folder/(record_id+'.part');self.require(not path.is_symlink(),'Invalid storage path.')
            with path.open('a+b') as stream:
                stream.truncate(row['bytes']);stream.write(data);stream.flush()
                import os;os.fsync(stream.fileno())
            with self.db() as c:c.execute('UPDATE recordings SET bytes=?,sequence=?,last_hash=? WHERE id=?',(row['bytes']+len(data),sequence+1,digest,record_id))
            return {'ok':True,'sequence':sequence+1}

    def finish(self,record_id,uid,complete):
        with self.record_lock(record_id):
            row=self.row(record_id,uid);source=self.folder/(record_id+'.part')
            if row['state']!='capturing':return {'ok':True,'state':row['state']}
            self.require(type(complete) is bool,'Invalid finalization.',400)
            state='uploading' if row['bytes'] else 'empty'
            if source.exists():
                with source.open('r+b') as stream:stream.truncate(row['bytes'])
                source.replace(self.folder/(record_id+('.mp4' if row['mime']=='video/mp4' else '.webm')))
            with self.db() as c:c.execute('UPDATE recordings SET state=?,interrupted=? WHERE id=?',(state,int(not complete),record_id))
            self.wake.set()
            return {'ok':True,'state':state}

    def delete(self,record_id,uid):
        with self.record_lock(record_id):
            row=self.row(record_id,uid)
            self.require(row['state']!='capturing','Stop this recording before deleting it.')
            self.cloud.remove(row)
            for ext in ('.part','.webm','.mp4'):(self.folder/(record_id+ext)).unlink(missing_ok=True)
            with self.db() as c:c.execute('DELETE FROM recordings WHERE id=?',(record_id,))

    def cleanup(self):
        with self.db() as c:expired=c.execute('SELECT id,owner FROM recordings WHERE expires<=?',(time.time(),)).fetchall()
        for item in expired:self.delete(item['id'],item['owner'])

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
        return {'recordings':[dict(row) for row in rows]}

    def finalize(self,record_id,uid,complete,duration):
        self.require(type(duration) in (float,int) and 0<=duration<=7200,'Invalid recording duration.',400)
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
                    with self.db() as c:rows=c.execute("SELECT * FROM recordings WHERE state='uploading' AND expires>? ORDER BY created LIMIT 20",(time.time(),)).fetchall()
                    for item in rows:
                        if self.closed.is_set():break
                        # Serialize cloud transfer/delete so deleted recordings cannot reappear.
                        with self.record_lock(item['id']):
                            row=self.row(item['id'],item['owner'])
                            path=self.folder/(row['id']+('.mp4' if row['mime']=='video/mp4' else '.webm'))
                            def checkpoint(upload,parts):
                                with self.db() as c:c.execute('UPDATE recordings SET upload_id=?,parts=? WHERE id=?',(upload,json.dumps(parts),row['id']))
                            self.cloud.upload(row,path,checkpoint)
                            with self.db() as c:c.execute("UPDATE recordings SET state='ready' WHERE id=?",(row['id'],))
                            self.activity.pop(row['id'],None)
                            path.unlink(missing_ok=True)
                except Exception:
                    # Never log object IDs, credentials, paths or user/media content.
                    print('Recording cloud transfer pending; check private storage configuration and persistent disk.',flush=True)
                self.wake.wait(30)
        self.worker=threading.Thread(target=run,daemon=True);self.worker.start()

    def close(self):self.closed.set();self.wake.set()
