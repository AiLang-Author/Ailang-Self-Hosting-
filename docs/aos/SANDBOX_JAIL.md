# AOS Sandbox Jail — Quarantine Disk, FUSE User Data, Capabilities Later

**Status**: v0 in progress (quarantine homes). v1 mount-ns / v2 FUSE+caps not wired.
**Related**: `OS/FileTree.ailang`, `OS/UUIDStore.ailang`, `OS/Schema.ailang` (`packages`, `applets`, `files`, `sandboxes`), `Applications/chrome_ipc.ailang`, `Applications/terminal_ipc.ailang`, `docs/aos/phase1-rls-pgcrypto-login.md`, `docs/aos/phase2-luks-secure-boot.md`, `CONTRIBUTING.md` §1 (X11 sandbox hardening), `docs/display/00_MASTER_INDEX.md`

---

## Intent

Ailang OS has two product aims that must not be implemented as one blob:

1. **A cleaner windowing display system and API** — Auckland, SysDisplay, IPC. The compositor sees windows, input, and messages. It does **not** open user blobs for Chrome.
2. **Containment for AI systems and foreign tools** — limit blast radius, protect user data. An agent that can run `grok`, Chrome, or busybox must not inherit the whole disk.

Foreign Linux ELFs (Chrome, grok CLI, VS Code, busybox `vi`) speak POSIX `open()` / `mmap()` / `$HOME`. First-party Auckland apps speak FileTree (Postgres directory index + UUID blobs). Until those programs are native ports, the only honest containment is a **jail that looks like a normal Linux tree**, with **user paths mediated** and **program guts quarantined**.

This is the path until proper ports or more native apps exist. IPC already abstracts “everything but the GUI” for wrapped apps (Xvfb + `input.mouse` / `input.key`). The jail is the matching abstraction for **disk**.

---

## What this is not

- Not apt/npm. A jail is a folder (later an overlay), not a dependency solver.
- Not “Chrome talks FileTree.” Chromium will not grow a Postgres client.
- Not “every `write()` is a `files` row.” Chrome cache in Tracker would be junk, and WAL would die.
- Not display.x as the filesystem gate. Display may **prompt** (“Allow Downloads?”). Enforcement is the jail supervisor / FUSE, reading a `capabilities` table.
- Not LUKS (phase 2) and not login RLS (phase 1). Those protect the machine at rest and SQL rows. The jail protects **one running tool** at runtime.
- **Not systemd, logind, or a D-Bus session bus.** Foreign ELFs (Chrome, Electron, Grok) *expect* those. We will not port them. Init and display.x cover the same jobs **natively**; leftovers are either a tiny POSIX file/env we already have, or a Chrome flag that turns the probe off.

v0 is **persist + convention**. It is **not** a security boundary. A hostile binary can still `open("/etc/passwd")` until v1 namespaces.

---

## No systemd — native substitutes

Foreign ELFs (Chrome, Electron, Grok, glib, NSS, fontconfig) probe for a systemd user session, logind, and D-Bus. We do **not** port those. Init and display.x cover the same jobs with POSIX files, env, and IPC. If a library cannot live without a bus, **that library does not ship** until we port it or wrap the binary with flags that disable the probe. Do not grow a compatibility daemon.

| ELF asks for | AOS native answer | Never |
|--------------|-------------------|--------|
| A window, input, clipboard | display.x + IPC (`input.key` / `input.mouse`) + Xvfb only inside the wrap | systemd user units, logind, Wayland |
| Browser chrome (tabs, URL bar, back/fwd) | Chrome's **own** toolbar inside the Xvfb framebuffer. Auckland `toolbar="about"` is the OS frame only. Do **not** use `--app=` (that hides Chrome's UI) and do **not** fake a browser toolbar in the window chrome | Auckland `toolbar="browser"` as a stand-in |
| Pointer over the wrap | display.x hides its cursor (`capture_mouse`) and chrome.x **paints a software arrow** on the copied framebuffer. Xvfb does not composite the X cursor into `Xvfb_screen0` | logind seat / Xorg hardware cursor |
| `$HOME`, `/tmp`, profile | jail dirs under `/data/sandboxes/<id>/` | writing the real `/` |
| Dynamic linker, extra `.so` | `/etc/ld.so.conf` + `/usr/lib/x86_64-linux-gnu`, `LD_LIBRARY_PATH` next to the ELF | Debian multiarch as a product |
| Keyboard for Xvfb | `xkbcomp` + `/usr/share/X11/xkb` | a systemd `keyboard-setup` service |
| `/dev/fd` (bash `>( )`) | `symlink /proc/self/fd → /dev/fd` in Init | — |
| GNU `bash` (Grok `run_terminal_command`) | `/bin/bash` from Buildroot | pretending BusyBox is bash |
| NSS (`libsoftokn3.so`, `libfreeblpriv3.so`, `.chk`, `libsqlite3.so.0`) | ship the **matching** modules + FIPS `.chk` next to `/opt/google/chrome/` + `LD_LIBRARY_PATH` / `NSS_LIBDIR`. Distro `.so` without `.chk` loads then dies with NSS `-8023` (`SEC_ERROR_NO_MODULE`) | a cert daemon |
| `/etc/machine-id` (32 hex) | Init writes it (`Init_WriteMachineId`). Not `systemd-machine-id-setup` | dbus machine-id service |
| Fonts (Skia “sans”) | one TTF + `fonts.conf` under `/usr/share/fonts` | fontconfig going to systemd |
| D-Bus (`org.freedesktop.DBus`) | **ignore**. Do not set `DBUS_SESSION_BUS_ADDRESS`. `--disable-features=Dbus`. Failures are noise | `dbus-daemon`, `systemd --user` |
| `XDG_SESSION_TYPE` / seat | env `XDG_SESSION_TYPE=x11` on the wrap. Display.x **is** the session | logind `XDG_SESSION_ID` |
| User documents | FileTree (later FUSE into the jail) | Chrome talking to Postgres |

