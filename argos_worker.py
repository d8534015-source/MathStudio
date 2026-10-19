"""One bounded, CPU-only inference child. Model/dependency installation is never done here."""
import contextlib
import json
import os
import re
import socket
import sys


def deny_network(*args, **kwargs):
    raise OSError('Network is disabled during offline translation.')


def sentencepiece_failure(error):
    # Native exception messages can contain paths and input text. Emit only
    # fixed labels for known SentencePiece/pybind failure categories.
    message=str(error)
    status=re.match(r'^(INTERNAL|INVALID_ARGUMENT|NOT_FOUND|DATA_LOSS|FAILED_PRECONDITION|UNIMPLEMENTED|OUT_OF_RANGE|RESOURCE_EXHAUSTED):',message)
    labels=['sp_status='+status[1]] if status else []
    location=re.search(r'\b(sentencepiece_processor|normalizer|model_interface|unigram_model|bpe_model|char_model|word_model)\.cc\((\d{1,6})\)',message)
    if location:labels.append('sp_native='+location[1]+':'+location[2])
    reasons=(('Unable to cast Python instance','python_cpp_cast'),
             ('Input must be str or bytes','input_type'),
             ('List elements must be str or bytes','input_type'),
             ('invalid UTF-8','invalid_utf8'),('Invalid UTF-8','invalid_utf8'),
             ('could not parse ModelProto','model_proto'),
             ('Model is not initialized','model_not_initialized'),
             ('unk is not defined','missing_unk'),
             ('Vocabulary size is 0','empty_vocabulary'),
             ('BOS token is not defined','missing_bos'),
             ('EOS token is not defined','missing_eos'))
    reason=next((label for fragment,label in reasons if fragment in message),'unclassified')
    return labels+['sp_reason='+reason]


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
        frames=[];tb=error.__traceback__;sentencepiece_frame=False
        while tb is not None:
            module=tb.tb_frame.f_globals.get('__name__','')
            sentencepiece_frame=sentencepiece_frame or module=='sentencepiece' or module.startswith('sentencepiece.')
            function=tb.tb_frame.f_code.co_name
            if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9.]{0,119}',module) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,79}',function):
                frames.append(module+'.'+function+':'+str(tb.tb_lineno))
            tb=tb.tb_next
        if sentencepiece_frame:details.extend(sentencepiece_failure(error))
        details.extend('at='+frame for frame in frames[-4:])
        error=error.__cause__ if error.__cause__ is not None else (None if error.__suppress_context__ else error.__context__)
    return '; '.join(details)[:1500]


def profile():
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parent/'packaging'/'argos'/'profile.json').read_text(encoding='utf-8'))


def inspect_tokenizer(pkg):
    # Fixed public test inputs only. No token values, model paths, vocabulary
    # entries or arbitrary exception messages enter this diagnostic report.
    from argostranslate.tokenizer import SentencePieceTokenizer
    tokenizer=pkg.tokenizer
    if not isinstance(tokenizer,SentencePieceTokenizer):return {'type':'other','status':'unsupported_probe'}
    report={'type':'sentencepiece','status':'failed','probes':[]}
    try:
        processor=tokenizer.lazy_processor()
        report['vocabulary_size']=processor.get_piece_size()
    except Exception as error:
        report['phase']='load';report['diagnostic']=safe_diagnostic(error);return report
    samples=['我们一起学习数学。','我们解一个方程。'] if pkg.from_code=='zh' else ['We learn mathematics together.','We solve an equation.']
    for api in ('argos_str','utf8_bytes','str_ids'):
        for index,text in enumerate(samples):
            item={'api':api,'sample':index+1}
            try:
                if api=='argos_str':tokens=tokenizer.encode(text)
                else:tokens=processor.encode(text.encode('utf-8') if api=='utf8_bytes' else text,out_type=str if api=='utf8_bytes' else int)
                expected=str if api!='str_ids' else int
                valid=isinstance(tokens,list) and bool(tokens) and all(type(token) is expected for token in tokens)
                item['status']='passed' if valid else 'invalid_output'
                item['token_count']=len(tokens) if isinstance(tokens,list) else None
            except Exception as error:
                item['status']='failed';item['diagnostic']=safe_diagnostic(error)
            report['probes'].append(item)
    report['phase']='encode'
    if all(item['status']=='passed' for item in report['probes']):report['status']='passed'
    return report


def offline_environment():
    # Deny Python network I/O before importing optional libraries. ONNX's native
    # telemetry is disabled separately, before creating any inference session.
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.socket.sendto = deny_network
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    if os.name != 'nt':
        try: os.nice(10)
        except OSError: pass


