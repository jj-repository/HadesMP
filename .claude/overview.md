# Overview

v0.1.0 WIP — Multiplayer co-op mod for Hades. Each player controls local hero (zero input lag), state synced via Python bridge + TCP/UDP.

## Files
**C (DLL Proxies):** `lua52_proxy.c`, `version_proxy.c`, `stdout_redirect.c`, `lua52.def`
**Python:** `hadesmp_bridge.py` (713L), `hadesmp_net.py` (456L), `hadesmp_platform.py` (247L), `build.py` (220L), `deploy_mod.py` (95L)
**Lua:** `lua/HadesMP.lua` (P1, 333L), `lua/HadesMPP2.lua` (P2 entity)
**Tests:** `tests/test_platform.py`, `tests/test_net.py`; manual: `test_spawn.py`, `test_p2.py`
**Docs:** `CONTEXT.md` (index), `MULTIPLAYER-MOD.md` (phases 0-3), `CORE-SYSTEMS.md`, `ENGINE-AND-FORMATS.md`, `ENEMIES-AI-ENCOUNTERS.md`, `GAME-DATA-REFERENCE.md`, `NPCS-QUESTS-PROGRESSION.md`, `UI-PRESENTATION-DEBUG.md`, `MODDING-GUIDE.md`

## Status
**Complete:** cross-platform detection, DLL proxy injection, bridge IPC, TCP/UDP networking, Lua heartbeat/inbox/dispatch, P2 spawn+movement/combat
**WIP/Not Started:** enemy AI retargeting to P2, state sync (encounters/boons), boon selection for 2 players, death/revive, lobby UI, encounter scaling
