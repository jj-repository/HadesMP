# Hades Engine & File Formats

## Engine: AQUARIUS

Supergiant Games' proprietary engine, located at `x64Vk/AQUARIUS/`. Supports D3D11 and Vulkan rendering.

### Dependencies
| Library | Purpose |
|---------|---------|
| Lua 5.2 (lua52.dll) | Core scripting |
| FMOD Studio (fmod.dll, fmodstudio.dll) | Audio middleware |
| SDL2 (SDL2.dll) | Input/cross-platform |
| Newtonsoft.Json | JSON handling |
| SQLite3 (sqlite3.dll) | Local database |
| Discord SDK | Discord integration |
| Steam API | Steam integration |
| EOS SDK | Epic Online Services |

### Rendering
- Two backends: DirectX 11 (`x64/`) and Vulkan (`x64Vk/`)
- Shaders in GLSL (`.vert`, `.frag` files)
- Post-processing: bloom, color grading, radial blur, vignette
- Sprite-based 2D with isometric perspective (32 rotation angles per character)
- Bink video codec for pre-rendered animations (`.bik`, `.bik_atlas`)

---

## SJSON Format (Structured JSON)

Custom data format used for all game data files. Human-readable, relaxed superset of JSON.

### Syntax Rules

**Key-Value Assignment** — uses `=` instead of `:`
```
Name = "ZagreusWalk"
Speed = 540.0
Loop = true
```

**No Commas** — items separated by whitespace/newlines only
```
Weapons = [
  {
    Name = "1_BaseWeapon"
  }
  {
    Name = "1_BasePlayerWeapon"
    InheritFrom = "1_BaseWeapon"
  }
]
```

**Objects** — `{ }` braces, opening brace on same or next line
```
Life = {
  Invulnerable = true
}
```

**Arrays** — `[ ]` brackets, no commas between elements
```
Points = [
  { X = 16 Y = 24 }
  { X = 48 Y = 8 }
]
```

**Top-Level Structure** — single object containing a named collection
```
{ Units = [ ... ] }
{ Weapons = [ ... ] }
{ Animations = [ ... ] }
{ Texts = [ ... ] }
```

**Comments** — C-style `/* block comments */`

**Data Types:**
- Strings: `"ZagreusIdle"` (double-quoted)
- Integers: `32`, `0`, `-3`
- Floats: `540.0`, `0.34`, `1E-05`
- Booleans: `true`, `false`
- Null sentinel: `"null"` (string, not actual null)
- Colors: `{ Red = 1.0 Green = 1.0 Blue = 1.0 Alpha = 1.0 }`

**Inheritance** — `InheritFrom` key for property inheritance
```
{
  Name = "FreezeShotUnit"
  InheritFrom = "BaseMedusaHead"
  DisplayInEditor = true
  Speed = 300.0
}
```
Naming conventions:
- `1_` or `_` prefix = base/template (abstract), `DisplayInEditor = false`
- No prefix = concrete type, `DisplayInEditor = true`

### SJSON Files by Domain

| File | Top-Level Key | Contents |
|------|---------------|----------|
| PlayerUnits.sjson | Units | Zagreus, shields |
| Enemies.sjson | Units | Enemy unit definitions |
| NPCs.sjson | Units | NPC definitions |
| PlayerWeapons.sjson | Weapons | Player weapons (158 KB) |
| EnemyWeapons.sjson | Weapons | Enemy weapons (158 KB) |
| PlayerProjectiles.sjson | Projectiles | Player projectiles (204 KB) |
| EnemyProjectiles.sjson | Projectiles | Enemy projectiles (279 KB) |
| Gameplay.sjson | Obstacles | Interactive objects |
| InGameUI.sjson | InGameUI | HUD layout |
| CharacterAnimationsHero.sjson | Animations | Hero animations (1.1 MB) |
| CharacterAnimationsEnemies.sjson | Animations | Enemy animations (336 KB) |
| Audio.sjson | Root keys | Audio bank routing |
| MapGroups.sjson | MapGroups | Map-to-biome groupings |

---

## Map Format (.map_text)

Uses **standard JSON** (NOT SJSON). Each file defines a room layout.

### Top-Level Structure
```json
{
  "AmbientLightColor": { "X": 0.428, "Y": 0.600, "Z": 0.428 },
  "BackdropColor": { "R": 0, "G": 0, "B": 0, "A": 255 },
  "Brightness": 0.5,
  "ThingGroups": [ ... ],
  "TimeLapseCameraLocation": { "X": 0, "Y": 0 },
  "TimeLapseCameraZoom": 1
}
```

### ThingGroups — Draw/Logic Layers

Two hierarchies:

**MapArt (Visual layers, back-to-front):**
- `Terrain_Below_02`, `Terrain_Below` — background
- `Terrain_base`, `Terrain`, `Terrain_01`, `Terrain_02` — ground
- `Terrain_Decor01`, `Terrain_Decor02` — details
- `Terrain_Lighting01` — lighting overlays
- `Terrain_Overlay` — overlay effects (BlendMode 9 = screen)
- `Standing` — objects on ground plane
- `Overlay_01` — above-standing (BlendMode 9)
- `Fog` — atmospheric
- `Lighting_01` — scene lighting
- `Foreground_01`, `ForegroundWall_01` — foreground parallax
- `Heatwave_01` (BlendMode 12) — heat distortion
- `ForegroundDust_01` (BlendMode 2) — particle dust

**MapLogic (Gameplay layers):**
- `Breakables` — destructible objects
- `AmbienceGenerators` — ambient sound
- `Scripting` — script triggers
- `SpikeTraps` — trap placements
- `Impassable` — collision/boundaries
- `SpawnPoints` — enemy/player spawns
- `ExitDoors` — room exits/entrances
- `Events` — scripted event triggers

