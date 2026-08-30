# Firmware on disk

**Policy**: a released AOS image ships **all** `linux-firmware` blobs under `/lib/firmware`. Users must never hunt `iwlwifi-*.ucode` or `i915/kbl_dmc_*.bin`.

**Status**: bake-time. `build_image.sh` `stage_all_firmware` runs `copy-firmware.sh` from linux-firmware 20240115 into the rootfs overlay. Buildroot kconfig also has every `BR2_PACKAGE_LINUX_FIRMWARE_*` set. Packed rootfs is **8G** so the tree fits; the GPT disk is 16G and `growroot` stretches ext4 on first boot.

## Why kconfig alone is not enough

Buildroot's `linux-firmware` package only copies **selected** files/dirs. An unset bool means that blob is absent even if `BR2_PACKAGE_LINUX_FIRMWARE=y`. The overlay copy is the whole WHENCE tree (plus generated symlinks).

## Early-boot caveat (not a missing file)

Built-in drivers (`CONFIG_DRM_I915=y`, `CONFIG_CFG80211=y`) request firmware **before** rootfs is mounted. Files on `/lib/firmware` do not help that first probe. Symptom: dmesg `firmware: failed to load …` at 0.2s, then a later load after Init mounts `/`. Fix later: `CONFIG_EXTRA_FIRMWARE` in the kernel, or load those drivers as modules after rootfs. That is Init/kernel, not “download this blob.”

## Related

- OS-side device **UI** (wifi, volume, print): `docs/aos/DEVICE_INTERFACES.md`
- Jail / no systemd: `docs/aos/SANDBOX_JAIL.md`
