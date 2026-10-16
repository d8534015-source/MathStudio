"""Math Studio local tutoring website. Python 3.9+, standard library only.
Run: py server.py | py server.py add-admin | py server.py reset-password
"""
import contextlib
import getpass
import hashlib
import hmac
import ipaddress
import io
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, quote, unquote, urlencode

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('MATH_DATA', str(ROOT / 'bulletin_data')))
PORT = int(os.environ.get('PORT', '5051'))
BIND = os.environ.get('BIND_HOST', '0.0.0.0')
PUBLIC_ORIGIN = os.environ.get('PUBLIC_ORIGIN', '').rstrip('/')
COOKIE = 'mathstudio_5051'
SESSIONS = {}
# Anonymous visitors should not occupy a session slot for eight hours.
ANON_SESSION_IDLE_SECONDS = 15 * 60
ANON_SESSION_LIMIT = 500
SESSION_LIMIT = 3000
SESSION_WARN_AT = 500
ROOMS = {}
RESOURCE_GRANTS = {}
OVERLAY_TOKENS = {}
TEACHER_APP_TOKENS = {}
TEACHER_MEDIA_TOKENS = {}
TEACHER_APP_PROCESSES = {}
LOCK = threading.RLock()
TURN_CACHE = {'iceServers': None, 'expires': 0.0, 'provider': '', 'error': ''}
TURN_CACHE_LOCK = threading.RLock()

def _cloudflare_turn_ice_servers():
    """Generate and cache short-lived Cloudflare Realtime TURN credentials.

    The long-lived TURN key token remains server-side. Browsers only receive
    short-lived ICE credentials returned by Cloudflare.
    """
    key_id=os.environ.get('CLOUDFLARE_TURN_KEY_ID','').strip()
    api_token=os.environ.get('CLOUDFLARE_TURN_API_TOKEN','').strip()
    if not (key_id and api_token):
        return None, '', ''
    with TURN_CACHE_LOCK:
        now=time.time()
        cached=TURN_CACHE.get('iceServers')
        if now < float(TURN_CACHE.get('expires') or 0):
            return cached, TURN_CACHE.get('provider','Cloudflare Realtime TURN'), TURN_CACHE.get('error','')
        url=f'https://rtc.live.cloudflare.com/v1/turn/keys/{quote(key_id,safe="")}/credentials/generate-ice-servers'
        payload=json.dumps({'ttl':86400}).encode('utf-8')
        req=urllib.request.Request(url,data=payload,method='POST',headers={
            'Authorization':'Bearer '+api_token,
            'Content-Type':'application/json',
            'User-Agent':'MathStudio/1.0'
        })
        try:
            with urllib.request.urlopen(req,timeout=8) as resp:
                body=json.loads(resp.read().decode('utf-8','replace'))
            servers=body.get('iceServers') or []
            clean=[]
            for item in servers:
                if not isinstance(item,dict): continue
                urls=item.get('urls')
                if isinstance(urls,str): urls=[urls]
                if not isinstance(urls,list): continue
                # Browser-incompatible/obsolete alternate port 53 is intentionally omitted.
                urls=[u for u in urls if isinstance(u,str) and ':53' not in u]
                if not urls: continue
                out={'urls':urls}
                if item.get('username'): out['username']=str(item['username'])
                if item.get('credential'): out['credential']=str(item['credential'])
                clean.append(out)
            if not any('credential' in x for x in clean):
                raise RuntimeError('Cloudflare did not return TURN credentials.')
            TURN_CACHE.update({'iceServers':clean,'expires':now+43200,'provider':'Cloudflare Realtime TURN','error':''})
            return clean,'Cloudflare Realtime TURN',''
        except Exception as ex:
            err=str(ex)[:180]
            TURN_CACHE.update({'iceServers':None,'expires':now+60,'provider':'Cloudflare Realtime TURN','error':err})
            return None,'Cloudflare Realtime TURN',err

def build_ice_servers(user_id):
    """Return ICE servers plus relay diagnostics without exposing long-lived secrets."""
    cloudflare,provider,error=_cloudflare_turn_ice_servers()
    if cloudflare:
        return cloudflare,True,provider,''
    servers=[]
    stun=os.environ.get('STUN_URL','').strip()
    if stun:
        servers.append({'urls':stun})
    else:
        servers.append({'urls':['stun:stun.cloudflare.com:3478','stun:stun.l.google.com:19302']})
    turn=os.environ.get('TURN_URL','').strip()
    if turn:
        static_user=os.environ.get('TURN_USERNAME','').strip()
        static_credential=os.environ.get('TURN_CREDENTIAL','').strip()
        secret=os.environ.get('TURN_SECRET','').strip()
        if static_user and static_credential:
            servers.append({'urls':turn,'username':static_user,'credential':static_credential})
        elif secret:
            import base64
            username=str(int(time.time())+14400)+':'+str(user_id)
            credential=base64.b64encode(hmac.new(secret.encode(),username.encode(),hashlib.sha1).digest()).decode()
            servers.append({'urls':turn,'username':username,'credential':credential})
    relay=any('credential' in x for x in servers)
    return servers,relay,('Static TURN' if relay else ''),error
DEFAULTS = {'name':'Math Studio','headline':'Find your way through challenging math.',
 'intro':'Thoughtful lessons for contest preparation and classroom confidence. Explore Waterloo and AMC problems, or build a stronger foundation in Alberta and Canadian school mathematics.',
 'teacher':'Your math teacher', 'about':'Lessons that make room for questions, different approaches, and the moment an idea clicks.',
 'contact':'', 'timezone':'America/Edmonton'}

def _extract_translatable_text(row):
    data=storage_get(row['storage_key'],row['storage_backend'])
    name=(row['original_name'] or '').lower()
    mime=(row['mime'] or '').lower()
    if mime.startswith('text/') or name.endswith(('.txt','.md','.csv','.json','.html','.htm')):
        value=data.decode('utf-8','replace')
        if name.endswith(('.html','.htm')):
            value=re.sub(r'<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>',' ',value,flags=re.I|re.S)
            value=re.sub(r'<[^>]+>',' ',value)
        return re.sub(r'\n{3,}','\n\n',value).strip()[:30000]
    if name.endswith('.docx') or mime=='application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml=z.read('word/document.xml').decode('utf-8','replace')
            xml=xml.replace('</w:p>','\n').replace('</w:tr>','\n')
            value=re.sub(r'<[^>]+>','',xml)
            value=value.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
            return re.sub(r'\n{3,}','\n\n',value).strip()[:30000]
        except Exception as ex:
            raise APIError('This Word document could not be prepared for translation: '+str(ex)[:120],422)
    if name.endswith('.pdf') or mime=='application/pdf':
        reader_cls=None
        try:
            from pypdf import PdfReader as reader_cls
        except Exception:
            try:
                from PyPDF2 import PdfReader as reader_cls
            except Exception:
                reader_cls=None
        need(reader_cls,'PDF translation needs the optional pypdf package on the website computer. Word and text documents work without it.',422)
        try:
            reader=reader_cls(io.BytesIO(data)); parts=[]
            for page in reader.pages[:80]:
                parts.append(page.extract_text() or '')
                if sum(map(len,parts))>30000: break
            return '\n\n'.join(parts)[:30000].strip()
        except Exception:
            raise APIError('This PDF does not contain readable text for automatic translation.',422)
    raise APIError('Automatic translation currently supports text, HTML, DOCX, and text-based PDF files.',422)

def _translate_online(value,target):
    target='zh-CN' if target.lower().startswith('zh') else 'en'
    need(value.strip(),'No readable text was found in this document.',422)
    chunks=[]; current=''
    for para in re.split(r'(\n+)',value[:30000]):
        if len(current)+len(para)>2800 and current:
            chunks.append(current); current=''
        if len(para)>2800:
            for i in range(0,len(para),2800):
                if current: chunks.append(current); current=''
                chunks.append(para[i:i+2800])
        else:
            current+=para
    if current: chunks.append(current)
    output=[]
    for chunk in chunks[:14]:
        query=urlencode({'client':'gtx','sl':'auto','tl':target,'dt':'t','q':chunk})
        req=urllib.request.Request('https://translate.googleapis.com/translate_a/single?'+query,headers={'User-Agent':'Mozilla/5.0 MathStudio/1.0'})
        try:
            with urllib.request.urlopen(req,timeout=12) as resp:
                payload=json.loads(resp.read().decode('utf-8','replace'))
            output.append(''.join(x[0] for x in (payload[0] or []) if x and x[0]))
        except Exception:
            raise APIError('The online translation service is temporarily unavailable. Try again later.',503)
    return ''.join(output).strip()

def current_public_origin():
    """Return the live public origin. The desktop teacher app can update it without restarting the server."""
    env=os.environ.get('PUBLIC_ORIGIN','').rstrip('/')
    if env:
        return env
    try:
        value=(DATA/'public_origin.txt').read_text(encoding='utf-8').strip().rstrip('/')
        if value.startswith('https://'):
            return value
    except OSError:
        pass
    return ''

