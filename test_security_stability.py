"""Phase 2A regressions: synthetic accounts, temporary data, loopback only."""
import http.client
import concurrent.futures
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import sys
import threading
import time
import unittest
from unittest import mock


class SecurityStability(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {'MATH_DATA': self.temp.name,
                                               'PUBLIC_ORIGIN': '',
                                               'CLOUDFLARE_TURN_KEY_ID': '',
                                               'CLOUDFLARE_TURN_API_TOKEN': '',
                                               'MATH_TRUSTED_PROXIES': ''})
        self.env.start()
        spec = importlib.util.spec_from_file_location('isolated_mathstudio', Path(__file__).with_name('server.py'))
        self.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.app)
        self.app.init()
        if not hasattr(type(self), 'password_hash'):
            type(self).password_hash = self.app.hash_password('synthetic-password-123')
        with self.app.db() as c:
            for name, role in [('teacher', 'admin'), ('teacher2', 'admin'),
                               ('student', 'student'), ('other', 'student')]:
                c.execute('INSERT INTO users(username,name,password,role) VALUES (?,?,?,?)',
                          (name, name, self.password_hash, role))
        self.http = self.app.ThreadingHTTPServer(('127.0.0.1', 0), self.app.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever,
                                       kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        self.env.stop()
        self.temp.cleanup()

    def request(self, path, data=None, state=None, headers=None, raw=None):
        h = {'Cookie': state.get('cookie', '') if state else ''}
        body = raw
        if data is not None:
            body = json.dumps(data)
            h.update({'Content-Type': 'application/json',
                      'X-CSRF-Token': state.get('csrf', '') if state else ''})
        h.update(headers or {})
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=5)
        try:
            conn.request('POST' if body is not None else 'GET', path, body, h)
            r = conn.getresponse()
            raw = r.read()
            response_headers = dict(r.getheaders())
            out = json.loads(raw) if r.getheader('Content-Type', '').startswith('application/json') else raw
            if state is not None:
                if r.getheader('Set-Cookie'):
                    state['cookie'] = r.getheader('Set-Cookie').split(';')[0]
                if isinstance(out, dict) and 'csrf' in out:
                    state['csrf'] = out['csrf']
            return r.status, out, response_headers
        finally:
            conn.close()

    def client(self, username=None):
        state = {}
        self.assertEqual(self.request('/api/me', state=state)[0], 200)
        if username:
            self.assertEqual(self.request('/api/login', {
                'username': username, 'password': 'synthetic-password-123'}, state)[0], 200)
        return state

    def uid(self, username):
        with self.app.db() as c:
            return c.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()[0]

    def lesson(self, kind='individual', user=None, status='scheduled'):
        with self.app.db() as c:
            r = c.execute('''INSERT INTO classes(title,track,description,start,minutes,capacity,
                status,live,approval,class_kind,requested_by) VALUES (?,?,?,?,60,5,?,1,'confirmed',?,?)''',
                ('Synthetic private title', 'Math', 'Synthetic private details', time.time()+600,
                 status, kind, self.uid(user) if user else None))
            cid = r.lastrowid
            if user:
                c.execute('INSERT INTO bookings(user_id,class_id,created) VALUES (?,?,?)',
                          (self.uid(user), cid, time.time()))
            return cid

    def instant(self, teacher):
        status, out, _ = self.request('/api/admin/instant-meeting', {'title': 'Synthetic instant'}, teacher)
        self.assertEqual(status, 200)
        return out

    def room(self):
        teacher, student = self.client('teacher'), self.client('student')
        meeting = self.instant(teacher)
        cid = meeting['class_id']
        self.assertEqual(self.request('/api/instant/join', {'code': meeting['code']}, student)[0], 200)
        tp = self.request('/api/room/join', {'class_id': cid}, teacher)[1]['peer']
        sp = self.request('/api/room/join', {'class_id': cid}, student)[1]['peer']
        return teacher, student, cid, tp, sp

    def native_tokens(self):
        teacher = self.client('teacher')
        meeting = self.instant(teacher)
        cid = meeting['class_id']
        launched = self.request('/api/admin/teacher-app-launch', {'class_id': cid}, teacher)
        self.assertEqual(launched[0], 200)
        app_token = launched[1]['token']
        media_token = self.request('/api/teacher-app/media-login-token', {'token': app_token}, teacher)[1]['media_token']
        peer = self.request('/api/room/join', {'class_id': cid}, teacher)[1]['peer']
        overlay = self.request('/api/room/overlay-token', {'class_id': cid, 'peer': peer}, teacher)[1]['token']
        return teacher, cid, app_token, media_token, overlay

    def assert_native_tokens_revoked(self, app_token, media_token, overlay):
        self.assertEqual(self.request('/api/teacher-app/state?token='+app_token)[0], 403)
        self.assertEqual(self.request('/api/teacher-app/permissions', {'token': app_token, 'drawing': True})[0], 403)
        self.assertEqual(self.request('/api/overlay/state?token='+overlay)[0], 403)
        self.assertEqual(self.request('/teacher-media-login?token='+media_token)[0], 403)

    def test_sec01_anonymous_only_sees_public_group_catalog(self):
        private = self.lesson(user='student')
        group = self.lesson(kind='group')
        old_group = self.lesson(kind='group', status='completed')
        teacher = self.client('teacher')
        meeting = self.instant(teacher)
        status, out, _ = self.request('/api/classes')
        self.assertEqual(status, 200)
        self.assertEqual({c['id'] for c in out['classes']}, {group})
        for row in out['classes']:
            self.assertNotIn('requested_by', row)
            self.assertNotIn('series_id', row)
            self.assertNotIn('group_chat_id', row)

    def test_sec01_student_own_history_and_admin_visibility(self):
        own = self.lesson(user='student', status='completed')
        other = self.lesson(user='other')
        student = self.client('student')
        rows = self.request('/api/classes', state=student)[1]['classes']
        self.assertEqual({x['id'] for x in rows}, {own})
        self.assertTrue(rows[0]['mine'])
        teacher = self.client('teacher')
        self.assertEqual({x['id'] for x in self.request('/api/classes', state=teacher)[1]['classes']}, {own, other})

    def test_sec01_guest_sees_only_admitted_instant_meeting(self):
        teacher = self.client('teacher')
        first, second = self.instant(teacher), self.instant(teacher)
        guest = self.client()
        self.assertEqual(self.request('/api/instant/join', {'code': first['code'], 'name': 'Synthetic guest'}, guest)[0], 200)
        rows = self.request('/api/classes', state=guest)[1]['classes']
        self.assertEqual({x['id'] for x in rows}, {first['class_id']})
        self.assertEqual(self.request('/api/room/join', {'class_id': first['class_id']}, guest)[0], 200)
        self.assertEqual(self.request('/api/room/join', {'class_id': second['class_id']}, guest)[0], 403)

    def test_sec02_generic_signaling_rejects_host_controls(self):
        teacher, student, cid, tp, sp = self.room()
        for state, source, target in [(student, sp, tp), (teacher, tp, sp)]:
            for signal in [{'control': 'host-mute', 'muted': True},
                           {'control': 'host-mute', 'muted': False,
                            'description': {'type': 'offer', 'sdp': 'synthetic'}}]:
                status = self.request('/api/room/signal', {
                    'class_id': cid, 'peer': source, 'to': target, 'signal': signal}, state)[0]
                self.assertEqual(status, 400)
        self.assertEqual(self.request(f'/api/room/poll?class={cid}&peer={tp}', state=teacher)[1]['events'], [])

    def test_sec02_valid_media_signals_and_authorized_mute_preserved(self):
        teacher, student, cid, tp, sp = self.room()
        for signal in [{'description': {'type': 'offer', 'sdp': 'synthetic'}},
                       {'description': {'type': 'answer', 'sdp': 'synthetic'}},
                       {'candidate': {'candidate': 'synthetic', 'sdpMid': '0',
                                      'sdpMLineIndex': 0, 'usernameFragment': 'test'}},
                       {'control': 'renegotiate', 'iceRestart': True},
                       {'control': 'camera-retry'}]:
            self.assertEqual(self.request('/api/room/signal', {
                'class_id': cid, 'peer': sp, 'to': tp, 'signal': signal}, student)[0], 200)
        self.assertEqual(self.request('/api/room/mute', {
            'class_id': cid, 'peer': sp, 'target': tp, 'muted': True}, student)[0], 403)
        self.assertEqual(self.request('/api/room/mute', {
            'class_id': cid, 'peer': tp, 'target': sp, 'muted': True}, teacher)[0], 200)
        polled = self.request(f'/api/room/poll?class={cid}&peer={sp}', state=student)[1]
        self.assertTrue(polled['forcedMute'])
        self.assertEqual(polled['events'][0]['signal']['control'], 'host-mute')

    def test_sec03_logout_revokes_native_overlay_and_pending_handoff(self):
        teacher, cid, app_token, media_token, overlay = self.native_tokens()
        self.assertEqual(self.request('/api/logout', {}, teacher)[0], 200)
        self.assert_native_tokens_revoked(app_token, media_token, overlay)

    def test_sec03_demotion_revokes_native_overlay_and_pending_handoff(self):
        teacher, cid, app_token, media_token, overlay = self.native_tokens()
        other_teacher = self.client('teacher2')
        self.assertEqual(self.request('/api/admin/role', {'user_id': self.uid('teacher'), 'role': 'student'}, other_teacher)[0], 200)
        self.assert_native_tokens_revoked(app_token, media_token, overlay)

    def test_sec03_password_change_invalidates_native_tokens(self):
        teacher, cid, app_token, media_token, overlay = self.native_tokens()
        with self.app.db() as c:
            c.execute('UPDATE users SET password=? WHERE username=?',
                      (self.app.hash_password('changed-synthetic-password'), 'teacher'))
        self.assert_native_tokens_revoked(app_token, media_token, overlay)

    def test_sec03_handoff_remains_one_use_and_tokens_have_absolute_expiry(self):
        teacher, cid, app_token, media_token, overlay = self.native_tokens()
        expiry = self.app.TEACHER_APP_TOKENS[app_token]['expires']
        self.assertEqual(self.request('/api/teacher-app/state?token='+app_token)[0], 200)
        self.assertEqual(self.app.TEACHER_APP_TOKENS[app_token]['expires'], expiry)
        browser = {}
        self.assertEqual(self.request('/teacher-media-login?token='+media_token, state=browser)[0], 302)
        self.assertEqual(self.request('/api/me', state=browser)[1]['user']['role'], 'admin')
        self.assertEqual(self.request('/teacher-media-login?token='+media_token)[0], 403)
        self.assertEqual(self.request('/api/teacher-app/state?token='+app_token)[0], 200)

    def test_sec03_overlay_rechecks_student_membership(self):
        cid = self.lesson(user='student')
        student = self.client('student')
        peer = self.request('/api/room/join', {'class_id': cid}, student)[1]['peer']
        token = self.request('/api/room/overlay-token', {'class_id': cid, 'peer': peer}, student)[1]['token']
        self.assertEqual(self.request('/api/overlay/state?token='+token)[0], 200)
        with self.app.db() as c:
            c.execute('DELETE FROM bookings WHERE class_id=?', (cid,))
        self.assertEqual(self.request('/api/overlay/state?token='+token)[0], 403)

    def test_sec03_same_browser_handoff_preserves_native_authorization(self):
        teacher, cid, app_token, media_token, overlay = self.native_tokens()
        self.assertEqual(self.request('/teacher-media-login?token='+media_token, state=teacher)[0], 302)
        self.assertEqual(self.request('/api/teacher-app/state?token='+app_token)[0], 200)
        self.assertEqual(self.request('/api/overlay/state?token='+overlay)[0], 200)
        # The redirected classroom boot fetches the rotated CSRF token.
        self.request('/api/me', state=teacher)
        self.assertEqual(self.request('/api/logout', {}, teacher)[0], 200)
        self.assertEqual(self.request('/api/teacher-app/state?token='+app_token)[0], 403)

    def test_sec03_expired_issuer_and_absolute_token_expiry_are_enforced(self):
        teacher, cid, app_token, media_token, overlay = self.native_tokens()
        self.app.TEACHER_APP_TOKENS[app_token]['expires'] = time.time()-1
        self.assertEqual(self.request('/api/teacher-app/state?token='+app_token)[0], 403)
        sid = teacher['cookie'].split('=', 1)[1]
        self.app.SESSIONS[sid]['expires'] = time.time()-1
        self.assertEqual(self.request('/api/overlay/state?token='+overlay)[0], 403)

    def wrong_login(self, state, username='teacher', headers=None):
        return self.request('/api/login', {'username': username, 'password': 'wrong'}, state, headers)[0]

    def test_sec04_other_account_success_does_not_reset_target_limit(self):
        state = self.client()
        for _ in range(10):
            self.assertEqual(self.wrong_login(state), 401)
            self.assertEqual(self.request('/api/login', {
                'username': 'student', 'password': 'synthetic-password-123'}, state)[0], 200)
        self.assertEqual(self.wrong_login(state), 429)

    def test_sec04_one_account_failure_does_not_lock_out_other_accounts(self):
        state = self.client()
        for _ in range(10):
            self.assertEqual(self.wrong_login(state), 401)
        other = self.client('teacher2')
        self.assertEqual(self.request('/api/me', state=other)[1]['user']['role'], 'admin')

    def test_sec04_forwarding_requires_explicit_trusted_proxy(self):
        state = self.client()
        for i in range(60):
            self.assertEqual(self.wrong_login(state, 'unknown_'+str(i),
                {'CF-Connecting-IP': '198.51.100.'+str(i+1)}), 401)
        self.assertEqual(self.wrong_login(state, 'another_unknown',
            {'CF-Connecting-IP': '203.0.113.2'}), 429)

    def test_sec04_trusted_proxy_keeps_client_buckets_separate(self):
        state = self.client()
        with mock.patch.dict(os.environ, {'MATH_TRUSTED_PROXIES': '127.0.0.1/32'}):
            for i in range(60):
                self.assertEqual(self.wrong_login(state, 'unknown_'+str(i),
                    {'CF-Connecting-IP': '198.51.100.1'}), 401)
            self.assertEqual(self.wrong_login(state, 'another_unknown',
                {'CF-Connecting-IP': '198.51.100.1'}), 429)
            self.assertEqual(self.request('/api/login', {
                'username': 'teacher', 'password': 'synthetic-password-123'}, state,
                {'CF-Connecting-IP': '198.51.100.2'})[0], 200)

    def test_sec04_signup_and_meeting_guesses_are_bounded(self):
        state = self.client()
        for i in range(10):
            # Invalid password keeps this test cheap while exercising signup admission.
            self.assertEqual(self.request('/api/signup', {
                'username': 'new_'+str(i), 'name': 'Synthetic', 'password': 'short'}, state)[0], 400)
        self.assertEqual(self.request('/api/signup', {
            'username': 'new_extra', 'name': 'Synthetic', 'password': 'short'}, state)[0], 429)
        for _ in range(30):
            self.assertEqual(self.request('/api/instant/info?code=0000000000')[0], 404)
        self.assertEqual(self.request('/api/instant/info?code=0000000000')[0], 429)

    def test_ses01_static_health_and_errors_do_not_create_sessions(self):
        for _ in range(12):
            for path, status in [('/', 200), ('/favicon.svg', 200),
                                 ('/api/desktop-info', 200), ('/api/classes', 200),
                                 ('/missing', 404)]:
                response = self.request(path)
                self.assertEqual(response[0], status)
                self.assertNotIn('Set-Cookie', response[2])
        self.assertEqual(len(self.app.SESSIONS), 0)

    def test_ses01_native_token_requests_reuse_issuing_authorization(self):
        teacher, cid, app_token, media_token, overlay = self.native_tokens()
        before = len(self.app.SESSIONS)
        for _ in range(12):
            self.assertEqual(self.request('/api/teacher-app/state?token='+app_token)[0], 200)
            self.assertEqual(self.request('/api/overlay/state?token='+overlay)[0], 200)
        self.assertEqual(self.request('/api/teacher-app/screen', {'token': app_token, 'active': True})[0], 200)
        for _ in range(3):
            self.assertEqual(self.request('/api/teacher-app/screen-frame',
                headers={'Content-Type': 'image/jpeg', 'X-Teacher-Token': app_token},
                raw=b'\xff\xd8synthetic-frame')[0], 200)
        self.assertEqual(len(self.app.SESSIONS), before)

    def test_sec03_guest_overlay_retains_authorized_drawing(self):
        teacher = self.client('teacher')
        meeting = self.instant(teacher)
        cid = meeting['class_id']
        guest = self.client()
        self.assertEqual(self.request('/api/instant/join', {
            'code': meeting['code'], 'name': 'Synthetic guest'}, guest)[0], 200)
        tp = self.request('/api/room/join', {'class_id': cid}, teacher)[1]['peer']
        gp = self.request('/api/room/join', {'class_id': cid}, guest)[1]['peer']
        token = self.request('/api/room/overlay-token', {'class_id': cid, 'peer': gp}, guest)[1]['token']
        self.assertEqual(self.request('/api/room/permissions', {
            'class_id': cid, 'peer': tp, 'drawing': True}, teacher)[0], 200)
        self.assertEqual(self.request('/api/overlay/board', {
            'token': token, 'version': 0, 'board': {'background': 'grid', 'shapes': []}})[0], 200)

    def test_ses01_cookie_reuse_rotation_and_session_pressure(self):
        teacher = self.client('teacher')
        for _ in range(5):
            self.assertEqual(self.request('/api/me', state=teacher)[0], 200)
        self.assertEqual(len(self.app.SESSIONS), 1)
        self.app.SESSION_LIMIT = 3
        self.app.ANON_SESSION_LIMIT = 2
        self.client(); self.client()
        self.assertEqual(self.request('/api/me')[0], 429)
        self.assertEqual(self.request('/favicon.svg')[0], 200)
        self.assertEqual(self.request('/api/me', state=teacher)[1]['user']['role'], 'admin')
        self.assertEqual(self.request('/api/logout', {}, teacher)[0], 200)
        self.assertEqual(len(self.app.SESSIONS), 3)

    def test_ses01_expiry_recovers_and_anonymous_issuance_is_throttled(self):
        state = self.client()
        old_cookie = state['cookie']
        self.app.SESSIONS[old_cookie.split('=', 1)[1]]['expires'] = time.time()-1
        self.assertEqual(self.request('/api/me', state=state)[0], 200)
        self.assertNotEqual(state['cookie'], old_cookie)
        self.assertEqual(len(self.app.SESSIONS), 1)
        for _ in range(28):
            self.assertEqual(self.request('/api/me')[0], 200)
        self.assertEqual(self.request('/api/me')[0], 429)
        self.assertEqual(self.request('/api/me', state=state)[0], 200)

    def test_ses01_idle_anonymous_eviction_preserves_active_users(self):
        teacher = self.client('teacher')
        anon = self.client()
        self.app.ANON_SESSION_LIMIT = 1
        self.app.SESSIONS[anon['cookie'].split('=', 1)[1]]['last_seen'] = time.time()-61
        self.assertEqual(self.request('/api/me')[0], 200)
        self.assertEqual(len(self.app.SESSIONS), 2)
        self.assertEqual(self.request('/api/me', state=teacher)[1]['user']['role'], 'admin')

    def test_rel01_duplicate_start_does_not_close_live_class(self):
        cid = self.lesson(user='student')
        with mock.patch.object(sys, 'argv', ['server.py']), \
             mock.patch.object(self.app, 'PORT', self.http.server_port), \
             mock.patch.object(self.app, 'BIND', '127.0.0.1'):
            with self.assertRaises(SystemExit):
                self.app.main()
        with self.app.db() as c:
            self.assertEqual(c.execute('SELECT live FROM classes WHERE id=?', (cid,)).fetchone()[0], 1)

    def test_rel01_successful_start_still_resets_crash_leftovers(self):
        cid = self.lesson(user='student')
        fake_http = mock.Mock()
        fake_http.serve_forever.side_effect = KeyboardInterrupt
        with mock.patch.object(sys, 'argv', ['server.py']), \
             mock.patch.object(self.app, 'ThreadingHTTPServer', return_value=fake_http), \
             mock.patch.object(self.app.socket, 'socket', side_effect=OSError('offline test')), \
             mock.patch('sys.stdout', new_callable=io.StringIO):
            self.app.main()
        with self.app.db() as c:
            self.assertEqual(c.execute('SELECT live FROM classes WHERE id=?', (cid,)).fetchone()[0], 0)
        fake_http.server_close.assert_called_once()

    def test_perf01_negative_cache_cooldown_and_provider_recovery(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'iceServers': [{'urls': ['turn:synthetic.invalid:3478'],
                            'username': 'synthetic', 'credential': 'synthetic'}]}).encode()
        with mock.patch.dict(os.environ, {'CLOUDFLARE_TURN_KEY_ID': 'synthetic',
                                          'CLOUDFLARE_TURN_API_TOKEN': 'synthetic'}), \
             mock.patch.object(self.app.time, 'time', return_value=1000) as clock, \
             mock.patch.object(self.app.urllib.request, 'urlopen',
                               side_effect=[OSError('synthetic outage'), response]) as provider:
            first = self.app._cloudflare_turn_ice_servers()
            self.assertIsNone(first[0])
            self.assertEqual(self.app._cloudflare_turn_ice_servers(), first)
            self.assertEqual(provider.call_count, 1)
            clock.return_value = 1061
            recovered = self.app._cloudflare_turn_ice_servers()
            self.assertEqual(recovered[0][0]['username'], 'synthetic')
            self.assertEqual(self.app._cloudflare_turn_ice_servers(), recovered)
            self.assertEqual(provider.call_count, 2)

    def slow_join(self, end_during_lookup=False, logout_during_lookup=False):
        teacher = self.client('teacher')
        cid = self.instant(teacher)['class_id']
        entered, release = threading.Event(), threading.Event()
        def provider(uid):
            entered.set()
            if not release.wait(3):
                raise RuntimeError('test did not release provider')
            return [{'urls': 'stun:synthetic.invalid'}], False, '', ''
        with mock.patch.object(self.app, 'build_ice_servers', side_effect=provider), \
             concurrent.futures.ThreadPoolExecutor(2) as pool:
            joined = pool.submit(self.request, '/api/room/join', {'class_id': cid}, teacher)
            self.assertTrue(entered.wait(2))
            responsive = False
            try:
                health = pool.submit(self.request, '/api/desktop-info')
                responsive = health.result(timeout=.75)[0] == 200
                if end_during_lookup:
                    ended = pool.submit(self.request, '/api/admin/class-action',
                                        {'class_id': cid, 'action': 'end'}, teacher)
                    self.assertEqual(ended.result(timeout=.75)[0], 200)
                if logout_during_lookup:
                    logged_out = pool.submit(self.request, '/api/logout', {}, teacher)
                    self.assertEqual(logged_out.result(timeout=.75)[0], 200)
            except concurrent.futures.TimeoutError:
                pass
            finally:
                release.set()
            result = joined.result(timeout=3)
        self.assertTrue(responsive, 'TURN lookup blocked unrelated HTTP requests')
        return cid, result

    def test_perf01_turn_lookup_does_not_hold_global_lock(self):
        cid, result = self.slow_join()
        self.assertEqual(result[0], 200)
        self.assertIn('peer', result[1])

    def test_perf01_join_rechecks_class_after_turn_lookup(self):
        cid, result = self.slow_join(end_during_lookup=True)
        self.assertEqual(result[0], 409)
        self.assertFalse(self.app.ROOMS.get(cid, {}).get('peers'))

    def test_perf01_join_rechecks_logout_after_turn_lookup(self):
        cid, result = self.slow_join(logout_during_lookup=True)
        self.assertEqual(result[0], 401)
        self.assertFalse(self.app.ROOMS.get(cid, {}).get('peers'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
