#!/usr/bin/env python3
"""
Generate AILang FixedPool Unicode tables for grep from UCD files.

Reads:  CaseFolding.txt, DerivedCoreProperties.txt, UnicodeData.txt
Writes: unicode_tables.ailang (FixedPool range tables)

Word characters (for -w / \w per UTS #18 RL1.2a):
    Letters (Alphabetic property) + Marks (Mn, Mc, Me) + Digits (Nd) +
    Connector_Punctuation (Pc) + U+200C (ZWNJ) + U+200D (ZWJ)

Simple case folding (for -i):
    Status C and S from CaseFolding.txt — one codepoint to one codepoint.
    Stored as (start, end, delta) runs where consecutive codepoints share
    the same offset. GNU grep uses simple case folding; full folding (F)
    changes string length and we skip it, same as GNU.

Tables are stored as flat integer arrays in FixedPool, searched at runtime
with binary search. No file I/O, no parsing at runtime.
"""

import sys
import os

def parse_alphabetic_ranges(path):
    """Parse DerivedCoreProperties.txt for Alphabetic ranges."""
    ranges = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if 'Alphabetic' not in line:
                continue
            parts = line.split(';')
            if len(parts) < 2:
                continue
            prop = parts[1].split('#')[0].strip()
            if prop != 'Alphabetic':
                continue
            cp_part = parts[0].strip()
            if '..' in cp_part:
                lo, hi = cp_part.split('..')
                ranges.append((int(lo, 16), int(hi, 16)))
            else:
                cp = int(cp_part, 16)
                ranges.append((cp, cp))
    return ranges


def parse_categories(path, cats):
    """Parse UnicodeData.txt for codepoints in given general categories.

    Handles both explicit codepoints and range markers like
    '<CJK Ideograph, First>' / '<CJK Ideograph, Last>'.
    """
    codepoints = []
    range_start = None
    with open(path) as f:
        for line in f:
            fields = line.strip().split(';')
            if len(fields) < 3:
                continue
            cp = int(fields[0], 16)
            name = fields[1]
            cat = fields[2]

            if name.endswith(', First>'):
                range_start = (cp, cat)
                continue
            if name.endswith(', Last>') and range_start is not None:
                if range_start[1] in cats:
                    for c in range(range_start[0], cp + 1):
                        codepoints.append(c)
                range_start = None
                continue

            range_start = None
            if cat in cats:
                codepoints.append(cp)
    return codepoints


def codepoints_to_ranges(cps):
    """Convert sorted list of codepoints to (start, end) ranges."""
    if not cps:
        return []
    cps = sorted(set(cps))
    ranges = []
    start = cps[0]
    end = cps[0]
    for cp in cps[1:]:
        if cp == end + 1:
            end = cp
        else:
            ranges.append((start, end))
            start = cp
            end = cp
    ranges.append((start, end))
    return ranges


def merge_ranges(r1, r2):
    """Merge two sorted range lists into one, coalescing overlaps."""
    all_ranges = sorted(r1 + r2)
    if not all_ranges:
        return []
    merged = [all_ranges[0]]
    for start, end in all_ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def parse_case_folding(path):
    """Parse CaseFolding.txt for Simple (C+S) mappings.
    Returns list of (from_cp, to_cp) sorted by from_cp.
    """
    mappings = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(';')
            if len(parts) < 3:
                continue
            status = parts[1].strip()
            if status not in ('C', 'S'):
                continue
            from_cp = int(parts[0].strip(), 16)
            to_cp = int(parts[2].strip().split()[0], 16)
            mappings.append((from_cp, to_cp))
    return sorted(mappings)


def compress_case_fold_runs(mappings):
    """Compress case fold mappings into (start, end, delta) runs.

    Consecutive codepoints with the same (to - from) offset are merged
    into a single run: fold(cp) = cp + delta for start <= cp <= end.
    """
    if not mappings:
        return []
    runs = []
    start, to_start = mappings[0]
    delta = to_start - start
    end = start

    for from_cp, to_cp in mappings[1:]:
        d = to_cp - from_cp
        if from_cp == end + 1 and d == delta:
            end = from_cp
        else:
            runs.append((start, end, delta))
            start = from_cp
            end = from_cp
            delta = d
    runs.append((start, end, delta))
    return runs


