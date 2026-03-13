# Hades Modding Context

Comprehensive reference for modding Hades (2020, Supergiant Games). This directory contains everything needed to understand, modify, and extend the game.

## Game Install Path
```
/mnt/ext4gamedrive/SteamLibrary/steamapps/common/Hades/
```

## Reference Files

| File | Contents |
|------|----------|
| [MODDING-GUIDE.md](MODDING-GUIDE.md) | How to set up modding, tools, ModImporter, ModUtil, mod structure, SJSON editing, community resources |
| [ENGINE-AND-FORMATS.md](ENGINE-AND-FORMATS.md) | AQUARIUS engine details, SJSON syntax, map format, pkg/sga archives, localization format, animation data |
| [CORE-SYSTEMS.md](CORE-SYSTEMS.md) | Threading/coroutines, event system, damage calculation, run management, room management, game state |
| [ENEMIES-AI-ENCOUNTERS.md](ENEMIES-AI-ENCOUNTERS.md) | All enemy types with stats, AI behaviors, encounter generation, boss mechanics, elite system |
| [NPCS-QUESTS-PROGRESSION.md](NPCS-QUESTS-PROGRESSION.md) | NPC definitions, dialogue system, quests, death loop, Mirror of Night, Pact of Punishment, gifts/keepsakes |
| [UI-PRESENTATION-DEBUG.md](UI-PRESENTATION-DEBUG.md) | Screen system, UI components, animation/tweens, HUD, boon selection, shops, debug commands |
| [GAME-DATA-REFERENCE.md](GAME-DATA-REFERENCE.md) | Weapons, traits/boons, god pools, duo/legendary boons, consumables, fishing, achievements, stores |

## Quick Reference

### Directory Layout (~12 GB)
```
Hades/
├── Content/
│   ├── Scripts/           # 97 Lua files, 302K+ lines — ALL game logic
│   ├── Game/
│   │   ├── Animations/    # SJSON animation definitions + .sga frame data
│   │   ├── GUI/           # UI layout SJSON
│   │   ├── Units/         # Player/Enemy/NPC unit SJSON
│   │   ├── Weapons/       # Weapon/projectile SJSON
│   │   ├── Projectiles/   # Projectile SJSON
│   │   ├── Obstacles/     # Environmental objects SJSON
│   │   └── Text/          # Localization (12 languages)
│   ├── Maps/              # 144 .map_text room layouts
│   ├── Audio/             # FMOD audio banks
│   ├── Movies/            # Bink video (.bik)
│   ├── Win/Packages/      # 130+ .pkg asset archives
│   └── Mods/              # Where mods go (create this)
├── x64/                   # D3D11 engine binaries
└── x64Vk/                 # Vulkan engine binaries (AQUARIUS/)
```

### Engine: AQUARIUS (Proprietary)
- **Scripting**: Lua 5.2 (runtime interpreted, not compiled)
- **Audio**: FMOD Studio
- **Rendering**: D3D11 + Vulkan backends
- **Input**: SDL2
- **Data**: Custom SJSON format

### What's Easily Moddable (plaintext)
- **Lua scripts** (.lua) — game logic, data tables, UI, AI, combat
- **SJSON files** (.sjson) — units, weapons, projectiles, animations, GUI, obstacles
- **Map files** (.map_text) — room layouts (JSON format)
- **Localization** (.sjson, .csv) — all game text in 12 languages
- **Shaders** (.vert, .frag) — GLSL vertex/fragment shaders

### What Needs Tools (binary)
- `.pkg` — texture/sprite archives (use **Deppth** to extract)
- `.sga` — animation frame data
- `.bank`/`.fsb` — FMOD audio (use **Audio Manager**)
- `.bik` — Bink video
- `.xnb` — compiled fonts

### Key Lua Files (by size/importance)

| File | Lines | Purpose |
|------|-------|---------|
| NPCData.lua | 49,227 | All NPC definitions, dialogue trees, interaction events |
| TraitData.lua | 43,276 | All boon/trait definitions, effects, scaling |
| EnemyData.lua | 27,653 | All enemy stats, behaviors, spawn data |
| LootData.lua | 20,973 | God boon pools, upgrade offerings |
| WeaponData.lua | 17,179 | Weapon stats, projectile data |
| AudioData.lua | 10,446 | Sound effect and music definitions |
| DeathLoopData.lua | 10,070 | House of Hades hub, between-run events |
| HeroData.lua | 8,933 | Zagreus base stats and abilities |
| RoomPresentation.lua | 6,719 | Room transition visuals and audio |
| RoomManager.lua | 6,016 | Room generation, script import hub |
| EncounterData.lua | 5,938 | Combat encounter definitions |
| ConditionalItemData.lua | 5,861 | House Contractor cosmetics |
| RunManager.lua | 5,682 | Run init, hero creation, game state |
| EnemyAI.lua | 4,618 | Enemy behavior trees and AI logic |
| Combat.lua | 3,885 | Damage calculation, healing, modifiers |
| Main.lua | ~600 | Threading, coroutines, event system |

### Script Load Order
`RoomManager.lua` is the import hub. It imports everything via `Import` statements:
```
RoomManager.lua → Combat.lua, RunManager.lua, UIScripts.lua, EnemyAI.lua,
                   TraitData.lua, WeaponData.lua, EnemyData.lua, etc.
```
Mods inject via `Import "../Mods/ModName/ModFile.lua"` appended to RoomManager.lua or Main.lua.

### Data Architecture Pattern
All game data uses Lua tables with inheritance:
```lua
EnemyData.HeavyMeleeElite = {
    InheritFrom = { "Elite", "HeavyMelee" },
    MaxHealth = 195,
    HealthBuffer = 50,
    -- overrides merge with inherited properties
}
```

### Currencies (progression ladder)
Darkness → Gems → Chthonic Keys → Nectar → Diamonds → Titan Blood → Ambrosia
