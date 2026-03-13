# Hades UI, Presentation & Debug

## Screen Architecture

### Universal Pattern
```lua
local screen = { Components = {} }
screen.Name = "ScreenName"
OnScreenOpened({ Flag = screen.Name, PersistCombatUI = true })
FreezePlayerUnit()
EnableShopGamepadCursor()
-- ... build UI ...
HandleScreenInput(screen)  -- BLOCKS until close
-- cleanup on close:
CloseScreen(GetAllIds(screen.Components))
DisableShopGamepadCursor()
UnfreezePlayerUnit()
OnScreenClosed({ Flag = screen.Name })
```

### Screen Lifecycle
1. Guard: `if IsScreenOpen(screen.Name) then return end`
2. Register: `OnScreenOpened()`
3. Lock input: `FreezePlayerUnit()`, `EnableShopGamepadCursor()`
4. Create background (dim overlay + panel)
5. Create title, close button, content
6. Input loop: `HandleScreenInput(screen)` — blocks
7. Cleanup: `CloseScreen()`, `DisableShopGamepadCursor()`, `UnfreezePlayerUnit()`, `OnScreenClosed()`

### ScreenAnchors Global Table
Central registry for all persistent UI element IDs:
- HUD: HealthBack, HealthFill, SuperMeterIcon, MoneyIcon, AmmoIndicatorUI
- Screens: AwardMenuScreen, RunClear, QuestLogScreen
- Transitions: Transition
- Boss bars: BossHealthTitles

---

## UI Components

### Creation Functions
- `CreateScreenComponent({ Name, Group, X, Y, Scale, Sound })` — Screen-space element, returns `{ Id = ... }`
- `CreateScreenObstacle({ Name, X, Y, Group, DestinationId, Scale })` — Low-level, returns raw ID
- `SpawnObstacle({ Name, Group, DestinationId, Attach, OffsetY })` — World-space (health bars)

### Widget Types
| Name | Purpose |
|------|---------|
| rectangle01 | Full-screen dim overlays |
| ShopBackground | Shop screen background |
| AwardMenuBackground | Keepsake menu background |
| EndPanelBox | Panel background |
| LevelUpBackground | Splatter/ink background |
| ButtonClose | Close button (Cancel hotkey) |
| ButtonDefault | Generic clickable |
| ButtonCodexUp/Down | Scroll arrows |
| ButtonCodexLeft/Right | Navigation arrows |
| ButtonGhostAdminTab | Category tab buttons |
| RadioButton | Selectable toggle |
| MarketSlot | Market item slot |
| BoonSlot1/2/3 | Boon selection buttons |
| BlankObstacle | Invisible anchor |
| EnemyHealthBar/Fill | Enemy health bars |

### Text System
```lua
CreateTextBox({ Id, Text, FontSize, Font, Color, OffsetX, OffsetY, Width, Justification })
ModifyTextBox({ Id, Text, Color, ColorTarget, ColorDuration, FadeTarget, ScaleTarget })
CreateTextBoxWithFormat({ Id, Text, Format, VariableAutoFormat, UseDescription, LuaKey, LuaValue })
DestroyTextBox({ Id })
```

### Fonts
SpectralSCLightTitling, SpectralSCMedium, AlegreyaSansSCBold, AlegreyaSansSCExtraBold, AlegreyaSansSCRegular, AlegreyaSansSCMedium, AlegreyaSansRegular, AlegreyaSansExtraBoldItalic, CrimsonTextItalic, CrimsonTextBoldItalic

### Render Groups (layering)
Combat_Menu, Combat_Menu_Additive, Combat_Menu_TraitTray, Combat_Menu_TraitTray_Overlay, Combat_Menu_Overlay, Combat_Menu_Overlay2, Combat_UI, Combat_UI_World, Combat_UI_World_Backing, Combat_UI_Backing, Overlay

---

## Animation / Tween System

### Movement
- `Move({ Id, DestinationId, Duration, EaseIn, EaseOut })` — toward target
- `Move({ Id, Angle, Speed, Distance, Duration })` — directional

