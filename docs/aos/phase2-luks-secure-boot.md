# Phase 2: LUKS Encryption & Secure Boot Ordering

**Status**: Deferred (requires Phase 1 completion)
**Prerequisites**: RLS + pgcrypto + Login validation working

---

## Overview

This phase adds full encryption at rest and restructures the boot sequence so that no data, network, or services are accessible until the device owner authenticates. This is the core containment mechanism — a rogue AI/LLM agent cannot access the encrypted database without the human operator's password.

**Boot flow after this phase:**
```
Power on → Mount rootfs → Load drivers → Login screen → Unlock LUKS → Start PG → Network → Services
```

---

## Part A: LUKS Encrypted PG Data Partition

### A.1 Infrastructure Requirements

**Kernel config** (`board/ailang_os/linux_alldrv.config`):
```
CONFIG_DM_CRYPT=y
CONFIG_CRYPTO_XTS=y
CONFIG_CRYPTO_SHA256=y
CONFIG_CRYPTO_AES=y
CONFIG_CRYPTO_USER_API=y
CONFIG_CRYPTO_USER_API_HASH=y
CONFIG_CRYPTO_USER_API_SKCIPHER=y
```

**Buildroot packages** (`board/ailang_os/buildroot_defconfig`):
```
BR2_PACKAGE_CRYPTSETUP=y
BR2_PACKAGE_LVM2=y
BR2_PACKAGE_JSON_C=y
BR2_PACKAGE_POPT=y
```

After enabling, full Buildroot rebuild required: `make clean && make`

### A.2 Disk Layout (3-Partition GPT)

```
Current (2 partitions):
  P1: EFI System (FAT32)     — 200MB    (sectors 2048-409599)
  P2: Linux rootfs (ext4)    — ~2100MB  (sectors 409600-end)

New (3 partitions):
  P1: EFI System (FAT32)     — 200MB    (sectors 2048-409599)
  P2: Linux rootfs (ext4)    — ~1835MB  (sectors 409600-4194303)
  P3: PG Data (LUKS2+ext4)   — ~500MB   (sectors 4194304-end)
```

Partition 3 ships UNFORMATTED in the disk image. The first-boot Installer handles LUKS formatting.

### A.3 LUKS Key Strategy

The user's login password IS the LUKS passphrase directly. No custom key derivation needed — LUKS2 internally applies Argon2id with configurable memory/time parameters for key stretching.

