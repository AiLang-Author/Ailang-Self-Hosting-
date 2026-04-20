# AILANG RPG Engine - Data Formats & Modding Guide

## Overview

All game content is defined in text files that can be edited without recompiling.
Place your data files in the `/data/` directory and maps in `/maps/`.

---

## File Types

| Extension | Purpose | Format |
|-----------|---------|--------|
| `.dndmap` | Map/level definitions | Custom ASCII |
| `.dnddat` | Data tables (items, monsters, etc) | CSV-like |
| `.dndscript` | Dialogue & events | Custom scripting |
| `.dndsav` | Save games | INI-like |

---

## Map Format (.dndmap)

```
NAME:Hometown
SIZE:20,16
START:5,14
TYPE:TOWN
PARENT:0,10,10
######################
#..................#
#.+--+....+--+.....#
#.|  |....|  |.....#
#.|  |....|  |.....#
#.+--+....+--+.....#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#.......+..........#
#..................#
######################
```

### Header Fields
- `NAME:` - Display name
- `SIZE:width,height` - Map dimensions
- `START:x,y` - Player spawn position
- `TYPE:` - OVERWORLD, TOWN, DUNGEON, BUILDING, CAVE
- `PARENT:map_id,return_x,return_y` - Where EXIT portals go

### Tile Characters
| Char | Meaning |
|------|---------|
| `#` | Wall |
| `.` | Floor |
| `+` | Closed door |
| `'` | Open door |
| `X` | Locked door |
| `<` | Stairs up |
| `>` | Stairs down |
| `~` | Water |
| `^` | Trap |
| `*` | Chest |
| `!` | Item |
| `$` | Gold |
| `M` | Monster spawn |
| `N` | NPC spawn |
| `@` | Player (for reference) |

---

## Items (items.dnddat)

```csv
# ITEM,id,name,type,slot,value,atk,def,mag,hp,mp,req_level,rarity
ITEM,1,Rusty Sword,WEAPON,WEAPON,5,3,0,0,0,0,1,COMMON
ITEM,2,Iron Sword,WEAPON,WEAPON,25,6,0,0,0,0,1,COMMON
ITEM,10,Cloth Tunic,ARMOR,ARMOR,5,0,1,0,0,0,1,COMMON
ITEM,60,Health Potion,POTION,NONE,25,0,0,0,0,0,1,COMMON
```

### Item Types
`WEAPON`, `ARMOR`, `SHIELD`, `HELMET`, `RING`, `AMULET`, `POTION`, `SCROLL`, `KEY`, `GOLD`, `FOOD`, `MISC`

### Equipment Slots
`WEAPON`, `ARMOR`, `SHIELD`, `HELMET`, `RING`, `AMULET`, `NONE`

### Rarity Levels
`COMMON`, `UNCOMMON`, `RARE`, `EPIC`, `LEGENDARY`

---

## Monsters (monsters.dnddat)

```csv
# MONSTER,id,name,symbol,hp,ac,damage_dice,damage_sides,damage_mod,xp,level
MONSTER,1,Goblin,g,8,12,1,6,0,25,1
MONSTER,2,Orc,o,15,13,1,8,1,50,2
MONSTER,3,Troll,T,30,15,2,6,2,100,4
MONSTER,10,Slime,s,5,8,1,4,0,10,1
MONSTER,11,Skeleton,k,12,11,1,6,1,30,2
MONSTER,20,Dragon,D,100,18,2,10,5,500,10
```

---

## Character Classes (classes.dnddat)

```csv
# CLASS,id,name,hp,mp,str,agi,vit,int,luk
CLASS,1,Warrior,30,5,12,8,12,6,8
CLASS,2,Mage,18,25,6,8,6,14,10
CLASS,3,Rogue,22,12,8,14,8,8,12
CLASS,4,Cleric,24,20,8,7,10,12,10
CLASS,5,Ranger,25,15,10,12,9,8,10
```

---

## Level Progression (level_gains.dnddat)

```csv
# LEVEL,class_id,level,hp,mp,str,agi,vit,int,skill_id
LEVEL,1,2,8,0,2,1,2,0,0
LEVEL,1,3,10,1,2,1,2,0,2
LEVEL,1,5,12,1,3,1,3,0,4
# skill_id 0 = no skill learned
```

---

## Skills (skills.dnddat)

```csv
# SKILL,id,name,type,target,mp_cost,power,accuracy
SKILL,1,Attack,ATTACK,SINGLE_ENEMY,0,0,95
SKILL,2,Power Strike,ATTACK,SINGLE_ENEMY,3,15,90
SKILL,10,Fire,ATTACK,SINGLE_ENEMY,4,20,100
SKILL,20,Heal,HEAL,SINGLE_ALLY,3,20,100
```

