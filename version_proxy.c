/*
 * VERSION.dll proxy - Redirects stdout via UCRT for Lua print() capture
 *
 * Strategy: EngineWin64sv.dll imports VERSION.dll, so placing our proxy in the
 * game directory makes it load instead of Wine's builtin. On first forwarded
 * call (after CRT is initialized), we use UCRT's own freopen() to redirect
 * stdout - this affects the SAME stdout that Lua's print() uses since they
 * share ucrtbase.dll.
 *
 * Build: x86_64-w64-mingw32-gcc -shared -o VERSION.dll version_proxy.c -O2
 */

#include <windows.h>
#include <stdio.h>

/* ========== State ========== */
static HMODULE g_real_version = NULL;
static char g_exedir[MAX_PATH] = {0};
static volatile int g_stdout_redirected = 0;

/* ========== Marker file (safe Win32 API, usable in DllMain) ========== */
static void write_marker(const char *exedir, const char *extra) {
    char path[MAX_PATH];
    snprintf(path, MAX_PATH, "%shadesmp_version_marker.txt", exedir);
    HANDLE h = CreateFileA(path, GENERIC_WRITE, 0, NULL,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h != INVALID_HANDLE_VALUE) {
        DWORD written;
        const char *msg = "VERSION.dll proxy loaded OK\r\n";
        WriteFile(h, msg, strlen(msg), &written, NULL);

        char buf[1024];
        snprintf(buf, sizeof(buf),
                 "real_version_dll: %p\r\nexedir: %s\r\nextra: %s\r\n",
                 (void *)g_real_version, exedir, extra ? extra : "none");
        WriteFile(h, buf, strlen(buf), &written, NULL);
        CloseHandle(h);
    }
}

