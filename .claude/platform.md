# Platform Detection

`hadesmp_platform.py` → returns `GameConfig` dataclass: `game_dir`, `Content`, `log`, `inbox`.

## Detection
- **Windows:** Registry + common Steam paths
- **WSL2:** scans /mnt/c,d,e for Steam libraries
- **Linux:** `~/.local/share/Steam`, `~/.steam/steam`

## Env Overrides
- `HADES_ROOT=/path/to/Hades`
- `WINE_PREFIX=/path/to/prefix`
