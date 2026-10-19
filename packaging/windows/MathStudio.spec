# PyInstaller onedir: runtime and Tcl/Tk bundled, installed by one Inno Setup EXE.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata
root=Path(SPECPATH).parents[1]
assets=Path(SPECPATH)/'generated'
datas=[(str(root/'version.json'),'.'),(str(root/'requirements.txt'),'.'),
       (str(assets/'teacher_package_role.json'),'.')]
datas+=collect_data_files('tzdata')
for package in ('Pillow','pypdf','tzdata'):datas+=copy_metadata(package)
a=Analysis([str(root/'windows_teacher.py')],pathex=[str(root)],datas=datas,
    hiddenimports=['teacher_meeting_app','teacher_app_bootstrap','PIL.ImageGrab','PIL._imagingtk'],
    excludes=['server','owner_auth','owner_review','website_content','public_translations','argos_runtime','argos_worker','argos_setup',
              'argostranslate','minisbd','sentencepiece','ctranslate2','onnxruntime','torch','stanza','spacy',
              'document_worker','runtime_setup','owner_launcher','pytest','unittest'],
    noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='MathStudioClient',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    icon=str(assets/'MathStudio.ico'),version=str(assets/'version.txt'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='MathStudioClient')