Init's job: mounts, `/dev/fd`, jail mkdirs, machine-id, hostname. Display's job: windows, input, software/native cursor. The wrap (`chrome_ipc`) is the adapter: env, flags, missing `.so` files, software cursor.

---

## Two kinds of bytes

| Kind | Examples | Store | Visible in Tracker / `files` |
|------|----------|--------|------------------------------|
| **User data** | Documents, Downloads, project trees, anything an AI must not spray | FileTree → `/data/blobs/{uuid}.blob` | Yes |
| **Program private** | `$HOME/.chrome`, `$HOME/.grok`, shader cache, `/tmp` inside the jail | Quarantine volume under `/data/sandboxes/<id>/` | **No** |

UUIDStore already touches ext4. “Don’t touch disk” means **the process cannot *name* user files or the rest of the machine**, not that the kernel never `write()`s. Blast radius of a leaked Chrome cache is one sandbox directory. Blast radius of leaked `~/Documents` is the failure.

```
                    ┌─ ~/Documents, ~/Downloads, ~/Projects
                    │    FileTree (PG + UUID blobs)
                    │    v2: FUSE POSIX costume + capability check
sandbox
                    └─ $HOME/.chrome, $HOME/.grok, /tmp
                         quarantine dir / overlay upper / loop image
                         not in `files`, wiped with the sandbox
```

---

## Layers (keep them un-collapsed)

| Name | Meaning now | Later |
|------|-------------|--------|
| `packages` / `applets` | What software exists (chrome, grok, busybox `ls`) | Unchanged. No ACL columns. |
| `sandboxes` | A POSIX view for one package (or session×package) | Principal of a capability |
| `files` (VFFS) | System documents; Auckland apps | Object id for user paths |
| `users` / `sessions` | Who is sitting at the glass | Subject of a capability |
| `capabilities` | **Not created in v0** | `(principal, object, verb)` |
| **display.x** | Windows, IPC, future allow-prompt UI | Never opens jail files |
| **init / jail supervisor** | mkdir (v0); unshare+mount (v1); start FUSE (v2) | Creates the ns, then exec |

Capabilities join **sandbox id** (and session), not `packages.can_exec`.

---

## On-disk layout (v0)

```
/data/blobs/{uuid}.blob          UUIDStore only (FileTree)
/data/sandboxes/
  chrome/
    home/                        $HOME  (uid of /home/bob)
      .chrome/                   --user-data-dir
    tmp/                         $TMPDIR, crash dumps
  grok/
    home/                        wrapper sets $HOME
      .grok/auth.json
    tmp/
```

Linux `/home/bob` stays an empty traditional dir for DropPriv uid lookup. It is **not** the Chrome profile and **not** the document tree (documents live in FileTree).

Xvfb framebuffers stay under `/tmp/chrome_fb` (ephemeral shm). That is display memory, not user data.

---

## Phases

### v0 — persist (this slice)

- Init creates `/data/sandboxes/{chrome,grok}/{home,tmp}`.
- Chrome: `HOME` + `--user-data-dir` + `TMPDIR` point at the chrome jail. **Stop deleting** the profile on cleanup.
- Grok: `/system/bin/grok` is a wrapper; real binary is `/system/libexec/grok`. Wrapper forces `HOME` / `TMPDIR` / `SSL_CERT_FILE`.
- Catalog row in `sandboxes`. No FUSE, no unshare, no capability checks.
- Honest label: **convention**, not confinement.

### v1 — mount namespace (kernel already has the knobs)

Guest kernel: `CONFIG_USER_NS`, `OVERLAY_FS`, `FUSE_FS`, `9P_FS`, `SECCOMP`. Busybox **does not** ship `unshare`; v1 needs util-linux `unshare` (or raw `unshare(2)` from Ailang).

