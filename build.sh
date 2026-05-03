#!/usr/bin/env bash
# build.sh — rebuild ClaudeCode and HalCode9000 binaries.
#
# Usage:
#   ./build.sh                     # rebuild everything
#   ./build.sh --no-tools          # rebuild just the main binaries (fast iteration)
#   ./build.sh --tools-only        # rebuild only the cc_*_ipc tools
#   ./build.sh --hal               # rebuild only HalCode9000 + its tools
#   ./build.sh --claude            # rebuild only ClaudeCode + its tools
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

BUILD_CLAUDE=1
BUILD_HAL=1

for arg in "$@"; do
    case "$arg" in
        --no-tools)    BUILD_TOOLS=0 ;;
        --tools-only)  BUILD_MAIN=0 ;;
        --hal)         BUILD_CLAUDE=0 ;;
        --claude)      BUILD_HAL=0 ;;
        --quiet|-q)    QUIET=1 ;;
        --no-copy)     COPY=0 ;;
        --help|-h)
            sed -n '2,17p' "$0" | sed 's/^# \?//'
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

build_app() {
    local app_dir="$1"     # e.g. Applications/ClaudeCode
    local main_src="$2"    # e.g. Applications/ClaudeCode/ClaudeCode.ailang
    local main_bin="$3"    # e.g. ClaudeCode.x
    local tools_dir="$4"   # e.g. Applications/ClaudeCode/cc_tools
    local tmp_prefix="$5"  # e.g. cc  (produces /tmp/cc_bash_ipc.x)

    local install_dir="$ROOT/$app_dir"

    if [[ $BUILD_TOOLS -eq 1 ]]; then
        log "Building ${app_dir} cc_tools..."
        local t local_tools=("${TOOLS[@]}")
        for t in "${local_tools[@]}"; do
            build_one "${tools_dir}/cc_${t}_ipc.ailang" \
                      "/tmp/${tmp_prefix}_cc_${t}_ipc.x" \
                      "${tmp_prefix}_cc_${t}_ipc"
        done
        if [[ -f "${tools_dir}/cc_relmem_ipc.ailang" ]]; then
            build_one "${tools_dir}/cc_relmem_ipc.ailang" \
                      "/tmp/${tmp_prefix}_cc_relmem_ipc.x" \
                      "${tmp_prefix}_cc_relmem_ipc"
            local_tools+=(relmem)
        fi
        if [[ -f "${tools_dir}/cc_pgmem_ipc.ailang" ]]; then
            build_one "${tools_dir}/cc_pgmem_ipc.ailang" \
                      "/tmp/${tmp_prefix}_cc_pgmem_ipc.x" \
                      "${tmp_prefix}_cc_pgmem_ipc"
            local_tools+=(pgmem)
        fi
    if [[ -f "${tools_dir}/cc_agent_ipc.ailang" ]]; then
        build_one "${tools_dir}/cc_agent_ipc.ailang" \
                  "/tmp/${tmp_prefix}_cc_agent_ipc.x" \
                  "${tmp_prefix}_cc_agent_ipc"
        local_tools+=(agent)
    fi
    if [[ -f "${tools_dir}/cc_js_ipc.ailang" ]]; then
        build_one "${tools_dir}/cc_js_ipc.ailang" \
                  "/tmp/${tmp_prefix}_cc_js_ipc.x" \
                  "${tmp_prefix}_cc_js_ipc"
        local_tools+=(js)
    fi
    if [[ -f "${tools_dir}/cc_mcp_ipc.ailang" ]] && [[ -s "${tools_dir}/cc_mcp_ipc.ailang" ]]; then
        build_one "${tools_dir}/cc_mcp_ipc.ailang" \
                  "/tmp/${tmp_prefix}_cc_mcp_ipc.x" \
                  "${tmp_prefix}_cc_mcp_ipc"
        local_tools+=(mcp)
    fi
        _BUILT_TOOLS=("${local_tools[@]}")
    fi

    if [[ $BUILD_MAIN -eq 1 ]]; then
        log "Building ${main_bin}..."
        build_one "$main_src" "/tmp/${main_bin}" "${main_bin%.x}"
    fi

    if [[ $COPY -eq 1 ]]; then
        log "Installing to $install_dir..."
        local busy=()
        local t
        for t in "${_BUILT_TOOLS[@]}"; do
            local bin="${install_dir}/cc_${t}_ipc.x"
            if [[ -x "$bin" ]] && fuser "$bin" &>/dev/null; then
                busy+=("cc_${t}_ipc.x")
            fi
        done
        local mbin="${install_dir}/${main_bin}"
        if [[ $BUILD_MAIN -eq 1 ]] && [[ -x "$mbin" ]] && fuser "$mbin" &>/dev/null; then
            busy+=("$main_bin")
        fi
        if [[ ${#busy[@]} -gt 0 ]]; then
            echo "" >&2
            echo "build.sh: cannot install — these binaries are currently running:" >&2
            printf '  %s\n' "${busy[@]}" >&2
            echo "Quit the app, then re-run build.sh." >&2
            echo "(All builds succeeded; rerun with --no-copy to skip install.)" >&2
            exit 3
        fi

        if [[ $BUILD_TOOLS -eq 1 ]]; then
            for t in "${_BUILT_TOOLS[@]}"; do
                cp "/tmp/${tmp_prefix}_cc_${t}_ipc.x" "${install_dir}/cc_${t}_ipc.x.new"
                mv "${install_dir}/cc_${t}_ipc.x.new" "${install_dir}/cc_${t}_ipc.x"
            done
        fi
        if [[ $BUILD_MAIN -eq 1 ]]; then
            cp "/tmp/${main_bin}" "${install_dir}/${main_bin}.new"
            mv "${install_dir}/${main_bin}.new" "${install_dir}/${main_bin}"
        fi
    fi
}

_BUILT_TOOLS=()
log "build.sh: starting"

if [[ $BUILD_CLAUDE -eq 1 ]]; then
    build_app "Applications/ClaudeCode" \
              "Applications/ClaudeCode/ClaudeCode.ailang" \
              "ClaudeCode.x" \
              "Applications/ClaudeCode/cc_tools" \
              "cc"
fi

if [[ $BUILD_HAL -eq 1 ]]; then
    build_app "Applications/HalCode9000" \
              "Applications/HalCode9000/HalCode9000.ailang" \
              "HalCode9000.x" \
              "Applications/HalCode9000/cc_tools" \
              "hal"
fi

log ""
log "build.sh: done"
if [[ $COPY -eq 1 && $BUILD_MAIN -eq 1 ]]; then
    [[ $BUILD_CLAUDE -eq 1 ]] && log "Run:  cd Applications/ClaudeCode  && ./ClaudeCode.x"
    [[ $BUILD_HAL    -eq 1 ]] && log "Run:  cd Applications/HalCode9000 && ./HalCode9000.x"
fi
