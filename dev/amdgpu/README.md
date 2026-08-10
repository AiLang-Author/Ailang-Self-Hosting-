# AMD GPU / GCN driver development kit

Bring-up tooling and notes for **Southern Islands / GCN 1.x** work that backs
`Librarys/Accel/` and `Librarys/Drivers/AMDGPU/`.

This is **developer infrastructure**, not an end-user library. The long-term
goal is a usable AILang-side GPU stack; these scripts are how that stack is
debugged against real hardware and Linux amdgpu/radeon behavior.

## Layout

```
dev/amdgpu/
├── tools/           # Python probes, MMIO trace compare, PCI capture helpers
├── notes/           # Handoffs, crash postmortems, init-sequence writeups
├── reference/       # ISA text, scraped kernel amdgpu docs
├── fw_trace/        # Firmware / DPM / RLC extractors from traces
└── traces/          # Local dumps only — gitignored (do not commit)
```

## Tools (overview)

| Area | Scripts (examples) |
|------|---------------------|
| Probe / BAR / HDP / VRAM | `gpu_probe*.py`, `gpu_vram_diag.py`, `gpu_hdp_*.py` |
| MTRR / PAT / cache attrs | `gpu_mtrr_*.py`, `gpu_pat_fix.py`, `gpu_cache_diag.py` |
| PCIe / cold boot | `gpu_pcie_diag.py`, `gpu_coldboot_test.py`, `gpu_first_access.py` |
| Trace analysis | `compare_traces*.py`, `parse_mmiotrace.py`, `extract_init_seq.py` |
| Capture helpers | `radeon_trace_*.sh`, `capture_working_pci.sh`, `gpu-mmiotrace.service` |

Run from this directory or pass absolute paths; many scripts assume host
access to sysfs / MMIO and need root or appropriate permissions.

## Related product code

- `Librarys/Accel/` — GCN HAL, dispatch, init, submit
- `Librarys/Drivers/AMDGPU/` — higher-level driver pieces
- `kernel_module/` — Linux module experiments (if present)

## Traces and blobs

Keep under `traces/` (or leave root-owned dumps where the OS put them):

- `mmiotrace_*`, `bus2_*.txt`, `*.rom` VBIOS dumps, `dmesg_*.txt`

These are **gitignored**. Useful tooling stays in `tools/` and is tracked.