def emit_ailang(word_ranges, fold_runs, out_path):
    """Write AILang source with FixedPool tables."""

    # Word char ranges: flat array of [start0, end0, start1, end1, ...]
    # Binary search: find the range where start <= cp, check cp <= end.
    word_flat = []
    for s, e in word_ranges:
        word_flat.append(s)
        word_flat.append(e)

    # Case fold runs: flat array of [start0, end0, delta0, start1, end1, delta1, ...]
    # Binary search on start, check cp <= end, return cp + delta.
    fold_flat = []
    for s, e, d in fold_runs:
        fold_flat.append(s)
        fold_flat.append(e)
        # delta can be negative — store as signed 64-bit
        fold_flat.append(d)

    with open(out_path, 'w') as f:
        f.write("// AUTO-GENERATED by gen_unicode_tables.py — do not edit.\n")
        f.write("// Unicode 18.0.0 tables for grep: word characters and simple case folding.\n")
        f.write("// Regenerate: python3 gen_unicode_tables.py\n\n")

        # Word character range table
        f.write(f"// Word character ranges: {len(word_ranges)} ranges, "
                f"{len(word_flat)} integers\n")
        f.write(f"// (Letters + Marks + Digits + Connector_Punctuation + ZWNJ + ZWJ)\n")
        f.write("FixedPool.UnicodeWordRanges {\n")
        f.write(f'    "count": Initialize={len(word_ranges)}\n')
        # Emit ranges as individual named entries for FixedPool
        for i, (s, e) in enumerate(word_ranges):
            f.write(f'    "s{i}": Initialize={s}\n')
            f.write(f'    "e{i}": Initialize={e}\n')
        f.write("}\n\n")

        # Case fold run table
        f.write(f"// Simple case folding runs: {len(fold_runs)} runs, "
                f"{len(fold_flat)} integers\n")
        f.write("// (start, end, delta) — fold(cp) = cp + delta when start <= cp <= end\n")
        f.write("FixedPool.UnicodeCaseFoldRuns {\n")
        f.write(f'    "count": Initialize={len(fold_runs)}\n')
        for i, (s, e, d) in enumerate(fold_runs):
            f.write(f'    "s{i}": Initialize={s}\n')
            f.write(f'    "e{i}": Initialize={e}\n')
            f.write(f'    "d{i}": Initialize={d}\n')
        f.write("}\n")

    return len(word_ranges), len(fold_runs)


