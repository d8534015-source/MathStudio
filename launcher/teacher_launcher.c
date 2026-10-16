/* Optional Windows Unicode launcher. No cmd.exe, PATH lookup or script discovery. */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,PWSTR command,int show) {
    wchar_t folder[32768], python[32768], script[32768], args[65536];
    STARTUPINFOW startup={0}; PROCESS_INFORMATION process={0};
    DWORD length=GetModuleFileNameW(NULL,folder,32768);
    (void)instance;(void)previous;(void)command;(void)show;
    if (!length || length>=32768) return 1;
    wchar_t *slash=wcsrchr(folder,L'\\');
    if (!slash) return 1;
    *slash=L'\0';
    if (swprintf_s(python,32768,L"%ls\\.venv\\Scripts\\python.exe",folder)<0 ||
        swprintf_s(script,32768,L"%ls\\runtime_setup.py",folder)<0 ||
        swprintf_s(args,65536,L"\"%ls\" \"%ls\" --launch teacher",python,script)<0) return 1;
    startup.cb=sizeof(startup);
    if (!CreateProcessW(python,args,NULL,NULL,FALSE,CREATE_NEW_CONSOLE,NULL,folder,&startup,&process)) {
        MessageBoxW(NULL,L"Run SETUP MATHSTUDIO.bat first, then OPEN MATHSTUDIO TEACHER.bat. See INSTALL_WINDOWS.md.",L"MathStudio setup required",MB_OK|MB_ICONERROR);
        return 1;
    }
    CloseHandle(process.hThread);
    if (WaitForSingleObject(process.hProcess,2000)==WAIT_OBJECT_0) {
        DWORD code=0;
        if (GetExitCodeProcess(process.hProcess,&code) && code!=0)
            MessageBoxW(NULL,L"MathStudio closed during startup. Run OPEN MATHSTUDIO TEACHER.bat to see the error, or SETUP MATHSTUDIO.bat outside teaching time.",L"MathStudio startup failed",MB_OK|MB_ICONERROR);
    }
    CloseHandle(process.hProcess);
    return 0;
}
