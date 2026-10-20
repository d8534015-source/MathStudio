"""New recording review regressions, synthetic data and mocked cloud only."""
import time,json,threading
from unittest import mock
import test_classroom_recording as prior
from review_features import MAX_BYTES,MAX_SECONDS,GB,PART_BYTES


class UpgradeTests(prior.RecordingTests.__bases__[0]):
    policy=prior.RecordingTests.policy;active=prior.RecordingTests.active;chunk=prior.RecordingTests.chunk

    def test_new_limits_allow_large_record_and_enforce_hard_cap(self):
        t,s,cid,tp,sp,rid,action=self.active()
        self.assertEqual((MAX_BYTES,MAX_SECONDS),(5_000_000_000,10800))
        self.assertEqual(self.chunk(rid,t)[0],200)
        with self.app.db() as c:c.execute('UPDATE recordings SET bytes=? WHERE id=?',(MAX_BYTES,rid))
        self.assertEqual(self.chunk(rid,t,b'x',1)[0],507)
        self.assertEqual(self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':MAX_SECONDS+1},t)[0],400)

    def test_local_record_is_not_automatically_uploaded(self):
        t,s,cid,tp,sp=self.room();self.policy()
        from recording_authorization import version
        with self.app.RECORDING_STORE.features.db() as c:c.execute('INSERT INTO guardian_scopes VALUES (?,?,?,?,?,?,0)',(self.uid('student'),json.dumps({'storage':['local','cloud'],'sharing':False,'download':False,'retention_days':7}),version(),time.time()+3600,'synthetic-verified-reference',time.time()))
        request=lambda action,data:self.request('/api/room/recording-'+action,{'class_id':cid,'peer':tp,**data},t)
        rid=request('request',{'consent':True,'mode':'local'})[1]['id']
        self.request('/api/room/recording-consent',{'class_id':cid,'peer':sp,'id':rid,'accepted':True},s)
        self.assertEqual(request('start',{'mime':'video/webm'})[0],200)
        self.assertEqual(self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':10},t)[1]['state'],'local')
        self.cloud.upload.assert_not_called()
        self.assertEqual(self.request('/api/admin/recordings/import',{'id':rid},t)[0],403)

    def test_cloud_parts_upload_before_finalization_without_blocking_chunks(self):
        t,s,cid,tp,sp,rid,action=self.active();store=self.app.RECORDING_STORE
        self.chunk(rid,t,b'\x1aE\xdf\xa3'+b'x'*(PART_BYTES-4))
        entered,release=threading.Event(),threading.Event()
        def cloud(*args,**kwargs):entered.set();release.wait(3);return False
        self.cloud.upload.side_effect=cloud;store.launch()
        try:
            self.assertTrue(entered.wait(2))
            before=time.monotonic();self.assertEqual(self.chunk(rid,t,b'end',1)[0],200)
            self.assertLess(time.monotonic()-before,.5)
            self.assertFalse(self.cloud.upload.call_args.kwargs['complete'])
        finally:release.set();store.close();store.worker.join(3)

    def test_local_upload_integrity_checkpoints_and_resume(self):
        import hashlib
        t,s,cid,tp,sp=self.room();self.policy();scope={'storage':['local','cloud'],'sharing':False,'download':False,'retention_days':7}
        from recording_authorization import version
        features=self.app.RECORDING_STORE.features
        with features.db() as c:c.execute('INSERT INTO guardian_scopes VALUES (?,?,?,?,?,?,0)',(self.uid('student'),json.dumps(scope),version(),time.time()+3600,'synthetic-evidence',time.time()))
        base={'class_id':cid,'peer':tp};out=self.request('/api/room/recording-request',{**base,'consent':True,'mode':'local','future_upload':True},t);rid=out[1]['id']
        self.request('/api/room/recording-consent',{'class_id':cid,'peer':sp,'id':rid,'accepted':True},s);self.request('/api/room/recording-start',{**base,'mime':'video/webm'},t)
        data=b'\x1aE\xdf\xa3synthetic-local'
        self.assertEqual(self.request('/api/admin/recordings/local-checkpoint',{'id':rid,'sequence':0,'size':len(data),'digest':hashlib.sha256(data).hexdigest()},t)[0],200)
        self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':15},t)
        self.assertEqual(self.request('/api/admin/recordings/import',{'id':rid},t)[0],200)
        self.assertEqual(self.chunk(rid,t,b'\x1aE\xdf\xa3wrong-file')[0],403)
        self.assertEqual(self.chunk(rid,t,data)[0],200)
        self.assertEqual(self.request('/api/admin/recordings/import',{'id':rid},t)[1]['sequence'],1)
        self.assertEqual(self.request('/api/admin/recordings/finish',{'id':rid,'complete':True,'duration':15},t)[0],200)

    def test_backup_restore_is_explicit_new_directory_and_revokes_access(self):
        import tempfile,sqlite3
        from pathlib import Path
        from review_backup import copy_verified
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'review';source.mkdir();db=source/'posts.db'
            with sqlite3.connect(db) as c:c.execute('CREATE TABLE desktop_credentials(selector TEXT)');c.execute("INSERT INTO desktop_credentials VALUES ('synthetic')")
            result=copy_verified(source,root/'backup',port=0);self.assertEqual(result['integrity'],'passed')
            copy_verified(root/'backup',root/'restored',port=0,restore=True)
            with sqlite3.connect(root/'restored'/'posts.db') as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM desktop_credentials').fetchone()[0],0)
            with sqlite3.connect(db) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM desktop_credentials').fetchone()[0],1)
