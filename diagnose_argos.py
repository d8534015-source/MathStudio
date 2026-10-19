"""Explicit offline compatibility check of existing official models; never activates."""
import argparse
import contextlib
import io
import json
from pathlib import Path
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
            result=runtime.run_worker({'operation':'inspect'},base=base,packages=packages)
            report['inspection_protocol']=runtime.worker_response_info(result)
            if result.returncode:
                report['worker_failure']=runtime.worker_diagnostic(result.stderr)
                raise RuntimeError('Inspection worker failed')
            report['inspection']=runtime.worker_json(result.response)
            with contextlib.redirect_stdout(io.StringIO()):report['examples']=setup.self_test(base,packages)
            report['status']='passed_staged_real_models'
    except Exception as error:
        report['diagnostic']=safe_diagnostic(error)
        # self_test produces a bounded, sanitized message, including direction.
        message=str(error)
        if message.startswith('Offline model self-test failed'):
            report['self_test_failure']=message
        if hasattr(error,'worker_protocol'):report['self_test_protocol']=error.worker_protocol
    try:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    except OSError:
        print('Cannot write diagnostic report. Choose a writable private output folder.');return 1
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='passed_staged_real_models' else 1


if __name__=='__main__':raise SystemExit(main())
