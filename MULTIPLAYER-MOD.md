# Hades Real-Time Co-op Mod — Project Plan

## Goal: Two players fighting in the same room, over the network. Can it be done?

**Last updated**: 2026-02-28

---

## Table of Contents

1. [The Challenge](#the-challenge)
2. [Prior Art — What Others Have Tried](#prior-art)
3. [Architecture](#architecture)
4. [StyxScribe Reference](#styxscribe-reference)
5. [Development Phases](#development-phases)
6. [Key Files & Hook Points](#key-files--hook-points)
7. [State Sync Protocol](#state-sync-protocol)
8. [The Hard Problems](#the-hard-problems)
9. [Setup Guide](#setup-guide)
10. [Project Layout](#project-layout)
11. [Open Questions](#open-questions)
12. [Reference Links](#reference-links)

---

## The Challenge

Hades runs on the AQUARIUS engine — proprietary, closed-source C++, 100% single-player. There is:

- **No networking** in the engine. No sockets, no netcode, no state sync.
- **No second player concept**. One hero (`CurrentRun.Hero`), one camera, one input handler.
- **Sandboxed Lua 5.2**. No `require("socket")`, no OS access, no FFI.
- **Single-threaded coroutines**. One thread of execution, cooperative multitasking.
- **Every AI targets one hero**. `AttackerAI`, `SurroundAI`, `LeapIntoRangeAI` — all hardcoded to path toward `CurrentRun.Hero`.
- **Boon selection freezes the game**. `OpenUpgradeChoiceMenu()` → `FreezePlayerUnit()` → all simulation stops.
- **The only bridge to the outside world**: StyxScribe (stdin/stdout pipe between the game and an external Python process).

Nobody in the 10k+ member Hades modding Discord has shipped real-time networked co-op. Two C++ DLL injection projects attempted it and stalled. One Lua project (Polycosmos/Archipelago) proved StyxScribe networking works, but only for low-frequency event messages, not real-time state sync.

**This might not work.** The plan is structured to find out as fast as possible where the walls are.

---

## Prior Art

### Polycosmos / Archipelago — **SHIPPED, StyxScribe networking proven**
- [github.com/NaixGames/Polycosmos](https://github.com/NaixGames/Polycosmos)
- StyxScribe + Python client → Archipelago multiworld server. Works over the internet.
- **Key finding**: `StyxScribeShared.Root` is too slow for runtime — causes crashes on HDDs. Use `StyxScribe.Send()` string messages only.
- Only does event-driven messages (boon grants, location checks). Untested at high frequency.

### SystematicSkid/HadesMP — **C++ DLL injection, stalled**
- [github.com/SystematicSkid/HadesMP](https://github.com/SystematicSkid/HadesMP)
- Reverse-engineered engine classes: `PlayerUnit`, `Camera`, `World`, `UnitManager`, `InputHandler`, `Weapon`
- Has network client/server stubs (ENet-based). Hooks DirectX for custom rendering.
- Windows-only. Last meaningful progress: 2022-ish. README still says "usage to be updated."
- **Useful**: The reversed class layouts tell us what the engine tracks internally.

### HadesMP/hades-mp — **C++ DLL loader + Lua networking, WIP**
- [github.com/HadesMP/hades-mp](https://github.com/HadesMP/hades-mp)
- Hooks `ScriptManager::Load` to inject custom scripts. Bypasses content folder integrity checks.
- Exposes `SubscribeMessage()` / `SendCustomPayload()` to Lua. C++ ASIO handles TCP/UDP.
- Packet format can serialize arbitrary `lua_State*` — full Lua tables over the wire.
- **319 engine action IDs mapped** (`SpawnUnit`, `Move`, `Teleport`, `FireWeaponFromUnit`, `SetAnimation`, `AdjustZoom`, etc.)
- Windows-only. Networking code exists but game-side scripts are TODO stubs.

### Nexus Co-op Mod (#215) — **Local co-op works**
- [nexusmods.com/hades/mods/215](https://www.nexusmods.com/hades/mods/215)
- Two controllers, two heroes, same machine. Works with Steam Remote Play.
- **Proves two hero units can exist in the engine without crashing.** This is critical — the engine doesn't blow up with a second PlayerUnit.

### What we take from this

| Source | What it tells us |
|--------|-----------------|
| Polycosmos | StyxScribe works for networking. Use string messages, not SharedState. |
| SystematicSkid | Engine internals are partially mapped. PlayerUnit memory layout is known. |
| hades-mp | 319 engine actions available from Lua. Content verification is bypassable. |
| Nexus Co-op | **Two heroes can coexist.** The engine handles it. |

---

## Architecture

### Why StyxScribe (not DLL injection)

We're on Linux/Proton. DLL injection is a non-starter without deep Wine hacking. StyxScribe works through stdin/stdout pipes which should work under Wine. If it doesn't, fallback is running Python natively on Linux and bridging to the Wine process via a local TCP socket.

If StyxScribe throughput becomes a bottleneck for real-time sync (which it might), the escape hatch is a small helper DLL that adds `luasocket` to the Lua environment — but we cross that bridge when we hit it.

### The Model

Both players run their own Hades instance. **Host-authoritative**: the host runs the real game with both heroes. The client sends inputs, receives state, and renders a mirror.

```
HOST                                          CLIENT
┌──────────┐  stdout  ┌──────────┐            ┌──────────┐  stdout  ┌──────────┐
│  Hades   │─────────►│  Python  │◄──TCP/UDP─►│  Python  │─────────►│  Hades   │
│  + Mod   │◄─────────│  Relay   │            │  Relay   │◄─────────│  + Mod   │
└──────────┘  stdin   └──────────┘            └──────────┘  stdin   └──────────┘
     │                                                                    │
     ├─ Runs both heroes (P1 via input, P2 via network commands)         │
     ├─ Runs all AI, combat, encounters                                  │
     ├─ Sends state snapshots (positions, HP, anims, enemies)            │
     └─ Receives P2 input commands                                       │
                                                                          │
                                              ├─ Sends local inputs to host
                                              ├─ Receives state, renders mirror
                                              ├─ P2 hero is real (local gameplay)
                                              └─ P1 hero is a synced ghost
```

**Why host-authoritative**: avoids desync entirely. All game logic (damage calc, AI, encounters, boons) runs on the host. Client is a "smart puppet" — plays their own game locally for responsiveness, but host is the source of truth for shared state (enemies, room progression, boons).

**The big design question**: Does each player play in their own game instance with results synced, or does only the host run the "real" game?

**Option A: Dual-instance (each plays locally, sync results)**
- Both games run independently. Each player controls their local hero normally.
- State that needs syncing: enemy health/death, room clear status, boon selections, damage dealt.
- Pro: both players have responsive controls (no input lag for P2).
- Con: desync risk is massive — two independent combat simulations diverging.

**Option B: Host-authoritative (host runs everything, client is a puppet)**
- Host game has two hero units. P1 is the real player, P2 is driven by network inputs.
- Client sends raw inputs (move direction, attack, dash). Host applies them to P2's unit.
- Client receives P2's state back and mirrors it locally for visual feedback.
- Pro: no desync possible. One simulation, one truth.
- Con: P2 has input latency (network round-trip + StyxScribe polling). Minimum ~30-80ms.

**Decision: Start with Option A (dual-instance), fall back to Option B if desync is unmanageable.**

Option A is simpler to build first — each game just needs to sync enemy kills, room clear, and boon picks. Combat runs locally with full responsiveness. If enemies desync badly, we switch to Option B.

---

## StyxScribe Reference

### How it works
`SubsumeHades.py` launches Hades as a subprocess. Captures stdout (instant), feeds stdin (polled by game loop).

### Latency
| Direction | Latency |
|-----------|---------|
| Game → Python (stdout) | ~0ms |
| Python → Game (stdin poll) | ~16ms at 60fps |
| Round-trip | ~16-32ms |

### API

```lua
-- Lua: send to Python
StyxScribe.Send("HadesMP:some data")

-- Lua: receive from Python
StyxScribe.AddHook(function(message)
    -- message has prefix stripped
end, "HadesMP:prefix:", MyMod)
```

```python
# Python: send to game
Scribe.Send("HadesMP:prefix:some data")

# Python: receive from game
def callback(message):
    pass
Scribe.AddHook(callback, "HadesMP:", "ModuleName")
```

### Rules
- **DO NOT** use `StyxScribeShared.Root` at runtime. It's broken. String messages only.
- All messages are line-based text. Use JSON for structured data.
- Messages are sequential, no parallelism.
- Must launch via `SubsumeHades.py`, not Steam directly.

---

## Development Phases

### Phase 0: Does the bridge work? (Days)

**The single most important question: does StyxScribe work on Linux/Proton?**

Everything else is moot if it doesn't.

- [ ] **0.1** Install modding stack:
  - ModImporter → `Content/modimporter.py`
  - ModUtil → `Content/Mods/ModUtil/`
  - StyxScribe → `Content/Mods/StyxScribe/` (Lua) + Python component
- [ ] **0.2** Minimal test mod — send heartbeat from Lua, receive in Python, send pong back:
  ```lua
  ModUtil.Mod.Register("HadesMP")
  StyxScribe.AddHook(function(msg)
      print("HadesMP: got pong: " .. msg)
  end, "HadesMP:pong:", HadesMP)
  OnAnyLoad{ function()
      thread(function()
          while true do
              StyxScribe.Send("HadesMP:ping:" .. tostring(GetTime({}) or 0))
              wait(1.0)
          end
      end)
  end }
  ```
  ```python
  import Scribe, time
  def on_ping(msg):
      Scribe.Send("HadesMP:pong:" + str(time.time()))
  def Load():
      Scribe.AddHook(on_ping, "HadesMP:ping:", "HadesMPTest")
  ```
- [ ] **0.3** Launch through Proton. Does it work? Do messages flow?
- [ ] **0.4** Stress test: crank to 20Hz, 50Hz, 100Hz. Where does it break?
- [ ] **0.5** Also test: can we `SpawnUnit()` a second hero-type entity without crashing?

**If StyxScribe doesn't work on Proton**: try running Python natively on Linux and connecting to the Wine process via a localhost TCP socket. The Lua side would need a coroutine polling a file or using a different IPC mechanism.

**Exit criteria**: bidirectional messages work, we know the throughput ceiling, we know if a second hero entity can exist.

---

### Phase 1: Two heroes in one room (1-2 weeks)

**Goal**: Player 1 plays normally. A second hero entity exists in the same room, controllable via Lua commands.

This is the local foundation — no networking yet. Just proving the engine can handle two heroes.

- [ ] **1.1** Spawn a second hero unit when a room loads:
  ```lua
  -- Try spawning a second PlayerUnit or a suitable substitute
  local p2Id = SpawnUnit({
      Name = "PlayerUnit",  -- or "NPC_Cerberus_01" as a safe test first
      Group = "Standing",
      DestinationId = CurrentRun.Hero.ObjectId,
      OffsetX = 100, OffsetY = 0
  })
  ```
  If `PlayerUnit` doesn't work, try spawning an NPC or enemy unit with Zagreus animations.

- [ ] **1.2** Control P2 via debug input or coroutine:
  - Move P2 around with `Move({ Id = p2Id, ... })` or `Teleport()`
  - Play animations with `SetAnimation({ Name = "ZagreusRun", DestinationId = p2Id })`
  - Fire weapons with `FireWeaponFromUnit({ Id = p2Id, ... })`

- [ ] **1.3** Test what works and what doesn't:
  - Does P2 have collision with enemies?
  - Does P2 take damage from enemies/traps?
  - Can P2 deal damage to enemies?
  - Does the camera freak out?
  - Does `AdjustZoom()` let us zoom out enough for both?
  - Does enemy AI notice P2 at all?

- [ ] **1.4** Hook enemy AI to sometimes target P2:
  ```lua
  -- Wrap AI target acquisition to randomly pick P1 or P2
  ModUtil.WrapBaseFunction("GetClosestUnitOfType", function(base, args)
      -- intercept and sometimes return P2's id instead
      ...
  end, HadesMP)
  ```

- [ ] **1.5** Handle P2 health/death:
  - Give P2 a health pool (or mirror P2's local game state)
  - What happens when P2 "dies"? Respawn? Run continues with P1 only?

- [ ] **1.6** Handle boon selection with two players:
  - When boon menu opens, both players need to pick (or one picks for both)
  - Test: can we call `OpenUpgradeChoiceMenu()` without `FreezePlayerUnit()`? Or wrap freeze to be a no-op?

- [ ] **1.7** Scale encounters:
  - Modify enemy spawn count/HP for two players
  - Hook the difficulty budget calculation in the encounter system

**This phase answers the biggest unknowns**: can a second hero exist with meaningful gameplay interaction, or is it just a cosmetic puppet?

---

### Phase 2: Network two instances (1-2 weeks)

**Goal**: Two Hades instances, two machines, connected over TCP/UDP. State flows between them.

- [ ] **2.1** Python networking module:
  - TCP for reliable messages (room transitions, boon picks, events)
  - UDP for high-frequency state (positions, animations) — with sequence numbers
  - Connection: host listens on port 26000, client connects to IP:port

- [ ] **2.2** Define what syncs and how often:

  | Data | Direction | Frequency | Transport |
  |------|-----------|-----------|-----------|
  | P2 position + angle + animation | Client → Host | 20Hz | UDP |
  | P1 position + angle + animation | Host → Client | 20Hz | UDP |
  | All enemy positions + HP + anims | Host → Client | 10Hz | UDP |
  | Damage events | Host → Client | On event | TCP |
  | Enemy kills | Bidirectional | On event | TCP |
  | Room transitions | Host → Client | On event | TCP |
  | Boon selections | Bidirectional | On event | TCP |
  | Room clear / encounter state | Host → Client | On event | TCP |
  | Hero HP / resources | Bidirectional | On change | TCP |

- [ ] **2.3** Lua side: emit local hero state at 20Hz via StyxScribe → Python → network
- [ ] **2.4** Lua side: receive remote hero state, apply to ghost/puppet entity
- [ ] **2.5** Position interpolation on the receiving side (lerp between snapshots)
- [ ] **2.6** Test on localhost (two instances, one machine) first
- [ ] **2.7** Test over LAN
- [ ] **2.8** Test over internet (port forwarding, measure latency impact)

**Network message format** (between Python relays):
```
[4 bytes: length][1 byte: type][N bytes: msgpack payload]

Types:
  0x01 = Position update (hero pos/angle/anim)
  0x02 = Enemy state batch (all enemy pos/hp/anim)
  0x03 = Game event (damage, kill, room clear, etc.)
  0x04 = Room transition
  0x05 = Boon selection
  0x06 = Input command (for host-auth mode)
  0x07 = Ping/Pong
  0x08 = Handshake
  0x09 = Full state sync (room boundary)
```

---

### Phase 3: Full co-op experience (Weeks-months)

**Goal**: It actually feels like co-op. Both players contribute, encounters are balanced, progression works.

- [ ] **3.1** Shared progression:
  - Shared money pool
  - Boon selection: each player picks from their own offered boons? Or shared pool?
  - Health: independent pools synced, or shared?
  - Death Defiances: independent

- [ ] **3.2** Room transitions:
  - Both players must reach the door / both must be "ready"
  - Door selection: host picks? Vote? P1 picks odd rooms, P2 picks even?

- [ ] **3.3** Death handling:
  - One player dies: other can revive? Timer before auto-revive? Or run ends?
  - Both die: normal death loop for both

- [ ] **3.4** Camera:
  - Zoom out to fit both players (test `AdjustZoom` range)
  - Or: each player's camera follows their own hero (separate camera per instance — naturally works in dual-instance model)

- [ ] **3.5** Polish:
  - P2 hero visual indicator (outline, color tint, name tag)
  - Network latency display
  - Disconnect handling (pause? AI takes over P2? Run continues solo?)
  - Connection lobby UI (simple: host displays code, client enters code)

---

## Key Files & Hook Points

### Lua Scripts (`Content/Scripts/`)

| File | What to hook | Why |
|------|-------------|-----|
| **Combat.lua** (154KB) | `Damage()`, `Heal()`, `Kill()`, `DamageHero()` | Sync damage/kills between instances |
| **EnemyAI.lua** (182KB) | AI target selection functions | Make enemies target P2 sometimes |
| **RoomManager.lua** (229KB) | `OnAnyLoad`, `LeaveRoom()`, room lifecycle | Spawn P2 on room load, sync transitions |
| **RunManager.lua** (194KB) | `StartNewRun()`, `StartRoom()`, `EndRun()` | Sync run start/end, room entry |
| **UpgradeChoice.lua** | `OpenUpgradeChoiceMenu()`, `HandleUpgradeChoiceSelection()` | Co-op boon picking |
| **Main.lua** | `wait()`, coroutine primitives | Threading for network polling |
| **HeroControl.lua** | Movement, dash, input | Driving P2's movement from network |
| **DeathLoop.lua** | `KillHero()`, `HandleDeath()` | Multiplayer death handling |
| **CombatPresentation.lua** | Hit animations, VFX | Sync visual feedback |

### Engine Functions Available from Lua (most relevant)

```
-- Entity queries
GetLocation({ Id })          -- XY position
GetAngle({ Id })             -- facing angle
GetVelocity({ Id })          -- velocity vector
IsAlive({ Id })              -- alive check
GetClosest({ Id, DestinationName })

-- Entity control
SpawnUnit({ Name, Group, DestinationId, OffsetX, OffsetY })
Move({ Id, DestinationId/Angle/Distance })
Teleport({ Id, DestinationId, OffsetX, OffsetY })
SetAnimation({ Name, DestinationId })
SetAngle({ Id, Angle })

-- Combat
FireWeaponFromUnit({ Id, WeaponName, ... })
CreateProjectileFromUnit({ Id, WeaponName, ... })
ApplyEffectFromWeapon({ Id, ... })
SetInvulnerable({ Id })
SetVulnerable({ Id })

-- Camera
PanCamera({ Ids, Duration })
FocusCamera({ FocusIds })
AdjustZoom({ Fraction, LerpTime })
LockCamera({ Id })
UnlockCamera()

-- Misc
AddInputBlock({ Name })
RemoveInputBlock({ Name })
AdjustSimulationSpeed({ Fraction })
```

### Key State Objects

| Object | What | Scope |
|--------|------|-------|
| `CurrentRun` | Run state (hero, traits, money, rooms, encounters) | Per-run |
| `CurrentRun.Hero` | Hero entity (ObjectId, Health, MaxHealth, Weapons) | Per-run |
| `CurrentRun.Hero.ObjectId` | Engine entity ID for position/animation queries | Per-run |
| `GameState` | Persistent save data | Persistent |
| `MapState` | Current room entities and state | Per-room |

---

## State Sync Protocol

### StyxScribe Message Format

All messages: `HadesMP:<type>:<payload>`

```
HadesMP:pos:<x>,<y>,<a>,<anim>        -- Position update (compact, 20Hz)
HadesMP:hp:<current>,<max>             -- Health update (on change)
HadesMP:ev:<json>                      -- Game event
HadesMP:room:<roomName>                -- Room transition
HadesMP:boon:<json>                    -- Boon selection
HadesMP:enemy:<json>                   -- Enemy state batch
HadesMP:ping:<timestamp>               -- Latency measurement
HadesMP:meta:<json>                    -- Handshake/config
```

Position updates are kept as compact CSV (not JSON) to minimize serialization overhead at 20Hz.

### Enemy Sync (the hard part)

Enemies are the trickiest sync target. In dual-instance mode:
- Both games spawn their own enemies (from the same room seed)
- Enemies need to have consistent IDs across instances
- When P1 kills an enemy, P2's copy needs to die too
- If enemy positions drift (different AI decisions due to two heroes), they need correction

Approach: **deterministic enemy spawning + kill sync + periodic position correction**
- Both instances generate the same enemies (same room, same seed)
- Enemy damage/kills are synced as events
- Every ~2 seconds, host sends authoritative enemy positions → client corrects

### Boon Sync

When boon selection triggers:
- Host sends the offered boons to client
- Both players pick from the same set (or: each player gets their own set)
- Selections are sent to both instances and applied

---

## The Hard Problems

### 1. StyxScribe throughput for real-time (UNKNOWN — Phase 0 answers this)
We need ~20 position updates/sec + enemy state at 10Hz + events. That's maybe 40-60 messages/sec sustained. Polycosmos only tested single-digit msgs/sec. If the pipe can't handle it, options:
- Reduce frequency (10Hz positions, 5Hz enemies)
- Batch messages (one big message per frame instead of many small ones)
- Switch to binary encoding (msgpack vs JSON)
- Nuclear option: add a UDP socket via DLL

### 2. StyxScribe on Proton (UNKNOWN — Phase 0 answers this)
stdin/stdout pipes through Wine. Should work in theory (Wine supports standard I/O), but subprocess spawning from Python → Wine executable might have quirks. If broken, fallback: native Python on Linux, connect to Wine process via localhost TCP.

### 3. Second hero entity (UNKNOWN — Phase 1 answers this)
Nexus co-op mod proves it's possible locally. But we need the spawned unit to:
- Take and deal damage
- Have weapon functionality
- Respond to `Move()` / `Teleport()` smoothly
- Not break the camera or encounter system

If `SpawnUnit("PlayerUnit")` doesn't give us a functional second hero, alternatives:
- Spawn an NPC with Zagreus animations
- Spawn an enemy and switch its allegiance (`SwitchAllegiance()` exists in the engine actions!)
- Use a completely different unit type as a proxy

### 4. Enemy AI retargeting (Phase 1 tests)
All AI paths toward `CurrentRun.Hero`. Need to wrap target selection to sometimes choose P2.

The risk: AI pathfinding is engine-level C++. Lua controls which target the AI chooses, but the actual pathfinding algorithm runs in C++. If the engine only pathfinds toward entities it considers "targets" (and only `CurrentRun.Hero` qualifies), wrapping the Lua side won't help.

Test: set an enemy's target to P2's spawned unit via Lua. Does the enemy actually move toward it?

### 5. Enemy desync in dual-instance mode
If both instances run their own AI independently, enemies will diverge within seconds (different positions, different attack timings, different targets). Solutions:
- **Accept visual desync, sync kills only** — enemies look different on each screen, but when one dies, it dies on both. Simplest. Might look janky.
- **Host-authoritative enemies** — only host runs enemy AI, client receives positions. Requires high-frequency enemy state sync. ~20-50 enemies × 10Hz = 200-500 msgs/sec. Might kill StyxScribe.
- **Periodic corrections** — both run AI locally, host sends corrections every 2s. Enemies "snap" to correct positions. Compromise between bandwidth and accuracy.

### 6. Boon selection freeze
`OpenUpgradeChoiceMenu()` freezes ALL simulation. In co-op, P2 is frozen too.

Options:
- **Accept it**: when boons appear, both players pause. One picks (or both pick via network relay). It's a natural pause point.
- **Wrap FreezePlayerUnit as no-op**: risky — the freeze might be load-bearing (prevents race conditions during menu).
- **Separate boon events per player**: each player gets their own boon offers at different times. Avoids the freeze conflict.

Best approach: **accept the freeze**. Boon selection is inherently a pause moment. Both players see the menu, one (or both) picks.

### 7. Input latency for P2 (host-authoritative model only)
If we go host-auth: P2's inputs travel: P2 keyboard → P2 Lua → P2 StyxScribe → P2 Python → network → Host Python → Host StyxScribe → Host Lua → apply. That's ~50-150ms minimum. For an action game, that's rough.

Mitigation: **client-side prediction**. P2 moves their local hero immediately. Host processes the input and sends authoritative state back. If prediction was wrong, correct with interpolation. Standard netcode technique, but tricky to implement in Lua.

In dual-instance mode, this problem doesn't exist — each player controls their own local hero with zero input lag.

### 8. Camera with two heroes
Each player's game instance naturally follows their own hero — **this is already solved in dual-instance mode**. Each player sees their own perspective. The only issue is: you can't see where your co-op partner is unless they're nearby.

Solution: minimap dot or off-screen indicator for partner's position.

---

## Setup Guide

### Required

| Tool | Source | Purpose |
|------|--------|---------|
| ModImporter | [SGG-Modding/ModImporter](https://github.com/SGG-Modding/ModImporter) | Patches Lua import chain |
| ModUtil | [SGG-Modding/ModUtil](https://github.com/SGG-Modding/ModUtil) | Function hooking |
| StyxScribe | [SGG-Modding/StyxScribe](https://github.com/SGG-Modding/StyxScribe) | Lua ↔ Python bridge |
| Python 3.8+ | System | Runs StyxScribe + relay |
| dkjson.lua | [dkolf.de/dkjson](http://dkolf.de/src/dkjson-lua.fsl/home) | JSON in Lua |

### Install

```bash
HADES="/mnt/ext4gamedrive/SteamLibrary/steamapps/common/Hades"

cd "$HADES/Content"

# ModImporter
wget https://raw.githubusercontent.com/SGG-Modding/ModImporter/main/modimporter.py

# ModUtil
mkdir -p Mods && cd Mods
git clone https://github.com/SGG-Modding/ModUtil.git

# StyxScribe — exact layout TBD in Phase 0
git clone https://github.com/SGG-Modding/StyxScribe.git

# Our mod
mkdir -p HadesMP

# Patch import chain
cd "$HADES/Content"
python3 modimporter.py
```

Game uses `x64Vk/` on Linux/Proton. StyxScribe's `lua52.dll` replacement (if needed) goes there, not in `x64/`.

---

## Project Layout

### Development (our code)

```
/mnt/ext4gamedrive/modding/Hades/
├── *.md                         # Reference docs (8 files)
├── MULTIPLAYER-MOD.md           # This plan
└── mod/                         # Our mod (git repo)
    ├── lua/
    │   ├── HadesMP.lua          # Entry point, lifecycle, config
    │   ├── HadesMPNet.lua       # StyxScribe messaging layer
    │   ├── HadesMPHero.lua      # Second hero spawn/control
    │   ├── HadesMPSync.lua      # State sync (enemies, events, boons)
    │   └── dkjson.lua           # JSON lib
    ├── python/
    │   ├── HadesMPRelay.py      # StyxScribe plugin + network relay
    │   └── network.py           # TCP/UDP transport
    ├── modfile.txt
    └── tools/
        ├── install.sh           # Symlink mod into game dir
        └── launch.sh            # Launch via StyxScribe/Proton
```

### Game directory (after setup)

```
Hades/Content/
├── modimporter.py
├── Scripts/                # Untouched vanilla
├── Mods/
│   ├── ModUtil/
│   ├── StyxScribe/         # Lua component
│   └── HadesMP/ → symlink to mod/lua/
└── StyxScribe/             # Python component
    └── Plugins/
        └── HadesMPRelay.py → symlink to mod/python/HadesMPRelay.py
```

---

## Open Questions

Ordered by "blocks everything if unanswered":

1. **Does StyxScribe work on Proton?** — Phase 0, day 1. If no: need alternative IPC.
2. **What is StyxScribe's throughput ceiling?** — Phase 0. Need 40-60 msgs/sec minimum.
3. **Can we spawn a functional second hero?** — Phase 1. `SpawnUnit("PlayerUnit")` — crash? Works? Cosmetic only?
4. **Can spawned units take/deal damage?** — Phase 1. Determines if P2 is a real combatant or a ghost.
5. **Can enemy AI be retargeted from Lua?** — Phase 1. Determines if enemies engage P2.
6. **Can we run two Hades instances on one machine?** — Phase 2 testing. Steam may prevent it.
7. **How bad is enemy desync in dual-instance mode?** — Phase 2. Determines if kill-sync-only is acceptable.

---

## Reference Links

- [SGG-Modding GitHub](https://github.com/SGG-Modding) — ModImporter, ModUtil, StyxScribe
- [Polycosmos](https://github.com/NaixGames/Polycosmos) — Working StyxScribe networking
- [SystematicSkid/HadesMP](https://github.com/SystematicSkid/HadesMP) — Engine RE (C++)
- [HadesMP/hades-mp](https://github.com/HadesMP/hades-mp) — C++ loader + Lua net (WIP)
- [Nexus Co-op](https://www.nexusmods.com/hades/mods/215) — Local co-op (two heroes proven)
- [Polycosmos Tutorial](https://naixgames.github.io/tutorials/010Tutorial/) — StyxScribe integration guide
