"""Lightweight OWNER adapter. Never imports Argos into the HTTP/teacher process."""
import json
import os
from pathlib import Path
import re
import subprocess
import threading
from runtime_paths import state_directory

ROOT = Path(__file__).resolve().parent
TIMEOUT = 30  # Bounded CPU work; only the translation-editor request gets a longer deadline.
_SLOT = threading.BoundedSemaphore(1)
TOKEN = re.compile(r'(MSKEEP[A-F0-9]{24}X\d+END)')


class ArgosError(Exception):
    pass


def home():
    selected = Path(os.environ.get('MATH_ARGOS_HOME') or state_directory()/'translation').expanduser()
    if not selected.is_absolute():
        raise ArgosError('Argos storage must use an absolute path.')
    path = selected.resolve()
    if path == ROOT or ROOT in path.parents:
        raise ArgosError('Argos storage must be outside the application folder.')
    return path


def python_path():
    return home()/'runtime'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def ready():
    try:
        base = home()
        receipt = base/'installation.json'
        if not python_path().is_file() or not receipt.is_file() or receipt.stat().st_size > 16384 or (base/'.setup.lock').exists():
            return False
        info = json.loads(receipt.read_text(encoding='utf-8'))
        if info.get('schema') != 1 or info.get('argos') != '1.11.0' or not info.get('verified'):
            return False
        for pair in ('en_zh', 'zh_en'):
            item = info['models'][pair]
            folder = base/'packages'/item['folder']
            if folder.parent != base/'packages' or not (folder/'metadata.json').is_file() or not (folder/'model'/'model.bin').is_file():
                return False
        return True
    except (ArgosError, OSError, ValueError, KeyError, TypeError):
        return False


def environment(base):
    # Inference receives no API keys, TURN secrets, account paths or provider credentials.
    allowed = ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','COMSPEC','PATHEXT','LD_LIBRARY_PATH')
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    env.update(USERPROFILE=str(base), LOCALAPPDATA=str(base/'cache'), APPDATA=str(base/'config'),
               STANZA_RESOURCES_DIR=str(base/'data'/'stanza'), PYTHONUTF8='1', PYTHONIOENCODING='utf-8', ARGOS_PACKAGES_DIR=str(base/'packages'),
               XDG_DATA_HOME=str(base/'data'), XDG_CONFIG_HOME=str(base/'config'), XDG_CACHE_HOME=str(base/'cache'),
               ARGOS_MODEL_PROVIDER='OPENNMT', ARGOS_DEVICE_TYPE='cpu', ARGOS_CHUNK_TYPE='STANZA',
               ARGOS_INTER_THREADS='1', ARGOS_INTRA_THREADS='1', ARGOS_COMPUTE_TYPE='int8',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TORCH_HOME=str(base/'cache'/'torch'), HF_HOME=str(base/'cache'/'huggingface'))
    return env


def translate(text, target):
    if target not in ('en', 'zh') or not isinstance(text, str) or len(text) > 20000:
        raise ArgosError('Invalid offline translation request.')
    if not ready():
        raise ArgosError('Offline translation models are unavailable. Run OWNER offline translation setup.')
    if not _SLOT.acquire(blocking=False):
        raise ArgosError('Offline translation is busy. Try again shortly.')
    try:
        # Tokens/names/math never pass through the model. They are rejoined verbatim.
        pieces = TOKEN.split(text)
        payload = {'target': target, 'pieces': pieces[::2]}
        options = {}
        if os.name == 'nt':
            options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
        try:
            result = subprocess.run([str(python_path()), '-I', '-u', str(ROOT/'argos_worker.py')],
                input=json.dumps(payload,ensure_ascii=False),encoding='utf-8',stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,timeout=TIMEOUT,cwd=str(home()),env=environment(home()),**options)
        except subprocess.TimeoutExpired:
            raise ArgosError('Offline translation timed out. Original content is unchanged.') from None
        except OSError:
            raise ArgosError('Offline translation could not start. Run OWNER offline translation setup.') from None
        if result.returncode or len(result.stdout) > 150000:
            raise ArgosError('Offline translation failed. Original content is unchanged.')
        try:
            translated = json.loads(result.stdout)['pieces']
            if not isinstance(translated,list) or len(translated) != len(pieces[::2]) or any(not isinstance(x,str) or len(x)>20000 for x in translated):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ArgosError('Offline translation failed. Original content is unchanged.') from None
        pieces[::2] = translated
        output = ''.join(pieces)
        if len(output) > 20000:
            raise ArgosError('Offline translation result is too large.')
        return output
    finally:
        _SLOT.release()
