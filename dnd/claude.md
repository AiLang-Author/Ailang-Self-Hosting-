# DnD Web Mode — Session Handoff

**Branch:** `kmod-link-layer` (pushed to origin)
**Last session ended:** 2026-04-24
**Hot binary used during testing:** `/tmp/dnd_fix2.x` (compile from current sources reproduces it)

---

## What got done

Web frontend for the DnD engine — same game state, alternate I/O driver.

```
./dnd_web --web game.dndconf
# then in any browser (Windows Chrome or WSL): http://localhost:9001/
```

### Wiring (`dnd_game.ailang`)
- New `FixedPool.Web_Flag { "enabled": 0 }`
- `Function.DetectWebFlag` — scans `/proc/self/cmdline` for `--web` token
- `Function.ParseArgs` — extended to skip leading `--*` args so `dnd --web game.dndconf` resolves the config path correctly
- `SubRoutine.Main`:
  - `DetectWebFlag()` runs right after `DND_Init()`
  - `Portal_DebugDump()` gated on `Web_Flag.enabled == 0` (its `TUI_WaitKey` blocks forever in web mode — no terminal)
  - After `StartFromConfig()`, branches: web mode → `HTML_Init()` + `HTML_StartServer()` (blocks); TUI mode → existing title/play flow unchanged

### Engine fixes (`Librarys/Library.HTMLBroadcast.ailang`)
- Port: 8088 → 9001
- `sin_family` byte order: was `[00, 02]`, now `[02, 00]` — bytes are little-endian on x86 so the old order produced 0x0200 (= 512, garbage), not `AF_INET=2`. Bind failed on every port before this fix.
- `shutdown(cli, SHUT_WR)` before `close(cli)` in the accept loop — graceful close, sends FIN after the send queue drains.
- **Body-delivery bug fix** (the big one): trailing headers blob `"\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n"` is **55 bytes**, not 52. Old code passed `52` to `SystemCall(write, ...)`, truncating the trailing `\r\n\r\n` end-of-headers separator. curl saw malformed headers, never found the body delimiter, and reported "transfer closed with N bytes remaining" — for *any* body size. All the SHUT_WR / SO_LINGER / partial-write debugging beforehand was chasing a red herring; `write(2)` always succeeded, the framing was wrong.

### Verified working endpoints
| Endpoint | Verified |
|---|---|
| `GET /` (shell) | 3576 B HTML returned, browser parses fine |
| `GET /state` | 17027 B JSON game state |
| `POST /action` `{"action":"right"}` | Player x increments 10 → 11; new state returned |
| Anything else | 404 + "not found" |

---

## What's still rough (next session pickups)

1. **Browser shows title bar / chrome but no visible game.** Last user observation: "some stuff on screen, no game, no login just a title screen." The shell page renders, JS polls `/state`, but the map grid may be empty or the JSON tiles may not be matching the CSS classes correctly. Likely candidates:
   - Tile char codes don't match the `.t<NN>` CSS rules in `HTML_ServeShell` (only a handful of codes have explicit color rules — others fall through to the default).
   - Player char is created with default Hero/Warrior in `DND_Init`, but a fresh game state without going through any title flow may have weird zero values somewhere (HP/MP bar widths could be NaN if `max_hp=0`).
   - First load: open browser DevTools → Network tab → look at the actual `/state` JSON content. Then DevTools → Console for any JS errors.

2. **No "login" / character creation in web mode.** Auto-spawns Hero/Warrior. Title screen + char-create are TUI-only right now. Future: HTML title screen + char-create endpoints.

3. **Inventory / equip keys (`i`, `e`) no-op on the server side.** The JS sends them but `HTML_HandleAction` only routes `up/down/left/right/wait/stairs_up/stairs_down`. Easy follow-up.

4. **TUI escapes still print to stdout in web mode** during early init (`Portal_DebugDump` itself is gated, but `TUI_Clear()` etc. inside `DND_Init` may still emit). Cosmetic — server still works, but messy logs.

