"""Synthetic authorization, storage, recovery and private-cloud regressions."""
import io
import json
import time
from pathlib import Path
from unittest import mock
import unittest
from test_security_stability import BackendCase
from recording_cloud import R2


class RecordingTests(BackendCase):
    def policy(self,guardian=True):
        policy={'enabled':True,'policy_approved':True,'private_cloud_approved':True,
                'notice':'Synthetic approved recording notice. Consent is optional.',
                'guardian_authorizations':{str(self.uid('student')):time.time()+3600} if guardian else {},'retention_days':7}
        (self.app.DATA/'recording-policy.json').write_text(json.dumps(policy))
        self.cloud=mock.Mock();self.cloud.ready.return_value=True;self.app.RECORDING_STORE.cloud=self.cloud

    def active(self):
        teacher,student,cid,tp,sp=self.room();self.policy()
        def action(name,data=None,state=teacher,peer=tp):return self.request('/api/room/recording-'+name,{'class_id':cid,'peer':peer,**(data or {})},state)
        status,out,_=action('request',{'consent':True});self.assertEqual(status,200,out);rid=out['id']
        self.assertEqual(action('consent',{'id':rid,'accepted':True},student,sp)[0],200)
        status,out,_=action('start',{'mime':'video/webm'});self.assertEqual(status,200,out)
        return teacher,student,cid,tp,sp,rid,action

    def chunk(self,rid,state,data=b'\x1aE\xdf\xa3synthetic',seq=0,csrf=True):
        return self.request(f'/api/admin/recordings/chunk?id={rid}&sequence={seq}',state=state,raw=data,headers={'Content-Type':'application/octet-stream','X-CSRF-Token':state['csrf'] if csrf else ''})

    def test_disabled_guardian_consent_and_teacher_only_controls(self):
        t,s,cid,tp,sp=self.room()
        def post(state,peer,name,**data):return self.request('/api/room/recording-'+name,{'class_id':cid,'peer':peer,**data},state)
        self.assertEqual(post(t,tp,'request',consent=True)[0],409)
        self.policy(False);self.assertEqual(post(t,tp,'request',consent=True)[0],403)
        self.policy();self.assertEqual(post(s,sp,'request',consent=True)[0],403)
        rid=post(t,tp,'request',consent=True)[1]['id']
        self.assertEqual(post(t,tp,'start',mime='video/webm')[0],403)
        self.assertEqual(post(s,sp,'consent',id=rid,accepted=True)[0],200)
        self.assertEqual(post(s,sp,'start',mime='video/webm')[0],403)
        self.assertEqual(post(t,tp,'start',mime='video/webm')[0],200)
        self.assertEqual(post(s,sp,'pause')[0],403)
        self.assertEqual(post(s,sp,'stop',ack=True)[0],403)
        self.assertEqual(post(t,tp,'pause')[1]['phase'],'paused')
        self.assertEqual(post(t,tp,'heartbeat',id=rid)[0],200)
        self.assertEqual(post(t,tp,'resume')[1]['phase'],'active')
        self.assertEqual(post(s,sp,'withdraw',id=rid)[1]['phase'],'stopping')
        self.assertEqual(post(t,tp,'heartbeat',id=rid)[0],403)

    def test_new_participant_cannot_enter_until_capture_stops(self):
        t,s,cid,tp,sp,rid,action=self.active();other=self.client('teacher2')
        self.assertEqual(self.request('/api/room/join',{'class_id':cid},other)[0],409)
        self.assertEqual(action('heartbeat',{'id':rid})[0],403)
        self.assertEqual(action('stop',{'ack':True})[0],200)
        self.assertEqual(self.request('/api/room/join',{'class_id':cid},other)[0],200)
        self.assertEqual(action('start',{'mime':'video/webm'})[0],409)

    def test_expired_lease_and_guardian_authorization_fail_closed(self):
        t,s,cid,tp,sp,rid,action=self.active()
        room=self.app.ROOMS[cid]
        room['recording']['lease']=time.monotonic()-1
        self.assertEqual(action('heartbeat',{'id':rid})[0],403)
        self.assertEqual(room['recording']['phase'],'stopping')

    def test_students_other_teachers_and_missing_csrf_never_access_files(self):
        t,s,cid,tp,sp,rid,action=self.active();other=self.client('teacher2')
        for state in (self.client(),s):
            self.assertIn(self.request('/api/admin/recordings',state=state)[0],(401,403))
            self.assertIn(self.request('/api/admin/recordings/content?id='+rid+'&ticket=fake',state=state)[0],(401,403))
            self.assertIn(self.chunk(rid,state)[0],(401,403))
            for name in ('access','delete','finish','handoff'):
                self.assertIn(self.request('/api/admin/recordings/'+name,{'id':rid},state)[0],(401,403))
        self.assertEqual(self.chunk(rid,t,csrf=False)[0],403)
        self.assertEqual(self.chunk(rid,other)[0],404)
        self.assertEqual(self.request('/api/admin/recordings/access',{'id':rid},other)[0],404)
        self.assertEqual(self.request('/api/admin/recordings',state=other)[1]['recordings'],[])
        self.cloud.open.assert_not_called()

    def test_chunks_idempotency_order_finalization_and_crash_truncation(self):
        t,s,cid,tp,sp,rid,action=self.active()
        self.assertEqual(self.chunk(rid,t,data=b'wrong')[0],415)
        first=b'\x1aE\xdf\xa3synthetic';self.assertEqual(self.chunk(rid,t,first)[0],200)
        self.assertEqual(self.chunk(rid,t,first)[1]['sequence'],1)
        self.assertEqual(self.chunk(rid,t,b'different')[0],409)
        self.assertEqual(self.chunk(rid,t,b'end',2)[0],409)
        self.assertEqual(self.chunk(rid,t,b'end',1)[0],200)
        path=self.app.RECORDING_STORE.folder/(rid+'.part')
        with path.open('ab') as file:file.write(b'uncommitted crash tail')
        out=self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':123},t)
        self.assertEqual(out[0],200,out)
        self.assertEqual(out[1]['state'],'processing')
        self.assertEqual(path.with_suffix('.webm').read_bytes(),first+b'end')
        self.assertEqual(self.chunk(rid,t,b'late',2)[0],409)
        listed=self.request('/api/admin/recordings',state=t)[1]['recordings'][0]
        self.assertEqual(listed['duration'],123);self.assertEqual(listed['state'],'processing')
        self.assertEqual(self.request('/api/admin/recordings/access',{'id':rid},t)[0],409)
        self.app.RECORDING_STORE.delete(rid,self.uid('teacher'));self.cloud.remove.assert_called_once()
        self.assertFalse(path.with_suffix('.webm').exists())

    def test_unrelated_recordings_never_share_a_cloud_transfer_lock(self):
        # Holding all references models simultaneous uploads/chunk requests.
        # A fixed lock-stripe pool made unrelated recordings block each other.
        store=self.app.RECORDING_STORE
        locks=[store.record_lock(f'{i:032x}') for i in range(20)]
        self.assertEqual(len({id(lock) for lock in locks}),20)
        self.assertIs(store.record_lock(f'{0:032x}'),locks[0])

    def test_recovery_uploads_to_cloud_and_removes_spool_after_acknowledgment(self):
        t,s,cid,tp,sp,rid,action=self.active();self.chunk(rid,t)
        store=self.app.RECORDING_STORE
        store.recovery_before=time.time()+.001
        store.launch()
        try:
            until=time.monotonic()+3
            while time.monotonic()<until and store.row(rid,self.uid('teacher'))['state']!='ready':time.sleep(.01)
            row=store.row(rid,self.uid('teacher'));self.assertEqual(row['state'],'ready');self.assertEqual(row['interrupted'],1)
            self.cloud.upload.assert_called_once();self.assertFalse((store.folder/(rid+'.webm')).exists())
        finally:store.close();store.worker.join(2)

    def test_ready_playback_requires_current_owner_session_and_expiring_ticket(self):
        t,s,cid,tp,sp,rid,action=self.active()
        with self.app.db() as c:c.execute("UPDATE recordings SET state='ready' WHERE id=?",(rid,))
        url=self.request('/api/admin/recordings/access',{'id':rid},t)[1]['url']
        response=io.BytesIO(b'video');response.status=206;response.headers={'Content-Length':'5','Content-Range':'bytes 0-4/5','Accept-Ranges':'bytes'}
        self.cloud.open.return_value=response
        status,data,headers=self.request(url,state=t,headers={'Range':'bytes=0-4'})
        self.assertEqual((status,data),(206,b'video'));self.assertEqual(headers['Content-Type'],'video/webm')
        self.assertEqual(headers['Cache-Control'],'private, no-store');self.cloud.open.assert_called_once();self.cloud.open.reset_mock()
        self.assertEqual(self.request(url,state=s)[0],403)
        # Expiration/revocation checked before any cloud access.
        for session in self.app.SESSIONS.values():
            for grant in session.get('recording_tickets',{}).values():grant['expires']=time.time()-1
        self.assertEqual(self.request(url,state=t)[0],403);self.cloud.open.assert_not_called()
        url=self.request('/api/admin/recordings/handoff',{'id':rid},t)[1]['url']
        self.request('/api/logout',{},t)
        self.assertEqual(self.request(url,state=self.client())[0],403)