def inspect_models(packages,versions):
    # Public model metadata only. Never include filesystem paths or model text.
    from pathlib import Path
    result=[]
    known_features={'space_before','capitalized','all_caps','numeric','start_of_para','end_of_para'}
    for pkg in packages:
        item={'from':pkg.from_code,'to':pkg.to_code,'version':str(pkg.package_version),
              'tokenizer':inspect_tokenizer(pkg)}
        resources=pkg.package_path/'stanza'/'resources.json'
        if resources.is_file() and resources.stat().st_size<2*1024**2:
            data=json.loads(resources.read_text(encoding='utf-8'))
            lang=data.get(pkg.from_code,{})
            item['legacy_resources']={'packages': 'packages' in lang,'default_processors':'default_processors' in lang}
        checkpoints=list((pkg.package_path/'stanza').glob('*/tokenize/*.pt'))
        if len(checkpoints)==1:
            try:
                import torch
                checkpoint=torch.load(checkpoints[0],map_location='cpu',weights_only=True)
                config=checkpoint['config']
                item['legacy_checkpoint']={'feat_dropout':'feat_dropout' in config,'lexicon':'lexicon' in checkpoint,
                    'features':[x if x in known_features else 'unknown' for x in config.get('feat_funcs',[])[:20]]}
            except Exception as error:
                item['legacy_checkpoint']={'diagnostic':safe_diagnostic(error)}
        result.append(item)
    return {'python':sys.version.split()[0],'profile':profile()['id'],'versions':versions,'models':result}


def initialize(inspect=False):
    from importlib.metadata import version
    import hashlib
    expected=profile()
    versions={name:version(name) for name in expected['versions']}
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from argostranslate import package,settings,translate
    packages=[p for p in package.get_installed_packages() if (p.from_code,p.to_code) in [('en','zh'),('zh','en')]]
    if inspect:
        report=inspect_models(packages,versions)
        report['compatible_runtime']=versions==expected['versions']
        report['configuration']={'device':settings.device,'chunk_type':settings.chunk_type.name,'provider':settings.model_provider.name}
        return translate,report
    if versions!=expected['versions']:raise ValueError('Runtime versions do not match profile')
    if settings.device!='cpu' or settings.model_provider!=settings.ModelProvider.OPENNMT or settings.chunk_type!=settings.ChunkType.MINISBD:
        raise ValueError('Offline CPU MiniSBD configuration required')
    for pair,spec in expected['sentence_models'].items():
        source,target=pair.split('_')
        matches=[p for p in packages if p.from_code==source and p.to_code==target and str(p.package_version)=='1.9']
        if len(matches)!=1:raise ValueError('Model unavailable')
        folder=matches[0].package_path/'minisbd'
        files=list(folder.glob('*.onnx'));model=folder/spec['filename']
        if files!=[model] or not model.is_file() or model.stat().st_size>32*1024**2:
            raise ValueError('Sentence model unavailable')
        with model.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=spec['sha256']:
                raise ValueError('Sentence model checksum mismatch')
    return translate,None


def run(payload):
    offline_environment()
    if payload.get('operation')=='inspect':return initialize(inspect=True)[1]
    target=payload.get('target');pieces=payload.get('pieces')
    if target not in ('en','zh') or not isinstance(pieces,list) or any(not isinstance(x,str) for x in pieces) or sum(map(len,pieces))>20000:
        raise ValueError('Invalid request')
    translate,_=initialize()
    from opencc import OpenCC
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


def main():
    try:
        # Parent callers use a private response file, independent of even cached
        # native stdout handles. The pipe fallback is for direct/manual invocation.
        result_file=os.environ.get('MATH_ARGOS_RESULT_FILE')
        descriptor=os.open(result_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600) if result_file else os.dup(sys.stdout.fileno())
        with os.fdopen(descriptor,'wb') as protocol:
            sys.stdout.flush()
            os.dup2(sys.stderr.fileno(),sys.stdout.fileno())
            if os.name=='nt':
                import ctypes
                import msvcrt
                setter=ctypes.WinDLL('kernel32',use_last_error=True).SetStdHandle
                setter.argtypes=(ctypes.c_uint32,ctypes.c_void_p);setter.restype=ctypes.c_int
                if not setter(0xfffffff5,msvcrt.get_osfhandle(sys.stderr.fileno())):
                    raise OSError('Cannot isolate worker protocol output')
            payload=json.loads(sys.stdin.read(100001))
            with contextlib.redirect_stdout(sys.stderr):result=run(payload)
            protocol.write(json.dumps(result,ensure_ascii=False).encode('utf-8')+b'\n')
            protocol.flush()
        return 0
    except Exception as error:
        # Setup reads only this safe record. Browser inference discards all stderr.
        print('\nARGOS_DIAGNOSTIC '+safe_diagnostic(error),file=sys.stderr,flush=True)
        return 2


if __name__=='__main__':
    sys.exit(main())
