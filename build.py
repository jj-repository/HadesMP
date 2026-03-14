#!/usr/bin/env python3
"""
HadesMP Unified Build Script — build and deploy DLL proxies from any platform.

Supports:
  - WSL2: cross-compile with x86_64-w64-mingw32-gcc, deploy to Windows game dir
  - Native Linux: cross-compile with mingw-w64, deploy to Proton game dir
  - Native Windows: compile with GCC (MinGW-w64) or MSVC

Usage:
    python3 build.py [--no-deploy] [--game-dir /path/to/Hades/x64]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add project dir to path
sys.path.insert(0, str(Path(__file__).parent))
from hadesmp_platform import detect_platform, detect_game_dir, GameConfig

SCRIPT_DIR = Path(__file__).parent.resolve()
DLLS = ["stdout_redirect.dll", "lua52.dll", "VERSION.dll"]


def find_compiler(plat: str) -> tuple[str, str]:
    """Find a suitable C compiler. Returns (compiler_path, compiler_type)."""
    if plat in ("wsl2", "linux"):
        # Cross-compile for Windows
        for cc in ["x86_64-w64-mingw32-gcc"]:
            if shutil.which(cc):
                return cc, "mingw"
        print("error: x86_64-w64-mingw32-gcc not found", file=sys.stderr)
        print("  install: sudo apt install gcc-mingw-w64-x86-64", file=sys.stderr)
        sys.exit(1)
    else:
        # Native Windows
        if shutil.which("gcc"):
            return "gcc", "gcc"
        if shutil.which("cl"):
            return "cl", "msvc"
        print("error: no C compiler found (need GCC or MSVC)", file=sys.stderr)
        print("  install MinGW-w64 via MSYS2: pacman -S mingw-w64-x86_64-gcc", file=sys.stderr)
        sys.exit(1)


def build_dlls(cc: str, cc_type: str) -> list[Path]:
    """Build all 3 proxy DLLs. Returns list of built DLL paths."""
    built = []

    if cc_type in ("mingw", "gcc"):
        # stdout_redirect.dll
        print("\n=== Building stdout_redirect.dll ===")
        cmd = [cc, "-shared", "-o", str(SCRIPT_DIR / "stdout_redirect.dll"),
               str(SCRIPT_DIR / "stdout_redirect.c"),
               "-Wl,--subsystem,windows", "-O2"]
        subprocess.check_call(cmd)
        built.append(SCRIPT_DIR / "stdout_redirect.dll")
        print("Built: stdout_redirect.dll")

        # lua52.dll (proxy)
        print("\n=== Building lua52.dll (proxy) ===")
        cmd = [cc, "-shared", "-o", str(SCRIPT_DIR / "lua52.dll"),
               str(SCRIPT_DIR / "lua52_proxy.c"), str(SCRIPT_DIR / "lua52.def"), "-O2"]
        subprocess.check_call(cmd)
        built.append(SCRIPT_DIR / "lua52.dll")
        print("Built: lua52.dll")

        # VERSION.dll (proxy)
        print("\n=== Building VERSION.dll (proxy) ===")
        cmd = [cc, "-shared", "-o", str(SCRIPT_DIR / "VERSION.dll"),
               str(SCRIPT_DIR / "version_proxy.c"), "-O2"]
        if cc_type == "gcc":
            cmd.append("-lversion")
        subprocess.check_call(cmd)
        built.append(SCRIPT_DIR / "VERSION.dll")
        print("Built: VERSION.dll")

    elif cc_type == "msvc":
        # MSVC builds
        print("\n=== Building stdout_redirect.dll ===")
        subprocess.check_call([
            "cl", "/LD", "/O2", f"/Fe:{SCRIPT_DIR / 'stdout_redirect.dll'}",
            str(SCRIPT_DIR / "stdout_redirect.c"),
            "/link", "/SUBSYSTEM:WINDOWS", "kernel32.lib",
        ])
        built.append(SCRIPT_DIR / "stdout_redirect.dll")

        print("\n=== Building lua52.dll (proxy) ===")
        subprocess.check_call([
            "cl", "/LD", "/O2", f"/Fe:{SCRIPT_DIR / 'lua52.dll'}",
            str(SCRIPT_DIR / "lua52_proxy.c"),
            "/link", f"/DEF:{SCRIPT_DIR / 'lua52.def'}",
        ])
        built.append(SCRIPT_DIR / "lua52.dll")

        print("\n=== Building VERSION.dll (proxy) ===")
        subprocess.check_call([
            "cl", "/LD", "/O2", f"/Fe:{SCRIPT_DIR / 'VERSION.dll'}",
            str(SCRIPT_DIR / "version_proxy.c"),
            "/link", "version.lib", "kernel32.lib",
        ])
        built.append(SCRIPT_DIR / "VERSION.dll")

    return built


def deploy_dlls(config: GameConfig):
    """Deploy built DLLs to the game directory."""
    game_dir = config.game_dir
    print(f"\n=== Deploying to {game_dir} ===")

    # VERSION.dll
    src = SCRIPT_DIR / "VERSION.dll"
    if src.exists():
        shutil.copy2(src, game_dir / "VERSION.dll")
        print(f"Installed: {game_dir / 'VERSION.dll'}")

    # lua52.dll — back up original first
    original = game_dir / "lua52_original.dll"
    game_lua52 = game_dir / "lua52.dll"
    if not original.exists() and game_lua52.exists():
        print("Backing up original lua52.dll -> lua52_original.dll")
        shutil.copy2(game_lua52, original)

    src = SCRIPT_DIR / "lua52.dll"
    if src.exists():
        shutil.copy2(src, game_lua52)
        print(f"Installed: {game_lua52}")

    # stdout_redirect.dll (optional — only needed for AppInit_DLLs approach)
    src = SCRIPT_DIR / "stdout_redirect.dll"
    if src.exists():
        shutil.copy2(src, game_dir / "stdout_redirect.dll")
        print(f"Installed: {game_dir / 'stdout_redirect.dll'}")


def main():
    parser = argparse.ArgumentParser(description="HadesMP Unified Build Script")
    parser.add_argument("--no-deploy", action="store_true",
                        help="Build DLLs but don't deploy to game directory")
    parser.add_argument("--game-dir", type=Path, default=None,
                        help="Override game directory path")
    parser.add_argument("--clean", action="store_true",
                        help="Remove built DLLs from project directory")
    args = parser.parse_args()

    plat = detect_platform()
    print(f"Platform: {plat}")

    if args.clean:
        for dll in DLLS:
            p = SCRIPT_DIR / dll
            if p.exists():
                p.unlink()
                print(f"Removed: {p}")
        # Also remove MSVC artifacts
        for ext in ("*.obj", "*.lib", "*.exp"):
            for f in SCRIPT_DIR.glob(ext):
                f.unlink()
                print(f"Removed: {f}")
        return

    # Find compiler
    cc, cc_type = find_compiler(plat)
    print(f"Compiler: {cc} ({cc_type})")

    # Build
    try:
        built = build_dlls(cc, cc_type)
    except subprocess.CalledProcessError as e:
        print(f"\nerror: build failed (exit code {e.returncode})", file=sys.stderr)
        sys.exit(1)

    if not built:
        print("error: no DLLs built", file=sys.stderr)
        sys.exit(1)

    # Deploy
    if args.no_deploy:
        print("\n=== Skipping deployment (--no-deploy) ===")
        return

    if args.game_dir:
        from hadesmp_platform import GameConfig
        config = GameConfig(
            game_dir=args.game_dir.resolve(),
            hades_root=args.game_dir.resolve().parent,
            game_subdir=args.game_dir.name,
            platform=plat,
            is_wsl=(plat == "wsl2"),
            log_path=args.game_dir / "hades_lua_stdout.log",
            inbox_path=args.game_dir / "hadesmp_inbox.lua",
            content_dir=args.game_dir.resolve().parent / "Content",
        )
    else:
        try:
            config = detect_game_dir(plat)
        except FileNotFoundError as e:
            print(f"\nwarning: {e}")
            print("DLLs built but not deployed. Use --game-dir to deploy manually.")
            return

    if not config.game_dir.is_dir():
        print(f"error: game directory not found: {config.game_dir}", file=sys.stderr)
        print("DLLs built but not deployed.")
        return

    deploy_dlls(config)

    print(f"\n=== Done ===")
    print(f"Launch Hades and check for hades_lua_stdout.log in {config.game_dir}")


if __name__ == "__main__":
    main()
