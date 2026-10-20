"""Restricted resources sharing: real API, synthetic roster, mocked R2 bytes."""
import io,json,time
from test_security_stability import BackendCase
import test_classroom_recording as previous
from recording_authorization import version

class RecordingSharing(BackendCase):
    policy=previous.RecordingTests.policy
    def recording(self):
        import policy_service
        with self.app.RECORDING_STORE.features.db() as c:
            for name in ('student','other'):c.execute('INSERT INTO policy_acks VALUES (?,?,?)',(self.uid(name),policy_service.metadata()['version'],time.time()))
        t,s=self.client('teacher'),self.client('student');cid=self.lesson('group','student');self.policy()
        with self.app.db() as c:c.execute('INSERT INTO bookings(user_id,class_id,created) VALUES (?,?,?)',(self.uid('other'),cid,time.time()))
        scope={'storage':['cloud'],'sharing':True,'download':True,'retention_days':7}
        with self.app.RECORDING_STORE.features.db() as c:c.execute('INSERT INTO guardian_scopes VALUES (?,?,?,?,?,?,0)',(self.uid('student'),json.dumps(scope),version(),time.time()+3600,'synthetic-evidence',time.time()))
        tp=self.request('/api/room/join',{'class_id':cid},t)[1]['peer'];sp=self.request('/api/room/join',{'class_id':cid},s)[1]['peer']
        data={'class_id':cid,'peer':tp,'consent':True,'sharing':True,'download':True}
        response=self.request('/api/room/recording-request',data,t);self.assertEqual(response[0],200,response);rid=response[1]['id']
        self.assertEqual(self.request('/api/room/recording-consent',{'class_id':cid,'peer':sp,'id':rid,'accepted':True},s)[0],200)
        response=self.request('/api/room/recording-start',{'class_id':cid,'peer':tp,'mime':'video/webm'},t);self.assertEqual(response[0],200,response)
        with self.app.db() as c:c.execute("UPDATE recordings SET state='ready',bytes=100,duration=30 WHERE id=?",(rid,))
        with self.app.RECORDING_STORE.features.db() as c:c.execute("INSERT INTO recording_playback(id,state) VALUES (?,'ready')",(rid,))
        return t,s,cid,rid
    def share(self,t,rid,download=False):return self.request('/api/admin/recordings/share',{'id':rid,'viewers':[self.uid('other')],'download':download,'expires':time.time()+1200},t)
    def verify(self,t,rid):return self.request('/api/admin/recordings/verify-absence',{'id':rid,'user_id':self.uid('other'),'confirmed':True},t)
    def test_unknown_absence_requires_verification_and_never_auto_shares(self):
        t,s,cid,rid=self.recording();self.assertEqual(self.share(t,rid)[0],403)
        with self.app.RECORDING_STORE.features.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM recording_codes').fetchone()[0],0)
        self.assertEqual(self.verify(t,rid)[0],200)
        out=self.share(t,rid);self.assertEqual(out[0],200,out);self.assertEqual(len(out[1]['code']),20)
        self.assertEqual(self.request('/api/admin/recordings/verify-absence',{'id':rid,'user_id':self.uid('student'),'confirmed':True},t)[0],403)
        self.assertEqual(self.request('/api/resources/redeem',{'code':out[1]['code']},s)[0],403)
        absent=self.client('other');accepted=self.request('/api/resources/redeem',{'code':out[1]['code']},absent)
        self.assertEqual(accepted[0],200,accepted);self.assertFalse(accepted[1]['recording']['download'])
        self.assertNotIn('id',accepted[1]['recording'])
    def test_every_range_checks_account_permission_revocation_and_consent(self):
        t,s,cid,rid=self.recording();self.verify(t,rid);grant=self.share(t,rid)[1];absent=self.client('other')
        resource=self.request('/api/resources/redeem',{'code':grant['code']},absent)[1];url='/resource/recording?grant='+resource['grant']
        self.assertEqual(self.request(url,state=s,headers={'Range':'bytes=0-3'})[0],403)
        self.assertEqual(self.request(url+'&download=1',state=absent)[0],403)
        response=io.BytesIO(b'data');response.status=206;response.headers={'Content-Length':'4','Content-Range':'bytes 0-3/100'};self.cloud.open.return_value=response
        self.assertEqual(self.request(url,state=absent,headers={'Range':'bytes=0-3'})[0],206)
        self.assertEqual(self.cloud.open.call_args.args[0]['id'],rid+'_playback')
        self.assertEqual(self.request('/api/admin/recordings/revoke',{'id':rid,'grant_id':grant['grant_id']},t)[0],200)
        self.assertEqual(self.request(url,state=absent,headers={'Range':'bytes=4-7'})[0],403)
    def test_withdrawal_expiry_and_unenrollment_revoke_access(self):
        t,s,cid,rid=self.recording();self.verify(t,rid);grant=self.share(t,rid,True)[1];absent=self.client('other')
        with self.app.RECORDING_STORE.features.db() as c:c.execute('UPDATE recording_subjects SET revoked=1 WHERE recording_id=?',(rid,))
        self.assertEqual(self.request('/api/resources/redeem',{'code':grant['code']},absent)[0],403)
        with self.app.RECORDING_STORE.features.db() as c:
            c.execute('UPDATE recording_subjects SET revoked=0 WHERE recording_id=?',(rid,));c.execute('UPDATE recording_codes SET expires=0')
        self.assertEqual(self.request('/api/resources/redeem',{'code':grant['code']},absent)[0],403)
        with self.app.RECORDING_STORE.features.db() as c:c.execute('UPDATE recording_codes SET expires=?',(time.time()+1200,))
        with self.app.db() as c:c.execute('DELETE FROM bookings WHERE class_id=? AND user_id=?',(cid,self.uid('other')))
        self.assertEqual(self.request('/api/resources/redeem',{'code':grant['code']},absent)[0],403)
    def test_quick_meetings_and_other_teachers_cannot_manage_absentee_access(self):
        t,s,cid,rid=self.recording();other=self.client('teacher2')
        self.assertEqual(self.request('/api/admin/recordings/roster',{'id':rid},other)[0],404)
        with self.app.db() as c:c.execute("UPDATE classes SET class_kind='instant' WHERE id=?",(cid,))
        self.assertEqual(self.verify(t,rid)[0],403)
        self.assertEqual(self.share(t,rid)[0],403)
