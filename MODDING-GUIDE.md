# Hades Modding Guide

## Community Resources

| Resource | URL | Purpose |
|----------|-----|---------|
| Hades Modding Discord | discord.gg/KuMbyrN (10,756+ members) | Primary community hub |
| SGG-Modding GitHub | github.com/SGG-Modding | All official community tools |
| Nexus Mods (Hades) | nexusmods.com/hades | Mod distribution |
| Modding Tutorial Repo | github.com/micriley/HadesModding | Guides and data docs |

## Required Tools

### 1. ModImporter (Build/Install Time)
- **Repo**: github.com/SGG-Modding/ModImporter
- **Nexus**: nexusmods.com/hades/mods/26
- Python script (or standalone .exe) placed in `Content/` folder
- Patches game files on disk: injects `Import` statements into Lua, merges SJSON changes
- Must be re-run after adding/removing mods or after game updates

**How it works internally:**
1. Restores `.bak` backup files (clean slate)
2. Scans `Content/Mods/` for subdirectories with `modfile.txt`
3. Parses all modfile directives, queues operations by priority
4. Applies modifications sequentially
5. Tags modified files with timestamp marker

**Installation:**
```
Content/
├── modimporter.py          # or modimporter.exe
├── sjson/                   # SJSON Python module (optional, for SJSON edits)
└── Mods/                    # Create this directory
```

### 2. ModUtil (Runtime Lua Library)
- **Repo**: github.com/SGG-Modding/ModUtil
- **Nexus**: nexusmods.com/hades/mods/27
- Lua library loaded first at game startup
- Provides safe function hooking that allows multiple mods to coexist
- Must be installed as a mod itself (uses `Top Import`)

### 3. Deppth (Asset Extractor)
- **Repo**: github.com/quaerus/deppth
- Extracts/repacks `.pkg` archive files
- Required for texture/sprite modding

### 4. Audio Manager
- **Nexus**: nexusmods.com/hades/mods/88
- Extracts and replaces audio within FMOD `.bank` files

### 5. HadesMapper (Map Tool)
- **Repo**: github.com/SGG-Modding/HadesMapper
- Encodes/decodes binary `.map` files to/from JSON

### 6. Other Tools
- **StyxScribe** (github.com/SGG-Modding/StyxScribe) — External hook system, console I/O
- **Hades-Extender** (github.com/SGG-Modding/Hades-Extender) — Extended Lua capabilities
- **Hephaistos** (github.com/nbusseneau/hephaistos) — Ultrawide/resolution binary patcher

---

## Mod Structure

### Directory Layout
```
Content/Mods/MyMod/
├── modfile.txt              # Required: directives for ModImporter
├── MyMod.lua                # Main Lua mod code
├── WeaponChanges.sjson      # Optional: SJSON data modifications
└── Subfolder/
    └── MoreCode.lua         # Optional: additional scripts
```

### modfile.txt Directives

| Directive | Syntax | Purpose |
|-----------|--------|---------|
| `To` | `To <path1> <path2>` | Set target files for subsequent operations |
| `Priority` | `Priority <number>` | Execution order (higher = later) |
| `Import` | `Import "file.lua"` | Append Import statement to target (default: RoomManager.lua) |
| `Top Import` | `Top Import "file.lua"` | Prepend Import (loads first — used by ModUtil) |
| `Replace` | `Replace "source"` | Replace entire target file |
| `SJSON` | `SJSON "mapfile.sjson"` | Merge SJSON changes into target |
| `XML` | `XML "mapfile.xml"` | Merge XML changes |
| `CSV` | `CSV "mapfile.csv"` | Merge CSV changes |
| `Map` | `Map "mapfile.json"` | Binary map modifications |
| `Include` | `Include <path>` | Recursively load another modfile |
| `Load` | `Load Priority <num>` | Combined priority setter |

Comments: `-:` block comment start, `:-` block comment end.

### Example modfile.txt
```
-: My Cool Gameplay Mod :-

To "../Scripts/RoomManager.lua"
Import "MyCoolMod.lua"

To "../Game/Weapons/PlayerWeapons.sjson"
SJSON "WeaponChanges.sjson"

To "../Game/Text/en/HelpText.en.sjson"
SJSON "TextChanges.sjson"
```

---

## Lua Modding Patterns

### Basic Data Modification (No ModUtil needed)
Directly modify global data tables after they load:
```lua
-- MyCoolMod.lua
-- Change Zagreus max health
HeroData.DefaultHero.MaxHealth = 100

-- Make sword do more damage
WeaponData.SwordWeapon.BaseDamage = 30

-- Change enemy HP
EnemyData.HeavyMelee.MaxHealth = 200

-- Add a new trait property
TraitData.SwordBaseUpgradeTrait.PropertyChanges[1].BaseValue = 50
```

### Function Wrapping (Requires ModUtil)
Safe function interception that chains with other mods:

```lua
ModUtil.WrapBaseFunction("FunctionName", function(baseFunc, arg1, arg2, ...)
    -- Pre-execution logic (runs BEFORE the original)

    local result = baseFunc(arg1, arg2, ...)  -- Call the original

    -- Post-execution logic (runs AFTER the original)

    return result
end, YourMod)
```

