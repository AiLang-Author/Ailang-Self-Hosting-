#!/bin/bash
# pool_cleanup.sh - Fix FixedPool collisions in AILang codebase
# Creates .bak backups of ALL files before modifying
# Usage: ./pool_cleanup.sh [--dry-run]

SEARCH_PATH="Librarys"
DRY_RUN=0
BACKUP_DIR="pool_cleanup_backups_$(date +%Y%m%d_%H%M%S)"

if [ "$1" == "--dry-run" ]; then
    DRY_RUN=1
    echo "=== DRY RUN MODE - No changes will be made ==="
    echo ""
fi

echo "========================================"
echo "AILang FixedPool Collision Cleanup"
echo "========================================"
echo ""

# ============================================
# PHASE 0: Create backup directory
# ============================================
if [ "$DRY_RUN" -eq 0 ]; then
    echo "PHASE 0: Creating backup directory..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    /bin/mkdir -p "$BACKUP_DIR"
    echo "  Backup dir: $BACKUP_DIR"
    echo ""
fi

# Helper: backup a file before modifying
backup_file() {
    local file="$1"
    if [ "$DRY_RUN" -eq 0 ] && [ -f "$file" ]; then
        local backup_name=$(/bin/echo "$file" | /usr/bin/tr '/' '_')
        /bin/cp "$file" "$BACKUP_DIR/$backup_name"
        echo "    [BACKUP] $file"
    fi
}

# Helper: remove a FixedPool block from a file
remove_pool_block() {
    local file="$1"
    local pool_name="$2"
    
    if ! /usr/bin/grep -q "^FixedPool\.${pool_name}" "$file" 2>/dev/null; then
        echo "    [SKIP] FixedPool.$pool_name not found"
        return 0
    fi
    
    local start_line=$(/usr/bin/grep -n "^FixedPool\.${pool_name}" "$file" | /usr/bin/head -1 | /usr/bin/cut -d: -f1)
    local end_line=$(/usr/bin/awk -v start="$start_line" 'NR >= start && /^}/ {print NR; exit}' "$file")
    
    echo "    Removing FixedPool.$pool_name (lines $start_line-$end_line)"
    
    if [ "$DRY_RUN" -eq 0 ]; then
        /usr/bin/awk -v start="$start_line" -v end="$end_line" \
            'NR < start || NR > end' "$file" > "${file}.tmp"
        /bin/mv "${file}.tmp" "$file"
    fi
    echo "    ✓ Removed"
}

# Helper: rename pool and all references
# $4 = optional regex pattern for members to match (only rename refs matching these members)
rename_pool() {
    local old_name="$1"
    local new_name="$2"
    local target_file="$3"
    local member_pattern="$4"  # e.g., "NOTYPE|OBJECT|FUNC|SECTION|FILE|LOCAL|GLOBAL|WEAK"
    
    echo ""
    echo "  Renaming: $old_name -> $new_name"
    echo "  In file:  $target_file"
    if [ -n "$member_pattern" ]; then
        echo "  Only members matching: $member_pattern"
    fi
    
    if [ ! -f "$target_file" ]; then
        echo "    [ERROR] File not found!"
        return 1
    fi
    
    if ! /usr/bin/grep -q "^FixedPool\.${old_name}" "$target_file"; then
        echo "    [SKIP] Pool not found in file"
        return 0
    fi
    
    # Build search pattern based on members
    if [ -n "$member_pattern" ]; then
        search_pattern="${old_name}\.\(${member_pattern}\)"
    else
        search_pattern="${old_name}\."
    fi
    
    # Find files that reference the SPECIFIC members we're renaming
    local ref_files=$(/usr/bin/grep -rl "$search_pattern" "$SEARCH_PATH" --include="*.ailang" 2>/dev/null | /usr/bin/sort -u)
    local ref_count=$(/bin/echo "$ref_files" | /usr/bin/grep -c . 2>/dev/null || echo 0)
    echo "    Found $ref_count files with matching references"
    
    if [ "$DRY_RUN" -eq 0 ]; then
        # Backup and modify target file (rename pool definition)
        backup_file "$target_file"
        /usr/bin/sed -i "s/^FixedPool\.${old_name}/FixedPool.${new_name}/" "$target_file"
        
        # Backup and modify referencing files
        for file in $ref_files; do
            if [ "$file" != "$target_file" ]; then
                backup_file "$file"
            fi
            
            if [ -n "$member_pattern" ]; then
                # Only rename references to specific members
                /usr/bin/sed -i "s/${old_name}\.\(${member_pattern}\)/${new_name}.\1/g" "$file"
            else
                # Rename all references
                /usr/bin/sed -i "s/${old_name}\./${new_name}./g" "$file"
            fi
        done
    else
        echo "    [DRY RUN] Would modify these files:"
        for file in $ref_files; do
            local count=$(/usr/bin/grep -c "$search_pattern" "$file" 2>/dev/null || echo 0)
            echo "      $file ($count refs)"
            # Show actual matches
            /usr/bin/grep -o "${old_name}\.[A-Z_]*" "$file" 2>/dev/null | /usr/bin/sort -u | /usr/bin/head -5 | while read match; do
                echo "        -> $match"
            done
        done
    fi
    
    echo "    ✓ Renamed $old_name -> $new_name"
}