**Why this works:**
- LUKS2 Argon2id provides brute-force resistance (memory-hard, time-configurable)
- Single password for login + disk unlock = simpler UX
- No key material stored on disk (password lives only in user's memory)

### A.4 First-Boot LUKS Setup

During first boot (no LUKS header detected on P3):

```
1. Init detects first boot: cryptsetup isLuks /dev/vda3 → fails
2. Init launches Installer in "first-boot" mode
3. Installer collects username + password from user
4. Installer executes:
   a. cryptsetup luksFormat /dev/vda3 --batch-mode --type luks2
      (password piped to stdin)
   b. cryptsetup luksOpen /dev/vda3 pgdata
      (password piped to stdin)
   c. mkfs.ext4 /dev/mapper/pgdata
   d. mount /dev/mapper/pgdata /var/lib/postgresql/data
5. Installer runs initdb, starts PG, bootstraps schema
6. Installer creates user with bcrypt-hashed password
7. Installer generates recovery key:
   a. recovery_key = 32 random hex chars
   b. cryptsetup luksAddKey /dev/vda3 (recovery key as new keyslot)
   c. Display recovery key to user ONCE
8. Normal boot continues
```

### A.5 Runtime LUKS Unlock (Every Boot After First)

```
1. Init mounts rootfs (kernel cmdline)
2. Init mounts /proc, /sys, /dev, /tmp, /run
3. Init loads boot config, hostname, kernel modules
4. Init waits for input devices (keyboard)
5. Init calls Login_Run() → user enters password
6. Init pipes password to cryptsetup:

   [pipe_write_fd] ← password bytes
   fork() → child:
     dup2(pipe_read_fd, 0)  // redirect stdin
     execve("/usr/sbin/cryptsetup",
            ["cryptsetup", "luksOpen", "/dev/vda3", "pgdata", "--key-file=-"],
            envp)
   parent:
     close(pipe_write_fd)
     waitpid(child) → check exit code

7. If exit code 0: mount /dev/mapper/pgdata /var/lib/postgresql/data
8. If exit code != 0: wrong password → retry (max 3 attempts)
9. Login_SecureClear() → zero password from memory
10. Start PostgreSQL on decrypted volume
11. Continue boot (network, services)
```

### A.6 Partition Discovery

Boot config (`/etc/ailang_boot.conf`):
```
luks_partition=/dev/vda3
luks_name=pgdata
luks_mount=/var/lib/postgresql/data
```

For real hardware: use `/dev/disk/by-partuuid/<uuid>` for stability.

### A.7 New Syscall Constants

```
SYS_PIPE  = 22   // pipe(int pipefd[2])
SYS_DUP2  = 33   // dup2(int oldfd, int newfd)
```

### A.8 build_image.sh Changes

```bash
# Partition layout
ROOTFS_END_SECTOR=4194303
PGDATA_START_SECTOR=4194304
IMAGE_SIZE_MB=3000

# Create partition 3 (unformatted)
parted -s "$DISK_IMAGE" mkpart pgdata ext4 ${PGDATA_START_SECTOR}s 100%

# Remove PG data pre-population step entirely
# (encrypted installs use Installer for first-boot setup)
```

---

## Part B: Secure Boot Ordering

### B.1 New Boot Sequence

```
Phase A: Minimal System (NO network, NO PG)
  ├─ Mount essential filesystems (proc, sys, dev, tmp, run)
  ├─ Load boot config
  ├─ Set hostname
  ├─ Load kernel modules (evdev for keyboard, dm-crypt)
  └─ Wait for input devices

Phase B: Authentication Gate
  ├─ Login_Run() → framebuffer login screen
  ├─ User enters credentials
  └─ On cancel/3 failures → system halts

Phase C: Unlock Encrypted Storage
  ├─ Init_UnlockLUKS(password, pass_len)
  ├─ mount /dev/mapper/pgdata /var/lib/postgresql/data
  └─ Login_SecureClear() → zero password from memory

Phase D: Start PostgreSQL
  ├─ chown data dir to postgres (121:124)
  ├─ Start PG process (fork/exec as UID 121)
  └─ Wait for PG ready (TCP poll 127.0.0.1:5432)

Phase E: Network (DEFERRED until after auth)
  ├─ DHCP/static IP setup
  ├─ WiFi auto-connect
  └─ Start SSHD

Phase F: Services + Watchdog
  ├─ Start service daemon
  └─ Watchdog loop (restart PG/svc_daemon/sshd on crash)
```

**Key security property**: No network interface is brought up until AFTER the human authenticates. A rogue AI cannot exfiltrate data or communicate externally without the operator unlocking the system.

### B.2 Login-to-Init Password Transfer API

Login.ailang currently zeros the password buffer before returning. For LUKS unlock, Init needs the password AFTER login succeeds.

**New Login API:**

```ailang
// Login_Run() — modified behavior:
//   On SUCCESS: password remains in LoginState.pass_buf (caller must zero)
//   On FAILURE: password is zeroed immediately
Function.Login_Run { Output: Integer }

// Get raw password buffer (for piping to cryptsetup)
Function.Login_GetPassword { Output: Address }

// Get password length in bytes
Function.Login_GetPasswordLen { Output: Integer }

// Explicit secure cleanup (Init calls this after LUKS unlock)
Function.Login_SecureClear {
    Body: {
        MemorySet(LoginState.pass_buf, 0, LoginConst.MAX_PASS)
        MemorySet(LoginState.user_buf, 0, LoginConst.MAX_USER)
        Deallocate(LoginState.pass_buf, LoginConst.MAX_PASS)
        Deallocate(LoginState.user_buf, LoginConst.MAX_USER)
        LoginState.pass_len = 0
        LoginState.user_len = 0
    }
}
```

### B.3 Wrong Password / Retry Logic

```
attempt = 0
max_attempts = 3

loop:
  login_result = Login_Run()
  if login_result == 0: halt (user cancelled)

  luks_ok = Init_UnlockLUKS(Login_GetPassword(), Login_GetPasswordLen())
  if luks_ok == 1: break (success)

  Login_SecureClear()
  attempt += 1
  if attempt >= max_attempts:
    print "FATAL: LUKS unlock failed after 3 attempts. Halting."
    halt

Login_SecureClear()  // zero after successful unlock
```

### B.4 First-Boot Detection

```ailang
Function.Init_IsFirstBoot {
    Output: Integer  // 1 = first boot, 0 = normal
    Body: {
        // Fork/exec: cryptsetup isLuks /dev/vda3
        // Exit code 0 = LUKS formatted (normal boot)
        // Exit code != 0 = not LUKS (first boot)
    }
}
```

On first boot: skip Login, launch Installer directly. Installer handles LUKS setup + user creation.

### B.5 Recovery Mode

**Recovery key:**
- Generated during first-boot: 32 random hex chars (128 bits entropy)
- Stored as LUKS keyslot 1 (user password is keyslot 0)
- Displayed to user ONCE during setup — must be written down
- Format: `XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX`

**Recovery boot:**
- Kernel cmdline parameter: `recovery=1`
- Init detects recovery flag in boot config
- Shows "Recovery Key" input instead of normal login
- On successful LUKS unlock via recovery key:
  - Boot into recovery shell
  - Allow password reset via PG UPDATE
  - Allow LUKS keyslot change

**No backdoor:** Without recovery key OR password, data is permanently unrecoverable. This is intentional for a containment OS.

### B.6 Multi-User Considerations

**Design decision: Single LUKS owner + RLS for additional users**

- First user's password unlocks LUKS (device owner)
- Additional users authenticate via display server login screen AFTER boot
- Additional user auth uses PG bcrypt (same as Phase 1)
- RLS provides logical isolation between users
- LUKS provides physical isolation from offline/cold-boot attacks

**Alternative (future):** Store all user passwords as LUKS keyslots (max 8 in LUKS2). Any authorized user can boot the device.

---

## Files to Modify

| File | Changes |
|------|---------|
| `board/ailang_os/linux_alldrv.config` | Enable CONFIG_DM_CRYPT and crypto modules |
| `board/ailang_os/buildroot_defconfig` | Enable BR2_PACKAGE_CRYPTSETUP + dependencies |
| `build_image.sh` | 3-partition GPT layout, remove PG pre-population |
| `OS/Init.ailang` | Complete Main restructure: deferred network, Init_UnlockLUKS(), Init_IsFirstBoot(), SYS_PIPE/SYS_DUP2, retry logic |
| `OS/Login.ailang` | Login_GetPassword(), Login_GetPasswordLen(), Login_SecureClear(); preserve password on success |
| `OS/Installer.ailang` | First-boot LUKS format flow, recovery key generation, initdb + schema bootstrap |
| `config/ailang_boot.conf` | Add luks_partition, luks_name, luks_mount, recovery flag |

---

## Security Properties

| Property | Mechanism |
|----------|-----------|
| Data at rest encrypted | LUKS2 AES-XTS-256 on PG partition |
| Key stretching | LUKS2 Argon2id (memory-hard) |
| No network before auth | Init defers network setup until Phase E |
| No services before auth | Service daemon starts after PG, which starts after LUKS unlock |
| Password not on disk | Lives only in user memory; LUKS derives key at unlock time |
| Memory cleanup | Login_SecureClear() zeros password after LUKS unlock |
| Brute-force protection | 3 attempts then halt; Argon2id adds ~1s per attempt |
| Offline attack resistance | Without password, partition 3 is random bytes |
| Rogue AI containment | No exfiltration possible before human unlocks |
| Recovery | Single-use recovery key in LUKS keyslot 1 |

---

## Verification

| Test | Expected |
|------|----------|
| Boot with correct password | LUKS unlocks, PG starts, desktop loads |
| Boot with wrong password | "LUKS unlock failed", retry offered |
| 3 wrong passwords | System halts |
| Mount disk image offline, read P3 | Random bytes (encrypted) |
| First boot (no LUKS header) | Installer launches, LUKS formatted |
| Recovery key boot | Unlocks LUKS, recovery shell available |
| Network check before login | No interfaces up, no DHCP, no SSH |
| `strace` password memory | Zeroed after Login_SecureClear() |

---

## Dependencies

```
Phase 1 (RLS + pgcrypto + Login)
  ↓ must be complete and tested
Phase 2A (LUKS partition)
  ↓ requires kernel + buildroot rebuild
Phase 2B (Secure boot ordering)
  ↓ requires LUKS working
Full containment achieved
```
