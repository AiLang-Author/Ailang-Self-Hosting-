#!/bin/bash
# build_all_utils.sh - Compile all AILANG utilities
#
# Invoke from anywhere; script relocates to AiLangSH root so the
# compiler resolves Librarys/ relative to the parent tree (where all
# LibraryImport.* targets live). Each utility's source lives at
# AiLang_CoreUtils/dist/${util}_util/${util}.ailang and is compiled
# in place to ${util}_exec.

set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AILANG_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$AILANG_ROOT" || { echo "Cannot cd to AILANG_ROOT=$AILANG_ROOT"; exit 1; }

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     AILANG CoreUtils Builder${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  running from: $AILANG_ROOT${NC}"
echo ""

DEST_DIR="AiLang_CoreUtils/dist"
COMPILER="./ailang.x"

# List of all utilities to build
UTILS=(
    "echo" "cat" "ls" "wc" "grep" "head" "tail" "seq" "true" "false" "yes"
    "basename" "dirname" "sleep" "touch" "pwd" "whoami" "env" "cut" "tee"
    "uniq" "nl" "rev" "tac" "tr" "fold" "logname" "id" "printenv" "uname"
    "date" "find" "sort" "diff" "cp" "mkdir" "rm" "ln" "file" "mv" "chmod"
    "sync" "readlink" "tty" "realpath" "which" "nohup" "chown" "df" "chgrp"
    "stat" "du" "dd" "split" "expand" "unexpand" "paste"
)

# Sanity: compiler must exist and be executable, DEST_DIR must exist.
if [ ! -x "$COMPILER" ]; then
    echo -e "${RED}❌ Compiler not found at $COMPILER. Run from AiLang_CoreUtils/ inside AiLangSH.${NC}"
    exit 1
fi
if [ ! -d "$DEST_DIR" ]; then
    echo -e "${RED}❌ $DEST_DIR/ not found.${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Building ${#UTILS[@]} utilities from ${DEST_DIR}/<util>_util/<util>.ailang${NC}"
echo -e "${YELLOW}   Compiler: ${COMPILER}${NC}"
echo ""

success_count=0
fail_count=0
skip_count=0
failed_utils=()
skipped_utils=()

LOGDIR="$(mktemp -d)"

for util in "${UTILS[@]}"; do
    source_file="${DEST_DIR}/${util}_util/${util}.ailang"
    output_file="${DEST_DIR}/${util}_util/${util}_exec"

    if [ ! -f "$source_file" ]; then
        echo -e "${YELLOW}  - Skipping ${util} (source not found at ${source_file})${NC}"
        skip_count=$((skip_count + 1))
        skipped_utils+=("$util")
        continue
    fi

    printf "  Building ${YELLOW}%-10s${NC}" "$util"

    logfile="${LOGDIR}/${util}.log"
    if "$COMPILER" "$source_file" "$output_file" > "$logfile" 2>&1; then
        size=$(stat -c '%s' "$output_file" 2>/dev/null || ls -l "$output_file" | awk '{print $5}')
        echo -e "  ${GREEN}✓${NC}  ${output_file}  (${size} bytes)"
        success_count=$((success_count + 1))
    else
        echo -e "  ${RED}✗ FAILED${NC}  (log: ${logfile})"
        fail_count=$((fail_count + 1))
        failed_utils+=("$util")
    fi
done

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Build Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "Success: ${GREEN}${success_count}${NC}"
echo -e "Failed:  ${RED}${fail_count}${NC}"
echo -e "Skipped: ${YELLOW}${skip_count}${NC}"

if [ $fail_count -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed utilities (see ${LOGDIR}/<util>.log for details):${NC}"
    for util in "${failed_utils[@]}"; do
        echo -e "  - $util"
    done
fi

if [ $skip_count -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Skipped (no source file found):${NC}"
    for util in "${skipped_utils[@]}"; do
        echo -e "  - $util"
    done
fi

echo ""

if [ $success_count -gt 0 ]; then
    echo -e "${GREEN}✅ Built $success_count utilities successfully${NC}"
    echo ""
    echo "Next steps:"
    echo "  ./install_ailang_utils.sh    # Install to ~/.local/bin"
    echo "  ./bench_all_utils.sh         # Benchmark performance"
else
    echo -e "${RED}❌ No utilities were built successfully${NC}"
    exit 1
fi

# Non-zero exit if any util failed, so CI/caller can react.
exit $fail_count