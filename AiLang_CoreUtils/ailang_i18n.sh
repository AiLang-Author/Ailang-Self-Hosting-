#!/bin/bash
# ailang_i18n.sh - Internationalization for AILANG utilities
# 
# PHILOSOPHY: Translation happens in the shell, not in utilities.
# This keeps binaries fast and lean while allowing optional i18n.
#
# INSTALLATION:
#   Source this file in ~/.bashrc or /etc/bash.bashrc:
#   source /usr/share/ailang/ailang_i18n.sh
#
# USAGE:
#   Set LANG environment variable (e.g., LANG=es_ES.UTF-8)
#   Translation files live in: /usr/share/ailang/translations/
#
.

# Only activate if LANG is set and not English
if [ -z "$LANG" ] || [[ "$LANG" =~ ^en ]]; then
    # English or unset - no translation needed
    return 0
fi

# Translation directory
AILANG_TRANS_DIR="${AILANG_TRANS_DIR:-/usr/share/ailang/translations}"

# Extract language code (e.g., es_ES.UTF-8 -> es_ES)
AILANG_LANG="${LANG%.*}"
AILANG_TRANS_FILE="$AILANG_TRANS_DIR/$AILANG_LANG.trans"

# Check if translation file exists
if [ ! -f "$AILANG_TRANS_FILE" ]; then
    # No translation available, silently continue in English
    return 0
fi

# Translation function - simple sed-based replacement
# Faster than jq, no dependencies
ailang_translate() {
    local sedscript="/tmp/ailang_trans_$$.sed"
    
    # Build sed script from translation file on first use
    if [ ! -f "$sedscript" ]; then
        awk -F'|' '{
            gsub(/[\/&]/, "\\\\&", $1);  # Escape sed metacharacters in pattern
            gsub(/[\/&]/, "\\\\&", $2);  # Escape sed metacharacters in replacement
            print "s/" $1 "/" $2 "/g"
        }' "$AILANG_TRANS_FILE" > "$sedscript"
        
        # Clean up on shell exit
        trap "rm -f $sedscript" EXIT
    fi
    
    # Run the actual command and translate output
    "$@" 2>&1 | sed -f "$sedscript"
    return ${PIPESTATUS[0]}  # Return original command's exit code
}

# List of AILANG utilities to auto-wrap
# Add more as you build them
AILANG_UTILS=(
    # Core utils
    cat wc head tail grep uniq sort cut paste tee
    # File ops
    ls cp mv rm mkdir touch chmod chown ln
    # Text processing
    sed awk tr rev tac nl fold
    # System
    echo true false basename dirname pwd whoami
    # Others
    find diff
)

# Create aliases for each utility
for util in "${AILANG_UTILS[@]}"; do
    # Only alias if the AILANG version exists
    if command -v "${util}_ailang" >/dev/null 2>&1; then
        alias "$util"="ailang_translate ${util}_ailang"
    elif [ -x "$HOME/.local/bin/$util" ]; then
        # Check if it's an AILANG binary (symlink to ailang dir)
        if readlink "$HOME/.local/bin/$util" 2>/dev/null | grep -q ailang; then
            alias "$util"="ailang_translate $util"
        fi
    fi
done

# Export function for subshells
export -f ailang_translate

# Print activation message (only on interactive shells)
if [[ $- == *i* ]]; then
    echo "AILANG i18n: Translations active for $AILANG_LANG" >&2
fi
