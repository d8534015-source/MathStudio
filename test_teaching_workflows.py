"""Approved Phase 2B part 1 regressions; no production data or native GUI."""
import ast
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import urllib.request
import urllib.error
import unittest
import subprocess
from types import SimpleNamespace, MethodType
from studio_time import studio_zone, parse_local, weekly_timestamp, timezone_rules

from test_security_stability import BackendCase


class TextDouble:
    def __init__(self): self.text=''; self.state='disabled'
    def config(self, **kw): self.state=kw.get('state',self.state)
    def delete(self, *args): self.text=''
    def insert(self, index, text): self.text+=text
    def see(self, *args): pass


class TimerDouble:
    def __init__(self): self.jobs={}; self.next_id=0
    def after(self, delay, callback):
        self.next_id+=1; self.jobs[self.next_id]=(delay,callback); return self.next_id
    def after_cancel(self, job): self.jobs.pop(job,None)
    def run_next(self):
        job=next(iter(self.jobs)); _,callback=self.jobs.pop(job); callback()


def chat_controller(client, kind, cid):
    ns=extracted_functions('teacher_desktop_app.py', {'refresh_group_messages'}, {'datetime':datetime,'studio_zone':studio_zone})
    obj=SimpleNamespace(client=client, active_chat_type=kind, active_chat_id=cid,
                        root=TimerDouble(), chat_text=TextDouble(), message_poll_job=None,
                        status_label=SimpleNamespace(config=lambda **kw:None), tr=lambda value:value,
                        studio_zone_name=lambda:'America/Edmonton')
    obj.refresh_group_messages=MethodType(ns['refresh_group_messages'],obj)
    return obj


def extracted_functions(filename, names, namespace):
    tree = ast.parse(Path(__file__).with_name(filename).read_text(encoding='utf-8'))
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=functions, type_ignores=[]), filename, 'exec'), namespace)
    return namespace


