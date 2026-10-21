"""Stable per-user state; explicitly preserve existing in-place installations."""
import os
import json
import sys
from pathlib import Path


def state_directory():
    base=Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'.local'/'share'))
    if getattr(sys,'frozen',False):
        try:
            marker=json.loads(Path(__file__).with_name('teacher_package_role.json').read_text(encoding='utf-8'))
            if marker.get('review') is True:
                selected=marker.get('review_profile');return base/(selected if selected in ('MathStudioClassroomReview','MathStudioRecordingUpgradeReview','MathStudioStopInputReview','MathStudioLayoutReview') else 'MathStudioReview')
        except (OSError,ValueError):pass
    return base/'MathStudio'


def data_directory(root):
    explicit=os.environ.get('MATH_DATA')
    if explicit:return Path(explicit).expanduser().resolve()
    legacy=Path(root)/'bulletin_data'
    # Never silently move or discard a legacy database. Migration is explicit.
    return legacy if legacy.exists() else state_directory()/'data'