/* ========== UCRT stdout redirect (called AFTER CRT init) ========== */
static void redirect_stdout_via_ucrt(void) {
    if (g_stdout_redirected) return;
    g_stdout_redirected = 1;

    /* Find ucrtbase.dll - the universal CRT shared by all modules */
    HMODULE ucrt = GetModuleHandleA("ucrtbase.dll");
    if (!ucrt) ucrt = LoadLibraryA("ucrtbase.dll");

    /* Also try msvcrt.dll as fallback (older Wine) */
    HMODULE msvcrt = NULL;
    if (!ucrt) {
        msvcrt = GetModuleHandleA("msvcrt.dll");
        if (msvcrt) ucrt = msvcrt;
    }

    if (!ucrt) {
        /* Log failure */
        char path[MAX_PATH];
        snprintf(path, MAX_PATH, "%shadesmp_redirect_fail.txt", g_exedir);
        HANDLE h = CreateFileA(path, GENERIC_WRITE, 0, NULL,
                               CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (h != INVALID_HANDLE_VALUE) {
            const char *msg = "FAIL: could not find ucrtbase.dll or msvcrt.dll\r\n";
            DWORD written;
            WriteFile(h, msg, strlen(msg), &written, NULL);
            CloseHandle(h);
        }
        return;
    }

    /* Get UCRT function pointers */
    typedef FILE *(__cdecl *freopen_func)(const char *, const char *, FILE *);
    typedef int (__cdecl *setvbuf_func)(FILE *, char *, int, size_t);
    typedef FILE *(__cdecl *iob_func)(unsigned);
    typedef int (__cdecl *fprintf_func)(FILE *, const char *, ...);
    typedef int (__cdecl *fflush_func)(FILE *);

    freopen_func uc_freopen = (freopen_func)GetProcAddress(ucrt, "freopen");
    setvbuf_func uc_setvbuf = (setvbuf_func)GetProcAddress(ucrt, "setvbuf");
    fprintf_func uc_fprintf = (fprintf_func)GetProcAddress(ucrt, "fprintf");
    fflush_func uc_fflush = (fflush_func)GetProcAddress(ucrt, "fflush");

    /* Get stdout FILE* - try __acrt_iob_func first (UCRT), then __iob_func (msvcrt) */
    iob_func uc_iob = (iob_func)GetProcAddress(ucrt, "__acrt_iob_func");
    if (!uc_iob) uc_iob = (iob_func)GetProcAddress(ucrt, "__iob_func");

    /* Log what we found */
    char diagpath[MAX_PATH];
    snprintf(diagpath, MAX_PATH, "%shadesmp_redirect_diag.txt", g_exedir);
    HANDLE hdiag = CreateFileA(diagpath, GENERIC_WRITE, 0, NULL,
                               CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hdiag != INVALID_HANDLE_VALUE) {
        char buf[1024];
        DWORD written;
        snprintf(buf, sizeof(buf),
                 "ucrt=%p msvcrt=%p\r\n"
                 "freopen=%p setvbuf=%p fprintf=%p fflush=%p iob=%p\r\n",
                 (void *)ucrt, (void *)msvcrt,
                 (void *)uc_freopen, (void *)uc_setvbuf,
                 (void *)uc_fprintf, (void *)uc_fflush, (void *)uc_iob);
        WriteFile(hdiag, buf, strlen(buf), &written, NULL);

        if (uc_iob) {
            FILE *uc_stdout = uc_iob(1);
            snprintf(buf, sizeof(buf), "uc_stdout=%p\r\n", (void *)uc_stdout);
            WriteFile(hdiag, buf, strlen(buf), &written, NULL);
        }
        CloseHandle(hdiag);
    }

    if (!uc_freopen || !uc_iob) return;

    FILE *uc_stdout = uc_iob(1);
    if (!uc_stdout) return;

    /* Redirect UCRT stdout to our log file */
    char logpath[MAX_PATH];
    snprintf(logpath, MAX_PATH, "%shades_lua_stdout.log", g_exedir);

    FILE *f = uc_freopen(logpath, "w", uc_stdout);

    /* Also try SetStdHandle as belt-and-suspenders */
    {
        HANDLE hFile = CreateFileA(logpath, GENERIC_WRITE, FILE_SHARE_READ,
                                   NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (hFile != INVALID_HANDLE_VALUE) {
            SetFilePointer(hFile, 0, NULL, FILE_END);
            SetStdHandle(STD_OUTPUT_HANDLE, hFile);
        }
    }

    if (f) {
        if (uc_setvbuf) uc_setvbuf(f, NULL, _IONBF, 0); /* unbuffered */
        if (uc_fprintf) {
            uc_fprintf(f, "HADESMP:PROXY:stdout_redirected path=%s\n", logpath);
        }
        if (uc_fflush) uc_fflush(f);
    }

    /* Also redirect stderr */
    FILE *uc_stderr = uc_iob(2);
    if (uc_stderr) {
        char errpath[MAX_PATH];
        snprintf(errpath, MAX_PATH, "%shades_lua_stderr.log", g_exedir);
        FILE *f2 = uc_freopen(errpath, "w", uc_stderr);
        if (f2 && uc_setvbuf) uc_setvbuf(f2, NULL, _IONBF, 0);
    }

    /* Update diagnostics */
    hdiag = CreateFileA(diagpath, GENERIC_WRITE, 0, NULL,
                        OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hdiag != INVALID_HANDLE_VALUE) {
        SetFilePointer(hdiag, 0, NULL, FILE_END);
        char buf[256];
        DWORD written;
        snprintf(buf, sizeof(buf), "freopen result: %p (success=%s)\r\n",
                 (void *)f, f ? "YES" : "NO");
        WriteFile(hdiag, buf, strlen(buf), &written, NULL);
        CloseHandle(hdiag);
    }
}

/* ========== DllMain ========== */
BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinstDLL);

        /* Save exe directory */
        GetModuleFileNameA(NULL, g_exedir, MAX_PATH);
        char *last = strrchr(g_exedir, '\\');
        if (last) *(last + 1) = '\0';

        /* Load real VERSION.dll from system directory */
        char syspath[MAX_PATH];
        GetSystemDirectoryA(syspath, MAX_PATH);
        strcat(syspath, "\\version.dll");
        g_real_version = LoadLibraryA(syspath);

        /* Write marker file */
        char extra[256];
        snprintf(extra, sizeof(extra), "sys_path=%s", syspath);
        write_marker(g_exedir, extra);

        /* Early SetStdHandle redirect (belt-and-suspenders, may help if
           CRT hasn't initialized yet) */
        {
            char logpath[MAX_PATH];
            snprintf(logpath, MAX_PATH, "%shades_lua_stdout.log", g_exedir);
            HANDLE hFile = CreateFileA(logpath, GENERIC_WRITE,
                                       FILE_SHARE_READ | FILE_SHARE_WRITE,
                                       NULL, CREATE_ALWAYS,
                                       FILE_ATTRIBUTE_NORMAL, NULL);
            if (hFile != INVALID_HANDLE_VALUE) {
                SetStdHandle(STD_OUTPUT_HANDLE, hFile);
            }
        }
    }
    return TRUE;
}

/* ========== Ensure redirect before first real use ========== */
static void ensure_redirect(void) {
    if (!g_stdout_redirected) redirect_stdout_via_ucrt();
}

/* ========== Forwarded exports ========== */

