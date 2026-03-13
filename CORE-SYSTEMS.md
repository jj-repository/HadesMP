# Hades Core Systems

## Script Import Chain

`RoomManager.lua` is the central hub. It imports everything in this order:
```
Color.lua, UIPresentation.lua, UIScripts.lua, CreditsScripts.lua,
EventPresentation.lua, AudioScripts.lua, Narrative.lua, CodexData.lua,
GiftData.lua, SellTraitData.lua, StoreData.lua, WeaponUpgradeData.lua,
BoonInfoScreenData.lua, GhostData.lua, ObstacleData.lua, CodexScripts.lua,
UtilityScripts.lua, DebugScripts.lua, PlayerAIData.lua, Localization.lua,
Art.lua, EnemyAI.lua, UpgradeManager.lua, FishingScripts.lua, FishingData.lua,
AwardMenuScripts.lua, KeepsakeScripts.lua, StoreScripts.lua, SellTraitScripts.lua,
MarketScreen.lua, GhostAdminScreen.lua, MusicPlayerScreen.lua, QuestLogScreen.lua,
AchievementLogic.lua, BadgePresentation.lua, BadgeLogic.lua, RunClearScreen.lua,
RunHistoryScreen.lua, GameStatsScreen.lua, RoomPresentation.lua, RunData.lua,
RunManager.lua, Combat.lua, CombatPresentation.lua, GhostScripts.lua,
TraitTrayScripts.lua, WeaponUpgradeScripts.lua, BoonInfoScreenScripts.lua
```
Then at the end: `Import "DeathLoop.lua"`

`OnPreThingCreation` hook in RoomManager.lua initializes the game on each map load.

---

## Threading System (Main.lua)

Hades uses Lua coroutines for all asynchronous gameplay behavior.

### Global State
```lua
_worldTime = 0          -- game world time
_screenTime = 0         -- screen/UI time (pauses with game)
_threads = {}           -- active waiting threads
_workingThreads = {}    -- threads being resumed this frame
_eventListeners = {}    -- threads waiting for events
_events = {}            -- events that have fired (for late listeners)
_threadStack = nil      -- stack of currently executing threads
_activeThread = nil     -- currently running thread
```

### Core Functions

**`wait(duration, tag)`** — Yield coroutine for `duration` seconds (world time)
```lua
function wait(duration, tag)
    coroutine.yield({ wait = duration, tag = tag, threadInfo = lastGoodThreadInfo })
end
```

**`waitScreenTime(duration, tag)`** — Same but uses screen time (pauses with UI)

**`waitUntil(event, tag)`** — Yield until named event fires. If event already fired, returns immediately.
```lua
function waitUntil(event, tag)
    if _events[event] ~= nil then  -- already happened
        _events[event] = nil
        return
    end
    coroutine.yield({ wait = -1, event = event, tag = tag })
end
```

**`notify(event, wasTimeout)`** — Fire an event, resume all waiting threads. Stores event if no one waiting.
```lua
function notify(event, wasTimeout)
    _eventTimeoutRecord[event] = wasTimeout
    local eventListeners = _eventListeners[event]
    if eventListeners ~= nil then
        _eventListeners[event] = nil
        for index, listener in pairs(eventListeners) do
            resume(listener.Thread, _workingThreads)
        end
    else
        _events[event] = true  -- store for late listeners
    end
end
```

**`notifyExistingWaiters(event)`** — Like notify but does NOT store if no one waiting.

**`thread(func, ...)`** — Spawn a new coroutine (not shown in Main.lua excerpt but used everywhere)

**`dispatch(func, triggerArgs)`** — Create and immediately start a coroutine:
```lua
function dispatch(func, triggerArgs)
    local co = coroutine.create(function() func(triggerArgs) end)
    local status = resume(co, _threads)
end
```

**`resume(thread, threadTable)`** — Resume a coroutine, handle wait/event yields:
- If yield contains `wait > 0`: schedule for future resume
- If yield contains `wait < 0` + event: register as event listener
- Returns "wait", "waitUntil", or "done"

### Thread Management
- **`killWaitUntilThreads(event)`** — Kill all threads waiting for an event
- **`hurryUpWaitingThreads(tag)`** — Set resume time to now for tagged threads
- **`HasThread(tag)`** — Check if a thread with given tag exists
- **`SetThreadWait(tag, duration)`** — Change a thread's wait duration

