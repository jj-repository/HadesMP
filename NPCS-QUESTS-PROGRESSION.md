# Hades NPCs, Quests & Progression

## NPC System (NPCData.lua — 49,227 lines)

### NPC Definition Schema
```lua
NPC_Name_01 = {
    InheritFrom = { "NPC_Neutral", "NPC_Giftable" },
    UseText = "UseTalkToHades",
    Portrait = "Portrait_Hades_Default_01",
    AnimOffsetZ = 270,
    Groups = { "NPCs" },
    Binks = { ... },                     -- video animations
    SubtitleColor = Color.HadesVoice,
    InteractTextLineSets = { ... },      -- dialogue trees (MASSIVE)
    CanReceiveGift = true,
}
```

Base types: `NPC_Neutral` (standard), `NPC_Giftable` (can receive gifts)

### All NPCs

| Key | Line | Character |
|-----|------|-----------|
| NPC_Hades_01 | 1014 | Lord Hades (desk) |
| NPC_Hades_Story_01 | 5259 | Hades (story variant) |
| NPC_Cerberus_01 | 5339 | Cerberus (house) |
| NPC_Cerberus_Field_01 | 6200 | Cerberus (field) |
| NPC_Achilles_01 | 6607 | Achilles (guard post) |
| NPC_Achilles_Story_01 | 10372 | Achilles (story) |
| NPC_Nyx_01 | 10427 | Nyx (house) |
| NPC_Nyx_Story_01 | 14345 | Nyx (story) |
| NPC_Hypnos_01 | 14494 | Hypnos (entrance) |
| NPC_Thanatos_01 | 19424 | Thanatos (house) |
| NPC_Thanatos_Story_01 | 23183 | Thanatos (story) |
| NPC_Thanatos_Field_01 | 23199 | Thanatos (field) |
| NPC_Skelly_01 | 24653 | Skelly (courtyard) |
| NPC_Dusa_01 | 24683 | Dusa (house) |
| NPC_Charon_01 | 29618 | Charon (shops) |
| NPC_Orpheus_01 | 30413 | Orpheus (court) |
| NPC_Orpheus_Story_01 | 32821 | Orpheus (story) |
| NPC_FurySister_01 | 33878 | Megaera (house) |
| NPC_FurySister_Story_01 | 37255 | Megaera (story) |
| NPC_Sisyphus_01 | 37332 | Sisyphus (Tartarus) |
| NPC_Bouldy_01 | 39673 | Bouldy (boulder) |
| NPC_Patroclus_01 | 40207 | Patroclus (Elysium) |
| NPC_Eurydice_01 | 43095 | Eurydice (Asphodel) |
| NPC_Persephone_01 | 45350 | Persephone (surface) |
| NPC_Persephone_Home_01 | 46767 | Persephone (house) |

### Dialogue System (InteractTextLineSets)

Each NPC has massive dialogue tables. Each dialogue set:
```lua
DialogueName = {
    PlayOnce = true,
    RequiredMinCompletedRuns = 1,
    RequiredTextLines = { "SomeDialogue01" },
    RequiredFalseTextLines = { "Ending01" },
    RequiredMinNPCInteractions = { NPC_Hades_01 = 2 },
    { Cue = "/VO/Hades_0008", Text = "Well that was quick..." },
    { Cue = "/VO/ZagreusHome_0015", Portrait = "Portrait_Zag_Defiant_01",
      Speaker = "CharProtag", Text = "..." },
}
```

**Dialogue conditions:**
- RequiredTextLines / RequiredFalseTextLines — dialogue chain gating
- RequiredMinCompletedRuns / RequiredMaxDepth — progression gates
- RequiredMinNPCInteractions — minimum chat counts
- RequiredKills / RequiredAnyKillsThisRun — enemy defeat requirements
- RequiredTrueFlags / RequiredFalseFlags — boolean state flags
- RequiredSeenRooms — biome progression
- RequiredTextLinesThisRun / RequiredFalseTextLinesThisRun — current-run conditions

### House NPC Spawning (DeathLoopData.lua)

