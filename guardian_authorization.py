"""OWNER-only evidence entry after independently verifying a guardian's identity/decision.

This is not automatic identity verification. Never let a student's self-assertion
stand in for a guardian's authorization. Evidence remains with OWNER, not in Git.
"""
import argparse
import getpass
import hashlib
import json
from pathlib import Path
import time
from review_features import Features
from recording_authorization import version,validate_scope


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['grant','withdraw']);p.add_argument('--data',type=Path,required=True);p.add_argument('--user-id',type=int,required=True);a=p.parse_args()
    import sqlite3,policy_service
    with sqlite3.connect(a.data/'posts.db') as c:person=c.execute("SELECT 1 FROM users WHERE id=? AND role='student'",(a.user_id,)).fetchone()
    if not person:raise SystemExit('Select an existing student account ID in the chosen review state.')
    if a.action=='grant' and not all(policy_service.metadata().get(k) is True for k in ('owner_reviewed','legal_reviewed')):raise SystemExit('Draft policy review is incomplete. OWNER and qualified privacy/legal review must be recorded before guardian grants for real use.')
    features=Features(a.data)
    if a.action=='withdraw':
        with features.db() as c:
            c.execute('UPDATE guardian_scopes SET revoked=1 WHERE user_id=?',(a.user_id,));c.execute('UPDATE standing_scopes SET revoked=1 WHERE user_id=?',(a.user_id,));c.execute('UPDATE recording_subjects SET revoked=1 WHERE user_id=?',(a.user_id,))
    else:
        print('Verify the guardian identity, relationship, signed/recorded decision and scope outside this software first. Do not use a student checkbox as guardian evidence.')
        if input('Type VERIFIED GUARDIAN only after completing that process: ')!='VERIFIED GUARDIAN':raise SystemExit('No authorization saved.')
        evidence=getpass.getpass('Private evidence reference (not displayed or stored in plaintext): ')
        if len(evidence.strip())<8:raise SystemExit('A meaningful private evidence reference is required.')
        scope=json.loads(input('Authorized scope JSON (storage/sharing/download/retention_days): '))
        if not validate_scope(scope):raise SystemExit('Invalid scope.')
        days=int(input('Expires after how many days (1–365): '))
        if not 1<=days<=365:raise SystemExit('Invalid expiry.')
        with features.db() as c:c.execute('INSERT OR REPLACE INTO guardian_scopes VALUES (?,?,?,?,?,?,0)',(a.user_id,json.dumps(scope),version(),time.time()+days*86400,hashlib.sha256(evidence.encode()).hexdigest(),time.time()))
    features.audit('guardian_'+a.action,None);print('Guardian decision saved in private OWNER review state. Student agreement remains separate.')
if __name__=='__main__':main()
