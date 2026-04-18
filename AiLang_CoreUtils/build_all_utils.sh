#!/bin/bash
# build_all_utils.sh - Compile all AILANG utilities

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     AILANG CoreUtils Builder${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

DEST_DIR="dist"

# List of all utilities to build
UTILS=(
    "echo" "cat" "ls" "wc" "grep" "head" "tail" "seq" "true" "false" "yes"
    "basename" "dirname" "sleep" "touch" "pwd" "whoami" "env" "cut" "tee"
    "uniq" "nl" "rev" "tac" "tr" "fold" "logname" "id" "printenv" "uname"
    "date" "find" "sort" "diff" "cp" "mkdir" "rm" "ln" "file" "mv" "chmod"
    "sync" "readlink" "tty" "realpath" "which" "nohup" "chown" "df" "chgrp"
    "stat" "du" "dd" "split" "expand" "unexpand" "paste"
)

echo -e "${YELLOW}🔍 Discovering utilities in the current directory to build into '$DEST_DIR/'...${NC}"

# Clean and create destination directory
mkdir -p "$DEST_DIR"

# Check if compiler exists
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ main.py not found! Run this from the ailang directory.${NC}"
    exit 1
fi

# Compile each utility
success_count=0
fail_count=0
failed_utils=()

for util in "${UTILS[@]}"; do
    source_file="${util}.ailang"

    if [ ! -f "$source_file" ]; then
        echo -e "${YELLOW}  - Skipping ${util} (source not found)${NC}"
        continue
    fi

    # Define output directory and file
    output_dir="${DEST_DIR}/${util}_util"
    mkdir -p "$output_dir"
    output_file="${output_dir}/${util}_exec"

    echo -e "${YELLOW}Building ${util}...${NC}"
    
    if python3 main.py "$source_file" -o "$output_file" > /dev/null 2>&1; then
        size=$(ls -lh "$output_file" | awk '{print $5}')
        echo -e "${GREEN}  ✓ ${util} -> ${output_file} (${size})${NC}"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}  ✗ ${util} compilation failed${NC}"
        echo -e "    To debug, run: python3 main.py \"$source_file\" -o \"$output_file\""
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

if [ $fail_count -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed utilities:${NC}"
    for util in "${failed_utils[@]}"; do
        echo -e "  - $util"
    done
fi

echo ""

if [ $success_count -gt 0 ]; then
    echo -e "${GREEN}✅ Built $success_count utilities successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  ./install_ailang_utils.sh    # Install to ~/.local/bin"
    echo "  ./bench_all_utils.sh         # Benchmark performance"
else
    echo -e "${RED}❌ No utilities were built successfully${NC}"
    exit 1
fi