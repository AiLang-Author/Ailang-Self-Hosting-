#!/usr/bin/env python3
"""
workbench_design.py — Apply Workbench Reborn design language to app icons and widgets.

Reference: Design-Language- Refrence/ (Palette, Icon set, System widgets)

Copyright © 2026 Sean Collins / AILANG project.
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Palette (from Palette.png) ---
VOID = "#060912"
ABYSS = "#0a1020"
NAVY = "#0e1730"
STEEL = "#16223f"
CYAN = "#2ad4ff"
AZURE = "#4a8cff"
VIOLET = "#a96bff"
MAGENTA = "#e25bd8"
GREEN = "#3ddc97"
AMBER = "#e8b030"
INK = "#e8eef8"
DIM = "#7a8aaa"
MUTE = "#4a5a72"
BORDER = "#2a4068"

STROKE_W = "1.6"
STROKE_ATTRS = (
    f'fill="none" stroke-width="{STROKE_W}" '
    'stroke-linecap="round" stroke-linejoin="round"'
)

COLORS = {
    "cyan": CYAN,
    "azure": AZURE,
    "violet": VIOLET,
    "magenta": MAGENTA,
    "green": GREEN,
    "amber": AMBER,
    "ink": INK,
    "dim": DIM,
}


def _path(color: str, d: str) -> str:
    return f'<path d="{d}" {STROKE_ATTRS} stroke="{color}"/>'


# Glyph library — 24×24 content area centered in 32×32 (offset ~4,4)
GLYPHS: dict[str, str] = {}

def _g(name: str, *paths: str) -> None:
    GLYPHS[name] = "\n  ".join(paths)


_g("folder_open",
   _path("{c}", "M8 13 L8 24 L24 24 L24 15 L19 15 L17 13 Z"),
   _path("{c}", "M8 13 L17 13 L19 15 L24 15"))
_g("folder_closed",
   _path("{c}", "M8 14 L8 24 L24 24 L24 17 L18 14 Z"))
_g("document",
   _path("{c}", "M10 9 L20 9 L20 23 L10 23 Z"),
   _path("{c}", "M16 9 L20 13 L16 13 Z"))
_g("shell",
   _path("{c}", "M9 12 L15 16 L9 20"),
   _path("{c}", "M17 20 L21 20"))
_g("code",
   _path("{c}", "M12 10 L8 16 L12 22"),
   _path("{c}", "M20 10 L24 16 L20 22"),
   _path("{c}", "M14 22 L18 10"))
_g("settings",
   _path("{c}", "M16 10 L16 8"),
   _path("{c}", "M16 24 L16 22"),
   _path("{c}", "M10 12 L8.5 10.5"),
   _path("{c}", "M23.5 21.5 L22 20"),
   _path("{c}", "M22 12 L23.5 10.5"),
   _path("{c}", "M8.5 21.5 L10 20"),
   _path("{c}", "M10 20 A6 6 0 1 0 22 20 A6 6 0 1 0 10 20"))
_g("monitor",
   _path("{c}", "M9 10 L23 10 L23 20 L9 20 Z"),
   _path("{c}", "M12 20 L12 23 L20 23 L20 20"),
   _path("{c}", "M14 23 L18 23"))
_g("globe",
   _path("{c}", "M16 9 A7 7 0 1 0 16 23 A7 7 0 1 0 16 9"),
   _path("{c}", "M9 16 L23 16"),
   _path("{c}", "M16 9 Q12 16 16 23"),
   _path("{c}", "M16 9 Q20 16 16 23"))
_g("envelope",
   _path("{c}", "M8 11 L24 11 L24 23 L8 23 Z"),
   _path("{c}", "M8 11 L16 17 L24 11"))
_g("trash",
   _path("{c}", "M10 12 L22 12"),
   _path("{c}", "M11 12 L11.5 23 L20.5 23 L21 12"),
   _path("{c}", "M13 9 L19 9 L18.5 12 L13.5 12 Z"))
_g("speaker",
   _path("{c}", "M11 14 L14 14 L18 11 L18 21 L14 18 L11 18 Z"),
   _path("{c}", "M20 13 Q22 16 20 19"),
   _path("{c}", "M22 11 Q25 16 22 21"))
_g("search",
   _path("{c}", "M14 10 A5 5 0 1 0 14 20 A5 5 0 1 0 14 10"),
   _path("{c}", "M18 18 L23 23"))
_g("user",
   _path("{c}", "M16 11 A3.5 3.5 0 1 0 16 18 A3.5 3.5 0 1 0 16 11"),
   _path("{c}", "M9 24 Q9 18 16 18 Q23 18 23 24"))
_g("lock",
   _path("{c}", "M11 14 L21 14 L21 23 L11 23 Z"),
   _path("{c}", "M13 14 L13 12 Q13 9 16 9 Q19 9 19 12 L19 14"))
_g("power",
   _path("{c}", "M16 9 L16 15"),
   _path("{c}", "M11 12 A7 7 0 1 0 21 12"))
_g("battery",
   _path("{c}", "M9 12 L9 21 L21 21 L21 12 Z"),
   _path("{c}", "M22 14 L23 14 L23 19 L22 19"),
   _path("{c}", "M11 14 L17 14"))
_g("clock",
   _path("{c}", "M16 9 A7 7 0 1 0 16 23 A7 7 0 1 0 16 9"),
   _path("{c}", "M16 13 L16 16 L19 18"))
_g("calculator",
   _path("{c}", "M10 8 L22 8 L22 24 L10 24 Z"),
   _path("{c}", "M12 11 L20 11"),
   _path("{c}", "M12 15 L14 15 M16 15 L18 15"),
   _path("{c}", "M12 19 L14 19 M16 19 L18 19"))
_g("alert",
   _path("{c}", "M16 9 L24 23 L8 23 Z"),
   _path("{c}", "M16 14 L16 18"),
   _path("{c}", "M16 20 L16 21"))
_g("info",
   _path("{c}", "M16 9 A7 7 0 1 0 16 23 A7 7 0 1 0 16 9"),
   _path("{c}", "M16 13 L16 14"),
   _path("{c}", "M16 17 L16 21"))
_g("help",
   _path("{c}", "M16 9 A7 7 0 1 0 16 23 A7 7 0 1 0 16 9"),
   _path("{c}", "M13 13 Q16 10 19 13 Q19 16 16 16 L16 19"))
_g("menu",
   _path("{c}", "M9 13 L23 13"),
   _path("{c}", "M9 16 L23 16"),
   _path("{c}", "M9 19 L23 19"))
_g("paint",
   _path("{c}", "M9 20 L18 11 L22 15 L13 24 Z"),
   _path("{c}", "M8 24 L14 24"))
_g("link",
   _path("{c}", "M11 17 Q9 15 11 13 Q13 11 15 13"),
   _path("{c}", "M17 15 Q19 17 17 19 Q15 21 13 19"))
_g("keyboard",
   _path("{c}", "M8 14 L24 14 L24 22 L8 22 Z"),
   _path("{c}", "M10 17 L12 17 M14 17 L16 17 M18 17 L20 17"),
   _path("{c}", "M12 20 L20 20"))
_g("image",
   _path("{c}", "M8 10 L24 10 L24 22 L8 22 Z"),
   _path("{c}", "M8 18 L13 14 L17 17 L24 12"),
   _path("{c}", "M18 12 A1.5 1.5 0 1 0 18 15 A1.5 1.5 0 1 0 18 12"))
_g("arrow_down",
   _path("{c}", "M16 10 L16 20"),
   _path("{c}", "M11 16 L16 21 L21 16"))
_g("arrow_up",
   _path("{c}", "M16 22 L16 12"),
   _path("{c}", "M11 16 L16 11 L21 16"))
_g("edit",
   _path("{c}", "M9 21 L13 21 L21 13 L17 9 Z"),
   _path("{c}", "M17 9 L21 13"))
_g("floppy",
   _path("{c}", "M10 9 L22 9 L22 23 L10 23 Z"),
   _path("{c}", "M10 9 L18 9 L18 15 L10 15"),
   _path("{c}", "M12 17 L20 17"))
_g("refresh",
   _path("{c}", "M19 11 Q22 13 22 16 Q22 21 16 21 Q11 21 10 16"),
   _path("{c}", "M13 11 L19 11 L19 15"))
_g("package",
   _path("{c}", "M8 13 L16 9 L24 13 L16 17 Z"),
   _path("{c}", "M8 13 L8 21 L16 25 L24 21 L24 13"),
   _path("{c}", "M16 17 L16 25"))
_g("chat",
   _path("{c}", "M8 10 Q8 20 16 20 L19 23 L19 20 Q24 20 24 12 Q24 10 8 10"))
_g("play",
   _path("{c}", "M11 10 L23 16 L11 22 Z"))
_g("music",
   _path("{c}", "M19 10 L19 20"),
   _path("{c}", "M19 12 L13 14 L13 20"),
   _path("{c}", "M13 20 A3 3 0 1 0 13 14 A3 3 0 1 0 13 20"))
_g("ailang_a",
   _path("{c}", "M11 23 L14 11 L16 11 L13 23"),
   _path("{c}", "M21 23 L18 11 L20 11 L23 23"),
   _path("{c}", "M12 17 L22 17"))


ICON_SPECS: dict[str, tuple[str, str]] = {
    "home": ("cyan", "folder_open"),
    "folder": ("amber", "folder_closed"),
    "folder-open": ("amber", "folder_open"),
    "file": ("azure", "document"),
    "notepad": ("azure", "document"),
    "terminal": ("green", "shell"),
    "code": ("violet", "code"),
    "browser": ("azure", "globe"),
    "display": ("magenta", "monitor"),
    "video": ("magenta", "monitor"),
    "network": ("cyan", "globe"),
    "wifi": ("cyan", "globe"),
    "mail": ("green", "envelope"),
    "trash": ("magenta", "trash"),
    "gear": ("azure", "settings"),
    "preferences": ("azure", "settings"),
    "volume": ("azure", "speaker"),
    "music": ("violet", "music"),
    "media-player": ("magenta", "play"),
    "search": ("cyan", "search"),
    "user": ("azure", "user"),
    "lock": ("violet", "lock"),
    "power": ("magenta", "power"),
    "shutdown": ("magenta", "power"),
    "start": ("cyan", "ailang_a"),
    "battery": ("green", "battery"),
    "clock": ("azure", "clock"),
    "calculator": ("azure", "calculator"),
    "alert": ("amber", "alert"),
    "info": ("cyan", "info"),
    "help": ("azure", "help"),
    "menu": ("ink", "menu"),
    "paint": ("violet", "paint"),
    "link": ("cyan", "link"),
    "keyboard": ("azure", "keyboard"),
    "image": ("magenta", "image"),
    "download": ("green", "arrow_down"),
    "upload": ("green", "arrow_up"),
    "edit": ("violet", "edit"),
    "save": ("azure", "floppy"),
    "refresh": ("cyan", "refresh"),
    "installer": ("green", "package"),
    "ai-chat": ("violet", "chat"),
}


def icon_chrome_svg(glyph_svg: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <defs>
    <linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1a2848"/>
      <stop offset="100%" stop-color="{NAVY}"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="28" height="28" rx="5" fill="url(#chrome)" stroke="{BORDER}" stroke-width="0.8"/>
  <rect x="3" y="3" width="26" height="3" rx="2" fill="{CYAN}" opacity="0.1"/>
  {glyph_svg}
</svg>
'''


def aos_logo_svg() -> str:
    """Deskbar start button — rectangular azure chrome with cyan A."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <defs>
    <linearGradient id="start-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{STEEL}"/>
      <stop offset="100%" stop-color="{NAVY}"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="28" height="28" rx="5" fill="url(#start-bg)" stroke="{AZURE}" stroke-width="1"/>
  <rect x="3" y="3" width="26" height="3" rx="2" fill="{CYAN}" opacity="0.15"/>
  {_path(CYAN, "M11 23 L14 11 L16 11 L13 23")}
  {_path(CYAN, "M21 23 L18 11 L20 11 L23 23")}
  {_path(CYAN, "M12 17 L22 17")}
