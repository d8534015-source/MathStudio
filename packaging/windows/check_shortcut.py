"""Read a .lnk with IShellLinkW; WScript.Shell's ANSI TargetPath loses Chinese."""
import ctypes
import json
import os
from pathlib import Path
import sys
import uuid


def main():
    if sys.platform!='win32':raise SystemExit('Windows shell-link validation requires Windows.')
    class GUID(ctypes.Structure):
        _fields_=[('a',ctypes.c_uint32),('b',ctypes.c_uint16),('c',ctypes.c_uint16),('d',ctypes.c_ubyte*8)]
    def guid(value):return GUID.from_buffer_copy(uuid.UUID(value).bytes_le)
    ole=ctypes.OleDLL('ole32')
    ole.CoInitialize.argtypes=[ctypes.c_void_p];ole.CoInitialize.restype=ctypes.c_long
    ole.CoCreateInstance.argtypes=[ctypes.POINTER(GUID),ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype=ctypes.c_long
    ole.CoUninitialize.argtypes=[];ole.CoUninitialize.restype=None
    def invoke(pointer,index,types,*args):
        table=ctypes.cast(pointer,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        call=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,*types)(table[index])
        result=call(pointer,*args)
        if result<0:raise OSError('Windows COM HRESULT '+hex(result&0xffffffff))
    link=ctypes.c_void_p();persist=ctypes.c_void_p()
    ole.CoInitialize(None)
    try:
        cls=guid('00021401-0000-0000-C000-000000000046')
        iid=guid('000214F9-0000-0000-C000-000000000046') # IShellLinkW
        ole.CoCreateInstance(ctypes.byref(cls),None,1,ctypes.byref(iid),ctypes.byref(link))
        iid_persist=guid('0000010b-0000-0000-C000-000000000046')
        invoke(link,0,[ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)],ctypes.byref(iid_persist),ctypes.byref(persist))
        invoke(persist,5,[ctypes.c_wchar_p,ctypes.c_uint32],sys.argv[1],0)
        buffer=ctypes.create_unicode_buffer(32768)
        invoke(link,3,[ctypes.c_wchar_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32],buffer,len(buffer),None,4)
        result={'target':buffer.value,'expected':sys.argv[2],'same_file':os.path.samefile(buffer.value,sys.argv[2])}
        if len(sys.argv)>3:Path(sys.argv[3]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))
        if not result['same_file']:raise SystemExit('Shortcut does not target the installed executable.')
    finally:
        if persist:invoke(persist,2,[])
        if link:invoke(link,2,[])
        ole.CoUninitialize()


if __name__=='__main__':main()
