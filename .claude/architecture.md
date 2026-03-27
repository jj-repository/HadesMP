# Architecture

## Data Flow
```
Game (Hades.exe)
  ↕ DLL proxy (lua52.dll / VERSION.dll)
  ↕ stdout → hades_lua_stdout.log  (HADESMP: prefixed lines)
  ↕ stdin  ← hadesmp_inbox.lua     (Python writes Lua commands)
Python Bridge (hadesmp_bridge.py)
  ↕ TCP (reliable: events, transitions, handshake)
  ↕ UDP (fast: position sync 20Hz)
Remote Bridge ↔ Remote Game
```

## Components

**DLL Proxies (C)**
- `lua52_proxy.c`: intercepts `luaopen_debug`, redirects stdout → log, injects io/os/package
- `version_proxy.c`: VERSION.dll proxy, UCRT stdout redirect

**Bridge (Python)**
- `StdoutWatcher`: tail-follows log for `HADESMP:` messages
- `InboxWriter`: atomic writes to `hadesmp_inbox.lua` (Lua dofile source)
- `HadesMPBridge`: heartbeat tracking, P2 state, CLI interface

**Networking (Python)**
- TCP: handshake, game events, room transitions, boon picks
- UDP: position sync 20Hz, sequence-numbered, drops out-of-order

**Lua Mods**
- `HadesMP.lua`: heartbeat loop, inbox polling, message dispatch, P1 position
- `HadesMPP2.lua`: P2 spawn, movement, combat, animation
