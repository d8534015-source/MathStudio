"""Fail a review build if OWNER code, translation runtimes or models are bundled."""
import json
from pathlib import Path
import re

FORBIDDEN={'classroom_recording','recording_cloud','server','owner_auth','owner_review','website_content','public_translations','argos_runtime','argos_worker','argos_setup',
    'diagnose_argos','verify_argos_models','argostranslate','minisbd','sentencepiece','ctranslate2',
    'onnxruntime','onnx','torch','stanza','spacy','transformers','runtime_setup','owner_launcher','document_worker'}


def check_names(modules,files):
    modules=list(modules);files=list(files);bad=[]
    for name in modules:
        if str(name).split('.')[0] in FORBIDDEN:bad.append(str(name))
    for name in files:
        parts=set(re.split(r'[/\\.\-]',str(name).lower()))
        native=re.search(r'(?:^|[/\\._-])(?:lib)?(?:torch|onnxruntime|ctranslate2|sentencepiece)',str(name).lower())
        if parts&FORBIDDEN or native or str(name).lower().endswith(('.argosmodel','.onnx','.pt','.model','model.bin','.db','.sqlite','.sqlite3')):
            bad.append(str(name))
    if bad:raise ValueError('Teacher payload contains forbidden OWNER/runtime/model files: '+', '.join(sorted(bad)[:20]))
    return {'status':'passed','python_modules_checked':len(modules),'files_checked':len(files),
            'server_translation_dependencies':0,'model_files':0}


def inspect_payload(root):
    # Inspect actual frozen PYZ modules, not only filenames in the build folder.
    from PyInstaller.archive.readers import CArchiveReader
    root=Path(root);archive=CArchiveReader(str(root/'MathStudioClient.exe'))
    embedded=[name for name,entry in archive.toc.items() if entry[-1]=='z']
    if len(embedded)!=1:raise ValueError('Expected exactly one inspectable client Python archive')
    modules=list(archive.open_embedded_archive(embedded[0]).toc)
    modules.extend(archive.toc)
    files=[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()]
    return check_names(modules,files)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('payload',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=inspect_payload(args.payload)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
