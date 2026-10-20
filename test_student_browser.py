"""Actual Chromium process restarts with a local synthetic HTTPS OWNER."""
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from test_security_stability import BackendCase
try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None

@unittest.skipUnless(sync_playwright and shutil.which('chromium') and shutil.which('openssl'),'Optional real Chromium/HTTPS restart harness unavailable')
class StudentBrowser(unittest.TestCase):
    def test_remembered_and_unchecked_login_across_real_browser_process_restarts(self):
        case=BackendCase();case.setUp()
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);key=temp/'test.key';cert=temp/'test.pem'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            secure=case.app.ThreadingHTTPServer(('127.0.0.1',0),case.app.Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key);secure.socket=context.wrap_socket(secure.socket,server_side=True)
            thread=threading.Thread(target=secure.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start();base=f'https://127.0.0.1:{secure.server_port}'
            try:
                with sync_playwright() as p:
                    def launch(profile):return p.chromium.launch_persistent_context(str(temp/profile),executable_path=shutil.which('chromium'),ignore_https_errors=True,args=['--no-sandbox'])
                    def signin(ctx,remember):
                        page=ctx.new_page();page.goto(base+'/login');page.locator('#username').fill('student');page.locator('#password').fill('synthetic-password-123')
                        if remember:page.locator('[name=remember_me]').check()
                        page.locator('#auth button').click();page.wait_for_url('**/account');page.wait_for_function('()=>window.__MATHSTUDIO_BOOTED__===true');return page
                    ctx=launch('remembered');page=signin(ctx,True)
                    cookies=ctx.cookies();persistent=next(c for c in cookies if c['name']=='mathstudio_student_remember')
                    self.assertTrue(persistent['secure'] and persistent['httpOnly']);self.assertEqual(persistent['sameSite'],'Strict');self.assertGreater(persistent['expires'],time.time())
                    self.assertFalse(page.evaluate("Object.keys(localStorage).some(k=>/password|token|remember/i.test(k))"));ctx.close()
                    for session in case.app.SESSIONS.values():session['expires']=0
                    ctx=launch('remembered');page=ctx.new_page();page.goto(base+'/account');page.wait_for_function('()=>window.__MATHSTUDIO_BOOTED__===true')
                    self.assertEqual(ctx.request.get(base+'/api/me').json()['user']['role'],'student')
                    replacement=next(c for c in ctx.cookies() if c['name']=='mathstudio_student_remember');self.assertNotEqual(replacement['value'],persistent['value'])
                    page.locator('#logout').click();page.wait_for_url(base+'/');ctx.close()
                    ctx=launch('remembered');self.assertIsNone(ctx.request.get(base+'/api/me').json()['user']);ctx.close()
                    ctx=launch('ordinary');signin(ctx,False);self.assertFalse(any(c['name']=='mathstudio_student_remember' for c in ctx.cookies()));ctx.close()
                    for session in case.app.SESSIONS.values():session['expires']=0
                    ctx=launch('ordinary');self.assertIsNone(ctx.request.get(base+'/api/me').json()['user']);ctx.close()
            finally:secure.shutdown();secure.server_close();thread.join(2);case.tearDown()
