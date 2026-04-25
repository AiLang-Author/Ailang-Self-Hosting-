# SSH Bullshit — resume point

## Status: SOLVED (capture working, hang reproduced, signature captured)

Next work is **debugging sysdisplay.x**, not setup.

## Goal
Capture sysdisplay.x stdout/stderr on Phenom II (Pop!_OS) before it hangs.
Log streamed to Ryzen Windows box over direct Cat6 link.

## Resolved setup

### Network (direct Cat6, no router between them)
- Phenom II: static `192.168.2.1/24` on `enp3s0`
- Ryzen Windows 10: static `192.168.2.2/24` on `Ethernet 2` (Realtek 2.5GbE)
  - Ryzen's Wi-Fi is 192.168.1.70 — different subnet, not used for this link
- Set the Ryzen side with (admin PowerShell, one-time; persists across reboots):
  `New-NetIPAddress -InterfaceAlias "Ethernet 2" -IPAddress 192.168.2.2 -PrefixLength 24`

### SSH from Ryzen
- OpenSSH client already installed (`OpenSSH.Client~~~~0.0.1.0`)
- **Not on PATH** — call by absolute path:
  `C:\Windows\System32\OpenSSH\ssh.exe bob@192.168.2.1`
- Host key already accepted + known_hosts

### Capture command (working)
At tty2 on the Phenom (or over SSH — hang reproduces either way):
```
sudo ./sysdisplay.x 2>&1 | tee /tmp/sysdisplay.log
```
- `tee` sidesteps a bash redirect issue we hit with `&>` (path ended up as argv[1], fd1/fd2 pointed to the invoking pts)
- Log lives at `/tmp/sysdisplay.log` (not `/dev/shm` — ran into perms issues there)
- Output echoes live to the invoking terminal AND writes to the log

## Hang signature (captured 2026-04-21)

Normal render loop is `SWAP.IN 0->1 root=0 cnt=8` → 8x `DRAW` → `SWAP.OUT 1->0`. Clean.

Hang trigger: a File-menu click fires this sequence and then freezes:
```
[ER_DRAIN] ptr=4703598 len=9 win=1 count=1
[EventRouter] menu:file
[Menu] Show id=0 win=1
[AKSlot] allocated slot 2
[SWAP.IN] 0->2 data=139400449359872 root=-1 cnt=0
```

Allocates a brand-new slot 2, then SWAP.IN-s into it with `root=-1 cnt=0` (empty/unrooted tree).
No subsequent `[AK] solved`, no DRAW, no SWAP.OUT. Dead there.

**Next debugging step**: grep sysdisplay source for the SWAP.IN path when `root=-1`. Probably unguarded loop or a wait that never fires.

## Post-hang recovery (what works, what doesn't)

- Hang is userspace-only — kernel + sshd stay alive, new SSH sessions connect fine
- `sudo pkill -9 sysdisplay.x` from a fresh SSH session kills the process cleanly
- **But**: framebuffer/VT stays wedged after the kill. sysdisplay.x owns `/dev/fb0` directly and doesn't restore mode on exit, so the monitor shows frozen pixels until reboot
- Tried and did NOT thaw the console:
  - `chvt 1 / chvt 2`
  - `printf '\x1bc' | sudo tee /dev/tty2` (VT100 full reset)
  - `systemctl restart display-manager` / `gdm3` (service not found by either name)
  - `echo 0/1/0 > /sys/class/graphics/fb0/blank` (screen blanks but unblanks to the same frozen image)
- **Only fix**: `sudo reboot`. System is otherwise fine via SSH; reboot is cosmetic.

## Outstanding todo (sysdisplay.x itself)

1. **Fix the root=-1 SWAP.IN hang** — primary bug
2. **Add teardown on exit signals** — so SIGINT/SIGTERM restore VT text mode instead of leaving the fb wedged. Crucial for iterative debugging; otherwise every crash costs a reboot.
3. **Enable sysrq** for last-resort recovery (not currently critical since SSH works through hangs):
   `echo kernel.sysrq=1 | sudo tee /etc/sysctl.d/99-sysrq.conf && sudo sysctl --system`

## Deferred (if SSH-level logging ever isn't enough)
- netconsole kernel module → streams printk via UDP, catches true kernel hangs:
  `modprobe netconsole netconsole=6666@192.168.2.1/enp3s0,9999@192.168.2.2/<ryzen-mac>`
- Ryzen listener: `ncat -u -l 9999 > kernel.log`
