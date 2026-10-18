"""Disposable Windows runner check: cleanup an owned child, leave another alive."""
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from owner_launcher import OwnedProcess


def main():
    if sys.platform!='win32':raise SystemExit('Windows job check requires Windows.')
    sleeper=[sys.executable,'-c','import time; time.sleep(60)']
    unrelated=subprocess.Popen(sleeper)
    owned=None
    try:
        owned=OwnedProcess(sleeper)
        assert owned.proc.poll() is None
        assert owned.job
        owned.close()
        assert owned.proc.poll() is not None
        assert unrelated.poll() is None
        target=Path('work/windows-build/installer/owner-cleanup-results.json')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({'windows_job_created':True,'owned_child_stopped':True,'unrelated_child_untouched':True})+'\n',encoding='utf-8')
        print('PASS: owned Windows child cleanup leaves unrelated child running')
    finally:
        if owned:owned.close()
        unrelated.terminate();unrelated.wait(timeout=5)


if __name__=='__main__':main()
