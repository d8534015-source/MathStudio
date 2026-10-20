"""Editable bilingual review policies and versioned, server-side acknowledgments."""
import hashlib
import html
import json
from pathlib import Path
import time
ROOT=Path(__file__).parent/'policies'
KINDS=('privacy','terms','cookies')


def digest():
    h=hashlib.sha256()
    for kind in KINDS:
        for lang in ('en','zh'):h.update((ROOT/(kind+'.'+lang+'.md')).read_bytes())
    return h.hexdigest()[:12]


def metadata():
    result=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));result['version']=result['version']+'.'+digest();return result


def validate(data,error):
    if data.get('policy_version')!=metadata()['version'] or any(data.get(k) is not True for k in ('accept_terms','ack_privacy','ack_cookies')):
        raise error('Review and acknowledge the current Terms, Privacy and Cookie policies.',400)


def acknowledge(features,uid,data,error):
    validate(data,error)
    with features.db() as c:c.execute('INSERT OR REPLACE INTO policy_acks VALUES (?,?,?)',(uid,metadata()['version'],time.time()))
    return {'ok':True,'version':metadata()['version']}


def registration(connection,features,uid):
    # Atomic new-account + acknowledgement, without altering account table schema.
    connection.execute('ATTACH DATABASE ? AS registration_policy',(str(features.path),))
    connection.execute('INSERT OR REPLACE INTO registration_policy.policy_acks VALUES (?,?,?)',(uid,metadata()['version'],time.time()))


def due(features,uid):
    with features.db() as c:return not bool(c.execute('SELECT 1 FROM policy_acks WHERE user_id=? AND version=?',(uid,metadata()['version'])).fetchone())


def document(kind,lang):
    if kind not in KINDS:raise ValueError('Unknown policy.')
    lang='zh' if lang=='zh' else 'en';text=(ROOT/(kind+'.'+lang+'.md')).read_text(encoding='utf-8')
    # Simple safe renderer; author-editable Markdown never executes HTML/scripts.
    paragraphs=[]
    for paragraph in text.split('\n\n'):
        if paragraph.startswith('# '):paragraphs.append('<h1>'+html.escape(paragraph[2:])+'</h1>')
        elif paragraph.startswith('## '):paragraphs.append('<h2>'+html.escape(paragraph[3:])+'</h2>')
        else:paragraphs.append('<p>'+html.escape(paragraph).replace('\n','<br>')+'</p>')
    return ('<!doctype html><html lang="'+lang+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MathStudio policy draft</title><link rel="stylesheet" href="/style.css"></head><body><main class="container"><a href="/">MathStudio</a> · <a href="?lang=en">English</a> · <a href="?lang=zh">中文</a> · <a href="/privacy-settings">Privacy settings / 隐私设置</a>'+''.join(paragraphs)+'</main></body></html>').encode()
