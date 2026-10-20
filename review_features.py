"""Additive review state in a separate SQLite file; never migrates account tables."""
import contextlib
import json
from pathlib import Path
import sqlite3
import time

GB=1_000_000_000
MAX_BYTES=5*GB
MAX_SECONDS=3*3600
WARN_BYTES=4*GB
WARN_SECONDS=150*60
PART_BYTES=8*1024**2


class Features:
    def __init__(self,data):
        self.path=Path(data)/'review-features.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS recording_context(id TEXT PRIMARY KEY,kind TEXT NOT NULL,start REAL NOT NULL,title TEXT NOT NULL,roster TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS local_chunks(id TEXT,sequence INTEGER,size INTEGER NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(id,sequence));
            CREATE TABLE IF NOT EXISTS recording_playback(id TEXT PRIMARY KEY,state TEXT NOT NULL,bytes INTEGER NOT NULL DEFAULT 0,upload_id TEXT NOT NULL DEFAULT '',parts TEXT NOT NULL DEFAULT '[]');
            CREATE TABLE IF NOT EXISTS recording_options(id TEXT PRIMARY KEY,mode TEXT NOT NULL,
              scope TEXT NOT NULL,subjects TEXT NOT NULL DEFAULT '[]',error TEXT NOT NULL DEFAULT '',
              stop_reason TEXT NOT NULL DEFAULT '',metrics TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS lesson_roster(class_id INTEGER,user_id INTEGER,PRIMARY KEY(class_id,user_id));
            CREATE TABLE IF NOT EXISTS attendance(class_id INTEGER,user_id INTEGER,status TEXT NOT NULL,
              verified_by INTEGER,at REAL NOT NULL,PRIMARY KEY(class_id,user_id));
            CREATE TABLE IF NOT EXISTS recording_codes(code_hash TEXT PRIMARY KEY,recording_id TEXT NOT NULL,
              owner INTEGER NOT NULL,expires REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,
              download INTEGER NOT NULL,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS recording_viewers(code_hash TEXT,user_id INTEGER,PRIMARY KEY(code_hash,user_id));
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,event TEXT NOT NULL,actor INTEGER,
              recording_id TEXT,code_hash TEXT,at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS audit_time ON audit(at);
            CREATE TABLE IF NOT EXISTS policy_acks(user_id INTEGER,version TEXT,at REAL NOT NULL,
              PRIMARY KEY(user_id,version));
            CREATE TABLE IF NOT EXISTS guardian_scopes(user_id INTEGER PRIMARY KEY,scope TEXT NOT NULL,
              version TEXT NOT NULL,expires REAL NOT NULL,evidence_hash TEXT NOT NULL,at REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS standing_scopes(user_id INTEGER PRIMARY KEY,scope TEXT NOT NULL,
              version TEXT NOT NULL,expires REAL NOT NULL,at REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS recording_subjects(recording_id TEXT,user_id INTEGER,scope TEXT NOT NULL,
              revoked INTEGER NOT NULL DEFAULT 0,at REAL NOT NULL,PRIMARY KEY(recording_id,user_id));
            CREATE TABLE IF NOT EXISTS student_credentials(selector TEXT PRIMARY KEY,user_id INTEGER NOT NULL,
              verifier TEXT NOT NULL,password_stamp TEXT NOT NULL,expires REAL NOT NULL,idle REAL NOT NULL);
            ''')

        import os
        if os.name!='nt':os.chmod(self.path,0o600)

    @contextlib.contextmanager
    def db(self):
        c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row
        try:
            c.execute('PRAGMA foreign_keys=ON')
            yield c;c.commit()
        except BaseException:c.rollback();raise
        finally:c.close()

    def options(self,record_id):
        with self.db() as c:
            row=c.execute('SELECT * FROM recording_options WHERE id=?',(record_id,)).fetchone()
            playback=c.execute('SELECT state FROM recording_playback WHERE id=?',(record_id,)).fetchone()
            local_bytes=c.execute('SELECT COALESCE(SUM(size),0) FROM local_chunks WHERE id=?',(record_id,)).fetchone()[0]
        return {**dict(row),'playback_state':playback['state'] if playback else 'unavailable','local_bytes':local_bytes} if row else {'mode':'cloud','scope':'{}','subjects':'[]','error':'','stop_reason':'','metrics':'{}'}

    def audit(self,event,actor,record_id=None,code_hash=None):
        with self.db() as c:
            now=time.time()
            if event in ('play','download') and c.execute('SELECT 1 FROM audit WHERE event=? AND actor=? AND recording_id=? AND at>? LIMIT 1',(event,actor,record_id,now-60)).fetchone():return
            c.execute('INSERT INTO audit(event,actor,recording_id,code_hash,at) VALUES (?,?,?,?,?)',(event,actor,record_id,code_hash,now))
