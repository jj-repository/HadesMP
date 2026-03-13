# Hades Enemies, AI & Encounters

## Data Structure

All enemies defined in `UnitSetData.Enemies` (EnemyData.lua, 27,653 lines). Each enemy is a Lua table with:

**Core:** Name, InheritFrom (multiple inheritance), GenusName, RequiredKill, DamageType
**Health:** MaxHealth, HealthBuffer (armor), HealthBufferRegenDelay/Rate
**Defense:** MaxHitShields (stagger resistance, default 5), HitShieldRegenTime
**Movement:** Speed, CanBeFrozen, DashDistance/Duration
**Combat:** DifficultyRating, WeaponOptions, AIOptions, AIStages (boss phases)
**Aggro:** AIAggroRange, AggroMinimumDistance, AggroIfLastAlive, ChainAggroAllEnemies
**Generator:** DifficultyRating, BlockEnemyTypes (mutex), RequiredRoomFeature

---

## Inheritance Hierarchy

### Base Types
| Type | Purpose |
|------|---------|
| IsNeutral | Non-combat (breakables, NPCs). DamageType="Neutral" |
| BaseVulnerableEnemy | Root of all combat enemies. RequiredKill=true, CanBeFrozen=true, MaxHitShields=5 |
| BaseBossEnemy | Bosses. Inherits BaseVulnerableEnemy + IsBoss=true |
| Elite | Elite modifier. Adds EliteAttributeOptions |
| SuperElite | Super-elite (Hades fight spawns) |

### Family Bases (all inherit BaseVulnerableEnemy)
| Family | GenusName | Description |
|--------|-----------|-------------|
| BaseThug | Wretched | Melee bruisers |
| BaseSwarmer | Numbskull | Fast weak melee |
| BaseGlutton | Wretched | Burrowing attackers |
| BaseThief | Wretched | Sneaky, mines, assassins |
| BaseCaster | Witch/Spreader | Ranged magic |
| BaseCrystal | Crystal | Stationary |
| BaseBloodless | Bloodless | Skeleton-type |
| BaseShade | Shade | Elysium enemies |
| BaseSatyr | Satyr | Poison users |
| BaseSpawner | Skullomat | Spawns others |
| BaseTrap | Trap | Environmental hazards |

---

## Complete Enemy Reference

### Tartarus (Biome 1)

| Enemy | HP | Armor | DiffRating | AI | Notes |
|-------|---:|------:|----------:|----|-------|
| HeavyMelee | 130 | 0 | 7 | AttackerAI | Basic melee thug |
| HeavyMeleeElite | 195 | 50 | 45 | AttackerAI | Elite version |
| HeavyMelee2 | 140 | 0 | 10 | AttackerAI | Shield dash variant |
| HeavyMelee2Elite | 210 | 50 | 50 | AttackerAI | Elite shield dash |
| Swarmer | 38 | 0 | 3 | AttackerAI | Fast, weak, groups |
| SwarmerElite | 57 | 0 | 25 | AttackerAI | Elite swarmer |
| LightRanged | 65 | 0 | 7 | Attacker+HideAndPeek | Ranged, takes cover |
| LightRangedElite | 97 | 35 | 50 | Attacker+HideAndPeek | Elite caster |
| PunchingBagUnit | 55 | 0 | 5 | AttackerAI | Numbskull charger |
| PunchingBagUnitElite | 82 | 0 | 35 | AttackerAI | Elite charger |
| ThiefMineLayer | 95 | 0 | 10 | AttackerAI | Proximity mines |
| ThiefMineLayerElite | 142 | 40 | 55 | AttackerAI | Elite mines |
| ThiefImpulseMineLayer | 100 | 0 | 12 | AttackerAI | Push mines |
| ThiefImpulseMineLayerElite | 150 | 45 | 60 | AttackerAI | Elite push mines |
| DisembodiedHead | 1 | 0 | 2 | PassiveAttack | Floating head, 1 HP |
| DisembodiedHeadElite | 1 | 0 | 20 | PassiveAttack | Elite floating head |
| FreezeShotUnit | 90 | 0 | 15 | Attacker+HideAndPeek | Chill projectiles |
| FreezeShotUnitElite | 135 | 40 | 60 | Attacker+HideAndPeek | Elite chill |
| CrusherUnit | 250 | 60 | 27 | AttackerAI | Large slam enemy |
| CrusherUnitElite | 375 | 120 | 70 | AttackerAI | Elite crusher |
| Spawner | 140 | 0 | 12 | PassiveAttack | Spawns swarmers |
| SpawnerElite | 210 | 50 | 55 | PassiveAttack | Elite spawner |

