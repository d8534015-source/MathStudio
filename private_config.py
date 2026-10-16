"""Read explicit allowlisted configuration as data; never execute batch scripts."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import tempfile
from runtime_paths import state_directory

KEYS=frozenset(('CLOUDFLARE_TURN_KEY_ID','CLOUDFLARE_TURN_API_TOKEN','STUN_URL',
    'TURN_URL','TURN_USERNAME','TURN_CREDENTIAL','TURN_SECRET','MATH_R2_ACCOUNT_ID',
    'MATH_R2_ACCESS_KEY_ID','MATH_R2_SECRET_ACCESS_KEY','MATH_R2_BUCKET','MATH_MAX_UPLOAD_MB'))


def config_path():
    return Path(os.environ['MATH_CONFIG']) if os.environ.get('MATH_CONFIG') else state_directory()/'private_config.json'


def validate(values):
    if not isinstance(values,dict) or set(values)-KEYS:raise ValueError('Configuration has unsupported keys.')
    result={}
    for key,value in values.items():
        if not isinstance(value,str) or not value.strip() or len(value)>4096 or any(ord(c)<32 for c in value):
            raise ValueError('Configuration contains an invalid value; credentials are not displayed.')
        value=value.strip()
        if re.search(r'YOUR_|PASTE_|REPLACE_ME|CHANGE_ME|<[^>]+>',value,re.I):
            raise ValueError('Configuration contains placeholder values.')
        result[key]=value
    if bool(result.get('CLOUDFLARE_TURN_KEY_ID'))!=bool(result.get('CLOUDFLARE_TURN_API_TOKEN')):
        raise ValueError('Supply both Cloudflare TURN Key ID and API token.')
    if 'TURN_URL' in result and not (result.get('TURN_SECRET') or (result.get('TURN_USERNAME') and result.get('TURN_CREDENTIAL'))):
        raise ValueError('Static TURN needs a shared secret or both username and credential.')
    r2={'MATH_R2_ACCOUNT_ID','MATH_R2_ACCESS_KEY_ID','MATH_R2_SECRET_ACCESS_KEY','MATH_R2_BUCKET'}
    if r2.intersection(result) and not r2.issubset(result):raise ValueError('Supply all four R2 configuration fields together.')
    for key,prefixes in (('TURN_URL',('turn:','turns:')),('STUN_URL',('stun:','stuns:'))):
        if key in result and not result[key].startswith(prefixes):raise ValueError('Invalid TURN/STUN URL scheme.')
    if 'MATH_MAX_UPLOAD_MB' in result and (not result['MATH_MAX_UPLOAD_MB'].isdigit() or not 1<=int(result['MATH_MAX_UPLOAD_MB'])<=500):
        raise ValueError('Upload size must be between 1 and 500 MB.')
    return result


def read_config(path=None):
    path=Path(path) if path is not None else config_path()
    if not path.exists():return {}
    if path.is_symlink() or path.stat().st_size>65536:raise ValueError('Unsafe configuration file.')
    def unique_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate configuration keys are not accepted.')
            result[key]=value
        return result
    return validate(json.loads(path.read_text(encoding='utf-8-sig'),object_pairs_hook=unique_pairs))


def parse_legacy(path):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>65536:raise ValueError('Unsafe import file.')
    values={}
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line=raw.strip()
        if not line or line.lower()=='@echo off' or line.lower().startswith(('rem ','::')):continue
        match=re.fullmatch(r'set\s+"([A-Z0-9_]+)=([^"\r\n]*)"',line,re.I)
        if not match or match[1].upper() in values:raise ValueError('Only unique quoted SET assignments and comments may be imported; no commands are executed.')
        values[match[1].upper()]=match[2]
    if not values:raise ValueError('No supported settings found.')
    return validate(values)


def write_config(values,path=None):
    values=validate(values);path=Path(path) if path is not None else config_path()
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,tmp=tempfile.mkstemp(prefix='.mathstudio-config-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:json.dump(values,out,indent=2);out.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def apply_config(env=None,path=None):
    env=os.environ if env is None else env
    for key,value in read_config(path).items():
        if not env.get(key):env[key]=value
    return env


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('configure-turn','import','check','test-turn'))
    parser.add_argument('--from-path',type=Path)
    parser.add_argument('--replace',action='store_true')
    args=parser.parse_args()
    try:
        if args.action in ('configure-turn','import'):
            current=read_config()
            if args.action=='import':
                if not args.from_path:raise ValueError('Select one legacy file explicitly with --from-path.')
                incoming=parse_legacy(args.from_path)
                if any(k in current and current[k]!=v for k,v in incoming.items()) and not args.replace:
                    raise ValueError('Existing values differ. Review your selection and use --replace explicitly to replace them.')
            else:
                incoming={'CLOUDFLARE_TURN_KEY_ID':input('Cloudflare TURN Key ID: ').strip(),
                          'CLOUDFLARE_TURN_API_TOKEN':getpass.getpass('TURN API token (hidden): ').strip()}
            write_config({**current,**incoming})
            print('Private configuration saved outside the application folder. Restart the website to apply changes.')
        elif args.action=='check':
            print('Configuration valid; configured fields: '+', '.join(sorted(read_config())))
        else:
            import urllib.request
            env=apply_config({})
            key=env.get('CLOUDFLARE_TURN_KEY_ID');token=env.get('CLOUDFLARE_TURN_API_TOKEN')
            if not key or not token:raise ValueError('Run SETUP FREE CAMERA + AUDIO.bat first.')
            from urllib.parse import quote
            request=urllib.request.Request('https://rtc.live.cloudflare.com/v1/turn/keys/'+quote(key,safe='')+'/credentials/generate-ice-servers',
                data=b'{"ttl":3600}',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(request,timeout=15) as response:result=json.load(response)
                if not result.get('iceServers'):raise ValueError('TURN provider returned no ICE servers.')
            except Exception:raise ValueError('TURN verification failed. Check credentials and network access; provider output is not logged.') from None
            print('SUCCESS: TURN credentials generated. Credentials are not displayed.')
        return 0
    except (OSError,ValueError) as ex:
        print('Configuration error: '+str(ex));return 1


if __name__=='__main__':raise SystemExit(main())
