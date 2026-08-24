#!/bin/bash
# deploy.sh — Compile and push AILang OS binaries to target over SSH
#
# Usage:
#   ./deploy.sh                            # deploy all to 192.168.1.25
#   ./deploy.sh 192.168.1.25 terminal      # just terminal.x
#   ./deploy.sh 10.0.0.2 init              # compile + push init (reboot needed)
#   ./deploy.sh 192.168.1.25 calc notepad  # multiple components

set -e
cd "$(dirname "$0")"

TARGET="${1:-192.168.1.25}"
shift 2>/dev/null || true
COMPONENTS=("${@:-all}")

SSH="ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$TARGET"
SCP="scp -o ConnectTimeout=5 -o StrictHostKeyChecking=no"

# component → source file, output binary, target path
declare -A SRC BIN DEST
SRC[init]="OS/Init.ailang";           BIN[init]="ailang_init";       DEST[init]="/sbin/ailang_init"
SRC[installer]="OS/Installer.ailang"; BIN[installer]="installer.x";  DEST[installer]="/system/bin/installer.x"
SRC[terminal]="Applications/terminal_ipc.ailang";   BIN[terminal]="terminal.x";    DEST[terminal]="/system/bin/terminal.x"
SRC[notepad]="Applications/notepad_ipc.ailang";     BIN[notepad]="notepad.x";      DEST[notepad]="/system/bin/notepad.x"
SRC[calc]="Applications/calc_ipc.ailang";           BIN[calc]="calc.x";            DEST[calc]="/system/bin/calc.x"
SRC[grep]="Applications/grep_ipc.ailang";           BIN[grep]="grep.x";            DEST[grep]="/system/bin/grep.x"
SRC[wifi]="Applications/wifi_ipc.ailang";           BIN[wifi]="wifi_ipc.x";        DEST[wifi]="/system/bin/wifi_ipc.x"
SRC[browser]="Applications/browser_ipc.ailang";     BIN[browser]="browser.x";      DEST[browser]="/system/bin/browser.x"
SRC[chrome]="Applications/chrome_ipc.ailang";       BIN[chrome]="chrome.x";        DEST[chrome]="/system/bin/chrome.x"
SRC[ladybird]="Applications/ladybird_ipc.ailang";   BIN[ladybird]="ladybird.x";    DEST[ladybird]="/system/bin/ladybird.x"
SRC[claude]="Applications/claude_ipc.ailang";       BIN[claude]="claude.x";        DEST[claude]="/system/bin/claude.x"
SRC[vscode]="Applications/vscode_ipc.ailang";       BIN[vscode]="vscode.x";        DEST[vscode]="/system/bin/vscode.x"
SRC[ide]="Applications/ide_ipc.ailang";             BIN[ide]="ide.x";              DEST[ide]="/system/bin/ide.x"
SRC[pkg]="Applications/installer_ipc.ailang";       BIN[pkg]="installer_ipc.x";    DEST[pkg]="/system/bin/installer_ipc.x"
SRC[display]="Main.ailang"; BIN[display]="display.x"; DEST[display]="/system/bin/display.x"
SRC[deskbar]="Applications/deskbar_ipc.ailang"; BIN[deskbar]="deskbar.x"; DEST[deskbar]="/system/bin/deskbar.x"
SRC[videoplayer]="Applications/videoplayer.ailang"; BIN[videoplayer]="videoplayer.x"; DEST[videoplayer]="/system/bin/videoplayer.x"
SRC[mediacenter]="MediaCenter/MediaCenter.ailang";  BIN[mediacenter]="MediaCenter.x"; DEST[mediacenter]="/system/bin/MediaCenter.x"

NEEDS_REBOOT=(init display)

OVERLAY="/home/bob/buildroot/board/ailang_os/rootfs_overlay"
OVERLAY_BIN="$OVERLAY/system/bin"
OVERLAY_SBIN="$OVERLAY/sbin"

# Codec workers — built with gcc, not ailang compiler
CODEC_WORKERS=(mp3_worker aac_worker opus_worker flac_worker vorbis_worker pcm_worker h264_worker h265_worker vp9_worker av1_worker demux_worker)

build_and_push() {
    local comp="$1"
    local src="${SRC[$comp]}"
    local bin="${BIN[$comp]}"
    local dest="${DEST[$comp]}"

    if [ -z "$src" ]; then
        echo "  SKIP  unknown component: $comp"
        return 1
    fi

    echo "  BUILD $src -> $bin"
    ./ailang.x "$src" -o "/tmp/$bin" 2>&1 | tail -1
    if [ $? -ne 0 ]; then
        echo "  FAIL  compile failed: $comp"
        return 1
    fi

    echo "  PUSH  $bin -> $TARGET:$dest"
    $SCP "/tmp/$bin" "root@$TARGET:$dest"

    # Also copy to rootfs overlay for image builds
    local overlay_dest="$OVERLAY$dest"
    local overlay_dir="$(dirname "$overlay_dest")"
    if [ -d "$OVERLAY" ]; then
        mkdir -p "$overlay_dir"
        cp "/tmp/$bin" "$overlay_dest"
        echo "  COPY  $bin -> overlay:$dest"
    fi

    for rb in "${NEEDS_REBOOT[@]}"; do
        if [ "$comp" = "$rb" ]; then
            echo "  NOTE  $comp requires reboot to take effect"
        fi
    done
    echo "  OK    $comp"
}

build_codec_workers() {
    echo "  BUILD codec workers (gcc)"
    pushd MediaCenter/Codec >/dev/null
    make clean 2>/dev/null; make 2>&1
    if [ $? -ne 0 ]; then
        echo "  FAIL  codec worker compilation failed"
        popd >/dev/null
        return 1
    fi
    for w in "${CODEC_WORKERS[@]}"; do
        if [ ! -f "$w" ]; then
            echo "  SKIP  $w not built"
            continue
        fi
        echo "  PUSH  $w -> $TARGET:/system/bin/$w"
        $SCP "$w" "root@$TARGET:/system/bin/$w"
        # Also copy to rootfs overlay for image builds
        if [ -d "$OVERLAY_BIN" ]; then
            cp "$w" "$OVERLAY_BIN/$w"
        fi
    done
    popd >/dev/null
    echo "  OK    codec workers"
}

# Resolve "all"
if [ "${COMPONENTS[0]}" = "all" ]; then
    COMPONENTS=(init installer display terminal notepad calc grep wifi browser chrome ladybird claude vscode ide pkg videoplayer mediacenter)
fi

echo "Target: $TARGET"
echo "Components: ${COMPONENTS[*]}"
echo ""

FAILED=0
for comp in "${COMPONENTS[@]}"; do
    build_and_push "$comp" || FAILED=$((FAILED + 1))
done

# Build + deploy codec workers when deploying mediacenter or all
for comp in "${COMPONENTS[@]}"; do
    if [ "$comp" = "mediacenter" ] || [ "$comp" = "all" ] || [ "$comp" = "codecs" ]; then
        build_codec_workers || FAILED=$((FAILED + 1))
        break
    fi
done

echo ""
if [ $FAILED -eq 0 ]; then
    echo "Done. All ${#COMPONENTS[@]} components deployed."
else
    echo "Done. $FAILED/${#COMPONENTS[@]} failed."
    exit 1
fi
