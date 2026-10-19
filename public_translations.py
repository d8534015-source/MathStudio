"""Opt-in translation of allowlisted PUBLIC descriptions, separate from originals.

No account, message, file, private-class or booking source is accepted here.
Provider calls run outside database transactions. Credentials never enter API output.
"""
import argos_runtime
import website_content
import hashlib
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request


class TranslationError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def initialize(c):
    website_content.initialize(c)
    c.executescript('''
      CREATE TABLE IF NOT EXISTS public_translation_config(
        id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0,
        terms TEXT NOT NULL DEFAULT '[]');
      INSERT OR IGNORE INTO public_translation_config(id) VALUES (1);
      CREATE TABLE IF NOT EXISTS public_translations(
        source_key TEXT NOT NULL, target TEXT NOT NULL, source_hash TEXT NOT NULL,
        draft TEXT NOT NULL, approved TEXT, revision INTEGER NOT NULL DEFAULT 1,
        updated REAL NOT NULL, PRIMARY KEY(source_key,target,source_hash));
    ''')
    if 'description' not in {r['name'] for r in c.execute('PRAGMA table_info(lesson_types)')}:
        c.execute("ALTER TABLE lesson_types ADD COLUMN description TEXT NOT NULL DEFAULT ''")


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sources(c,public=False):
    result = {}
    for row in c.execute("SELECT key,value FROM settings WHERE key IN ('headline','intro','about')"):
        result['settings:0:' + row['key']] = row['value']
    for row in c.execute('SELECT id,body FROM posts'+(' WHERE published=1 ORDER BY id DESC LIMIT 30' if public else ' ORDER BY id DESC')):
        result[f"posts:{row['id']}:body"] = row['body']
    for row in c.execute("SELECT id,description FROM lesson_types WHERE active=1"):
        result[f"courses:{row['id']}:description"] = row['description']
    for row in c.execute("SELECT id,description FROM classes WHERE class_kind='group' AND approval='confirmed' AND status='scheduled'"):
        result[f"groups:{row['id']}:description"] = row['description']
    return website_content.translation_sources(c,result,public)


def config(c):
    row = c.execute('SELECT enabled,terms FROM public_translation_config WHERE id=1').fetchone()
    name = provider_name()
    return {'enabled': bool(row['enabled']), 'terms': json.loads(row['terms']),
            'provider': name, 'offline': name == 'argos',
            'configured': argos_runtime.ready() if name == 'argos' else name != 'disabled'}


def provider_name():
    name = os.environ.get('MATH_PUBLIC_TRANSLATION_PROVIDER')
    if name is None:
        name = 'argos' if argos_runtime.ready() else ''
    name = name.strip()
    if name == 'argos':
        return name
    if name == 'legacy-google':
        return name
    if name == 'libretranslate':
        url = urllib.parse.urlsplit(os.environ.get('MATH_PUBLIC_TRANSLATION_URL', ''))
        if url.scheme == 'https' and url.hostname and not url.username and not url.password and not url.query and not url.fragment:
            return name
    return 'disabled'