# ============================================
# PHASE 1: Remove subset pools from CEmitTypes
# ============================================
echo "PHASE 1: Removing duplicate pools from CEmitTypes.ailang..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

EMIT_TYPES="Librarys/Compiler/CodeEmit/Library.CEmitTypes.ailang"

if [ -f "$EMIT_TYPES" ]; then
    echo "  Target: $EMIT_TYPES"
    
    if [ "$DRY_RUN" -eq 0 ]; then
        backup_file "$EMIT_TYPES"
    fi
    
    # Remove SysNum (subset of CSyscallTable's 345 syscalls)
    remove_pool_block "$EMIT_TYPES" "SysNum"
    
    # Remove FD (identical to CSyscallTable)
    remove_pool_block "$EMIT_TYPES" "FD"
    
    # Remove Arch if it's the 1-member subset
    arch_members=$(/usr/bin/awk '/^FixedPool\.Arch/,/^}/' "$EMIT_TYPES" 2>/dev/null | /usr/bin/grep -c '"' || echo 0)
    if [ "$arch_members" -lt 3 ] && [ "$arch_members" -gt 0 ]; then
        echo "    FixedPool.Arch has only $arch_members member(s) - removing subset..."
        remove_pool_block "$EMIT_TYPES" "Arch"
    fi
    
    # NOTE: DataRelocField is handled in Phase 4 (rename, not remove)
else
    echo "  [ERROR] CEmitTypes.ailang not found!"
fi
echo ""

# ============================================
# PHASE 2: Rename SymType -> ELFSymType
# ============================================
echo "PHASE 2: Renaming SymType in CEmitTypes..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# IMPORTANT: Only rename the ELF SymType members, NOT the semantic SYM_* members
# ELF members: NOTYPE, OBJECT, FUNC, SECTION, FILE, LOCAL, GLOBAL, WEAK
# Semantic members (keep as-is): SYM_UNKNOWN, SYM_FUNCTION, SYM_VARIABLE, etc.
ELF_SYMTYPE_MEMBERS="NOTYPE|OBJECT|FUNC|SECTION|FILE|LOCAL|GLOBAL|WEAK"

rename_pool "SymType" "ELFSymType" "$EMIT_TYPES" "$ELF_SYMTYPE_MEMBERS"

echo ""

# ============================================
# PHASE 3: Rename RelocType -> X86RelocKind
# ============================================
echo "PHASE 3: Renaming RelocType in CEmitX86Helpers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# X86Helpers has: DATA_ABS64, CODE_REL32
# CEmitTypes has: R_X86_64_* (different members, no collision in references)
X86_RELOC_MEMBERS="DATA_ABS64|CODE_REL32"

X86_HELPERS="Librarys/Compiler/CodeEmit/X86/Library.CEmitX86Helpers.ailang"
rename_pool "RelocType" "X86RelocKind" "$X86_HELPERS" "$X86_RELOC_MEMBERS"

echo ""

# ============================================
# PHASE 4: Rename DataRelocField -> CodeRelocField in CEmitTypes
# ============================================
echo "PHASE 4: Renaming DataRelocField in CEmitTypes..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# CEmitTypes has CODE_POSITION, CEmitCore has POSITION - different members!
# Rename CEmitTypes version to CodeRelocField
CODERELOC_MEMBERS="CODE_POSITION"

rename_pool "DataRelocField" "CodeRelocField" "$EMIT_TYPES" "$CODERELOC_MEMBERS"

echo ""

# ============================================
# PHASE 5: Verification
# ============================================
echo "PHASE 5: Verification..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$DRY_RUN" -eq 0 ]; then
    # Quick duplicate check
    dupes=$(/usr/bin/find "$SEARCH_PATH" -name "*.ailang" -type f ! -path "*.bak*" -exec \
        /usr/bin/grep -h "^FixedPool\." {} \; 2>/dev/null | \
        /usr/bin/sed 's/FixedPool\.\([A-Za-z_][A-Za-z0-9_]*\).*/\1/' | \
        /usr/bin/sort | /usr/bin/uniq -d)
    
    if [ -z "$dupes" ]; then
        echo "  ✅ No duplicate FixedPool names found!"
    else
        echo "  ⚠️  Remaining duplicates:"
        /bin/echo "$dupes" | while read d; do
            echo "      - FixedPool.$d"
            /usr/bin/grep -rn "^FixedPool\.${d}" "$SEARCH_PATH" --include="*.ailang" 2>/dev/null | /usr/bin/head -3
        done
    fi
    
    echo ""
    echo "  Backups saved to: $BACKUP_DIR/"
    echo "  Files backed up:"
    /bin/ls -1 "$BACKUP_DIR/" 2>/dev/null | /usr/bin/wc -l | /usr/bin/tr -d ' '
else
    echo "  [DRY RUN] Skipping verification"
fi

echo ""
echo "========================================"
echo "CLEANUP COMPLETE"
echo "========================================"
if [ "$DRY_RUN" -eq 1 ]; then
    echo ""
    echo "This was a dry run. To apply changes, run:"
    echo "  ./pool_cleanup.sh"
else
    echo ""
    echo "To restore from backups if needed:"
    echo "  /bin/cp $BACKUP_DIR/Librarys_* ./Librarys/ (adjust paths)"
    echo ""
    echo "To remove backups after verifying:"
    echo "  /bin/rm -rf $BACKUP_DIR"
fi