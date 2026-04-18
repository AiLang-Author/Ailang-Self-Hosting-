#!/bin/bash
# package_for_github.sh - Organizes each utility into its own folder for distribution.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Destination directory
DEST_DIR="dist"

# List of all utilities
UTILS=(
    "echo" "cat" "ls" "wc" "grep" "head" "tail" "seq" "true" "false" "yes"
    "basename" "dirname" "sleep" "touch" "pwd" "whoami" "env" "cut" "tee"
    "uniq" "nl" "rev" "tac" "tr" "fold" "logname" "id" "printenv" "uname"
    "date" "find" "sort" "diff" "cp" "mkdir" "rm" "ln" "file" "mv" "chmod"
    "sync" "readlink" "tty" "realpath" "which" "nohup" "chown" "df" "chgrp"
    "stat" "du" "dd" "split" "expand" "unexpand" "paste"
)

echo -e "${BLUE}📦 Packaging AILANG Utilities for GitHub${NC}"
echo "=========================================="
echo ""

# Clean and create destination directory
echo -e "${YELLOW}🧹 Cleaning and creating destination directory: $DEST_DIR/${NC}"
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"
echo ""

packaged_count=0

# Loop through each utility and package it
for util in "${UTILS[@]}"; do
    echo -e "${YELLOW}Processing ${util}...${NC}"
    
    source_file="${util}.ailang"
    exec_file="${util}_exec"
    
    # Check if source file exists
    if [ ! -f "$source_file" ]; then
        echo -e "  ${RED}✗ Source file '$source_file' not found. Skipping.${NC}"
        continue
    fi
    
    # Check if executable exists
    if [ ! -f "$exec_file" ]; then
        echo -e "  ${RED}✗ Executable '$exec_file' not found. Skipping.${NC}"
        echo -e "  (Run ./build_all_utils.sh first)"
        continue
    fi
    
    # Create the utility's dedicated folder
    util_dir="${DEST_DIR}/${util}_util"
    mkdir -p "$util_dir"
    
    # Copy the source and executable files
    /bin/cp "$source_file" "$util_dir/"
    /bin/cp "$exec_file" "$util_dir/"
    
    # Copy the README for the utility, if it exists
    readme_source_file="docs/${util}.md"
    if [ -f "$readme_source_file" ]; then
        cp "$readme_source_file" "${util_dir}/README.md"
    fi
    
    echo -e "  ${GREEN}✓ Packaged '$source_file' and '$exec_file' into '$util_dir/'${NC}"
    packaged_count=$((packaged_count + 1))
done

echo ""
echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo -e "${BLUE}Packaging Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════${NC}"

if [ $packaged_count -gt 0 ]; then
    echo -e "${GREEN}✅ Successfully packaged $packaged_count utilities into the '$DEST_DIR/' directory.${NC}"
else
    echo -e "${RED}❌ No utilities were packaged. Ensure source and executable files exist.${NC}"
fi
echo ""