### Opacity
- `SetAlpha({ Id, Fraction, Duration })` — 0.0 to 1.0

### Scale
- `SetScale({ Id, Fraction, Duration, EaseIn, EaseOut })` — uniform
- `SetScaleX/Y({ Id, Fraction, Duration })` — axis-specific (health bars)

### Color
- `SetColor({ Id, Color, Duration, EaseIn, EaseOut })` — transition

### Sprite Animation
- `SetAnimation({ Name, DestinationId, Scale })` — set sprite anim
- `CreateAnimation({ Name, DestinationId, GroupName, Color, Scale })` — one-shot VFX
- `StopAnimation({ Name, DestinationId })` — stop anim
- `SetAnimationFrameTarget({ Name, Fraction, DestinationId })` — progress bar (health)

### Screen Effects
- `ShakeScreen({ Speed, Distance, FalloffSpeed, Duration })` — camera shake
- `Shake({ Id, Distance, Speed, Duration })` — object shake
- `Flash({ Id, Speed, MinFraction, MaxFraction, Color })` — pulse
- `FocusCamera({ Fraction, ZoomType, Duration })` — zoom ("Ease", "Overshoot")
- `PanCamera({ Id, Duration, EaseIn, EaseOut })` — pan
- `LockCamera({ Id, Duration })` — lock to target

### Post-Processing
- `AdjustColorGrading({ Name, Duration })` — presets: "Off", "Dusk", "Rain", "DeathDefianceSubtle"
- `AdjustFullscreenBloom({ Name, Duration })` — "Off", "Default", "LightningStrike", "DeathDefiance", "Blur"
- `AdjustRadialBlurStrength/Distance({ Fraction, Duration })`
- `AdjustFrame({ Duration, Fraction })` — vignette

### Full-Screen Transitions
```lua
FullScreenFadeOutAnimation(animationName)  -- Group "Overlay", Dusk grading
FullScreenFadeInAnimation(animationName)   -- Remove grading/bloom
```

### Combat Presentation Budget
```lua
CombatPresentationCaps = {
    GeneralCap = 20,
    DoImpactSound = 5,
    DisplayDamageText = ConstantsData.MaxActiveEnemyCount,
}
```
Semaphore-based: `CanStartBudgetedPresentation(name)` / `ExitBudgetedPresentation(name)`

---

## Boon Selection (UpgradeChoice.lua)

`OpenUpgradeChoiceMenu(lootData)` when touching a god boon pickup.

### Button Layout
BoonSlot1/2/3 — each shows: trait icon with rarity color, name, description with formatted stats, slot indicator (Melee/Secondary/Ranged/Rush/Shout), "New" badge.

### Three Item Types
1. **Trait** — standard god boon
2. **Consumable** — Pom of Power, health, etc.
3. **TransformingTrait** — Chaos (curse→blessing)

### Sorting
By slot: Melee=0, Secondary=1, Ranged=2, Rush=3, Shout=4

### Rarity Visualization
BoonRarityPatch animation + color coding: Common, Rare, Epic, Heroic, Legendary

### Exchange System
When replacing existing trait: shows existing trait overlay, comparison on hover via `ActivateSwapTraitPresentation()`

### Reroll
RerollPanel shows cost/count. `AttemptBoonLootReroll()`: spend reroll → regenerate options (excluding current) → rebuild buttons.

### Selection Flow
`HandleUpgradeChoiceSelection()`: log choice → `AddTraitToHero()` → presentation → close screen

---

## Shop Screens

### Wretched Broker (MarketScreen.lua)
- Items generated once/run, cached in `CurrentRun.MarketItems`
- Priority items always shown, non-priority fill remaining slots
- Purchase: check afford → spend → add resource → mark sold out

### House Contractor (GhostAdminScreen.lua)
- Category tabs with DisplayOrder arrays
- Pagination: ScrollOffset + ItemsPerPage
- "New" sparkle for unviewed items
- Purchase triggers camera pan → fade → activate cosmetic → reveal VFX → voice lines

