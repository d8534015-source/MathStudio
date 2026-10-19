"""One bounded, CPU-only inference child. Model/dependency installation is never done here."""
import contextlib
import json
import os
import re
import socket
import sys


def deny_network(*args, **kwargs):
    raise OSError('Network is disabled during offline translation.')


def safe_diagnostic(error):
    """Code locations and error types only: never exception text, paths or locals."""
    details=[];seen=set()
    while error is not None and id(error) not in seen and len(seen)<3:
        seen.add(id(error))
        name=type(error).__name__
        details.append('exception='+name if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,79}',name) else 'exception=Unknown')
        # Only fixed schema labels are safe to expose; arbitrary KeyError text is not.
        schema_keys={'feat_dropout','lexicon','config','model','vocab','vocab_size','emb_dim','hidden_dim','dropout','packages'}
        if isinstance(error,KeyError) and len(error.args)==1 and isinstance(error.args[0],str) and error.args[0] in schema_keys:
            details.append('missing_key='+error.args[0])
        for key in ('errno','winerror'):
            value=getattr(error,key,None)
            if type(value) is int:details.append(key+'='+str(value))
        frames=[];tb=error.__traceback__
        while tb is not None:
            module=tb.tb_frame.f_globals.get('__name__','')
            function=tb.tb_frame.f_code.co_name
            if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9.]{0,119}',module) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,79}',function):
                frames.append(module+'.'+function+':'+str(tb.tb_lineno))
            tb=tb.tb_next
        details.extend('at='+frame for frame in frames[-4:])
        error=error.__cause__ if error.__cause__ is not None else (None if error.__suppress_context__ else error.__context__)
    return '; '.join(details)[:1500]


def compatible_stanza_resources(resources):
    # Older bundled tokenizers name defaults directly; Stanza 1.10 expects packages.
    # Adapt only that known schema, without changing models or inventing defaults.
    result=resources.copy()
    for lang,info in resources.items():
        if isinstance(info,dict) and 'packages' not in info and isinstance(info.get('default_processors'),dict):
            result[lang]={**info,'packages':{'default':dict(info['default_processors'])}}
    return result


def compatible_tokenizer_checkpoint(checkpoint):
    # Legacy Stanza saved exactly model/vocab/config, before feature dropout and
    # lexicons existed. Preserve all weights and dimensions for strict loading.
    if not isinstance(checkpoint,dict) or set(checkpoint)!={'model','vocab','config'}:
        return checkpoint
    config=checkpoint['config']
    if not isinstance(config,dict) or 'feat_dropout' in config or not {'vocab_size','emb_dim','hidden_dim','dropout'}<=config.keys():
        return checkpoint
    return {**checkpoint,'config':{**config,'feat_dropout':0.0},'lexicon':None}


def offline_stanza_pipeline(pipeline,*args,**kwargs):
    from stanza.pipeline import core
    from stanza.models.tokenization import trainer
    loader=core.load_resources_json
    original_torch=trainer.torch
    def load_compatible(*load_args,**load_kwargs):
        return compatible_stanza_resources(loader(*load_args,**load_kwargs))
    class TokenizerTorch:
        def load(self,*load_args,**load_kwargs):
            # Keep Stanza's weights_only=True and normal strict load_state_dict.
            return compatible_tokenizer_checkpoint(original_torch.load(*load_args,**load_kwargs))
        def __getattr__(self,name):
            return getattr(original_torch,name)
    kwargs['download_method']=None
    # This patch is confined to the single inference child and this initialization.
    core.load_resources_json=load_compatible
    trainer.torch=TokenizerTorch()
    try:
        return pipeline(*args,**kwargs)
    finally:
        core.load_resources_json=loader
        trainer.torch=original_torch


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
        return offline_stanza_pipeline(original_pipeline,*args,**kwargs)
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
    except Exception as error:
        # Setup reads only this safe record. Browser inference discards all stderr.
        print('ARGOS_DIAGNOSTIC '+safe_diagnostic(error),file=sys.stderr,flush=True)
        sys.exit(2)
