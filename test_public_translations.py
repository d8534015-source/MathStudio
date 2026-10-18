"""Synthetic HTTP regressions. No real provider, student data or credentials."""
from unittest import mock
import json
import public_translations as pt
from test_security_stability import BackendCase


class PublicTranslations(BackendCase):
    endpoint = '/api/admin/content-translations'

    def setUp(self):
        super().setUp()
        self.teacher = self.client('teacher')
        with self.app.db() as c:
            c.execute("UPDATE settings SET value='Public introduction.' WHERE key='intro'")

    def state(self):
        status, out, _ = self.request(self.endpoint, state=self.teacher)
        self.assertEqual(status, 200)
        return out

    def payload(self, action='save', key='settings:0:intro', text='公开介绍'):
        state = self.state()
        source = next(x for x in state['sources'] if x['key'] == key)
        row = next((x for x in state['translations'] if x['source_key'] == key and x['target'] == 'zh'), {})
        return dict(action=action, key=key, target='zh', source_hash=source['source_hash'], text=text, revision=row.get('revision', 0))

    def post(self, data):
        return self.request(self.endpoint, data, self.teacher)

    def test_disabled_defaults_and_opt_in_without_provider_is_honest(self):
        self.assertFalse(self.state()['config']['enabled'])
        with mock.patch.dict('os.environ', {'MATH_PUBLIC_TRANSLATION_PROVIDER': ''}):
            self.assertEqual(self.post(self.payload('generate'))[0], 503)
            self.assertEqual(self.post(dict(action='config', enabled=True, terms=[]))[0], 200)
            self.assertEqual(self.post(self.payload('generate'))[0], 503)
            self.assertEqual(self.state()['translations'], [])

    def test_edit_approve_separate_original_and_stale_source(self):
        draft = self.payload(text='<img src=x onerror=alert(1)>中文介绍')
        self.assertEqual(self.post(draft)[0], 200)
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'], {})
        self.assertEqual(self.post(self.payload('approve', text=draft['text']))[0], 200)
        visible = self.request('/api/content-translations?lang=zh')[1]['translations']
        self.assertEqual(visible[draft['key']]['text'], draft['text'])
        with self.app.db() as c:
            original = c.execute("SELECT value FROM settings WHERE key='intro'").fetchone()[0]
            self.assertEqual(pt.digest(original), draft['source_hash'])
            c.execute("UPDATE settings SET value='Author changed the introduction' WHERE key='intro'")
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'], {})
        self.assertEqual(self.post(draft)[0], 409)
        self.app.init()  # Additive migration preserves originals and drafts across restart.
        with self.app.db() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM public_translations').fetchone()[0], 1)

    def test_drafts_do_not_replace_approved_and_stale_tabs_cannot_overwrite(self):
        first = self.payload('approve')
        self.assertEqual(self.post(first)[0], 200)
        update = self.payload(text='新草稿')
        self.assertEqual(self.post(update)[0], 200)
        self.assertEqual(self.post(update)[0], 409)
        self.assertEqual(self.request('/api/content-translations?lang=zh')[1]['translations'][first['key']]['text'], first['text'])

    def test_authorization_csrf_and_private_source_isolation(self):
        private = self.lesson('individual', 'student')
        instant = self.lesson('instant')
        group = self.lesson('group')
        self.assertEqual(self.request(self.endpoint)[0], 401)
        student = self.client('student')
        self.assertEqual(self.request(self.endpoint, state=student)[0], 403)
        self.assertEqual(self.request(self.endpoint, self.payload(), student)[0], 403)
        self.assertEqual(self.request(self.endpoint, self.payload(), self.teacher, headers={'X-CSRF-Token': 'bad'})[0], 403)
        keys = {x['key'] for x in self.state()['sources']}
        self.assertIn(f'groups:{group}:description', keys)
        for cid in (private, instant):
            key = f'groups:{cid}:description'
            self.assertNotIn(key, keys)
            self.assertEqual(self.post(dict(action='generate', key=key, target='zh', source_hash='unknown'))[0], 404)
        for key in ['users:1:name', 'messages:1:text', 'settings:0:contact']:
            self.assertEqual(self.post(dict(action='generate', key=key, target='zh', source_hash='unknown'))[0], 404)

    def test_provider_mock_cache_math_and_failure(self):
        original = 'Learn $x^2+1$ with Alice Chen at https://example.org/math and `x = 2`.'
        with self.app.db() as c:
            c.execute("UPDATE settings SET value=? WHERE key='intro'", (original,))
        self.post(dict(action='config', enabled=True, terms=['Alice Chen']))
        def provider(text, target, legacy):
            self.assertNotIn('Alice Chen', text)
            self.assertNotIn('$x^2+1$', text)
            self.assertNotIn('example.org', text)
            return text.replace('Learn ', '学习 ').replace(' with ', ' 跟随 ')
        with mock.patch.object(pt, 'provider_name', return_value='synthetic'), mock.patch.object(pt, 'translate', side_effect=provider) as call:
            self.assertEqual(self.post(self.payload('generate'))[0], 200)
            self.assertTrue(self.post(self.payload('generate'))[1]['cached'])
            self.assertEqual(call.call_count, 1)
            row = self.state()['translations'][0]
            for value in ('$x^2+1$', 'Alice Chen', 'https://example.org/math', '`x = 2`'):
                self.assertIn(value, row['draft'])
            regenerate = self.payload('generate'); regenerate['regenerate'] = True
            call.side_effect = OSError('synthetic upstream failure')
            self.assertEqual(self.post(regenerate)[0], 503)
            self.assertEqual(self.state()['translations'][0]['draft'], row['draft'])
        self.assertEqual(self.post(self.payload('approve', text='Missing math'))[0], 409)

    def test_provider_response_after_source_edit_or_opt_out_is_rejected(self):
        self.post(dict(action='config', enabled=True, terms=[]))
        def provider(*args):
            with self.app.db() as c:
                c.execute("UPDATE settings SET value='Changed during request' WHERE key='intro'")
            return '翻译'
        with mock.patch.object(pt, 'provider_name', return_value='synthetic'), mock.patch.object(pt, 'translate', side_effect=provider):
            self.assertEqual(self.post(self.payload('generate'))[0], 409)
        self.assertEqual(self.state()['translations'], [])
        def opt_out(text, *args):
            with self.app.db() as c:
                c.execute('UPDATE public_translation_config SET enabled=0 WHERE id=1')
            return text
        with mock.patch.object(pt, 'provider_name', return_value='synthetic'), mock.patch.object(pt, 'translate', side_effect=opt_out):
            self.assertEqual(self.post(self.payload('generate'))[0], 503)
        self.assertEqual(self.state()['translations'], [])

    def test_course_description_additive_and_teacher_only(self):
        with self.app.db() as c:
            lid = c.execute('SELECT id FROM lesson_types LIMIT 1').fetchone()[0]
        body = {'id': lid, 'description': 'Public course explanation'}
        self.assertEqual(self.request('/api/admin/course-description', body, self.client('student'))[0], 403)
        self.assertEqual(self.request('/api/admin/course-description', body, self.teacher)[0], 200)
        self.assertEqual(next(x['original'] for x in self.state()['sources'] if x['key'] == f'courses:{lid}:description'), body['description'])
        self.assertEqual(self.request('/api/desktop-info')[1]['build'], 'v41.6.6-delivery-candidate1')

    def test_provider_config_rejects_non_https_credential_urls_and_redirects(self):
        for url in ['http://example.org/translate', 'https://user:password@example.org/translate', 'https://example.org/translate?key=secret']:
            with mock.patch.dict('os.environ', {'MATH_PUBLIC_TRANSLATION_PROVIDER': 'libretranslate', 'MATH_PUBLIC_TRANSLATION_URL': url}):
                self.assertEqual(pt.provider_name(), 'disabled')
        with mock.patch.dict('os.environ', {'MATH_PUBLIC_TRANSLATION_PROVIDER': 'libretranslate', 'MATH_PUBLIC_TRANSLATION_URL': 'https://example.org/translate'}):
            self.assertEqual(pt.provider_name(), 'libretranslate')
        protected, spans = pt.protect('Try \\(a+b\\) and https://example.org', [])
        with self.assertRaises(pt.TranslationError):
            pt.restore('Lost all placeholders', spans)
