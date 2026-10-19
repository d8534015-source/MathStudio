"""Optional Chromium acceptance checks against an isolated synthetic database.

Run with a test-only Playwright environment; see WEBSITE_INTEGRATION.md.
Does not use provider credentials, the production database or real media devices.
"""
import argparse
import json
from pathlib import Path
from unittest import mock
from test_security_stability import BackendCase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--chromium', default='/usr/bin/chromium')
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright
    args.output.mkdir(parents=True, exist_ok=True)
    results = []; errors = []
    case = BackendCase()
    with mock.patch.dict('os.environ', {'MATH_PUBLIC_TRANSLATION_PROVIDER': '', 'MATH_PUBLIC_TRANSLATION_API_KEY': ''}):
        case.setUp()
        try:
            with case.app.db() as c:
                c.execute("UPDATE settings SET value='MathStudio Synthetic' WHERE key='name'")
                c.execute("UPDATE settings SET value='Teacher' WHERE key='teacher'")
                c.execute("UPDATE settings SET value='Home' WHERE key='headline'")
                c.execute("UPDATE settings SET value='Public introduction: $x^2+1$.' WHERE key='intro'")
                c.execute("UPDATE settings SET value='Synthetic public teacher introduction.' WHERE key='about'")
            teacher = case.client('teacher')
            cid = case.lesson('group', 'student')
            gid = case.request('/api/admin/groups/create', {'name': 'Home', 'user_ids': [case.uid('student')]}, teacher)[1]['group_id']
            case.request('/api/group-messages/send', {'group_id': gid, 'text': 'Teacher Home Schedule $x^2$ https://example.org'}, teacher)
            upload = case.request('/api/admin/files/upload', state=teacher, raw=b'Synthetic public resource', headers={
                'Content-Type': 'application/octet-stream', 'X-CSRF-Token': teacher['csrf'], 'X-File-Name': 'Home.txt', 'X-File-Type': 'text/plain'})
            assert upload[0] == 200, upload
            code = case.request('/api/admin/files/code', {'file_ids': [upload[1]['file']['id']], 'label': 'Schedule'}, teacher)[1]['code']
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
                context = browser.new_context(viewport={'width': 1440, 'height': 1100})
                page = context.new_page(); page.set_default_timeout(7000)
                page.on('pageerror', lambda e: errors.append(str(e)))
                origin = f'http://127.0.0.1:{case.http.server_port}'

                def visit(route, lang='en'):
                    page.goto(origin+route)
                    page.evaluate('(lang)=>localStorage.setItem("mathstudio_lang",lang)', lang)
                    page.reload()
                    if route in ('/teacher','/teacher/translations'):
                        page.wait_for_function('()=>document.documentElement.lang===localStorage.getItem("mathstudio_lang").replace("zh","zh-CN")')
                    else:
                        page.wait_for_function('()=>window.__MATHSTUDIO_BOOTED__===true')
                    page.wait_for_timeout(120)

                def capture(name):
                    page.screenshot(path=str(args.output/(name+'.png')), full_page=True)

                def check(name, condition):
                    assert condition, name
                    results.append(name)

                def login(user):
                    page.goto(origin+'/login');page.wait_for_selector('#auth')
                    page.locator('#username').fill(user)
                    page.locator('#password').fill('synthetic-password-123')
                    page.locator('#auth button').click();page.wait_for_url('**/account')
                    page.wait_for_function('()=>window.__MATHSTUDIO_BOOTED__===true')

                for route in ['/', '/booking', '/login', '/signup', '/join', '/resources', '/teacher']:
                    for lang in ['en', 'zh']:
                        visit(route, lang)
                        capture((route.strip('/') or 'home')+'-'+lang)
                        check(route+' '+lang+' renders', page.locator('h1').count() > 0)
                        check(route+' '+lang+' document language', page.locator('html').get_attribute('lang') == ('zh-CN' if lang == 'zh' else 'en'))
                visit('/booking', 'en'); check('Booking initial English', page.get_by_text('Log in to book', exact=True).count() > 0)
                page.evaluate('window.__languageProbe="same-document"');page.locator('#langToggle').click()
                page.get_by_text('登录后预约', exact=True).first.wait_for()
                check('Observed booking descriptions translated', page.get_by_text('加入已安排的小组课', exact=True).count() == 1)
                page.wait_for_timeout(3300)
                check('Language survives dynamic polling', page.get_by_text('加入已安排的小组课', exact=True).count() == 1)
                page.locator('#langToggle').click();page.get_by_text('Log in to book', exact=True).first.wait_for()
                check('Switch does not reload document', page.evaluate('window.__languageProbe') == 'same-document')
                page.reload();page.wait_for_function('()=>window.__MATHSTUDIO_BOOTED__===true')
                check('Preference survives refresh', page.evaluate('localStorage.getItem("mathstudio_lang")') == 'en')
                visit('/login','en');page.locator('#username').fill('Teacher');page.locator('#langToggle').click()
                check('Live switch preserves typed name', page.locator('#username').input_value() == 'Teacher')
                check('Live switch updates form labels', page.get_by_text('用户名',exact=True).count() == 1)
                page.locator('#username').fill('missing_user');page.locator('#password').fill('wrong-password-123');page.locator('#auth button').click()
                page.locator('#auth .error:not(.hidden)').wait_for()
                check('Dynamic login error localized', '用户名或密码' in page.locator('#auth .error').inner_text())
                page.locator('#langToggle').click()
                check('Displayed error round trips', 'Incorrect username or password' in page.locator('#auth .error').inner_text())
                login('student')
                for route in ['/account', f'/messages?group={gid}', f'/classroom?id={cid}']:
                    for lang in ['en','zh']:
                        visit(route,lang);capture(('classroom' if route.startswith('/classroom') else route.split('?')[0].strip('/'))+'-'+lang)
                        check(route+' '+lang+' authenticated rendering', page.evaluate('window.__MATHSTUDIO_BOOTED__===true'))
                visit(f'/messages?group={gid}','zh')
                page.locator('.chat-text').first.wait_for()
                check('Message remains original', page.locator('.chat-text').first.inner_text() == 'Teacher Home Schedule $x^2$ https://example.org')
                page.locator('#persistentMessageInput').fill('Home Teacher')
                page.locator('#langToggle').click()
                check('Message draft preserved', page.locator('#persistentMessageInput').input_value() == 'Home Teacher')
                visit('/resources','en');page.locator('#resource_code').fill(code);page.locator('#resourceCodeForm button').click()
                page.get_by_text('Home.txt',exact=True).wait_for();link=page.locator('a[href^="/resource/download?"]').first.get_attribute('href')
                page.locator('#langToggle').click();page.wait_for_timeout(3300)
                check('Resource state and download survive polling and switch', page.locator('a[href^="/resource/download?"]').first.get_attribute('href') == link)
                check('Resource label remains original', page.get_by_text('Schedule',exact=True).count() == 1)
                check('Filename remains original', page.get_by_text('Home.txt',exact=True).count() == 1)
                # Join with camera/microphone off: validate room state, no physical-media claim.
                visit(f'/classroom?id={cid}','en');page.locator('#join').click();page.locator('#room:not(.hidden)').wait_for()
                peers_before=page.locator('#participantCount').inner_text()
                page.locator('#langToggle').click()
                check('Live classroom stays joined during switch', not page.locator('#room').evaluate('el=>el.classList.contains("hidden")'))
                check('Call-control accessibility label changes', page.locator('.roomcontrols').get_attribute('aria-label') == '通话控制')
                check('Class title remains original', page.locator('.roomhead h1').inner_text() == 'Synthetic private title')
                check('Language switch preserves participant count', page.locator('#participantCount').inner_text() == peers_before)
                check('Classroom input placeholder localized', page.locator('#chatInput').get_attribute('placeholder') == '发送课堂消息…')
                capture('classroom-joined-zh')
                page.locator('#leave').click()
                page.locator('#logout').click();page.wait_for_url(origin+'/')
                login('teacher');visit('/teacher','zh')
                check('Management moved to desktop', page.locator('[data-i18n="teacher.website_management"]').count()==1)
                check('Retired translation UI is absent', page.locator('#translationDraft').count()==0)
                response=context.request.get(origin+'/teacher/translations',max_redirects=0)
                check('Old translation URL retires to desktop guidance',response.status in (302,303) and response.headers.get('location')=='/teacher')
                state=context.request.get(origin+'/api/admin/content-translations').json()
                source_row=next(item for item in state['sources'] if item['key']=='settings:0:intro')
                source=source_row['original'];translated='公开介绍：$x^2+1$。<img src=x onerror=alert(1)>'
                csrf=context.request.get(origin+'/api/me').json()['csrf']
                payload=dict(action='save',key=source_row['key'],source_hash=source_row['source_hash'],revision=0,target='zh',text=translated)
                response=context.request.post(origin+'/api/admin/content-translations',data=payload,headers={'X-CSRF-Token':csrf})
                check('Desktop-compatible draft API saves',response.ok)
                pub=context.request.get(origin+'/api/content-translations?lang=zh').json()
                check('Draft not public','settings:0:intro' not in pub['translations'])
                row=next(item for item in context.request.get(origin+'/api/admin/content-translations').json()['translations'] if item['source_key']==source_row['key'])
                payload.update(action='approve',revision=row['revision'])
                check('Desktop-compatible explicit approval succeeds',context.request.post(origin+'/api/admin/content-translations',data=payload,headers={'X-CSRF-Token':csrf}).ok)
                visit('/','zh');lead=page.locator('.lead')
                check('Approved translation displayed', translated in lead.inner_text())
                check('Translated HTML remains text', lead.locator('img').count() == 0)
                check('Original title not translated by UI', page.locator('h1').inner_text().startswith('Home'))
                page.locator('#langToggle').click()
                check('English original and visible fallback', source in page.locator('.lead').inner_text() and 'Original' in page.locator('.lead').inner_text())
                with case.app.db() as c:
                    c.execute("UPDATE settings SET value='Changed synthetic public introduction.' WHERE key='intro'")
                visit('/','zh')
                check('Stale translation replaced by original fallback', 'Changed synthetic' in page.locator('.lead').inner_text() and '暂无译文' in page.locator('.lead').inner_text())
                check('No browser JavaScript errors', not errors)
                page.route('**/app.js*', lambda route: route.abort())
                page.goto(origin+'/')
                page.get_by_text('启动诊断',exact=True).wait_for()
                check('Startup diagnostic localized when app module fails', page.get_by_text('Math Studio 无法打开',exact=True).count() == 1)
                capture('startup-diagnostic-zh')
                browser.close()
        finally:
            case.tearDown()
    outcome={'passed':len(results),'failed':0,'checks':results,'javascript_errors':errors,
             'provider':'disabled; manual synthetic drafts only; no real provider called',
             'media':'Joined loopback room without camera/microphone. No physical media/device acceptance.'}
    (args.output/'browser-results.json').write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(outcome,ensure_ascii=False))


if __name__ == '__main__':
    main()