class CloudTests(unittest.TestCase):
    def test_multipart_retry_resumes_acknowledged_parts_and_never_uses_public_url(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic';path.write_bytes(b'x'*(8*1024**2)+b'end')
            r2=R2(lambda:{'backend':'r2'});r2.request=mock.Mock(side_effect=[(b'<Result><UploadId>synthetic</UploadId></Result>',{}),(b'',{'ETag':'one'}),RuntimeError('interrupted')])
            saved={}
            def checkpoint(upload,parts):saved.update(upload_id=upload,parts=json.dumps(parts))
            row={'id':'a'*32,'mime':'video/webm','upload_id':'','parts':'[]'}
            with self.assertRaises(RuntimeError):r2.upload(row,path,checkpoint)
            self.assertEqual(json.loads(saved['parts']),['one'])
            r2.request=mock.Mock(side_effect=[(b'',{'ETag':'two'}),(b'<CompleteMultipartUploadResult/>',{})])
            r2.upload({**row,**saved},path,checkpoint)
            self.assertEqual(r2.request.call_args_list[0].args[2],b'end')
            self.assertEqual(r2.request.call_args_list[0].args[3],{'partNumber':2,'uploadId':'synthetic'})
            self.assertEqual(r2.request.call_args_list[1].args[0],'POST')

    def test_lost_completion_ack_checks_private_object_size_before_replaying(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'x';path.write_bytes(b'synthetic')
            r2=R2(lambda:{'backend':'r2'});r2.request=mock.Mock(return_value=(b'',{'Content-Length':'9'}))
            r2.upload({'id':'a'*32,'mime':'video/webm','upload_id':'old','parts':'["etag"]'},path,lambda *x:None)
            self.assertEqual(r2.request.call_args.args,('HEAD','private-recordings/'+'a'*32));self.assertEqual(r2.request.call_count,1)

    def test_invalid_cloud_completion_does_not_count_as_ready(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'x';path.write_bytes(b'x')
            r2=R2(lambda:{'backend':'r2'});r2.request=mock.Mock(side_effect=[(b'<r><UploadId>x</UploadId></r>',{}),(b'',{'ETag':'one'}),(b'<Error/>',{})])
            with self.assertRaises(RuntimeError):r2.upload({'id':'a'*32,'mime':'video/webm','upload_id':'','parts':'[]'},path,lambda *x:None)