### Well of Charon (SellTraitScripts.lua)
- Shows up to 3 random owned god traits
- Sell value based on rarity: `SellTraitData.RarityValues[rarity]` with Min/Max
- Stack bonus for multi-level traits

---

## HUD System (UIScripts.lua)

### Health Bar
Components: HealthBack, HealthFill, HealthFlash, HealthRally, LifePipIds
Functions: `ShowHealthUI()`, `UpdateHealthUI()`, `HideHealthUI()`, `RecreateLifePips()`
Updated via `SetAnimationFrameTarget` for smooth fill.

### Super Meter
Components: SuperMeterIcon, SuperPipIds, SuperPipBackingIds
Functions: `ShowSuperMeter()`, `UpdateSuperMeterUI()`, `SuperMeterFeedback()`

### Trait Tray
Components: TraitBacking, TraitAnchorIds, TraitPlaceholderIcons
Sorted: Melee, Secondary, Ranged, Rush, Shout, then Keepsake at bottom.
Functions: `TraitUIAdd()`, `TraitUIRemove()`

### Show/Hide System
```lua
CombatUI.Hide = {}  -- table of reasons to hide
HideCombatUI(flag)   -- add reason, hide all
ShowCombatUI(flag)   -- remove reason, show if all cleared
UnblockCombatUI(flag) -- remove reason, don't force show
```
Multiple systems can independently request hiding (e.g., "BossEntrance", "AwardMenu").

### Enemy Health Bars
- World-space attached obstacles
- Auto-sized by MaxHealth thresholds (Small/Medium/Large/ExtraLarge)
- Color-coded: Red (normal), Gold (armor), Cyan (shields), Purple (cursed), Green (charmed)
- Stored ammo icons (bloodstones) below bar
- Elite badges to the left
- Deferred update system for performance

### Boss Health Bars
- Screen-space elements
- Name text + fill bar + falloff bar (slow drain)
- Status effect icons positioned via `PositionEffectStacks()`

---

## Input Handling

### HandleScreenInput Loop
```lua
function HandleScreenInput(screen)
    screen.KeepOpen = true
    while screen.KeepOpen do
        -- Collect interactive button IDs
        -- Register NotifyOnInteract for buttons
        -- Register NotifyOnControlPressed for hotkeys
        waitUntil("ScreenInput")
        -- Dispatch to button.OnPressedFunctionName
    end
end
```

### Button Configuration
```lua
component.OnPressedFunctionName = "HandleMarketPurchase"
component.ControlHotkey = "Cancel"
component.ControlHotkeys = { "MenuLeft", "Left" }
component.OnMouseOverFunctionName = "..."
component.OnMouseOffFunctionName = "..."
```

### Input Blocking
- `AddInputBlock({ Name = "..." })` / `RemoveInputBlock()` — named blocks (stack)
- `FreezePlayerUnit()` / `UnfreezePlayerUnit()` — complete freeze
- `SetPlayerInvulnerable("Name")` / `SetPlayerVulnerable()` — damage immunity
- `AddTimerBlock(CurrentRun, "Name")` / `RemoveTimerBlock()` — pause timers

### Gamepad Navigation
```lua
EnableShopGamepadCursor() / DisableShopGamepadCursor()
SetConfigOption({ Name = "FreeFormSelectWrapY", Value = true })
SetConfigOption({ Name = "FreeFormSelectStepDistance", Value = 32 })
SetInteractProperty({ DestinationId, Property = "FreeFormSelectable", Value = false })
```

---

## Debug Commands (DebugScripts.lua — 1,215 lines)

### Hotkeys

