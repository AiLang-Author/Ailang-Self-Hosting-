#!/usr/bin/env python3
"""
svg_w3c_runner.py — W3C SVG 1.1 Conformance Test Runner for Ailang SVG Library

Runs the official W3C SVG 1.1 Second Edition test suite against the Ailang SVG
renderer. Tests are categorized by feature area. Results include:
  - Crash/render/blank status
  - Reference image comparison (pixel similarity %)
  - Per-category and overall compliance scores

Usage:
    python3 tools/svg_w3c_runner.py                     # Run all rendering tests
    python3 tools/svg_w3c_runner.py --category shapes    # Run shapes-* tests only
    python3 tools/svg_w3c_runner.py --category paths     # Run paths-* tests only
    python3 tools/svg_w3c_runner.py --test shapes-rect-01-t  # Run specific test
    python3 tools/svg_w3c_runner.py --dump-ppm /tmp/w3c  # Save PPM outputs
    python3 tools/svg_w3c_runner.py --verbose            # Show binary output
    python3 tools/svg_w3c_runner.py --quick              # Skip ref comparison
    python3 tools/svg_w3c_runner.py --list               # List available tests

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import os
import sys
import subprocess
import argparse
import shutil
import struct
import zlib
from pathlib import Path
from collections import Counter, defaultdict

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
SVG_TEST_BIN = PROJECT_DIR / "svg_test.x"
W3C_SVG_DIR = PROJECT_DIR / "tests" / "svg" / "spec" / "svg"
W3C_PNG_DIR = PROJECT_DIR / "tests" / "svg" / "spec" / "png"
BASIC_SVG_DIR = PROJECT_DIR / "tests" / "svg" / "basic"

# Test categories relevant to a rendering engine (no DOM, scripting, animation)
RENDER_CATEGORIES = [
    "shapes-rect", "shapes-circle", "shapes-ellipse", "shapes-line",
    "shapes-polygon", "shapes-polyline", "shapes-intro", "shapes-grammar",
    "paths-data",
    "coords-coord", "coords-trans", "coords-transformattr",
    "coords-units", "coords-viewattr",
    "painting-fill", "painting-stroke", "painting-control", "painting-render",
    "pservers-grad", "pservers-grad-stops",
    "render-elems", "render-groups",
    "struct-group", "struct-defs", "struct-svg", "struct-frag",
    "masking-opacity",
    "color-prop",
    "text-intro", "text-text", "text-align", "text-tspan",
    "text-fonts", "text-deco", "text-spacing", "text-path", "text-ws",
    "styling-pres", "styling-inherit",
]

# Categories we intentionally skip (require DOM, JS, animation, interaction)
SKIP_CATEGORIES = [
    "animate-", "script-", "interact-", "linking-",
    "conform-", "extend-", "metadata-", "svgdom-",
    "types-dom", "struct-dom", "coords-dom", "paths-dom",
    "painting-marker",  # markers not implemented
    "pservers-pattern",  # patterns not implemented
    "fonts-",  # SVG fonts not implemented
    "struct-image",  # external image loading not implemented
    "struct-use",  # <use> not implemented
    "struct-symbol",  # <symbol> not implemented
    "struct-cond",  # conditional processing not implemented
    "masking-filter", "masking-mask", "masking-path",  # filters/masks not implemented
    "filters-",  # filters not implemented
    "text-altglyph", "text-bidi", "text-tref", "text-tselect",  # advanced text
    "styling-css", "styling-class", "styling-elem",  # CSS not in SVG lib
    "color-prof",  # color profiles not implemented
]


def read_png(png_path):
    """Read a PNG file and decode to raw RGB pixel data.
    Returns (width, height, rgb_data) or None on failure.
    Supports 8-bit RGB and RGBA PNGs (the common W3C reference format)."""
    try:
        with open(png_path, "rb") as f:
            # Check PNG signature
            sig = f.read(8)
            if sig != b'\x89PNG\r\n\x1a\n':
                return None

            width = height = 0
            bit_depth = color_type = 0
            idat_chunks = []
            palette = None

            while True:
                chunk_hdr = f.read(8)
                if len(chunk_hdr) < 8:
                    break
                length = struct.unpack(">I", chunk_hdr[:4])[0]
                chunk_type = chunk_hdr[4:8]
                chunk_data = f.read(length)
                f.read(4)  # CRC

                if chunk_type == b'IHDR':
                    width = struct.unpack(">I", chunk_data[0:4])[0]
                    height = struct.unpack(">I", chunk_data[4:8])[0]
                    bit_depth = chunk_data[8]
                    color_type = chunk_data[9]
                elif chunk_type == b'PLTE':
                    palette = chunk_data
                elif chunk_type == b'IDAT':
                    idat_chunks.append(chunk_data)
                elif chunk_type == b'IEND':
                    break

            if width == 0 or height == 0:
                return None

            # Decompress
            compressed = b''.join(idat_chunks)
            raw = zlib.decompress(compressed)

            # Determine bytes per pixel and stride
            if color_type == 2:  # RGB
                bpp = 3
            elif color_type == 6:  # RGBA
                bpp = 4
            elif color_type == 0:  # Grayscale
                bpp = 1
            elif color_type == 4:  # Grayscale + Alpha
                bpp = 2
            elif color_type == 3:  # Indexed
                bpp = 1
            else:
                return None

            stride = 1 + width * bpp  # +1 for filter byte

            # Unfilter
            lines = []
            prev_line = b'\x00' * (width * bpp)
            for y in range(height):
                offset = y * stride
                filt = raw[offset]
                scanline = bytearray(raw[offset + 1: offset + stride])

                if filt == 0:  # None
                    pass
                elif filt == 1:  # Sub
                    for i in range(bpp, len(scanline)):
                        scanline[i] = (scanline[i] + scanline[i - bpp]) & 0xFF
                elif filt == 2:  # Up
                    for i in range(len(scanline)):
                        scanline[i] = (scanline[i] + prev_line[i]) & 0xFF
                elif filt == 3:  # Average
                    for i in range(len(scanline)):
                        a = scanline[i - bpp] if i >= bpp else 0
                        b = prev_line[i]
                        scanline[i] = (scanline[i] + (a + b) // 2) & 0xFF
                elif filt == 4:  # Paeth
                    for i in range(len(scanline)):
                        a = scanline[i - bpp] if i >= bpp else 0
                        b = prev_line[i]
                        c = prev_line[i - bpp] if i >= bpp else 0
                        p = a + b - c
                        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                        if pa <= pb and pa <= pc:
                            pr = a
                        elif pb <= pc:
                            pr = b
                        else:
                            pr = c
                        scanline[i] = (scanline[i] + pr) & 0xFF

                lines.append(bytes(scanline))
                prev_line = scanline

            # Convert to RGB
            rgb = bytearray()
            for line in lines:
                for x in range(width):
                    if color_type == 2:  # RGB
                        idx = x * 3
                        rgb.extend(line[idx:idx + 3])
                    elif color_type == 6:  # RGBA
                        idx = x * 4
                        rgb.extend(line[idx:idx + 3])
                    elif color_type == 0:  # Grayscale
                        g = line[x]
                        rgb.extend([g, g, g])
                    elif color_type == 4:  # Gray+Alpha
                        idx = x * 2
                        g = line[idx]
                        rgb.extend([g, g, g])
                    elif color_type == 3:  # Indexed
                        pi = line[x] * 3
                        if palette and pi + 2 < len(palette):
                            rgb.extend(palette[pi:pi + 3])
                        else:
                            rgb.extend([0, 0, 0])

            return width, height, bytes(rgb)
    except Exception:
        return None


def read_ppm(ppm_path):
    """Read a P6 PPM file, return (width, height, rgb_data) or None."""
    try:
        with open(ppm_path, "rb") as f:
            magic = f.readline().strip()
            if magic != b"P6":
                return None
            line = f.readline()
            while line.startswith(b"#"):
                line = f.readline()
            w, h = map(int, line.split())
            f.readline()  # max value
            data = f.read()
        return w, h, data
    except Exception:
        return None


def compare_images(ppm_path, png_path, tolerance=32):
    """Compare rendered PPM against reference PNG.
    Returns dict with similarity metrics.
    tolerance: per-channel difference allowed (0-255)."""
    ppm = read_ppm(ppm_path)
    png = read_png(png_path)

    if ppm is None:
        return {"valid": False, "reason": "PPM read failed"}
    if png is None:
        return {"valid": False, "reason": "PNG read failed"}

    pw, ph, pdata = ppm
    rw, rh, rdata = png

    # If sizes differ, we need to scale comparison
    # For now, compare at the rendered size by sampling the reference
    if pw != rw or ph != rh:
        # Nearest-neighbor resample reference to rendered size
        resampled = bytearray()
        for y in range(ph):
            ry = min(int(y * rh / ph), rh - 1)
            for x in range(pw):
                rx = min(int(x * rw / pw), rw - 1)
                ri = (ry * rw + rx) * 3
                if ri + 2 < len(rdata):
                    resampled.extend(rdata[ri:ri + 3])
                else:
                    resampled.extend([0, 0, 0])
        rdata = bytes(resampled)
        rw, rh = pw, ph

    total_pixels = pw * ph
    if total_pixels == 0:
        return {"valid": False, "reason": "zero pixels"}

    # Sample for speed (full comparison on small images, sampling on large)
    sample_step = max(1, total_pixels // 100000)
    matching = 0
    close = 0
    wrong = 0
    sampled = 0

    min_len = min(len(pdata), len(rdata))

    for i in range(0, min_len - 2, sample_step * 3):
        pr, pg, pb = pdata[i], pdata[i + 1], pdata[i + 2]
        rr, rg, rb = rdata[i], rdata[i + 1], rdata[i + 2]
        sampled += 1

        dr = abs(pr - rr)
        dg = abs(pg - rg)
        db = abs(pb - rb)

        if dr == 0 and dg == 0 and db == 0:
            matching += 1
        elif dr <= tolerance and dg <= tolerance and db <= tolerance:
            close += 1
        else:
            wrong += 1

    exact_pct = (matching / sampled * 100) if sampled > 0 else 0
    close_pct = ((matching + close) / sampled * 100) if sampled > 0 else 0

    return {
        "valid": True,
        "sampled": sampled,
        "exact_match_pct": exact_pct,
        "close_match_pct": close_pct,
        "wrong_pct": (wrong / sampled * 100) if sampled > 0 else 0,
        "ref_size": f"{rw}x{rh}",
        "render_size": f"{pw}x{ph}",
    }


def render_svg(svg_path, output_ppm, width=480, height=360, timeout=15):
    """Render an SVG file through svg_test.x binary."""
    try:
        os.unlink(output_ppm)
    except FileNotFoundError:
        pass

    try:
        result = subprocess.run(
            [str(SVG_TEST_BIN), str(svg_path), output_ppm, str(width), str(height)],
            capture_output=True,
            timeout=timeout,
            cwd=str(PROJECT_DIR),
        )
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT", -1, 0, 0
    except Exception as e:
        return False, "", str(e), -1, 0, 0

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    elem_count = 0
    edge_count = 0
    for line in stdout.split("\n"):
        if "Elements rendered:" in line:
            try:
                elem_count = int(line.split(":")[-1].strip())
            except ValueError:
                pass
        if "Edge count:" in line:
            try:
                edge_count = int(line.split(":")[-1].strip())
            except ValueError:
                pass

    success = result.returncode == 0 and os.path.exists(output_ppm)
    return success, stdout, stderr, result.returncode, elem_count, edge_count


def analyze_ppm(ppm_path):
    """Quick PPM analysis: non-white percentage."""
    info = read_ppm(ppm_path)
    if info is None:
        return {"exists": False}

    w, h, data = info
    total = w * h
    step = max(1, total // 50000)
    non_white = 0
    sampled = 0

    for i in range(0, len(data) - 2, step * 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        sampled += 1
        if (r, g, b) != (255, 255, 255):
            non_white += 1

    return {
        "exists": True,
        "width": w,
        "height": h,
        "non_white_pct": (non_white / sampled * 100) if sampled > 0 else 0,
    }


def should_skip(test_name):
    """Check if a test should be skipped (requires unimplemented features)."""
    for skip in SKIP_CATEGORIES:
        if test_name.startswith(skip):
            return True
    return False


def get_category(test_name):
    """Extract category from test name (e.g., shapes-rect-01-t -> shapes-rect)."""
    parts = test_name.rsplit("-", 2)
    if len(parts) >= 3:
        return "-".join(parts[:-2])
    return test_name


def run_test(test_name, svg_path, png_path, dump_dir=None,
             width=480, height=360, timeout=15, verbose=False, quick=False):
    """Run a single W3C test. Returns result dict."""
    output_ppm = f"/tmp/w3c_{test_name}.ppm"

    success, stdout, stderr, rc, elems, edges = render_svg(
        svg_path, output_ppm, width, height, timeout
    )

    result = {
        "name": test_name,
        "category": get_category(test_name),
        "returncode": rc,
        "elem_count": elems,
        "edge_count": edges,
    }

    if rc == -1 and "TIMEOUT" in stderr:
        result["status"] = "TIMEOUT"
    elif not success:
        result["status"] = "CRASH"
        if verbose:
            result["stderr"] = stderr[:500]
    else:
        # Check if blank
        ppm_info = analyze_ppm(output_ppm)
        if ppm_info.get("exists") and ppm_info["non_white_pct"] < 0.1:
            result["status"] = "BLANK"
        elif elems == 0:
            result["status"] = "NO_ELEMS"
        else:
            result["status"] = "RENDER"

        # Reference comparison
        if not quick and png_path and png_path.exists():
            cmp = compare_images(output_ppm, str(png_path))
            result["ref_compare"] = cmp
            if cmp.get("valid"):
                result["similarity"] = cmp["close_match_pct"]

        if dump_dir:
            try:
                shutil.copy2(output_ppm, os.path.join(dump_dir, f"{test_name}.ppm"))
            except Exception:
                pass

    if verbose:
        result["stdout"] = stdout

    return result


def print_result(r, verbose=False):
    """Print a single test result."""
    status = r["status"]
    name = r["name"]

    if status == "RENDER":
        icon = "[OK  ]"
    elif status == "BLANK":
        icon = "[BLNK]"
    elif status == "NO_ELEMS":
        icon = "[NOEM]"
    elif status == "CRASH":
        icon = "[CRSH]"
    elif status == "TIMEOUT":
        icon = "[TIME]"
    else:
        icon = "[????]"

    sim_str = ""
    if "similarity" in r:
        sim_str = f"  sim={r['similarity']:.0f}%"

    elem_str = f"  elems={r['elem_count']}" if r.get('elem_count', 0) > 0 else ""
    edge_str = f"  edges={r['edge_count']}" if r.get('edge_count', 0) > 0 else ""

    print(f"  {icon} {name}: {status}{sim_str}{elem_str}{edge_str}")

    if verbose and status == "CRASH" and "stderr" in r:
        for line in r["stderr"].split("\n")[:5]:
            print(f"         {line}")


def main():
    parser = argparse.ArgumentParser(
        description="W3C SVG 1.1 Conformance Test Runner for Ailang SVG Library"
    )
    parser.add_argument(
        "--test", metavar="NAME",
        help="Run specific test (e.g., shapes-rect-01-t)",
    )
    parser.add_argument(
        "--category", metavar="CAT",
        help="Run tests for a category (e.g., shapes, paths, coords, painting, pservers, text)",
    )
    parser.add_argument(
        "--dump-ppm", metavar="DIR",
        help="Save PPM output to this directory",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show full binary output for failures",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Skip reference image comparison (faster)",
    )
    parser.add_argument(
        "--timeout", type=int, default=15,
        help="Timeout per render in seconds (default: 15)",
    )
    parser.add_argument(
        "--size", metavar="WxH", default="480x360",
        help="Render size (default: 480x360, W3C ref images are 480x360)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available tests and exit",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run ALL W3C tests (including skipped categories)",
    )
    parser.add_argument(
        "--basic", action="store_true",
        help="Also run the basic/ test suite",
    )
    args = parser.parse_args()

    # Parse size
    if "x" in args.size:
        w, h = map(int, args.size.split("x"))
    else:
        w = h = int(args.size)

    # Check binary
    if not SVG_TEST_BIN.exists():
        print(f"ERROR: SVG test binary not found at {SVG_TEST_BIN}")
        print(f"Build it first:")
        print(f"  ./ailang.x TestCode/svg_test.ailang svg_test.x")
        sys.exit(1)

    # Collect W3C tests
    if not W3C_SVG_DIR.exists():
        print(f"ERROR: W3C SVG test directory not found at {W3C_SVG_DIR}")
        print(f"Download the W3C SVG 1.1 test suite first.")
        sys.exit(1)

    all_tests = []

    # W3C tests
    for svg_file in sorted(W3C_SVG_DIR.glob("*.svg")):
        name = svg_file.stem
        png_file = W3C_PNG_DIR / f"{name}.png"
        if not args.all and should_skip(name):
            continue
        if args.category and not name.startswith(args.category):
            continue
        if args.test and name != args.test:
            continue
        all_tests.append((name, svg_file, png_file if png_file.exists() else None))

    # Basic tests (if requested)
    if args.basic and BASIC_SVG_DIR.exists():
        for svg_file in sorted(BASIC_SVG_DIR.glob("*.svg")):
            name = f"basic-{svg_file.stem}"
            if args.test and name != args.test:
                continue
            all_tests.append((name, svg_file, None))

    if args.list:
        print(f"\nAvailable W3C SVG Tests ({len(all_tests)} total):")
        cats = defaultdict(list)
        for name, _, _ in all_tests:
            cats[get_category(name)].append(name)
        for cat in sorted(cats.keys()):
            print(f"\n  {cat} ({len(cats[cat])} tests):")
            for t in cats[cat]:
                print(f"    {t}")
        sys.exit(0)

    if not all_tests:
        print("No tests matched the criteria.")
        sys.exit(1)

    if args.dump_ppm:
        os.makedirs(args.dump_ppm, exist_ok=True)

    # Header
    print(f"\n{'='*74}")
    print(f"  Ailang SVG Library — W3C SVG 1.1 Conformance Test Suite")
    print(f"{'='*74}")
    print(f"  Binary:     {SVG_TEST_BIN}")
    print(f"  Test dir:   {W3C_SVG_DIR}")
    print(f"  Ref dir:    {W3C_PNG_DIR}")
    print(f"  Size:       {w}x{h}")
    print(f"  Tests:      {len(all_tests)}")
    print(f"  Mode:       {'Quick (no ref compare)' if args.quick else 'Full (with ref compare)'}")
    print(f"{'='*74}")

    # Run tests
    results = []
    for i, (name, svg_path, png_path) in enumerate(all_tests):
        r = run_test(name, svg_path, png_path, args.dump_ppm,
                     w, h, args.timeout, args.verbose, args.quick)
        results.append(r)
        print_result(r, args.verbose)

        # Progress indicator every 50 tests
        if (i + 1) % 50 == 0:
            print(f"\n  --- Progress: {i+1}/{len(all_tests)} ---\n")

    # Category summary
    print(f"\n{'='*74}")
    print(f"  PER-CATEGORY RESULTS")
    print(f"{'='*74}")

    cat_stats = defaultdict(lambda: {"render": 0, "blank": 0, "crash": 0,
                                      "timeout": 0, "other": 0, "total": 0,
                                      "sim_sum": 0.0, "sim_count": 0})
    for r in results:
        cat = r["category"]
        cat_stats[cat]["total"] += 1
        st = r["status"]
        if st == "RENDER":
            cat_stats[cat]["render"] += 1
        elif st == "BLANK":
            cat_stats[cat]["blank"] += 1
        elif st == "CRASH":
            cat_stats[cat]["crash"] += 1
        elif st == "TIMEOUT":
            cat_stats[cat]["timeout"] += 1
        else:
            cat_stats[cat]["other"] += 1
        if "similarity" in r:
            cat_stats[cat]["sim_sum"] += r["similarity"]
            cat_stats[cat]["sim_count"] += 1

    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        total = s["total"]
        render_pct = (s["render"] / total * 100) if total > 0 else 0
        sim_avg = (s["sim_sum"] / s["sim_count"]) if s["sim_count"] > 0 else 0

        status_parts = []
        if s["render"] > 0:
            status_parts.append(f"{s['render']} OK")
        if s["blank"] > 0:
            status_parts.append(f"{s['blank']} blank")
        if s["crash"] > 0:
            status_parts.append(f"{s['crash']} crash")
        if s["timeout"] > 0:
            status_parts.append(f"{s['timeout']} timeout")
        if s["other"] > 0:
            status_parts.append(f"{s['other']} other")

        sim_str = f"  avg_sim={sim_avg:.0f}%" if s["sim_count"] > 0 else ""
        print(f"  {cat:35s} {render_pct:5.1f}% ({', '.join(status_parts)}) / {total}{sim_str}")

    # Overall summary
    print(f"\n{'='*74}")
    print(f"  OVERALL COMPLIANCE SUMMARY")
    print(f"{'='*74}")

    total = len(results)
    render_count = sum(1 for r in results if r["status"] == "RENDER")
    blank_count = sum(1 for r in results if r["status"] == "BLANK")
    crash_count = sum(1 for r in results if r["status"] == "CRASH")
    timeout_count = sum(1 for r in results if r["status"] == "TIMEOUT")
    noelem_count = sum(1 for r in results if r["status"] == "NO_ELEMS")
    other_count = total - render_count - blank_count - crash_count - timeout_count - noelem_count

    render_pct = (render_count / total * 100) if total > 0 else 0

    print(f"\n  Total tests:     {total}")
    print(f"  Rendered (OK):   {render_count} ({render_pct:.1f}%)")
    if blank_count > 0:
        print(f"  Blank:           {blank_count} ({blank_count/total*100:.1f}%)")
    if noelem_count > 0:
        print(f"  No elements:     {noelem_count} ({noelem_count/total*100:.1f}%)")
    if crash_count > 0:
        print(f"  Crashed:         {crash_count} ({crash_count/total*100:.1f}%)")
    if timeout_count > 0:
        print(f"  Timeout:         {timeout_count} ({timeout_count/total*100:.1f}%)")
    if other_count > 0:
        print(f"  Other:           {other_count} ({other_count/total*100:.1f}%)")

    # Reference similarity stats
    sim_results = [r for r in results if "similarity" in r]
    if sim_results:
        avg_sim = sum(r["similarity"] for r in sim_results) / len(sim_results)
        high_sim = sum(1 for r in sim_results if r["similarity"] >= 80)
        med_sim = sum(1 for r in sim_results if 50 <= r["similarity"] < 80)
        low_sim = sum(1 for r in sim_results if r["similarity"] < 50)

        print(f"\n  Reference Image Comparison:")
        print(f"    Tests compared: {len(sim_results)}")
        print(f"    Average similarity: {avg_sim:.1f}%")
        print(f"    High match (>=80%): {high_sim}")
        print(f"    Medium match (50-79%): {med_sim}")
        print(f"    Low match (<50%): {low_sim}")

    # Compliance score: render + not-crash = basic compliance
    # render + high_similarity = visual compliance
    basic_compliance = ((render_count + blank_count) / total * 100) if total > 0 else 0
    crash_free = ((total - crash_count - timeout_count) / total * 100) if total > 0 else 0

    print(f"\n  COMPLIANCE SCORES:")
    print(f"    Crash-free rate:      {crash_free:.1f}%")
    print(f"    Render rate:          {render_pct:.1f}%")
    print(f"    Basic compliance:     {basic_compliance:.1f}% (render + blank, no crashes)")
    if sim_results:
        print(f"    Visual compliance:    {avg_sim:.1f}% (avg reference similarity)")

    print(f"\n{'='*74}")

    # List failures for debugging
    failures = [r for r in results if r["status"] in ("CRASH", "TIMEOUT")]
    if failures:
        print(f"\n  FAILURES (crash/timeout):")
        for r in failures:
            print(f"    {r['name']}: {r['status']} (rc={r['returncode']})")

    print()
    sys.exit(0 if crash_count == 0 else 1)


if __name__ == "__main__":
    main()
