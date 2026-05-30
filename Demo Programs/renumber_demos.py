#!/usr/bin/env python3
"""
Renumber AILang Demo Programs - Clean Gap-Free Sequence
Run from the project root or adjust paths.
Creates a clean 001_ to 132_ teaching sequence.
Moves the two advanced fork demos into the logical control-flow section.
"""

import os
import shutil
import subprocess
from pathlib import Path

# === CONFIG ===
PROJECT_ROOT = Path("/home/bob/Ailang-Self-Hosting-")
DEMO_DIR = PROJECT_ROOT / "Demo Programs" / "programs"
DRY_RUN = False   # Set to False to actually rename

# Curated teaching order (old filenames).
# We take the natural sorted list and surgically move the two fork companions
# right after the control-flow block (after 066_nested_if).
# This gives a beautiful linear curriculum.

def get_current_files():
    files = sorted([f for f in DEMO_DIR.iterdir() if f.suffix == ".ailang"], key=lambda p: p.name)
    return [f.name for f in files]

def build_new_order(current_files):
    """Build the desired clean teaching order."""
    # Start with everything in roughly original order
    order = list(current_files)

    # Remove the two special files so we can insert them in the perfect spot
    fork1 = "fork_not_switch.ailang"
    fork2 = "fork_branch_combinatorial.ailang"

    if fork1 in order:
        order.remove(fork1)
    if fork2 in order:
        order.remove(fork2)

    # Find the position right after the control flow lessons (after 066)
    # We insert the Fork/Branch companions here — this is the pedagogical sweet spot.
    insert_pos = None
    for i, name in enumerate(order):
        if name.startswith("066_"):
            insert_pos = i + 1
            break

    if insert_pos is None:
        insert_pos = 66  # fallback

    # Insert the two advanced companions in the best teaching order
    order.insert(insert_pos, fork1)      # First explain Fork
    order.insert(insert_pos + 1, fork2)  # Then the powerful combinatorial example

    # Now we have exactly 132 files in perfect teaching sequence
    return order

def main():
    current = get_current_files()
    print(f"Found {len(current)} demo programs.")

    new_order = build_new_order(current)
    assert len(new_order) == 132, f"Expected 132, got {len(new_order)}"

    print("\n=== NEW CLEAN NUMBERING (first 15 + control flow section + last 10) ===")
    for i, old in enumerate(new_order[:15], 1):
        print(f"  {i:03d}  <-  {old}")
    print("  ...")
    for i, old in enumerate(new_order[60:72], 61):
        print(f"  {i:03d}  <-  {old}")
    print("  ...")
    for i, old in enumerate(new_order[-10:], 123):
        print(f"  {i:03d}  <-  {old}")

    if DRY_RUN:
        print("\n[DRY RUN] No files were renamed.")
        return

    # Perform the actual renumbering
    print("\nRenumbering files to 001-132 clean sequence...")

    temp_dir = DEMO_DIR / "_renumber_temp"
    temp_dir.mkdir(exist_ok=True)

    # First move everything into temp with new names
    for new_num, old_name in enumerate(new_order, 1):
        old_path = DEMO_DIR / old_name
        # Preserve the descriptive slug (strip old number if present)
        if old_name[0].isdigit() and old_name[3] == "_":
            slug = old_name[4:]
        else:
            slug = old_name
        new_name = f"{new_num:03d}_{slug}"
        new_path = temp_dir / new_name
        shutil.move(str(old_path), str(new_path))
        print(f"  {old_name:35s}  ->  {new_name}")

    # Move back from temp
    for f in temp_dir.iterdir():
        shutil.move(str(f), str(DEMO_DIR / f.name))

    temp_dir.rmdir()

    print("\n✅ Renumbering complete. All demos now numbered 001-132 with no gaps.")
    print("   The two Fork/Branch companions are now in the ideal teaching position (around 067-068).")

if __name__ == "__main__":
    main()