</svg>
'''


def make_icon(name: str) -> str:
    if name == "aos-logo":
        return aos_logo_svg()
    spec = ICON_SPECS.get(name)
    if not spec:
        raise KeyError(f"No icon spec for {name}")
    color_key, glyph_key = spec
    color = COLORS[color_key]
    glyph = GLYPHS[glyph_key].format(c=color)
    return icon_chrome_svg(glyph)


# --- Widget palette (System widgets.png) ---

WORKBENCH_DEFS = f'''<defs>
<linearGradient id="g-tb" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a2848"/><stop offset="100%" stop-color="{NAVY}"/></linearGradient>
<linearGradient id="g-tb-i" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#121c34"/><stop offset="100%" stop-color="{ABYSS}"/></linearGradient>
<linearGradient id="g-btn" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a2848"/><stop offset="100%" stop-color="{NAVY}"/></linearGradient>
<linearGradient id="g-btn-h" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#223058"/><stop offset="100%" stop-color="{STEEL}"/></linearGradient>
<linearGradient id="g-btn-p" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{ABYSS}"/><stop offset="100%" stop-color="#121c34"/></linearGradient>
<linearGradient id="g-btn-d" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{CYAN}"/><stop offset="100%" stop-color="#1a9fd4"/></linearGradient>
<linearGradient id="g-close" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ff6688"/><stop offset="100%" stop-color="#cc3355"/></linearGradient>
<linearGradient id="g-close-h" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ff88aa"/><stop offset="100%" stop-color="#dd4466"/></linearGradient>
<linearGradient id="g-close-p" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#992244"/><stop offset="100%" stop-color="#cc3355"/></linearGradient>
<linearGradient id="g-min" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#334466"/><stop offset="100%" stop-color="#223050"/></linearGradient>
<linearGradient id="g-min-h" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3a5070"/><stop offset="100%" stop-color="#2a4060"/></linearGradient>
<linearGradient id="g-min-p" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a2840"/><stop offset="100%" stop-color="#223050"/></linearGradient>
<linearGradient id="g-max" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#334466"/><stop offset="100%" stop-color="#223050"/></linearGradient>
<linearGradient id="g-max-h" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3a5070"/><stop offset="100%" stop-color="#2a4060"/></linearGradient>
<linearGradient id="g-max-p" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a2840"/><stop offset="100%" stop-color="#223050"/></linearGradient>
<linearGradient id="g-track" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{ABYSS}"/><stop offset="100%" stop-color="{VOID}"/></linearGradient>
<linearGradient id="g-vtrack" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="{ABYSS}"/><stop offset="100%" stop-color="{VOID}"/></linearGradient>
<linearGradient id="g-thumb" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2a4068"/><stop offset="100%" stop-color="#1a3050"/></linearGradient>
<linearGradient id="g-vthumb" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#2a4068"/><stop offset="100%" stop-color="#1a3050"/></linearGradient>
<linearGradient id="g-check" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{AZURE}"/><stop offset="100%" stop-color="#2a68cc"/></linearGradient>
<linearGradient id="g-input" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{ABYSS}"/><stop offset="15%" stop-color="{NAVY}"/><stop offset="100%" stop-color="{STEEL}"/></linearGradient>
<linearGradient id="g-input-f" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#142040"/><stop offset="15%" stop-color="{NAVY}"/><stop offset="100%" stop-color="#1a3058"/></linearGradient>
<linearGradient id="g-prog" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{AZURE}"/><stop offset="50%" stop-color="{CYAN}"/><stop offset="100%" stop-color="#2a68cc"/></linearGradient>
<linearGradient id="g-status" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{NAVY}"/><stop offset="100%" stop-color="{ABYSS}"/></linearGradient>
<linearGradient id="g-tab-a" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#223058"/><stop offset="100%" stop-color="{STEEL}"/></linearGradient>
<linearGradient id="g-tab-i" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#121c34"/><stop offset="100%" stop-color="{ABYSS}"/></linearGradient>
<linearGradient id="g-tab-h" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2a3860"/><stop offset="100%" stop-color="#1a2848"/></linearGradient>
<linearGradient id="g-split" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a2848"/><stop offset="50%" stop-color="{ABYSS}"/><stop offset="100%" stop-color="#1a2848"/></linearGradient>
<linearGradient id="g-vsplit" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#1a2848"/><stop offset="50%" stop-color="{ABYSS}"/><stop offset="100%" stop-color="#1a2848"/></linearGradient>
<linearGradient id="g-resize" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#2a4068"/><stop offset="100%" stop-color="{MUTE}"/></linearGradient>
<linearGradient id="g-panel" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{STEEL}"/><stop offset="100%" stop-color="{NAVY}"/></linearGradient>
</defs>'''

OLD_DEFS_RE = re.compile(r"<defs>.*?</defs>", re.DOTALL)

# Per-file body overrides after defs replacement
WIDGET_BODIES: dict[str, str] = {
    "sunken_bevel": f'''<rect x="0" y="0" width="128" height="32" fill="{ABYSS}" stroke="{BORDER}" stroke-width="1"/>