def translate(text, target, legacy):
    """Adapters share one plain-text interface. Only called after saved opt-in."""
    name = provider_name()
    if name == 'argos':
        try:
            return argos_runtime.translate(text,target)
        except argos_runtime.ArgosError as ex:
            raise TranslationError(str(ex),503) from None
    if name == 'legacy-google':
        return legacy(text, 'zh-CN' if target == 'zh' else 'en')
    if name != 'libretranslate':
        raise TranslationError('Public translation provider is disabled.', 503)
    payload = {'q': text, 'source': 'auto', 'target': target, 'format': 'text'}
    key = os.environ.get('MATH_PUBLIC_TRANSLATION_API_KEY', '')
    if key:
        payload['api_key'] = key
    request = urllib.request.Request(os.environ['MATH_PUBLIC_TRANSLATION_URL'],
                                     data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    # Never forward configured credentials to a redirect destination.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
            raw = response.read(100001)
        if len(raw) > 100000:
            raise ValueError('Oversized response')
        result = json.loads(raw)['translatedText']
        if not isinstance(result, str) or not result.strip() or len(result) > 20000:
            raise ValueError('Invalid response')
        return result
    except (OSError, ValueError, KeyError, TypeError):
        raise TranslationError('Public translation provider failed. Original content is unchanged.', 503) from None


# Protect entire math/code/URL spans; never interpolate a student's private data.
PROTECTED = re.compile(r'```[\s\S]*?```|`[^`\n]+`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|https?://[^\s<>。；，！？、]+|[\w.+-]+@[\w.-]+\.[A-Za-z]+|\b[A-Za-z][\w]*(?:\([^\n=]*?\))?\s*=\s*[^\n,;。]+|\b[A-Z]{2,}\b')


# Conservative plain-text arithmetic protection in addition to delimited LaTeX.
ATOM = r'(?:\d+(?:\.\d+)?[A-Za-z]?|[A-Za-z](?:_\{?[A-Za-z0-9]+\}?|[²³])?)'
INLINE_MATH = re.compile(r'(?<!\w)'+ATOM+r'(?:[ \t]*[+*/^=×÷≤≥≠±−-][ \t]*(?:'+ATOM+r'|\([^\n)]+\)))+')
LATEX_COMMAND = re.compile(r'\\[A-Za-z]+(?:\[[^\]\n]*\])?(?:\{(?:[^{}\n]|\{[^{}\n]*\})*\})*')


def protected_spans(text, terms):
    spans = [(m.start(),m.end()) for pattern in (PROTECTED,INLINE_MATH,LATEX_COMMAND) for m in pattern.finditer(text)]
    # Capitalized proper-name phrases plus explicit names supplied by the teacher.
    terms = [*terms, *re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)]
    for term in terms:
        if term:
            spans.extend((m.start(), m.end()) for m in re.finditer(re.escape(term), text))
    merged = []
    for a, b in sorted(spans):
        if merged and a < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def protect(text, terms):
    pieces, replacements, cursor = [], {}, 0
    prefix = 'MSKEEP' + secrets.token_hex(12).upper()
    for index, (a, b) in enumerate(protected_spans(text, terms)):
        token = f'{prefix}X{index}END'
        pieces.extend((text[cursor:a], token)); replacements[token] = text[a:b]; cursor = b
    pieces.append(text[cursor:])
    return ''.join(pieces), replacements


def restore(text, replacements):
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise TranslationError('Invalid translated content.', 502)
    for token, original in replacements.items():
        if text.count(token) != 1:
            raise TranslationError('Translation did not preserve protected content.', 502)
        text = text.replace(token, original)
    return text


def terms_for(c):
    terms = config(c)['terms']
    terms += [r['value'] for r in c.execute("SELECT value FROM settings WHERE key IN ('name','teacher')")]
    return terms


def check_protected(original, translated, terms):
    for a, b in protected_spans(original, terms):
        if translated.count(original[a:b]) < original.count(original[a:b]):
            raise TranslationError('Translation did not preserve protected content.', 409)


def public(c, language):
    originals = sources(c,public=True)
    if language not in ('en', 'zh'):
        raise TranslationError('Invalid translation language.')
    rows = c.execute('SELECT source_key,source_hash,approved FROM public_translations WHERE target=? AND approved IS NOT NULL', (language,))
    return {'translations': {r['source_key']: {'text': r['approved'], 'original': originals[r['source_key']]}
            for r in rows if r['source_key'] in originals and digest(originals[r['source_key']]) == r['source_hash']}}