**Biome 1 Pool:** HeavyMelee, HeavyMelee2, Swarmer, LightRanged, PunchingBagUnit, ThiefMineLayer, ThiefImpulseMineLayer, DisembodiedHead, FreezeShotUnit, CrusherUnit, Spawner

### Asphodel (Biome 2)

| Enemy | HP | Armor | DiffRating | AI | Notes |
|-------|---:|------:|----------:|----|-------|
| HeavyRanged | 200 | 0 | 17 | AttackerAI | Ranged bloodless |
| HeavyRangedElite | 300 | 80 | 65 | AttackerAI | Elite ranged |
| HeavyRangedSplitter | 220 | 0 | 20 | AttackerAI | Split projectile |
| HeavyRangedSplitterElite | 330 | 90 | 72 | AttackerAI | Elite splitter |
| HeavyRangedForked | 200 | 0 | 17 | AttackerAI | Forked shot |
| HeavyRangedForkedElite | 300 | 80 | 65 | AttackerAI | Elite forked |
| BloodlessNaked | 120 | 0 | 9 | AttackerAI | Melee bloodless |
| BloodlessNakedElite | 180 | 50 | 50 | AttackerAI | Elite melee |
| BloodlessNakedBerserker | 130 | 0 | 11 | AttackerAI | Berserker |
| BloodlessNakedBerserkerElite | 195 | 55 | 55 | AttackerAI | Elite berserker |
| BloodlessPitcher | 160 | 0 | 15 | AttackerAI | Grenade thrower |
| BloodlessPitcherElite | 240 | 65 | 60 | AttackerAI | Elite pitcher |
| BloodlessSelfDestruct | 85 | 0 | 7 | AttackerAI | Suicide bomber |
| BloodlessSelfDestructElite | 127 | 35 | 42 | AttackerAI | Elite bomber |
| Crawler | 88 | 0 | 5 | AttackerAI | Magma crawler |
| CrawlerElite | 132 | 0 | 35 | AttackerAI | Elite crawler |
| CrawlerMiniBoss | 430 | 200 | 240 | AttackerAI | Miniboss crawler |
| Brimstone | 1 | 0 | 10 | PassiveAttack | Flame pillar |
| BrimstoneElite | 1 | 0 | 35 | PassiveAttack | Elite flame |
| Spreader | 170 | 0 | 20 | Attacker+HideAndPeek | AoE spreader |
| SpreaderElite | 255 | 70 | 70 | Attacker+HideAndPeek | Elite spreader |
| Grenadier | 200 | 0 | 22 | AttackerAI | Mortar attacks |
| GrenadierElite | 300 | 85 | 72 | AttackerAI | Elite grenadier |

### Elysium (Biome 3)

