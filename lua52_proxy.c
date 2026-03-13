/*
 * lua52 proxy DLL - Intercepts Lua init to inject io/os/package + redirect stdout
 *
 * Build: x86_64-w64-mingw32-gcc -shared -o lua52.dll lua52_proxy.c lua52.def -O2
 */

#include <windows.h>
#include <stdio.h>

typedef void lua_State;
typedef int (*luaopen_func)(lua_State *L);
typedef void (*lua_setglobal_func)(lua_State *L, const char *name);

static HMODULE g_original = NULL;
static int g_injected = 0;
static char g_exedir[MAX_PATH] = {0};

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        /* Load the real lua52 DLL */
        g_original = LoadLibraryA("lua52_original.dll");

        /* Save exe directory for later use (safe Win32 API call) */
        GetModuleFileNameA(NULL, g_exedir, MAX_PATH);
        char *last = strrchr(g_exedir, '\\');
        if (last) *(last + 1) = '\0';

        /* Write a marker using raw Win32 API (safe in DllMain) */
        char markerpath[MAX_PATH];
        snprintf(markerpath, MAX_PATH, "%shadesmp_dll_marker.txt", g_exedir);
        HANDLE h = CreateFileA(markerpath, GENERIC_WRITE, 0, NULL,
                               CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (h != INVALID_HANDLE_VALUE) {
            const char *msg = "lua52 proxy DLL loaded OK\r\n";
            DWORD written;
            WriteFile(h, msg, strlen(msg), &written, NULL);

            char buf[512];
            snprintf(buf, sizeof(buf), "original dll: %p\r\nexedir: %s\r\n",
                     (void*)g_original, g_exedir);
            WriteFile(h, buf, strlen(buf), &written, NULL);
            CloseHandle(h);
        }
    }
    return TRUE;
}

__declspec(dllexport) int luaopen_debug(lua_State *L) {
    /* Redirect stdout NOW (safe outside DllMain) */
    if (!g_injected) {
        char logpath[MAX_PATH];
        snprintf(logpath, MAX_PATH, "%shades_lua_stdout.log", g_exedir);

        FILE *f = freopen(logpath, "w", stdout);
        if (f) {
            setvbuf(stdout, NULL, _IONBF, 0);
            fprintf(stdout, "HADESMP:PROXY:stdout_redirected path=%s\n", logpath);
        }

        /* Also try stderr */
        char logpath2[MAX_PATH];
        snprintf(logpath2, MAX_PATH, "%shades_lua_stderr.log", g_exedir);
        freopen(logpath2, "w", stderr);
    }

    /* Call original luaopen_debug */
    luaopen_func orig = (luaopen_func)GetProcAddress(g_original, "luaopen_debug");
    int result = 0;
    if (orig) result = orig(L);

    /* Inject io/os/package (only once) */
    if (!g_injected && g_original) {
        g_injected = 1;

        lua_setglobal_func setglobal =
            (lua_setglobal_func)GetProcAddress(g_original, "lua_setglobal");

        luaopen_func open_io = (luaopen_func)GetProcAddress(g_original, "luaopen_io");
        luaopen_func open_os = (luaopen_func)GetProcAddress(g_original, "luaopen_os");
        luaopen_func open_pkg = (luaopen_func)GetProcAddress(g_original, "luaopen_package");

        if (setglobal) {
            if (open_io) {
                open_io(L);
                setglobal(L, "io");
                fprintf(stdout, "HADESMP:PROXY:io_injected\n");
            }
            if (open_os) {
                open_os(L);
                setglobal(L, "os");
                fprintf(stdout, "HADESMP:PROXY:os_injected\n");
            }
            if (open_pkg) {
                open_pkg(L);
                setglobal(L, "package");
                fprintf(stdout, "HADESMP:PROXY:package_injected\n");
            }
        }
        fflush(stdout);
    }

    return result;
}
