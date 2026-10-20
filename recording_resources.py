"""Recording resources extend existing redeem grants; never grant public access."""
import hashlib
import json
import secrets
import time


class Sharing:
    def __init__(self,store,db,error):self.store=store;self.features=store.features;self.db=db;self.error=error
    def require(self,value,message,status=403):
        if not value:raise self.error(message,status)

    def lesson(self,row):
        with self.db() as c:lesson=c.execute('SELECT * FROM classes WHERE id=?',(row['class_id'],)).fetchone()
        with self.features.db() as c:captured=c.execute('SELECT * FROM recording_context WHERE id=?',(row['id'],)).fetchone()
        self.require(captured and captured['kind'] in ('individual','group'),'This recording has no verified scheduled capture roster.')
        self.require(lesson and lesson['class_kind'] in ('individual','group') and lesson['approval']=='confirmed','Only verified scheduled lessons support absentee sharing.')
        return {**dict(lesson),'start':captured['start'],'title':captured['title']}

    def roster(self,row):
        lesson=self.lesson(row)
        with self.db() as c:booked=c.execute('SELECT b.user_id,u.name FROM bookings b JOIN users u ON u.id=b.user_id WHERE b.class_id=? AND u.role=\'student\'',(row['class_id'],)).fetchall()
        with self.features.db() as c:
            context=c.execute('SELECT roster FROM recording_context WHERE id=?',(row['id'],)).fetchone()
            snapshot=set(json.loads(context['roster'])) if context else set()
            attendance={r['user_id']:r['status'] for r in c.execute('SELECT user_id,status FROM attendance WHERE class_id=?',(row['class_id'],))}
        return {'lesson':{'id':lesson['id'],'title':lesson['title'],'start':lesson['start']},'students':[{'id':u['user_id'],'name':u['name'],'attendance':attendance.get(u['user_id'],'unknown'),'enrolled_at_capture':u['user_id'] in snapshot} for u in booked]}

    def snapshot_roster(self,cid):
        with self.db() as c:
            lesson=c.execute('SELECT class_kind FROM classes WHERE id=?',(cid,)).fetchone()
            if not lesson or lesson['class_kind'] not in ('individual','group'):return
            users=[r[0] for r in c.execute('SELECT user_id FROM bookings WHERE class_id=?',(cid,))]
        with self.features.db() as c:
            for uid in users:c.execute('INSERT OR IGNORE INTO lesson_roster VALUES (?,?)',(cid,uid))

    def present(self,cid,user):
        if user['role']!='student':return
        with self.features.db() as c:c.execute("INSERT INTO attendance(class_id,user_id,status,at) VALUES (?,?,'present',?) ON CONFLICT(class_id,user_id) DO UPDATE SET status='present',verified_by=NULL,at=excluded.at",(cid,user['id'],time.time()))

    def verify_absent(self,row,teacher,uid,confirmed):
        self.require(confirmed is True,'Teacher must explicitly verify absence.')
        roster=self.roster(row)['students'];person=next((u for u in roster if u['id']==uid),None)
        self.require(person and person['enrolled_at_capture'] and person['attendance']!='present','Enrollment or absence cannot be verified.')
        with self.features.db() as c:c.execute("INSERT INTO attendance VALUES (?,?,'verified_absent',?,?) ON CONFLICT(class_id,user_id) DO UPDATE SET status='verified_absent',verified_by=excluded.verified_by,at=excluded.at",(row['class_id'],uid,teacher,time.time()))
        self.features.audit('verify_absence',teacher,row['id']);return {'ok':True}

    def eligible(self,row,uid):
        self.lesson(row)
        with self.db() as c:enrolled=c.execute('SELECT 1 FROM bookings WHERE class_id=? AND user_id=?',(row['class_id'],uid)).fetchone()
        with self.features.db() as c:
            context=c.execute('SELECT roster FROM recording_context WHERE id=?',(row['id'],)).fetchone()
            original=context and uid in json.loads(context['roster'])
            absent=c.execute("SELECT 1 FROM attendance WHERE class_id=? AND user_id=? AND status='verified_absent'",(row['class_id'],uid)).fetchone()
        self.require(enrolled and original and absent,'This account is not an authorized absent enrollee.')

    def subjects_allowed(self,row,download):
        scope=json.loads(row['scope'])
        self.require(scope.get('sharing') is True and (not download or scope.get('download') is True),'The recording authorization does not cover this sharing purpose.')
        from recording_authorization import sharing_allowed
        self.require(sharing_allowed(self.features,row,download),'Participant or guardian sharing authorization is missing, expired or withdrawn.')

    def create(self,row,teacher,viewers,expiry,download):
        self.require(row['state']=='ready' and not row['interrupted'] and row['expires']>time.time(),'Only completed cloud recordings may be shared.')
        self.require(type(download) is bool and isinstance(viewers,list) and 1<=len(viewers)<=100 and all(type(uid) is int for uid in viewers),'Choose eligible absent accounts.',400)
        self.require(type(expiry) in (float,int) and time.time()<expiry<=min(row['expires'],time.time()+30*86400),'Invalid share expiry.',400)
        self.subjects_allowed(row,download)
        for uid in viewers:self.eligible(row,uid)
        with self.features.db() as c:
            indexed=c.execute("SELECT 1 FROM recording_playback WHERE id=? AND state='ready'",(row['id'],)).fetchone()
        self.require(indexed,'Seekable playback is not ready. OWNER must configure its trusted FFmpeg and finish processing.',409)
        alphabet='ABCDEFGHJKLMNPQRSTUVWXYZ23456789';code=''.join(secrets.choice(alphabet) for _ in range(20));digest=hashlib.sha256(code.encode()).hexdigest()
        with self.features.db() as c:
            c.execute('INSERT INTO recording_codes VALUES (?,?,?,?,0,?,?)',(digest,row['id'],teacher,expiry,int(download),time.time()))
            for uid in set(viewers):c.execute('INSERT INTO recording_viewers VALUES (?,?)',(digest,uid))
        self.features.audit('grant',teacher,row['id'],digest)
        return {'code':code,'expires':expiry,'download':download,'grant_id':digest}

    def revoke(self,row,teacher,grant_id):
        with self.features.db() as c:
            result=c.execute('UPDATE recording_codes SET revoked=1 WHERE code_hash=? AND owner=? AND recording_id=?',(grant_id,teacher,row['id']))
        self.require(result.rowcount,'Recording grant unavailable.',404);self.features.audit('revoke',teacher,row['id'],grant_id);return {'ok':True}

    def grants(self,row):
        with self.features.db() as c:return {'grants':[dict(r) for r in c.execute('SELECT code_hash AS grant_id,expires,revoked,download,created FROM recording_codes WHERE recording_id=? AND owner=? ORDER BY created DESC LIMIT 200',(row['id'],row['owner']))]}

    def authorize(self,digest,user,download=False):
        self.require(user and user['role']=='student','Sign in with the enrolled student account.',401 if not user else 403)
        import policy_service
        self.require(not policy_service.due(self.features,user['id']),'Review the current policies before accessing a recording resource.')
        with self.features.db() as c:
            grant=c.execute('SELECT * FROM recording_codes WHERE code_hash=?',(digest,)).fetchone()
            allowed=c.execute('SELECT 1 FROM recording_viewers WHERE code_hash=? AND user_id=?',(digest,user['id'])).fetchone()
        self.require(grant and allowed and not grant['revoked'] and grant['expires']>time.time(),'Recording resource access is unavailable.')
        self.require(not download or grant['download'],'Downloads are not permitted for this recording.')
        row=self.store.row(grant['recording_id'],grant['owner'])
        self.require(row['state']=='ready' and not row['interrupted'] and row['expires']>time.time(),'Recording resource is unavailable.')
        self.eligible(row,user['id']);self.subjects_allowed(row,download)
        return row

    def redeem(self,code,user):
        digest=hashlib.sha256(code.encode()).hexdigest()
        with self.features.db() as c:exists=c.execute('SELECT download FROM recording_codes WHERE code_hash=?',(digest,)).fetchone()
        if not exists:return None
        row=self.authorize(digest,user);lesson=self.lesson(row);
        with self.db() as c:zone=c.execute("SELECT value FROM settings WHERE key='timezone'").fetchone()
        self.features.audit('redeem',user['id'],row['id'],digest)
        return {'code_hash':digest,'recording':{'title':lesson['title'],'timezone':zone[0] if zone else 'America/Edmonton','date':lesson['start'],'duration':row['duration'],'download':bool(exists['download'])},'label':lesson['title']}
