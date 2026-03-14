#!/usr/bin/env python3
"""
HadesMP Platform Detection — auto-detect environment, Hades install, and paths.

Supports:
  - Native Windows (game runs natively, Python runs natively)
  - WSL2 (game runs on Windows natively, Python runs in WSL2)
  - Native Linux (game runs under Proton/Wine)
"""

import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GameConfig:
    """Resolved game configuration for the current platform."""
    game_dir: Path          # e.g. .../Hades/x64 or .../Hades/x64Vk
    hades_root: Path        # e.g. .../Hades
    game_subdir: str        # "x64" or "x64Vk"
    platform: str           # "windows", "wsl2", "linux"
    is_wsl: bool
    log_path: Path          # game_dir / hades_lua_stdout.log
    inbox_path: Path        # game_dir / hadesmp_inbox.lua
    content_dir: Path       # .../Hades/Content (for mods)


def detect_platform() -> str:
    """Detect the current platform: 'windows', 'wsl2', or 'linux'."""
    if platform.system() == "Windows":
        return "windows"
    if platform.system() == "Linux":
        try:
            version = Path("/proc/version").read_text()
            if "microsoft" in version.lower() or "wsl" in version.lower():
                return "wsl2"
        except OSError:
            pass
        return "linux"
    return platform.system().lower()


def _parse_libraryfolders_vdf(vdf_path: Path) -> list[Path]:
    """Parse Steam's libraryfolders.vdf to extract library paths."""
    paths = []
    try:
        text = vdf_path.read_text(errors="replace")
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            p = Path(match.group(1))
            if p.is_dir():
                paths.append(p)
    except OSError:
        pass
    return paths


def _find_hades_windows() -> Path | None:
    """Find Hades on native Windows via registry and common paths."""
    # Try Steam registry key
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
        winreg.CloseKey(key)
        vdf = steam_path / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            for lib in _parse_libraryfolders_vdf(vdf):
                candidate = lib / "steamapps" / "common" / "Hades"
                if candidate.is_dir():
                    return candidate
    except (ImportError, OSError):
        pass

    # Fallback: common paths
    for base in [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    ]:
        candidate = base / "Steam" / "steamapps" / "common" / "Hades"
        if candidate.is_dir():
            return candidate

    # Check additional drive letters
    for drive in "DEFG":
        candidate = Path(f"{drive}:\\SteamLibrary\\steamapps\\common\\Hades")
        if candidate.is_dir():
            return candidate

    return None


def _find_hades_wsl2() -> Path | None:
    """Find Hades from WSL2 by scanning Windows Steam libraries via /mnt/."""
    # Check all /mnt/<drive> for Steam installations
    vdf_candidates = []

    for drive_letter in "cdefg":
        mnt = Path(f"/mnt/{drive_letter}")
        if not mnt.is_dir():
            continue

        # Standard Steam location
        steam_base = mnt / "Program Files (x86)" / "Steam"
        vdf = steam_base / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            vdf_candidates.append(vdf)

        # Direct SteamLibrary on drive root
        lib = mnt / "SteamLibrary" / "steamapps" / "common" / "Hades"
        if lib.is_dir():
            return lib

    # Parse VDFs for additional library folders
    for vdf in vdf_candidates:
        for lib_path in _parse_libraryfolders_vdf(vdf):
            # Convert Windows paths (C:\SteamLibrary) to WSL paths (/mnt/c/SteamLibrary)
            path_str = str(lib_path)
            if len(path_str) >= 2 and path_str[1] == ":":
                drive = path_str[0].lower()
                rest = path_str[2:].replace("\\", "/")
                wsl_path = Path(f"/mnt/{drive}{rest}")
            else:
                wsl_path = lib_path

            candidate = wsl_path / "steamapps" / "common" / "Hades"
            if candidate.is_dir():
                return candidate

    # Also check ext4 game drives (common setup)
    for p in Path("/mnt").iterdir():
        if not p.is_dir():
            continue
        for pattern in [
            p / "SteamLibrary" / "steamapps" / "common" / "Hades",
        ]:
            if pattern.is_dir():
                return pattern

    return None


def _find_hades_linux() -> Path | None:
    """Find Hades on native Linux via Steam library folders."""
    steam_dirs = [
        Path.home() / ".local" / "share" / "Steam" / "steamapps",
        Path.home() / ".steam" / "steam" / "steamapps",
    ]

    # Parse libraryfolders.vdf for additional paths
    for base in list(steam_dirs):
        vdf = base / "libraryfolders.vdf"
        if vdf.exists():
            for lib_path in _parse_libraryfolders_vdf(vdf):
                extra = lib_path / "steamapps"
                if extra.is_dir() and extra not in steam_dirs:
                    steam_dirs.append(extra)

    for d in steam_dirs:
        candidate = d / "common" / "Hades"
        if candidate.is_dir():
            return candidate

    return None


def detect_game_dir(plat: str | None = None) -> GameConfig:
    """Auto-detect Hades game directory and return a GameConfig.

    Raises FileNotFoundError if Hades cannot be found.
    Respects HADES_ROOT env var as override.
    """
    if plat is None:
        plat = detect_platform()

    # Env var override
    env_root = os.environ.get("HADES_ROOT")
    if env_root:
        hades_root = Path(env_root)
    elif plat == "windows":
        hades_root = _find_hades_windows()
    elif plat == "wsl2":
        hades_root = _find_hades_wsl2()
    elif plat == "linux":
        hades_root = _find_hades_linux()
    else:
        hades_root = None

    if hades_root is None or not hades_root.is_dir():
        raise FileNotFoundError(
            f"Could not find Hades install directory (platform={plat}).\n"
            "Set HADES_ROOT environment variable to your Hades directory.\n"
            "  e.g.: export HADES_ROOT=/mnt/c/.../steamapps/common/Hades"
        )

    # Determine subdirectory: x64Vk for Linux/Proton, x64 for Windows/WSL2
    if plat == "linux":
        subdir = "x64Vk" if (hades_root / "x64Vk").is_dir() else "x64"
    else:
        # Windows and WSL2 both target native Windows game -> x64
        subdir = "x64" if (hades_root / "x64").is_dir() else "x64Vk"

    game_dir = hades_root / subdir
    if not game_dir.is_dir():
        raise FileNotFoundError(
            f"Game subdirectory not found: {game_dir}\n"
            f"Expected '{subdir}' inside {hades_root}"
        )

    content_dir = hades_root / "Content"

    return GameConfig(
        game_dir=game_dir,
        hades_root=hades_root,
        game_subdir=subdir,
        platform=plat,
        is_wsl=(plat == "wsl2"),
        log_path=game_dir / "hades_lua_stdout.log",
        inbox_path=game_dir / "hadesmp_inbox.lua",
        content_dir=content_dir,
    )


def print_config(config: GameConfig):
    """Print detected configuration."""
    print(f"Platform:     {config.platform}")
    print(f"WSL2:         {config.is_wsl}")
    print(f"Hades root:   {config.hades_root}")
    print(f"Game dir:     {config.game_dir}")
    print(f"Game subdir:  {config.game_subdir}")
    print(f"Log path:     {config.log_path}")
    print(f"Inbox path:   {config.inbox_path}")
    print(f"Content dir:  {config.content_dir}")


if __name__ == "__main__":
    plat = detect_platform()
    print(f"Detected platform: {plat}")
    try:
        config = detect_game_dir(plat)
        print_config(config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