**BlendMode values:** 0=Normal, 2=Additive, 9=Screen, 11=Lighter, 12=Custom shader

### Room Naming Convention
- **Prefix**: `A_`=Tartarus, `B_`=Asphodel, `C_`=Elysium, `D_`=Styx, `E_`=Surface
- **Type**: `Combat##`, `Boss##`, `MiniBoss##`, `PreBoss##`, `PostBoss##`, `Shop##`, `Story##`, `Reprieve##`, `Survival##`, `Intro`, `Mini##`
- **Special**: `DeathArea` (House hub), `RoomPreRun`, `RoomReturn`

---

## PKG Archives (.pkg + .pkg_manifest)

Binary asset packages containing textures, sprite atlases, and art assets (~1.1 GB total, 130+ packages).

### Organization
- Biome packages: `Tartarus.pkg`, `Asphodel.pkg`, `Elysium.pkg`, `Styx.pkg`
- Weapon packages: `BowWeapon.pkg`, `SwordWeapon.pkg` (per weapon variant)
- God packages: `ZeusUpgrade.pkg`, `AresUpgrade.pkg` (per god)
- Special: `GUI.pkg` (160 MB), `Fx.pkg` (232 MB), `RoomManager.pkg` (51 MB)

### Manifest Format
Binary files mapping asset names to package locations. Contains:
- Sprite atlas references (paths like `bin\Win\Atlases\Asphodel_Fountain_Water00`)
- Animation frame references
- Coordinate/dimension data (X, Y, width, height, UV coords)

**Extraction tool:** Deppth (github.com/quaerus/deppth)

---

## Localization Format

Located at `Content/Game/Text/{lang}/` for 12 languages: en, de, es, fr, it, ja, ko, pl, pt-BR, ru, zh-CN, zh-TW.

### Structure (SJSON)
```
{
  lang = "en"
  Texts = [
    {
      Id = "Health"
      DisplayName = "{!Icons.Health} Life"
      Description = "Your Life Total is {#UpgradeFormat}{$CurrentRun.Hero.Health}..."
    }
  ]
}
```

### Variable Substitution
| Syntax | Purpose |
|--------|---------|
| `{$Variable}` | DisplayName of a Lua variable with auto-formatting |
| `{@Variable}` | DisplayName with ItemName formatting |
| `{*Variable}` | Auto red/green coloring for stat mods |
| `{%Variable}` | Full Description + AdditionalDescription |
| `{^Variable}` | Description only |
| `{+Variable}` | AdditionalDescription only |
| `{!Texture.Path}` | Inline icon: `{!Icons.Health}`, `{!Icons.Currency}` |
| `{#FormatName}` | Text format: `{#UpgradeFormat}`, `{#ItalicFormat}`, `{#BoldFormatGraft}` |

### Files per Language
| File | Contents |
|------|----------|
| HelpText.{lang}.sjson | All gameplay UI text (largest file) |
| CodexText.{lang}.sjson | Codex lore entries |
| MiscText.{lang}.sjson | Dialogue choices, offers, buttons |
| MacroText.sjson | Auto-generated substitutions (no lang suffix) |
| LaunchText.{lang}.sjson | Loading screen text |
| PatchNotes.{lang}.sjson | In-game patch notes |

---

## Animation Data Format

### Animation SJSON Structure
```
{
  Name = "ZagreusWalk"
  FilePath = "Animations\Zagreus\Walk\ZagreusWalk"
  StopAnimation = "ZagreusWalkStop"
  ChainTo = "ZagreusIdle"
  Type = "Slide"
  VideoTexture = "ZagreusWalk_Bink"
  StartFrame = 1
  EndFrame = 60
  NumFrames = 60
  NumAngles = 32
  FrameDataFile = "Game\Animations\FrameData\ZagreusWalk.sga"
  Loop = true
  Scale = 1.05
  OffsetY = -105.0
  Slides = [ ... ]
}
```

### Animation Types
- **Slide** — Frame-by-frame sprite with per-frame events (most common)
- **Constant** — Single frame with interpolated properties over time (VFX)

### Slide Array (Per-Frame Events)
```
{ DurationFrames = 1 FootstepFxL = "FireFootstepL-Spawner" FootstepSound = "/SFX/Player Sounds/FootstepsHardSurfaceRun" }
```

### Key Properties
| Property | Purpose |
|----------|---------|
| FilePath | Sprite sheet path (Windows backslashes) |
| VideoTexture | Bink video texture name |
| FrameDataFile | .sga file with hitbox/collision data |
| NumAngles | Rotation angles (32 = isometric) |
| GroupName | Draw layer (FX_Standing_Top, FX_Auras) |
| Material | Shader: "Emissive", "Unlit" |
| ChainTo | Auto-transition on completion |
| ScaleRadius | VFX effect radius |

### VFX Properties (Constant type)
```
{
  Name = "AuraExplosionDissipation"
  Type = "Constant"
  StartAlpha = 1.0
  Duration = 3.0
  EaseIn = 0.6
  EaseOut = 1.0
  EndScale = 1.15
  StartScale = 0.9
  Material = "Unlit"
}
```

---

## Audio System (FMOD)

- Audio banks in `Content/Audio/Build/` (.bank, .fsb files)
- GUIDs mapped in `Content/Audio/GUIDs.txt`
- Sound paths use forward slashes: `/SFX/Player Sounds/FootstepsHardSurfaceRun`
- Audio routing defined in `Audio.sjson` (maps maps to banks)
- Lua references in `AudioData.lua` (10,446 lines of sound mappings)

### Audio Tools
- **Audio Manager** (Nexus) — guided extract/replace workflow
- **FMOD Bank Tools** — unpack/repack .bank files
- **fsbext** — FMOD/FSB archive extractor