### Usage Pattern (Common in game code)
```lua
-- Start an async task
thread(function()
    wait(1.0)  -- wait 1 second
    DoSomething()
    waitUntil("SomeEvent")  -- wait for event
    DoSomethingElse()
end)

-- Fire an event
notify("SomeEvent")
```

---

## Game State Architecture

### Global Tables

**`GameState`** — Persistent save data (survives between runs and sessions):
```lua
GameState = {
    WeaponHistory = {},           -- weapons used per run
    WeaponsUnlocked = {},         -- unlocked weapons
    RunHistory = {},              -- past run records
    MetaUpgrades = {},            -- Mirror of Night levels
    WeaponKills = {},             -- kills per weapon
    LootPickups = {},             -- boons picked up lifetime
    TraitsTaken = {},             -- traits used lifetime
    QuestStatus = {},             -- quest completion status
    Cosmetics = {},               -- purchased cosmetics
    NPCInteractions = {},         -- NPC talk counts
    EnemyKills = {},              -- enemy kill counts
    Resources = {},               -- current resource amounts
    LifetimeResourcesGained = {}, -- total resources earned
    LifetimeResourcesSpent = {},  -- total resources spent
    ShrinePointClearsComplete = {},-- heat clears
    Flags = {},                   -- boolean game state flags
    EasyModeLevel = 0,            -- God Mode damage reduction level
    MetaUpgradesSelected = {},    -- which Mirror upgrade variant is active
    -- ... many more
}
```

**`CurrentRun`** — Current run state (reset each run):
```lua
CurrentRun = {
    Hero = { ... },               -- hero unit with stats, traits, weapons
    DamageRecord = {},            -- damage dealt this run
    HealthRecord = {},            -- healing received
    RoomHistory = {},             -- rooms visited
    LootTypeHistory = {},         -- boons offered
    Money = 0,                    -- current obols
    MoneySpent = 0,
    NumRerolls = 0,               -- remaining rerolls
    RunDepthCache = 1,            -- current depth
    GameplayTime = 0,             -- run timer
    BiomeTime = 0,                -- current biome timer
    ActiveBiomeTimer = false,     -- pact time limit active
    CompletedStyxWings = 0,       -- styx tunnels completed
    BannedEliteAttributes = {},   -- elites excluded this run
    SupportAINames = {},          -- active companion summons
    ClosedDoors = {},             -- doors chosen (for reward tracking)
    -- ... many more
}
```

**`SessionState`** — Ephemeral session state (not saved)

### Hero Creation (RunManager.lua)
```lua
function CreateNewHero(prevRun, args)
    local newHero = DeepCopyTable(GetEligibleHero())
    newHero.Traits = {}
    newHero.Health = newHero.MaxHealth
    newHero.SuperMeter = 0
    newHero.SuperMeterLimit = 100

    -- Apply Pact damage modifiers
    AddIncomingDamageModifier(newHero, {
        Name = "EnemyDamageShrineUpgrade",
        NonTrapDamageTakenMultiplier = damageIncrease
    })

    -- Apply Mirror rally health bonus
    newHero.RallyHealth.ConversionPercent = newHero.RallyHealth.ConversionPercent + mirrorBonus

    return newHero
end
```

### Run Initialization (RunManager.lua)
`StartNewRun(prevRun, args)` creates a fresh run:
1. Creates `CurrentRun` table
2. Creates hero via `CreateNewHero()`
3. Applies bonus darkness weapon trait
4. Equips keepsake, companion, weapon aspect
5. Initializes room history, loot history, records
6. Sets starting money (Mirror bonus + trait bonuses)
7. Sets reroll count from Mirror upgrades
8. Initializes Death Defiance last stands
9. Initializes reward stores
10. Creates first room

### Game State Flags
`GameStateFlagData.RunStartFlags` — flags checked at run start:
- `FistUnlocked`: requires Sword, Spear, Shield, Bow unlocked
- `GunUnlocked`: requires all 5 previous weapons
- `AspectsUnlocked`: requires all 6 weapons + 1 Titan Blood earned

---

## Combat System (Combat.lua)

### Damage Calculation

The damage pipeline has three stages:

