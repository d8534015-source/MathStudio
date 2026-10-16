"""Canonical release identity used by backend, desktop and generated web assets."""
import json
from pathlib import Path
INFO=json.loads(Path(__file__).with_name('version.json').read_text(encoding='utf-8'))
VERSION=INFO['version']
BUILD_ID=INFO['build_id']
ASSET_VERSION=INFO['asset_version']
