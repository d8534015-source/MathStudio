"""Explicit offline compatibility check of existing official models; never activates."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import argos_runtime as runtime
import argos_setup as setup
from argos_worker import safe_diagnostic


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-files',type=Path,required=True)
    parser.add_argument('--sbd-files',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report={'status':'failed','activation':'not performed by this diagnostic','profile':runtime.PROFILE['id']}
    try:
        setup.check_host()
        with setup.maintenance() as base,tempfile.TemporaryDirectory(prefix='diagnose-',dir=base) as scratch:
            packages=Path(scratch)/'packages';packages.mkdir()
            # No pip or downloads, no active model/config/database modifications.
            with contextlib.redirect_stdout(io.StringIO()):
                report['archives']=setup.prepare_models(base,packages,args.model_files,args.sbd_files,allow_download=False)
            env=runtime.environment(base);env['ARGOS_PACKAGES_DIR']=str(packages)
            result=subprocess.run([str(runtime.python_path()),'-I','-u',str(setup.ROOT/'argos_worker.py')],
                input=json.dumps({'operation':'inspect'}),encoding='utf-8',capture_output=True,
                timeout=runtime.TIMEOUT,cwd=base,env=env)
            if result.returncode:
                notes=[x for x in result.stderr.splitlines() if x.startswith('ARGOS_DIAGNOSTIC ')]
                import re
                report['worker_failure']=notes[-1] if notes and re.fullmatch(r'[A-Za-z0-9_.:=; -]{1,1600}',notes[-1]) else 'No safe worker record'
                raise RuntimeError('Inspection worker failed')
            report['inspection']=json.loads(result.stdout)
            with contextlib.redirect_stdout(io.StringIO()):report['examples']=setup.self_test(base,packages)
            report['status']='passed_staged_real_models'
    except Exception as error:
        report['diagnostic']=safe_diagnostic(error)
        # self_test produces a bounded, sanitized message, including direction.
        message=str(error)
        if message.startswith('Offline model self-test failed'):
            report['self_test_failure']=message
    try:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    except OSError:
        print('Cannot write diagnostic report. Choose a writable private output folder.');return 1
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='passed_staged_real_models' else 1


if __name__=='__main__':raise SystemExit(main())