| Enemy | HP | Armor | DiffRating | AI | Notes |
|-------|---:|------:|----------:|----|-------|
| ShadeNakedUnit | 180 | 0 | 12 | AttackerAI | Basic shade |
| ShadeNakedUnitElite | 270 | 70 | 60 | AttackerAI | Elite shade |
| ShadeBowUnit | 150 | 0 | 15 | Attacker+HideAndPeek | Archer |
| ShadeBowUnitElite | 225 | 65 | 65 | Attacker+HideAndPeek | Elite archer |
| ShadeShieldUnit | 200 | 120 | 20 | Attacker+SurroundAI | Shield bearer |
| ShadeShieldUnitElite | 300 | 200 | 72 | Attacker+SurroundAI | Elite shield |
| ShadeSwordUnit | 175 | 0 | 15 | Attacker+SurroundAI | Sword shade |
| ShadeSwordUnitElite | 262 | 70 | 65 | Attacker+SurroundAI | Elite sword |
| ShadeSpearUnit | 190 | 0 | 18 | Attacker+LeapIntoRange | Spear shade |
| ShadeSpearUnitElite | 285 | 75 | 68 | Attacker+LeapIntoRange | Elite spear |
| ShadeGreatShieldUnit | 280 | 250 | 30 | Attacker+RamAI | Greatshield, charges |
| ShadeGreatShieldUnitElite | 420 | 400 | 80 | Attacker+RamAI | Elite greatshield |
| ShadeSniperUnit | 100 | 0 | 18 | Attacker+HideAndPeek | Long-range sniper |
| ShadeSniperUnitElite | 150 | 50 | 65 | Attacker+HideAndPeek | Elite sniper |
| CrystalBeamUnit | 90 | 0 | 18 | PassiveAttack | Continuous beam |
| CrystalBeamUnitElite | 135 | 45 | 65 | PassiveAttack | Elite crystal |
| ShadeChariot | 250 | 150 | 28 | TheseusChariotAI | Patrol chariot |
| ShadeChariotElite | 375 | 250 | 75 | TheseusChariotAI | Elite chariot |

### Styx (Biome 4)

| Enemy | HP | Armor | DiffRating | AI | Notes |
|-------|---:|------:|----------:|----|-------|
| SatyrRanged | 140 | 0 | 40 | AttackerAI | Poison ranged |
| SatyrRangedElite | 210 | 60 | 95 | AttackerAI | Elite poison |
| RatThug | 220 | 0 | 55 | AttackerAI | Rat melee |
| RatThugElite | 330 | 100 | 110 | AttackerAI | Elite rat |
| SatyrCaster | 130 | 0 | 45 | Attacker+HideAndPeek | Satyr mage |
| SatyrCasterElite | 195 | 55 | 100 | Attacker+HideAndPeek | Elite mage |
| SnakeSwarmer | 50 | 0 | 15 | AttackerAI | Small snake |
| SnakeSwarmerElite | 75 | 0 | 50 | AttackerAI | Elite snake |
| RatThugProng | 240 | 0 | 60 | AttackerAI | Pronged rat |
| RatThugProngElite | 360 | 110 | 115 | AttackerAI | Elite pronged |

### Minibosses

| Enemy | HP | Armor | Biome |
|-------|---:|------:|-------|
| WretchAssassin | 600 | 0 | Tartarus |
| SwarmerHelmeted | 900 | 250 | Tartarus |
| HeavyRangedSplitterMiniBoss | 800 | 300 | Asphodel |
| GrenadierMiniBoss | 850 | 280 | Asphodel |
| CrawlerMiniBoss | 430 | 200 | Asphodel |
| ShadeGreatShieldMiniBoss | 900 | 600 | Elysium |
| ShadeSniperMiniBoss | 600 | 200 | Elysium |
| SatyrRangedMiniBoss | 650 | 250 | Styx |
| RatThugMiniBoss | 1100 | 350 | Styx |

### Super-Elites (Hades Fight)

**Large:** BloodlessPitcherSuperElite (400/200), ShadeShieldUnitSuperElite (500/350), CrusherUnitSuperElite (600/250), ShadeGreatShieldUnitSuperElite (550/450)
**Small:** ShadeBowUnitSuperElite (300/150), PunchingBagUnitSuperElite (200/100), SatyrRangedSuperElite (280/120), BloodlessSelfDestructSuperElite (170/80)

---

## AI Behavior Patterns

### AttackerAI (Primary combat AI, line 729)
```
while IsAIActive(enemy):
    SelectWeapon() → GetTargetId() → MoveWithinRange() → AttackOnce() → cooldown → loop
```

### AttackOnce Sequence (line 1360)
```
1. Stop movement, face target
2. Pre-attack telegraph (charge-up animation, PreAttackSound)
3. Fire weapon (FireTicks/FireInterval for multi-hit)
4. Post-attack cooldown (PostAttackDuration)
5. Return to movement
```

### Weapon Selection (SelectWeapon, line 1018)
Priority: Forced weapons → Eligible weapons → Random from eligible

**Force conditions (IsEnemyWeaponForced):**
- ForceWithinPlayerDistance, ForceUnderHealthPercent, ForceIfTypeExists, MaxAttacksBetweenUse

