#!/usr/bin/env python3
"""Convert amsynth .bank files to SynthKit JSON patches."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# amsynth: 0 sine, 1 square/pulse, 2 triangle, 3 noise, 4 saw
# ours:    0 sine, 1 square, 2 pulse, 3 saw, 4 tri, 5 noise
WAVE_MAP = {0: 0, 1: 2, 2: 4, 3: 5, 4: 3}


def clamp(n: int, lo: int, hi: int) -> int:
    return lo if n < lo else hi if n > hi else n


def f(p: dict, k: str, d: float = 0.0) -> float:
    try:
        return float(p.get(k, d))
    except ValueError:
        return d


def convert_preset(name: str, p: dict, bank: str) -> dict:
    w1 = WAVE_MAP.get(int(f(p, "osc1_waveform")), 3)
    w2 = WAVE_MAP.get(int(f(p, "osc2_waveform")), w1)
    cut = clamp(int((f(p, "filter_cutoff") + 0.5) * 160), 0, 256)
    res = clamp(int(f(p, "filter_resonance") * 240), 0, 240)
    fenv = clamp(int(abs(f(p, "filter_env_amount")) * 18), 0, 256)
    det = clamp(int(abs(f(p, "osc2_detune")) * 80), 0, 80)
    mix = clamp(int(f(p, "osc_mix") * 256), 0, 256)
    o2 = int(f(p, "osc2_range"))
    o2oct = clamp(o2 + 2, 0, 4)
    pw = clamp(int(f(p, "osc1_pulsewidth") * 255), 8, 248)
    atk = clamp(int(f(p, "amp_attack") * 1000), 0, 2500)
    dec = clamp(int(f(p, "amp_decay") * 1000), 0, 2500)
    rel = clamp(int(f(p, "amp_release") * 1000), 0, 4000)
    sus = clamp(int(f(p, "amp_sustain") * 256), 0, 256)
    vol = clamp(int(f(p, "master_vol") * 256), 0, 320)
    lfo = clamp(int(f(p, "lfo_freq") * 24), 0, 256)
    lff = clamp(int(abs(f(p, "filter_mod_amount")) * 256), 0, 256)
    lfa = clamp(int(abs(f(p, "amp_mod_amount")) * 256), 0, 256)
    wet = clamp(int(f(p, "reverb_wet") * 256), 0, 256)
    dms = clamp(int(f(p, "reverb_roomsize") * 900), 0, 1300)
    drv = clamp(int(f(p, "distortion_crunch") * 400), 0, 256)
    return {
        "format": "synthkit.patch.v1",
        "name": name,
        "source": {"kind": "amsynth", "bank": bank},
        "engine": {
            "wave": w1,
            "wave2": w2,
            "osc_mix": mix,
            "osc2_oct": o2oct,
            "cutoff": cut,
            "res": res,
            "delay_ms": dms,
            "delay_fb": clamp(int(f(p, "reverb_damp") * 200), 0, 250),
            "delay_wet": wet,
            "vol": vol,
            "atk_ms": atk,
            "dec_ms": dec,
            "rel_ms": rel,
            "sustain": sus,
            "oct": 2,
            "pw": pw,
            "detune": det,
            "fenv": fenv,
            "lfo_rate": lfo,
            "lfo_pwm": clamp(int(f(p, "osc1_pulsewidth") * 0), 0, 256),
            "lfo_filt": lff,
            "lfo_amp": lfa,
            "submix": 0,
            "drive": drv,
        },
        "mod": {
            "value": 0,
            "slots": [
                {"dest": 1, "depth": 180},
                {"dest": 0, "depth": 0},
                {"dest": 0, "depth": 0},
            ],
        },
        "pending": {
            "amsynth": {k: v for k, v in p.items()},
        },
    }


def parse_bank(text: str) -> list[tuple[str, dict]]:
    presets = []
    cur_name = None
    cur: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("<preset>"):
            if cur_name is not None:
                presets.append((cur_name, cur))
            m = re.search(r"<name>\s*(.+)$", line)
            cur_name = (m.group(1).strip() if m else "untitled")
            cur = {}
        elif line.startswith("<parameter>"):
            rest = line[len("<parameter>") :].strip()
            parts = rest.split(None, 1)
            if len(parts) == 2:
                cur[parts[0]] = parts[1]
    if cur_name is not None:
        presets.append((cur_name, cur))
    return presets


def slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
    return s[:80] or "preset"


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/amsynth/banks")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "presets" / "amsynth")
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    files = sorted(src.glob("*.bank")) + sorted(src.glob("*.amSynth.bank"))
    for fp in files:
        text = fp.read_text(errors="replace")
        if not text.startswith("amSynth") and "<preset>" not in text:
            continue
        for name, params in parse_bank(text):
            patch = convert_preset(name, params, fp.name)
            out = dst / f"{slug(fp.stem)}__{slug(name)}.json"
            out.write_text(json.dumps(patch, indent=2) + "\n")
            n += 1
    print(f"wrote {n} patches to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