<rect x="1" y="1" width="126" height="1" fill="{VOID}"/>
<rect x="1" y="30" width="126" height="1" fill="#2a4068" opacity="0.5"/>''',
    "raised_bevel": f'''<rect x="0" y="0" width="128" height="32" fill="{STEEL}" stroke="{BORDER}" stroke-width="1"/>
<rect x="1" y="1" width="126" height="1" fill="#2a4068" opacity="0.6"/>
<rect x="1" y="30" width="126" height="1" fill="{CYAN}" opacity="0.08"/>''',
    "input_body_disabled": f'''<rect x="0" y="0" width="128" height="32" rx="2" fill="{VOID}" stroke="{MUTE}" stroke-width="1"/>
<rect x="0" y="0" width="128" height="4" rx="1" fill="{ABYSS}" opacity="0.6"/>''',
    "progress_fill": f'''<rect x="0" y="0" width="128" height="32" rx="2" fill="url(#g-prog)" stroke="{AZURE}" stroke-width="0.8"/>
<rect x="0" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="12" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="24" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="36" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="48" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="60" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="72" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="84" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="96" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="108" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>
<rect x="120" y="0" width="8" height="32" fill="{INK}" opacity="0.12"/>''',
    "titlebar_strip_active": f'''<rect x="0" y="0" width="128" height="32" fill="url(#g-tb)" stroke="{BORDER}" stroke-width="1"/>