### Skill Types
`ATTACK`, `HEAL`, `BUFF`, `DEBUFF`, `UTILITY`, `PASSIVE`

### Targets
`SELF`, `SINGLE_ENEMY`, `ALL_ENEMIES`, `SINGLE_ALLY`, `ALL_ALLIES`

---

## Shops (shops.dnddat)

```csv
# SHOP,id,name,buy_rate,sell_rate,map_id,x,y,type
SHOP,0,General Store,120,50,1,14,4,GENERAL
SHOP,1,Weapon Smithy,100,40,1,4,4,WEAPON

# STOCK,shop_id,item_id,quantity,restock_rate
STOCK,0,60,10,50
STOCK,0,61,10,50
STOCK,1,1,255,0
STOCK,1,2,5,20
```

- `buy_rate`: % of base price (100 = normal, 120 = 20% markup)
- `sell_rate`: % of value player gets when selling
- `quantity`: 255 = unlimited
- `restock_rate`: % chance to restock per game day

---

## Inns (inns.dnddat)

```csv
# INN,id,name,price,map_id,x,y,save_enabled
INN,0,Cozy Hearth Inn,10,1,4,3,1
INN,1,Castle Guest Room,0,4,8,8,1
```

---

## Encounter Zones (encounters.dnddat)

```csv
# ZONE,id,name,map_id,min_x,min_y,max_x,max_y,rate
ZONE,0,Fields,0,5,8,15,15,8
ZONE,1,Wilderness,0,16,0,39,24,12

# GROUP,zone_id,monster_id,min_count,max_count,weight
GROUP,0,1,1,2,50
GROUP,0,1,3,4,20
GROUP,1,2,1,2,50
```

- `rate`: % chance of encounter per step
- `weight`: relative probability of this group spawning

---

## World/Portals (world.dnddat)

```csv
# MAP,id,name,path,type,parent_id
MAP,0,Overworld,maps/overworld.dndmap,OVERWORLD,0
MAP,1,Hometown,maps/hometown.dndmap,TOWN,0
MAP,2,Dark Cave B1,maps/cave_b1.dndmap,DUNGEON,0

# PORTAL,map_id,src_x,src_y,type,dest_map,dest_x,dest_y
PORTAL,0,10,10,ENTRANCE,1,5,14
PORTAL,1,5,15,EXIT,0,10,11
PORTAL,2,15,10,STAIRS_DOWN,3,3,3
```

### Portal Types
`STAIRS_DOWN`, `STAIRS_UP`, `DOOR`, `ENTRANCE`, `EXIT`

---

## NPCs (npcs.dnddat)

```csv
# NPC,id,name,symbol,map_id,x,y,dialogue_id,can_move
NPC,0,King,K,4,10,5,100,0
NPC,1,Guard,G,4,8,10,101,1
NPC,2,Villager,V,1,8,8,102,1
```

---

## Dialogue Scripts (.dndscript)

```
[DIALOGUE:100]
SAY: Welcome, brave adventurer!
SAY: Our kingdom is in peril.
CHOICE: How can I help?
  GOTO: 101
CHOICE: Not interested.
  SAY: Very well. Return when you change your mind.
  END

[DIALOGUE:101]
SAY: A dragon has stolen the royal crown!
SAY: Venture to the Dark Cave and defeat it.
FLAG: quest_dragon,1
GIVE: 60,5
SAY: Take these potions. Good luck!
END
```

### Script Commands
- `SAY: text` - Display text
- `CHOICE: text` - Player option
- `GOTO: dialogue_id` - Jump to dialogue
- `END` - End conversation
- `FLAG: name,value` - Set game flag
- `CHECK: flag,value` - Conditional
- `GIVE: item_id,qty` - Give item
- `TAKE: item_id,qty` - Remove item
- `GOLD: amount` - Give/take gold (negative to take)

---

## Creating a Mod

1. Create a folder: `/mods/my_adventure/`
2. Add your data files and maps
3. Create `mod.dnddat`:

```csv
# MOD INFO
NAME,My Adventure
AUTHOR,Your Name
VERSION,1.0
DESCRIPTION,A new quest in a distant land

# FILES TO LOAD
LOAD,mods/my_adventure/items.dnddat
LOAD,mods/my_adventure/monsters.dnddat
LOAD,mods/my_adventure/maps/start.dndmap
```

---

## Tips for Content Creators

1. **Balance**: Test XP/gold values against progression
2. **IDs**: Use high IDs (1000+) for mod content to avoid conflicts
3. **Maps**: Keep under 80x40 for performance
4. **Encounters**: Rate 5-15% feels good, higher in dungeons
5. **Economy**: sell_rate 40-50% prevents gold exploits