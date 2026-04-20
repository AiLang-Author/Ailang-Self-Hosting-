# Save System Documentation

## Overview

The save system provides Dragon Quest-style inn checkpoints with support for parties up to 4 characters. Designed with future network play in mind.

## Features

- **3 Save Slots** - Each with preview showing character, level, gold, location
- **Party Support** - Saves up to 4 characters with full stats
- **Inn Checkpoints** - Rest and save at inns, respawn there on death
- **Quest Flags** - Persistent flags for quest state (64 max)
- **Human-Readable** - INI-like `.dndsav` format for easy debugging/modding
- **Checksum** - Data integrity validation (network-ready)
- **Playtime Tracking** - Hours played shown in save preview

---

## Libraries

### Library.Save.ailang
Core save/load functionality.

**Key Functions:**
```
Save_Init()                          // Initialize system
Save_Cleanup()                       // Free resources

// Single player
Save_GameSingle(slot, char, x, y, map, gold, location)
Save_LoadSingle(slot, &char, &x, &y, &map, &gold)

// Party (multiplayer-ready)
Save_Game(slot, party[], count, x, y, map, gold, location)
Save_Load(slot, party[], &count, &x, &y, &map, &gold)

// Quick save/load (slot 0)
Save_QuickSave(char, x, y, map, gold)
Save_QuickLoad(&char, &x, &y, &map, &gold)

// Quest flags
Save_SetFlag("quest_name", value)
Save_GetFlag("quest_name") → Integer

// Inn checkpoints
Save_SetInnCheckpoint(map, x, y)
Save_GetInnCheckpoint(&map, &x, &y)

// Utilities
Save_SlotExists(slot) → 0/1
Save_DeleteSlot(slot)
Save_AddPlaytime(seconds)
```

### Library.SaveScreen.ailang
TUI-based save/load interface.

**Key Functions:**
```
SaveScreen_Save(char, x, y, map, gold, location) → slot or -1
SaveScreen_Load(&char, &x, &y, &map, &gold) → slot or -1
SaveScreen_SaveParty(party[], count, x, y, map, gold, location)
SaveScreen_TitleLoad(&char, &x, &y, &map, &gold) → slot or -1
```

---

## File Format (.dndsav)

```ini
[HEADER]
VERSION=1
SLOT=0
PLAYTIME=7245          # seconds played

[WORLD]
MAP_ID=2               # current map
PLAYER_X=15
PLAYER_Y=8
INN_MAP=1              # respawn location
INN_X=4
INN_Y=3

[PARTY]
COUNT=2                # 1-4 characters
GOLD=1250

[CHAR:0]               # lead character
NAME=Aldric
CLASS=1                # 1=Warrior, 2=Mage, etc
LEVEL=7
XP=2450
HP=45
MAX_HP=52
MP=12
MAX_MP=20
STR=18
AGI=12
VIT=15
INT=10
LUK=11
SKILLS=7               # bitmask of learned skills

[CHAR:1]               # second party member
...

[INVENTORY]
COUNT=8
ITEM_0=60,5            # item_id,quantity
ITEM_1=61,3
...

[EQUIPMENT]
SLOT_0=3               # weapon
SLOT_1=12              # armor
SLOT_2=22              # shield
SLOT_3=31              # helm
SLOT_4=0               # accessory 1
SLOT_5=0               # accessory 2

[FLAGS]
COUNT=4
quest_dragon=1
met_king=1
cave_unlocked=1
rescued_villager=0

[CHECKSUM]
VALUE=48291573         # XOR-based integrity check
```

---

## Integration Points

### Title Screen
```
choice = ShowTitleScreen_v2()
// 0 = Quit
// 1 = New Game
// 2 = Continue (shows load screen)
```

### Inn Interaction
```
// When player steps on inn tile and presses interact:
inn_id = Inn_GetAtPosition(map, x, y)
Inn_ShowMenu_v2(inn_id, char_data, party, party_count,
                &gold, x, y, map)
```

### Death/Respawn
```
// On player death:
Inn_RespawnAtCheckpoint(char_data, &x, &y, &map)
// Teleports to last inn, sets HP to 1
```

### Quest System
```
// Set flag when quest event occurs:
Save_SetFlag("quest_dragon", 1)

// Check flag for conditional dialogue/events:
IfCondition EqualTo(Save_GetFlag("quest_dragon"), 1) ThenBlock: {
    // Dragon quest is active
}
```

---

## Network Considerations

The save system is designed for future multiplayer:

1. **Party Array** - All functions accept party arrays, not just single characters
2. **Server Authority** - Checksum prevents client-side save tampering
3. **Slot Isolation** - Each player can have their own save slots (server-side)
4. **Flag Sync** - Quest flags can be synced across party members

For network play, the server would:
- Validate checksums on load
- Store saves in `saves/{player_id}/slot_N.dndsav`
- Sync party data when players join/leave groups
- Auto-save periodically (configurable in server.dnddat)

---

## Usage Examples

### Save at Inn
```ailang
// Player interacts with inn
inn_id = Inn_GetAtPosition(current_map, player_x, player_y)
Inn_ShowMenu_v2(inn_id, DND_Player.char_data, 0, 1,
               AddressOf(DND_Player.gold),
               DND_Player.x, DND_Player.y, DND_Map.level)
```

### Quick Save (Development)
```ailang
// Bind to F5 or similar
Save_QuickSave(DND_Player.char_data, DND_Player.x, DND_Player.y,
              DND_Map.level, DND_Player.gold)
```

### Load from Title Screen
```ailang
slot = SaveScreen_TitleLoad(AddressOf(char_data),
                           AddressOf(x), AddressOf(y),
                           AddressOf(map), AddressOf(gold))
IfCondition GreaterEqual(slot, 0) ThenBlock: {
    // Apply loaded data
    DND_Player.char_data = char_data
    DND_Player.x = x
    DND_Player.y = y
    DND_Player.gold = gold
    DND_LoadMap(map)
}
```

---

## Files Added

| File | Purpose |
|------|---------|
| `Library.Save.ailang` | Core save/load logic |
| `Library.SaveScreen.ailang` | TUI save/load interface |
| `saves/*.dndsav` | Save files (auto-created) |

## Updated Files

| File | Changes |
|------|---------|
| `Library.Inn.ailang` | Added `Inn_ShowMenu_v2`, party healing |
| `dnd.ailang` | Title screen with Continue option |
| `Library.DND.ailang` | Death respawn handling |