def emit_ailang_array(word_ranges, fold_runs, out_path):
    """Write AILang source using runtime-initialized arrays instead of FixedPool.

    FixedPool entries create named globals, which is fine but for 700+ ranges
    that's 1400+ globals. Instead we allocate arrays at init time and fill
    them with literal values. Binary search then operates on the flat arrays.
    """

    with open(out_path, 'w') as f:
        f.write("// AUTO-GENERATED by gen_unicode_tables.py — do not edit.\n")
        f.write("// Unicode 18.0.0 tables for grep: word characters and simple case folding.\n")
        f.write("// Regenerate: python3 gen_unicode_tables.py\n\n")

        # FixedPool for pointers and counts
        f.write("FixedPool.UnicodeData {\n")
        f.write(f'    "word_starts":     Initialize=0\n')
        f.write(f'    "word_ends":       Initialize=0\n')
        f.write(f'    "word_count":      Initialize={len(word_ranges)}\n')
        f.write(f'    "fold_starts":     Initialize=0\n')
        f.write(f'    "fold_ends":       Initialize=0\n')
        f.write(f'    "fold_deltas":     Initialize=0\n')
        f.write(f'    "fold_count":      Initialize={len(fold_runs)}\n')
        f.write(f'    "ready":           Initialize=0\n')
        f.write("}\n\n")

        # Init function that allocates and fills the arrays
        f.write("Function.UnicodeInit {\n")
        f.write("    Body: {\n")
        f.write("        IfCondition EqualTo(UnicodeData.ready, 0) ThenBlock: {\n")

        n_word = len(word_ranges)
        n_fold = len(fold_runs)

        # Word ranges: two arrays of 8 bytes each (64-bit integers)
        f.write(f"            UnicodeData.word_starts = Allocate({n_word * 8})\n")
        f.write(f"            UnicodeData.word_ends   = Allocate({n_word * 8})\n")

        for i, (s, e) in enumerate(word_ranges):
            f.write(f"            WRMEM_64(UnicodeData.word_starts, {i*8}, {s})\n")
            f.write(f"            WRMEM_64(UnicodeData.word_ends, {i*8}, {e})\n")

        f.write("\n")

        # Case fold runs: three arrays
        f.write(f"            UnicodeData.fold_starts = Allocate({n_fold * 8})\n")
        f.write(f"            UnicodeData.fold_ends   = Allocate({n_fold * 8})\n")
        f.write(f"            UnicodeData.fold_deltas = Allocate({n_fold * 8})\n")

        for i, (s, e, d) in enumerate(fold_runs):
            f.write(f"            WRMEM_64(UnicodeData.fold_starts, {i*8}, {s})\n")
            f.write(f"            WRMEM_64(UnicodeData.fold_ends, {i*8}, {e})\n")
            f.write(f"            WRMEM_64(UnicodeData.fold_deltas, {i*8}, {d})\n")

        f.write("\n            UnicodeData.ready = 1\n")
        f.write("        }\n")  # close IfCondition
        f.write("    }\n")
        f.write("}\n\n")

        # Binary search for word character
        f.write("// Binary search: is codepoint cp a word character?\n")
        f.write("// Returns 1 if yes, 0 if no.\n")
        f.write("Function.UnicodeIsWord {\n")
        f.write("    Input: cp: Integer\n")
        f.write("    Output: Integer\n")
        f.write("    Body: {\n")
        f.write("        lo = 0\n")
        f.write(f"        hi = Subtract(UnicodeData.word_count, 1)\n")
        f.write("        WhileLoop LessEqual(lo, hi) {\n")
        f.write("            mid = Divide(Add(lo, hi), 2)\n")
        f.write("            ms = RDMEM_64(UnicodeData.word_starts, Multiply(mid, 8))\n")
        f.write("            me = RDMEM_64(UnicodeData.word_ends, Multiply(mid, 8))\n")
        f.write("            IfCondition LessThan(cp, ms) ThenBlock: {\n")
        f.write("                hi = Subtract(mid, 1)\n")
        f.write("            } ElseBlock: {\n")
        f.write("                IfCondition GreaterThan(cp, me) ThenBlock: {\n")
        f.write("                    lo = Add(mid, 1)\n")
        f.write("                } ElseBlock: {\n")
        f.write("                    ReturnValue(1)\n")
        f.write("                }\n")
        f.write("            }\n")
        f.write("        }\n")
        f.write("        ReturnValue(0)\n")
        f.write("    }\n")
        f.write("}\n\n")

        # Binary search for case fold
        f.write("// Simple case fold: returns the folded codepoint.\n")
        f.write("// If cp has no fold mapping, returns cp unchanged.\n")
        f.write("Function.UnicodeFold {\n")
        f.write("    Input: cp: Integer\n")
        f.write("    Output: Integer\n")
        f.write("    Body: {\n")
        f.write("        lo = 0\n")
        f.write(f"        hi = Subtract(UnicodeData.fold_count, 1)\n")
        f.write("        WhileLoop LessEqual(lo, hi) {\n")
        f.write("            mid = Divide(Add(lo, hi), 2)\n")
        f.write("            ms = RDMEM_64(UnicodeData.fold_starts, Multiply(mid, 8))\n")
        f.write("            me = RDMEM_64(UnicodeData.fold_ends, Multiply(mid, 8))\n")
        f.write("            IfCondition LessThan(cp, ms) ThenBlock: {\n")
        f.write("                hi = Subtract(mid, 1)\n")
        f.write("            } ElseBlock: {\n")
        f.write("                IfCondition GreaterThan(cp, me) ThenBlock: {\n")
        f.write("                    lo = Add(mid, 1)\n")
        f.write("                } ElseBlock: {\n")
        f.write("                    md = RDMEM_64(UnicodeData.fold_deltas, Multiply(mid, 8))\n")
        f.write("                    ReturnValue(Add(cp, md))\n")
        f.write("                }\n")
        f.write("            }\n")
        f.write("        }\n")
        f.write("        ReturnValue(cp)\n")
        f.write("    }\n")
        f.write("}\n\n")

        # UTF-8 decoder
        f.write("// Decode one UTF-8 character from buf at offset pos.\n")
        f.write("// Returns the codepoint. Sets consumed bytes via the\n")
        f.write("// second output. Invalid sequences return 0xFFFD and\n")
        f.write("// consume 1 byte.\n")
        f.write("Function.UTF8Decode {\n")
        f.write("    Input: buf: Address\n")
        f.write("    Input: pos: Integer\n")
        f.write("    Input: len: Integer\n")
        f.write("    Input: out_advance: Address\n")
        f.write("    Output: Integer\n")
        f.write("    Body: {\n")
        f.write("        b0 = RDMEM_8(buf, pos)\n")
        f.write("        IfCondition LessThan(b0, 128) ThenBlock: {\n")
        f.write("            WRMEM_64(out_advance, 1)\n")
        f.write("            ReturnValue(b0)\n")
        f.write("        }\n")
        f.write("        IfCondition LessThan(b0, 194) ThenBlock: {\n")
        f.write("            WRMEM_64(out_advance, 1)\n")
        f.write("            ReturnValue(65533)\n")
        f.write("        }\n")
        f.write("        IfCondition LessThan(b0, 224) ThenBlock: {\n")
        f.write("            IfCondition LessThan(Subtract(len, pos), 2) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            b1 = RDMEM_8(buf, Add(pos, 1))\n")
        f.write("            IfCondition Or(LessThan(b1, 128), GreaterEqual(b1, 192)) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            cp = Add(Multiply(BitwiseAnd(b0, 31), 64), BitwiseAnd(b1, 63))\n")
        f.write("            WRMEM_64(out_advance, 2)\n")
        f.write("            ReturnValue(cp)\n")
        f.write("        }\n")
        f.write("        IfCondition LessThan(b0, 240) ThenBlock: {\n")
        f.write("            IfCondition LessThan(Subtract(len, pos), 3) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            b1 = RDMEM_8(buf, Add(pos, 1))\n")
        f.write("            b2 = RDMEM_8(buf, Add(pos, 2))\n")
        f.write("            IfCondition Or(LessThan(b1, 128), GreaterEqual(b1, 192)) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            IfCondition Or(LessThan(b2, 128), GreaterEqual(b2, 192)) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            cp = Add(Add(Multiply(BitwiseAnd(b0, 15), 4096), Multiply(BitwiseAnd(b1, 63), 64)), BitwiseAnd(b2, 63))\n")
        f.write("            IfCondition LessThan(cp, 2048) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            WRMEM_64(out_advance, 3)\n")
        f.write("            ReturnValue(cp)\n")
        f.write("        }\n")
        f.write("        IfCondition LessThan(b0, 245) ThenBlock: {\n")
        f.write("            IfCondition LessThan(Subtract(len, pos), 4) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            b1 = RDMEM_8(buf, Add(pos, 1))\n")
        f.write("            b2 = RDMEM_8(buf, Add(pos, 2))\n")
        f.write("            b3 = RDMEM_8(buf, Add(pos, 3))\n")
        f.write("            IfCondition Or(LessThan(b1, 128), GreaterEqual(b1, 192)) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            IfCondition Or(LessThan(b2, 128), GreaterEqual(b2, 192)) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            IfCondition Or(LessThan(b3, 128), GreaterEqual(b3, 192)) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            cp = Add(Add(Add(Multiply(BitwiseAnd(b0, 7), 262144), Multiply(BitwiseAnd(b1, 63), 4096)), Multiply(BitwiseAnd(b2, 63), 64)), BitwiseAnd(b3, 63))\n")
        f.write("            IfCondition Or(LessThan(cp, 65536), GreaterThan(cp, 1114111)) ThenBlock: {\n")
        f.write("                WRMEM_64(out_advance, 1)\n")
        f.write("                ReturnValue(65533)\n")
        f.write("            }\n")
        f.write("            WRMEM_64(out_advance, 4)\n")
        f.write("            ReturnValue(cp)\n")
        f.write("        }\n")
        f.write("        WRMEM_64(out_advance, 1)\n")
        f.write("        ReturnValue(65533)\n")
        f.write("    }\n")
        f.write("}\n\n")

        # UTF-8 encoder
        f.write("// Encode one codepoint as UTF-8 into buf at offset pos.\n")
        f.write("// Returns the number of bytes written (1-4).\n")
        f.write("Function.UTF8Encode {\n")
        f.write("    Input: buf: Address\n")
        f.write("    Input: pos: Integer\n")
        f.write("    Input: cp: Integer\n")
        f.write("    Output: Integer\n")
        f.write("    Body: {\n")
        f.write("        IfCondition LessThan(cp, 128) ThenBlock: {\n")
        f.write("            WRMEM_8(buf, pos, cp)\n")
        f.write("            ReturnValue(1)\n")
        f.write("        }\n")
        f.write("        IfCondition LessThan(cp, 2048) ThenBlock: {\n")
        f.write("            WRMEM_8(buf, pos, Add(192, Divide(cp, 64)))\n")
        f.write("            WRMEM_8(buf, Add(pos, 1), Add(128, BitwiseAnd(cp, 63)))\n")
        f.write("            ReturnValue(2)\n")
        f.write("        }\n")
        f.write("        IfCondition LessThan(cp, 65536) ThenBlock: {\n")
        f.write("            WRMEM_8(buf, pos, Add(224, Divide(cp, 4096)))\n")
        f.write("            WRMEM_8(buf, Add(pos, 1), Add(128, BitwiseAnd(Divide(cp, 64), 63)))\n")
        f.write("            WRMEM_8(buf, Add(pos, 2), Add(128, BitwiseAnd(cp, 63)))\n")
        f.write("            ReturnValue(3)\n")
        f.write("        }\n")
        f.write("        WRMEM_8(buf, pos, Add(240, Divide(cp, 262144)))\n")
        f.write("        WRMEM_8(buf, Add(pos, 1), Add(128, BitwiseAnd(Divide(cp, 4096), 63)))\n")
        f.write("        WRMEM_8(buf, Add(pos, 2), Add(128, BitwiseAnd(Divide(cp, 64), 63)))\n")
        f.write("        WRMEM_8(buf, Add(pos, 3), Add(128, BitwiseAnd(cp, 63)))\n")
        f.write("        ReturnValue(4)\n")
        f.write("    }\n")
        f.write("}\n")

    return len(word_ranges), len(fold_runs)


