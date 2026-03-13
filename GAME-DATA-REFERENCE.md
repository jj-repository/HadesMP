# Hades Game Data Reference

## Data Architecture

All game data uses Lua tables with inheritance (`InheritFrom`). Key design patterns:

### PropertyChanges (how traits modify gameplay)
```lua
PropertyChanges = {
    {
        WeaponName = "SwordWeapon",
        ProjectileProperty = "DamageLow",
        BaseMin = 20, BaseMax = 20,
        ChangeType = "Add",                              -- Add, Multiply, or Absolute
        IdenticalMultiplier = { Value = -0.60 },          -- pom diminishing returns
        ExtractValue = { ExtractAs = "TooltipDamage" },   -- display binding
    },
}
```

### Global Constants
- `DuplicateMultiplier = -0.60` — standard pom scaling (40% retention per level)
- `DuplicateStrongMultiplier = -0.40` — strong scaling (60% retention)
- `DuplicateVeryStrongMultiplier = -0.20` — best scaling (80% retention)

### WeaponSets (referenced in PropertyChanges)
- `HeroPhysicalWeapons` — all melee attack weapons + dash variants
- `HeroNonPhysicalWeapons` — cast weapons (RangedWeapon etc.)
- `HeroRushWeapons` — dash weapons
- `HeroSecondaryWeapons` — special attack weapons

### Trait Slots
Melee (Attack), Secondary (Special), Ranged (Cast), Rush (Dash), Shout (Call), Keepsake, Assist (Companion). One trait per slot.

---

## Hero Stats (HeroData.lua)

| Stat | Value |
|------|-------|
| MaxHealth | 50 |
| DefaultWeapon | SwordWeapon |
| Super DamageDealtMultiplier | 0.01 (wrath per damage dealt) |
| Super DamageTakenMultiplier | 60 (wrath per damage taken) |
| Rally ConversionPercent | 1.0 (100%) |
| Rally DecayRateSeconds | 1.3 |
| InvulnerableFrameDuration | 1.3s |
| InvulnerableFrameMinDamage | 10 |
| InvulnerableFrameThreshold | 0.25 (25% of MaxHealth) |
| God Mode Base | 0.8 (20% DR) |
| God Mode Per Death | -0.02 (2% more DR) |
| God Mode Cap | 0.20 multiplier (80% DR at 30 deaths) |

---

## Weapons (WeaponData.lua)

### The 6 Infernal Arms

| Weapon | Internal | Unlock Cost | Dash | Special |
|--------|----------|-------------|------|---------|
| Stygius (Sword) | SwordWeapon | 0 (default) | SwordWeaponDash | SwordWeapon3 (combo finisher) |
| Varatha (Spear) | SpearWeapon | 4 keys | SpearWeaponDash | SpearWeaponThrow |
| Aegis (Shield) | ShieldWeapon | 3 keys | ShieldWeaponDash | ShieldThrow |
| Coronacht (Bow) | BowWeapon | 1 key | BowWeaponDash | BowSplitShot |
| Exagryph (Gun) | GunWeapon | 8 keys | GunWeaponDash | GunGrenadeToss |
| Malphon (Fists) | FistWeapon | 8 keys | FistWeaponDash | FistWeaponSpecial |

**Attack Chains:**
- Sword: SwordWeapon → SwordWeapon2 → SwordWeapon3 (overhead finisher)
- Spear: SpearWeapon → SpearWeapon2 → SpearWeapon3 + SpearWeaponSpin (charged)
- Shield: ShieldWeapon (bash) + ShieldWeaponRush (Bull Rush, hold attack)
- Bow: BowWeapon (charged shot) + charge mechanic
- Gun: Rapid fire + ReloadDelay 0.2s + ActiveReloadTime 0.75s + SniperGunWeapon variants
- Fists: Rapid combo chain

**Cast (Universal):** RangedWeapon, StoreAmmoOnHit=1, AmmoDropDelay=16s, base MaxAmmo=1

### Weapon Aspects (WeaponUpgradeData.lua)

