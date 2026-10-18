"""Explicit OWNER-only installation. Never imported or run by classroom requests."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import urllib.request
import venv
import zipfile
import argos_runtime
from runtime_paths import data_directory

ROOT=Path(__file__).resolve().parent
MODELS={
    'en_zh': {'url':'https://argos-net.com/v1/translate-en_zh-1_9.argosmodel','version':'1.9'},
    'zh_en': {'url':'https://argos-net.com/v1/translate-zh_en-1_9.argosmodel','version':'1.9'},
}


def stopped_owner():
    # Installation is maintenance work. Refuse even an idle OWNER on the fixed port.
    try:
        with socket.create_connection(('127.0.0.1',5051),timeout=1):
            raise RuntimeError('Stop OWNER and all lessons before installing translation dependencies or models.')
    except (ConnectionRefusedError,TimeoutError):
        pass


def check_host():
    if sys.version_info[:2] != (3,13) or struct.calcsize('P') != 8:
        raise RuntimeError('Run with 64-bit CPython 3.13: py -3.13 argos_setup.py install')
    if sys.platform not in ('win32','linux'):
        raise RuntimeError('This dependency lock supports Windows x64 and Linux x64 only.')
    stopped_owner()
    data=data_directory(ROOT)
    if data == ROOT or ROOT in data.parents:
        raise RuntimeError('Existing OWNER data is inside the application folder. Back it up, move it explicitly to a stable private folder and set MATH_DATA before setup. No data was moved.')


@contextlib.contextmanager
def maintenance():
    base=argos_runtime.home();base.mkdir(parents=True,exist_ok=True)
    lock=base/'.setup.lock'
    try:fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise RuntimeError('Translation setup is already running. A crash may leave .setup.lock; remove it only after confirming no setup or OWNER process is running.') from None
    try:
        os.close(fd);yield base
    finally:
        lock.unlink(missing_ok=True)


def file_digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source,'sha256').hexdigest()


def download_model(url,destination):
    # Only explicit setup performs network operations. Models are data, not scripts.
    with urllib.request.urlopen(url,timeout=60) as response, Path(destination).open('wb') as output:
        if not response.url.startswith('https://'):
            raise RuntimeError('Model download must stay on HTTPS.')
        size=0
        while block:=response.read(1024*1024):
            size+=len(block)
            if size>1024*1024*1024:raise RuntimeError('Model archive is unexpectedly large.')
            output.write(block)


def unpack_model(archive,destination,pair):
    with zipfile.ZipFile(archive) as source:
        entries=source.infolist()
        if len(entries)>10000 or sum(x.file_size for x in entries)>2*1024**3:
            raise RuntimeError('Model archive is unexpectedly large.')
        roots=set()
        for item in entries:
            name=PurePosixPath(item.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in item.filename or ':' in item.filename or not name.parts or (item.external_attr>>16)&0o170000==0o120000:
                raise RuntimeError('Unsafe model archive path.')
            roots.add(name.parts[0])
        if len(roots)!=1:raise RuntimeError('Expected one model package folder.')
        folder=next(iter(roots));metadata=json.loads(source.read(folder+'/metadata.json'))
        from_code,to_code=pair.split('_')
        if metadata.get('from_code')!=from_code or metadata.get('to_code')!=to_code or str(metadata.get('package_version'))!=MODELS[pair]['version']:
            raise RuntimeError('Model metadata does not match the pinned language pair/version.')
        if folder+'/model/model.bin' not in source.namelist():raise RuntimeError('Missing translation model.')
        source.extractall(destination)
    return folder


def install(model_files=None,wheelhouse=None):
    check_host()
    with maintenance() as base:
        runtime=base/'runtime'
        if not argos_runtime.python_path().exists():
            venv.EnvBuilder(with_pip=True).create(runtime)
        lock=ROOT/'packaging'/'argos'/('requirements-windows-py313.txt' if os.name=='nt' else 'requirements-linux-py313.txt')
        command=[str(argos_runtime.python_path()),'-m','pip','install','--require-hashes','--only-binary=:all:','-r',str(lock)]
        if wheelhouse:command+=['--no-index','--find-links',str(Path(wheelhouse).resolve())]
        else:command+=['--index-url','https://pypi.org/simple','--extra-index-url','https://download.pytorch.org/whl/cpu']
        subprocess.run(command,check=True)
        (base/'packages').mkdir(exist_ok=True)
        installed={}
        with tempfile.TemporaryDirectory(prefix='setup-',dir=base) as scratch:
            scratch=Path(scratch);packages=scratch/'packages';packages.mkdir()
            for pair,spec in MODELS.items():
                archive=Path(model_files)/('translate-'+pair+'-1_9.argosmodel') if model_files else scratch/(pair+'.argosmodel')
                if not model_files:
                    print('Downloading official free model:',pair,flush=True);download_model(spec['url'],archive)
                sha=file_digest(archive)
                folder=unpack_model(archive,packages,pair)
                installed[pair]={'folder':folder,'version':spec['version'],'url':spec['url'],'sha256':sha}
                print(pair,'SHA-256:',sha,flush=True)
            # Validate actual models with all network operations disabled before publication.
            env=argos_runtime.environment(base);env['ARGOS_PACKAGES_DIR']=str(packages)
            examples=[]
            for target,text in [('zh','We learn mathematics together.'),('en','我们一起学习数学。')]:
                result=subprocess.run([str(argos_runtime.python_path()),'-I','-u',str(ROOT/'argos_worker.py')],
                    input=json.dumps({'target':target,'pieces':[text]}),encoding='utf-8',stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,timeout=argos_runtime.TIMEOUT,cwd=base,env=env)
                if result.returncode:raise RuntimeError('Offline model self-test failed. No new models were activated.')
                translated=json.loads(result.stdout)['pieces'][0]
                if not translated.strip() or translated.strip()==text:raise RuntimeError('Offline model self-test produced no translation.')
                examples.append({'target':target,'source':text,'translation':translated})
                print(text,'->',translated,flush=True)
            replaced=[]
            try:
                for item in installed.values():
                    target=base/'packages'/item['folder'];backup=base/'packages'/(item['folder']+'.previous')
                    if backup.exists():raise RuntimeError('A previous model backup needs OWNER review before setup can continue.')
                    if target.exists():target.rename(backup)
                    replaced.append((target,backup))
                    (packages/item['folder']).rename(target)
                receipt={'schema':1,'argos':'1.11.0','python':sys.version.split()[0],'verified':True,
                         'dependencies_sha256':file_digest(lock),'models':installed,'offline_examples':examples}
                pending=base/'installation.pending.json'
                pending.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                pending.replace(base/'installation.json')
            except Exception:
                for target,backup in reversed(replaced):
                    if target.exists():shutil.rmtree(target)
                    if backup.exists():backup.rename(target)
                raise
            for _,backup in replaced:
                if backup.exists():shutil.rmtree(backup)
    if not argos_runtime.ready():raise RuntimeError('Installed models did not pass readiness checks.')
    # Explicit setup opts in to selecting the local provider, never to external translation.
    print('Offline models ready. Start OWNER with MATH_PUBLIC_TRANSLATION_PROVIDER=argos, then enable offline translation on /teacher/translations.')
    print('Stored outside application:',base)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('install','status'))
    parser.add_argument('--model-files',type=Path,help='Directory containing the two official .argosmodel files for disconnected setup.')
    parser.add_argument('--wheelhouse',type=Path,help='Pre-downloaded hash-locked wheels for disconnected setup.')
    args=parser.parse_args()
    if args.action=='status':
        print(json.dumps({'home':str(argos_runtime.home()),'ready':argos_runtime.ready()},indent=2));return
    try:install(args.model_files,args.wheelhouse)
    except (OSError,RuntimeError,ValueError,subprocess.SubprocessError,zipfile.BadZipFile) as ex:
        print('Offline translation setup failed:',str(ex),file=sys.stderr);sys.exit(1)


if __name__=='__main__':main()
