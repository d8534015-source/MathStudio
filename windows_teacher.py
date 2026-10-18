"""Windowless frozen teacher entry point; never import or host the OWNER backend."""
import json
import os
from pathlib import Path
import sys
import traceback


def main():
    if '--meeting-bootstrap' in sys.argv:
        sys.argv.remove('--meeting-bootstrap')
        from teacher_app_bootstrap import main as bootstrap
        return bootstrap()
    if '--meeting' in sys.argv:
        sys.argv.remove('--meeting')
        from teacher_meeting_app import main as meeting
        meeting();return 0
    from dependency_check import verify_runtime
    verify_runtime(gui=True)
    if '--self-test' in sys.argv:
        # Exercises bundled Tcl/Tk, native Win32 imports, timezone and dependency metadata.
        import ctypes
        import teacher_meeting_app
        from teacher_connection import teacher_only
        from build_info import BUILD_ID
        from studio_time import studio_zone
        assert teacher_only()
        assert ctypes.windll.kernel32.GetConsoleWindow()==0
        from runtime_paths import state_directory
        path=state_directory()/'installer-self-test.json';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'build':BUILD_ID,'runtime':sys.version,'frozen':bool(getattr(sys,'frozen',False)),
            'console':False,'timezone':str(studio_zone('Asia/Shanghai'))}),encoding='utf-8')
        return 0
    from teacher_connection import select_origin
    origin=select_origin()
    if not origin:return 0
    os.environ['MATHSTUDIO_REMOTE']='1';os.environ['MATHSTUDIO_SERVER_URL']=origin
    from teacher_desktop_app import TeacherDesktopApp
    TeacherDesktopApp().run()
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        from runtime_paths import state_directory
        from teacher_app_bootstrap import message
        log=state_directory()/'teacher_startup_error.log';log.parent.mkdir(parents=True,exist_ok=True)
        log.write_text(traceback.format_exc(),encoding='utf-8')
        message('MathStudio / 启动失败','MathStudio could not start. / MathStudio 无法启动。\n'+str(log))
        raise SystemExit(1)