| Weapon | Zagreus | Aspect 2 | Aspect 3 | Hidden Aspect |
|--------|---------|----------|----------|---------------|
| Sword | SwordBaseUpgradeTrait | Nemesis (SwordCriticalParryTrait) | Poseidon (DislodgeAmmoTrait) | Arthur (SwordConsecrationTrait) |
| Spear | SpearBaseUpgradeTrait | Achilles (SpearTeleportTrait) | Hades (SpearWeaveTrait) | Guan Yu (SpearSpinTravel) |
| Shield | ShieldBaseUpgradeTrait | Chaos (ShieldRushBonusProjectileTrait) | Zeus (ShieldTwoShieldTrait) | Beowulf (ShieldLoadAmmoTrait) |
| Bow | BowBaseUpgradeTrait | Chiron (BowMarkHomingTrait) | Hera (BowLoadAmmoTrait) | Rama (BowBondTrait) |
| Gun | GunBaseUpgradeTrait | Eris (GunGrenadeSelfEmpowerTrait) | Hestia (GunManualReloadTrait) | Lucifer (GunLoadedGrenadeTrait) |
| Fists | FistBaseUpgradeTrait | Talos (FistVacuumTrait) | Demeter (FistWeaveTrait) | Gilgamesh (FistDetonateTrait) |

**Costs (Titan Blood):** Zagreus: 5 (1x5), Aspect 2: 15 (1+2+3+4+5), Aspect 3: 16 (2+2+3+4+5), Hidden: 15 (3x5). Per weapon: 51. All weapons: 306.

**Hidden Aspect Revealers:**
| Weapon | Aspect | NPC | Required Text |
|--------|--------|-----|---------------|
| Sword | Arthur | Nyx | NyxRevealsArthurAspect01 |
| Spear | Guan Yu | Achilles | AchillesRevealsGuanYuAspect01 |
| Shield | Beowulf | Chaos | ChaosRevealsBeowulfAspect01 |
| Bow | Rama | Artemis | ArtemisRevealsRamaAspect01 |
| Gun | Lucifer | Zeus | ZeusRevealsLuciferAspect01 |
| Fists | Gilgamesh | Asterius | MinotaurRevealsGilgameshAspect01 |

---

## Rarity System

### Standard Boons (ShopTier1Trait)
| Rarity | Min Mult | Max Mult |
|--------|----------|----------|
| Common | 1.00 | 1.00 |
| Rare | 1.30 | 1.50 |
| Epic | 1.80 | 2.00 |
| Heroic | 2.30 | 2.50 |

### Strong Boons (ShopTier2Trait)
| Rarity | Min Mult | Max Mult |
|--------|----------|----------|
| Common | 1.00 | 1.00 |
| Rare | 1.30 | 1.50 |
| Epic | 2.00 | 2.50 |
| Heroic | 2.50 | 2.70 |

### Other Types
- **Legendary (ShopTier3Trait):** Fixed 1.0x, no scaling
- **Duo (SynergyTrait):** Fixed 1.0x, IsDuoBoon=true, Frame="Duo"
- **Keepsake (GiftTrait):** Common 1.0x → Rare 1.5x (25 encounters) → Epic 2.0x (50 encounters)
- **Companion (AssistTrait):** Levels 1-5 at 1.0x-5.0x
- **Chaos Blessing:** Common 1.0x, Rare 1.5x, Epic 2.0x
- **Daedalus Hammer:** Levels 1-5 at 1.0x-5.0x

---

## God Boon Pools (LootData.lua)

### Zeus (ZeusUpgrade)

**Slot Boons:**
| Trait | Slot | Name | Base Effect |
|-------|------|------|-------------|
| ZeusWeaponTrait | Melee | Lightning Strike | Chain lightning 10 dmg |
| ZeusSecondaryTrait | Secondary | Thunder Flourish | Chain lightning on special |
| ZeusRangedTrait | Ranged | Electric Shot | Chain lightning cast |
| ZeusRushTrait | Rush | Thunder Dash | Lightning AoE 10 dmg |
| ZeusShoutTrait | Shout | Zeus' Aid | Lightning bolt barrage |

