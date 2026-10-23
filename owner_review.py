"""Explicit, isolated OWNER review setup; never downloads translation models."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
PORT = 5069


def environment(state):
    # Do not inherit production credentials, configuration, data or Python paths.
    allowed = ('PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP')
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(LOCALAPPDATA=str(state/'profile'), APPDATA=str(state/'profile'),
               USERPROFILE=str(state/'profile'), MATH_DATA=str(state/'data'),
               MATH_CONFIG=str(state/'empty-config.json'),
               MATH_ARGOS_HOME=str(state/'translation'), PORT=str(PORT),
               BIND_HOST='127.0.0.1', PUBLIC_ORIGIN=f'http://127.0.0.1:{PORT}',
               MATH_PUBLIC_TRANSLATION_PROVIDER='argos', PYTHONUTF8='1',
               PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    return env


def python_at(folder):
    return folder/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def copy_models(source, destination):
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise RuntimeError('Source and review Argos storage must be separate.')
    # Explicit selection excludes archives, downloads, caches and unrelated files.
    for name in ('runtime', 'packages', 'installation.json'):
        item = source/name
        if not item.exists():
            raise RuntimeError('Selected Argos home is missing '+name+'.')
        candidates = [item, *item.rglob('*')] if item.is_dir() else [item]
        if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in candidates):
            raise RuntimeError('Linked Argos storage is not copied; select a regular installed folder.')
    if (source/'.setup.lock').exists():
        raise RuntimeError('Argos setup is in progress. Retry after it finishes.')
    destination.mkdir(exist_ok=False)
    for name in ('runtime', 'packages'):
        shutil.copytree(source/name, destination/name)
    shutil.copyfile(source/'installation.json', destination/'installation.json')


def run(state, command):
    subprocess.run(command, cwd=ROOT, env=environment(state), check=True)


def setup(state, source, wheelhouse=None):
    if sys.version_info[:2] != (3, 13) or os.name != 'nt':
        raise RuntimeError('Use Windows 64-bit Python 3.13 on the same PC as the installed Argos runtime.')
    if state == ROOT or ROOT in state.parents or state in ROOT.parents:
        raise RuntimeError('Review storage must be outside the extracted source folder.')
    if state == source or state in source.parents or source in state.parents:
        raise RuntimeError('Review storage must be separate from the existing Argos installation.')
    state.mkdir(parents=True, exist_ok=False)  # Never clear or overwrite existing state.
    (state/'profile').mkdir()
    (state/'empty-config.json').write_text('{}\n', encoding='utf-8')
    print('Copying installed Argos runtime and models locally; no model downloads.', flush=True)
    copy_models(source, state/'translation')
    copied = python_at(state/'translation'/'runtime')
    # Copied Windows venvs still need their original base CPython installation.
    probe = ('import pathlib,sys,argostranslate; '
             'p=pathlib.Path(sys.argv[1]).resolve(); '
             'assert pathlib.Path(sys.prefix).resolve()==p; '
             'assert p in pathlib.Path(argostranslate.__file__).resolve().parents')
    run(state, [str(copied), '-I', '-c', probe, str(state/'translation'/'runtime')])
    runtime = state/'owner-runtime'
    venv.EnvBuilder(with_pip=True).create(runtime)
    python = str(python_at(runtime))
    command = [python, '-m', 'pip', 'install', '--disable-pip-version-check',
               '--require-hashes', '--only-binary=:all:', '-r', str(ROOT/'requirements.txt')]
    command += ['--no-index', '--find-links', str(wheelhouse)] if wheelhouse else ['--index-url', 'https://pypi.org/simple']
    run(state, command)
    run(state, [python, '-m', 'pip', 'check'])
    run(state, [python, '-c', 'from dependency_check import verify_runtime; verify_runtime()'])
    # Existing receipts are never trusted without checking this local copy.
    run(state, [python, '-c', 'import argos_runtime; assert argos_runtime.ready(), "Copied models are not ready"; '
               'from argos_setup import self_test; self_test(argos_runtime.home(), argos_runtime.home()/"packages")'])
    (state/'review-ready.json').write_text(json.dumps({'schema': 1, 'port': PORT})+'\n', encoding='utf-8')
    print('Review setup passed both offline translation directions. Run REVIEW OWNER START.bat.')


def start(state):
    if not (state/'review-ready.json').is_file():
        raise RuntimeError('Run REVIEW OWNER SETUP.bat successfully first.')
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', PORT))
        except OSError:
            raise RuntimeError('Review port 5069 is occupied; no existing server was changed.') from None
    python = str(python_at(state/'owner-runtime'))
    run(state, [python, '-c', 'from dependency_check import verify_runtime; verify_runtime()'])
    print('Starting isolated review with an official Cloudflare Quick Tunnel.\nUse synthetic accounts only. Ctrl+C stops review and its own tunnel.', flush=True)
    run(state, [python, '-c', 'from owner_launcher import main; '
               'raise SystemExit(main(port=5069,bind="127.0.0.1",reuse=False))'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'start'))
    parser.add_argument('--state', type=Path, default=Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'MathStudioOwnerCompactReview')
    parser.add_argument('--argos-home', type=Path)
    parser.add_argument('--wheelhouse', type=Path)
    args = parser.parse_args()
    try:
        state = args.state.expanduser().resolve()
        if args.action == 'start':
            start(state)
        else:
            source = args.argos_home or Path(input('Existing ready Argos home (folder containing installation.json): ').strip().strip('"'))
            setup(state, source.expanduser().resolve(), args.wheelhouse)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print('Review setup/start stopped: '+str(error), file=sys.stderr)
        print('Existing OWNER was not reconfigured. Failed review storage is retained; choose a NEW --state folder to retry.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
