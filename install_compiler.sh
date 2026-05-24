#!/usr/bin/env bash
# install_compiler_toolchain.sh
# Installs the AILang compiler and analyzer as symlinks into $INSTALL_DIR.
# Symlinks mean rebuilds (ailang.x, analyzer.x) are live immediately — no
# re-install needed.  Librarys/ stays in the source tree; the compiler finds
# it via /proc/self/exe readlink at startup.
#
# Usage: sudo ./install_compiler_toolchain.sh [install-dir]
#   Default install-dir: /usr/local/bin
#
# To uninstall:
#   sudo rm /usr/local/bin/ailang.x /usr/local/bin/analyzer.x

set -euo pipefail

INSTALL_DIR="${1:-/usr/local/bin}"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

COMPILER="$SOURCE_DIR/ailang.x"
ANALYZER="$SOURCE_DIR/analyzer.x"

if [[ $EUID -ne 0 ]]; then
    echo "Error: must run as root (sudo $0)" >&2
    exit 1
fi

for bin in "$COMPILER" "$ANALYZER"; do
    if [[ ! -x "$bin" ]]; then
        echo "Error: not found or not executable: $bin" >&2
        exit 1
    fi
done

mkdir -p "$INSTALL_DIR"

ln -sf "$COMPILER" "$INSTALL_DIR/ailang.x"
ln -sf "$ANALYZER" "$INSTALL_DIR/analyzer.x"

echo "Installed:"
echo "  $INSTALL_DIR/ailang.x  -> $COMPILER"
echo "  $INSTALL_DIR/analyzer.x -> $ANALYZER"
echo ""
echo "Verify:"
echo "  ailang.x   $(readlink -f "$INSTALL_DIR/ailang.x")  $(stat -c%s "$COMPILER") bytes"
echo "  analyzer.x $(readlink -f "$INSTALL_DIR/analyzer.x") $(stat -c%s "$ANALYZER") bytes"
echo ""
echo "Note: Librarys/ is resolved at runtime via /proc/self/exe — no copy needed."
echo "Rebuilding ailang.x or analyzer.x in $SOURCE_DIR is live immediately."