Each return to House randomly activates NPCs:
```lua
NPCsOnStart = {
    {
        FunctionName = "ActivateRandomPrePlaced",
        Args = {
            Names = { "NPC_Hypnos_01", "NPC_Nyx_01", "NPC_Achilles_01",
                      "NPC_Dusa_01", "NPC_Orpheus_01", "NPC_FurySister_01", "NPC_Thanatos_01" },
            ActivationCapMin = 4,
            ActivationCapMax = 6,
        },
    },
    -- Force-spawn for quests
    { FunctionName = "ActivateAnyPrePlaced", Args = { Ids = { 370010, 390082 } },
      GameStateRequirements = { RequiredTextLinesThisRun = "Ending01" } },
}
```

---

## Quest System (QuestData.lua — 2,551 lines)

### Schema
```lua
QuestName = {
    InheritFrom = { "DefaultQuestItem" },
    RewardResourceName = "Gems",
    RewardResourceAmount = 200,
    UnlockGameStateRequirements = { ... },   -- when quest appears
    CompleteGameStateRequirements = { ... },  -- when quest fulfilled
}
```

### Complete Quest List (56 quests)

**Weapon Mastery (6):** Use all Daedalus upgrades per weapon
- SwordHammerUpgrades, BowHammerUpgrades, ShieldHammerUpgrades, SpearHammerUpgrades, FistHammerUpgrades, GunHammerUpgrades (200 gems each, 12 traits)

**God Boon Collection (9):** Collect all boons from each Olympian (150 gems each)
- AthenaUpgrades, ZeusUpgrades, ArtemisUpgrades, AphroditeUpgrades, AresUpgrades, PoseidonUpgrades, DionysusUpgrades, HermesUpgrades, DemeterUpgrades

**Special Boon (3):**
- LegendaryUpgrades — all legendary boons (150 gems)
- SynergyUpgrades — all duo boons (150 gems)
- ChaosBlessings / ChaosCurses — all Chaos boons/curses (150 gems each)

**Progression:**
- FirstClear — escape once (1000 Darkness)
- MeetOlympians / MeetChthonicGods (150 gems each)
- WeaponUnlocks — unlock all 6 weapons (300 gems)
- WeaponClears — clear with each weapon (500 gems)
- WeaponAspects — reveal all aspects
- WeaponClearsHighHeat — clear at 8+ heat per weapon (SuperLockKeys)
- KeepsakesQuest — obtain all keepsakes (150 gems)

**Story/Character:**
- EpilogueSetUp / OlympianReunion — the epilogue
- NyxChaosReunion — reunite Nyx and Chaos
- SisyphusLiberation — free Sisyphus
- OrpheusRelease / OrpheusEurydiceReunion
- AchillesPatroclusReunion_A/_B/_C
- DusaLoungeRenovation
- SkellyTrueDeath / SkellyTrueDeath_B

**Combat:** MiniBossKills, EliteAttributeKills

**Hidden Aspect Escapes (6):** Clear with each hidden aspect
- GuanYuAspectEscape, ArthurAspectEscape, RamaAspectEscape, BeowulfAspectEscape, GilgameshAspectEscape, LuciferAspectEscape

---

## Death Loop / Meta Progression

### Death Handling (DeathLoop.lua)

`KillHero()` → `HandleDeath()`:
1. Increment EasyModeLevel if God Mode enabled
2. Record run stats, invalidate checkpoint
3. Zero super meter
4. Reset money to 0
5. Reset rerolls to Mirror base amount
6. Load "DeathArea" map (House of Hades)

`StartDeathLoop()` — plays boat return or blood pool return animation
`SetupDeathArea()` — runs house events, assigns obstacles, starts triggers

### House Systems (DeathLoopData.lua — 10,070 lines)

**Employee of the Month:** Rotating display showing NPC portraits
- Options: Thanatos, Megaera, Cerberus, Achilles, Orpheus, HouseContractor, WretchedBroker, HeadChef, Dusa, Hypnos, Zagreus
- Zagreus portrait requires: `OlympianReunionQuestComplete`

**Flashback System:**
- Flashback 1: 150+ accumulated MetaPoints, 5+ completed runs
- Flashback 2: 26+ completed runs, seen Flashback 1

**Bedroom Encounters:** Romance scenes with Megaera/Thanatos, gated by gift progress
- Meg: requires killing a Fury + MegaeraGift04

**Skelly Trophy Statues:**
- Bronze: clear at 8 total heat
- Silver: clear at 16 total heat
- Gold: clear at 32 total heat

---

## Mirror of Night (MetaUpgradeData.lua)

Purchased with Darkness. Each slot has A/B paired alternatives:

| Slot | Upgrade A | Upgrade B |
|------|-----------|-----------|
| 1 | Shadow Presence (+10% backstab) | Fiery Presence (+15% first-hit) |
| 2 | Dark Regeneration (+1 HP/door) | Chthonic Vitality (+30% darkness heal) |
| 3 | Death Defiance (+1 extra life) | Stubborn Defiance (1 replenishing life at 30% HP) |
| 4 | Greater Reflex (+1 dash) | Ruthless Reflex (+50% dmg after close dash) |
| 5 | Boiling Blood (+10% dmg per lodged cast) | Abyssal Blood (-6% speed/dmg per lodged cast) |
| 6 | Infernal Soul (+1 cast ammo) | Stygian Soul (-1s auto-retrieve cast) |
| 7 | Deep Pockets (+10 gold/level) | Golden Touch (+5% gold interest/room) |
| 8 | Thick Skin (+5 max HP/level) | High Confidence (+5% dmg above 80% HP) |
| 9 | Privilege Status (+20% per 2 curses) | Family Favorite (+2.5% per unique god) |
| 10 | Rare Drop (+1% rare/level) | Olympian Favor (+2% bonus/level) |
| 11 | Epic Drop (+1% epic/level) | Duo Drop (+1%/level) |
| 12 | Fated Authority (+1 reroll/level) | Fated Persuasion (+1 boon reroll/level) |

**Unlock:** First 4 pairs start unlocked. 2 more sets require Chthonic Keys (costs: 5, 10, 20, 30).

---

## Pact of Punishment (Heat System)

| Modifier | Max Rank | Heat/Rank | Effect |
|----------|----------|-----------|--------|
| Hard Labor | 5 | 1 | +20% enemy damage |
| Lasting Consequences | 4 | 1 | +25% heal reduction |
| Convenience Fee | 2 | 1 | +40% shop prices |
| Jury Summons | 3 | 1 | +20% enemy count |
| Extreme Measures | 4 | 1-4 | Boss enhancements |
| Calisthenics Program | 2 | 1 | +15% enemy health |
| Benefits Package | 2 | 2-3 | Elite bonuses |
| Middle Management | 1 | 2 | Extra minibosses |
| Underworld Customs | 1 | 2 | Lose boon each biome |
| Forced Overtime | 2 | 3 | +20% enemy speed |
| Damage Control | 1 | 1 | Traps 5x damage |
| Approval Process | 4 | 2 | -3 Mirror ranks/level |
| Tight Deadline | 3 | 1-3 | Biome time limits |
| Routine Inspection | 2 | 2-3 | -1 boon choice/level |
| Enemy Shields | 2 | 1 | Enemy shields |
| Personal Liability | 1 | 1 | Remove i-frames (HardMode) |

**Biome Time Limits (Tight Deadline):**
- Rank 1: 9 min/biome, Rank 2: 7 min, Rank 3: 5 min
- Penalty: 5 damage/second after time expires

**Extreme Measures rank 4:** Requires cosmetic `HadesEMFight` from House Contractor

---

## Gift / Keepsake System (GiftData.lua — 474 lines)

**Currencies:** GiftPoints (Nectar) for hearts 1-6, SuperGiftPoints (Ambrosia) for locked hearts 7+.

### Keepsake Order

**Row 1 (Chthonic):**
1. MaxHealthKeepsakeTrait (Cerberus)
2. DirectionalArmorTrait (Achilles)
3. BackstabAlphaStrikeTrait (Nyx)
4. PerfectClearDamageBonusTrait (Thanatos)
5. ShopDurationTrait (Charon)
6. BonusMoneyTrait (Hypnos)
7. LowHealthDamageTrait (Megaera)
8. DistanceDamageTrait (Orpheus)
9. LifeOnUrnTrait (Dusa)
10. ReincarnationTrait (Skelly)

**Row 2 (Olympian):**
11-19. ForceZeus/Poseidon/Athena/Aphrodite/Ares/Artemis/DionysousBoonTrait
20. FastClearDodgeBonusTrait (Hermes)
21. ForceDemeterBoonTrait
22. ChaosBoonTrait

**Row 3:**
23. VanillaTrait (Sisyphus), ShieldBossTrait (Eurydice), ShieldAfterHitTrait (Patroclus), ChamberStackTrait (Persephone), HadesShoutKeepsake (Hades)

### Companions (6)
FuryAssistTrait, ThanatosAssistTrait, SisyphusAssistTrait, SkellyAssistTrait, DusaAssistTrait, AchillesPatroclusAssistTrait