class TeachingBackend(BackendCase):
    def local_start(self, value):
        return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo('America/Edmonton')).timestamp()

    def test_book01_availability_and_group_recurrence_preserve_wall_time(self):
        teacher=self.client('teacher')
        lesson=self.request('/api/schedule')[1]['lesson_types'][0]['id']
        for day in ('2026-10-25','2027-03-07'):
            with self.subTest(day=day):
                start=self.local_start(day+'T16:00')
                made=self.request('/api/admin/availability',{'start':start,'end':start+7200,'repeat_weekly':True,'weeks':2},teacher)
                self.assertEqual(made[0],200,made[1])
                group=self.request('/api/admin/group-class',{'title':'Synthetic','lesson_type_id':lesson,'start':start,'capacity':2,'repeat_weekly':True,'weeks':2},teacher)
                self.assertEqual(group[0],200,group[1])
                with self.app.db() as c:
                    for table,ids in [('availability',made[1]['ids']),('classes',group[1]['ids'])]:
                        rows=c.execute(f'SELECT start FROM {table} WHERE id IN (?,?) ORDER BY start',ids).fetchall()
                        local=[datetime.fromtimestamp(r['start'],ZoneInfo('America/Edmonton')) for r in rows]
                        self.assertEqual([d.hour for d in local],[16,16])
                        self.assertEqual((local[1].date()-local[0].date()).days,7)

    def test_book01_weekly_confirmation_uses_local_availability(self):
        teacher,student=self.client('teacher'),self.client('student')
        start=self.local_start('2026-10-25T16:00')
        second=self.local_start('2026-11-01T16:00')
        with self.app.db() as c:
            aid=c.execute('INSERT INTO availability(start,end) VALUES (?,?)',(start,start+7200)).lastrowid
            c.execute('INSERT INTO availability(start,end) VALUES (?,?)',(second,second+7200))
        lid=self.request('/api/schedule')[1]['lesson_types'][0]['id']
        booked=self.request('/api/request-booking',{'lesson_type_id':lid,'availability_id':aid,'start':start},student)
        self.assertEqual(booked[0],200,booked[1]); cid=booked[1]['class_id']
        confirmed=self.request('/api/admin/booking-action',{'class_id':cid,'action':'confirm_weekly','weeks':2},teacher)
        self.assertEqual(confirmed[0],200,confirmed[1])
        with self.app.db() as c:
            starts=[r[0] for r in c.execute('SELECT start FROM classes ORDER BY start')]
        self.assertEqual(starts,[start,second])

    def test_book01_invalid_dst_occurrence_rolls_back_entire_series(self):
        teacher=self.client('teacher')
        start=self.local_start('2027-03-07T02:30')
        made=self.request('/api/admin/availability',{'start':start,'end':start+5400,'repeat_weekly':True,'weeks':2},teacher)
        self.assertEqual(made[0],400)
        with self.app.db() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM availability').fetchone()[0],0)

    def test_book01_conflicting_dst_week_keeps_request_pending(self):
        teacher,student=self.client('teacher'),self.client('student')
        first=self.local_start('2026-10-25T16:00'); second=self.local_start('2026-11-01T16:00')
        busy=self.lesson(user='other')
        with self.app.db() as c:
            c.execute('UPDATE classes SET start=? WHERE id=?',(second+1800,busy))
            aid=c.execute('INSERT INTO availability(start,end) VALUES (?,?)',(first,first+7200)).lastrowid
            c.execute('INSERT INTO availability(start,end) VALUES (?,?)',(second,second+7200))
        lid=self.request('/api/schedule')[1]['lesson_types'][0]['id']
        cid=self.request('/api/request-booking',{'lesson_type_id':lid,'availability_id':aid,'start':first},student)[1]['class_id']
        self.assertEqual(self.request('/api/admin/booking-action',{'class_id':cid,'action':'confirm_weekly','weeks':2},teacher)[0],409)
        with self.app.db() as c:
            self.assertEqual(c.execute('SELECT approval FROM classes WHERE id=?',(cid,)).fetchone()[0],'pending')
            self.assertEqual(c.execute('SELECT count(*) FROM classes').fetchone()[0],2)

    def test_book01_availability_end_and_repeated_hour_policy(self):
        teacher=self.client('teacher')
        first=self.local_start('2026-10-25T00:00')
        made=self.request('/api/admin/availability',{'start':first,'end':first+14400,'repeat_weekly':True,'weeks':2},teacher)
        self.assertEqual(made[0],200,made[1])
        with self.app.db() as c:
            row=c.execute('SELECT start,end FROM availability ORDER BY start DESC LIMIT 1').fetchone()
        self.assertEqual(datetime.fromtimestamp(row['end'],studio_zone()).hour,4)
        self.assertEqual(row['end']-row['start'],18000)
        self.assertEqual(weekly_timestamp(self.local_start('2026-10-25T01:30'),1),self.local_start('2026-11-01T01:30'))

    def test_book02_browser_receives_authoritative_timezone_rules(self):
        teacher=self.client('teacher')
        self.assertEqual(self.request('/api/admin/settings',{'timezone':'America/Vancouver'},teacher)[0],200)
        rules=self.request('/api/public')[1]['timezone_rules']
        self.assertEqual(rules['zone'],'America/Vancouver')
        stamp=parse_local('2026-11-01','16:00','America/Vancouver')
        offset=[x['offset'] for x in rules['transitions'] if x['at']<=stamp][-1]
        self.assertEqual(offset,int(datetime.fromtimestamp(stamp,studio_zone('America/Vancouver')).utcoffset().total_seconds()))
        script="""import fs from 'node:fs'; import assert from 'node:assert/strict';
import {setTimezoneRules,fromWall,formatAt} from './studio_time.js';
const x=JSON.parse(fs.readFileSync(0,'utf8'));setTimezoneRules(x.rules);
assert.equal(fromWall({year:2026,month:11,day:1,hour:16},x.rules.zone).getTime()/1000,x.stamp);
assert.equal(formatAt(x.stamp*1000,x.rules.zone,'en-CA',{hour:'2-digit',minute:'2-digit',hourCycle:'h23'}),'16:00');"""
        result=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps({'rules':rules,'stamp':stamp}),
                              cwd=Path(__file__).parent,text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.request('/studio_time.js')[0],200)

    def test_media01_real_native_helper_can_request_one_use_handoff(self):
        teacher, cid, token, _, _ = self.native_tokens()
        ns = extracted_functions('teacher_meeting_app.py', {'http_json'}, {
            'json': json, 'Request': urllib.request.Request,
            'urlopen': urllib.request.urlopen, 'HTTPError': urllib.error.HTTPError,
            'URLError': urllib.error.URLError})
        before = len(self.app.SESSIONS)
        handoff = ns['http_json'](f'http://127.0.0.1:{self.http.server_port}/api/teacher-app/media-login-token',
                                  'POST', {'token': token})
        self.assertEqual(len(self.app.SESSIONS), before)
        browser = {}
        path = '/teacher-media-login?token='+handoff['media_token']
        self.assertEqual(self.request(path, state=browser)[0], 302)
        self.assertEqual(self.request('/api/me', state=browser)[1]['user']['role'], 'admin')
        self.assertEqual(self.request(path)[0], 403)

    def test_media01_missing_and_revoked_tokens_cannot_bypass_auth(self):
        teacher, cid, token, _, _ = self.native_tokens()
        path = '/api/teacher-app/media-login-token'
        for bad in ['', 'not-a-valid-native-token']:
            self.assertEqual(self.request(path, {'token': bad})[0], 403)
        self.request('/api/logout', {}, teacher)
        self.assertEqual(self.request(path, {'token': token})[0], 403)
        # Ordinary account mutations retain their CSRF gate.
        self.assertEqual(self.request('/api/login', {'username': 'teacher', 'password': 'anything'})[0], 403)

    def test_ui01_teacher_reads_all_pages_and_resource_code_messages(self):
        teacher=self.client('teacher')
        with self.app.db() as c:
            c.execute("INSERT INTO resource_codes(code,label,created,created_by) VALUES ('ABC234','Synthetic',0,?)",(self.uid('teacher'),))
        for kind in ('class','group'):
            with self.subTest(kind=kind):
                if kind=='class':
                    cid=self.lesson(user='student'); table='class_messages'; column='class_id'
                else:
                    with self.app.db() as c:
                        cid=c.execute("INSERT INTO group_chats(name,created,created_by) VALUES ('Synthetic',0,?)",(self.uid('teacher'),)).lastrowid
                    table='group_messages'; column='group_id'
                with self.app.db() as c:
                    c.executemany(f'INSERT INTO {table}({column},user_id,text,created) VALUES (?,?,?,?)',
                        [(cid,self.uid('teacher'),f'Message {i}'+(' ABC234' if i==450 else ''),0) for i in range(601)])
                paths=[]
                def get(path):
                    paths.append(path); status,out,_=self.request(path,state=teacher)
                    self.assertEqual(status,200); return out
                ui=chat_controller(SimpleNamespace(json=get),kind,cid)
                ui.refresh_group_messages(); ui.root.run_next(); ui.root.run_next()
                self.assertIn('Message 600\n',ui.chat_text.text)
                self.assertIn('[resource: ABC234]',ui.chat_text.text)
                self.assertEqual(ui.chat_text.text.count('Message '),601)
                self.assertEqual(ui.chat_text.state,'disabled')
                ui.refresh_group_messages()
                self.assertEqual(ui.chat_text.text.count('Message '),601)
                self.assertEqual(len(ui.root.jobs),1)
                self.assertIn('since=300',paths[1]); self.assertIn('since=600',paths[2])

    def test_ui01_poll_failure_preserves_chat_and_one_retry(self):
        calls=iter([{'messages':[{'id':1,'at':0,'name':'Synthetic','text':'Keep this','codes':[]}],'seq':1},RuntimeError('synthetic outage')])
        def get(path):
            out=next(calls)
            if isinstance(out,Exception): raise out
            return out
        ui=chat_controller(SimpleNamespace(json=get),'class',1)
        ui.refresh_group_messages(); previous=ui.chat_text.text
        ui.refresh_group_messages()
        self.assertEqual(ui.chat_text.text,previous)
        self.assertEqual(ui.chat_text.state,'disabled')
        self.assertEqual(len(ui.root.jobs),1)

    def test_ui01_switching_conversation_resets_cursor_and_old_content(self):
        paths=[]
        def get(path):
            paths.append(path)
            if len(paths)==2: raise RuntimeError('synthetic outage')
            return {'messages':[{'id':1,'at':0,'name':'Synthetic','text':'First chat','codes':[]}],'seq':1}
        ui=chat_controller(SimpleNamespace(json=get),'class',1)
        ui.refresh_group_messages();ui.active_chat_id=2;ui.refresh_group_messages()
        self.assertIn('class=2&since=0',paths[1])
        self.assertEqual(ui.chat_text.text,'')
        self.assertEqual(ui.chat_text.state,'disabled')
        self.assertEqual(len(ui.root.jobs),1)


