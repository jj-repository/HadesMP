#!/usr/bin/env python3
"""
HadesMP Mod Deployer — install Lua mod scripts to the Hades Content directory.

Copies lua/HadesMP.lua and lua/HadesMPP2.lua to:
  {hades_root}/Content/Mods/HadesMP/

The bridge auto-bootstraps the mod via EXEC:dofile("Content/Mods/HadesMP/HadesMP.lua")
on first heartbeat.

Usage:
    python3 deploy_mod.py [--game-dir /path/to/Hades/x64]
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hadesmp_platform import detect_platform, detect_game_dir

SCRIPT_DIR = Path(__file__).parent.resolve()
LUA_DIR = SCRIPT_DIR / "lua"

MOD_FILES = [
    "HadesMP.lua",
    "HadesMPP2.lua",
]


def deploy(content_dir: Path):
    """Copy Lua mod files to the Content/Mods/HadesMP directory."""
    mod_dir = content_dir / "Mods" / "HadesMP"
    mod_dir.mkdir(parents=True, exist_ok=True)

    for filename in MOD_FILES:
        src = LUA_DIR / filename
        dst = mod_dir / filename
        if not src.exists():
            print(f"warning: {src} not found, skipping", file=sys.stderr)
            continue
        shutil.copy2(src, dst)
        print(f"Installed: {dst}")

    print(f"\nMod files deployed to: {mod_dir}")
    return mod_dir


def main():
    parser = argparse.ArgumentParser(description="HadesMP Mod Deployer")
    parser.add_argument("--game-dir", type=Path, default=None,
                        help="Override game directory path")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deployed without copying")
    args = parser.parse_args()

    plat = detect_platform()
    print(f"Platform: {plat}")

    if args.game_dir:
        content_dir = args.game_dir.resolve().parent / "Content"
    else:
        try:
            config = detect_game_dir(plat)
            content_dir = config.content_dir
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Content dir: {content_dir}")

    if args.dry_run:
        mod_dir = content_dir / "Mods" / "HadesMP"
        print(f"\nWould deploy to: {mod_dir}")
        for f in MOD_FILES:
            src = LUA_DIR / f
            print(f"  {src} -> {mod_dir / f}  {'(exists)' if src.exists() else '(MISSING)'}")
        return

    if not content_dir.is_dir():
        print(f"error: Content directory not found: {content_dir}", file=sys.stderr)
        print("Use --game-dir to specify the path manually.", file=sys.stderr)
        sys.exit(1)

    mod_dir = deploy(content_dir)

    print(f"\nThe bridge will auto-load the mod on first heartbeat via:")
    print(f'  EXEC:dofile("Content/Mods/HadesMP/HadesMP.lua")')
    print(f"\nTo verify: launch Hades, start a run, then run the bridge.")


if __name__ == "__main__":
    main()