Upgrade costs: 1, 2, 3, 4, 5 Ambrosia per level (5 levels)

### Per-NPC Gift Data
- Default: Max 8 hearts, locked at 5
- Gods: Max 7, locked at 5
- Megaera: Max 10, locked at 7 (companion at heart 7, bond requires bedroom scene)
- Hades: Max 5, locked at 2
- Bouldy: Locked at 11, `InfiniteGifts = true`

---

## Codex System (CodexData.lua — 2,343 lines)

### Categories
ChthonicGods, OlympianGods, OtherDenizens, Biomes, Weapons, Enemies, Items, Fish, Keepsakes

### Entry Structure
```lua
CodexData = {
    NPC_Hades_01 = {
        [1] = { UnlockThreshold = 1, Entries = { { ... } } },  -- chapter 1
        [2] = { UnlockThreshold = 5, Entries = { { ... } } },  -- chapter 2
        [3] = { UnlockThreshold = 10, Entries = { { ... } } }, -- chapter 3
    },
}
```
UnlockThreshold = interactions/encounters needed to unlock chapter.

---

## Achievements (39 total)

Key achievements: AchClearAnyRun, AchReachedEnding (text "Ending01"), AchReachedEpilogue (OlympianReunionQuestComplete), AchFoundKeepsakes (25), AchLeveledKeepsakes (all max), AchFoundAllSummons (6), AchPickedManyBoons (100 unique), AchPickedManyHammers (50 unique), AchMirrorAllUnlocked, AchWeaponClears (all 6), AchCerberusPets (10 times), AchBuffedButterfly (1.296x bonus), AchWellShopItems (9 in one run).

Checked every 0.3 seconds via `CheckProgressAchievements()`.

---

## Store System

### Well of Charon (Mid-Run Shops)
MaxOffers = 3. One guaranteed healing, rest from pool of 14 temporary traits + consumables.

### Charon's Shop (Between Biomes)
Three weighted groups offering BlindBoxLoot, RandomLoot, resources, meta drops.

### Styx Final Shop (D_WorldShop)
6 offers across 4 groups. Includes HermesUpgrade (500) and ChaosWeaponUpgrade (650).

### Wretched Broker (Resource Exchange)
**Standard (always):** Gems→Keys, Keys→Nectar, Nectar→Diamonds, Diamonds→Ambrosia, Ambrosia→Titan Blood
**Rotating (1 at a time):** Various cross-currency trades, gated by boss kills

---

## Fishing System (FishingData.lua)

### Mechanics
- 0-3 fake bobs before real bite
- Good window: 0.34s, Perfect window: 0.34s
- Give up: 3s, Way late: 1s

### Fish by Biome

| Biome | Common | Rare | Legendary |
|-------|--------|------|-----------|
| Tartarus | Hellfish (5 gems) | Knucklehead (20 gems) | Scyllascion (30 gems) |
| Asphodel | Slavug (1 key) | Chrustacean (3 keys) | Flameater (5 keys) |
| Elysium | Chlam (1 nectar) | Charp (2 nectar) | Seamare (3 nectar) |
| Styx | Gupp (20 gems) | Scuffer (40 gems) | Stonewhal (150 gems) |
| Chaos | Mati (100 dark) | Projelly (250 dark) | Voidskate (500 dark) |
| Surface | Trout (1 diamond) | Bass (1 ambrosia) | Sturgeon (1 titan blood) |

**Catch rates:** Good timing → Common + 4.76% Rare. Perfect timing → Rare + 4.76% Legendary.

---

## Conditional Items / House Contractor (ConditionalItemData.lua — 5,861 lines)

### Cosmetic Tiers (gated by total purchased)
Tier D: 7, Tier C: 14, Tier B: 24, Tier A: 44, Tier S: 54

### UI Theme Skins
Default, Artemis, Hades, Heat, Love, Chthonic, Stone, Chaos, Orphic — each changes TraitBacking, ShrineUpgradeBacking, MetaUpgradeBacking, etc.

### Cosmetic Categories
- Bedroom: Posters, daggers, water bowl, lyre, bed upgrades
- North Hall: Mirror, couch, rugs, paintings, pedestals, sundial
- Lounge: Dusa renovation items
- Garden: Post-ending garden items

Each purchase triggers Zagreus and Hades voice line reactions.
