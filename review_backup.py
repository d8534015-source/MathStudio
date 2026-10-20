"""Verified stopped-review backup and fail-closed restore to a NEW directory.

Never runs automatically. Select review data explicitly. Backups contain private
information and must be kept off Git, encrypted and access restricted by OWNER.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3


def file_digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.digest()


def copy_verified(source,destination,port=5063,restore=False):
    source=Path(source).resolve();destination=Path(destination).resolve()
    if destination.exists() or source==destination or source in destination.parents:raise ValueError('Choose a new, separate backup/restore directory.')
    with socket.socket() as probe:
        probe.settimeout(.5)
        if probe.connect_ex(('127.0.0.1',port))==0:raise ValueError('Stop the selected review OWNER before backup/restore.')
    if not source.is_dir() or any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in [source,*source.rglob('*')]):raise ValueError('Only a regular explicitly selected review data folder is supported.')
    shutil.copytree(source,destination)
    files=[p for p in source.rglob('*') if p.is_file()]
    for path in files:
        if file_digest(path)!=file_digest(destination/path.relative_to(source)):raise ValueError('Backup hash verification failed.')
    for name in ('posts.db','review-features.sqlite3'):
        path=destination/name
        if path.exists():
            with sqlite3.connect(path) as c:
                if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup database integrity failed.')
                if restore:
                    tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    for table in ('desktop_credentials','student_credentials'):
                        if table in tables:c.execute('DELETE FROM '+table)
                    for table in ('guardian_scopes','standing_scopes','recording_codes','recording_subjects'):
                        if table in tables:c.execute('UPDATE '+table+' SET revoked=1')
    return {'hashes_verified':len(files),'integrity':'passed','restored_to_new_directory':restore,'credentials_and_sharing_revoked':restore}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['backup','restore']);p.add_argument('--from-data',type=Path,required=True);p.add_argument('--to-data',type=Path,required=True);p.add_argument('--port',type=int,default=5063);a=p.parse_args()
    print(json.dumps(copy_verified(a.from_data,a.to_data,a.port,a.action=='restore')))
if __name__=='__main__':main()