**1. Damage Additions** (`CalculateDamageAdditions`)
Fixed damage added based on attacker modifiers:
- `TriggerEffectAddition` — bonus damage from triggered effects
- `GoldMultiplier` — damage based on current gold (e.g., Ocean's Bounty synergy)

**2. Damage Multipliers** (`CalculateDamageMultipliers`)
Two categories that combine differently:
- **Additive multipliers** (bonuses ≥ 1.0): `damageMultipliers += multiplier - 1`
- **Multiplicative multipliers** (reductions < 1.0): `damageReductionMultipliers *= multiplier`

Final: `baseDamage * damageMultipliers * damageReductionMultipliers`

**Attacker OutgoingDamageModifiers checked:**
| Modifier | Condition |
|----------|-----------|
| GlobalMultiplier | Always applies |
| ValidWeaponMultiplier | Weapon matches ValidWeapons list |
| HighHealthSourceMultiplierData | Attacker above health threshold |
| PerUniqueGodMultiplier | Per unique god boon equipped |
| BossDamageMultiplier | Target is a boss |
| ZeroRangedWeaponAmmoMultiplier | No cast ammo remaining |
| EffectThresholdDamageMultiplier | Effect damage threshold met |
| PerfectChargeMultiplier | Perfect charge attack |
| StoredAmmoMultiplier | Target has lodged bloodstones |
| UnstoredAmmoMultiplier | Target has no lodged bloodstones |
| HealthBufferDamageMultiplier | Target has armor |
| HitVulnerabilityMultiplier | Target is vulnerable |
| HitMaxHealthMultiplier | Target at full health |
| MinRequiredVulnerabilityEffects | Target has N+ status effects (Privileged Status) |
| DistanceMultiplier | Distance above threshold |
| ProximityMultiplier | Distance below threshold |
| RequiredEffectsMultiplier | Target has required status effects |
| RequiredSelfEffectsMultiplier | Attacker has required effects |
| LowHealthDamageOutputMultiplier | Attacker below health threshold |

**Victim IncomingDamageModifiers checked:**
| Modifier | Condition |
|----------|-----------|
| GlobalMultiplier | Always applies |
| NonTrapDamageTakenMultiplier | Damage from enemies (Pact) |
| TrapDamageTakenMultiplier | Damage from traps (Pact) |
| BossDamageMultiplier | Attacker is a boss |
| LowHealthDamageTakenMultiplier | Victim below health threshold |
| ValidWeaponMultiplier | Weapon matches list |
| ProjectileDeflectedMultiplier | Projectile was deflected |
| DistanceMultiplier / ProximityMultiplier | Distance-based |
| HitVulnerabilityMultiplier | Vulnerability state |
| HitArmorMultiplier | Hit armor |
| PlayerMultiplier | Attacker is player |
| NonPlayerMultiplier | Attacker is not player |
| SelfMultiplier | Self-damage |

### Healing System
```lua
function Heal(victim, triggerArgs)
    -- HealFraction converts to HealAmount based on MaxHealth
    -- Caps at MaxHealth
    -- Records healing source for stats
    -- Updates health UI
    -- Checks low-health trait thresholds
end
```

### Damage Modifier API
```lua
AddIncomingDamageModifier(unit, { Name="...", GlobalMultiplier=0.8, ... })
AddOutgoingDamageModifier(unit, { Name="...", ValidWeapons={...}, ... })
RemoveIncomingDamageModifier(unit, name)
HasIncomingDamageModifier(unit, name)
HasOutgoingDamageModifier(unit, name)
AddOutgoingLifestealModifier(unit, data)
```

### Weapon Events (Combat.lua)
The file registers global event handlers:

```lua
OnProjectileReflect  -- Parry/reflect: fire OnProjectileReflectWeapons traits
OnProjectileBlock    -- Block: play block presentation, trigger OnBlockDamageFunctionName traits
OnDodge              -- Player dodge: play dodge presentation
OnWeaponFired "RangedWeapon"  -- Cast fired: handle ammo reload (Stygian Soul), update ammo UI
OnWeaponFired "GunWeapon..."  -- Gun fired: update gun UI, handle last-shot traits, swap sniper back
OnControlPressed "Reload"     -- Manual reload: for Exagryph and aspects
OnWeaponTriggerRelease        -- Weapon release: stop sounds, auto-reload gun
```

### Gun Reload System
```lua
function ReloadGun(attacker, weaponData)
    -- Disable all gun weapons during reload
    -- Empty ammo, play reload animation
    -- Wait ActiveReloadTime
    -- Refill ammo, re-enable weapons
    -- Handle manual reload bonus (Hestia aspect)
end
```

---

## Room Management (RoomManager.lua)

### Initialization Hook
`OnPreThingCreation` — runs before each map loads:
1. `UpdateConfigOptionCache()`
2. `RandomInit()` — seed RNG
3. `DoPatches()` — cleanup leaked globals
4. `SetupMap()` — configure map
5. `AudioInit()` — initialize audio
6. `NarrativeInit()` — initialize dialogue system
7. `CodexInit()` — initialize codex
8. If `GameState == nil`: `StartNewGame()` — first-time setup
9. Handle room flipping and map resets

### Map Load Hook
`OnAnyLoad` — runs after map finishes loading:
1. `CheckQuestStatus()` — update quest progress
2. `CheckProgressAchievements()` — check achievement progress
3. `RemoveInputBlock("MapLoad")`
4. If exits unlocked: `RestoreUnlockRoomExits()`
5. Else: `StartRoom()` — begin room gameplay

### Using Declarations
RoomManager.lua declares `Using` for pre-loaded assets:
- Screen objects: BlackScreen, BaseLoot, BloodFrame
- Interactive objects: ChallengeSwitchBase, SecretDoor, ShrinePointDoor
- Enemy weapon pickups: EnemySwordIdle/Pickup, EnemySpearIdle/Pickup, etc.
- Breakables: BreakableIdle1/2/3, BreakableHighValue
- Traps: SpikeTrap, DartTrap, GasTrap, SawTrap, ReflectiveMirror
- Enemies (non-binked): Swarmer, HeavyRanged, Crawler, ShadeNaked, etc.

### Room Lifecycle
1. `OnPreThingCreation` — pre-load setup
2. `OnAnyLoad` → `StartRoom()` — begin room
3. Room entrance presentation plays
4. Encounter starts (enemies spawn)
5. Combat until encounter complete
6. Exits unlock, rewards offered
7. Player chooses door → next room loads
8. `OnPreThingCreation` for new room...

---

## GameStateRequirements — Universal Condition System

Used across ALL systems (quests, dialogue, cosmetics, shop items, NPC spawning, achievements):

| Condition | Type | Purpose |
|-----------|------|---------|
| RequiredTextLines | string[] | Must have seen these dialogue lines |
| RequiredFalseTextLines | string[] | Must NOT have seen these lines |
| RequiredMinCompletedRuns | int | Minimum completed runs |
| RequiredMaxDepth | int | Maximum dungeon depth reached |
| RequiredKills | table | Specific enemy kill requirements |
| RequiredAnyKillsThisRun | string[] | Killed any of these this run |
| RequiredSeenRooms | string[] | Must have visited these rooms |
| RequiredCosmetics | string[] | Must own these cosmetics |
| RequiredNumCosmeticsMin | int | Minimum cosmetics purchased |
| RequiredWeaponsUnlocked | string[] | Must have unlocked these weapons |
| RequiredTraitsTaken | string[] | Must have used these traits |
| RequiredOneOfTraits | string[] | Must have any one of these |
| RequiredTrueFlags | string[] | Boolean flags that must be true |
| RequiredFalseFlags | string[] | Boolean flags that must be false |
| RequiredMinShrinePointThresholdClear | int | Minimum heat clear |
| RequiredLifetimeResourcesGainedMin | table | Minimum lifetime resources |
| RequiredLifetimeResourcesSpentMin | table | Minimum lifetime spent |
| RequiredMinNPCInteractions | table | Minimum NPC interaction counts |
| RequiredTextLinesThisRun | string[] | Seen these lines THIS run |
| RequiredFalseTextLinesThisRun | string[] | NOT seen these THIS run |
| RequiredPlayed | string[] | Specific voice lines played |
| RequiredClearedWithMetaUpgrades | string[] | Cleared with specific upgrades |
| RequiredEliteAttributeKills | table | Killed elites with specific attributes |
| RequiredMinItemInteractions | table | Minimum item use counts |
