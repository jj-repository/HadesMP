@echo off
REM Build proxy DLLs for HadesMP on Windows
REM Requires: MinGW-w64 (install via MSYS2: pacman -S mingw-w64-x86_64-gcc)
REM   or Visual Studio Developer Command Prompt (cl.exe)

setlocal enabledelayedexpansion

REM Auto-detect Hades install path via Steam
set "HADES_ROOT="
for %%D in (
    "%ProgramFiles(x86)%\Steam\steamapps\common\Hades"
    "%ProgramFiles%\Steam\steamapps\common\Hades"
    "D:\SteamLibrary\steamapps\common\Hades"
    "E:\SteamLibrary\steamapps\common\Hades"
    "F:\SteamLibrary\steamapps\common\Hades"
) do (
    if exist "%%~D\x64\Hades.exe" (
        set "HADES_ROOT=%%~D"
        goto :found_hades
    )
)

echo [!] Could not auto-detect Hades install path.
echo     Set HADES_ROOT manually: set HADES_ROOT=C:\path\to\Hades
echo     Then re-run this script.
if not defined HADES_ROOT goto :eof
:found_hades
echo [*] Hades found at: %HADES_ROOT%

REM Detect compiler
where gcc >nul 2>&1
if %errorlevel%==0 (
    set "COMPILER=gcc"
    echo [*] Using GCC (MinGW-w64)
    goto :build_gcc
)

where cl >nul 2>&1
if %errorlevel%==0 (
    set "COMPILER=msvc"
    echo [*] Using MSVC (cl.exe)
    goto :build_msvc
)

echo [!] No compiler found. Install one of:
echo     - MSYS2 MinGW-w64: https://www.msys2.org/
echo       Then: pacman -S mingw-w64-x86_64-gcc
echo       Add C:\msys64\mingw64\bin to PATH
echo     - Visual Studio Build Tools with C++ workload
goto :eof

:build_gcc
echo.
echo === Building stdout_redirect.dll ===
gcc -shared -o stdout_redirect.dll stdout_redirect.c -Wl,--subsystem,windows -O2
if %errorlevel% neq 0 ( echo [!] Failed to build stdout_redirect.dll & goto :eof )
echo Built: stdout_redirect.dll

echo.
echo === Building lua52.dll (proxy) ===
gcc -shared -o lua52.dll lua52_proxy.c lua52.def -O2
if %errorlevel% neq 0 ( echo [!] Failed to build lua52.dll & goto :eof )
echo Built: lua52.dll

echo.
echo === Building VERSION.dll (proxy) ===
gcc -shared -o VERSION.dll version_proxy.c -O2 -lversion
if %errorlevel% neq 0 ( echo [!] Failed to build VERSION.dll & goto :eof )
echo Built: VERSION.dll

goto :install

:build_msvc
echo.
echo === Building stdout_redirect.dll ===
cl /LD /O2 /Fe:stdout_redirect.dll stdout_redirect.c /link /SUBSYSTEM:WINDOWS kernel32.lib
if %errorlevel% neq 0 ( echo [!] Failed to build stdout_redirect.dll & goto :eof )

echo.
echo === Building lua52.dll (proxy) ===
cl /LD /O2 /Fe:lua52.dll lua52_proxy.c /link /DEF:lua52.def
if %errorlevel% neq 0 ( echo [!] Failed to build lua52.dll & goto :eof )

echo.
echo === Building VERSION.dll (proxy) ===
cl /LD /O2 /Fe:VERSION.dll version_proxy.c /link version.lib kernel32.lib
if %errorlevel% neq 0 ( echo [!] Failed to build VERSION.dll & goto :eof )

goto :install

:install
echo.
echo === Installing DLLs ===

REM Hades uses x64 directory on native Windows
set "DEST=%HADES_ROOT%\x64"
if not exist "%DEST%" (
    echo [!] Game directory not found: %DEST%
    echo     DLLs built but not installed. Copy manually to your Hades\x64 folder.
    goto :done
)

copy /Y VERSION.dll "%DEST%\VERSION.dll"
echo Installed: %DEST%\VERSION.dll

REM lua52 proxy: rename original first
if not exist "%DEST%\lua52_original.dll" (
    if exist "%DEST%\lua52.dll" (
        echo Backing up original lua52.dll -^> lua52_original.dll
        copy /Y "%DEST%\lua52.dll" "%DEST%\lua52_original.dll"
    )
)
copy /Y lua52.dll "%DEST%\lua52.dll"
echo Installed: %DEST%\lua52.dll

:done
echo.
echo === Done ===
echo DLLs built successfully.
if defined DEST (
    echo Installed to: %DEST%
    echo.
    echo To test: launch Hades, check for hades_lua_stdout.log in the x64 folder.
    echo To uninstall: delete VERSION.dll and lua52.dll from %DEST%,
    echo              rename lua52_original.dll back to lua52.dll.
)
endlocal