**Eligibility conditions (IsEnemyWeaponEligible):**
- MinAttacksBetweenUse, MaxConsecutiveUses, MaxPlayerDistance, MinPlayerDistance, MaxActiveSpawns, RequireComboPartner, EligibleIfTypeExists, EligibleIfAllTypesDead

### HideAndPeekAI (line 1846) — Ranged enemies
```
Find cover → Move to cover → Wait (HideDuration) → Peek out & attack → Return to cover → loop
```
Used by: LightRanged, Spreader, SatyrCaster, ShadeBowUnit, ShadeSniperUnit

### SurroundAI (line 1922) — Flanking
```
Circle around player → Get behind/beside → Attack when in position
```
Used by: ShadeShieldUnit, ShadeSwordUnit

### LeapIntoRangeAI (line 1965) — Gap closer
```
If player far → Leap to close distance → Immediate attack → Standard loop
```
Used by: ShadeSpearUnit

### RamAILoop (line 2127) — Charging
```
Position at SetupDistance → Telegraph/windup → Charge forward → Hit wall or max dist → Recovery → loop
```
Used by: ShadeGreatShieldUnit

### TheseusChariotAI (line 2207) — Patrol
```
Follow waypoint path → Attack if player in range at waypoints → Loop path
```
Used by: ShadeChariot

### PassiveAttack (line 416) — Stationary periodic
```
Wait (AttackInterval) → Fire weapon (no movement) → loop
```
Used by: Crystals, Brimstones, Spawners, DisembodiedHeads

### Other AI Types
- **FollowAI** (line 38): Follow player at 300 dist, never attack (companions)
- **AggroAI** (line 1740): Wander → detect player → ChainAggro → AttackerAI
- **IdleUntilAggroAI** (line 1708): Idle until damaged, then AttackerAI
- **CollisionRetaliate** (line 273): Attack only when touched (traps)
- **SeekingCollisionRetaliate** (line 366): Move toward player, attack on proximity
- **RemoteAttack** (line 539): Trigger linked enemies (Hydra controller)

---

## Boss Mechanics

### Fury Sisters (End of Tartarus)

**Megaera** — HP: 4,400 (4,800 with shrine). 2 phases.
- Phase 1 (100-50%): Melee + whip + shadow dash
- Phase 2 (<50%): + AoE attacks, summons Snakestones + ShadeSupportUnit
- Weapons: Melee combo, ranged whip, AoE slam, summon adds

**Alecto** — HP: 4,600 (4,900). 2 phases.
- Phase 1: Aggressive melee, rage meter builds
- Phase 2 (<50%): Rage state — faster attacks, larger AoE, red visual

**Tisiphone** — HP: 5,200 (5,600). 2 phases.
- Phase 1: Methodical attacks, hazard zones
- Phase 2 (<50%): Room fills with fog, reduced visibility, teleportation

**Triumvirate** — All three simultaneously, reduced HP each.

### Lernaean Bone Hydra (End of Asphodel)

Main Head HP: 6,000. 3 phases.
- Phase 1 (100-66%): Main head only, bite/slam
- Phase 2 (66-33%): +2 side heads
- Phase 3 (<33%): +3 side heads, more aggressive
- Side head types: Slammer, Spitter, Beamer, Spreader, Tracker
- Main head is Immortal — regenerates, must kill side heads

### Theseus & Asterius (End of Elysium)

**Theseus** — HP: 9,000 (12,000 armored form). 2 phases.
- Phase 1: Spear throws (boomerang), shield block, chariot charges
- Phase 2 (<50%): Calls random Olympian god — arena-wide AoE hazards (Zeus lightning, Poseidon waves, Ares blade rifts, etc.)
- Front-facing shield — must hit from behind

**Asterius** — HP: 14,000 (16,000 rematch). Heavy armor.
- Axe combo (3-hit), Bull Rush (charge), Ground Slam (AoE)
- Can appear as solo miniboss in earlier Elysium rooms

### Hades (Final Boss)

