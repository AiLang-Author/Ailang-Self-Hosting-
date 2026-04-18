#!/usr/bin/env bash
# install_ailang_utils.sh — Install AILANG CoreUtils.
#
# Convention (April 2026 refresh):
#   * Compiled binaries use the .x extension everywhere — no more _exec
#     in dist/ and no more _ailang in the central install dir.
#   * `./install_ailang_utils.sh`              installs every *.x found in dist/
#   * `./install_ailang_utils.sh head wc cat`  installs only those
#
# Layout after install:
#   ~/.local/bin/ailang/<util>.x   ← the binary
#   ~/.local/bin/<util>            ← symlink → ~/.local/bin/ailang/<util>.x

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

AILANG_DIR="$HOME/.local/bin/ailang"
BIN_DIR="$HOME/.local/bin"

echo -e "${BLUE}🔧 AILANG Utilities Installer${NC}"
echo "================================"
echo ""

if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Don't run as root — installs go to the user directory.${NC}"
    exit 1
fi

mkdir -p "$AILANG_DIR" "$BIN_DIR"

# ------------------------------------------------------------------
# Per-utility selection. If any args are supplied, treat each as a
# utility name to install. Otherwise install everything we can find.
# ------------------------------------------------------------------
SELECTED=("$@")
if [ ${#SELECTED[@]} -gt 0 ]; then
    echo -e "${YELLOW}🎯 Installing only: ${SELECTED[*]}${NC}"
else
    echo -e "${YELLOW}🎯 Installing every *.x found in dist/${NC}"
fi
echo ""

# ------------------------------------------------------------------
# Cleanup. Two modes:
#   - Full install (no args): prune every symlink in BIN_DIR that points
#     into AILANG_DIR so we don't leave stale entries. Central binaries
#     are left in place so legacy *_ailang / *_exec names keep working
#     alongside the new *.x naming.
#   - Selective install (args given): only the specified utilities are
#     touched. Other installed utilities are untouched.
# ------------------------------------------------------------------
if [ ${#SELECTED[@]} -eq 0 ]; then
    echo -e "${YELLOW}🧹 Full install — cleaning stale symlinks in $BIN_DIR...${NC}"
    find "$BIN_DIR" -maxdepth 1 -type l -exec bash -c '
        for link; do
            target=$(readlink "$link")
            if [ -n "$target" ] && [[ "$target" == *"/ailang/"* ]]; then
                echo "  - removing old symlink: $(basename "$link")"
                rm -f "$link"
            fi
        done
    ' bash {} +
else
    echo -e "${YELLOW}🧹 Selective install — only touching: ${SELECTED[*]}${NC}"
fi

# ------------------------------------------------------------------
# Install loop — picks up dist/<name>_util/<name>.x and dist/<name>.x.
# ------------------------------------------------------------------
echo ""
echo -e "${YELLOW}📦 Installing...${NC}"
echo ""

found_count=0

install_one() {
    local exec_file="$1"
    local base_name util
    base_name=$(basename "$exec_file")
    # Strip either new-style .x or legacy _exec suffix.
    util=${base_name%.x}
    util=${util%_exec}

    if [ ${#SELECTED[@]} -gt 0 ]; then
        local match=0
        for want in "${SELECTED[@]}"; do
            [ "$want" = "$util" ] && match=1 && break
        done
        [ $match -eq 1 ] || return 0
    fi

    echo -e "${GREEN}  ✓ ${util}${NC}"
    # Use absolute /usr/bin paths — the AILANG replacements for these
    # commands may be on PATH and may themselves be incomplete (e.g.
    # missing SUFFIX support in basename). They also can fail with
    # "Text file busy" when overwriting a currently-executing binary,
    # so rm+cp rather than cp-over-existing.
    /usr/bin/rm -f "$AILANG_DIR/${util}.x"
    /usr/bin/cp "$exec_file" "$AILANG_DIR/${util}.x"
    /usr/bin/chmod +x "$AILANG_DIR/${util}.x"
    /usr/bin/ln -sfn "$AILANG_DIR/${util}.x" "$BIN_DIR/$util"
    found_count=$((found_count + 1))
}

# Prefer freshly-built .x; fall back to legacy _exec so pre-refresh
# dist/ trees still install without needing a full rebuild first.
#
# Files named *.ailang.x are treated as backups of previous builds —
# explicitly skipped here so they aren't installed over the current
# build and aren't deleted by the cleanup path. Keep them around.
declare -A seen
shopt -s nullglob
for exec_file in dist/*/*.x dist/*.x dist/*/*_exec dist/*_exec; do
    [ -f "$exec_file" ] || continue
    base=$(basename "$exec_file")
    case "$base" in
        *.ailang.x) continue ;;   # backup snapshot, leave alone
    esac
    util=${base%.x}
    util=${util%_exec}
    [ -n "${seen[$util]:-}" ] && continue
    seen[$util]=1
    install_one "$exec_file"
done
shopt -u nullglob

if [ $found_count -eq 0 ]; then
    echo -e "${RED}❌ No matching *.x files found in dist/.${NC}"
    echo ""
    echo "Expected layout: dist/<util>_util/<util>.x"
    echo ""
    echo "What I see:"
    ls -la dist/ 2>/dev/null | head -10 || echo "dist/ directory not found"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Installed $found_count utilities${NC}"

# ------------------------------------------------------------------
# Rewrite the ailang-utils manager to match the .x convention.
# ------------------------------------------------------------------
echo ""
echo -e "${YELLOW}📝 Refreshing ailang-utils manager...${NC}"

cat > "$BIN_DIR/ailang-utils" << 'MANAGER_SCRIPT'
#!/usr/bin/env bash
# AILANG Utils Manager — .x convention

AILANG_DIR="$HOME/.local/bin/ailang"
BIN_DIR="$HOME/.local/bin"

get_utils() {
    find "$AILANG_DIR" -type f -name '*.x' 2>/dev/null \
        | xargs -n 1 basename \
        | sed 's/\.x$//' \
        | sort | tr '\n' ' '
}

show_status() {
    echo "AILANG Utilities Status:"
    echo "========================"
    for util in $(get_utils); do
        if [ -L "$BIN_DIR/$util" ] && [[ "$(readlink "$BIN_DIR/$util")" == *"/ailang/"* ]]; then
            echo "  $util: ✅ AILANG"
        elif command -v "$util" >/dev/null 2>&1; then
            if [ -f "$AILANG_DIR/${util}.x" ]; then
                echo "  $util: ⚪ Available (system version active)"
            else
                echo "  $util: 🔵 System"
            fi
        else
            echo "  $util: ❌ Not found"
        fi
    done
}

list_utils() {
    echo "Installed AILANG Utilities:"
    echo "==========================="
    for f in "$AILANG_DIR"/*.x; do
        [ -f "$f" ] || continue
        util=$(basename "$f" .x)
        size=$(ls -lh "$f" | awk '{print $5}')
        status="⚪"
        [ -L "$BIN_DIR/$util" ] && [[ "$(readlink "$BIN_DIR/$util")" == *"/ailang/"* ]] && status="✅"
        echo "  $status $util ($size)"
    done
}

enable_util() {
    local util="$1"
    if [ "$util" = "all" ]; then
        for u in $(get_utils); do
            [ -f "$AILANG_DIR/${u}.x" ] || continue
            ln -sfn "$AILANG_DIR/${u}.x" "$BIN_DIR/$u"
            echo "✅ Enabled $u"
        done
    else
        if [ -f "$AILANG_DIR/${util}.x" ]; then
            ln -sfn "$AILANG_DIR/${util}.x" "$BIN_DIR/$util"
            echo "✅ Enabled $util"
        else
            echo "❌ $util not found in $AILANG_DIR"
            exit 1
        fi
    fi
}

disable_util() {
    local util="$1"
    if [ "$util" = "all" ]; then
        for u in $(get_utils); do
            if [ -L "$BIN_DIR/$u" ]; then
                target=$(readlink "$BIN_DIR/$u")
                [[ "$target" == *"ailang"* ]] && rm "$BIN_DIR/$u" && echo "✅ Disabled $u"
            fi
        done
    else
        if [ -L "$BIN_DIR/$util" ]; then
            rm "$BIN_DIR/$util"
            echo "✅ Disabled $util"
        else
            echo "ℹ️  $util not currently enabled"
        fi
    fi
}

benchmark_util() {
    local util="$1"
    local iterations="${2:-100}"

    if [ ! -f "$AILANG_DIR/${util}.x" ]; then
        echo "❌ $util not found"
        exit 1
    fi

    local system_util=""
    for path in /usr/bin /bin; do
        if [ -f "$path/$util" ] && [ ! -L "$path/$util" ]; then
            system_util="$path/$util"
            break
        fi
    done
    [ -z "$system_util" ] && echo "❌ System $util not found" && exit 1

    echo "🏋️  Benchmarking $util ($iterations iterations)..."
    echo ""

    if [ "$util" = "head" ] || [ "$util" = "tail" ]; then
        seq 1 10000 > /tmp/ailang_bench_test.txt
    else
        echo "test data for benchmarking" > /tmp/ailang_bench_test.txt
        for i in {1..1000}; do echo "line $i with content" >> /tmp/ailang_bench_test.txt; done
    fi

    local AI="$AILANG_DIR/${util}.x"
    echo -n "AILANG: "
    case "$util" in
        grep)  time (for i in $(seq 1 $iterations); do "$AI" "content" /tmp/ailang_bench_test.txt >/dev/null 2>&1; done) 2>&1 | grep real ;;
        head|tail|wc|cat) time (for i in $(seq 1 $iterations); do "$AI" /tmp/ailang_bench_test.txt >/dev/null 2>&1; done) 2>&1 | grep real ;;
        seq)   time (for i in $(seq 1 $iterations); do "$AI" 1 100 >/dev/null 2>&1; done) 2>&1 | grep real ;;
        yes)   time (for i in $(seq 1 $iterations); do "$AI" | head -100 >/dev/null 2>&1; done) 2>&1 | grep real ;;
        *)     time (for i in $(seq 1 $iterations); do "$AI" "test" >/dev/null 2>&1; done) 2>&1 | grep real ;;
    esac

    echo -n "System: "
    case "$util" in
        grep)  time (for i in $(seq 1 $iterations); do "$system_util" -F "content" /tmp/ailang_bench_test.txt >/dev/null 2>&1; done) 2>&1 | grep real ;;
        seq)   time (for i in $(seq 1 $iterations); do "$system_util" 1 100 >/dev/null 2>&1; done) 2>&1 | grep real ;;
        yes)   time (for i in $(seq 1 $iterations); do "$system_util" | head -100 >/dev/null 2>&1; done) 2>&1 | grep real ;;
        head|tail|wc|cat) time (for i in $(seq 1 $iterations); do "$system_util" /tmp/ailang_bench_test.txt >/dev/null 2>&1; done) 2>&1 | grep real ;;
        *)     time (for i in $(seq 1 $iterations); do "$system_util" "test" >/dev/null 2>&1; done) 2>&1 | grep real ;;
    esac

    rm -f /tmp/ailang_bench_test.txt
}

test_util() {
    local util="$1"
    [ -z "$util" ] && echo "Usage: ailang-utils test <util>" && exit 1
    if [ -f "$AILANG_DIR/${util}.x" ]; then
        local AI="$AILANG_DIR/${util}.x"
        case "$util" in
            grep)       echo "hello world" | "$AI" "world" ;;
            head|tail)  seq 1 20 | "$AI" -n 5 ;;
            seq)        "$AI" 1 5 ;;
            *)          "$AI" "test" ;;
        esac
    else
        echo "❌ $util not found"
        exit 1
    fi
}

case "$1" in
    status)    show_status ;;
    list)      list_utils ;;
    enable)    [ -z "$2" ] && { echo "Usage: ailang-utils enable <util|all>"; exit 1; } ; enable_util "$2" ;;
    disable)   [ -z "$2" ] && { echo "Usage: ailang-utils disable <util|all>"; exit 1; } ; disable_util "$2" ;;
    benchmark) [ -z "$2" ] && { echo "Usage: ailang-utils benchmark <util> [iters]"; exit 1; } ; benchmark_util "$2" "$3" ;;
    test)      test_util "$2" ;;
    *)
        echo "AILANG Utils Manager"
        echo "===================="
        echo ""
        echo "Commands:"
        echo "  list                - Show all utilities"
        echo "  status              - Show which utilities are active"
        echo "  enable <util|all>   - Enable AILANG version"
        echo "  disable <util|all>  - Disable AILANG version"
        echo "  benchmark <util> [N]- Compare performance"
        echo "  test <util>         - Quick test"
        echo ""
        echo "Available utilities: $(get_utils)"
        ;;
esac
MANAGER_SCRIPT

chmod +x "$BIN_DIR/ailang-utils"
echo -e "${GREEN}✅ ailang-utils manager refreshed${NC}"

echo ""
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}⚠️  Add to your shell rc:${NC}"
    echo -e "    ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
else
    echo -e "${GREEN}✅ PATH already configured${NC}"
fi

echo ""
echo -e "${BLUE}📊 Installed:${NC}"
ailang-utils list | head -n 20
echo ""
echo -e "${GREEN}✅ Done.${NC}"
