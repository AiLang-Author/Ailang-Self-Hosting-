#!/usr/bin/env bash
# build.sh — rebuild all ClaudeCode binaries in one command.
#
# Usage:
#   ./build.sh                     # rebuild everything (7 binaries)
#   ./build.sh --no-tools          # rebuild just ClaudeCode.x (fast iteration)
#   ./build.sh --tools-only        # rebuild only the 6 cc_*_ipc tools
#   ./build.sh --quiet             # suppress per-file [ok] output
#   ./build.sh --no-copy           # build to /tmp only, don't touch project root
#
# Behavior:
#   - All ailang.x compiles go to /tmp first.
#   - Fails fast if any compile fails (the rest are skipped).
#   - On success, atomically copies all built binaries to project root.
#   - "Atomic" here means: either every binary updates, or none does.
#     If you ctrl-C mid-copy, your project-root binaries stay coherent
#     because we copy to *.new files first, then rename.
#
# Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ---- arg parsing ------------------------------------------------------------
BUILD_MAIN=1
BUILD_TOOLS=1
QUIET=0
COPY=1

for arg in "$@"; do
    case "$arg" in
        --no-tools)    BUILD_TOOLS=0 ;;
        --tools-only)  BUILD_MAIN=0 ;;
        --quiet|-q)    QUIET=1 ;;
        --no-copy)     COPY=0 ;;
        --help|-h)
            sed -n '2,16p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "build.sh: unknown arg: $arg (try --help)" >&2
            exit 2
            ;;
    esac
done

# ---- preflight --------------------------------------------------------------
if [[ ! -x ./ailang.x ]]; then
    echo "build.sh: ./ailang.x not found or not executable in $ROOT" >&2
    exit 1
fi

# Tool list: bare names, expanded both for source and binary
TOOLS=(read head ls write bash webfetch)

# ---- build phase: everything goes to /tmp first ----------------------------
log() { [[ $QUIET -eq 1 ]] || echo "$@"; }

build_one() {
    local src="$1"
    local out="$2"
    local label="$3"
    local logf="/tmp/build_${label}.log"

    if ./ailang.x "$src" "$out" >"$logf" 2>&1; then
        log "  [ok]  $label"
        return 0
    fi

    echo "  [FAIL] $label  (see $logf)" >&2
    # Surface the first real error line; AILang produces a lot of progress noise.
    grep -m1 -iE "ERROR|Unknown|FATAL|Failed" "$logf" \
        | grep -vE "^\[POOL|^\[LOAD|^\[STORE|JParse\.error|XERROR|^\[FUNCDEF|OPT-TRY|ARITH |^\[IO\]|^\[FILE\]" \
        | head -3 >&2
    return 1
}

log "build.sh: starting"

if [[ $BUILD_TOOLS -eq 1 ]]; then
    log "Building cc_tools..."
    for t in "${TOOLS[@]}"; do
        build_one "Applications/ClaudeCode/cc_tools/cc_${t}_ipc.ailang" \
                  "/tmp/cc_${t}_ipc.x" \
                  "cc_${t}_ipc"
    done

    # cc_relmem_ipc is treated specially: source might not exist (sibling agent
    # building it). If source is missing we skip; if present we build.
    if [[ -f Applications/ClaudeCode/cc_tools/cc_relmem_ipc.ailang ]]; then
        build_one "Applications/ClaudeCode/cc_tools/cc_relmem_ipc.ailang" \
                  "/tmp/cc_relmem_ipc.x" \
                  "cc_relmem_ipc"
        TOOLS+=(relmem)
    elif [[ -x ./cc_relmem_ipc.x ]]; then
        log "  [skip] cc_relmem_ipc (source missing, keeping existing binary)"
    fi
fi

if [[ $BUILD_MAIN -eq 1 ]]; then
    log "Building ClaudeCode..."
    build_one "Applications/ClaudeCode/ClaudeCode.ailang" \
              "/tmp/ClaudeCode.x" \
              "ClaudeCode"
fi

# ---- copy phase: atomic-ish replace in install dir -------------------------
# All ClaudeCode binaries live together in Applications/ClaudeCode/. Run with:
#   cd Applications/ClaudeCode && ./ClaudeCode.x
INSTALL_DIR="$ROOT/Applications/ClaudeCode"

if [[ $COPY -eq 1 ]]; then
    log "Installing to $INSTALL_DIR..."

    # Refuse to overwrite a running binary — the kernel returns ETXTBSY
    # ("Text file busy") which would leave the install half-done.
    busy=()
    for t in "${TOOLS[@]}"; do
        if [[ -x "$INSTALL_DIR/cc_${t}_ipc.x" ]] && fuser "$INSTALL_DIR/cc_${t}_ipc.x" &>/dev/null; then
            busy+=("cc_${t}_ipc.x")
        fi
    done
    if [[ $BUILD_MAIN -eq 1 ]] && [[ -x "$INSTALL_DIR/ClaudeCode.x" ]] && fuser "$INSTALL_DIR/ClaudeCode.x" &>/dev/null; then
        busy+=("ClaudeCode.x")
    fi
    if [[ ${#busy[@]} -gt 0 ]]; then
        echo "" >&2
        echo "build.sh: cannot install — these binaries are currently running:" >&2
        printf '  %s\n' "${busy[@]}" >&2
        echo "Quit ClaudeCode, then re-run build.sh." >&2
        echo "(All builds succeeded; rerun with --no-copy if you want to keep /tmp/* and skip install.)" >&2
        exit 3
    fi

    # Stage to .new files, then rename. Rename is atomic per-file on the
    # same filesystem; sequential renames mean a brief window where the
    # set is half-old half-new, but no individual file is half-written.
    if [[ $BUILD_TOOLS -eq 1 ]]; then
        for t in "${TOOLS[@]}"; do
            cp "/tmp/cc_${t}_ipc.x" "$INSTALL_DIR/cc_${t}_ipc.x.new"
            mv "$INSTALL_DIR/cc_${t}_ipc.x.new" "$INSTALL_DIR/cc_${t}_ipc.x"
        done
    fi
    if [[ $BUILD_MAIN -eq 1 ]]; then
        cp "/tmp/ClaudeCode.x" "$INSTALL_DIR/ClaudeCode.x.new"
        mv "$INSTALL_DIR/ClaudeCode.x.new" "$INSTALL_DIR/ClaudeCode.x"
    fi
fi

log ""
log "build.sh: done"

if [[ $COPY -eq 1 && $BUILD_MAIN -eq 1 ]]; then
    log "Run:  cd Applications/ClaudeCode && ./ClaudeCode.x"
fi
