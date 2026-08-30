# Device interfaces — chrome and access, not kernel services

**Claim**: AOS already has (or will have) kernel drivers and firmware on disk. The weakness is **window chrome and access**: Ailang talking to `/dev` and sysfs the way `wifi_ipc` talks to `iw` / `wpa_supplicant`. Not NetworkManager, bluetoothd, Pulse, CUPS, or udev.

**Policy**: no systemd, no D-Bus session, no compatibility daemon. Fork the smallest helper that speaks the kernel API, or raw ioctl. Display.x owns glass + HID. MediaCenter should own ALSA.

---

## What already has an OS face

| Device | Kernel / node | AOS interface | Notes |
|--------|----------------|---------------|--------|
| Keyboard / mouse | hid/evdev `/dev/input/event*` | display.x `DInputDiscover` + `Evdev_Poll`; rescan ~60 frames | Works. USB HID, not hidraw. |
| Framebuffer | `/dev/fb0` | SysDisplay mmap | Works. No DRM/KMS ioctl yet. |
| Ethernet | NIC + `udhcpc` | Init once at boot | Works, no settings UI. |
| Wi-Fi | nl80211 | `wifi_ipc` + `config/wifi.html`: `iw` scan, write `/etc/wpa_supplicant.conf`, `wpa_supplicant -D nl80211,wext`, `udhcpc` | **Template.** Flaky: no rfkill, persist/reconnect, tray, signal/security parse. Init auto-connect only if `wlan0` + conf exist. |
| Theme / font sizes | — | Settings | Not devices. |
| Screenshot | fb | `sys.screenshot` → BMP | Works. |
| GPU research | PCI BAR | `Librarys/Drivers/AMDGPU` | Not the desktop compositor path. |

Postgres: **only `wifi` is a hardware config app.** Display is the only hardware-owning **autostart** service.

---

## Missing chrome / access (the real list)

| Need | Intended face | Today |
|------|----------------|--------|
| Volume / default sink | MediaCenter owns `/dev/snd/pcmC*`; deskbar volume via `controlC*` | `AudioEngine` raw ALSA ioctl exists. **Not** a `services` row. `videoplayer` can open the same PCM and fight it. Chrome wrap is `--mute-audio`. |
| Wi-Fi reliability | same `wifi_ipc` | `/dev/rfkill` unblock, saved nets, deskbar status. |
| Ethernet UI | extend wifi/net window | Init DHCP only. |
| Print | DocRaster Letter/A4 page → BMP → `/dev/usb/lp*` | Spec only (`DOCUMENT_FACILITY.md`). `usblp` is kernel. No CUPS. |
| Display outputs | Settings: mode, scale | Guest locked to boot EDID. DRM/KMS belongs **inside display.x**, not a daemon. |
| Bluetooth pair | `bt_ipc` like wifi | Kernel `CONFIG_BT` still off on current defconfig; no HCI UI. Do **not** ship bluetoothd+D-Bus as the product. |
| Power / battery | sysfs `power_supply` | Chrome already fails UPower/D-Bus. |
| USB “what’s plugged in” | read `/sys/bus/usb` | HID just appears as evdev. No udev/mdev; nodes are **devtmpfs**. Init modprobe is **PCI modalias only**. |
| Airplane / rfkill | one control | Missing. |

---

## Pattern (copy wifi, do not invent buses)

1. Auckland window (`config/<name>.html`).
2. Register with display (`service":"<name>"`).
3. Fork the smallest userspace that speaks the kernel (`wpa_supplicant`, `iw`, raw `/dev/snd`, `usblp`).
4. Persist in a file and/or PG `settings`.
5. Optional `autostart` only if it must **own** a node (display owns fb+evdev; MediaCenter should own ALSA).

**Do not** add NetworkManager, PipeWire, bluetoothd, CUPS, Weston, or udev to “fill the gap.” Those are the systemd-shaped holes we refused for Chrome.

---

## Ranked work

1. Wi-Fi persist + rfkill (finish the only existing device UI).
2. MediaCenter **as a service** + volume chrome; test on real HDA speakers.
3. DRM/KMS in display.x (library).
4. Print: DocRaster → BMP → usblp.
5. Bluetooth last (kernel option + non-D-Bus helper).

Firmware on disk: `docs/aos/FIRMWARE.md`. Jail / no systemd: `docs/aos/SANDBOX_JAIL.md`.
