"""Run: py -S test_server.py. Uses a temporary database, never your real data."""
import concurrent.futures
import http.client
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
import zipfile

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        os.environ['MATH_DATA']=cls.temp.name
        import server
        cls.app=server
        with sqlite3.connect(str(Path(cls.temp.name)/'posts.db')) as c:
            c.execute('CREATE TABLE admins(id INTEGER PRIMARY KEY,name TEXT,password TEXT)')
            c.execute('INSERT INTO admins(name,password) VALUES (?,?)',('teacher',server.hash_password('temporary-password-123')))
        c.close()  # sqlite connection context commits; it does not close the handle.
        server.init()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()

    def client(self):
        state={'cookie':'','csrf':''}
        def request(path,data=None,csrf=True):
            conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
            headers={'Cookie':state['cookie']}
            if data is not None:
                headers['Content-Type']='application/json'
                if csrf: headers['X-CSRF-Token']=state['csrf']
            conn.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers)
            r=conn.getresponse();raw=r.read();status=r.status
            if r.getheader('Set-Cookie'):state['cookie']=r.getheader('Set-Cookie').split(';')[0]
            payload=json.loads(raw) if r.getheader('Content-Type','').startswith('application/json') else raw
            if isinstance(payload,dict) and 'csrf' in payload:state['csrf']=payload['csrf']
            conn.close();return status,payload
        request('/api/me')
        return request


    def test_group_chats_and_group_booking(self):
        teacher,s1,s2,s3=[self.client() for _ in range(4)]
        self.assertEqual(teacher('/api/login',{'username':'teacher','password':'temporary-password-123'})[0],200)
        for client,username in [(s1,'group_student_one'),(s2,'group_student_two'),(s3,'group_student_three')]:
            self.assertEqual(client('/api/signup',{'name':username,'username':username,'password':'temporary-password-123'})[0],200)
        info=teacher('/api/admin')[1]
        ids={u['username']:u['id'] for u in info['users']}
        created=teacher('/api/admin/groups/create',{'name':'Grade 7 Class 1','user_ids':[ids['group_student_one'],ids['group_student_two']]})
        self.assertEqual(created[0],200); gid=created[1]['group_id']
        self.assertTrue(any(g['id']==gid for g in s1('/api/groups')[1]['groups']))
        self.assertFalse(any(g['id']==gid for g in s3('/api/groups')[1]['groups']))
        self.assertEqual(teacher('/api/group-messages/send',{'group_id':gid,'text':'Homework code ABC234'})[0],200)
        self.assertEqual(s1(f'/api/group-messages?group={gid}&since=0')[0],200)
        self.assertEqual(s3(f'/api/group-messages?group={gid}&since=0')[0],403)
        self.assertEqual(teacher('/api/admin/groups/update',{'group_id':gid,'name':'Grade 7 Class 1','user_ids':[ids['group_student_one'],ids['group_student_two'],ids['group_student_three']]})[0],200)
        self.assertEqual(s3(f'/api/group-messages?group={gid}&since=0')[0],200)

        schedule=teacher('/api/schedule')[1]
        lesson=next(x for x in schedule['lesson_types'] if x['name']=='Grade 8 Math' and x['minutes']==60)
        start=((int(time.time()+31*86400)//900)+1)*900
        made=teacher('/api/admin/group-class',{'title':'Grade 8 Algebra Group','lesson_type_id':lesson['id'],'start':start,'capacity':2,'price_label':'Price TBD','description':'Algebra practice','repeat_weekly':False,'weeks':1})
        self.assertEqual(made[0],200); cid=made[1]['ids'][0]; lesson_gid=made[1]['group_chat_id']
        self.assertEqual(s1('/api/group-booking/join',{'class_id':cid})[0],200)
        self.assertEqual(s2('/api/group-booking/join',{'class_id':cid})[0],200)
        self.assertEqual(s3('/api/group-booking/join',{'class_id':cid})[0],409)
        c=next(x for x in s1('/api/classes')[1]['classes'] if x['id']==cid)
        self.assertEqual(c['class_kind'],'group'); self.assertEqual(c['booked'],2); self.assertTrue(c['mine'])
        self.assertTrue(any(g['id']==lesson_gid for g in s1('/api/groups')[1]['groups']))
        self.assertEqual(teacher('/api/admin/groups/delete',{'group_id':lesson_gid})[0],409)
        self.assertEqual(s1('/api/unbook',{'class_id':cid})[0],200)
        self.assertEqual(s3('/api/group-booking/join',{'class_id':cid})[0],200)
        self.assertEqual(teacher('/api/admin/groups/delete',{'group_id':gid})[0],200)

    def test_resource_file_codes(self):
        def raw_request(state,path,body=None,headers=None,method=None):
            conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
            h={'Cookie':state.get('cookie','')}
            if headers: h.update(headers)
            if method is None: method='POST' if body is not None else 'GET'
            conn.request(method,path,body,h)
            r=conn.getresponse(); raw=r.read(); status=r.status; ctype=r.getheader('Content-Type','')
            if r.getheader('Set-Cookie'): state['cookie']=r.getheader('Set-Cookie').split(';')[0]
            conn.close()
            return status,raw,ctype,r.getheader('Content-Disposition','')
        def json_request(state,path,data=None):
            headers={}
            body=None
            if data is not None:
                body=json.dumps(data).encode(); headers={'Content-Type':'application/json','X-CSRF-Token':state['csrf']}
            status,raw,ctype,_=raw_request(state,path,body,headers)
            payload=json.loads(raw)
            if 'csrf' in payload: state['csrf']=payload['csrf']
            return status,payload
        teacher={'cookie':'','csrf':''}; guest={'cookie':'','csrf':''}; other={'cookie':'','csrf':''}
        for state in (teacher,guest,other): json_request(state,'/api/me')
        self.assertEqual(json_request(teacher,'/api/login',{'username':'teacher','password':'temporary-password-123'})[0],200)
        for name,data in [('Unit 1 Notes.pdf',b'%PDF-1.4\nnotes'),('Unit 1 Homework.docx',b'PK\x03\x04homework')]:
            status,payload,ctype,_=raw_request(teacher,'/api/admin/files/upload',data,{
                'Content-Type':'application/octet-stream','X-CSRF-Token':teacher['csrf'],
                'X-File-Name':name.replace(' ','%20'),'X-File-Type':'application%2Foctet-stream'},'POST')
            self.assertEqual(status,200,payload)
        status,library=json_request(teacher,'/api/admin/files')
        self.assertEqual(status,200); self.assertEqual(len(library['files']),2)
        ids=[x['id'] for x in library['files']]
        status,created=json_request(teacher,'/api/admin/files/code',{'file_ids':ids,'label':'Grade 7 Unit 1'})
        self.assertEqual(status,200); code=created['code']; self.assertEqual(len(code),6)
        self.assertEqual(json_request(other,'/api/resources/redeem',{'code':'WRONG9'})[0],404)
        status,bundle=json_request(guest,'/api/resources/redeem',{'code':code.lower()})
        self.assertEqual(status,200); self.assertEqual(bundle['label'],'Grade 7 Unit 1'); self.assertEqual(len(bundle['files']),2)
        grant=bundle['grant']; file_id=bundle['files'][0]['id']
        status,raw,ctype,disp=raw_request(guest,f'/resource/download?grant={grant}&file={file_id}')
        self.assertEqual(status,200); self.assertIn('attachment',disp)
        self.assertEqual(raw,next(data for name,data in [('Unit 1 Notes.pdf',b'%PDF-1.4\nnotes'),('Unit 1 Homework.docx',b'PK\x03\x04homework')] if name==bundle['files'][0]['name']))
        self.assertEqual(raw_request(other,f'/resource/download?grant={grant}&file={file_id}')[0],403)
        status,zraw,ctype,disp=raw_request(guest,f'/resource/download-all?grant={grant}')
        self.assertEqual(status,200); self.assertEqual(ctype,'application/zip')
        with zipfile.ZipFile(io.BytesIO(zraw)) as z:
            self.assertEqual(set(z.namelist()),{'Unit 1 Notes.pdf','Unit 1 Homework.docx'})
        code_id=next(x['id'] for x in json_request(teacher,'/api/admin/files')[1]['codes'] if x['code']==code)
        self.assertEqual(json_request(teacher,'/api/admin/files/code-action',{'code_id':code_id,'action':'revoke'})[0],200)
        self.assertEqual(json_request(guest,'/api/resources/redeem',{'code':code})[0],404)

    def test_full_flow(self):
        a,s1,s2,guest=[self.client() for _ in range(4)]
        self.assertEqual(a('/api/login',{'username':'teacher','password':'temporary-password-123'})[0],200)
        self.assertEqual(a('/api/me')[1]['user']['role'],'admin')
        for client,username in [(s1,'student_one'),(s2,'student_two')]:
            status,data=client('/api/signup',{'name':username,'username':username,'password':'temporary-password-123','role':'admin'})
            self.assertEqual(status,200);self.assertEqual(data['user']['role'],'student')
        self.assertEqual(guest('/api/admin')[0],401)
        self.assertEqual(s1('/api/admin')[0],403)
        self.assertEqual(a('/api/admin/post',{'title':'x','body':'y'},csrf=False)[0],403)
        self.assertEqual(a('/api/admin/post',{'title':'Hello','body':'<script>test</script>'})[0],200)
        self.assertEqual(guest('/api/public')[1]['posts'][0]['title'],'Hello')

        start=((int(time.time()+900)//900)+1)*900; end=start+2*3600
        av=a('/api/admin/availability',{'start':start,'end':end,'repeat_weekly':True,'weeks':3})
        self.assertEqual(av[0],200); self.assertEqual(len(av[1]['ids']),3)
        schedule=s1('/api/schedule')[1]
        lesson=next(x for x in schedule['lesson_types'] if x['name']=='Grade 10 AP Math' and x['minutes']==90)
        aid=schedule['availability'][0]['id']
        req={'lesson_type_id':lesson['id'],'availability_id':aid,'start':start}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda c:c('/api/request-booking',req)[0],[s1,s2]))
        self.assertEqual(sorted(results),[200,409])
        winner,loser=(s1,s2) if results[0]==200 else (s2,s1)
        username='student_one' if winner is s1 else 'student_two'
        info=a('/api/admin')[1]
        booking=next(x for x in info['bookings'] if x['username']==username)
        cid=booking['class_id']
        self.assertEqual(booking['approval'],'pending')
        self.assertEqual(winner('/api/room/join',{'class_id':cid})[0],409)
        self.assertEqual(loser('/api/request-booking',{'lesson_type_id':lesson['id'],'availability_id':aid,'start':start+1800})[0],409)

        weekly=a('/api/admin/booking-action',{'class_id':cid,'action':'confirm_weekly','weeks':3})
        self.assertEqual(weekly[0],200); self.assertEqual(weekly[1]['created'],3)
        mine=[x for x in winner('/api/classes')[1]['classes'] if x['mine'] and x['status']=='scheduled']
        self.assertEqual(len(mine),3); self.assertTrue(all(x['approval']=='confirmed' for x in mine))

        self.assertEqual(a('/api/admin/class-action',{'class_id':cid,'action':'open'})[0],200)
        self.assertEqual(loser('/api/room/join',{'class_id':cid})[0],403)
        ap=a('/api/room/join',{'class_id':cid})[1]['peer']
        sp=winner('/api/room/join',{'class_id':cid})[1]['peer']
        base={'class_id':cid,'peer':ap}; sb={'class_id':cid,'peer':sp}
        self.assertEqual(winner('/api/room/permissions',{**sb,'drawing':True})[0],403)
        board={'background':'grid','shapes':[{'id':'one','type':'line','color':'#09695f','width':4,'x':.1,'y':.1,'x2':.5,'y2':.5}]}
        self.assertEqual(winner('/api/room/board',{**sb,'version':0,'board':board})[0],403)
        self.assertEqual(a('/api/room/board',{**base,'version':0,'board':board})[0],200)
        self.assertEqual(a('/api/room/board',{**base,'version':0,'board':board})[0],409)
        poll=winner(f'/api/room/poll?class={cid}&peer={sp}&since=0')[1]
        self.assertEqual(poll['board'],board)
        self.assertEqual(a('/api/room/permissions',{**base,'drawing':True})[0],200)
        self.assertEqual(winner('/api/room/board',{**sb,'version':1,'board':board})[0],200)
        self.assertEqual(a('/api/room/presenter',{**base,'active':True})[0],200)
        self.assertEqual(winner('/api/room/presenter',{**sb,'active':True})[0],409)
        self.assertEqual(a('/api/room/signal',{**base,'to':sp,'signal':{'description':{'type':'offer','sdp':'test'}}})[0],200)
        with self.app.db() as c:
            c.execute('INSERT INTO resource_codes(code,label,created,created_by,active) VALUES (?,?,?,?,1)',('ABC234','Grade 7 Unit 1',time.time(),a('/api/me')[1]['user']['id']))
        # Persistent class messages work even outside the live room and recognize active resource codes.
        self.assertEqual(a('/api/messages/send',{'class_id':cid,'text':'Unit notes: ABC234'})[0],200)
        persistent=winner(f'/api/messages?class={cid}&since=0')
        self.assertEqual(persistent[0],200); self.assertEqual(persistent[1]['messages'][0]['codes'][0]['code'],'ABC234')
        self.assertEqual(loser(f'/api/messages?class={cid}&since=0')[0],403)
        self.assertEqual(a('/api/room/chat',{**base,'text':'Today’s notes: ABC234'})[0],200)
        first_poll=winner(f'/api/room/poll?class={cid}&peer={sp}&since=0&chat_since=0')[1]
        self.assertEqual(first_poll['chat'][0]['text'],'Today’s notes: ABC234')
        self.assertEqual(first_poll['chat'][0]['codes'][0]['code'],'ABC234')
        self.assertEqual(winner('/api/room/chat',{**sb,'text':'Thanks!'})[0],200)
        later=a(f"/api/room/poll?class={cid}&peer={ap}&since=0&chat_since={first_poll['chatSeq']}")[1]
        self.assertEqual(later['chat'][0]['text'],'Thanks!')
        self.assertEqual(len(first_poll['events']),1)
        self.assertEqual(winner('/api/room/media-state',{**sb,'mic_on':True,'camera_on':True})[0],200)
        teacher_poll=a(f'/api/room/poll?class={cid}&peer={ap}&since=0')[1]
        student_peer=next(x for x in teacher_poll['peers'] if x['id']==sp)
        self.assertTrue(student_peer['mic_on']); self.assertTrue(student_peer['camera_on'])
        self.assertEqual(a('/api/room/mute',{**base,'target':sp,'muted':True})[0],200)
        mute_poll=winner(f"/api/room/poll?class={cid}&peer={sp}&since={first_poll['seq']}")[1]
        self.assertTrue(mute_poll['forcedMute'])
        self.assertEqual(mute_poll['events'][0]['signal']['control'],'host-mute')
        self.assertEqual(winner('/api/room/media-state',{**sb,'mic_on':True,'camera_on':True})[1]['forcedMute'],True)
        teacher_poll=a(f'/api/room/poll?class={cid}&peer={ap}&since=0')[1]
        student_peer=next(x for x in teacher_poll['peers'] if x['id']==sp)
        self.assertFalse(student_peer['mic_on'])
        self.assertEqual(a('/api/room/mute',{**base,'target':sp,'muted':False})[0],200)
        self.assertEqual(a('/api/admin/class-action',{'class_id':cid,'action':'end'})[0],200)
        self.assertEqual(winner(f'/api/room/poll?class={cid}&peer={sp}&since=0')[0],409)
        with self.app.db() as c:self.assertEqual(c.execute('SELECT version FROM boards WHERE class_id=?',(cid,)).fetchone()[0],2)
        self.assertEqual(a('/api/logout',{})[0],200)
        self.assertEqual(a('/api/admin')[0],401)
        self.assertEqual(guest('/bulletin_data/posts.db')[0],404)
        self.assertEqual(guest('/server.py')[0],404)


    def test_instant_meeting_guest_and_account_join(self):
        teacher,guest,student=[self.client() for _ in range(3)]
        self.assertEqual(teacher('/api/login',{'username':'teacher','password':'temporary-password-123'})[0],200)
        made=teacher('/api/admin/instant-meeting',{'title':'Instant Algebra'})
        self.assertEqual(made[0],200)
        code=made[1]['code'];cid=made[1]['class_id']
        self.assertEqual(len(code),10);self.assertTrue(code.isdigit())
        # Instant meetings are live immediately; joining must not depend on the
        # native teacher window launching successfully first.
        joined=guest('/api/instant/join',{'code':code,'name':'Guest Learner'})
        self.assertEqual(joined[0],200);self.assertEqual(joined[1]['class_id'],cid)
        self.assertEqual(guest('/api/me')[1]['user']['role'],'guest')
        g_room=guest('/api/room/join',{'class_id':cid});self.assertEqual(g_room[0],200)
        self.assertEqual(student('/api/signup',{'name':'Account Learner','username':'instant_account','password':'temporary-password-123'})[0],200)
        self.assertEqual(student('/api/instant/join',{'code':code})[0],200)
        s_room=student('/api/room/join',{'class_id':cid});self.assertEqual(s_room[0],200)
        # A second device signed into the same student account must not kick out
        # the first device or other participants.
        student2=self.client()
        self.assertEqual(student2('/api/login',{'username':'instant_account','password':'temporary-password-123'})[0],200)
        self.assertEqual(student2('/api/instant/join',{'code':code})[0],200)
        s2_room=student2('/api/room/join',{'class_id':cid});self.assertEqual(s2_room[0],200)
        poll_multi=student(f"/api/room/poll?class={cid}&peer={s_room[1]['peer']}&since=0&chat_since=0")
        self.assertEqual(poll_multi[0],200)
        self.assertGreaterEqual(len(poll_multi[1]['peers']),2)
        self.assertEqual(guest('/api/room/chat',{'class_id':cid,'peer':g_room[1]['peer'],'text':'Hello from guest'})[0],200)
        poll=student(f"/api/room/poll?class={cid}&peer={s_room[1]['peer']}&since=0&chat_since=0")
        self.assertEqual(poll[0],200);self.assertEqual(poll[1]['chat'][0]['text'],'Hello from guest')
        self.assertEqual(teacher('/api/admin/class-action',{'class_id':cid,'action':'end'})[0],200)
        self.assertEqual(guest('/api/room/join',{'class_id':cid})[0],409)

    def test_teacher_media_handoff_goes_direct_to_classroom(self):
        teacher=self.client()
        self.assertEqual(teacher('/api/login',{'username':'teacher','password':'temporary-password-123'})[0],200)
        made=teacher('/api/admin/instant-meeting',{'title':'Direct Host Meeting'})
        self.assertEqual(made[0],200); cid=made[1]['class_id']
        launch=teacher('/api/admin/teacher-app-launch',{'class_id':cid,'client_launch':True})
        self.assertEqual(launch[0],200); self.assertTrue(launch[1].get('browser_url')); app_token=launch[1]['token']
        handoff=teacher('/api/teacher-app/media-login-token',{'token':app_token})
        self.assertEqual(handoff[0],200); media_token=handoff[1]['media_token']

        # Simulate the clean browser app window the native Teacher App opens.
        state={'cookie':''}
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
        conn.request('GET',f'/teacher-media-login?token={media_token}',headers={'Cookie':''})
        r=conn.getresponse(); raw=r.read();
        self.assertEqual(r.status,302); self.assertEqual(r.getheader('Location'),f'/classroom?id={cid}&teacherhost=1&autojoin=1')
        cookie=r.getheader('Set-Cookie'); self.assertTrue(cookie); state['cookie']=cookie.split(';')[0]
        conn.close()
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
        conn.request('GET','/api/me',headers={'Cookie':state['cookie']})
        r=conn.getresponse(); payload=json.loads(r.read()); conn.close()
        self.assertEqual(r.status,200); self.assertEqual(payload['user']['role'],'admin')
        # One-time means the bootstrap URL cannot be replayed.
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
        conn.request('GET',f'/teacher-media-login?token={media_token}',headers={'Cookie':''})
        r=conn.getresponse(); r.read(); conn.close()
        self.assertEqual(r.status,403)

if __name__=='__main__':unittest.main(verbosity=2)

# v37 direct teacher-browser handoff smoke test lives outside unittest class intentionally