def main():
    ucd_dir = os.path.dirname(os.path.abspath(__file__))

    cf_path = os.path.join(ucd_dir, 'CaseFolding.txt')
    dcp_path = os.path.join(ucd_dir, 'DerivedCoreProperties.txt')
    ud_path = os.path.join(ucd_dir, 'UnicodeData.txt')
    out_path = os.path.join(ucd_dir, 'unicode_tables.ailang')

    for p in (cf_path, dcp_path, ud_path):
        if not os.path.exists(p):
            print(f"ERROR: Missing {p}", file=sys.stderr)
            sys.exit(1)

    print("Parsing Alphabetic property from DerivedCoreProperties.txt...")
    alpha_ranges = parse_alphabetic_ranges(dcp_path)
    print(f"  {len(alpha_ranges)} Alphabetic ranges")

    print("Parsing categories from UnicodeData.txt...")
    # Marks: Mn, Mc, Me
    mark_cps = parse_categories(ud_path, {'Mn', 'Mc', 'Me'})
    # Digits: Nd
    digit_cps = parse_categories(ud_path, {'Nd'})
    # Connector punctuation: Pc
    conn_cps = parse_categories(ud_path, {'Pc'})

    print(f"  {len(mark_cps)} Mark codepoints")
    print(f"  {len(digit_cps)} Digit codepoints")
    print(f"  {len(conn_cps)} Connector_Punctuation codepoints")

    # Add ZWNJ (U+200C) and ZWJ (U+200D) per UTS #18
    extra_cps = [0x200C, 0x200D]

    # Convert all to ranges and merge
    mark_ranges = codepoints_to_ranges(mark_cps)
    digit_ranges = codepoints_to_ranges(digit_cps)
    conn_ranges = codepoints_to_ranges(conn_cps)
    extra_ranges = codepoints_to_ranges(extra_cps)

    word_ranges = merge_ranges(alpha_ranges, mark_ranges)
    word_ranges = merge_ranges(word_ranges, digit_ranges)
    word_ranges = merge_ranges(word_ranges, conn_ranges)
    word_ranges = merge_ranges(word_ranges, extra_ranges)
    print(f"  => {len(word_ranges)} merged word-character ranges")

    # Count total codepoints
    total_cp = sum(e - s + 1 for s, e in word_ranges)
    print(f"  => {total_cp} total word codepoints")

    print("Parsing simple case folding from CaseFolding.txt...")
    fold_mappings = parse_case_folding(cf_path)
    print(f"  {len(fold_mappings)} simple mappings (C+S)")

    fold_runs = compress_case_fold_runs(fold_mappings)
    print(f"  => {len(fold_runs)} compressed runs")

    # Stats
    word_bytes = len(word_ranges) * 2 * 8  # two 8-byte arrays
    fold_bytes = len(fold_runs) * 3 * 8    # three 8-byte arrays
    print(f"\nMemory: {word_bytes} bytes word + {fold_bytes} bytes fold = "
          f"{word_bytes + fold_bytes} bytes total ({(word_bytes + fold_bytes) / 1024:.1f} KB)")

    print(f"Generating {out_path}...")
    nw, nf = emit_ailang_array(word_ranges, fold_runs, out_path)

    lines = sum(1 for _ in open(out_path))
    size = os.path.getsize(out_path)
    print(f"Done: {lines} lines, {size} bytes ({size/1024:.1f} KB)")
    print(f"  {nw} word ranges, {nf} case fold runs")


if __name__ == '__main__':
    main()
