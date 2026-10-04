# OS code status

Checked against the tree on 2026-10-03. This is what the source does, not the plan.

## In this directory

`Init.ailang` is PID 1. It mounts the early filesystems, creates the chrome and grok sandbox directories, can show login, starts PostgreSQL, and watches those children. `Login.ailang` checks `crypt()` against `users.password_hash`. `Schema.ailang` creates the tables, seeds the default user with bcrypt, and seeds two `sandboxes` rows. There is no `ROW LEVEL SECURITY` in that file.

`FileTree.ailang` plus `UUIDStore.ailang` are a PostgreSQL directory index and `/data/blobs/{uuid}.blob`. The operations are implemented. The only caller is `TestFileTree.ailang`. Nothing in the display server or the jails opens that tree.

`ServiceDaemon.ailang` and `Installer.ailang` are in this directory with their tests.

## Not finished

Sandbox v0 is a directory convention (`HOME`, `TMPDIR`, tmpfs). The kernel config does not enable user namespaces, overlayfs, or FUSE, so v1 and v2 in `docs/aos/SANDBOX_JAIL.md` cannot run on the current board config.

The desktop is HTML. Window clients live in `Applications/*_ipc.ailang` (17 files) and send `window.create` with an html path. `Library.AucklandBind` parses it. Those files stay in the compiler repository because the display libraries stay there.

## Screen

`FB_Init` uses the mode already on `/dev/fb0` and `FB_RGB` packs BGRA. QEMU should be launched with `./run_aos.sh` (`bochs-display` 1152×864). `virtio-vga` size flags are ignored on this QEMU.
