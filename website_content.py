"""Drafts/publication for existing PUBLIC content only. No student data sources."""
import hashlib
import json

SETTINGS=('name','headline','teacher','contact','intro','about')


class ContentError(Exception):
    def __init__(self,message,status=400):self.message,self.status=message,status


def valid_text(value,limit):
    if not isinstance(value,str) or len(value)>limit:return False
    try:value.encode('utf-8')
    except UnicodeEncodeError:return False
    return True


def initialize(c):
    if 'published' not in {r['name'] for r in c.execute('PRAGMA table_info(posts)')}:
        c.execute('ALTER TABLE posts ADD COLUMN published INTEGER NOT NULL DEFAULT 1')
    c.execute('''CREATE TABLE IF NOT EXISTS website_drafts(
        source_key TEXT PRIMARY KEY, draft TEXT NOT NULL, title TEXT,
        base_hash TEXT NOT NULL, revision INTEGER NOT NULL, visible INTEGER NOT NULL DEFAULT 1)''')


def originals(c):
    rows={f"settings:0:{r['key']}":{'text':r['value'],'title':'','visible':True}
          for r in c.execute('SELECT key,value FROM settings') if r['key'] in SETTINGS}
    for r in c.execute('SELECT id,title,body,published FROM posts'):
        rows[f"posts:{r['id']}:body"]={'text':r['body'],'title':r['title'],'visible':bool(r['published'])}
    for r in c.execute('SELECT id,name,description FROM lesson_types WHERE active=1'):
        rows[f"courses:{r['id']}:description"]={'text':r['description'],'title':r['name'],'visible':True}
    for r in c.execute("SELECT id,title,description FROM classes WHERE class_kind='group' AND approval='confirmed' AND status='scheduled'"):
        rows[f"groups:{r['id']}:description"]={'text':r['description'],'title':r['title'],'visible':True}
    return rows


def fingerprint(item):
    return hashlib.sha256(json.dumps([item['text'],item['title']],ensure_ascii=False).encode('utf-8')).hexdigest()


def state(c):
    drafts={r['source_key']:dict(r) for r in c.execute('SELECT * FROM website_drafts')}
    entries=[]
    for key,item in originals(c).items():
        row=drafts.get(key);current=fingerprint(item)
        visible=item['visible'] and (not row or bool(row['visible']))
        changed=bool(row and (row['draft']!=item['text'] or (key.startswith('posts:') and row['title']!=item['title'])))
        entries.append(dict(key=key,original=item['text'],title=item['title'],draft=row['draft'] if row else item['text'],
            draft_title=row['title'] if row and key.startswith('posts:') else item['title'],
            base_hash=current,revision=row['revision'] if row else 0,visible=visible,
            status='conflict' if row and row['base_hash']!=current else 'draft' if changed or not visible else 'published'))
    return {'entries':entries}


def visibility(c):
    return {r['source_key']:bool(r['visible']) for r in c.execute('SELECT source_key,visible FROM website_drafts')}


def translation_sources(c,values,public=False):
    rows={r['source_key']:r for r in c.execute('SELECT * FROM website_drafts')}
    if public:return {k:v for k,v in values.items() if k not in rows or rows[k]['visible']}
    return {k:rows[k]['draft'] if k in rows else v for k,v in values.items()}


def action(c,data,author):
    op=data.get('action')
    c.execute('BEGIN IMMEDIATE')
    if op=='create_post':
        title=data.get('title');text=data.get('text')
        if not valid_text(title,160) or not title.strip() or not valid_text(text,20000) or not text.strip():
            raise ContentError('Write an announcement title and message.')
        cur=c.execute('INSERT INTO posts(title,body,author,published) VALUES (?,?,?,0)',(title,text,author))
        key=f'posts:{cur.lastrowid}:body'
        item=originals(c)[key]
        c.execute('INSERT INTO website_drafts VALUES (?,?,?,?,1,0)',(key,text,title,fingerprint(item)))
        return {'ok':True,'key':key}
    key=data.get('key');items=originals(c)
    if not isinstance(key,str) or key not in items:raise ContentError('Public content not found.',404)
    item=items[key];row=c.execute('SELECT * FROM website_drafts WHERE source_key=?',(key,)).fetchone()
    revision=row['revision'] if row else 0
    if type(data.get('revision')) is not int or data['revision']!=revision or data.get('base_hash')!=fingerprint(item):
        raise ContentError('Content changed. Reload before saving.',409)
    if op=='save':
        text=data.get('text');title=data.get('title',item['title'])
        limit=1500 if key.startswith('settings:') else 2000 if key.startswith('courses:') else 20000
        if not valid_text(text,limit) or not valid_text(title,160):
            raise ContentError('Invalid public content.')
        if key.startswith('posts:') and (not text.strip() or not title.strip()):raise ContentError('Write an announcement title and message.')
        c.execute('''INSERT INTO website_drafts VALUES (?,?,?,?,?,?) ON CONFLICT(source_key) DO UPDATE SET
          draft=excluded.draft,title=excluded.title,base_hash=excluded.base_hash,revision=excluded.revision''',
          (key,text,title,fingerprint(item),revision+1,int(item['visible'])))
    elif op in ('publish','unpublish'):
        if row and row['base_hash']!=fingerprint(item):raise ContentError('Content changed. Reload and save your draft again.',409)
        text=row['draft'] if row else item['text'];title=row['title'] if row else item['title']
        kind,identifier,field=key.split(':');identifier=int(identifier)
        if op=='publish':
            if kind=='settings':c.execute('UPDATE settings SET value=? WHERE key=?',(text,field))
            elif kind=='posts':c.execute('UPDATE posts SET body=?,title=?,published=1 WHERE id=?',(text,title,identifier))
            elif kind=='courses':c.execute('UPDATE lesson_types SET description=? WHERE id=?',(text,identifier))
            elif kind=='groups':c.execute('UPDATE classes SET description=? WHERE id=?',(text,identifier))
        elif kind=='posts':c.execute('UPDATE posts SET published=0 WHERE id=?',(identifier,))
        current=originals(c)[key]
        c.execute('''INSERT INTO website_drafts VALUES (?,?,?,?,?,?) ON CONFLICT(source_key) DO UPDATE SET
          base_hash=excluded.base_hash,revision=excluded.revision,visible=excluded.visible''',
          (key,text,title,fingerprint(current),revision+1,int(op=='publish')))
    else:raise ContentError('Invalid public content action.')
    return {'ok':True,'key':key}
