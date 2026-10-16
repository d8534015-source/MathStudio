"""Stable per-user state; explicitly preserve existing in-place installations."""
import os
from pathlib import Path


def state_directory():
    base=Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'.local'/'share'))
    return base/'MathStudio'


def data_directory(root):
    explicit=os.environ.get('MATH_DATA')
    if explicit:return Path(explicit).expanduser().resolve()
    legacy=Path(root)/'bulletin_data'
    # Never silently move or discard a legacy database. Migration is explicit.
    return legacy if legacy.exists() else state_directory()/'data'
