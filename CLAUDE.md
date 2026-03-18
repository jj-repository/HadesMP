# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**HadesMP** is a work-in-progress multiplayer co-op mod for Hades (Supergiant Games). It uses DLL proxy injection to capture Lua output, a Python bridge for IPC, and TCP/UDP networking to connect two game instances.

**Version:** 0.1.0 (WIP)

## Files Structure

```
HadesMP/
├── C Source (DLL Proxies)
│   ├── lua52_proxy.c           # Intercepts luaopen_debug, redirects stdout, injects io/os/package
│   ├── version_proxy.c         # VERSION.dll proxy, UCRT stdout redirect (404 lines)
│   ├── stdout_redirect.c       # Simple AppInit_DLLs approach (58 lines)
│   ├── lua52.def               # Lua 5.2 export definitions
│   └── lua52_proxy.c.def       # Proxy export definitions
│
├── Python (Bridge + Networking)
│   ├── hadesmp_bridge.py       # Main IPC bridge: stdout watcher + inbox writer (713 lines)
│   ├── hadesmp_net.py          # TCP/UDP transport layer (456 lines)
│   ├── hadesmp_platform.py     # Platform detection: Windows/WSL2/Linux (247 lines)
│   ├── build.py                # Unified build script (220 lines)
│   └── deploy_mod.py           # Copies Lua mods to game Content/ (95 lines)
│
├── Lua Mods
│   ├── lua/HadesMP.lua         # P1 mod: heartbeat, inbox polling, message dispatch (333 lines)
│   └── lua/HadesMPP2.lua       # P2 entity: spawn, movement, combat, animation
│
├── Build Scripts
│   ├── build_dll.sh            # Linux/WSL2 build (MinGW cross-compile)
│   └── build_dll.bat           # Windows build (GCC or MSVC)
│
├── Tests
│   ├── tests/test_platform.py  # Platform detection tests
│   ├── tests/test_net.py       # TCP/UDP networking tests
│   ├── test_spawn.py           # Manual P2 spawn test
│   ├── test_p2.py              # Manual P2 control test
│   └── hadesmp_p2_test.py      # Legacy test
│
├── Documentation
│   ├── CONTEXT.md              # Hades modding knowledge base index
│   ├── MULTIPLAYER-MOD.md      # Project plan (Phases 0-3)
│   ├── CORE-SYSTEMS.md         # Game engine systems
│   ├── ENGINE-AND-FORMATS.md   # AQUARIUS engine, SJSON, animations
│   ├── ENEMIES-AI-ENCOUNTERS.md
│   ├── GAME-DATA-REFERENCE.md
│   ├── NPCS-QUESTS-PROGRESSION.md
│   ├── UI-PRESENTATION-DEBUG.md
│   └── MODDING-GUIDE.md
│
├── README.md
└── .gitignore
```

## Build and Run Commands

```bash
# Build DLLs (auto-detects platform, compiler, game directory)
python3 build.py
python3 build.py --no-deploy    # Build only, don't copy to game
python3 build.py --clean        # Remove built DLLs

# Deploy Lua mods to game Content/
python3 deploy_mod.py

# Run bridge
python3 hadesmp_bridge.py --mode solo      # Test without networking
python3 hadesmp_bridge.py --mode host      # Host (awaits client)
python3 hadesmp_bridge.py --mode client --host <ip>  # Client

# Run tests
python3 -m pytest tests/ -v
```

## Architecture Overview

### Data Flow
```
Game (Hades.exe)
  ↕ DLL proxy injection (lua52.dll / VERSION.dll)
  ↕ stdout → hades_lua_stdout.log (Lua prints HADESMP: prefixed lines)
  ↕ stdin  ← hadesmp_inbox.lua (Python writes Lua commands)
Python Bridge (hadesmp_bridge.py)
  ↕ TCP (reliable: room transitions, events, handshake)
  ↕ UDP (fast: position sync at 20Hz)
Remote Bridge (other player)
  ↕ Same DLL/Lua/Bridge stack
Remote Game
```

### Components

1. **DLL Proxies (C)** — Loaded by game at startup
   - `lua52_proxy.c`: Intercepts `luaopen_debug`, redirects stdout to log file, injects io/os/package libraries
   - `version_proxy.c`: Alternative proxy via VERSION.dll, uses UCRT for stdout redirect

2. **Bridge (Python)** — Orchestrates communication
   - `StdoutWatcher`: Tail-follows log file for `HADESMP:` messages
   - `InboxWriter`: Atomic writes to `hadesmp_inbox.lua` (Lua dofile source)
   - `HadesMPBridge`: Main controller — heartbeat tracking, P2 state, CLI interface