**Key characteristics:**
- `baseFunc` is always the first parameter, followed by original args
- You MUST call `baseFunc(...)` yourself — omitting it skips the original
- You can modify arguments before passing them
- You can modify return values after
- Multiple mods wrapping the same function form a chain
- Third argument is your mod table for context

### Function Override (Use Sparingly)
Completely replaces a function — blocks the chain for other mods:
```lua
ModUtil.BaseOverride("SomeFunction", function(arg1, arg2)
    -- Entirely new implementation — original never called
end, YourMod)
```

### Real-World Examples

**Wrap encounter generation:**
```lua
MyMod = {}

ModUtil.WrapBaseFunction("GenerateEncounter", function(baseFunc, currentRun, room, encounter)
    local runDepth = GetRunDepth(currentRun)
    -- Modify encounter before generation
    encounter.BaseDifficulty = encounter.BaseDifficulty * 1.5
    baseFunc(currentRun, room, encounter)
end, MyMod)
```

**Wrap room start:**
```lua
ModUtil.WrapBaseFunction("StartRoom", function(baseFunc, currentRun, currentRoom)
    -- Do something before room starts
    baseFunc(currentRun, currentRoom)
    -- Do something after room starts
end, MyMod)
```

**Add a new trait/boon:**
```lua
TraitData.MyCustomTrait = {
    InheritFrom = { "ShopTier1Trait" },
    Name = "MyCustomTrait",
    Icon = "Boon_Zeus_01",
    RarityLevels = {
        Common = { Multiplier = 1.0 },
        Rare = { Multiplier = 1.5 },
        Epic = { Multiplier = 2.0 },
    },
    PropertyChanges = {
        {
            WeaponNames = WeaponSets.HeroPhysicalWeapons,
            ProjectileProperty = "DamageLow",
            ChangeType = "Multiply",
            BaseValue = 1.2,
            ChangeValue = 0.1,
        },
    },
}
```

---

## SJSON Modification Patterns

SJSON map files describe changes to apply. Special prefix keys act as operations:

| Operation | Behavior |
|-----------|----------|
| `_append` | Add elements to an existing list |
| `_replace` | Wholesale replace a node |
| `_delete` | Remove an entry entirely |
| `_search` | Find elements by predicate and modify them |
| `_sequence` | Treat dict keys as numeric indices (convert to array) |

### Example: Modify a weapon in SJSON
```sjson
{
    Weapons = [
        {
            Name = "SwordWeapon"
            _replace = true
            Damage = 30
        }
    ]
}
```

### Example: Add a new weapon entry
```sjson
{
    Weapons = {
        _append = [
            {
                Name = "MyNewWeapon"
                InheritFrom = "SwordWeapon"
                Damage = 50
            }
        ]
    }
}
```

---

## File Loading Order

1. Engine loads `RoomManager.lua` first
2. `RoomManager.lua` imports all other scripts via `Import` statements (see CORE-SYSTEMS.md)
3. Data definition scripts execute, populating global tables: `HeroData`, `TraitData`, `WeaponData`, `EnemyData`, `LootData`, etc.
4. ModImporter-injected `Import` lines at the end of target files load mod scripts
5. Mod scripts execute: modify data tables, wrap functions via ModUtil
6. Game engine calls Lua functions during gameplay — wrapped versions execute mod code

**Critical ordering rule:** Your mod code runs AFTER the data tables it modifies are defined. This is why mods target `RoomManager.lua` (or files imported after data scripts) — to ensure tables exist when your code runs.

---

## Common Pitfalls

1. **Forgetting to re-run ModImporter** after adding/removing mods or game updates
2. **Using `BaseOverride` when `WrapBaseFunction` suffices** — overrides block the chain
3. **Editing game files directly** — changes lost on update, prevents multi-mod coexistence
4. **Wrong load order** — mod runs before data tables exist → nil reference errors
5. **SJSON syntax errors** — no commas, `=` not `:`, missing SJSON Python module
6. **Path separators** — use forward slashes in modfile paths even on Windows
7. **Save corruption** — mods adding new data can corrupt saves if removed mid-playthrough

## Limitations

- **No new art assets** easily — engine has no public asset import pipeline
- **No new audio** easily — FMOD event system non-trivial to extend
- **Engine-level behavior** hardcoded in C++ (rendering, physics, input)
- **No official modding API** — Supergiant doesn't provide tools or support
- **No Steam Workshop** — all mod installation is manual
- **Game updates break mods** — scripts/data may change between versions
- **Mod conflicts** — multiple mods editing same data can clash (ModUtil helps for functions)

## Popular Existing Mods (Reference)

| Mod | Type | Description |
|-----|------|-------------|
| OlympusExtra | Content | Adds new gods (Apollo, Hestia, Hera) with boons, art, voice acting |
| Zyruvias's Incremental Overhaul | Overhaul | Reimagines progression as incremental/idle-game style |
| Ello's Boss Rush | Gameplay | Sequential boss challenges |
| EncounterBalancer | Balance | Rebalances encounter generation |
| Hephaistos | Technical | Ultrawide/multi-monitor resolution support |
| Skip Death Scene | QoL | Removes death animation for faster runs |
| SplitDisplay | Speedrun | Adds split timer display |
| Export Run History | Utility | Exports run history to JSON |
