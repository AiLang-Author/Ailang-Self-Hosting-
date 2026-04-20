# Battle System - Quick Reference

## What It Replaces

| Before | After |
|--------|-------|
| Auto-combat (attack/counter) | Full turn-based menu |
| Simple messages | Battle log with history |
| No defend option | Defend halves damage |
| No spell casting | Full spell menu |
| No item use in battle | Use potions/scrolls |
| No flee option | Flee based on AGI |

---

## Battle Screen Layout

```
            === BATTLE ===

+----------------------------+    +----------------------------+
|        Goblin              |    |  Hero                      |
|                            |    |  Warrior Lv.5              |
|          ,---.             |    |                            |
|         / oo  \            |    |  HP: [=========    ] 45/52 |
|        (  ><   )           |    |  MP: 12 / 20               |
|         \    /             |    |                            |
|          `--'              |    |                            |
|                            |    +----------------------------+
|  HP: [=======     ] 8/12   |    +----------------------------+
+----------------------------+    | Command:                   |
                                  |   > Attack                 |
--- Battle Log ---                |     Defend                 |
A wild enemy appears!             |     Cast                   |
You attack!                       |     Item                   |
Enemy takes damage!               |     Flee                   |
                                  +----------------------------+
```

---

## Menu Options

| Option | Effect |
|--------|--------|
| **Attack** | Basic attack using STR + weapon |
| **Defend** | +4 AC, damage taken halved this turn |
| **Cast** | Opens spell submenu (uses MP) |
| **Item** | Opens consumables submenu |
| **Flee** | 30% + (AGI × 2)% chance to escape |

---

## Combat Flow

```
Battle starts
      │
      ▼
┌─────────────────┐
│ Player's Turn   │◄────────────────┐
│ Choose action   │                 │
└────────┬────────┘                 │
         │                          │
         ▼                          │
   ┌─────────────┐                  │
   │ Attack?     │──yes──► Deal damage
   │ Defend?     │──yes──► Set defending flag
   │ Cast?       │──yes──► Spell submenu
   │ Item?       │──yes──► Item submenu  
   │ Flee?       │──yes──► Roll escape
   └─────────────┘                  │
         │                          │
         ▼                          │
┌─────────────────┐                 │
│ Enemy's Turn    │                 │
│ Roll attack     │                 │
│ Apply defend    │                 │
└────────┬────────┘                 │
         │                          │
         ▼                          │
   Check HP ───── both alive ───────┘
         │
    enemy=0 ──► VICTORY (XP + Gold)
    player=0 ─► DEFEAT (death handling)
```

---

## Monster ASCII Art

The system includes ASCII art for common monsters:

| Symbol | Monster | Art Preview |
|--------|---------|-------------|
| g | Goblin | Small head with pointy ears |
| o | Orc | Square face with tusks |
| T | Troll | Large with horns |
| D | Dragon | Winged serpent (yellow) |
| s | Slime | Simple blob (green) |
| k | Skeleton | Skull with ribcage |

Unknown monsters show their symbol enlarged.

---

## Spell System

Spells use the existing skill system from Library.Character:

```ailang
// Skills bitmask in character data
skills_mask = Char_GetStat16(char_data, Char_Offsets.SKILLS)

// Each bit = one skill learned
// Skill IDs 2+ (1 is basic Attack)
```

### Spell Types

| Type | Effect |
|------|--------|
| ATTACK | Deals damage (power + INT bonus) |
| HEAL | Restores HP (power + INT bonus) |
| BUFF | Temporary stat boost (future) |

### MP Cost

- Shown in spell menu: `Fire (4MP)`
- Grayed out if insufficient MP
- Deducted on cast

---

## Item Usage

Only consumables work in battle:

| Type | Item IDs | Effect |
|------|----------|--------|
| POTION (3) | 60-69 | HP/MP restore |
| SCROLL (4) | 70-79 | Various effects |

### Default Items

| ID | Name | Effect |
|----|------|--------|
| 60 | Health Potion | +30 HP |
| 61 | Mana Potion | +20 MP |
| 62 | Elixir | +100 HP, +50 MP |

---

## Defend Mechanics

When player chooses Defend:
1. `Battle_State.defending = 1`
2. Player AC increased by +4
3. Damage taken is halved
4. Flag resets after enemy turn

---

## Flee Mechanics

```
flee_chance = 30 + (AGI × 2)
cap at 90%

roll = random 1-100
if roll <= flee_chance:
    battle ends, no penalty
else:
    "Couldn't escape!"
    enemy gets free attack
```

---

## Victory Rewards

```
XP = Monster's XP value
Gold = XP ÷ 2

Char_AddXP() checks for level up
```

---

## Files Added/Modified

### New Files
| File | Purpose |
|------|---------|
| `Library.BattleScreen.ailang` | Complete battle UI system |

### Modified Files
| File | Changes |
|------|---------|
| `Library.DND.ailang` | Add Battle_Init, replace combat |
| `Library.Item.ailang` | Add HP/MP bonus getters |
| `Library.Character.ailang` | Add skill info getters |

---

## Integration Checklist

- [ ] Add `LibraryImport.BattleScreen`
- [ ] Add `Battle_Init()` to `DND_Init`
- [ ] Add `Battle_Cleanup()` to `DND_Cleanup`
- [ ] Replace `DND_StartCombat` with `DND_StartBattle`
- [ ] Update `DND_MovePlayer` to use new battle
- [ ] Remove old combat from `DND_HandleInput`
- [ ] Add helper functions to Item/Character libraries

---

## Next Steps

With the battle system complete, the next integration is:

**Random Encounters** — Hook `Enc_CheckEncounter()` into movement to trigger battles when walking in encounter zones.