/*
 * stdout_redirect.dll - Redirects C stdout to a file for Hades/Wine
 *
 * Build: x86_64-w64-mingw32-gcc -shared -o stdout_redirect.dll stdout_redirect.c -Wl,--subsystem,windows
 */

#include <windows.h>
#include <stdio.h>

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        char exename[MAX_PATH];
        GetModuleFileNameA(NULL, exename, MAX_PATH);

        /* Write a marker file to prove DLL loaded (relative to exe cwd) */
        FILE *marker = fopen("hadesmp_dll_loaded.txt", "w");
        if (marker) {
            fprintf(marker, "DLL loaded in: %s\n", exename);
            fclose(marker);
        }

        /* Only redirect stdout for Hades.exe */
        if (strstr(exename, "Hades.exe") != NULL ||
            strstr(exename, "hades.exe") != NULL) {

            /* Use relative path - cwd should be game's exe directory */
            FILE *f = freopen("hades_lua_stdout.log", "a", stdout);
            if (f) {
                setvbuf(stdout, NULL, _IONBF, 0);
            }

            /* Also try absolute path via the exe's own directory */
            if (!f) {
                /* Extract directory from exe path */
                char dir[MAX_PATH];
                strncpy(dir, exename, MAX_PATH);
                char *last_slash = strrchr(dir, '\\');
                if (last_slash) {
                    *(last_slash + 1) = '\0';
                    char fullpath[MAX_PATH];
                    snprintf(fullpath, MAX_PATH, "%shades_lua_stdout.log", dir);
                    f = freopen(fullpath, "a", stdout);
                    if (f) {
                        setvbuf(stdout, NULL, _IONBF, 0);
                    }
                }
            }

            /* Write confirmation */
            if (f) {
                fprintf(stdout, "HADESMP:DLL_STDOUT_REDIRECTED\n");
                fflush(stdout);
            }
        }
    }
    return TRUE;
}