@contextlib.contextmanager
def db():
    c=sqlite3.connect(str(DATA/'posts.db'),timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        with c:
            yield c
    finally:
        c.close()

def init():
    DATA.mkdir(parents=True,exist_ok=True)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student');
        CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY, title TEXT NOT NULL, track TEXT NOT NULL,
          description TEXT NOT NULL, start REAL NOT NULL, minutes INTEGER NOT NULL, capacity INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'scheduled', live INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id),
          class_id INTEGER REFERENCES classes(id), created REAL NOT NULL, UNIQUE(user_id,class_id));
        CREATE TABLE IF NOT EXISTS availability(id INTEGER PRIMARY KEY, start REAL NOT NULL, end REAL NOT NULL,
          status TEXT NOT NULL DEFAULT 'open', repeat_group TEXT);
        CREATE TABLE IF NOT EXISTS lesson_types(id INTEGER PRIMARY KEY, name TEXT NOT NULL, minutes INTEGER NOT NULL,
          price_label TEXT NOT NULL DEFAULT 'Price TBD', active INTEGER NOT NULL DEFAULT 1,
          UNIQUE(name, minutes));
        CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY,title TEXT NOT NULL,body TEXT NOT NULL,
          author TEXT NOT NULL,created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M','now')));
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(ip TEXT PRIMARY KEY,count INTEGER NOT NULL,start REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS boards(class_id INTEGER PRIMARY KEY REFERENCES classes(id),
          version INTEGER NOT NULL DEFAULT 0, content TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS stored_files(id INTEGER PRIMARY KEY, original_name TEXT NOT NULL,
          storage_key TEXT UNIQUE NOT NULL, storage_backend TEXT NOT NULL DEFAULT 'local', mime TEXT NOT NULL,
          size INTEGER NOT NULL, created REAL NOT NULL, uploaded_by INTEGER REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS resource_codes(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL,
          label TEXT NOT NULL DEFAULT 'Shared files', created REAL NOT NULL, created_by INTEGER REFERENCES users(id),
          active INTEGER NOT NULL DEFAULT 1, translate_enabled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS resource_code_files(code_id INTEGER NOT NULL REFERENCES resource_codes(id) ON DELETE CASCADE,
          file_id INTEGER NOT NULL REFERENCES stored_files(id) ON DELETE CASCADE, position INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(code_id,file_id));
        CREATE INDEX IF NOT EXISTS resource_code_files_file_idx ON resource_code_files(file_id);
        CREATE TABLE IF NOT EXISTS class_messages(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, text TEXT NOT NULL, created REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS class_messages_class_idx ON class_messages(class_id,id);
        CREATE TABLE IF NOT EXISTS group_chats(id INTEGER PRIMARY KEY, name TEXT NOT NULL, created REAL NOT NULL,
          created_by INTEGER REFERENCES users(id), kind TEXT NOT NULL DEFAULT 'manual');
        CREATE TABLE IF NOT EXISTS group_chat_members(group_id INTEGER NOT NULL REFERENCES group_chats(id) ON DELETE CASCADE,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, joined REAL NOT NULL, PRIMARY KEY(group_id,user_id));
        CREATE INDEX IF NOT EXISTS group_chat_members_user_idx ON group_chat_members(user_id,group_id);
        CREATE TABLE IF NOT EXISTS group_messages(id INTEGER PRIMARY KEY, group_id INTEGER NOT NULL REFERENCES group_chats(id) ON DELETE CASCADE,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, text TEXT NOT NULL, created REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS group_messages_group_idx ON group_messages(group_id,id);
        CREATE TABLE IF NOT EXISTS instant_meetings(code TEXT PRIMARY KEY, class_id INTEGER NOT NULL UNIQUE REFERENCES classes(id) ON DELETE CASCADE,
          created REAL NOT NULL, expires REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_by INTEGER REFERENCES users(id));
        CREATE INDEX IF NOT EXISTS instant_meetings_class_idx ON instant_meetings(class_id);
        ''')
        # Additive booking migration. Existing fixed classes remain confirmed appointments.
        columns={r['name'] for r in c.execute('PRAGMA table_info(classes)')}
        for name,sql in (
            ('approval',"ALTER TABLE classes ADD COLUMN approval TEXT NOT NULL DEFAULT 'confirmed'"),
            ('lesson_type_id',"ALTER TABLE classes ADD COLUMN lesson_type_id INTEGER"),
            ('availability_id',"ALTER TABLE classes ADD COLUMN availability_id INTEGER"),
            ('series_id',"ALTER TABLE classes ADD COLUMN series_id TEXT"),
            ('requested_by',"ALTER TABLE classes ADD COLUMN requested_by INTEGER"),
            ('class_kind',"ALTER TABLE classes ADD COLUMN class_kind TEXT NOT NULL DEFAULT 'individual'"),
            ('group_price_label',"ALTER TABLE classes ADD COLUMN group_price_label TEXT"),
            ('group_chat_id',"ALTER TABLE classes ADD COLUMN group_chat_id INTEGER"),
        ):
            if name not in columns: c.execute(sql)
        resource_columns={r['name'] for r in c.execute('PRAGMA table_info(resource_codes)')}
        if 'translate_enabled' not in resource_columns:
            c.execute("ALTER TABLE resource_codes ADD COLUMN translate_enabled INTEGER NOT NULL DEFAULT 0")
        # One-time migration from the previous Bulletin database; no data is deleted.
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='admins'").fetchone() and not c.execute("SELECT 1 FROM settings WHERE key='legacy_imported'").fetchone():
            for row in c.execute('SELECT * FROM admins').fetchall():
                c.execute("INSERT OR IGNORE INTO users(username,name,password,role) VALUES (?,?,?,'admin')",(row['name'],row['name'],row['password']))
            c.execute("INSERT INTO settings VALUES ('legacy_imported','1')")
        for key,value in DEFAULTS.items():
            c.execute('INSERT OR IGNORE INTO settings VALUES (?,?)',(key,value))
        lesson_names=[
            ('Grade 7 Math',60),('Grade 7 Math',90),('Grade 8 Math',60),('Grade 8 Math',90),
            ('Grade 9 Math',60),('Grade 9 Math',90),('Grade 10 Math',60),('Grade 10 Math',90),
            ('Grade 10 AP Math',60),('Grade 10 AP Math',90),('Grade 10 IB Math',60),('Grade 10 IB Math',90),
            ('Grade 11 Math',60),('Grade 11 Math',90),('Grade 11 AP Math',60),('Grade 11 AP Math',90),
            ('Grade 11 IB Math',60),('Grade 11 IB Math',90),('Grade 12 Math',60),('Grade 12 Math',90),
            ('Grade 12 AP Math',60),('Grade 12 AP Math',90),('Grade 12 IB Math',60),('Grade 12 IB Math',90),
            ('Waterloo Contest Prep',60),('Waterloo Contest Prep',90),('AMC Contest Prep',60),('AMC Contest Prep',90),
        ]
        for name,minutes in lesson_names:
            c.execute("INSERT OR IGNORE INTO lesson_types(name,minutes,price_label,active) VALUES (?,?,?,1)",(name,minutes,'Price TBD'))

def hash_password(password):
    salt=secrets.token_hex(16)
    result=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
    return 'pbkdf2:sha256:600000$'+salt+'$'+result

def check_password(stored,password):
    try:
        method,salt,expected=stored.split('$')
        kind,algo,count=method.split(':')
        if kind!='pbkdf2' or algo!='sha256' or not 1<=int(count)<=2000000: return False
        return hmac.compare_digest(hashlib.pbkdf2_hmac(algo,password.encode(),salt.encode(),int(count)).hex(),expected)
    except (ValueError,TypeError): return False

def cli_account(reset=False):
    username=input('Username: ').strip().lower()
    if not re.fullmatch(r'[a-z0-9_]{3,40}',username): raise SystemExit('Use 3–40 letters, numbers, or underscores.')
    password=getpass.getpass('Password (12+ characters; input hidden): ')
    if not 12<=len(password)<=256: raise SystemExit('Use 12–256 characters.')
    if password!=getpass.getpass('Repeat password: '): raise SystemExit('Passwords did not match.')
    with db() as c:
        if reset:
            r=c.execute('UPDATE users SET password=? WHERE username=?',(hash_password(password),username))
            if not r.rowcount: raise SystemExit('User not found.')
        else:
            try: c.execute("INSERT INTO users(username,name,password,role) VALUES (?,?,?,'admin')",(username,username,hash_password(password)))
            except sqlite3.IntegrityError: raise SystemExit('Username exists. Promote this account in Admin → Users.')
    print('Account updated.' if reset else 'Admin created. Use the normal Log in page.')

class APIError(Exception):
    def __init__(self,message,status=400): self.message,self.status=message,status

def need(condition,message,status=400):
    if not condition: raise APIError(message,status)

def field(data,key,low=1,high=200):
    value=data.get(key,'')
    need(isinstance(value,str), 'Invalid '+key)
    value=value.strip()
    need(low<=len(value)<=high,f'{key.capitalize()} must be {low}–{high} characters.')
    return value

def number(data,key,low,high):
    value=data.get(key)
    need(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and low<=value<=high,'Invalid '+key)
    return value

def public_user(row):
    return {key:row[key] for key in ('id','username','name','role')} if row else None

def limit_requests(limits,message):
    """Atomically consume fixed-window budgets; successful accounts cannot
    erase another account's or a client's history."""
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        now=time.time()
        c.execute('DELETE FROM attempts WHERE start<?',(now-300,))
        updates=[]
        for key,maximum,window in limits:
            row=c.execute('SELECT count,start FROM attempts WHERE ip=?',(key,)).fetchone()
            count,start=(row['count'],row['start']) if row and row['start']>now-window else (0,now)
            need(count<maximum,message,429)
            updates.append((key,count+1,start))
        c.executemany('INSERT OR REPLACE INTO attempts VALUES (?,?,?)',updates)

def session_capacity(anonymous=False):
    """Caller holds LOCK. Reserve capacity for authenticated/guest users and
    reclaim idle anonymous entries without evicting active authorizations."""
    now=time.time()
    anon=[(v.get('last_seen',0),key) for key,v in SESSIONS.items()
          if not v.get('user') and not v.get('guest_identity')]
    anon_count=len(anon)
    if len(SESSIONS)>=SESSION_LIMIT or (anonymous and len(anon)>=ANON_SESSION_LIMIT):
        for seen,key in sorted(anon):
            if now-seen<=60: continue
            SESSIONS.pop(key,None)
            anon_count-=1
            if len(SESSIONS)<SESSION_LIMIT and (not anonymous or anon_count<ANON_SESSION_LIMIT): break
    remaining=sum(not v.get('user') and not v.get('guest_identity') for v in SESSIONS.values())
    need(len(SESSIONS)<SESSION_LIMIT and (not anonymous or remaining<ANON_SESSION_LIMIT),
         'Too many sessions. Try again later.',429)

def clean_room(room):
    now=time.time()
    for key in list(room['peers']):
        if room['peers'][key]['seen']<now-25: del room['peers'][key]
    if room['presenter'] not in room['peers']: room['presenter']=None
    room['events'][:]=[event for event in room['events'] if event['at']>now-120]
    room['messages'][:]=[message for message in room.get('messages',[]) if message['at']>now-21600][-300:]

def room_for(class_id):
    return ROOMS.setdefault(class_id,{
        'peers':{},'events':[],'seq':0,'drawing':False,'presenter':None,
        'messages':[],'chat_seq':0,
        'teacher_command_seq':0,'teacher_commands':[],
        'native_screen':{'active':False,'seq':0,'jpeg':b'','at':0.0}
    })

def valid_board(content):
    need(isinstance(content,dict),'Invalid board')
    need(content.get('background') in ('blank','grid'),'Invalid background')
    shapes=content.get('shapes')
    need(isinstance(shapes,list) and len(shapes)<=400,'The board is full. Clear it or remove some shapes.')
    for shape in shapes:
        need(isinstance(shape,dict),'Invalid shape')
        need(shape.get('type') in ('pen','line','circle','rect','text','graph'),'Invalid shape type')
        need(isinstance(shape.get('id'),str) and len(shape['id'])<=80,'Invalid shape ID')
        need(re.fullmatch(r'#[a-fA-F0-9]{6}',str(shape.get('color',''))) is not None,'Invalid colour')
        number(shape,'width',1,12)
        if shape['type']=='graph':
            need(shape.get('fn') in ('quadratic','linear','sine','absolute'),'Invalid graph')
            for key in ('a','h','k'): number(shape,key,-10,10)
        elif shape['type']=='pen':
            pts=shape.get('points')
            need(isinstance(pts,list) and 1<=len(pts)<=1500,'Invalid stroke')
            for p in pts:
                need(isinstance(p,list) and len(p)==2 and all(isinstance(v,(float,int)) and math.isfinite(v) and 0<=v<=1 for v in p),'Invalid point')
        else:
            for key in ('x','y'): number(shape,key,0,1)
            if shape['type']=='text': field(shape,'text',1,300)
            else:
                for key in ('x2','y2'): number(shape,key,0,1)
    need(len(json.dumps(content))<=500000,'Board is too large.')
    return content


RESOURCE_CODE_ALPHABET='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
BLOCKED_UPLOAD_EXTENSIONS={'.html','.htm','.xhtml','.js','.mjs','.svg','.exe','.msi','.bat','.cmd','.com','.scr','.ps1','.vbs'}
INLINE_MIME_PREFIXES=('image/','application/pdf','text/','video/mp4','application/msword','application/vnd.ms-','application/vnd.openxmlformats-officedocument.')

def storage_config():
    keys=('MATH_R2_ACCOUNT_ID','MATH_R2_ACCESS_KEY_ID','MATH_R2_SECRET_ACCESS_KEY','MATH_R2_BUCKET')
    values={k:os.environ.get(k,'').strip() for k in keys}
    if all(values.values()):
        return {'backend':'r2','label':'Cloudflare R2','cloud':True,
                'account':values['MATH_R2_ACCOUNT_ID'],'access':values['MATH_R2_ACCESS_KEY_ID'],
                'secret':values['MATH_R2_SECRET_ACCESS_KEY'],'bucket':values['MATH_R2_BUCKET']}
    return {'backend':'local','label':'Local test storage','cloud':False}

def _sig_key(key,msg): return hmac.new(key,msg.encode(),hashlib.sha256).digest()

def _r2_request(method,key,body=b'',mime='application/octet-stream'):
    cfg=storage_config(); need(cfg['backend']=='r2','Cloud storage is not configured on this server.',503)
    now=datetime.now(timezone.utc); amz_date=now.strftime('%Y%m%dT%H%M%SZ'); date_stamp=now.strftime('%Y%m%d')
    host=f"{cfg['account']}.r2.cloudflarestorage.com"
    uri='/' + quote(cfg['bucket'],safe='') + '/' + quote(key,safe='/~')
    payload_hash=hashlib.sha256(body).hexdigest()
    canonical_headers=f'host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n'
    signed_headers='host;x-amz-content-sha256;x-amz-date'
    canonical_request='\n'.join((method,uri,'',canonical_headers,signed_headers,payload_hash))
    scope=f'{date_stamp}/auto/s3/aws4_request'
    string_to_sign='\n'.join(('AWS4-HMAC-SHA256',amz_date,scope,hashlib.sha256(canonical_request.encode()).hexdigest()))
    k_date=_sig_key(('AWS4'+cfg['secret']).encode(),date_stamp)
    k_region=_sig_key(k_date,'auto'); k_service=_sig_key(k_region,'s3'); k_signing=_sig_key(k_service,'aws4_request')
    signature=hmac.new(k_signing,string_to_sign.encode(),hashlib.sha256).hexdigest()
    auth=f"AWS4-HMAC-SHA256 Credential={cfg['access']}/{scope}, SignedHeaders={signed_headers}, Signature={signature}"
    headers={'Host':host,'x-amz-date':amz_date,'x-amz-content-sha256':payload_hash,'Authorization':auth}
    if method=='PUT': headers['Content-Type']=mime or 'application/octet-stream'
    req=urllib.request.Request('https://'+host+uri,data=body if method=='PUT' else None,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as ex:
        detail=ex.read(500).decode('utf-8','replace')
        print('R2 error:',ex.code,detail)
        raise APIError('Cloud storage request failed. Check the R2 settings and try again.',502)
    except OSError as ex:
        print('R2 network error:',type(ex).__name__,str(ex))
        raise APIError('Could not reach cloud storage. Try again.',502)

def storage_put(key,data,mime):
    cfg=storage_config()
    if cfg['backend']=='r2':
        _r2_request('PUT',key,data,mime); return 'r2'
    root=DATA/'file_store'; target=root/key
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data); return 'local'

def storage_get(key,backend):
    if backend=='r2': return _r2_request('GET',key)
    target=(DATA/'file_store'/key).resolve(); root=(DATA/'file_store').resolve()
    need(root==target or root in target.parents,'Invalid stored file.',500)
    need(target.is_file(),'The stored file is missing.',404)
    return target.read_bytes()

def storage_delete(key,backend):
    if backend=='r2': _r2_request('DELETE',key); return
    target=(DATA/'file_store'/key).resolve(); root=(DATA/'file_store').resolve()
    need(root==target or root in target.parents,'Invalid stored file.',500)
    try: target.unlink()
    except FileNotFoundError: pass

def upload_filename(value):
    need(isinstance(value,str),'Invalid file name.')
    value=unquote(value).replace('\\','/').split('/')[-1].strip()
    need(1<=len(value)<=180 and '\x00' not in value,'Invalid file name.')
    need(not any(ord(ch)<32 for ch in value),'Invalid file name.')
    suffix=Path(value).suffix.lower()
    need(suffix not in BLOCKED_UPLOAD_EXTENSIONS,'That file type is not allowed for safety.')
    return value

def normalize_resource_code(value):
    need(isinstance(value,str),'Enter an access code.')
    code=re.sub(r'[^A-Z0-9]','',value.upper())
    need(4<=len(code)<=16,'Enter a valid access code.')
    return code

def make_resource_code(c):
    for _ in range(50):
        code=''.join(secrets.choice(RESOURCE_CODE_ALPHABET) for _ in range(6))
        if not c.execute('SELECT 1 FROM resource_codes WHERE code=?',(code,)).fetchone(): return code
    raise APIError('Could not generate a unique code. Try again.',500)

def make_instant_meeting_code(c):
    for _ in range(100):
        code=f'{secrets.randbelow(10_000_000_000):010d}'
        if not c.execute('SELECT 1 FROM instant_meetings WHERE code=?',(code,)).fetchone():
            return code
    raise APIError('Could not generate a meeting code. Try again.',500)

def active_resource_codes_in_text(text):
    # Generated codes are six characters from an ambiguity-safe alphabet. Only
    # codes that currently exist and are active become classroom download links.
    candidates=[]
    for match in re.findall(r'(?<![A-Z0-9])([A-HJ-NP-Z2-9]{6})(?![A-Z0-9])',text.upper()):
        if match not in candidates: candidates.append(match)
    if not candidates: return []
    marks=','.join('?' for _ in candidates)
    with db() as c:
        rows=c.execute(f'SELECT code,label FROM resource_codes WHERE active=1 AND code IN ({marks})',candidates).fetchall()
    found={row['code']:row['label'] for row in rows}
    return [{'code':code,'label':found[code]} for code in candidates if code in found]


def clean_overlay_tokens():
    now=time.time()
    for key in list(OVERLAY_TOKENS):
        if OVERLAY_TOKENS[key]['expires']<now:
            del OVERLAY_TOKENS[key]

def credential_version(user):
    return hashlib.sha256(user['password'].encode()).hexdigest() if user['role']!='guest' else ''

def token_claims(user,sid):
    return {'uid':user['id'],'role':user['role'],'session':sid,
            'credential_version':credential_version(user)}

def revoke_tokens(session=None,uid=None):
    # Caller holds LOCK. Revocation includes handoffs not yet consumed.
    for tokens in (OVERLAY_TOKENS,TEACHER_APP_TOKENS,TEACHER_MEDIA_TOKENS):
        for key,item in list(tokens.items()):
            if (session is not None and item.get('session')==session) or (uid is not None and item.get('uid')==uid):
                tokens.pop(key,None)

def validate_token_user(item,c,cl,admin=False):
    """Recheck the issuing authorization, rather than trusting a saved role."""
    now=time.time()
    session=SESSIONS.get(item.get('session'))
    need(session and session['expires']>now,'Teacher or annotation authorization expired. Sign in again.',403)
    if item.get('role')=='guest':
        user=session.get('guest_identity')
    else:
        user=c.execute('SELECT * FROM users WHERE id=?',(session.get('user'),)).fetchone()
    need(user and user['id']==item['uid'] and user['role']==item['role']
         and hmac.compare_digest(credential_version(user),item.get('credential_version','')),
         'Teacher or annotation authorization expired. Sign in again.',403)
    if admin: need(user['role']=='admin','Admin access required.',403)
    if user['role']!='admin':
        access=session.get('instant_access',{}).get(str(cl['id']),{})
        instant=cl['class_kind']=='instant' and access.get('expires',0)>now
        booked=c.execute('SELECT 1 FROM bookings WHERE class_id=? AND user_id=?',(cl['id'],user['id'])).fetchone()
        need(instant or booked,'Class access is no longer available.',403)
    # Token activity keeps its issuing session alive, but never extends the
    # token's own absolute lifetime.
    session['last_seen']=now; session['expires']=now+28800
    return user

def overlay_token_access(token,require_live=True):
    need(isinstance(token,str) and 16<=len(token)<=160,'Invalid desktop annotation code.',403)
    with LOCK:
        clean_overlay_tokens(); item=OVERLAY_TOKENS.get(token)
        need(item,'Desktop annotation code expired. Generate a new one from the classroom.',403)
        cid=item['class_id']
        with db() as c:
            cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
            need(cl,'Class is unavailable.',404)
            validate_token_user(item,c,cl)
            if require_live:
                need(cl and cl['status']=='scheduled' and cl['live'],'This classroom is no longer open.',409)
        room=room_for(cid); clean_room(room)
        return item,room


def clean_teacher_app_tokens():
    now=time.time()
    for key in list(TEACHER_APP_TOKENS):
        if TEACHER_APP_TOKENS[key]['expires']<now:
            del TEACHER_APP_TOKENS[key]

def clean_teacher_media_tokens():
    now=time.time()
    for key in list(TEACHER_MEDIA_TOKENS):
        if TEACHER_MEDIA_TOKENS[key]['expires']<now:
            del TEACHER_MEDIA_TOKENS[key]

def make_teacher_media_token(app_token):
    item,room,cl=teacher_app_access(app_token,require_live=True)
    with LOCK:
        clean_teacher_media_tokens()
        token=secrets.token_urlsafe(32)
        TEACHER_MEDIA_TOKENS[token]={
            **{key:item[key] for key in ('uid','role','session','credential_version')},
            'class_id':item['class_id'],'expires':time.time()+90
        }
    return token,cl

def consume_teacher_media_token(token):
    need(isinstance(token,str) and 20<=len(token)<=160,'Teacher media link expired. Reopen the meeting from the Teacher App.',403)
    with LOCK:
        clean_teacher_media_tokens()
        item=TEACHER_MEDIA_TOKENS.pop(token,None)
    need(item,'Teacher media link expired. Reopen the meeting from the Teacher App.',403)
    with LOCK:
        with db() as c:
            cl=c.execute('SELECT * FROM classes WHERE id=?',(item['class_id'],)).fetchone()
            need(cl and cl['status']=='scheduled' and cl['live'],'This classroom is no longer open.',409)
            user=validate_token_user(item,c,cl,admin=True)
    return item,user,cl

def teacher_app_access(token,require_live=True):
    need(isinstance(token,str) and 24<=len(token)<=180,'Teacher app link expired. Open the meeting again from Admin.',403)
    with LOCK:
        clean_teacher_app_tokens(); item=TEACHER_APP_TOKENS.get(token)
        need(item,'Teacher app link expired. Open the meeting again from Admin.',403)
        cid=item['class_id']
        with db() as c:
            cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
            need(cl and cl['status']!='cancelled','This class is unavailable.',404)
            validate_token_user(item,c,cl,admin=True)
        if require_live:
            need(cl['status']=='scheduled' and cl['live'],'This classroom is no longer open.',409)
        room=room_for(cid); clean_room(room)
        return item,room,cl

def read_json_request(handler,max_bytes=600000):
    need(not handler.headers.get('Transfer-Encoding'),'Unsupported request.')
    need(handler.headers.get_content_type()=='application/json','Expected JSON.',415)
    try: length=int(handler.headers.get('Content-Length','0'))
    except ValueError: raise APIError('Invalid request length.')
    need(0<length<=max_bytes,'Request too large.',413)
    try: data=json.loads(handler.rfile.read(length))
    except (ValueError,UnicodeError): raise APIError('Invalid JSON.')
    need(isinstance(data,dict),'Expected an object.')
    return data

def clean_resource_grants():
    now=time.time()
    for key in list(RESOURCE_GRANTS):
        if RESOURCE_GRANTS[key]['expires']<now: del RESOURCE_GRANTS[key]

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup(); self.connection.settimeout(15)

    def log_message(self,fmt,*args):
        # Do not log query strings containing private classroom peer IDs.
        pass

    def send(self,payload,status=200,mime='application/json; charset=utf-8'):
        data=json.dumps(payload,ensure_ascii=False).encode() if mime.startswith('application/json') else payload
        self.send_response(status)
        self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin'); self.send_header('X-Frame-Options','DENY')
        # Be explicit about the browser capabilities MathStudio needs.  This
        # does not make HTTP secure; it simply ensures a secure MathStudio
        # origin is allowed to use its own camera, microphone and display-capture APIs.
        self.send_header('Permissions-Policy','camera=(self), microphone=(self), display-capture=(self)')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if getattr(self,'sid',None):
            secure='; Secure' if self.headers.get('X-Forwarded-Proto','').lower()=='https' else ''
            self.send_header('Set-Cookie',f'{COOKIE}={self.sid}; Path=/; HttpOnly; SameSite=Strict{secure}')
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError): pass

    def send_download(self,data,filename,mime='application/octet-stream',inline=False):
        disposition='inline' if inline else 'attachment'
        safe_ascii=re.sub(r'[^A-Za-z0-9._ -]','_',filename)[:140] or 'download'
        self.send_response(200)
        self.send_header('Content-Type',mime or 'application/octet-stream')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Content-Disposition',f"{disposition}; filename=\"{safe_ascii}\"; filename*=UTF-8''{quote(filename)}")
        self.send_header('Cache-Control','private, no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Permissions-Policy','camera=(self), microphone=(self), display-capture=(self)')
        if getattr(self,'sid',None):
            secure='; Secure' if self.headers.get('X-Forwarded-Proto','').lower()=='https' else ''
            self.send_header('Set-Cookie',f'{COOKIE}={self.sid}; Path=/; HttpOnly; SameSite=Strict{secure}')
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError): pass

    def send_redirect(self,location,status=302):
        self.send_response(status)
        self.send_header('Location',location)
        self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        if getattr(self,'sid',None):
            secure='; Secure' if self.headers.get('X-Forwarded-Proto','').lower()=='https' else ''
            self.send_header('Set-Cookie',f'{COOKIE}={self.sid}; Path=/; HttpOnly; SameSite=Strict{secure}')
        self.send_header('Content-Length','0')
        self.end_headers()

    def resource_grant(self):
        grant=self.query.get('grant',[''])[0]
        with LOCK:
            clean_resource_grants(); item=RESOURCE_GRANTS.get(grant)
            need(item and item['session']==self.sid,'This download link expired. Enter the access code again.',403)
            item['expires']=time.time()+1800
            return item

    def handle_resource_download(self,path):
        grant=self.resource_grant(); code_id=grant['code_id']
        if path=='/resource/download-all':
            with db() as c:
                code=c.execute('SELECT * FROM resource_codes WHERE id=? AND active=1',(code_id,)).fetchone()
                need(code,'This access code is no longer active.',403)
                rows=c.execute('''SELECT f.* FROM stored_files f JOIN resource_code_files m ON m.file_id=f.id
                                  WHERE m.code_id=? ORDER BY m.position,f.id''',(code_id,)).fetchall()
            need(rows,'There are no files attached to this code.',404)
            need(sum(r['size'] for r in rows)<=250*1024*1024,'This bundle is too large to create as one ZIP. Download the files individually.',413)
            out=io.BytesIO(); used={}
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for row in rows:
                    name=row['original_name']; base,ext=os.path.splitext(name); n=used.get(name,0)+1; used[name]=n
                    archive_name=name if n==1 else f'{base} ({n}){ext}'
                    z.writestr(archive_name,storage_get(row['storage_key'],row['storage_backend']))
            label=re.sub(r'[\\/:*?"<>|]+','-',code['label']).strip() or 'MathStudio files'
            self.send_download(out.getvalue(),label+'.zip','application/zip'); return
        try: file_id=int(self.query.get('file',['0'])[0])
        except ValueError: raise APIError('Invalid file.',400)
        with db() as c:
            row=c.execute('''SELECT f.* FROM stored_files f JOIN resource_code_files m ON m.file_id=f.id
                             JOIN resource_codes rc ON rc.id=m.code_id
                             WHERE f.id=? AND m.code_id=? AND rc.active=1''',(file_id,code_id)).fetchone()
        need(row,'File not found for this access code.',404)
        inline=path=='/resource/open' and any(row['mime'].startswith(x) for x in INLINE_MIME_PREFIXES)
        self.send_download(storage_get(row['storage_key'],row['storage_backend']),row['original_name'],row['mime'],inline=inline)

    def handle_file_upload(self):
        self.require_user(True)
        need(hmac.compare_digest(self.headers.get('X-CSRF-Token','').encode(),self.session['csrf'].encode()),'Form expired. Refresh and try again.',403)
        need(not self.headers.get('Transfer-Encoding'),'Unsupported request.')
        need(self.headers.get_content_type()=='application/octet-stream','Expected a file upload.',415)
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise APIError('Invalid upload size.')
        max_mb=max(1,min(int(os.environ.get('MATH_MAX_UPLOAD_MB','100')),500))
        need(0<length<=max_mb*1024*1024,f'Each file must be {max_mb} MB or smaller.',413)
        name=upload_filename(self.headers.get('X-File-Name',''))
        supplied_mime=unquote(self.headers.get('X-File-Type','')).strip()[:120]
        if not re.fullmatch(r'[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+',supplied_mime): supplied_mime=''
        mime=(mimetypes.guess_type(name)[0] or supplied_mime or 'application/octet-stream')
        data=self.rfile.read(length); need(len(data)==length,'Upload was interrupted. Try again.',400)
        ext=Path(name).suffix.lower()[:16]
        key=datetime.now(timezone.utc).strftime('%Y/%m/')+secrets.token_hex(18)+ext
        backend=storage_put(key,data,mime)
        try:
            with db() as c:
                r=c.execute('''INSERT INTO stored_files(original_name,storage_key,storage_backend,mime,size,created,uploaded_by)
                               VALUES (?,?,?,?,?,?,?)''',(name,key,backend,mime,length,time.time(),self.user['id']))
                file_id=r.lastrowid
        except Exception:
            storage_delete(key,backend); raise
        return {'ok':True,'file':{'id':file_id,'name':name,'size':length,'mime':mime,'backend':backend}}

    def prepare(self):
        self.sid=None
        self.session={'user':None,'csrf':secrets.token_hex(32)}
        self.path_only=urlsplit(self.path).path
        self.query=parse_qs(urlsplit(self.path).query)
        # Accept localhost and, when intentionally listening on the LAN, private/local
        # IP-literal Host headers on this server port. Domain names are still rejected
        # unless PUBLIC_ORIGIN explicitly allowlists one, which keeps the basic
        # DNS-rebinding protection while allowing phones/tablets to use 192.168.x.x,
        # 10.x.x.x, or 172.16-31.x.x addresses.
        raw_host=self.headers.get('Host','').strip().lower()
        allowed=False
        public_origin=current_public_origin()
        if public_origin and raw_host==urlsplit(public_origin).netloc.lower():
            allowed=True
        else:
            try:
                # urlsplit handles IPv4, hostnames, and bracketed IPv6 correctly.
                parsed=urlsplit('//' + raw_host)
                hostname=(parsed.hostname or '').lower()
                port=parsed.port or (443 if public_origin.startswith('https://') else 80)
                if port==self.server.server_port and hostname in ('localhost','127.0.0.1','::1'):
                    allowed=True
                elif port==self.server.server_port and BIND in ('0.0.0.0','::',''):
                    try:
                        ip=ipaddress.ip_address(hostname)
                        allowed=ip.is_private or ip.is_loopback or ip.is_link_local
                    except ValueError:
                        allowed=False
            except ValueError:
                allowed=False
        need(allowed,'Invalid host.',400)
        cookies=SimpleCookie()
        try: cookies.load(self.headers.get('Cookie',''))
        except CookieError: pass
        sid=cookies[COOKIE].value if COOKIE in cookies else ''
        now=time.time()
        with LOCK:
            for key in list(SESSIONS):
                if SESSIONS[key]['expires']<now:
                    del SESSIONS[key]; revoke_tokens(session=key)
            if sid in SESSIONS:
                self.sid=sid; self.session=SESSIONS[sid]
                self.session['last_seen']=now
                self.session['expires']=now+(28800 if self.session.get('user') or self.session.get('guest_identity') else ANON_SESSION_IDLE_SECONDS)
        # Only the explicit browser/native-dashboard bootstrap allocates an
        # anonymous session. Existing cookies are still honored on every route.
        if self.command=='GET' and self.path_only=='/api/me' and self.sid is None:
            limit_requests([('session:'+self.client_ip(),30,60),('session-global',300,60)],
                           'Too many sessions. Try again later.')
            with LOCK:
                session_capacity(anonymous=True)
                self.sid=secrets.token_hex(32)
                self.session={'user':None,'csrf':secrets.token_hex(32),
                              'expires':now+ANON_SESSION_IDLE_SECONDS,'last_seen':now}
                SESSIONS[self.sid]=self.session
        with db() as c:
            self.user=c.execute('SELECT * FROM users WHERE id=?',(self.session.get('user'),)).fetchone() if self.session.get('user') else None
        if self.user is None and isinstance(self.session.get('guest_identity'),dict):
            guest=self.session['guest_identity']
            self.user={'id':guest.get('id'),'username':'guest','name':guest.get('name','Guest'),'role':'guest'}

    def require_user(self,admin=False):
        need(self.user is not None,'Please log in.',401)
        if admin: need(self.user['role']=='admin','Admin access required.',403)

    def client_ip(self):
        peer=ipaddress.ip_address(self.client_address[0])
        # Only a configured connector may supply Cloudflare's single-client IP.
        # X-Forwarded-For is deliberately not accepted as an arbitrary chain.
        for network in os.environ.get('MATH_TRUSTED_PROXIES','').split(','):
            try: trusted=peer in ipaddress.ip_network(network.strip())
            except ValueError: continue
            if trusted:
                try: return str(ipaddress.ip_address(self.headers.get('CF-Connecting-IP','')))
                except ValueError: break
        return str(peer)

    def limit_auth(self,username,signup=False):
        limits=[('auth-account:'+username,10,300),
                ('auth-client:'+self.client_ip(),60,300),('auth-global',600,300)]
        if signup: limits.append(('signup:'+self.client_ip(),10,300))
        limit_requests(limits,'Too many attempts. Wait five minutes.')

    def limit_resource_code(self):
        limit_requests([('resource:'+self.client_ip(),30,300),('resource-global',600,300)],
                       'Too many access-code attempts. Wait five minutes.')

    def limit_meeting_code(self):
        limit_requests([('meeting:'+self.client_ip(),30,60),('meeting-global',300,60)],
                       'Too many meeting-code attempts. Try again later.')

    def rotate(self,user_id,transfer_tokens=False):
        with LOCK:
            old_sid=self.sid
            if old_sid not in SESSIONS: session_capacity()
            SESSIONS.pop(old_sid,None); self.sid=secrets.token_hex(32)
            now=time.time()
            self.session={'user':user_id,'csrf':secrets.token_hex(32),'last_seen':now,
                          'expires':now+(28800 if user_id else ANON_SESSION_IDLE_SECONDS)}
            SESSIONS[self.sid]=self.session
            if transfer_tokens:
                for tokens in (OVERLAY_TOKENS,TEACHER_APP_TOKENS,TEACHER_MEDIA_TOKENS):
                    for item in tokens.values():
                        if item.get('session')==old_sid: item['session']=self.sid
            else:
                revoke_tokens(session=old_sid)

    def room_access(self,class_id,live=True):
        self.require_user()
        with db() as c:
            cl=c.execute('SELECT * FROM classes WHERE id=?',(class_id,)).fetchone()
            need(cl and cl['status']!='cancelled','Class is unavailable.',404)
            need(cl['approval']=='confirmed','This booking is still waiting for teacher confirmation.',409)
            instant_access=str(class_id) in self.session.get('instant_access',{}) and cl['class_kind']=='instant'
            booked=None if instant_access else c.execute('SELECT 1 FROM bookings WHERE class_id=? AND user_id=?',(class_id,self.user['id'])).fetchone()
            need(self.user['role']=='admin' or booked or instant_access,'Book this class or enter its meeting code before joining.',403)
            if live:
                if cl['class_kind']=='instant':
                    instant=c.execute('SELECT active,expires FROM instant_meetings WHERE class_id=? LIMIT 1',(class_id,)).fetchone()
                    need(instant and instant['active'] and instant['expires']>time.time(),'This instant meeting has ended or expired.',409)
                    # An active share code itself means the instant classroom is open.
                    if not cl['live']:
                        c.execute('UPDATE classes SET live=1 WHERE id=?',(class_id,))
                        cl=c.execute('SELECT * FROM classes WHERE id=?',(class_id,)).fetchone()
                else:
                    need(cl['live'],'The teacher has not opened this classroom, or the class has ended.',409)
        return cl

    def group_access(self,group_id):
        self.require_user()
        with db() as c:
            group=c.execute('SELECT * FROM group_chats WHERE id=?',(group_id,)).fetchone()
            need(group,'Group chat not found.',404)
            if self.user['role']!='admin':
                need(c.execute('SELECT 1 FROM group_chat_members WHERE group_id=? AND user_id=?',(group_id,self.user['id'])).fetchone(),
                     'You are not a member of this group chat.',403)
        return group

    def owned_peer(self,room,peer):
        need(isinstance(peer,str),'Invalid participant')
        p=room['peers'].get(peer)
        need(p and p['uid']==self.user['id'] and p['session']==self.sid,'Your classroom connection expired. Rejoin the room.',409)
        p['seen']=time.time()
        return p

    def do_GET(self): self.handle_api(False)
    def do_POST(self): self.handle_api(True)

    def handle_api(self,post):
        try:
            # When the HTTPS launcher is active, a user may accidentally type the
            # LAN IP (http://10.x/192.168.x). Top-level GET navigations are sent
            # straight to the secure public origin so browser media APIs are not
            # silently disabled by an insecure origin. API/background requests are
            # never redirected here.
            public_origin=current_public_origin()
            if not post and public_origin.startswith('https://'):
                raw_host=self.headers.get('Host','').strip().lower()
                public_host=urlsplit(public_origin).netloc.lower()
                if raw_host and raw_host!=public_host and self.headers.get('Sec-Fetch-Mode','')=='navigate':
                    target=public_origin+self.path
                    self.send_response(302)
                    self.send_header('Location',target)
                    self.send_header('Cache-Control','no-store')
                    self.send_header('Content-Length','0')
                    self.end_headers()
                    return
            self.prepare()
            if not post and self.path_only=='/teacher-media-login':
                token=self.query.get('token',[''])[0]
                with LOCK:
                    item,user,cl=consume_teacher_media_token(token)
                    self.rotate(user['id'],transfer_tokens=self.sid==item['session'])
                self.send_redirect(f"/classroom?id={item['class_id']}&teacherhost=1&autojoin=1")
                return
            data={}
            if post and self.path_only=='/api/admin/files/upload':
                self.send(self.handle_file_upload()); return
            if post and self.path_only=='/api/overlay/board':
                need(not self.headers.get('Transfer-Encoding'),'Unsupported request.')
                need(self.headers.get_content_type()=='application/json','Expected JSON.',415)
                try: length=int(self.headers.get('Content-Length','0'))
                except ValueError: raise APIError('Invalid request length.')
                need(0<length<=600000,'Request too large.',413)
                try: overlay_data=json.loads(self.rfile.read(length))
                except (ValueError,UnicodeError): raise APIError('Invalid JSON.')
                need(isinstance(overlay_data,dict),'Expected an object.')
                token=overlay_data.get('token',''); item,room=overlay_token_access(token)
                need(item['role']=='admin' or room['drawing'],'The teacher has not enabled student drawing.',403)
                board=valid_board(overlay_data.get('board'))
                version=int(number(overlay_data,'version',0,1e12))
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    old=c.execute('SELECT version FROM boards WHERE class_id=?',(item['class_id'],)).fetchone()
                    need(version==(old['version'] if old else 0),'The annotations changed. Refresh and try again.',409)
                    c.execute('INSERT OR REPLACE INTO boards VALUES (?,?,?)',(item['class_id'],version+1,json.dumps(board)))
                self.send({'version':version+1}); return
            if post and self.path_only=='/api/teacher-app/screen-frame':
                token=self.headers.get('X-Teacher-Token','')
                item,room,cl=teacher_app_access(token,require_live=True)
                need(self.headers.get_content_type()=='image/jpeg','Expected JPEG frame.',415)
                try: length=int(self.headers.get('Content-Length','0'))
                except ValueError: raise APIError('Invalid frame length.')
                need(0<length<=900000,'Screen frame too large.',413)
                frame=self.rfile.read(length)
                need(frame.startswith(b'\xff\xd8'),'Invalid JPEG frame.',400)
                native=room.setdefault('native_screen',{'active':False,'seq':0,'jpeg':b'','at':0.0})
                need(native.get('active'),'Screen sharing is not active.',409)
                native['seq']=int(native.get('seq',0))+1
                native['jpeg']=frame
                native['at']=time.time()
                self.send({'ok':True,'seq':native['seq']}); return
            if post and self.path_only in ('/api/teacher-app/board','/api/teacher-app/permissions','/api/teacher-app/end','/api/teacher-app/media-command','/api/teacher-app/screen'):
                app_data=read_json_request(self)
                token=app_data.get('token','')
                require_live=self.path_only!='/api/teacher-app/end'
                item,room,cl=teacher_app_access(token,require_live=require_live)
                if self.path_only=='/api/teacher-app/board':
                    board=valid_board(app_data.get('board'))
                    version=int(number(app_data,'version',0,1e12))
                    with db() as c:
                        c.execute('BEGIN IMMEDIATE')
                        old=c.execute('SELECT version FROM boards WHERE class_id=?',(item['class_id'],)).fetchone()
                        need(version==(old['version'] if old else 0),'The annotations changed. Refresh and try again.',409)
                        c.execute('INSERT OR REPLACE INTO boards VALUES (?,?,?)',(item['class_id'],version+1,json.dumps(board)))
                    self.send({'version':version+1}); return
                if self.path_only=='/api/teacher-app/permissions':
                    room['drawing']=bool(app_data.get('drawing'))
                    self.send({'ok':True,'drawing':bool(room['drawing'])}); return
                if self.path_only=='/api/teacher-app/media-command':
                    command=str(app_data.get('command','')).strip().lower()
                    need(command in ('mic-toggle','camera-toggle'),'Invalid media command.')
                    room['teacher_command_seq']=int(room.get('teacher_command_seq',0))+1
                    seq=room['teacher_command_seq']
                    room.setdefault('teacher_commands',[]).append({'seq':seq,'command':command,'at':time.time()})
                    room['teacher_commands'][:]=room['teacher_commands'][-50:]
                    self.send({'ok':True,'seq':seq}); return
                if self.path_only=='/api/teacher-app/screen':
                    active=bool(app_data.get('active'))
                    native=room.setdefault('native_screen',{'active':False,'seq':0,'jpeg':b'','at':0.0})
                    native['active']=active
                    native['seq']=int(native.get('seq',0))+1
                    native['at']=time.time()
                    if not active: native['jpeg']=b''
                    self.send({'ok':True,'active':active,'seq':native['seq']}); return
                if self.path_only=='/api/teacher-app/end':
                    with LOCK:
                        with db() as c:
                            current=c.execute('SELECT * FROM classes WHERE id=?',(item['class_id'],)).fetchone()
                            need(current and current['status']=='scheduled','Classroom is already closed.',409)
                            c.execute("UPDATE classes SET live=0,status='completed' WHERE id=?",(item['class_id'],))
                            c.execute('UPDATE instant_meetings SET active=0 WHERE class_id=?',(item['class_id'],))
                        ROOMS.pop(item['class_id'],None)
                    self.send({'ok':True}); return
            if post:
                need(not self.headers.get('Transfer-Encoding'),'Unsupported request.')
                need(hmac.compare_digest(self.headers.get('X-CSRF-Token','').encode(),self.session['csrf'].encode()),'Form expired. Refresh and try again.',403)
                need(self.headers.get_content_type()=='application/json','Expected JSON.',415)
                try: length=int(self.headers.get('Content-Length','0'))
                except ValueError: raise APIError('Invalid request length.')
                need(0<length<=600000,'Request too large.',413)
                try: data=json.loads(self.rfile.read(length))
                except (ValueError,UnicodeError): raise APIError('Invalid JSON.')
                need(isinstance(data,dict),'Expected an object.')
            result=self.post_api(data) if post else self.get_api()
            if result is not None: self.send(result)
        except APIError as ex: self.send({'error':ex.message},ex.status)
        except (sqlite3.Error,OSError) as ex:
            print('Server error:',type(ex).__name__,str(ex)); self.send({'error':'Could not complete the request. Please retry.'},500)
        except Exception as ex:
            print('Unexpected server error:',type(ex).__name__,str(ex)); self.send({'error':'Unexpected server error. Please retry.'},500)

    def get_api(self):
        path=self.path_only
        if path=='/api/desktop-info': return {'build':'v41.6.6-release-candidate','port':PORT,'public_origin':current_public_origin(),'lan_origin':f'http://{self.server.server_address[0] if self.server.server_address[0] not in ("0.0.0.0","::") else "127.0.0.1"}:{PORT}','cloudflare_turn_configured':bool(os.environ.get('CLOUDFLARE_TURN_KEY_ID','').strip() and os.environ.get('CLOUDFLARE_TURN_API_TOKEN','').strip())}
        if path=='/api/me': return {'user':public_user(self.user),'csrf':self.session['csrf']}
        if path=='/api/public':
            with db() as c:
                settings={r['key']:r['value'] for r in c.execute('SELECT * FROM settings') if r['key'] in DEFAULTS}
                posts=[dict(r) for r in c.execute('SELECT * FROM posts ORDER BY id DESC LIMIT 30')]
            return {'settings':settings,'posts':posts}
        if path=='/api/instant/info':
            self.limit_meeting_code()
            code=re.sub(r'\D','',self.query.get('code',[''])[0])
            need(len(code)==10,'Enter a 10-digit meeting code.',400)
            with db() as c:
                item=c.execute('''SELECT i.code,i.expires,i.active,cl.id AS class_id,cl.title,cl.live,cl.status
                    FROM instant_meetings i JOIN classes cl ON cl.id=i.class_id WHERE i.code=?''',(code,)).fetchone()
            need(item and item['active'] and item['expires']>time.time() and item['status']=='scheduled','Meeting code is invalid or expired.',404)
            if not item['live']:
                with db() as c: c.execute('UPDATE classes SET live=1 WHERE id=?',(item['class_id'],))
            return {'code':code,'class_id':item['class_id'],'title':item['title'],'live':True}
        if path=='/api/classes':
            with db() as c:
                rows=c.execute('''SELECT classes.*, (SELECT count(*) FROM bookings b WHERE b.class_id=classes.id) AS booked,
                  EXISTS(SELECT 1 FROM bookings b WHERE b.class_id=classes.id AND b.user_id=?) AS mine,
                  COALESCE(classes.group_price_label,lesson_types.price_label,'') AS price_label
                  FROM classes LEFT JOIN lesson_types ON lesson_types.id=classes.lesson_type_id ORDER BY start''',(self.user['id'] if self.user else -1,)).fetchall()
            if self.user and self.user['role']=='admin':
                return {'classes':[dict(r) for r in rows]}
            # Public catalog records must not disclose private lessons or internal
            # ownership/series metadata. Admitted guests still need their class
            # record to bootstrap the existing browser classroom.
            visible=[]; now=time.time()
            fields=('id','title','track','description','start','minutes','capacity',
                    'status','live','approval','class_kind','booked','mine','price_label')
            for row in rows:
                public_group=(row['class_kind']=='group' and row['status']=='scheduled'
                              and row['approval']=='confirmed' and row['start']>now)
                access=self.session.get('instant_access',{}).get(str(row['id']),{})
                admitted=(row['class_kind']=='instant' and row['status']=='scheduled'
                          and access.get('expires',0)>now)
                if not (row['mine'] or public_group or admitted): continue
                item={key:row[key] for key in fields}
                if row['mine']: item['group_chat_id']=row['group_chat_id']
                visible.append(item)
            return {'classes':visible}
        if path=='/api/schedule':
            now=time.time(); horizon=now+70*86400
            with db() as c:
                lessons=[dict(r) for r in c.execute("SELECT * FROM lesson_types WHERE active=1 ORDER BY name,minutes")]
                availability=[dict(r) for r in c.execute("SELECT * FROM availability WHERE status='open' AND end>? AND start<? ORDER BY start",(now,horizon))]
                busy=[dict(r) for r in c.execute("SELECT id,start,minutes,approval,status FROM classes WHERE status='scheduled' AND approval IN ('pending','confirmed') AND start<? AND start+minutes*60>? ORDER BY start",(horizon,now))]
            return {'lesson_types':lessons,'availability':availability,'busy':busy}
        if path in ('/resource/download','/resource/open','/resource/download-all'):
            self.handle_resource_download(path); return None
        if path=='/api/overlay/state':
            token=self.query.get('token',[''])[0]
            item,room=overlay_token_access(token)
            with db() as c:
                board=c.execute('SELECT * FROM boards WHERE class_id=?',(item['class_id'],)).fetchone()
                cl=c.execute('SELECT title FROM classes WHERE id=?',(item['class_id'],)).fetchone()
            return {'class_id':item['class_id'],'title':cl['title'] if cl else 'MathStudio classroom',
                    'can_draw':bool(item['role']=='admin' or room['drawing']),
                    'version':board['version'] if board else 0,
                    'board':json.loads(board['content']) if board else {'background':'blank','shapes':[]}}
        if path=='/api/teacher-app/state':
            token=self.query.get('token',[''])[0]
            item,room,cl=teacher_app_access(token,require_live=False)
            with db() as c:
                board=c.execute('SELECT * FROM boards WHERE class_id=?',(item['class_id'],)).fetchone()
                attendees=[dict(r) for r in c.execute('''SELECT u.id,u.name,u.username,u.role FROM bookings b
                    JOIN users u ON u.id=b.user_id WHERE b.class_id=? ORDER BY u.name''',(item['class_id'],)).fetchall()]
            connected=[]
            for peer_id,p in room['peers'].items():
                connected.append({'peer':peer_id,'uid':p['uid'],'name':p['name'],'role':p['role'],
                                  'mic_on':bool(p.get('mic_on')),'camera_on':bool(p.get('camera_on')),
                                  'forced_mute':bool(p.get('forced_mute'))})
            return {'class':{'id':cl['id'],'title':cl['title'],'start':cl['start'],'minutes':cl['minutes'],
                             'live':bool(cl['live']),'status':cl['status'],'class_kind':cl['class_kind']},
                    'drawing':bool(room['drawing']),'version':board['version'] if board else 0,
                    'board':json.loads(board['content']) if board else {'background':'blank','shapes':[]},
                    'attendees':attendees,'connected':connected,'presenter':room.get('presenter'),
                    'native_screen':{'active':bool(room.get('native_screen',{}).get('active')),
                                     'seq':int(room.get('native_screen',{}).get('seq',0)),
                                     'at':float(room.get('native_screen',{}).get('at',0.0))}}
        if path=='/api/admin/files':
            self.require_user(True)
            with db() as c:
                files=[dict(r) for r in c.execute('''SELECT f.id,f.original_name AS name,f.mime,f.size,f.created,f.storage_backend AS backend,
                    (SELECT count(*) FROM resource_code_files m WHERE m.file_id=f.id) AS code_count
                    FROM stored_files f ORDER BY f.created DESC''')]
                codes=[]
                for row in c.execute('SELECT * FROM resource_codes ORDER BY created DESC').fetchall():
                    item=dict(row)
                    item['files']=[dict(x) for x in c.execute('''SELECT f.id,f.original_name AS name,f.size,f.mime FROM stored_files f
                        JOIN resource_code_files m ON m.file_id=f.id WHERE m.code_id=? ORDER BY m.position,f.id''',(row['id'],))]
                    codes.append(item)
            cfg=storage_config()
            return {'files':files,'codes':codes,'storage':{'backend':cfg['backend'],'label':cfg['label'],'cloud':cfg['cloud']},
                    'max_upload_mb':max(1,min(int(os.environ.get('MATH_MAX_UPLOAD_MB','100')),500))}
        if path=='/api/admin':
            self.require_user(True)
            with db() as c:
                users=[]
                for r in c.execute('SELECT * FROM users ORDER BY name').fetchall():
                    item=public_user(r)
                    item['booking_count']=c.execute('SELECT count(*) FROM bookings WHERE user_id=?',(r['id'],)).fetchone()[0]
                    item['group_count']=c.execute('SELECT count(*) FROM group_chat_members WHERE user_id=?',(r['id'],)).fetchone()[0]
                    users.append(item)
                bookings=[dict(r) for r in c.execute('''SELECT b.id,b.class_id,u.name,u.username,cl.title,cl.start,cl.minutes,cl.approval,cl.status,
                  cl.series_id,cl.availability_id,cl.class_kind,cl.capacity,cl.group_chat_id,
                  COALESCE(cl.group_price_label,lt.price_label,'Price TBD') AS price_label
                  FROM bookings b JOIN users u ON u.id=b.user_id JOIN classes cl ON cl.id=b.class_id
                  LEFT JOIN lesson_types lt ON lt.id=cl.lesson_type_id ORDER BY cl.start''')]
                groups=[]
                for r in c.execute('''SELECT g.*,
                    (SELECT count(*) FROM group_chat_members m WHERE m.group_id=g.id) AS member_count,
                    (SELECT count(*) FROM classes cl WHERE cl.group_chat_id=g.id) AS linked_class_count
                    FROM group_chats g ORDER BY g.created DESC''').fetchall():
                    item=dict(r)
                    item['members']=[public_user(x) for x in c.execute('''SELECT u.* FROM users u JOIN group_chat_members m ON m.user_id=u.id
                        WHERE m.group_id=? ORDER BY u.name''',(r['id'],)).fetchall()]
                    groups.append(item)
                calendar_classes=[]
                for r in c.execute('''SELECT cl.*, COALESCE(cl.group_price_label,lt.price_label,'Price TBD') AS price_label,
                    (SELECT count(*) FROM bookings b WHERE b.class_id=cl.id) AS booked
                    FROM classes cl LEFT JOIN lesson_types lt ON lt.id=cl.lesson_type_id
                    WHERE cl.status='scheduled' ORDER BY cl.start''').fetchall():
                    item=dict(r)
                    attendees=c.execute('''SELECT u.id,u.name,u.username FROM users u JOIN bookings b ON b.user_id=u.id
                        WHERE b.class_id=? ORDER BY u.name''',(r['id'],)).fetchall()
                    item['attendees']=[dict(x) for x in attendees]
                    item['name']=', '.join(x['name'] for x in attendees)
                    instant=c.execute('SELECT code,active,expires FROM instant_meetings WHERE class_id=?',(r['id'],)).fetchone()
                    item['share_code']=instant['code'] if instant and instant['active'] and instant['expires']>time.time() else ''
                    calendar_classes.append(item)
            return {'users':users,'bookings':bookings,'groups':groups,'calendar_classes':calendar_classes}
        if path=='/api/groups':
            self.require_user()
            with db() as c:
                if self.user['role']=='admin':
                    rows=c.execute('SELECT * FROM group_chats ORDER BY created DESC').fetchall()
                else:
                    rows=c.execute('''SELECT g.* FROM group_chats g JOIN group_chat_members m ON m.group_id=g.id
                        WHERE m.user_id=? ORDER BY g.created DESC''',(self.user['id'],)).fetchall()
                groups=[]
                for row in rows:
                    item=dict(row)
                    item['members']=[public_user(x) for x in c.execute('''SELECT u.* FROM users u JOIN group_chat_members m ON m.user_id=u.id
                        WHERE m.group_id=? ORDER BY u.name''',(row['id'],)).fetchall()]
                    item['member_count']=len(item['members'])
                    groups.append(item)
            return {'groups':groups}
        if path=='/api/group-messages':
            try:
                gid=int(self.query.get('group',['0'])[0]); since=int(self.query.get('since',['0'])[0])
            except ValueError: raise APIError('Invalid group chat.')
            group=self.group_access(gid)
            with db() as c:
                rows=c.execute('''SELECT m.id,m.text,m.created AS at,u.name,u.role,u.id AS uid
                    FROM group_messages m JOIN users u ON u.id=m.user_id
                    WHERE m.group_id=? AND m.id>? ORDER BY m.id LIMIT 300''',(gid,max(0,since))).fetchall()
            messages=[]
            for row in rows:
                item=dict(row); item['codes']=active_resource_codes_in_text(item['text']); messages.append(item)
            return {'group':{'id':group['id'],'name':group['name']},'messages':messages,
                    'seq':messages[-1]['id'] if messages else max(0,since)}
        if path=='/api/messages':
            try:
                cid=int(self.query.get('class',['0'])[0]); since=int(self.query.get('since',['0'])[0])
            except ValueError: raise APIError('Invalid class chat.')
            cl=self.room_access(cid,live=False)
            with db() as c:
                rows=c.execute('''SELECT m.id,m.text,m.created AS at,u.name,u.role,u.id AS uid
                    FROM class_messages m JOIN users u ON u.id=m.user_id
                    WHERE m.class_id=? AND m.id>? ORDER BY m.id LIMIT 300''',(cid,max(0,since))).fetchall()
            messages=[]
            for row in rows:
                item=dict(row); item['codes']=active_resource_codes_in_text(item['text']); messages.append(item)
            return {'class':{'id':cl['id'],'title':cl['title'],'start':cl['start'],'minutes':cl['minutes']},
                    'messages':messages,'seq':messages[-1]['id'] if messages else max(0,since)}
        if path=='/api/room/poll':
            try:
                cid=int(self.query.get('class',['0'])[0]); since=int(self.query.get('since',['0'])[0])
                chat_since=int(self.query.get('chat_since',['0'])[0])
                command_since=int(self.query.get('command_since',['0'])[0])
            except ValueError: raise APIError('Invalid room.')
            self.room_access(cid)
            with LOCK:
                room=room_for(cid); clean_room(room)
                peer=self.query.get('peer',[''])[0]; self.owned_peer(room,peer)
                peers=[{'id':key,'name':p['name'],'role':p['role'],'mic_on':bool(p.get('mic_on')),'camera_on':bool(p.get('camera_on')),'forced_mute':bool(p.get('forced_mute'))} for key,p in room['peers'].items()]
                events=[x for x in room['events'] if x['seq']>since and x['to']==peer]
                messages=[x for x in room['messages'] if x['id']>chat_since]
                current_peer=room['peers'][peer]
                commands=[]
                if current_peer.get('role')=='admin':
                    commands=[x for x in room.get('teacher_commands',[]) if int(x.get('seq',0))>command_since]
                native=room.get('native_screen') or {'active':False,'seq':0,'at':0.0}
                with db() as c: board=c.execute('SELECT * FROM boards WHERE class_id=?',(cid,)).fetchone()
                return {'peers':peers,'events':events,'seq':room['seq'],'drawing':room['drawing'],
                        'presenter':room['presenter'],'forcedMute':bool(current_peer.get('forced_mute')),
                        'chat':messages,'chatSeq':room['chat_seq'],
                        'teacherCommands':commands,'teacherCommandSeq':int(room.get('teacher_command_seq',0)),
                        'nativeShare':{'active':bool(native.get('active')),'seq':int(native.get('seq',0)),'at':float(native.get('at',0.0))},
                        'version':board['version'] if board else 0,
                        'board':json.loads(board['content']) if board else {'background':'grid','shapes':[]}}
        if path=='/api/native-screen':
            try: cid=int(self.query.get('class',['0'])[0])
            except ValueError: raise APIError('Invalid classroom.',400)
            self.room_access(cid)
            with LOCK:
                room=room_for(cid); clean_room(room)
                native=room.get('native_screen') or {}
                frame=native.get('jpeg') or b''
                active=bool(native.get('active'))
            need(active and frame,'No native screen frame is available.',404)
            self.send(frame,mime='image/jpeg'); return None
        if path.startswith('/api/'): raise APIError('Not found.',404)
        files={'/':'index.html','/app.js':'app.js','/diagnostics.js':'diagnostics.js','/classroom.js':'classroom.js','/style.css':'style.css','/favicon.svg':'favicon.svg'}
        if path not in files and path in ('/booking','/login','/signup','/account','/classroom','/resources','/messages','/join'): path='/'
        need(path in files,'Page not found.',404)
        f=ROOT/files[path]; mime=mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
        if f.suffix=='.js': mime='text/javascript'
        self.send(f.read_bytes(),mime=mime+'; charset=utf-8')

    def post_api(self,d):
        path=self.path_only
        if path=='/api/teacher-app/media-login-token':
            token=str(d.get('token',''))
            media_token,cl=make_teacher_media_token(token)
            return {'ok':True,'media_token':media_token,'class_id':cl['id'],'expires_in':90}
        if path=='/api/instant/join':
            self.limit_meeting_code()
            code=re.sub(r'\D','',str(d.get('code','')))
            need(len(code)==10,'Enter a 10-digit meeting code.')
            with db() as c:
                item=c.execute('''SELECT i.*,cl.title,cl.live,cl.status,cl.class_kind FROM instant_meetings i
                    JOIN classes cl ON cl.id=i.class_id WHERE i.code=?''',(code,)).fetchone()
            need(item and item['active'] and item['expires']>time.time() and item['status']=='scheduled','Meeting code is invalid or expired.',404)
            if not item['live']:
                with db() as c: c.execute('UPDATE classes SET live=1 WHERE id=?',(item['class_id'],))
            if self.user and self.user['role']!='guest':
                identity={'id':self.user['id'],'name':self.user['name'],'role':self.user['role']}
            else:
                name=field(d,'name',1,80)
                guest_id='guest-'+secrets.token_hex(8)
                identity={'id':guest_id,'name':name,'role':'guest'}
                self.session['guest_identity']=identity
            access=self.session.setdefault('instant_access',{})
            access[str(item['class_id'])]={'code':code,'expires':item['expires']}
            return {'ok':True,'class_id':item['class_id'],'title':item['title'],'user':identity}
        if path in ('/api/signup','/api/login'):
            username=field(d,'username',3,40).lower()
            need(re.fullmatch(r'[a-z0-9_]{3,40}',username),'Username: use letters, numbers, and underscores.')
            self.limit_auth(username,signup=path=='/api/signup')
            password=d.get('password',''); need(isinstance(password,str) and 1<=len(password)<=256,'Invalid password.')
            if path=='/api/signup':
                need(len(password)>=12,'Use at least 12 characters for your password.')
                name=field(d,'name',1,80)
                with db() as c:
                    try: r=c.execute("INSERT INTO users(username,name,password,role) VALUES (?,?,?,'student')",(username,name,hash_password(password)))
                    except sqlite3.IntegrityError: raise APIError('That username is already in use.',409)
                    uid=r.lastrowid
            else:
                with db() as c: u=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
                need(u and check_password(u['password'],password),'Incorrect username or password.',401)
                uid=u['id']
            self.rotate(uid)
            with db() as c:
                c.execute('DELETE FROM attempts WHERE ip=?',('auth-account:'+username,))
                u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            return {'user':public_user(u),'csrf':self.session['csrf']}
        if path=='/api/logout':
            with LOCK:
                for room in ROOMS.values():
                    for key in list(room['peers']):
                        if room['peers'][key]['session']==self.sid: del room['peers'][key]
            self.rotate(None); return {'ok':True,'csrf':self.session['csrf']}
        if path=='/api/resources/redeem':
            self.limit_resource_code()
            code=normalize_resource_code(d.get('code',''))
            with db() as c:
                row=c.execute('SELECT * FROM resource_codes WHERE code=? AND active=1',(code,)).fetchone()
                need(row,'That access code was not found or is no longer active.',404)
                files=[dict(x) for x in c.execute('''SELECT f.id,f.original_name AS name,f.size,f.mime FROM stored_files f
                    JOIN resource_code_files m ON m.file_id=f.id WHERE m.code_id=? ORDER BY m.position,f.id''',(row['id'],))]
                need(files,'There are no files attached to this code.',404)
            grant=secrets.token_urlsafe(24)
            with LOCK:
                clean_resource_grants(); RESOURCE_GRANTS[grant]={'code_id':row['id'],'session':self.sid,'expires':time.time()+1800}
            return {'grant':grant,'label':row['label'],'files':files,'expires_in':1800,'translate_enabled':bool(row['translate_enabled'])}
        if path=='/api/resources/translate':
            grant=str(d.get('grant',''))
            try: file_id=int(d.get('file_id',0))
            except Exception: raise APIError('Invalid file.',400)
            target='zh-CN' if str(d.get('target','zh-CN')).lower().startswith('zh') else 'en'
            with LOCK:
                clean_resource_grants(); access=RESOURCE_GRANTS.get(grant)
                need(access and access['session']==self.sid,'This resource session expired. Enter the access code again.',403)
                access['expires']=time.time()+1800
            with db() as c:
                code=c.execute('SELECT * FROM resource_codes WHERE id=? AND active=1',(access['code_id'],)).fetchone()
                need(code,'This access code is no longer active.',403)
                need(bool(code['translate_enabled']),'Automatic translation is disabled for this share code.',403)
                row=c.execute("SELECT f.* FROM stored_files f JOIN resource_code_files m ON m.file_id=f.id WHERE f.id=? AND m.code_id=?",(file_id,access['code_id'])).fetchone()
                need(row,'File not found for this access code.',404)
            source=_extract_translatable_text(row)
            translated=_translate_online(source,target)
            return {'ok':True,'file_id':file_id,'name':row['original_name'],'target':target,'text':translated,'source_chars':len(source)}
        if path=='/api/request-booking':
            self.require_user()
            lid=int(number(d,'lesson_type_id',1,1e9)); aid=int(number(d,'availability_id',1,1e9)); start=number(d,'start',time.time()+30,time.time()+70*86400)
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                lesson=c.execute("SELECT * FROM lesson_types WHERE id=? AND active=1",(lid,)).fetchone()
                avail=c.execute("SELECT * FROM availability WHERE id=? AND status='open'",(aid,)).fetchone()
                need(lesson and avail,'That lesson or availability is no longer offered.',409)
                minutes=lesson['minutes']; end=start+minutes*60
                need(avail['start']<=start and end<=avail['end'],'That lesson does not fit inside this availability block.',409)
                # Starts are aligned to the site-wide 15-minute calendar grid.
                need(abs((start/60)%15)<0.001,'Choose one of the displayed 15-minute start times.',409)
                overlap=c.execute("SELECT 1 FROM classes WHERE status='scheduled' AND approval IN ('pending','confirmed') AND start<? AND start+minutes*60>?",(end,start)).fetchone()
                need(not overlap,'That time was just taken. Choose another opening.',409)
                student_overlap=c.execute('''SELECT 1 FROM bookings b JOIN classes cl ON cl.id=b.class_id
                    WHERE b.user_id=? AND cl.status='scheduled' AND cl.approval IN ('pending','confirmed')
                    AND cl.start<? AND cl.start+cl.minutes*60>?''',(self.user['id'],end,start)).fetchone()
                need(not student_overlap,'You already have a booking at that time.',409)
                r=c.execute('''INSERT INTO classes(title,track,description,start,minutes,capacity,status,live,approval,lesson_type_id,availability_id,requested_by)
                    VALUES (?,?,?,?,?,1,'scheduled',0,'pending',?,?,?)''',(lesson['name'],lesson['name'],'Student booking request',start,minutes,lid,aid,self.user['id']))
                c.execute('INSERT INTO bookings(user_id,class_id,created) VALUES (?,?,?)',(self.user['id'],r.lastrowid,time.time()))
            return {'ok':True,'class_id':r.lastrowid}
        if path=='/api/group-booking/join':
            self.require_user(); cid=int(number(d,'class_id',1,1e9))
            need(self.user['role']!='admin','Teachers already have access to group lessons.',409)
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
                need(cl and cl['class_kind']=='group' and cl['status']=='scheduled' and cl['approval']=='confirmed',
                     'This group lesson is no longer available.',404)
                need(cl['start']>time.time(),'This group lesson has already started.',409)
                need(not c.execute('SELECT 1 FROM bookings WHERE class_id=? AND user_id=?',(cid,self.user['id'])).fetchone(),
                     'You already booked this group lesson.',409)
                booked=c.execute('SELECT count(*) FROM bookings WHERE class_id=?',(cid,)).fetchone()[0]
                need(booked<cl['capacity'],'This group lesson is full.',409)
                end=cl['start']+cl['minutes']*60
                conflict=c.execute('''SELECT 1 FROM bookings b JOIN classes x ON x.id=b.class_id
                    WHERE b.user_id=? AND x.status='scheduled' AND x.approval IN ('pending','confirmed')
                    AND x.start<? AND x.start+x.minutes*60>?''',(self.user['id'],end,cl['start'])).fetchone()
                need(not conflict,'You already have another lesson at that time.',409)
                c.execute('INSERT INTO bookings(user_id,class_id,created) VALUES (?,?,?)',(self.user['id'],cid,time.time()))
                if cl['group_chat_id']:
                    c.execute('INSERT OR IGNORE INTO group_chat_members(group_id,user_id,joined) VALUES (?,?,?)',
                              (cl['group_chat_id'],self.user['id'],time.time()))
            return {'ok':True,'group_chat_id':cl['group_chat_id']}
        if path=='/api/unbook':
            self.require_user(); cid=int(number(d,'class_id',1,1e9))
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                cl=c.execute('''SELECT cl.* FROM classes cl JOIN bookings b ON b.class_id=cl.id WHERE cl.id=? AND b.user_id=?''',(cid,self.user['id'])).fetchone()
                need(cl,'Booking not found.',404); need(cl['start']>time.time(),'Bookings can only be cancelled before they begin.',409)
                c.execute('DELETE FROM bookings WHERE class_id=? AND user_id=?',(cid,self.user['id']))
                if cl['requested_by']==self.user['id']: c.execute("UPDATE classes SET status='cancelled',live=0 WHERE id=?",(cid,))
                if cl['class_kind']=='group' and cl['group_chat_id']:
                    remaining=c.execute('''SELECT 1 FROM bookings b JOIN classes x ON x.id=b.class_id
                        WHERE b.user_id=? AND x.group_chat_id=? AND x.status!='cancelled' LIMIT 1''',
                        (self.user['id'],cl['group_chat_id'])).fetchone()
                    if not remaining:
                        c.execute('DELETE FROM group_chat_members WHERE group_id=? AND user_id=?',
                                  (cl['group_chat_id'],self.user['id']))
            return {'ok':True}
        if path.startswith('/api/admin/'):
            self.require_user(True)
            if path=='/api/admin/files/code':
                ids=d.get('file_ids'); need(isinstance(ids,list) and 1<=len(ids)<=50,'Select at least one file, up to 50.')
                clean_ids=[]
                for value in ids:
                    need(isinstance(value,int) and not isinstance(value,bool) and 1<=value<=1_000_000_000,'Invalid file selection.')
                    if value not in clean_ids: clean_ids.append(value)
                label=d.get('label','')
                need(isinstance(label,str),'Invalid label.'); label=label.strip()[:120] or 'Shared files'
                translate_enabled=1 if bool(d.get('translate_enabled',False)) else 0
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    placeholders=','.join('?' for _ in clean_ids)
                    found={r['id'] for r in c.execute(f'SELECT id FROM stored_files WHERE id IN ({placeholders})',clean_ids)}
                    need(found==set(clean_ids),'One of the selected files no longer exists.',409)
                    code=make_resource_code(c)
                    r=c.execute('INSERT INTO resource_codes(code,label,created,created_by,active,translate_enabled) VALUES (?,?,?,?,1,?)',(code,label,time.time(),self.user['id'],translate_enabled))
                    for pos,file_id in enumerate(clean_ids): c.execute('INSERT INTO resource_code_files(code_id,file_id,position) VALUES (?,?,?)',(r.lastrowid,file_id,pos))
                return {'ok':True,'code':code,'label':label,'file_count':len(clean_ids),'translate_enabled':bool(translate_enabled)}
            if path=='/api/admin/files/code-action':
                cid=int(number(d,'code_id',1,1e9)); action=d.get('action'); need(action in ('revoke','restore','enable_translate','disable_translate'),'Invalid action.')
                with db() as c:
                    need(c.execute('SELECT 1 FROM resource_codes WHERE id=?',(cid,)).fetchone(),'Code not found.',404)
                    if action in ('enable_translate','disable_translate'):
                        c.execute('UPDATE resource_codes SET translate_enabled=? WHERE id=?',(1 if action=='enable_translate' else 0,cid))
                    else:
                        c.execute('UPDATE resource_codes SET active=? WHERE id=?',(1 if action=='restore' else 0,cid))
                if action in ('revoke','restore'):
                    with LOCK:
                        for key in list(RESOURCE_GRANTS):
                            if RESOURCE_GRANTS[key]['code_id']==cid: del RESOURCE_GRANTS[key]
                return {'ok':True}
            if path=='/api/admin/files/delete':
                fid=int(number(d,'file_id',1,1e9))
                with db() as c:
                    row=c.execute('SELECT * FROM stored_files WHERE id=?',(fid,)).fetchone(); need(row,'File not found.',404)
                storage_delete(row['storage_key'],row['storage_backend'])
                with db() as c:
                    c.execute('DELETE FROM stored_files WHERE id=?',(fid,))
                    c.execute('UPDATE resource_codes SET active=0 WHERE active=1 AND NOT EXISTS (SELECT 1 FROM resource_code_files m WHERE m.code_id=resource_codes.id)')
                return {'ok':True}
            if path=='/api/admin/groups/create':
                name=field(d,'name',1,100); ids=d.get('user_ids',[])
                need(isinstance(ids,list) and 1<=len(ids)<=100,'Select at least one user for the group chat.')
                clean=[]
                for value in ids:
                    need(isinstance(value,int) and not isinstance(value,bool) and value>0,'Invalid group member.')
                    if value not in clean: clean.append(value)
                with db() as c:
                    if clean:
                        q=','.join('?' for _ in clean); found={r['id'] for r in c.execute(f'SELECT id FROM users WHERE id IN ({q})',clean)}
                        need(found==set(clean),'One of those users no longer exists.',409)
                    r=c.execute("INSERT INTO group_chats(name,created,created_by,kind) VALUES (?,?,?,'manual')",
                                (name,time.time(),self.user['id']))
                    members=set(clean); members.add(self.user['id'])
                    for uid in members: c.execute('INSERT INTO group_chat_members(group_id,user_id,joined) VALUES (?,?,?)',(r.lastrowid,uid,time.time()))
                return {'ok':True,'group_id':r.lastrowid}
            if path=='/api/admin/groups/update':
                gid=int(number(d,'group_id',1,1e9)); name=field(d,'name',1,100); ids=d.get('user_ids',[])
                need(isinstance(ids,list) and len(ids)<=100,'Invalid group members.')
                clean=[]
                for value in ids:
                    need(isinstance(value,int) and not isinstance(value,bool) and value>0,'Invalid group member.')
                    if value not in clean: clean.append(value)
                with db() as c:
                    group=c.execute('SELECT * FROM group_chats WHERE id=?',(gid,)).fetchone(); need(group,'Group chat not found.',404)
                    if clean:
                        q=','.join('?' for _ in clean); found={r['id'] for r in c.execute(f'SELECT id FROM users WHERE id IN ({q})',clean)}
                        need(found==set(clean),'One of those users no longer exists.',409)
                    c.execute('UPDATE group_chats SET name=? WHERE id=?',(name,gid))
                    keep=set(clean); keep.add(group['created_by'])
                    c.execute('DELETE FROM group_chat_members WHERE group_id=?',(gid,))
                    for uid in keep: c.execute('INSERT OR IGNORE INTO group_chat_members(group_id,user_id,joined) VALUES (?,?,?)',(gid,uid,time.time()))
                return {'ok':True}
            if path=='/api/admin/groups/delete':
                gid=int(number(d,'group_id',1,1e9))
                with db() as c:
                    group=c.execute('SELECT * FROM group_chats WHERE id=?',(gid,)).fetchone(); need(group,'Group chat not found.',404)
                    linked=c.execute("SELECT 1 FROM classes WHERE group_chat_id=? AND status!='cancelled' LIMIT 1",(gid,)).fetchone()
                    need(not linked,'This group chat belongs to a group lesson. Cancel those lessons before deleting it.',409)
                    c.execute('DELETE FROM group_chats WHERE id=?',(gid,))
                return {'ok':True}
            if path=='/api/admin/group-class':
                title=field(d,'title',1,140); lid=int(number(d,'lesson_type_id',1,1e9))
                start=number(d,'start',time.time()+30,time.time()+366*86400)
                capacity=int(number(d,'capacity',2,5))
                need(abs((start/60)%15)<0.001,'Group lessons must start on a 15-minute interval.')
                description=d.get('description',''); need(isinstance(description,str),'Invalid description.'); description=description.strip()[:2000] or 'Small-group lesson'
                price=d.get('price_label',''); need(isinstance(price,str),'Invalid price.'); price=price.strip()[:80] or 'Price TBD'
                repeat=bool(d.get('repeat_weekly',False)); weeks=int(number(d,'weeks',2,24)) if repeat else 1
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    lesson=c.execute('SELECT * FROM lesson_types WHERE id=? AND active=1',(lid,)).fetchone(); need(lesson,'Lesson option not found.',404)
                    planned=[]
                    for i in range(weeks):
                        st=start+i*7*86400; en=st+lesson['minutes']*60
                        conflict=c.execute("SELECT 1 FROM classes WHERE status='scheduled' AND approval IN ('pending','confirmed') AND start<? AND start+minutes*60>?",(en,st)).fetchone()
                        need(not conflict,f'Week {i+1} conflicts with another lesson.',409)
                        planned.append(st)
                    gr=c.execute("INSERT INTO group_chats(name,created,created_by,kind) VALUES (?,?,?,'lesson')",
                                 (title,time.time(),self.user['id']))
                    c.execute('INSERT INTO group_chat_members(group_id,user_id,joined) VALUES (?,?,?)',(gr.lastrowid,self.user['id'],time.time()))
                    series=secrets.token_hex(8) if weeks>1 else None; ids=[]
                    for st in planned:
                        r=c.execute('''INSERT INTO classes(title,track,description,start,minutes,capacity,status,live,approval,lesson_type_id,series_id,class_kind,group_price_label,group_chat_id)
                            VALUES (?,?,?,?,?,?,'scheduled',0,'confirmed',?,?, 'group',?,?)''',
                            (title,lesson['name'],description,st,lesson['minutes'],capacity,lid,series,price,gr.lastrowid))
                        ids.append(r.lastrowid)
                return {'ok':True,'ids':ids,'group_chat_id':gr.lastrowid,'created':len(ids)}
            if path=='/api/admin/settings':
                with db() as c:
                    for key in DEFAULTS:
                        if key in d:
                            value=field(d,key,0 if key=='contact' else 1,1500)
                            if key=='timezone': need(value in ('America/Edmonton','America/Vancouver','America/Toronto','UTC'),'Choose a supported timezone.')
                            c.execute('UPDATE settings SET value=? WHERE key=?',(value,key))
                return {'ok':True}
            if path=='/api/admin/availability':
                start=number(d,'start',time.time()+30,time.time()+366*86400); end=number(d,'end',start+15*60,time.time()+367*86400)
                need(end>start and end-start<=12*3600,'Availability must be between 15 minutes and 12 hours.')
                need(abs((start/60)%15)<0.001 and abs((end/60)%15)<0.001,'Availability must start and end on a 15-minute interval.')
                repeat=bool(d.get('repeat_weekly',False)); weeks=int(number(d,'weeks',1,24)) if repeat else 1
                group=secrets.token_hex(8) if weeks>1 else None
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    for i in range(weeks):
                        a=start+i*7*86400; b=end+i*7*86400
                        overlap=c.execute("SELECT 1 FROM availability WHERE status='open' AND start<? AND end>?",(b,a)).fetchone()
                        need(not overlap,'An open availability block already overlaps one of those times.',409)
                    ids=[]
                    for i in range(weeks):
                        r=c.execute("INSERT INTO availability(start,end,status,repeat_group) VALUES (?,?,'open',?)",(start+i*7*86400,end+i*7*86400,group)); ids.append(r.lastrowid)
                return {'ok':True,'ids':ids}
            if path=='/api/admin/availability-action':
                aid=int(number(d,'availability_id',1,1e9)); action=d.get('action'); need(action=='close','Invalid action.')
                with db() as c:
                    need(c.execute('SELECT 1 FROM availability WHERE id=?',(aid,)).fetchone(),'Availability not found.',404)
                    c.execute("UPDATE availability SET status='closed' WHERE id=?",(aid,))
                return {'ok':True}
            if path=='/api/admin/booking-action':
                cid=int(number(d,'class_id',1,1e9)); action=d.get('action'); need(action in ('confirm','reject','confirm_weekly'),'Invalid action.')
                weeks=int(number(d,'weeks',2,24)) if action=='confirm_weekly' else 1
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
                    need(cl and cl['status']=='scheduled' and cl['approval']=='pending','This request is no longer pending.',409)
                    booking=c.execute('SELECT * FROM bookings WHERE class_id=?',(cid,)).fetchone(); need(booking,'Booking not found.',404)
                    if action=='reject':
                        c.execute("UPDATE classes SET approval='rejected',status='cancelled',live=0 WHERE id=?",(cid,)); return {'ok':True,'created':0}
                    series=secrets.token_hex(8) if action=='confirm_weekly' else cl['series_id']
                    planned=[]
                    if action=='confirm_weekly':
                        for i in range(1,weeks):
                            st=cl['start']+i*7*86400; en=st+cl['minutes']*60
                            av=c.execute("SELECT * FROM availability WHERE status='open' AND start<=? AND end>=? ORDER BY start LIMIT 1",(st,en)).fetchone()
                            need(av,f'Week {i+1} does not have matching teacher availability. Add weekly availability first.',409)
                            conflict=c.execute("SELECT 1 FROM classes WHERE id<>? AND status='scheduled' AND approval IN ('pending','confirmed') AND start<? AND start+minutes*60>?",(cid,en,st)).fetchone()
                            need(not conflict,f'Week {i+1} conflicts with another booking.',409)
                            student_conflict=c.execute('''SELECT 1 FROM bookings b JOIN classes x ON x.id=b.class_id WHERE b.user_id=? AND x.id<>? AND x.status='scheduled' AND x.approval IN ('pending','confirmed') AND x.start<? AND x.start+x.minutes*60>?''',(booking['user_id'],cid,en,st)).fetchone()
                            need(not student_conflict,f'The student has another booking in week {i+1}.',409)
                            planned.append((st,av['id']))
                    c.execute("UPDATE classes SET approval='confirmed',series_id=? WHERE id=?",(series,cid))
                    for st,aid in planned:
                        r=c.execute('''INSERT INTO classes(title,track,description,start,minutes,capacity,status,live,approval,lesson_type_id,availability_id,series_id,requested_by)
                          VALUES (?,?,?,?,?,1,'scheduled',0,'confirmed',?,?,?,?)''',(cl['title'],cl['track'],cl['description'],st,cl['minutes'],cl['lesson_type_id'],aid,series,cl['requested_by']))
                        c.execute('INSERT INTO bookings(user_id,class_id,created) VALUES (?,?,?)',(booking['user_id'],r.lastrowid,time.time()))
                return {'ok':True,'created':len(planned)+1}
            if path=='/api/admin/class':
                # Backwards-compatible fixed class creation for older clients/tests.
                title=field(d,'title',1,140); description=field(d,'description',1,2000); track=field(d,'track')
                start=number(d,'start',time.time()+30,time.time()+366*86400); minutes=int(number(d,'minutes',15,180)); capacity=int(number(d,'capacity',1,5))
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    overlap=c.execute("SELECT 1 FROM classes WHERE status='scheduled' AND approval IN ('pending','confirmed') AND start<? AND start+minutes*60>?",(start+minutes*60,start)).fetchone()
                    need(not overlap,'Another class already occupies that time.',409)
                    r=c.execute("INSERT INTO classes(title,track,description,start,minutes,capacity,approval) VALUES (?,?,?,?,?,?,'confirmed')",(title,track,description,start,minutes,capacity))
                return {'ok':True,'id':r.lastrowid}
            if path=='/api/admin/instant-meeting':
                title=str(d.get('title','Instant meeting')).strip()[:120] or 'Instant meeting'
                now=time.time()
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    r=c.execute("""INSERT INTO classes(title,track,description,start,minutes,capacity,status,live,approval,class_kind)
                        VALUES (?,?,?, ?,60,5,'scheduled',1,'confirmed','instant')""",
                        (title,'Instant','Started directly by the teacher',now))
                    cid=r.lastrowid
                    code=make_instant_meeting_code(c)
                    c.execute('INSERT INTO instant_meetings(code,class_id,created,expires,active,created_by) VALUES (?,?,?,?,1,?)',
                              (code,cid,now,now+12*3600,self.user['id']))
                return {'ok':True,'class_id':cid,'code':code,'title':title,'expires_in':43200}
            if path=='/api/admin/teacher-app-launch':
                cid=int(number(d,'class_id',1,1e9))
                with LOCK:
                    with db() as c:
                        cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
                        need(cl and cl['status']=='scheduled','Class unavailable.',404)
                        need(cl['approval']=='confirmed','Confirm the booking before opening its classroom.',409)
                        need(time.time()>=cl['start']-1800,'The meeting can be opened from 30 minutes before the scheduled start.')
                        c.execute('UPDATE classes SET live=1 WHERE id=?',(cid,))
                    clean_teacher_app_tokens()
                    token=secrets.token_urlsafe(36)
                    TEACHER_APP_TOKENS[token]={**token_claims(self.user,self.sid),'class_id':cid,'expires':time.time()+12*3600}
                    proc=TEACHER_APP_PROCESSES.get(cid)
                    if proc is not None and proc.poll() is not None:
                        TEACHER_APP_PROCESSES.pop(cid,None); proc=None
                launched=False; already_running=proc is not None
                launch_error=''
                if not already_running and sys.platform=='win32':
                    try:
                        python=Path(sys.executable)
                        pythonw=python.with_name('pythonw.exe')
                        executable=str(pythonw if pythonw.exists() else python)
                        public_origin=current_public_origin() or f'http://127.0.0.1:{PORT}'
                        args=[executable,str(ROOT/'teacher_app_bootstrap.py'),'--server',f'http://127.0.0.1:{PORT}',
                              '--token',token,'--public-origin',public_origin,'--skip-auto-media']
                        flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if Path(executable).name.lower()!='pythonw.exe' else 0
                        proc=subprocess.Popen(args,cwd=str(ROOT),close_fds=True,creationflags=flags)
                        with LOCK: TEACHER_APP_PROCESSES[cid]=proc
                        launched=True
                    except Exception as ex:
                        launch_error=str(ex)[:240]
                # Always provide the same full browser classroom for scheduled and instant meetings.
                # It is authenticated with a short-lived one-time admin handoff token so the teacher
                # never sees the student join-code page.
                media_token,_=make_teacher_media_token(token)
                browser_origin=current_public_origin() or f'http://127.0.0.1:{PORT}'
                browser_url=f"{browser_origin}/teacher-media-login?token={quote(media_token)}"
                return {'ok':True,'token':token,'class_id':cid,'title':cl['title'],'expires_in':43200,
                        'launched':launched,'already_running':already_running,'launch_error':launch_error,
                        'browser_url':browser_url,'full_classroom':True,
                        'windows_app_supported':sys.platform=='win32'}
            if path=='/api/admin/class-action':
                cid=int(number(d,'class_id',1,1e9)); action=d.get('action')
                need(action in ('cancel','open','end'),'Invalid action.')
                with LOCK:
                    with db() as c:
                        cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
                        need(cl and cl['status']=='scheduled','Class unavailable.',404)
                        if action=='open':
                            need(cl['approval']=='confirmed','Confirm the booking before opening its classroom.',409)
                            need(time.time()>=cl['start']-1800,'The classroom can be opened from 30 minutes before the scheduled start. If the lesson starts late, it remains available until you end or cancel it.')
                            c.execute('UPDATE classes SET live=1 WHERE id=?',(cid,))
                        else:
                            c.execute('UPDATE classes SET live=0,status=? WHERE id=?',('cancelled' if action=='cancel' else 'completed',cid))
                            c.execute('UPDATE instant_meetings SET active=0 WHERE class_id=?',(cid,))
                            ROOMS.pop(cid,None)
                return {'ok':True}
            if path=='/api/admin/role':
                uid=int(number(d,'user_id',1,1e9)); role=d.get('role')
                need(role in ('admin','student'),'Invalid role.')
                need(uid!=self.user['id'],'You cannot change your own role.')
                with db() as c:
                    need(c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone(),'User not found.',404)
                    c.execute('UPDATE users SET role=? WHERE id=?',(role,uid))
                with LOCK:
                    revoke_tokens(uid=uid)
                    for room in ROOMS.values():
                        for key in list(room['peers']):
                            if room['peers'][key]['uid']==uid: del room['peers'][key]
                return {'ok':True}
            if path=='/api/admin/post':
                title=field(d,'title',1,160); body=field(d,'body',1,20000)
                with db() as c: c.execute('INSERT INTO posts(title,body,author) VALUES (?,?,?)',(title,body,self.user['name']))
                return {'ok':True}
        if path=='/api/group-messages/send':
            gid=int(number(d,'group_id',1,1e9)); self.group_access(gid)
            text=field(d,'text',1,1000)
            with db() as c:
                cur=c.execute('INSERT INTO group_messages(group_id,user_id,text,created) VALUES (?,?,?,?)',
                              (gid,self.user['id'],text,time.time()))
                mid=cur.lastrowid
            return {'ok':True,'id':mid}
        if path=='/api/messages/send':
            cid=int(number(d,'class_id',1,1e9)); self.room_access(cid,live=False)
            text=field(d,'text',1,1000)
            with db() as c:
                cur=c.execute('INSERT INTO class_messages(class_id,user_id,text,created) VALUES (?,?,?,?)',
                              (cid,self.user['id'],text,time.time()))
                mid=cur.lastrowid
            return {'ok':True,'id':mid}
        if path.startswith('/api/room/'):
            cid=int(number(d,'class_id',1,1e9)); self.room_access(cid)
            if path=='/api/room/join':
                # Provider I/O is serialized only by TURN_CACHE_LOCK, never the
                # global session/room lock needed by unrelated requests.
                servers,relay_configured,relay_provider,relay_error=build_ice_servers(self.user['id'])
            with LOCK:
                if path=='/api/room/join':
                    # Lookup can outlast logout, role changes or class closure.
                    self.prepare()
                    self.room_access(cid)
                room=room_for(cid); clean_room(room)
                if path=='/api/room/join':
                    # Rejoining in the same browser replaces only that browser's old peer.
                    # A student may join from a second device, and multiple guests/accounts
                    # can be connected at the same time.
                    for key in list(room['peers']):
                        existing=room['peers'][key]
                        if existing.get('session')==self.sid and existing.get('uid')==self.user['id']:
                            del room['peers'][key]
                    need(len(room['peers'])<6,'This small-group room is full (maximum 6 connected participants).',409)
                    peer=secrets.token_hex(16)
                    room['peers'][peer]={'uid':self.user['id'],'name':self.user['name'],'role':self.user['role'],'session':self.sid,'seen':time.time(),'mic_on':False,'camera_on':False,'forced_mute':False}
                    return {'peer':peer,'iceServers':servers,'relayConfigured':relay_configured,
                            'relayProvider':relay_provider,'relayError':relay_error}
                peer=d.get('peer'); self.owned_peer(room,peer)
                if path=='/api/room/leave':
                    room['peers'].pop(peer,None); clean_room(room); return {'ok':True}
                if path=='/api/room/signal':
                    target=d.get('to'); need(target in room['peers'],'Participant left.',409)
                    signal=d.get('signal'); need(isinstance(signal,dict) and len(json.dumps(signal))<100000,'Invalid signal.')
                    # Host moderation is generated only by /api/room/mute. Keep
                    # participant signaling limited to the existing media protocol.
                    if 'control' in signal:
                        need(signal['control'] in ('renegotiate','camera-retry')
                             and set(signal)<= {'control','iceRestart'},'Invalid signal.')
                        need('iceRestart' not in signal or isinstance(signal['iceRestart'],bool),'Invalid signal.')
                    else:
                        need(set(signal) in ({'description'},{'candidate'}),'Invalid signal.')
                    need(len(room['events'])<12000,'Room is busy. Try again.',429)
                    room['seq']+=1; room['events'].append({'seq':room['seq'],'from':peer,'to':target,'signal':signal,'at':time.time()})
                    return {'ok':True}
                if path=='/api/room/chat':
                    text=field(d,'text',1,1000)
                    room['chat_seq']+=1
                    message={'id':room['chat_seq'],'from':peer,'uid':self.user['id'],'name':self.user['name'],
                             'role':self.user['role'],'text':text,'codes':active_resource_codes_in_text(text),'at':time.time()}
                    room['messages'].append(message)
                    room['messages'][:]=room['messages'][-300:]
                    return {'ok':True,'message':message}
                if path=='/api/room/media-state':
                    current=room['peers'][peer]
                    mic=bool(d.get('mic_on',False))
                    cam=bool(d.get('camera_on',False))
                    if current.get('forced_mute'): mic=False
                    current['mic_on']=mic; current['camera_on']=cam
                    return {'ok':True,'forcedMute':bool(current.get('forced_mute'))}
                if path=='/api/room/overlay-token':
                    token=secrets.token_urlsafe(24)
                    with LOCK:
                        clean_overlay_tokens()
                        OVERLAY_TOKENS[token]={**token_claims(self.user,self.sid),'class_id':cid,'expires':time.time()+4*3600}
                    return {'token':token,'class_id':cid,'expires_in':14400}
                if path=='/api/room/mute':
                    self.require_user(True)
                    target=d.get('target'); need(target in room['peers'] and target!=peer,'Participant unavailable.',409)
                    muted=bool(d.get('muted',True)); target_peer=room['peers'][target]
                    target_peer['forced_mute']=muted
                    if muted: target_peer['mic_on']=False
                    room['seq']+=1
                    room['events'].append({'seq':room['seq'],'from':peer,'to':target,'signal':{'control':'host-mute','muted':muted},'at':time.time()})
                    return {'ok':True,'muted':muted}
                if path=='/api/room/permissions':
                    self.require_user(True); room['drawing']=bool(d.get('drawing')); return {'ok':True}
                if path=='/api/room/presenter':
                    if d.get('active'):
                        need(room['presenter'] in (None,peer),'Someone else is presenting.',409)
                        room['presenter']=peer
                    elif room['presenter']==peer: room['presenter']=None
                    return {'ok':True}
                if path=='/api/room/board':
                    need(self.user['role']=='admin' or room['drawing'],'The teacher has not enabled student drawing.',403)
                    board=valid_board(d.get('board'))
                    version=int(number(d,'version',0,1e12))
                    with db() as c:
                        c.execute('BEGIN IMMEDIATE')
                        old=c.execute('SELECT version FROM boards WHERE class_id=?',(cid,)).fetchone()
                        need(version==(old['version'] if old else 0),'The board changed. Your action was not saved; try again.',409)
                        c.execute('INSERT OR REPLACE INTO boards VALUES (?,?,?)',(cid,version+1,json.dumps(board)))
                    return {'version':version+1}
        raise APIError('Not found.',404)

def main():
    init()
    if sys.argv[1:]==['add-admin']: return cli_account()
    if sys.argv[1:]==['reset-password']: return cli_account(True)
    if sys.argv[1:]: raise SystemExit('Usage: py server.py [add-admin|reset-password]')
    with db() as c: missing=not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone()
    if missing:
        if os.environ.get('MATH_DESKTOP_MODE')=='1':
            raise SystemExit('No teacher account exists. Start MathStudioTeacher.exe to create one.')
        print('Create the first teacher/admin account:'); cli_account()
    try: server=ThreadingHTTPServer((BIND,PORT),Handler)
    except OSError as ex: raise SystemExit(f'Could not open port {PORT}: {ex}. Stop the program already using that port first.')
    # A failed duplicate launch must not mutate the running server's classes.
    try:
        with db() as c: c.execute('UPDATE classes SET live=0')
    except Exception:
        server.server_close(); raise
    # Show both the same-computer address and a best-effort LAN address so
    # phones/tablets/other computers on the same network know what to open.
    lan_ip = None
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(('8.8.8.8', 80))
        lan_ip = probe.getsockname()[0]
        probe.close()
    except OSError:
        pass
    print(f'MathStudio v41.6.6 is running on port {PORT}', flush=True)
    print('Build: v41.6.6-release-candidate', flush=True)
    print(f'Math Studio (this computer): http://127.0.0.1:{PORT}')
    if lan_ip:
        print(f'Math Studio (same Wi-Fi/LAN): http://{lan_ip}:{PORT}')
    else:
        print(f'Math Studio is listening on the local network on port {PORT}.')
        print('Run ipconfig and use your IPv4 address, for example http://192.168.1.25:%d' % PORT)
    print('Leave this terminal open. Ctrl+C stops the server.')
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nStopped.')
    finally: server.server_close()

if __name__=='__main__': main()