HP: 17,000 (Phase 1), 22,000 total. 2-3 phases.
- Phase 1: Spear combo, spear throw (boomerang), spin attack (360 AoE), skull cast (homing), dash attacks
- Transition: "Dies", dialogue, resurrects with full second health bar
- Phase 2: All Phase 1 + laser sweep, AoE hazard zones, summons super-elites
- Phase 3 (shrine): Even more aggressive + more summons
- Two full health bars — must deplete twice
- Very high MaxHitShields — cannot be interrupted during key animations

### Charon (Optional Secret Boss)

HP: 16,500. 2 phases. Triggered by stealing from shop.
- Phase 1: Oar melee, wave projectiles, AoE slam
- Phase 2 (<50%): Faster + stygian darkness zones
- Rewards large discount item

---

## Encounter System

### Difficulty Budget Algorithm
1. Calculate budget: `BaseDifficulty + (Depth * DepthDifficultyRamp)`
2. Distribute across waves via `WaveDifficultyPatterns`
3. Select `MinTypes` to `MaxTypes` enemy names from biome pool
4. Fill waves — spawn enemies whose DifficultyRating fits budget
5. Apply elite chance: up to `MaxEliteTypes` attributes
6. Enforce `ActiveEnemyCapBase`/`ActiveEnemyCapMax`

### Wave Patterns
```lua
{ 1 }                     -- 1 wave: 100%
{ 0.5, 0.5 }             -- 2 waves: 50/50
{ 0.3, 0.15, 0.55 }      -- 3 waves: ramp to big finale
{ 0.2, 0.2, 0.25, 0.35 } -- 4 waves: escalating
```

### Per-Biome Configuration

| Param | Tartarus | Asphodel | Elysium | Styx |
|-------|----------|----------|---------|------|
| BaseDifficulty | 30 | 170 | 220 | 900 |
| DepthDifficultyRamp | 11 | 25 | 70 | 0 |
| MinWaves | 1 | 1 | 2 | 2 |
| MaxWaves | 2 | 3 | 3 | 3 |
| MinTypes | 1 | 1 | 2 | 2 |
| MaxTypes | 2 | 2 | 2 | 3 |
| MaxEliteTypes | 1 | 2 | 3 | 3 |
| ActiveEnemyCap | 2.3-8 | 2.3-8 | 2.3-8 | 2.3-8 |

Styx: `DepthDifficultyRamp=0` — flat difficulty, short biome. StyxMini: BaseDifficulty=700.

### Special Encounter Types
- **Time Challenge**: Timed encounters with modified difficulty per biome
- **Survival**: Endurance — 45-55 seconds continuous spawning
- **Devotion**: God trial encounters with modified pools
- **Thanatos**: Kill-race encounters for competition scoring
- **Perfect Clear**: No damage taken requirement
- **Wrapping Asphodel**: Scrolling terrain boat encounter
- **Intro Encounters**: First-time teaching encounters for new enemy types
- **Escalation**: UnstableGenerator spawns that create enemies when destroyed

---

## Elite System

### How Elites Work
- +50% HP (approx, defined per variant)
- Armor (HealthBuffer) added
- One random elite attribute from pool
- 3-5x base DifficultyRating cost

### Elite Attributes

| Attribute | Effect | Restriction |
|-----------|--------|-------------|
| Blink | Periodic teleportation | All |
| Frenzy | Increased attack speed | All |
| HeavyArmor | Extra armor | All |
| Molten | Lava pools on death/periodically | Asphodel |
| Homing | Tracking projectiles | Ranged only |
| ExtraDamage | Increased damage | All |
| Vacuuming | Pulls player toward enemy | All |
| Disguise | Appears as weaker enemy until hit | Tartarus |
| Beams | Fires periodic beam attacks | All |
| DeathSpreadHitShields | Spreads stagger resistance on death | All |
| MultiEgg | Splits into multiple enemies on death | Shades only |

### Pact/Shrine Scaling
Shrine modifiers affect encounters:
- **Jury Summons**: +20% enemy count per rank
- **Calisthenics Program**: +15% enemy HP per rank
- **Benefits Package**: More elite types, guaranteed elites
- **Middle Management**: Extra miniboss per biome
- **Forced Overtime**: +20% enemy speed per rank
- **Heightened Security**: Enemies gain armor
- **Damage Control**: Enemies gain hit shields
- **Extreme Measures**: Boss mechanic changes per rank