**Passives:** RetaliateWeaponTrait (Heaven's Vengeance), SuperGenerationTrait (Billowing Strength), OnWrathDamageBuffTrait (Clouded Judgment), PerfectDashBoltTrait (Lightning Reflexes)

**Legendary:** ZeusChargedBoltTrait (Splitting Bolt) — all lightning spawns secondary sparks, 40 dmg

### Athena (AthenaUpgrade)

**Slot Boons:**
| Trait | Slot | Name | Base Effect |
|-------|------|------|-------------|
| AthenaWeaponTrait | Melee | Divine Strike | Deflect + bonus damage |
| AthenaSecondaryTrait | Secondary | Divine Flourish | Deflect on special |
| AthenaRangedTrait | Ranged | Phalanx Shot | Cast deflects |
| AthenaRushTrait | Rush | Divine Dash | Dash deflects |
| AthenaShoutTrait | Shout | Athena's Aid | Brief invulnerability |

**Passives:** TrapDamageTrait (Bronze Skin), EnemyDamageTrait (Holy Shield), AthenaRetaliateTrait (Proud Bearing), PreloadSuperGenerationTrait (Deathless Stand)

**Legendary:** ShieldHitTrait (Divine Protection) — auto-activating shield, 20s cooldown

### Poseidon (PoseidonUpgrade)

**Slot Boons:**
| Trait | Slot | Name | Base Effect |
|-------|------|------|-------------|
| PoseidonWeaponTrait | Melee | Tempest Strike | Knockback + 30% damage |
| PoseidonSecondaryTrait | Secondary | Tempest Flourish | Knockback on special |
| PoseidonRangedTrait | Ranged | Flood Shot | Knockback cast |
| PoseidonRushTrait | Rush | Tidal Dash | Knockback wave |
| PoseidonShoutTrait | Shout | Poseidon's Aid | Surf slam |

**Passives:** RoomRewardBonusTrait (Ocean's Bounty), DefensiveSuperGenerationTrait (Sunken Treasure), EncounterStartOffenseBuffTrait (Typhoon's Fury)

**Legendaries:** DoubleCollisionTrait (Second Wave) — double knockback; FishingTrait (Huge Catch) — fishing everywhere

### Artemis (ArtemisUpgrade)

**Slot Boons:** ArtemisWeaponTrait (Deadly Strike), ArtemisSecondaryTrait (Deadly Flourish), ArtemisRangedTrait (True Shot — homing), ArtemisRushTrait (Hunter Dash), ArtemisShoutTrait (Artemis' Aid — homing arrows)

**Passive:** CritBonusTrait (Pressure Points) — global crit chance

**Legendary:** MoreAmmoTrait (Fully Loaded) — +2 max bloodstones

### Aphrodite (AphroditeUpgrade)

**Slot Boons:** AphroditeWeaponTrait (Heartbreak Strike — Weak), AphroditeSecondaryTrait (Heartbreak Flourish), AphroditeRangedTrait (Crush Shot), AphroditeRushTrait (Passion Dash), AphroditeShoutTrait (Aphrodite's Aid — Charm burst)

**Passives:** AphroditeRetaliateTrait (Wave of Despair), AphroditeDeathTrait (Dying Lament), ProximityArmorTrait (Different League), HealthRewardBonusTrait (Life Affirmation — +30% Centaur Heart HP)

**Legendary:** CharmTrait (Unhealthy Fixation) — 15% chance Weak→Charm for 4s

### Ares (AresUpgrade)

**Slot Boons:** AresWeaponTrait (Curse of Agony — Doom 50 dmg), AresSecondaryTrait (Curse of Pain), AresRangedTrait (Slicing Shot — Blade Rift), AresRushTrait (Blade Dash), AresShoutTrait (Ares' Aid — become Blade Rift)

**Passives:** AresRetaliateTrait (Curse of Vengeance), IncreasedDamageTrait (Black Metal), OnEnemyDeathDamageInstanceBuffTrait (Battle Rage), LastStandDamageBonusTrait (Blood Frenzy)

**Legendary:** AresCursedRiftTrait (Vicious Cycle) — Blade Rift +2 dmg per consecutive hit

### Dionysus (DionysusUpgrade)

**Slot Boons:** DionysusWeaponTrait (Drunken Strike — Hangover DoT), DionysusSecondaryTrait (Drunken Flourish), DionysusRangedTrait (Trippy Shot — Festive Fog), DionysusRushTrait (Drunken Dash), DionysusShoutTrait (Dionysus' Aid)

**Passives:** DoorHealTrait (Premium Vintage), LowHealthDefenseTrait (After Party), FountainDamageBonusTrait (Bad Influence)

**Legendary:** DionysusComboVulnerability (Black Out) — +60% damage to enemies with Hangover AND Festive Fog

### Demeter (DemeterUpgrade)

**Slot Boons:** DemeterWeaponTrait (Frost Strike — Chill), DemeterSecondaryTrait (Frost Flourish), DemeterRangedTrait (Crystal Beam — laser), DemeterRushTrait (Mistral Dash), DemeterShoutTrait (Demeter's Aid)

**Passives:** CastNovaTrait (Arctic Blast), ZeroAmmoBonusTrait (Glacial Glare), DemeterRetaliateTrait (Frozen Touch)

**Legendary:** InstantChillKill (Killing Freeze) — instant kill Chilled enemies below 10% HP

### Hermes (HermesUpgrade)

**NO slot boons.** All passives:
- HermesWeaponTrait (Swift Strike), HermesSecondaryTrait (Swift Flourish)
- MoveSpeedTrait (Hyper Sprint), RushSpeedBoostTrait (Greater Haste)
- BonusDashTrait (Greater Evasion — +1/2/3/4 dashes by rarity)
- DodgeChanceTrait (Second Wind), RapidCastTrait (Quick Reload)
- RushRallyTrait (Rush Delivery), AmmoReloadTrait (Auto Reload)
- AmmoReclaimTrait (Quick Recovery), ChamberGoldTrait (Side Hustle)
- RegeneratingSuperTrait (Quick Favor), HermesShoutDodge (Greatest Reflex)

**Legendaries (3):** MagnetismTrait (Auto Collect — bloodstones auto-return), UnstoredAmmoDamageTrait (Billowing Blow — +50% dmg no lodged stones), HermesRushAreaSlow (Bad News — enemies slowed after dash)

---

## Duo Boons (34 total)

| Duo | Gods | Name | Effect |
|-----|------|------|--------|
| LightningCloudTrait | Zeus+Dionysus | Scintillating Feast | Festive Fog strikes lightning (60 dmg, 0.85s interval) |
| AutoRetaliateTrait | Zeus+Ares | Vengeful Mood | Auto-retaliate on timer (range 300, 3s interval) |
| CriticalBoltTrait | Artemis+Zeus | Lightning Rod | Crit fires lightning from victim (20 dmg) |
| ImpactBoltTrait | Poseidon+Zeus | Sea Storm | Knockback fires lightning (40 dmg) |
| ReboundingAthenaCastTrait | Zeus+Athena | Lightning Phalanx | Athena cast bounces (3 jumps, 450 range) |
| JoltDurationTrait | Demeter+Zeus | Cold Fusion | Jolted lasts 10 seconds |
| RegeneratingCappedSuperTrait | Zeus+Aphrodite | Smoldering Air | Auto-fill wrath (capped at 25%) |
| CurseSickTrait | Ares+Aphrodite | Curse of Longing | Doom refreshes Weak at 50% |
| TriggerCurseTrait | Athena+Ares | Merciful End | Deflect triggers Doom (+40 bonus) |
| AresHomingTrait | Artemis+Ares | Hunting Blades | Blade Rift homes on enemies |
| StationaryRiftTrait | Ares+Demeter | Freezing Vortex | Blade Rift inflicts Chill |
| PoisonTickRateTrait | Dionysus+Ares | Curse of Nausea | Hangover ticks at 0.35s (much faster) |
| PoseidonAresProjectileTrait | Poseidon+Ares | Curse of Drowning | Cast orbits player |
| ImprovedPomTrait | Aphrodite+Poseidon | Sweet Nectar | Pom gives +1 bonus level |
| RaritySuperBoost | Dionysus+Poseidon | Exclusive Access | All boons Epic minimum |
| SlowProjectileTrait | Dionysus+Athena | Stubborn Roots | Enemy projectiles halved speed |
| StatusImmunityTrait | Poseidon+Athena | Unshakable Mettle | Full status immunity + 10% boss DR |
| NoLastStandRegenerationTrait | Demeter+Athena | Stubborn Roots | Regen HP when no DD remain (1 HP/0.8s) |
| ArtemisReflectBuffTrait | Artemis+Athena | Deadly Reversal | +20% crit for 2s after deflect |
| HeartsickCritDamageTrait | Artemis+Aphrodite | Heart Rend | +150% crit damage to Weak targets |
| DionysusAphroditeStackIncreaseTrait | Dionysus+Aphrodite | Low Tolerance | +3 Hangover stacks when enemy Weak |
| PoisonCritVulnerabilityTrait | Dionysus+Artemis | Hunter's Mark | +1.5% crit per Hangover stack |
| HomingLaserTrait | Demeter+Artemis | Crystal Clarity | Demeter laser homes +10% dmg |
| MultiLaserTrait | Aphrodite+Demeter | Blizzard Shot | Demeter cast fires 3 beams |
| SelfLaserTrait | Aphrodite+Demeter | Cold Fusion | Demeter cast locks to player +30% dmg |
| BlizzardOrbTrait | Poseidon+Demeter | Blizzard Shot | Cast becomes slow orb spawning ice (20 dmg shards) |
| IceStrikeArrayTrait | Demeter+Dionysus | Ice Wine | Festive Fog instant + Chill +30% |

### Duo Requirements Pattern
Each duo needs `OneFromEachSet` — one trait from God A's pool AND one from God B's pool. See LootData.lua LinkedUpgrades for exact trait lists.

---

## Status Effects

| Effect | God | Internal Name | Description |
|--------|-----|---------------|-------------|
| Doom | Ares | DelayedDamage | Delayed damage burst |
| Hangover | Dionysus | DamageOverTime | Stacking DoT |
| Chill | Demeter | DemeterSlow | Slows enemy actions |
| Weak | Aphrodite | ReduceDamageOutput | Reduces enemy damage |
| Jolted | Zeus | ZeusAttackPenalty | Damage on enemy's next attack |
| Charm | Aphrodite (legendary) | Charm | Enemy fights for you |
| Festive Fog | Dionysus (cast) | WinePuddleVulnerability | Vulnerability marker |
| Styx Poison | Styx enemies | StyxPoison | Damage over time |

---

## Consumables (ConsumableData.lua)

### Health/Resources
| Name | Internal | Effect |
|------|----------|--------|
| Health Restore | HealDropRange | 21-39% of max HP |
| Centaur Heart | RoomRewardMaxHealthDrop | +25 max HP, cost 125 |
| Nectar | GiftDrop | +1 GiftPoints, cost 200 |
| Ambrosia | SuperGiftDrop | +1 SuperGiftPoints, cost 1100 |
| Chthonic Key | LockKeyDrop | +1, cost 50 |
| Titan Blood | SuperLockKeyDrop | +1, cost 1200 |
| Diamond | SuperGemDrop | +1, cost 1000 |
| Gemstone | GemDrop | +5, cost 50 |
| Death Defiance | LastStandDrop | +1 DD, heal 50%, cost 200 |
| Anvil of Fates | ChaosWeaponUpgrade | Swap hammer upgrades, cost 275 |

---

## Mutually Exclusive Traits
- HomingLaserTrait / SelfLaserTrait / MultiLaserTrait (Demeter cast mods)
- BlizzardOrbTrait / PoseidonAresProjectileTrait / IceStrikeArrayTrait (cast reworks)
- MagnetismTrait / UnstoredAmmoDamageTrait (Hermes legendaries)
- AresHomingTrait / StationaryRiftTrait (Ares cast mods)

---

## How to Add a New Boon (Modding Pattern)

1. Define in TraitData.lua with InheritFrom (`ShopTier1Trait`/`2`/`3`/`SynergyTrait`)
2. Set metadata: God, Slot, Icon, RarityLevels
3. Define PropertyChanges targeting weapons/projectiles/effects
4. Add trait name to god's pool in LootData.lua (WeaponUpgrades or Traits array)
5. For duo: add LinkedUpgrades with OneFromEachSet
6. For legendary: add LinkedUpgrades with OneOf

### PropertyChanges Templates

**Damage addition:**
```lua
{ WeaponName = "SwordWeapon", ProjectileProperty = "DamageLow",
  BaseMin = 20, BaseMax = 20, ChangeType = "Add",
  IdenticalMultiplier = { Value = DuplicateMultiplier } }
```

**Damage multiplier:**
```lua
AddOutgoingDamageModifiers = {
    ValidWeaponMultiplier = { BaseValue = 1.30, SourceIsMultiplier = true },
    ValidWeapons = WeaponSets.HeroPhysicalWeapons,
}
```

**Status effect activation:**
```lua
{ WeaponNames = WeaponSets.HeroPhysicalWeapons,
  EffectName = "DemeterSlow", EffectProperty = "Active", ChangeValue = true }
```