def admin(c):
    originals = sources(c)
    rows = [dict(r) for r in c.execute('SELECT * FROM public_translations')
            if r['source_key'] in originals and digest(originals[r['source_key']]) == r['source_hash']]
    previous=[dict(r) for r in c.execute('SELECT * FROM public_translations ORDER BY updated DESC')
              if r['source_key'] in originals and digest(originals[r['source_key']])!=r['source_hash']]
    return {'config': config(c), 'sources': [{'key': k, 'original': v, 'source_hash': digest(v)} for k, v in originals.items()],
            'translations': rows,'previous_translations':previous}


def action(db, data, legacy):
    op = data.get('action')
    if op == 'config':
        terms = data.get('terms', [])
        if not isinstance(data.get('enabled'), bool) or not isinstance(terms, list) or len(terms) > 100 or any(not isinstance(x, str) or not 1 <= len(x) <= 120 for x in terms):
            raise TranslationError('Invalid translation settings.')
        with db() as c:
            c.execute('UPDATE public_translation_config SET enabled=?,terms=? WHERE id=1', (int(data['enabled']), json.dumps(terms)))
        return {'ok': True}
    key, target = data.get('key'), data.get('target')
    if not isinstance(key, str) or target not in ('en', 'zh'):
        raise TranslationError('Invalid translation source or language.')
    with db() as c:
        original = sources(c).get(key)
        if original is None:
            raise TranslationError('Public translation source not found.', 404)
        source_hash = digest(original)
        if data.get('source_hash') != source_hash:
            raise TranslationError('Source content changed. Refresh before translating.', 409)
        terms = terms_for(c)
        conf = config(c)
        existing = c.execute('SELECT * FROM public_translations WHERE source_key=? AND target=? AND source_hash=?', (key, target, source_hash)).fetchone()
        if op == 'generate':
            if data.get('offline_only') and conf['provider']!='argos':
                raise TranslationError('OWNER offline translation is unavailable.',503)
            if not conf['enabled'] or not conf['configured']:
                raise TranslationError('Public translation provider is disabled.', 503)
            if not original.strip():
                raise TranslationError('Write a public description before translating.')
            if existing and not data.get('regenerate', False):
                return {'ok': True, 'cached': True, 'draft': existing['draft']}
        elif op not in ('save', 'approve'):
            raise TranslationError('Invalid translation action.')
    if op == 'generate':
        protected, replacements = protect(original, terms)
        try:
            draft = restore(translate(protected, target, legacy), replacements)
        except TranslationError:
            raise
        except Exception:
            raise TranslationError('Public translation provider failed. Original content is unchanged.', 503) from None
    else:
        draft = data.get('text')
        if not isinstance(draft, str) or not draft.strip() or len(draft) > 20000:
            raise TranslationError('Invalid translated content.')
    check_protected(original, draft, terms)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        if sources(c).get(key) != original or terms_for(c) != terms:
            raise TranslationError('Source content changed. Refresh before translating.', 409)
        latest = c.execute('SELECT revision FROM public_translations WHERE source_key=? AND target=? AND source_hash=?', (key, target, source_hash)).fetchone()
        # Reject stale browser tabs and provider responses racing a teacher edit.
        revision = existing['revision'] if existing else 0
        if (latest['revision'] if latest else 0) != revision or (op != 'generate' and data.get('revision', 0) != revision):
            raise TranslationError('Translation changed. Refresh before saving.', 409)
        if op == 'generate' and not config(c)['enabled']:
            raise TranslationError('Public translation provider is disabled.', 503)
        c.execute('''INSERT INTO public_translations(source_key,target,source_hash,draft,approved,updated) VALUES (?,?,?,?,?,?)
          ON CONFLICT(source_key,target,source_hash) DO UPDATE SET draft=excluded.draft,
          approved=CASE WHEN ? THEN excluded.approved ELSE public_translations.approved END,
          revision=public_translations.revision+1,updated=excluded.updated''',
          (key, target, source_hash, draft, draft if op == 'approve' else None, time.time(), op == 'approve'))
    return {'ok': True, 'cached': False, 'draft': draft}
