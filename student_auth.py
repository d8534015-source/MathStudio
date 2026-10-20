"""Student-only persistent cookie family, separate from native teacher DPAPI."""
import hashlib
import hmac
import re
import secrets
import time
COOKIE='mathstudio_student_remember'
ABSOLUTE=30*86400
IDLE=7*86400

def digest(secret):return hashlib.sha256(secret.encode()).hexdigest()
def stamp(user):return digest(user['password']+'\0'+user['role'])

def revoke(features,selector):
    with features.db() as c:c.execute('DELETE FROM student_credentials WHERE selector=?',(selector,))

def issue(features,user):
    if user['role']!='student':raise ValueError('Student persistence requires a student account.')
    selector=secrets.token_hex(16);secret=secrets.token_urlsafe(32);now=time.time()
    with features.db() as c:
        c.execute('DELETE FROM student_credentials WHERE expires<=? OR idle<=?',(now,now))
        count=c.execute('SELECT COUNT(*) FROM student_credentials WHERE user_id=?',(user['id'],)).fetchone()[0]
        if count>=10:c.execute('DELETE FROM student_credentials WHERE selector IN (SELECT selector FROM student_credentials WHERE user_id=? ORDER BY expires LIMIT 1)',(user['id'],))
        c.execute('INSERT INTO student_credentials VALUES (?,?,?,?,?,?)',(selector,user['id'],digest(secret),stamp(user),now+ABSOLUTE,now+IDLE))
    return selector+'.'+secret,selector

def validate(features,selector,user):
    with features.db() as c:row=c.execute('SELECT * FROM student_credentials WHERE selector=?',(selector,)).fetchone()
    valid=bool(row and user and user['role']=='student' and row['user_id']==user['id'] and row['expires']>time.time() and row['idle']>time.time() and hmac.compare_digest(row['password_stamp'],stamp(user)))
    if row and not valid:revoke(features,selector)
    if valid and row['idle']<min(time.time()+IDLE-60,row['expires']):
        with features.db() as c:c.execute('UPDATE student_credentials SET idle=? WHERE selector=?',(min(time.time()+IDLE,row['expires']),selector))
    return valid

def restore(features,token,lookup):
    if not isinstance(token,str) or not re.fullmatch(r'[0-9a-f]{32}\.[A-Za-z0-9_-]{43}',token):return None
    selector,secret=token.split('.')
    with features.db() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM student_credentials WHERE selector=?',(selector,)).fetchone()
        if not row:return None
        user=lookup(row['user_id']);now=time.time()
        valid=(user and user['role']=='student' and row['expires']>now and row['idle']>now and hmac.compare_digest(row['password_stamp'],stamp(user)) and hmac.compare_digest(row['verifier'],digest(secret)))
        if not valid:c.execute('DELETE FROM student_credentials WHERE selector=?',(selector,));return None
        # Keep the selector/family so a replay of an old validator revokes the
        # restored session too. Only the random secret rotates; absolute age does not.
        replacement=secrets.token_urlsafe(32)
        c.execute('UPDATE student_credentials SET verifier=?,idle=? WHERE selector=?',(digest(replacement),min(now+IDLE,row['expires']),selector))
        return user,selector+'.'+replacement,selector,int(row['expires']-now)

def cookie(token,max_age=ABSOLUTE):return f'{COOKIE}={token}; Path=/; Max-Age={max_age}; Secure; HttpOnly; SameSite=Strict'
