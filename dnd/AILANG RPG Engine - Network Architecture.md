# AILANG RPG Engine - Network Architecture

## Overview

The engine supports two modes:
1. **Local Mode** - Single player, direct terminal
2. **Server Mode** - Multi-player MUD via telnet

```
┌─────────────────────────────────────────────────────────────┐
│                      SERVER MODE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐                                          │
│   │   Server    │◄─── Port 2323 (configurable)             │
│   │   Process   │                                          │
│   └──────┬──────┘                                          │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────────────────────────────────┐              │
│   │         Connection Manager              │              │
│   │  • Accept new connections               │              │
│   │  • Track active sessions                │              │
│   │  • Handle disconnects                   │              │
│   └──────┬──────────────┬───────────┬──────┘              │
│          │              │           │                      │
│          ▼              ▼           ▼                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐             │
│   │ Session  │   │ Session  │   │ Session  │  ...        │
│   │    1     │   │    2     │   │    3     │             │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘             │
│        │              │              │                     │
│        ▼              ▼              ▼                     │
│   ┌──────────────────────────────────────────┐            │
│   │            Shared World State            │            │
│   │  • Maps, NPCs, Monsters                  │            │
│   │  • Per-player: Position, Stats, Inv      │            │
│   │  • Global: Flags, Economy                │            │
│   └──────────────────────────────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Telnet Protocol

Telnet is ideal because:
- Text-based (matches our TUI)
- Universal client support
- Simple to implement
- Classic MUD heritage

### Connection Flow

```
1. Client connects to server:port
2. Server sends: IAC WILL ECHO, IAC WILL SGA
3. Server sends: Welcome banner
4. Client sends: Character name
5. Server: Login/Create character flow
6. Main game loop begins
```

### Escape Sequences

The existing TUI escape codes work over telnet:
- `\x1b[H` - Home cursor
- `\x1b[2J` - Clear screen
- `\x1b[31m` - Red text
- etc.

Most modern terminals (PuTTY, iTerm, Linux terminal) handle these.

---

## Library.Network.ailang (Planned)

```ailang
// ============================================
// Library.Network.ailang
// Telnet Server for Multiplayer
// ============================================

FixedPool.Net_Config {
    "port": Initialize=2323
    "max_connections": Initialize=32
    "timeout": Initialize=300        // 5 min idle timeout
    "motd_enabled": Initialize=1
}

// Session structure per connection
// 0-3:   Socket FD (4 bytes)
// 4:     State (1 byte) - 0=new, 1=login, 2=playing
// 5-8:   Player ID (4 bytes)
// 9-12:  Last activity timestamp
// 13-268: Input buffer (256 bytes)
// ...

FixedPool.Session_Offsets {
    "SOCKET": Initialize=0
    "STATE": Initialize=4
    "PLAYER_ID": Initialize=5
    "LAST_ACTIVE": Initialize=9
    "INPUT_BUF": Initialize=13
    "SIZE": Initialize=512
}

// Server states
FixedPool.Server_State {
    "listen_fd": Initialize=0
    "sessions": Initialize=0
    "session_count": Initialize=0
    "running": Initialize=0
}

// Start server
Function.Net_StartServer {
    Input: port: Integer
    Output: Integer
    Body: {
        // socket(AF_INET, SOCK_STREAM, 0)
        sock = SystemCall(41, 2, 1, 0)
        
        // Set SO_REUSEADDR
        opt = Allocate(4)
        StoreValue(opt, 1)
        SystemCall(54, sock, 1, 2, opt, 4)  // setsockopt
        
        // bind()
        addr = Allocate(16)
        // ... set up sockaddr_in ...
        SystemCall(49, sock, addr, 16)
        
        // listen()
        SystemCall(50, sock, 10)
        
        Server_State.listen_fd = sock
        Server_State.running = 1
        
        ReturnValue(sock)
    }
}

// Main server loop (select/poll based)
Function.Net_ServerLoop {
    Body: {
        WhileLoop EqualTo(Server_State.running, 1) {
            // poll() on listen socket + all sessions
            // Accept new connections
            // Read from active connections
            // Process input
            // Send output
        }
    }
}
```

---

## Session Management

### Player States
```
NEW        → Just connected, show MOTD
LOGIN      → Entering name/password
CREATING   → New character creation
PLAYING    → In-game
COMBAT     → In battle (special input mode)
MENU       → In shop/inn/dialogue
LINKDEAD   → Disconnected but character persists
```

### Shared vs Per-Player Data

**Shared (World State):**
- Map layouts
- NPC positions and dialogue
- Shop inventories
- Monster spawns (static)
- Global flags (quests completed, etc)

**Per-Player:**
- Character data (stats, level, etc)
- Inventory & equipment
- Position (map + x,y)
- Session state
- Personal flags

---

## Multi-Player Modes

### 1. Parallel Worlds (Easy)
Each player in their own instance. Can chat but don't interact.

```
Player A: [Overworld 15,10] Fighting goblin
Player B: [Overworld 15,10] No goblin (their instance)
```

### 2. Shared World (Medium)
All players see same world. Monsters respawn on timer.

```
Player A kills goblin → gone for everyone
Timer: Goblin respawns after 60 seconds
```

### 3. Party System (Advanced)
Players can group up, share XP, coordinated combat.

```
/party invite PlayerB
/party accept
Now in same battles, share XP
```

---

## Chat & Commands

```
/say Hello!           → Local area chat
/shout HELLO!         → Server-wide
/tell PlayerB Hi      → Private message
/who                  → List online players
/party invite Name    → Party management
/quit                 → Disconnect
```

---

## Server Configuration (server.dnddat)

```ini
[SERVER]
PORT=2323
MAX_PLAYERS=32
TIMEOUT=300
MOTD_FILE=data/motd.txt

[WORLD]
MODE=SHARED
RESPAWN_TIME=60
PVP_ENABLED=0

[SAVES]
AUTO_SAVE=1
SAVE_INTERVAL=300
SAVE_PATH=saves/

[ADMIN]
ADMIN_PASSWORD=changeme
LOG_FILE=logs/server.log
```

---

## Security Considerations

1. **Input Validation**
   - Max input length (256 chars)
   - Strip control characters
   - Rate limit commands

2. **Authentication**
   - Password hashing (simple XOR for AILang, or external)
   - Lockout after failed attempts

3. **Anti-Cheat**
   - Server-authoritative (client can't modify stats)
   - Sanity checks on movement (no teleporting)
   - Rate limit actions (no spam attacks)

---

## Implementation Phases

### Phase 1: Basic Telnet
- [ ] Accept connections
- [ ] Send/receive text
- [ ] Single player over network

### Phase 2: Multi-Session  
- [ ] Multiple connections
- [ ] Session management
- [ ] Basic chat

### Phase 3: Shared World
- [ ] Sync world state
- [ ] See other players
- [ ] Monster respawn system

### Phase 4: Interaction
- [ ] Party system
- [ ] Trading
- [ ] PvP (optional)

---

## Alternative: WebSocket Server

For modern web access, could add WebSocket support:

```
Browser ←→ WebSocket ←→ AILANG Server ←→ Game Engine
```

Benefits:
- Play in web browser
- No client install
- Mobile friendly

Implementation would use raw HTTP upgrade + frame parsing.

---

## Running the Server

```bash
# Compile with network support
./ailang compile dnd_server.ailang

# Start server
./dnd_server --port 2323 --config server.dnddat

# Connect with any telnet client
telnet localhost 2323

# Or with netcat
nc localhost 2323
```

---

## D&D Campaign Support

For tabletop groups using this as a virtual tabletop:

1. **DM Mode**: Special account with god powers
   - Spawn monsters anywhere
   - Teleport players
   - Modify world in real-time
   - Trigger scripted events

2. **Roll Integration**
   ```
   /roll 1d20+5     → You rolled 17 (12+5)
   /roll 4d6        → You rolled 14 (3+4+4+3)
   ```

3. **Session Logging**
   - Auto-save chat transcript
   - Combat log for review

4. **Map Reveal**
   - Fog of war per-player
   - DM reveals areas as party explores