3. **Networking (Python)** — TCP/UDP between two bridges
   - TCP: Handshake, game events, room transitions, boon picks
   - UDP: Position sync (20Hz), sequence-numbered, drops out-of-order

4. **Lua Mods** — Run inside the game engine
   - `HadesMP.lua`: Heartbeat loop, inbox polling, message dispatch, P1 position reporting
   - `HadesMPP2.lua`: P2 entity spawning, movement, combat, animation

### Message Protocol

**Lua → Python** (via stdout log):
```
HADESMP:HB                        # Heartbeat (~10Hz)
HADESMP:P1POS:<x>,<y>,<angle>     # Hero position
HADESMP:ROOM:<name>               # Room transition
HADESMP:ACK:<seq>                  # Inbox acknowledged
HADESMP:PONG:<timestamp>          # Ping response
HADESMP:P2EVT:<payload>           # P2 events
```

**Python → Lua** (via inbox file):
```
PING:<timestamp>                   # Latency measurement
P2ENABLE:<0|1>                     # Enable/disable P2
P2SYNC:<x>,<y>,<angle>,<anim>     # Combined P2 update
EXEC:<lua_code>                    # Execute arbitrary Lua
```

**Network (TCP/UDP between bridges):**
```
TCP: [4B length][1B type][JSON]    # Reliable messages
UDP: [2B seq][1B type][JSON]       # Position updates
```

## Platform Detection

`hadesmp_platform.py` auto-detects:
- **Windows**: Registry + common Steam paths
- **WSL2**: Scans /mnt/c,d,e for Steam libraries
- **Linux**: ~/.local/share/Steam, ~/.steam/steam

Returns `GameConfig` dataclass with paths to game_dir, Content, log, inbox.

**Environment overrides:**
- `HADES_ROOT=/path/to/Hades`
- `WINE_PREFIX=/path/to/prefix`

## Dependencies

No managed dependencies. Uses Python stdlib only:
- `socket`, `threading`, `json`, `struct`, `pathlib`, `dataclasses`
- `subprocess` (for build scripts)

C compilation requires:
- Linux/WSL2: `x86_64-w64-mingw32-gcc` (MinGW cross-compiler)
- Windows: GCC or MSVC (`cl.exe`)

## Testing

**Automated tests:**
- `tests/test_platform.py`: Platform detection, VDF parsing, GameConfig
- `tests/test_net.py`: TCP handshake, ping/pong, UDP position, disconnect

**Manual tests:**
- `test_spawn.py`, `test_p2.py`: Interactive P2 entity testing (requires game running)

## Security Features

- Atomic file writes via temp file + `os.replace()` (inbox)
- Thread-safe shared state with locks
- Proper daemon threads with stop events
- UDP sequence numbering (drops stale packets)
- No shell=True in subprocess calls

## Development Status

**Complete:**
- Cross-platform detection (Windows/WSL2/Linux)
- DLL proxy injection (stdout redirect + library injection)
- Bridge IPC (stdout watcher + inbox writer)
- TCP/UDP networking layer
- Lua heartbeat + inbox + message dispatch
- P2 entity spawn + basic movement/combat

**WIP / Not Started:**
- Enemy AI retargeting to P2
- State synchronization (encounters, boons)
- Boon selection for two players
- Death/revive handling
- Connection lobby UI
- Encounter scaling for co-op

## Known Issues / Technical Debt

1. No requirements.txt (uses stdlib only, but build deps aren't listed)
2. No CI/CD pipeline yet
3. P2 entity uses TrainingMeleeSummon (placeholder, not a proper hero)
4. StyxScribe throughput unvalidated on Proton

---

## Review Status

> **Last Full Review:** 2026-03-18
> **Status:** WIP — Foundation complete, gameplay integration pending

### Code Quality
- [x] Platform detection tested
- [x] Networking layer tested
- [x] Atomic file I/O
- [x] Thread-safe state management
- [x] Daemon threads with proper shutdown

## Intentional Design Decisions

| Decision | Rationale |
|----------|-----------|
| DLL proxy (not StyxScribe) | StyxScribe requires ModImporter setup; proxy works without dependencies |
| File-based IPC (not pipes) | More reliable across Wine/Proton boundary |
| Dual-instance architecture | Each player controls local hero with zero input lag |
| Python bridge (not C++) | Faster iteration; networking and IPC don't need native speed |
| UDP for positions | 20Hz position updates can tolerate packet loss |

## Won't Fix (Accepted Limitations)

| Issue | Reason |
|-------|--------|
| No macOS support | Hades on macOS doesn't support mods |
| File IPC latency (~50ms) | Acceptable for game state sync; position uses UDP directly |
| No encryption on network | LAN/friend use only; not a public server |

**DO NOT further optimize:** Focus on gameplay integration (Phase 1-2), not infrastructure. The bridge and networking layers are solid.
