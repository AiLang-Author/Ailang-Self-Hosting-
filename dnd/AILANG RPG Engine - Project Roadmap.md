# AILANG RPG Engine - Project Roadmap

## Vision

An open-source, fully moddable, Dragon Quest-style RPG engine written in AILang that compiles to native code. Supports single-player and multiplayer (MUD-style via telnet).

**Target Audience:**
- Hobbyist game developers
- D&D/tabletop groups wanting virtual adventures
- Retro gaming enthusiasts
- AILang learners

---

## Current Status (v0.1)

### ✅ Core Engine Complete
| Component | Status | Description |
|-----------|--------|-------------|
| Library.TUI | ✅ Done | Terminal UI, colors, input, raw mode |
| Library.DICE | ✅ Done | RNG, dice rolls (NdS+M), advantage |
| Library.CSV | ✅ Done | RFC 4180 parser, file I/O |
| Library.Character | ✅ Done | Classes, stats, skills, leveling |
| Library.Item | ✅ Done | Items, inventory, equipment |
| Library.DND | ✅ Done | Game logic, maps, combat |
| Library.World | ✅ Done | Map transitions, portals |
| Library.Save | ✅ Done | Save/load game state |
| Library.Shop | ✅ Done | Buy/sell items |
| Library.Inn | ✅ Done | Rest, heal, save points |
| Library.Encounter | ✅ Done | Random battles |
| Library.EquipScreen | ✅ Done | Equipment management UI |

### 📋 Data Files Defined
- Maps (.dndmap)
- Items, Monsters, Classes (.dnddat)
- Shops, Inns, Encounters (.dnddat)
- Dialogue scripts (.dndscript)
- Save files (.dndsav)

---

## Roadmap

### Phase 1: Polish Core (Current)
- [ ] Integrate all new libraries into main game
- [ ] Full random battle UI
- [ ] Test shop/inn interactions
- [ ] Bug fixes and balance

### Phase 2: NPCs & Dialogue
- [ ] Library.NPC - NPC spawns and movement
- [ ] Library.Dialogue - Script parser and execution
- [ ] Quest system (flags + conditions)
- [ ] NPC shops (talk to buy)

### Phase 3: Visual Polish
- [ ] Sprite/tile customization system
- [ ] Character appearance selection
- [ ] Map tile palettes (forest, desert, snow)
- [ ] Animation frames for combat

### Phase 4: Network - Basic
- [ ] Library.Network - Socket handling
- [ ] Telnet server (accept connections)
- [ ] Single-player over network
- [ ] Basic authentication

### Phase 5: Network - Multiplayer
- [ ] Multiple sessions
- [ ] Chat system (/say, /tell, /shout)
- [ ] See other players on map
- [ ] Shared world state

### Phase 6: Advanced Multiplayer
- [ ] Party system
- [ ] Group combat
- [ ] Trading between players
- [ ] DM mode for tabletop groups

### Phase 7: Community & Tools
- [ ] Map editor (TUI-based)
- [ ] Item/monster editor
- [ ] Mod loader system
- [ ] Documentation site

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    /data/ (Moddable)                    │
│  items.dnddat │ monsters.dnddat │ classes.dnddat │ ... │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Engine Libraries                       │
│                                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │Character│ │  Item   │ │  World  │ │Encounter│       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
│       └──────────┬┴──────────┬┴───────────┘            │
│                  │           │                          │
│           ┌──────┴───┐ ┌─────┴────┐                    │
│           │   DND    │ │   Save   │                    │
│           │  (Core)  │ │  System  │                    │
│           └──────┬───┘ └──────────┘                    │
│                  │                                      │
│           ┌──────┴───┐                                 │
│           │   TUI    │◄── Terminal Control             │
│           └──────┬───┘                                 │
│                  │                                      │
└──────────────────┼──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────┐      ┌──────────────┐
│    Local     │      │   Network    │
│   Terminal   │      │   (Telnet)   │
└──────────────┘      └──────────────┘
```

---

## Contributing

### Code Style
- Functions: `Library_FunctionName`
- Constants: `UPPER_SNAKE_CASE`
- Variables: `lower_snake_case`
- Comments: Explain "why" not "what"

### Adding Content
1. Use data files, not code changes
2. Test with existing saves
3. Document new file formats
4. Submit as mod first, merge if popular

### Submitting Changes
1. Fork the repository
2. Create feature branch
3. Test thoroughly
4. Submit pull request
5. Describe changes clearly

---

## File Structure

```
ailang-rpg/
├── ailang/              # Compiler (separate project)
├── src/
│   ├── Library.TUI.ailang
│   ├── Library.DICE.ailang
│   ├── Library.CSV.ailang
│   ├── Library.Character.ailang
│   ├── Library.Item.ailang
│   ├── Library.DND.ailang
│   ├── Library.World.ailang
│   ├── Library.Save.ailang
│   ├── Library.Shop.ailang
│   ├── Library.Inn.ailang
│   ├── Library.Encounter.ailang
│   ├── Library.NPC.ailang        # TODO
│   ├── Library.Dialogue.ailang   # TODO
│   ├── Library.Network.ailang    # TODO
│   ├── Library.EquipScreen.ailang
│   └── dnd.ailang               # Main entry point
├── data/
│   ├── items.dnddat
│   ├── monsters.dnddat
│   ├── classes.dnddat
│   ├── skills.dnddat
│   ├── level_gains.dnddat
│   ├── xp_table.dnddat
│   ├── shops.dnddat
│   ├── inns.dnddat
│   ├── encounters.dnddat
│   ├── npcs.dnddat              # TODO
│   └── world.dnddat
├── maps/
│   ├── overworld.dndmap
│   ├── hometown.dndmap
│   ├── cave_b1.dndmap
│   └── ...
├── mods/
│   └── example_mod/
│       ├── mod.dnddat
│       └── ...
├── saves/
│   └── *.dndsav
├── docs/
│   ├── DATA_FORMATS.md
│   ├── NETWORK_ARCHITECTURE.md
│   └── PROJECT_ROADMAP.md
├── README.md
└── LICENSE
```

---

## Why AILang?

- **Native Performance**: Compiles to x86-64, no runtime overhead
- **Educational**: Learn low-level systems programming
- **Self-Contained**: No dependencies, pure syscalls
- **Moddable**: Data-driven design, text-based files
- **Portable**: Runs anywhere Linux runs

---

## License

MIT License - Use it, modify it, share it, sell it.
Just give credit and keep it open.

---

## Links

- [AILang Compiler](github.com/yourname/ailang)
- [RPG Engine](github.com/yourname/ailang-rpg)
- [Discord/Community](discord.gg/xxxxx) # TODO
- [Documentation](ailang-rpg.readthedocs.io) # TODO