/* Helper macro */
#define GET_REAL(name, type) \
    static type p_##name = NULL; \
    if (!p_##name && g_real_version) \
        p_##name = (type)GetProcAddress(g_real_version, #name); \

/* The 3 functions actually imported by EngineWin64sv.dll */

__declspec(dllexport) DWORD WINAPI GetFileVersionInfoSizeA(
    LPCSTR lptstrFilename, LPDWORD lpdwHandle)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(LPCSTR, LPDWORD);
    GET_REAL(GetFileVersionInfoSizeA, fn_t);
    if (p_GetFileVersionInfoSizeA)
        return p_GetFileVersionInfoSizeA(lptstrFilename, lpdwHandle);
    if (lpdwHandle) *lpdwHandle = 0;
    return 0;
}

__declspec(dllexport) BOOL WINAPI GetFileVersionInfoA(
    LPCSTR lptstrFilename, DWORD dwHandle, DWORD dwLen, LPVOID lpData)
{
    ensure_redirect();
    typedef BOOL (WINAPI *fn_t)(LPCSTR, DWORD, DWORD, LPVOID);
    GET_REAL(GetFileVersionInfoA, fn_t);
    if (p_GetFileVersionInfoA)
        return p_GetFileVersionInfoA(lptstrFilename, dwHandle, dwLen, lpData);
    return FALSE;
}

__declspec(dllexport) BOOL WINAPI VerQueryValueA(
    LPCVOID pBlock, LPCSTR lpSubBlock, LPVOID *lplpBuffer, PUINT puLen)
{
    ensure_redirect();
    typedef BOOL (WINAPI *fn_t)(LPCVOID, LPCSTR, LPVOID *, PUINT);
    GET_REAL(VerQueryValueA, fn_t);
    if (p_VerQueryValueA)
        return p_VerQueryValueA(pBlock, lpSubBlock, lplpBuffer, puLen);
    return FALSE;
}

/* Remaining VERSION.dll exports (other DLLs in the process might use them) */

__declspec(dllexport) DWORD WINAPI GetFileVersionInfoSizeW(
    LPCWSTR lptstrFilename, LPDWORD lpdwHandle)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(LPCWSTR, LPDWORD);
    GET_REAL(GetFileVersionInfoSizeW, fn_t);
    if (p_GetFileVersionInfoSizeW)
        return p_GetFileVersionInfoSizeW(lptstrFilename, lpdwHandle);
    if (lpdwHandle) *lpdwHandle = 0;
    return 0;
}

__declspec(dllexport) BOOL WINAPI GetFileVersionInfoW(
    LPCWSTR lptstrFilename, DWORD dwHandle, DWORD dwLen, LPVOID lpData)
{
    ensure_redirect();
    typedef BOOL (WINAPI *fn_t)(LPCWSTR, DWORD, DWORD, LPVOID);
    GET_REAL(GetFileVersionInfoW, fn_t);
    if (p_GetFileVersionInfoW)
        return p_GetFileVersionInfoW(lptstrFilename, dwHandle, dwLen, lpData);
    return FALSE;
}

__declspec(dllexport) BOOL WINAPI VerQueryValueW(
    LPCVOID pBlock, LPCWSTR lpSubBlock, LPVOID *lplpBuffer, PUINT puLen)
{
    ensure_redirect();
    typedef BOOL (WINAPI *fn_t)(LPCVOID, LPCWSTR, LPVOID *, PUINT);
    GET_REAL(VerQueryValueW, fn_t);
    if (p_VerQueryValueW)
        return p_VerQueryValueW(pBlock, lpSubBlock, lplpBuffer, puLen);
    return FALSE;
}

__declspec(dllexport) DWORD WINAPI GetFileVersionInfoSizeExA(
    DWORD dwFlags, LPCSTR lpwstrFilename, LPDWORD lpdwHandle)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPCSTR, LPDWORD);
    GET_REAL(GetFileVersionInfoSizeExA, fn_t);
    if (p_GetFileVersionInfoSizeExA)
        return p_GetFileVersionInfoSizeExA(dwFlags, lpwstrFilename, lpdwHandle);
    if (lpdwHandle) *lpdwHandle = 0;
    return 0;
}

__declspec(dllexport) DWORD WINAPI GetFileVersionInfoSizeExW(
    DWORD dwFlags, LPCWSTR lpwstrFilename, LPDWORD lpdwHandle)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPCWSTR, LPDWORD);
    GET_REAL(GetFileVersionInfoSizeExW, fn_t);
    if (p_GetFileVersionInfoSizeExW)
        return p_GetFileVersionInfoSizeExW(dwFlags, lpwstrFilename, lpdwHandle);
    if (lpdwHandle) *lpdwHandle = 0;
    return 0;
}

