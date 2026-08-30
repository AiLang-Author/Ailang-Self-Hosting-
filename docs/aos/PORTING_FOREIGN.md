# Porting a foreign Linux app (Chrome, VS Code, Xvfb)

Not apt. Not wrap-to-widget. Copy the ELF, jail its `$HOME`, wrap the GUI.

## Four questions

Never both FileTree and raw `/` in one process.

1. **Display** — Auckland native, or Xvfb wrap (`chrome_ipc` / `vscode_ipc`).
2. **FS** — quarantine `$HOME` / `$TMPDIR` under `/data/sandboxes/<id>/`.
3. **Net** — QEMU user-net today; capability later.
4. **Identity** — DropPriv to the session uid; jail is that uid.

## Library resolution (the thing we kept doing by hand)

`DT_NEEDED` is mechanical. `dlopen("libsoftokn3.so")` is not. Automate the first; list the second per app.

```bash
# Shared libs for an ELF → overlay (do not copy glibc)
tools/bundle_foreign.py \
  --elf /usr/bin/Xvfb \
  --dest /home/bob/buildroot/board/ailang_os/rootfs_overlay/usr/lib

# Chrome: also dump the directory of plugins + NSS checksums
tools/bundle_foreign.py \
  --elf /opt/google/chrome/chrome \
  --also-dir /opt/google/chrome \
  --extra 'libsoftokn3.so' --extra 'libfreeblpriv3.so' --extra '*.chk' \
  --dest overlay/opt/google/chrome \
  --env-out overlay/opt/google/chrome/ld.env
```

**Copy:** anything `NEEDED` except glibc (`libc`, `ld-linux`, `libpthread`, `libm`, …). **Including** `libsystemd.so.0` / `libselinux.so.1` if the ELF links them — that is a file, not a daemon.

**Do not copy:** guest already has a libc. Host `resize2fs` died with `undefined symbol` because we mixed libcs.

**Prefer Buildroot-built helpers** (`Xvfb`, `xkbcomp`) over host Debian binaries so the NEEDED set matches guest glibc. Host Xvfb dragged in `libsystemd.so` only because it was a Debian ELF.

**dlopen extras** (must be named; ldd will not see them):

| App | Extra |
|-----|--------|
| Chrome NSS | `libsoftokn3.so`, `libfreebl3.so`, `libfreeblpriv3.so`, `libnssckbi.so`, matching `.chk`, `libsqlite3.so.0` |
| Fontconfig/Skia | `/etc/fonts/fonts.conf` + one TTF (not an `.so`) |
| Xvfb | `xkbcomp` + `/usr/share/X11/xkb` (not an `.so`) |

The wrap sets `LD_LIBRARY_PATH=<jail-or-opt>:/usr/lib`.

## Non-library files the wrap still owes

See `SANDBOX_JAIL.md` native substitutes: `/etc/machine-id`, `/dev/fd`, jail tmp as tmpfs, `--disable-features=Dbus`, empty D-Bus is noise.

## Recipe checklist

1. Place ELF tree under `/opt/<app>/` (or overlay).
2. `bundle_foreign.py` into that tree + extras.
3. `packages` / `applets` / `sandboxes` rows.
4. Auckland wrap (clone chrome_ipc): jail HOME, Xvfb, shm canvas, xdotool.
5. Deskbar service.

VS Code is this recipe with `vscode_ipc.ailang` (still `/tmp` profile — copy Chrome’s jail).
