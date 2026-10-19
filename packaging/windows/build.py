"""Rebuild on Windows x64 with CPython 3.13.12. Never reads private source state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import venv

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
INNO_URL='https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe'
INNO_SHA='0362a383ed217d4c4239b5933866dd96d3eb2102737da92f80f6057a4b40df2f'


def run(command,**kwargs):
    subprocess.run([str(x) for x in command],check=True,**kwargs)


def assets(review=False):
    from PIL import Image,ImageDraw
    target=HERE/'generated';target.mkdir(exist_ok=True)
    role=json.loads((ROOT/'teacher_package_role.json').read_text(encoding='utf-8'))
    if review:role.update(review=True,review_profile='MathStudioClassroomReview')
    (target/'teacher_package_role.json').write_text(json.dumps(role)+'\n',encoding='utf-8')
    image=Image.new('RGBA',(256,256),'#0d2f34');draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((8,8,248,248),radius=48,fill='#0d2f34',outline='#22a699',width=10)
    draw.line([(55,190),(55,65),(128,145),(201,65),(201,190)],fill='#dff5ed',width=20,joint='curve')
    image.save(target/'MathStudio.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    description='MathStudio Teacher Review' if review else 'MathStudio Teacher'
    (target/'version.txt').write_text("""VSVersionInfo(ffi=FixedFileInfo(filevers=(41,6,6,0),prodvers=(41,6,6,0),mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','MathStudio project'),StringStruct('FileDescription','MathStudio Teacher'),StringStruct('FileVersion','41.6.6'),StringStruct('ProductName','MathStudio'),StringStruct('ProductVersion','41.6.6'),StringStruct('OriginalFilename','MathStudioClient.exe')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])""".replace("StringStruct('FileDescription','MathStudio Teacher')","StringStruct('FileDescription',"+repr(description)+")"),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--review',action='store_true',help='Isolated review installer; does not replace the installed teacher app')
    parser.add_argument('--output',type=Path,default=ROOT/'work'/'windows-build')
    args=parser.parse_args();output=args.output.resolve()
    if sys.platform!='win32':raise SystemExit('A genuine Windows x64 runner is required; cross-building a Windows EXE on Linux is unsupported.')
    if sys.version_info[:3]!=(3,13,12):raise SystemExit('Use the pinned x64 CPython 3.13.12 Windows build runtime.')
    output.mkdir(parents=True,exist_ok=True)
    if not args.freeze:
        environment=output/'venv';venv.EnvBuilder(with_pip=True).create(environment)
        python=environment/'Scripts'/'python.exe'
        run([python,'-m','pip','install','--require-hashes','--only-binary=:all:',
            '--index-url','https://pypi.org/simple','-r',ROOT/'requirements.txt','-r',HERE/'requirements-build.txt'])
        run([python,'-m','pip','check'])
        run([python,__file__,'--freeze','--output',output]+(['--review'] if args.review else []));return
    assets(args.review)
    # Explicit manifest validation detects source tampering before freezing.
    from_source=subprocess.run([sys.executable,str(ROOT/'release_package.py'),'--kind','teacher'],check=True)
    run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--distpath',output/'dist',
        '--workpath',output/'freeze',HERE/'MathStudio.spec'],cwd=ROOT)
    from check_client_payload import inspect_payload
    payload_check=inspect_payload(output/'dist'/'MathStudioClient')
    # Compiler is downloaded only from its pinned upstream release; no discovered scripts.
    compiler=output/'inno-installer.exe'
    with urllib.request.urlopen(INNO_URL,timeout=60) as response:compiler.write_bytes(response.read())
    if hashlib.sha256(compiler.read_bytes()).hexdigest()!=INNO_SHA:raise RuntimeError('Inno Setup compiler checksum mismatch.')
    run([compiler,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/DIR='+str(output/'inno')])
    run([output/'inno'/'ISCC.exe','/DBuildRoot='+str(output)]+(['/DReviewBuild=1'] if args.review else [])+[HERE/'MathStudio.iss'])
    installer=output/'installer'/('MathStudio-Classroom-Review.exe' if args.review else 'MathStudio.exe')
    (installer.parent/'client-isolation.json').write_text(json.dumps(payload_check,indent=2)+'\n',encoding='utf-8')
    digest=hashlib.sha256(installer.read_bytes()).hexdigest()
    (installer.parent/'SHA256SUMS.txt').write_text(digest+'  '+installer.name+'\n',encoding='utf-8')
    from build_info import BUILD_ID
    inventory={str(p.relative_to(output/'dist')):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (output/'dist').rglob('*') if p.is_file()}
    (installer.parent/'build-manifest.json').write_text(json.dumps({'build':BUILD_ID,'python':sys.version,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,encoding='utf-8').strip(),
        'review_head_commit':os.environ.get('REVIEW_HEAD_SHA') or None,
        'source_manifest_sha256':hashlib.sha256((ROOT/'release_manifest.json').read_bytes()).hexdigest(),
        'requirements_sha256':hashlib.sha256((ROOT/'requirements.txt').read_bytes()).hexdigest(),
        'build_requirements_sha256':hashlib.sha256((HERE/'requirements-build.txt').read_bytes()).hexdigest(),
        'compiler_sha256':INNO_SHA,'signed':False,'review':args.review,'payload':inventory},indent=2)+'\n',encoding='utf-8')
    print('Unsigned installer built: '+str(installer)+' SHA256 '+digest)


if __name__=='__main__':main()