| Key | Function |
|-----|----------|
| Ctrl+Shift+K | Free camera |
| Ctrl+Shift+L | Load checkpoint |
| Ctrl+Shift+X | Damage player 45 HP |
| Ctrl+X | Kill player |
| Ctrl+T | Toggle UI visibility |
| Ctrl+Shift+P | Toggle AutoPlay |
| Ctrl+Alt+Shift+P | AutoPlay + Invulnerable |
| Alt+W | Spawn Daedalus Hammer |
| Alt+L | Spawn Pom of Power |
| Shift+X | Spawn god boon (Dionysus default) |
| Alt+X | Spawn MetaUpgrade + Darkness |
| Alt+A | Spawn ChaosWeaponUpgrade |
| Alt+H | Spawn health drop |
| Alt+R | Add 99 rerolls |
| Alt+M | Spawn 50 obols |
| Alt+D | Spawn dummy enemy (PunchingBagUnit) |
| Alt+K | Kill all required kills (skip encounter) |
| Alt+I | Display run info |
| Alt+T | Add test traits |
| Alt+Y | Toggle damage multiplier logging |
| Alt+1-6 | Switch weapons (Sword/Spear/Shield/Bow/Gun/Fist) |
| Ctrl+N | Force navigate to B_MiniBoss02 |
| Ctrl+M | Add 99999 resources (MetaPoints, Gems, Keys, etc.) |
| Ctrl+Shift+S | Fill super meter |
| Ctrl+Shift+F | Full wrath + Zeus shout |
| Ctrl+Shift+G | Max all NPC gifts |
| Ctrl+Shift+C | Unlock entire Codex |
| Ctrl+Shift+Y | Show RunClearScreen |
| Ctrl+Alt+C | Play credits |
| Ctrl+Alt+L | Open Mirror screen |
| Ctrl+Alt+S | Open Pact screen |
| Ctrl+Alt+G | Dump game state stats |
| Ctrl+Shift+CapsLock | Dump game state to JSON |
| Ctrl+Alt+Shift+C | Unlock all Contractor items |
| Ctrl+Alt+R | Reload all traits (hot reload) |
| Ctrl+Alt+Shift+T | Performance test (spawn 1000 objects) |
| Ctrl+Alt+N | Animation test |

### Helper Functions
- `SpawnDummyEnemy()` — PunchingBagUnit at hero position
- `ForcePlayTextLines(textLineSet)` — force dialogue
- `ReloadAllTraits()` — hot reload trait data
- `UnlockEntireCodex()` — unlock all entries
- `DumpGameStateStats()` — print statistics
- `DumpGameStateToFile()` — serialize to JSON
- `OnHotLoadXML()` / `OnHotLoadLua()` — hot reload callbacks

---

## Room Presentation (RoomPresentation.lua — 6,719 lines)

### Room Transitions
1. `StartRoomPresentation()` — camera clamps, zoom, music, ambience
2. Entrance function (per room type):
   - `RoomEntranceStandard()` — standard fade-in, hero walk-in
   - `RoomEntranceBoss()` — dramatic entrance with name card
   - `RoomEntranceHades()` — special Hades arena entrance
   - `AsphodelEnterRoomPresentation()` — boat arrival
   - `RoomEntrancePortal()` — portal entry
3. Input blocks during presentation, removed on completion
4. Leave: camera pan, fade out, load next room

### Location Text Display
`DisplayLocationText()` — room name with character fade-in, slow zoom, fade-out

### Unlock Text
`DisplayUnlockText()` — for weapon unlocks, achievements. Centered title + subtitle, icon, sound, auto-fade.

### Toast Notifications
- `ShowCodexUpdate()` — "Entry Unlocked", fades after 3s
- `QuestAddedPresentation()` / `QuestCompletedPresentation()` — quest toasts

---

## Run Clear Screen (RunClearScreen.lua — 374 lines)

Shows conditional victory messages based on:
- Milestone clears (1, 10, 50, 100, 250, 500)
- Near-death clear (under 5% HP, no DD)
- Full health clear
- Speed clears (under 15 min, 12 min)
- Slow clears (over 60 min)
- No money / high money (2000+)
- No Mirror investments
- No Olympian boons
- God-themed clears (all Zeus boons, etc.)

---

## Music Player (MusicPlayerScreen.lua)

Interactive jukebox in House of Hades:
- Tracks unlocked via cosmetics
- Play/pause per track
- Sets all audio stems to full volume
- Kills Orpheus ambient music
- Hades voice line complaints
