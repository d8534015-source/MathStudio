"""Explicit OWNER-selected FFmpeg, bounded stream-copy indexing for seekable playback.

No binary is discovered/downloaded automatically. Original downloads are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from review_features import MAX_BYTES,PART_BYTES


def configured(data):
    path=Path(data)/'recording-processor.json'
    try:
        if path.is_symlink() or path.stat().st_size>4096:return None
        config=json.loads(path.read_text());selected=Path(config['ffmpeg'])
        return selected if selected.is_absolute() and selected.is_file() and not selected.is_symlink() and hashlib.sha256(selected.read_bytes()).hexdigest()==config.get('sha256') else None
    except (OSError,ValueError,KeyError,TypeError):return None


def remux(executable,source,destination,mime,cancelled=None):
    args=[str(executable),'-nostdin','-hide_banner','-loglevel','error','-y','-protocol_whitelist','file,pipe','-i',str(source),'-map','0:v:0','-map','0:a?','-c','copy']
    if mime=='video/mp4':args+=['-movflags','+faststart']
    args+=[str(destination)]
    try:
        process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        deadline=time.monotonic()+180
        try:
            while process.poll() is None:
                if (cancelled is not None and cancelled.is_set()) or time.monotonic()>=deadline or (destination.exists() and destination.stat().st_size>MAX_BYTES+PART_BYTES):
                    process.kill();process.wait();raise RuntimeError('Seekable playback indexing exceeded its bounds.')
                try:process.wait(timeout=.1)
                except subprocess.TimeoutExpired:pass
            result=process
        finally:
            if process.poll() is None:process.kill();process.wait()

        if result.returncode:raise RuntimeError('FFmpeg indexing failed (exit='+str(int(result.returncode))+').')
        if not destination.is_file() or not 0<destination.stat().st_size<=MAX_BYTES+PART_BYTES:raise RuntimeError('FFmpeg output validation failed.')
    except (OSError,subprocess.TimeoutExpired):raise RuntimeError('Seekable playback processor unavailable or timed out.') from None


def process(store,row):
    """Single background worker. All transfer buffers remain at most 8MiB."""
    executable=configured(store.data)
    if not executable:return False
    feature=store.features;rid=row['id']
    with feature.db() as c:
        c.execute("INSERT OR IGNORE INTO recording_playback(id,state) VALUES (?,'processing')",(rid,))
        job=dict(c.execute('SELECT * FROM recording_playback WHERE id=?',(rid,)).fetchone())
    if job['state']=='ready':return True
    suffix='.mp4' if row['mime']=='video/mp4' else '.webm';source=store.folder/(rid+suffix);indexed=store.folder/(rid+'.indexed'+suffix)
    stage='source'
    try:
        if not indexed.exists():
            import shutil
            if shutil.disk_usage(store.folder).free<row['bytes']*2+256*1024**2:raise RuntimeError('Not enough disk space for seekable playback processing.')
            if not source.exists():
                with store.cloud.open(row) as response,source.open('wb') as output:
                    total=0;deadline=time.monotonic()+180
                    while True:
                        if store.closed.is_set() or time.monotonic()>deadline:raise RuntimeError('Playback preparation transfer timed out.')
                        chunk=response.read(PART_BYTES)
                        if not chunk:break
                        total+=len(chunk)
                        if total>MAX_BYTES:raise RuntimeError('Original recording exceeded its validated size.')
                        output.write(chunk)
                if total!=row['bytes']:raise RuntimeError('Incomplete original recording transfer.')
            temporary=store.folder/(rid+'.indexing'+suffix)
            stage='index'
            try:remux(executable,source,temporary,row['mime'],store.closed);temporary.replace(indexed)
            finally:temporary.unlink(missing_ok=True)
        stage='playback-upload'
        def checkpoint(upload,parts):
            with feature.db() as c:c.execute('UPDATE recording_playback SET upload_id=?,parts=? WHERE id=?',(upload,json.dumps(parts),rid))
        if not store.cloud.upload({**row,'id':rid+'_playback','upload_id':job['upload_id'],'parts':job['parts']},indexed,checkpoint,max_parts=1):return False
        with feature.db() as c:c.execute("UPDATE recording_playback SET state='ready',bytes=? WHERE id=?",(indexed.stat().st_size,rid))
        source.unlink(missing_ok=True);indexed.unlink(missing_ok=True);return True
    except Exception as error:
        import re
        code=type(error).__name__ if isinstance(error,(OSError,RuntimeError,ValueError)) else 'error'
        match=re.fullmatch(r'FFmpeg indexing failed \(exit=(-?\d+)\)\.',str(error))
        if match:code+=':exit='+match[1]
        with feature.db() as c:c.execute("UPDATE recording_playback SET state='failed' WHERE id=?",(rid,))
        with feature.db() as c:c.execute("UPDATE recording_options SET error=? WHERE id=?",('playback-'+stage+':'+code,rid))
        return False


def main():
    from runtime_paths import data_directory
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['configure','status']);parser.add_argument('--data',type=Path,default=data_directory(Path(__file__).parent));parser.add_argument('--path',type=Path)
    args=parser.parse_args()
    if args.action=='configure':
        if not args.path or not args.path.is_absolute() or args.path.is_symlink() or not args.path.is_file():raise SystemExit('Select an absolute path to a trusted FFmpeg executable.')
        try:subprocess.run([str(args.path),'-version'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=True)
        except (OSError,subprocess.SubprocessError):raise SystemExit('Selected FFmpeg could not be verified.') from None
        args.data.mkdir(parents=True,exist_ok=True);(args.data/'recording-processor.json').write_text(json.dumps({'ffmpeg':str(args.path.resolve()),'sha256':hashlib.sha256(args.path.read_bytes()).hexdigest()})+'\n')
    print('Trusted recording processor configured.' if configured(args.data) else 'Recording processor unavailable; authenticated original downloads remain possible, absentee playback/sharing is blocked until indexing succeeds.')

if __name__=='__main__':main()