__declspec(dllexport) BOOL WINAPI GetFileVersionInfoExA(
    DWORD dwFlags, LPCSTR lpwstrFilename, DWORD dwHandle, DWORD dwLen, LPVOID lpData)
{
    ensure_redirect();
    typedef BOOL (WINAPI *fn_t)(DWORD, LPCSTR, DWORD, DWORD, LPVOID);
    GET_REAL(GetFileVersionInfoExA, fn_t);
    if (p_GetFileVersionInfoExA)
        return p_GetFileVersionInfoExA(dwFlags, lpwstrFilename, dwHandle, dwLen, lpData);
    return FALSE;
}

__declspec(dllexport) BOOL WINAPI GetFileVersionInfoExW(
    DWORD dwFlags, LPCWSTR lpwstrFilename, DWORD dwHandle, DWORD dwLen, LPVOID lpData)
{
    ensure_redirect();
    typedef BOOL (WINAPI *fn_t)(DWORD, LPCWSTR, DWORD, DWORD, LPVOID);
    GET_REAL(GetFileVersionInfoExW, fn_t);
    if (p_GetFileVersionInfoExW)
        return p_GetFileVersionInfoExW(dwFlags, lpwstrFilename, dwHandle, dwLen, lpData);
    return FALSE;
}

__declspec(dllexport) DWORD WINAPI VerFindFileA(
    DWORD uFlags, LPSTR szFileName, LPSTR szWinDir, LPSTR szAppDir,
    LPSTR szCurDir, PUINT puCurDirLen, LPSTR szDestDir, PUINT puDestDirLen)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPSTR, LPSTR, LPSTR, LPSTR, PUINT, LPSTR, PUINT);
    GET_REAL(VerFindFileA, fn_t);
    if (p_VerFindFileA)
        return p_VerFindFileA(uFlags, szFileName, szWinDir, szAppDir,
                              szCurDir, puCurDirLen, szDestDir, puDestDirLen);
    return 0;
}

__declspec(dllexport) DWORD WINAPI VerFindFileW(
    DWORD uFlags, LPWSTR szFileName, LPWSTR szWinDir, LPWSTR szAppDir,
    LPWSTR szCurDir, PUINT puCurDirLen, LPWSTR szDestDir, PUINT puDestDirLen)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPWSTR, LPWSTR, LPWSTR, LPWSTR, PUINT, LPWSTR, PUINT);
    GET_REAL(VerFindFileW, fn_t);
    if (p_VerFindFileW)
        return p_VerFindFileW(uFlags, szFileName, szWinDir, szAppDir,
                              szCurDir, puCurDirLen, szDestDir, puDestDirLen);
    return 0;
}

__declspec(dllexport) DWORD WINAPI VerInstallFileA(
    DWORD uFlags, LPSTR szSrcFileName, LPSTR szDestFileName,
    LPSTR szSrcDir, LPSTR szDestDir, LPSTR szCurDir,
    LPSTR szTmpFile, PUINT puTmpFileLen)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPSTR, LPSTR, LPSTR, LPSTR, LPSTR, LPSTR, PUINT);
    GET_REAL(VerInstallFileA, fn_t);
    if (p_VerInstallFileA)
        return p_VerInstallFileA(uFlags, szSrcFileName, szDestFileName,
                                 szSrcDir, szDestDir, szCurDir,
                                 szTmpFile, puTmpFileLen);
    return 0;
}

__declspec(dllexport) DWORD WINAPI VerInstallFileW(
    DWORD uFlags, LPWSTR szSrcFileName, LPWSTR szDestFileName,
    LPWSTR szSrcDir, LPWSTR szDestDir, LPWSTR szCurDir,
    LPWSTR szTmpFile, PUINT puTmpFileLen)
{
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPWSTR, LPWSTR, LPWSTR, LPWSTR, LPWSTR, LPWSTR, PUINT);
    GET_REAL(VerInstallFileW, fn_t);
    if (p_VerInstallFileW)
        return p_VerInstallFileW(uFlags, szSrcFileName, szDestFileName,
                                 szSrcDir, szDestDir, szCurDir,
                                 szTmpFile, puTmpFileLen);
    return 0;
}

__declspec(dllexport) DWORD WINAPI VerLanguageNameA(DWORD wLang, LPSTR szLang, DWORD cchLang) {
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPSTR, DWORD);
    GET_REAL(VerLanguageNameA, fn_t);
    if (p_VerLanguageNameA) return p_VerLanguageNameA(wLang, szLang, cchLang);
    return 0;
}

__declspec(dllexport) DWORD WINAPI VerLanguageNameW(DWORD wLang, LPWSTR szLang, DWORD cchLang) {
    ensure_redirect();
    typedef DWORD (WINAPI *fn_t)(DWORD, LPWSTR, DWORD);
    GET_REAL(VerLanguageNameW, fn_t);
    if (p_VerLanguageNameW) return p_VerLanguageNameW(wLang, szLang, cchLang);
    return 0;
}