5. **`Library.DND_HTML_Output_engine.ailang`** is a near-duplicate of `HTMLBroadcast` (~579 vs 587 lines, same header `Library.HTMLOutput.ailang`, only diff is which one `dnd_game.ailang` imports). **Reconcile**: pick one canonical name (probably `HTMLBroadcast` since that's what dnd_game imports), delete the other.

6. **Polling is 150ms** (`HTMLCfg.poll_ms`). Real-time would want WebSocket / SSE. The shell page already opens a `WebSocket` connection in JS (`/ws/mana/{channel}`) but that's a leftover/unused path — not wired into game updates.

---

## Compile + run cheatsheet

```bash
# Build
cd /mnt/c/Users/Sean/Documents/AiLangSH
./ailang.x dnd_game.ailang dnd_web.x          # produces dnd_web.x in repo root

# Run web mode (default config)
cd dnd
../dnd_web.x --web game.dndconf
# or any other .dndconf

# Run TUI mode (default — same binary, no flag)
../dnd_web.x game.dndconf

# Browse
# Windows Chrome OR Linux/WSL: http://localhost:9001/
# (WSL2 auto-forwards localhost so no IP juggling needed)
```

---

## Architecture quick-ref

```
HTTP request
   |
   v
HTML_StartServer accept loop  (blocking, in main thread)
   |
   +-- GET / ----------> HTML_ServeShell  -> HTMLOut buffer + send
   +-- GET /state -----> HTML_ServeState  -> HTML_RenderFrame()
   |                                          -> JSON state object
   |                                          -> JSON.SerializeObject
   |                                          -> HTML_SendHTTP
   +-- POST /action --> HTML_HandleAction -> Game_MovePlayer / etc.
   |                                          -> HTML_ServeState
   +-- other ---------> 404
   |
   v
shutdown(SHUT_WR) + close(cli)
```

State source for `HTML_RenderFrame`:
- `DND_Player.{x, y, gold, char_data}` — viewport center, gold, char ptr
- `DND_Map.{width, height}` + `DND_GetTile(x, y)` — terrain
- `DND_Monsters` (via `DND_GetMonsterAt`, `DND_GetMonsterSymbol`) — monster overlay
- `Char_Get*(char_data)` — name/class/level/HP/MP/XP for stats panel
- `DND_GetMessage(i)` / `DND_GetMessageCount()` — message log
- `Config_GetMapName(Config_State.current_map)` — map name display

The render is a pure read of the engine state — no input handling on the render side, no mutation. `HTML_HandleAction` is the only place the engine's `Game_*` functions are called.

---

## Files touched this session

```
M  dnd_game.ailang
M  Librarys/Library.HTMLBroadcast.ailang
A  dnd/claude.md            (this file)
```

Two commits on `kmod-link-layer` past the previous push:
- `55c8b297` — `web: wire --web flag into DnD main loop; HTMLBroadcast bind fix`
- `7f8f9706` — `HTMLBroadcast: fix 52->55 byte length on trailing headers blob`

---

## Useful diagnostic snippets (kept for future debugging)

```bash
# Strace the server to see actual write() calls + return values
strace -f -e trace=accept,read,write,close,shutdown \
    -o /tmp/srv_strace.log \
    ./dnd_web.x --web game.dndconf

# Verbose curl to see HTTP framing
curl -v -m 8 http://localhost:9001/state

# Raw HTTP, no curl
printf 'GET /state HTTP/1.0\r\n\r\n' | nc 127.0.0.1 9001 | head -c 400

# Check what's bound to 9001
ss -lntp | grep 9001

# Kill stale instances
pkill -9 -f dnd_
```

The 52→55 fix was found via strace (option (a) from the WIP commit's "next angles" list) — the byte-count discrepancy was visible directly in the strace output of the `write()` calls. Worth remembering: when "headers arrive but body doesn't," distrust the framing before distrusting the network.
