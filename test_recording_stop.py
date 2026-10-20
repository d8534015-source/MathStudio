"""Normal Stop, final chunk drain and native-end ordering; synthetic accounts only."""
import json,time,threading
from unittest import mock
from test_security_stability import BackendCase
import test_classroom_recording as prior

class StopTests(BackendCase):
    active=prior.RecordingTests.active;policy=prior.RecordingTests.policy;chunk=prior.RecordingTests.chunk

    def test_stop_ack_accepts_last_chunk_and_does_not_finalize_multipart_early(self):
        t,s,cid,tp,sp,rid,action=self.active();store=self.app.RECORDING_STORE
        self.assertEqual(self.chunk(rid,t)[0],200)
        self.assertEqual(action('stop',{'ack':True})[0],200)
        self.assertEqual(store.row(rid,self.uid('teacher'))['state'],'finalizing')
        self.assertEqual(action('heartbeat',{'id':rid})[0],403)
        self.assertEqual(self.chunk(rid,t,b'final',1)[0],200)
        self.assertEqual(self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':2},t)[1]['state'],'processing')
        self.assertEqual(store.row(rid,self.uid('teacher'))['interrupted'],0)
        self.assertEqual(self.chunk(rid,t,b'late',2)[0],409)

    def test_empty_cloud_never_counts_as_successful_capture(self):
        t,s,cid,tp,sp,rid,action=self.active()
        result=self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':1},t)
        self.assertEqual(result[1]['state'],'failed');self.assertEqual(self.app.RECORDING_STORE.row(rid,self.uid('teacher'))['interrupted'],1)

    def test_native_end_defers_until_encoder_has_flushed_and_still_preserves_private_class(self):
        t,s,cid,tp,sp,rid,action=self.active()
        token=self.request('/api/admin/teacher-app-launch',{'class_id':cid,'client_launch':True},t)[1]['token']
        self.assertEqual(self.chunk(rid,t)[0],200)
        for _ in range(2):
            status,out,_=self.request('/api/teacher-app/end',{'token':token},t);self.assertEqual(status,202);self.assertTrue(out['pending'])
        room=self.app.ROOMS[cid];self.assertEqual(sum(x['command']=='record-stop' for x in room['teacher_commands']),1)
        with self.app.db() as c:self.assertEqual(c.execute('SELECT live FROM classes WHERE id=?',(cid,)).fetchone()[0],1)
        self.assertEqual(action('stop',{'ack':True})[0],200);self.assertEqual(self.chunk(rid,t,b'final',1)[0],200)
        self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':1},t)
        self.assertEqual(self.request('/api/teacher-app/end',{'token':token},t)[1],{'ok':True})
        self.assertEqual(self.app.RECORDING_STORE.row(rid,self.uid('teacher'))['interrupted'],0)

    def test_finalizing_expiry_stays_bounded_and_no_more_capture_is_authorized(self):
        t,s,cid,tp,sp,rid,action=self.active();store=self.app.RECORDING_STORE
        action('stop',{'ack':True});store.activity[rid]=time.time()-121
        self.assertEqual(self.chunk(rid,t)[0],409)
        self.assertEqual(action('heartbeat',{'id':rid})[0],403)

    def test_normal_stop_during_inflight_part_keeps_final_bytes_and_waits_for_cloud_ack(self):
        from review_features import PART_BYTES
        t,s,cid,tp,sp,rid,action=self.active();store=self.app.RECORDING_STORE
        first=b'\x1aE\xdf\xa3'+b'x'*(PART_BYTES-4);self.assertEqual(self.chunk(rid,t,first)[0],200)
        entered,release=threading.Event(),threading.Event();calls=[]
        def upload(row,path,checkpoint,**kwargs):
            calls.append(kwargs['complete'])
            if not kwargs['complete']:entered.set();release.wait(3);return False
            self.assertEqual(path.read_bytes(),first+b'final');return True
        self.cloud.upload.side_effect=upload;store.launch()
        try:
            self.assertTrue(entered.wait(2));action('stop',{'ack':True})
            self.assertEqual(self.chunk(rid,t,b'final',1)[0],200)
            self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':2},t)
            self.assertNotEqual(store.row(rid,self.uid('teacher'))['state'],'ready');release.set()
            deadline=time.monotonic()+2
            while store.row(rid,self.uid('teacher'))['state']!='ready' and time.monotonic()<deadline:store.wake.set();time.sleep(.02)
            self.assertEqual(store.row(rid,self.uid('teacher'))['state'],'ready');self.assertEqual(calls,[False,True])
        finally:release.set();store.close();store.worker.join(3);store.processor.join(3)