class BrowserWorkflows(unittest.TestCase):
    def test_browser_workflow_regressions(self):
        result=subprocess.run(['node',str(Path(__file__).with_name('test_browser_workflows.mjs'))],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


class StudioTimeTests(unittest.TestCase):
    def test_book02_shared_python_rules_match_browser_policy(self):
        expected={'America/Edmonton':'2026-11-01T23:00:00+00:00',
                  'America/Vancouver':'2026-11-01T23:00:00+00:00',
                  'America/Toronto':'2026-11-01T21:00:00+00:00','UTC':'2026-11-01T16:00:00+00:00'}
        for zone,value in expected.items():
            self.assertEqual(datetime.fromtimestamp(parse_local('2026-11-01','16:00',zone),ZoneInfo('UTC')).isoformat(),value)
            first=parse_local('2026-10-25','16:00',zone)
            self.assertEqual(weekly_timestamp(first,1,zone),parse_local('2026-11-01','16:00',zone))
        with self.assertRaises(ValueError): parse_local('2027-03-14','02:30','America/Edmonton')
        self.assertEqual(datetime.fromtimestamp(parse_local('2026-11-01','01:30'),ZoneInfo('UTC')).hour,7)

    def test_book02_desktop_calendar_and_labels_ignore_device_zone(self):
        class DeviceDateTime(datetime):
            @classmethod
            def now(cls,tz=None):
                return cls.fromtimestamp(datetime(2026,10,26,18,tzinfo=ZoneInfo('UTC')).timestamp(),tz)
            @classmethod
            def fromtimestamp(cls,ts,tz=None):
                value=datetime.fromtimestamp(ts,tz or ZoneInfo('Asia/Shanghai'))
                return value if tz else value.replace(tzinfo=None)
        class Canvas:
            def __init__(self): self.texts=[]
            def winfo_width(self): return 1000
            def delete(self,*a): self.texts=[]
            def configure(self,**kw): pass
            def create_polygon(self,*a,**kw): pass
            def create_rectangle(self,*a,**kw): pass
            def create_line(self,*a,**kw): pass
            def create_text(self,*a,**kw): self.texts.append((a,kw))
        tree=ast.parse(Path(__file__).with_name('teacher_desktop_app.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='TeacherDesktopApp')
        methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('studio_zone_name','fmt_time','draw_calendar')]
        globals_=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fmt_time']
        shell=ast.ClassDef(name='Desktop',bases=[],keywords=[],decorator_list=[],body=methods)
        namespace={'datetime':DeviceDateTime,'timedelta':timedelta,'studio_zone':studio_zone}
        exec(compile(ast.fix_missing_locations(ast.Module(body=globals_+[shell],type_ignores=[])),'desktop-clock-test','exec'),namespace)
        ui=namespace['Desktop']();ui.public={'settings':{'timezone':'America/Edmonton'}}
        ui.lang='en';ui.week_offset=0;ui.tr=lambda value:value
        ui.calendar_canvas=Canvas();ui.week_label=SimpleNamespace(config=lambda **kw:None)
        stamp=parse_local('2026-11-01','16:00')
        ui.schedule={'availability':[]};ui.admin={'calendar_classes':[{'id':1,'start':stamp,'minutes':60,'status':'scheduled','title':'Synthetic class','attendees':[]}]}
        self.assertIn('Nov 1',ui.fmt_time(stamp))
        ui.lang='zh';self.assertEqual(ui.fmt_time(stamp),'2026年11月01日 16:00')
        ui.draw_calendar()
        labels=[(coords,kw) for coords,kw in ui.calendar_canvas.texts if kw.get('text','').startswith('Synthetic class')]
        self.assertEqual(len(labels),1)
        self.assertEqual(labels[0][0][1],933)


if __name__ == '__main__':
    unittest.main(verbosity=2)
