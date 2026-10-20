"""Account policies and separate student persistent credentials, synthetic only."""
import json,time
from unittest import mock
from test_security_stability import BackendCase
import policy_service
import recording_authorization as auth

class StudentPolicies(BackendCase):
    def acknowledgement(self):return dict(policy_version=policy_service.metadata()['version'],accept_terms=True,ack_privacy=True,ack_cookies=True)
    def test_signup_requires_current_acknowledgments_and_never_grants_recording(self):
        state=self.client();data={'username':'synthetic_new','password':'synthetic-password-123','name':'Synthetic'}
        self.assertEqual(self.request('/api/signup',data,state)[0],400)
        self.assertEqual(self.request('/api/signup',{**data,**self.acknowledgement()},state)[0],200)
        features=self.app.RECORDING_STORE.features
        self.assertFalse(policy_service.due(features,self.uid('synthetic_new')))
        with features.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM standing_scopes').fetchone()[0],0)
        with mock.patch('policy_service.metadata',return_value={**policy_service.metadata(),'version':'changed-review-version'}):
            self.assertTrue(policy_service.due(features,self.uid('synthetic_new')))
            self.assertEqual(self.request('/api/me',state=state)[1]['policies_due'],True)
    def remembered(self):
        state=self.client();status,out,headers=self.request('/api/login',{'username':'student','password':'synthetic-password-123','remember_me':True},state)
        self.assertEqual(status,200,out);cookie=headers['Set-Cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie);self.assertIn('SameSite=Strict',cookie)
        return state,cookie.split(';')[0]
    def test_rotation_replay_revoke_family_and_no_token_in_json(self):
        old,persistent=self.remembered();restored={'cookie':persistent}
        status,out,headers=self.request('/api/me',state=restored);self.assertEqual(status,200);self.assertEqual(out['user']['role'],'student')
        self.assertNotEqual(headers['Set-Cookie'].split(';')[0],persistent);self.assertNotIn('verifier',json.dumps(out))
        replay={'cookie':persistent};self.assertIsNone(self.request('/api/me',state=replay)[1]['user'])
        self.assertIsNone(self.request('/api/me',state=restored)[1]['user'])
    def test_logout_password_role_and_expiry_revoke_remembered_sessions(self):
        state,persistent=self.remembered();self.request('/api/logout',{},state)
        self.assertIsNone(self.request('/api/me',state={'cookie':persistent})[1]['user'])
        state,persistent=self.remembered()
        with self.app.db() as c:c.execute("UPDATE users SET password='different-stamp' WHERE username='student'")
        self.assertIsNone(self.request('/api/me',state=state)[1]['user'])
        self.assertIsNone(self.request('/api/me',state={'cookie':persistent})[1]['user'])
    def test_unchecked_login_does_not_create_persistent_credential(self):
        state=self.client();self.assertEqual(self.request('/api/login',{'username':'student','password':'synthetic-password-123','remember_me':False},state)[0],200)
        with self.app.RECORDING_STORE.features.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM student_credentials').fetchone()[0],0)
    def test_guardian_and_student_scope_are_independent_and_withdrawable(self):
        state=self.client('student');self.request('/api/policies/ack',self.acknowledgement(),state);features=self.app.RECORDING_STORE.features
        scope={'storage':['cloud'],'sharing':False,'download':False,'retention_days':7};data={'accepted':True,'version':auth.version(),'expires':time.time()+3600,'scope':scope}
        self.assertEqual(self.request('/api/account/recording-authorization',data,state)[0],403)
        with features.db() as c:c.execute('INSERT INTO guardian_scopes VALUES (?,?,?,?,?,?,0)',(self.uid('student'),json.dumps(scope),auth.version(),time.time()+3600,'synthetic-verified-evidence',time.time()))
        self.assertEqual(self.request('/api/account/recording-authorization',data,state)[0],200)
        self.assertTrue(auth.standing(features,{'role':'student','uid':self.uid('student')},scope))
        self.assertFalse(auth.standing(features,{'role':'student','uid':self.uid('student')},{**scope,'sharing':True}))
        self.assertEqual(self.request('/api/account/recording-authorization',{'action':'withdraw'},state)[0],200)
        self.assertFalse(auth.standing(features,{'role':'student','uid':self.uid('student')},scope))
        with mock.patch('recording_authorization.version',return_value='changed-material-scope'):self.assertFalse(auth.guardian(features,self.uid('student'),scope))
    def test_bilingual_policy_pages_and_safe_paths(self):
        for kind in ('privacy','terms','cookies'):
            for lang in ('en','zh'):
                status,data,_=self.request('/policies/'+kind+'?lang='+lang);self.assertEqual(status,200);self.assertIn('DRAFT' if lang=='en' else '草案',data.decode())
        with self.assertRaises(ValueError):policy_service.document('../server','en')
    def test_valid_standing_scope_skips_repeated_prompt_and_withdrawal_stops_capture(self):
        import test_classroom_recording as fixtures
        t,s,cid,tp,sp=self.room();fixtures.RecordingTests.policy(self)
        self.request('/api/policies/ack',self.acknowledgement(),s)
        features=self.app.RECORDING_STORE.features;scope={'storage':['cloud'],'sharing':False,'download':False,'retention_days':7}
        with features.db() as c:c.execute('INSERT INTO guardian_scopes VALUES (?,?,?,?,?,?,0)',(self.uid('student'),json.dumps(scope),auth.version(),time.time()+3600,'synthetic-evidence',time.time()))
        self.assertEqual(self.request('/api/account/recording-authorization',{'accepted':True,'scope':scope,'version':auth.version(),'expires':time.time()+3600},s)[0],200)
        data={'class_id':cid,'peer':tp,'consent':True};out=self.request('/api/room/recording-request',data,t)
        self.assertEqual(out[1]['consent_count'],2)
        self.assertEqual(self.request('/api/room/recording-start',{**data,'mime':'video/webm'},t)[0],200)
        rid=out[1]['id'];self.request('/api/account/recording-authorization',{'action':'withdraw'},s)
        self.assertEqual(self.request('/api/room/recording-heartbeat',{**data,'id':rid},t)[0],403)
    def test_persistent_expiry_and_role_change_fail_closed(self):
        state,cookie=self.remembered()
        with self.app.RECORDING_STORE.features.db() as c:c.execute('UPDATE student_credentials SET idle=0')
        self.assertIsNone(self.request('/api/me',state=state)[1]['user'])
        state,cookie=self.remembered()
        with self.app.db() as c:c.execute("UPDATE users SET role='admin' WHERE username='student'")
        self.assertIsNone(self.request('/api/me',state=state)[1]['user'])
        self.assertIsNone(self.request('/api/me',state={'cookie':cookie})[1]['user'])