Then:

- `unshare -m` (and later net)
- Overlay: image `/usr` `/lib` `/bin` read-only + writable `upper/`
- Bind jail `home` → `$HOME`, jail `tmp` → `/tmp`
- Do **not** mount `/data/blobs` or other sandboxes
- Drop bounding set (`CAP_SYS_ADMIN`, `CAP_NET_RAW`, …); Chrome can drop `--no-sandbox` only when this is real
- Optional 9p: host repo bind into a **dev** jail only

This is the CONTRIBUTING.md “X11 Application Sandbox Hardening” item, with a persistent home instead of `/tmp`.

### v2 — FUSE user data + capabilities

FUSE projects FileTree at `~/Documents` (and optionally `~/Downloads`) **inside** the jail. Every `open()` on those prefixes hits FileTree. Capability row:

```
principal     = sandbox id + session
object_kind   = path_prefix | files_id | applet | net
object        = /home/user/Documents
verb          = read | write | exec | net
```

display.x may show the grant UI. The FUSE daemon (or supervisor at launch) **enforces**. Init does not become a file server; display.x does not `open()` blobs for Chrome.

---

## Porting a foreign application

Four questions. Never both FileTree and raw `/` in one process.

1. **Display** — Auckland native, Xvfb wrap (Chrome today), or Vulkan later.
2. **FS** — always a sandbox POSIX tree for Linux ELFs. Auckland apps keep FileTree.
3. **Net** — capability later; today QEMU user-net.
4. **Identity** — session user; `$HOME` in the jail; not root when DropPriv exists.

IPC wrap (chrome_ipc / vscode_ipc) already isolates the **GUI** (own X display, no `/dev/fb0`). The jail isolates the **disk**. Together they are the foreign-app story until a native port.

Shared-library chase is automated: `tools/bundle_foreign.py` (DT_NEEDED walk, skip glibc, copy extras/dlopen plugins). See `docs/aos/PORTING_FOREIGN.md`.

---

## Schema (orthogonal catalog)

```sql
CREATE TABLE IF NOT EXISTS sandboxes (
  id        TEXT PRIMARY KEY,     -- 'chrome', 'grok'
  package   TEXT NOT NULL,        -- packages.name
  root_path TEXT NOT NULL,        -- /data/sandboxes/chrome
  kind      TEXT DEFAULT 'quarantine'  -- quarantine | overlay | fuse
);
```

No `allowed_paths`, no `can_net`. Those are `capabilities` later.

---

## Failure modes we accept in v0

- Process can still read `/etc`, `/home`, `/data` if it tries. Fix in v1.
- Terminal login shell still `HOME=/root` (root admin TTY). Grok **wrapper** ignores that and uses the grok jail.
- VS Code still uses `/tmp/vscode_ailang_profile` until the same pattern is copied.
- FUSE not mounted: Tracker/Document remain the only FileTree clients. Chrome cannot see documents, which is correct (no grant yet).

---

## Relationship to other AOS docs

| Doc | Boundary |
|-----|----------|
| phase1 RLS / pgcrypto / login | Who may see SQL rows. Not runtime tool jails. |
| phase2 LUKS | Encryption at rest after login. Complements, does not replace, jails. |
| FileTree / UUIDStore | User-data API. Only UUIDStore opens `/data/blobs`. |
| display/* | Windowing. Prompt UI later; no FS enforcement. |
| CONTRIBUTING X11 sandbox | v1 namespaces / seccomp on the same chrome_ipc fork path. |

---

## Implementation map (v0)

| Piece | Where |
|-------|--------|
| mkdir jails | `OS/Init.ailang` `Init_PrepareFS` |
| catalog | `OS/Schema.ailang` `sandboxes` + seed |
| Chrome HOME / profile / tmp | `Applications/chrome_ipc.ailang` |
| Do not wipe profile | `Chrome_CleanupStaleXvfb` |
| Grok wrapper | `config/grok.sh` → overlay `/system/bin/grok` |
| Grok binary | overlay `/system/libexec/grok` |
| Auth | `/data/sandboxes/grok/home/.grok/auth.json` (and build overlay) |
| GNU bash 5.2 | `/bin/bash` (Buildroot `BR2_PACKAGE_BASH`). Grok's `run_terminal_command` execs bash, not busybox ash. BusyBox is built with `CONFIG_BASH_IS_NONE`. |
| `/etc/machine-id` | `OS/Init.ailang` `Init_WriteMachineId` |
| Chrome native toolbar | `Applications/chrome_ipc.ailang` — no `--app=`; URL as a regular argument |
| Software cursor | `Chrome_BlitCursor` after each framebuffer copy |
| NSS + sqlite | overlay `/opt/google/chrome/libsoftokn3.so` + `libsqlite3.so.0`; wrap sets `LD_LIBRARY_PATH` |
