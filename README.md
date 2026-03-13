# HadesMP - Multiplayer Mod for Hades

> **WARNING: This project is a Work In Progress and is NOT functional yet.**
> Everything is experimental — expect broken builds, missing features, and incomplete systems.
> Contributions and feedback are welcome, but do not expect a playable experience at this stage.

A multiplayer mod for [Hades](https://store.steampowered.com/app/1145360/Hades/) (Supergiant Games) using DLL proxy injection to intercept Lua calls and bridge game state between players.

## How It Works

The mod uses proxy DLLs to intercept the game's Lua 5.2 runtime:

- **`VERSION.dll`** — Proxy for the system VERSION.dll. Redirects stdout/stderr so Lua `print()` output can be captured.
- **`lua52.dll`** — Proxy for the game's Lua runtime. Intercepts `luaopen_debug` to inject `io`, `os`, and `package` libraries (normally stripped by the game).
- **`stdout_redirect.dll`** — Alternative stdout redirect via AppInit_DLLs (Linux/Wine only).
- **`hadesmp_bridge.py`** — Python bridge server that connects two game instances.

## Prerequisites

### Windows
- **MinGW-w64** via [MSYS2](https://www.msys2.org/): `pacman -S mingw-w64-x86_64-gcc`
  - Add `C:\msys64\mingw64\bin` to your PATH
- **Or** Visual Studio Build Tools with C++ workload (`cl.exe`)
- Python 3.8+ (for the bridge server)

### Linux
- `mingw-w64` cross-compiler: `sudo pacman -S mingw-w64-gcc` (Arch) or `sudo apt install gcc-mingw-w64-x86-64` (Debian/Ubuntu)
- Wine/Proton (via Steam)
- Python 3.8+

## Building

### Windows
```cmd
build_dll.bat
```

### Linux
```bash
chmod +x build_dll.sh
./build_dll.sh
```

Both scripts auto-detect the Hades install path. Override with:
```bash
# Linux
HADES_ROOT=/path/to/Hades ./build_dll.sh

# Windows (cmd)
set HADES_ROOT=D:\Games\Hades
build_dll.bat
```

## Uninstalling

1. Delete `VERSION.dll` and `lua52.dll` from the Hades game directory (`x64/` or `x64Vk/`)
2. Rename `lua52_original.dll` back to `lua52.dll`