<rect x="0" y="30" width="128" height="2" fill="{GREEN}" opacity="0.85"/>''',
    "slider_thumb": f'''<circle cx="16" cy="16" r="14" fill="url(#g-btn-d)" stroke="{CYAN}" stroke-width="1.2"/>
<circle cx="16" cy="16" r="10" fill="{CYAN}" opacity="0.25"/>''',
    "radio_disabled": f'''<circle cx="16" cy="16" r="14" fill="{VOID}" stroke="{MUTE}" stroke-width="1"/>''',
    "checkbox_box_disabled": f'''<rect x="0" y="0" width="32" height="32" rx="3" fill="{VOID}" stroke="{MUTE}" stroke-width="1"/>''',
}

# Stroke/border color substitutions for widget bodies
WIDGET_STROKE_REPLACEMENTS = [
    (r'stroke="#999"', f'stroke="{BORDER}"'),
    (r'stroke="#aaa"', f'stroke="{BORDER}"'),
    (r'stroke="#bbb"', f'stroke="{BORDER}"'),
    (r'stroke="#909090"', f'stroke="{BORDER}"'),
    (r'stroke="#777"', f'stroke="{BORDER}"'),
    (r'stroke="#888"', f'stroke="{BORDER}"'),
    (r'stroke="#5a7a9a"', f'stroke="{AZURE}"'),
    (r'stroke="#6a8aaa"', f'stroke="{AZURE}"'),
    (r'stroke="#333"', f'stroke="{INK}"'),
    (r'fill="white" opacity="0\.45"', f'fill="{CYAN}" opacity="0.12"'),
    (r'fill="white" opacity="0\.22"', f'fill="{CYAN}" opacity="0.1"'),
    (r'fill="white" opacity="0\.7"', f'fill="{CYAN}" opacity="0.08"'),
    (r'stroke="#1a6a1a"', f'stroke="{BORDER}"'),
    (r'stroke="#188018"', f'stroke="{AZURE}"'),
    (r'stroke="#0a4a0a"', f'stroke="{BORDER}"'),
    (r'stroke="#a87810"', f'stroke="{BORDER}"'),
    (r'stroke="#987010"', f'stroke="{AZURE}"'),
    (r'stroke="#6a5008"', f'stroke="{BORDER}"'),
    (r'stroke="#b03030"', f'stroke="#cc4466"'),
    (r'stroke="#a02828"', f'stroke="#dd5577"'),
    (r'stroke="#8a2020"', f'stroke="#aa3355"'),
]

GLYPH_STROKE_REPLACEMENTS = [
    (r'stroke="#333"', f'stroke="{INK}"'),
    (r'stroke-width="3"', 'stroke-width="2.2"'),
]


def restyle_widget_svg(content: str, filename: str) -> str:
    base = os.path.splitext(filename)[0]
    if not content.strip().startswith("<svg"):
        return content
    # Extract viewBox dimensions from opening tag
    m = re.search(r'width="(\d+)" height="(\d+)"', content)
    w, h = (m.group(1), m.group(2)) if m else ("32", "32")

    if base in WIDGET_BODIES:
        body = WIDGET_BODIES[base]
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n{WORKBENCH_DEFS}\n{body}\n</svg>\n'

    updated = OLD_DEFS_RE.sub(WORKBENCH_DEFS, content, count=1)
    for pat, repl in WIDGET_STROKE_REPLACEMENTS:
        updated = re.sub(pat, repl, updated)
    if base.startswith("glyph_"):
        for pat, repl in GLYPH_STROKE_REPLACEMENTS:
            updated = re.sub(pat, repl, updated)
    return updated


def generate_icons() -> int:
    icon_dir = os.path.join(ROOT, "app_icons")
    count = 0
    for fname in sorted(os.listdir(icon_dir)):
        if not fname.endswith(".svg"):
            continue
        name = fname[:-4]
        if name == "aos-logo":
            svg = aos_logo_svg()
        elif name in ICON_SPECS:
            svg = make_icon(name)
        else:
            print(f"  [skip] no spec: {fname}")
            continue
        path = os.path.join(icon_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        count += 1
    return count


def restyle_widgets() -> int:
    widget_dir = os.path.join(ROOT, "silver_system_atoms")
    count = 0
    for fname in sorted(os.listdir(widget_dir)):
        if not fname.endswith(".svg"):
            continue
        path = os.path.join(widget_dir, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        updated = restyle_widget_svg(content, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        count += 1
    return count


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("icons", "all"):
        n = generate_icons()
        print(f"[workbench] generated {n} app icons")
    if cmd in ("widgets", "all"):
        n = restyle_widgets()
        print(f"[workbench] restyled {n} widget atoms")


if __name__ == "__main__":
    main()