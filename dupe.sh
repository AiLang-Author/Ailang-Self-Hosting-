#!/bin/bash
# pool_collisions.sh - Find duplicate FixedPool definitions in AILang codebase
# Usage: ./pool_collisions.sh [search_path]

SEARCH_PATH="${1:-Librarys}"
TEMP_DIR=$(/usr/bin/mktemp -d)
trap "/bin/rm -rf $TEMP_DIR" EXIT

echo "========================================"
echo "AILang FixedPool Collision Detector"
echo "========================================"
echo "Scanning: $SEARCH_PATH"
echo ""

# Step 1: Extract all FixedPool definitions with file locations
echo "Step 1: Finding all FixedPool definitions..."
/usr/bin/find "$SEARCH_PATH" -name "*.ailang" -type f ! -name "*.bak*" | while read file; do
    # Extract pool names and line numbers
    /usr/bin/grep -n "^FixedPool\." "$file" 2>/dev/null | while read line; do
        line_num=$(/bin/echo "$line" | /usr/bin/cut -d: -f1)
        pool_def=$(/bin/echo "$line" | /usr/bin/cut -d: -f2-)
        # Extract just the pool name (FixedPool.NAME)
        pool_name=$(/bin/echo "$pool_def" | /usr/bin/sed 's/FixedPool\.\([A-Za-z_][A-Za-z0-9_]*\).*/\1/')
        /bin/echo "${pool_name}|${file}|${line_num}"
    done
done > "$TEMP_DIR/all_pools.txt"

# Step 2: Find duplicates
echo "Step 2: Identifying duplicates..."
echo ""

# Get unique pool names that appear more than once
/usr/bin/cut -d'|' -f1 "$TEMP_DIR/all_pools.txt" | /usr/bin/sort | /usr/bin/uniq -c | /usr/bin/sort -rn > "$TEMP_DIR/pool_counts.txt"

# Count stats
total_pools=$(/usr/bin/wc -l < "$TEMP_DIR/all_pools.txt" | /usr/bin/tr -d ' ')
unique_pools=$(/usr/bin/cut -d'|' -f1 "$TEMP_DIR/all_pools.txt" | /usr/bin/sort -u | /usr/bin/wc -l | /usr/bin/tr -d ' ')
duplicate_names=$(/usr/bin/awk '$1 > 1 {print $2}' "$TEMP_DIR/pool_counts.txt" | /usr/bin/wc -l | /usr/bin/tr -d ' ')

echo "Summary:"
echo "  Total FixedPool definitions: $total_pools"
echo "  Unique pool names: $unique_pools"
echo "  Pool names with duplicates: $duplicate_names"
echo ""

if [ "$duplicate_names" -eq 0 ]; then
    echo "✅ No duplicate FixedPool names found!"
    exit 0
fi

echo "========================================"
echo "DUPLICATE FIXEDPOOLS FOUND"
echo "========================================"
echo ""

# Step 3: For each duplicate, show details
/usr/bin/awk '$1 > 1 {print $2}' "$TEMP_DIR/pool_counts.txt" | while read pool_name; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "DUPLICATE: FixedPool.$pool_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    /usr/bin/grep "^${pool_name}|" "$TEMP_DIR/all_pools.txt" | while read entry; do
        file=$(/bin/echo "$entry" | /usr/bin/cut -d'|' -f2)
        line_num=$(/bin/echo "$entry" | /usr/bin/cut -d'|' -f3)
        
        echo ""
        echo "  📁 $file:$line_num"
        
        # Extract first 5 members of this pool definition
        echo "     Members:"
        /usr/bin/awk -v start="$line_num" 'NR >= start && NR <= start+15 {
            if (/^}/) exit
            if (/"[^"]+":/) {
                gsub(/^[[:space:]]+/, "")
                print "       " $0
            }
        }' "$file" | /usr/bin/head -5
        
        # Check if there are more members
        member_count=$(/usr/bin/awk -v start="$line_num" 'NR >= start {
            if (/^}/) exit
            if (/"[^"]+":/) count++
        } END {print count+0}' "$file")
        
        if [ "$member_count" -gt 5 ]; then
            remaining=$((member_count - 5))
            echo "       ... and $remaining more members"
        fi
    done
    echo ""
done

echo ""
echo "========================================"
echo "RECOMMENDED ACTIONS"
echo "========================================"
echo ""

# Generate rename suggestions
/usr/bin/awk '$1 > 1 {print $2}' "$TEMP_DIR/pool_counts.txt" | while read pool_name; do
    echo "For FixedPool.$pool_name:"
    
    # Get file list
    files=$(/usr/bin/grep "^${pool_name}|" "$TEMP_DIR/all_pools.txt" | /usr/bin/cut -d'|' -f2)
    
    for file in $files; do
        basename=$(/usr/bin/basename "$file" .ailang)
        
        # Suggest rename based on module
        if [[ "$basename" == *"Emit"* ]]; then
            echo "  - In $basename: Consider renaming to Emit${pool_name} or ELF${pool_name}"
        elif [[ "$basename" == *"Lexer"* ]]; then
            echo "  - In $basename: Consider renaming to Lex${pool_name}"
        elif [[ "$basename" == *"Parser"* ]]; then
            echo "  - In $basename: Consider renaming to Parse${pool_name}"
        elif [[ "$basename" == *"AST"* ]] || [[ "$basename" == *"Semantic"* ]]; then
            echo "  - In $basename: This is likely the canonical definition (keep as-is)"
        else
            echo "  - In $basename: Review which module should own this pool"
        fi
    done
    echo ""
done

echo "========================================"
echo "REFERENCE FINDER"
echo "========================================"
echo ""
echo "To find all references to a pool member, run:"
echo "  /usr/bin/grep -rn 'PoolName.MemberName' $SEARCH_PATH"
echo ""
echo "Example for SymType:"
echo "  /usr/bin/grep -rn 'SymType\.' $SEARCH_PATH --include='*.ailang'"