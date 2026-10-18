"""One bounded, CPU-only inference child. Model/dependency installation is never done here."""
import contextlib
import json
import os
import re
import socket
import sys


def deny_network(*args, **kwargs):
    raise OSError('Network is disabled during offline translation.')


def run(payload):
    # Set before optional imports. Missing resources must fail, never fetch anything.
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    if os.name != 'nt':
        try: os.nice(10)
        except OSError: pass
    import stanza
    original_pipeline = stanza.Pipeline
    def offline_pipeline(*args, **kwargs):
        kwargs['download_method'] = None
        return original_pipeline(*args, **kwargs)
    stanza.Pipeline = offline_pipeline
    from argostranslate import translate
    from opencc import OpenCC
    target = payload['target']
    if target not in ('en','zh') or not isinstance(payload['pieces'],list) or sum(len(x) for x in payload['pieces']) > 20000:
        raise ValueError('Invalid request')
    source = 'en' if target == 'zh' else 'zh'
    languages = {language.code:language for language in translate.get_installed_languages()}
    if source not in languages or target not in languages:
        raise ValueError('Model unavailable')
    engine = languages[source].get_translation(languages[target])
    if engine is None:
        raise ValueError('Model unavailable')
    simplified = OpenCC('t2s') if target == 'zh' else None
    result=[]
    for piece in payload['pieces']:
        # Preserve spacing adjoining protected tokens; do not send empty punctuation fragments.
        match=re.fullmatch(r'(\s*)([\s\S]*?)(\s*)',piece)
        leading,body,trailing=match.groups()
        if not re.search(r'[A-Za-z\u3400-\u9fff]',body):
            result.append(piece);continue
        chunks=[]
        # Bound model input even for unusually long unpunctuated descriptions.
        while len(body)>500:
            cut=max(body.rfind(' ',0,500),body.rfind('。',0,500)+1,body.rfind('\n',0,500)+1)
            if cut<100:cut=500
            chunks.append(body[:cut]);body=body[cut:]
        chunks.append(body)
        value=' '.join(engine.translate(chunk) for chunk in chunks)
        if simplified:value=simplified.convert(value)
        result.append(leading+value+trailing)
    return {'pieces':result}


if __name__=='__main__':
    try:
        payload=json.loads(sys.stdin.read(100001))
        with contextlib.redirect_stdout(sys.stderr):result=run(payload)
        print(json.dumps(result,ensure_ascii=False))
    except Exception:
        # Package errors may include filesystem paths; do not expose them to browsers.
        sys.exit(2)
