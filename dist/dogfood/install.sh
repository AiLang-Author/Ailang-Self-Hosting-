#!/usr/bin/env bash
# install_dogfood.sh — full setup for AILang CAD design-feedback dogfood
#
# What it does:
#   1) Detects distro and installs system packages (X11, build tools, python3, git)
#   2) Clones the monorepo if needed (or uses current tree / Telegram kit)
#   3) Builds X11 host + panel (and optional FLTK shell)
#   4) Optionally installs ailang.x symlink (full monorepo only)
#   5) Optionally launches the CAD app
#
# Usage:
#   ./install_dogfood.sh                 # deps + build hosts (in repo or kit)
#   ./install_dogfood.sh --full          # deps + clone if needed + rebuild cad_app + hosts
#   ./install_dogfood.sh --fltk          # also build local FLTK + shell
#   ./install_dogfood.sh --run           # launch CAD when done
#   ./install_dogfood.sh --deps-only     # only apt/dnf/pacman packages
#   ./install_dogfood.sh --no-sudo       # skip package manager (assume deps present)
#   curl -fsSL .../install_dogfood.sh | bash -s -- --full --run
#
# GitHub: https://github.com/AiLang-Author/Ailang-Self-Hosting-
#
set -euo pipefail

REPO_URL="${AILANG_REPO_URL:-https://github.com/AiLang-Author/Ailang-Self-Hosting-.git}"
REPO_BRANCH="${AILANG_REPO_BRANCH:-master}"
INSTALL_DIR="${AILANG_INSTALL_DIR:-$HOME/Ailang-Self-Hosting-}"
WANT_FULL=0
WANT_FLTK=0
WANT_RUN=0
DEPS_ONLY=0
NO_SUDO=0
INSTALL_COMPILER=0

log()  { printf '\n==> %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  sed -n '2,25p' "$0" | sed 's/^# \?//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) WANT_FULL=1; shift ;;
    --fltk) WANT_FLTK=1; shift ;;
    --run) WANT_RUN=1; shift ;;
    --deps-only) DEPS_ONLY=1; shift ;;
    --no-sudo) NO_SUDO=1; shift ;;
    --install-compiler) INSTALL_COMPILER=1; shift ;;
    --dir) INSTALL_DIR="${2:-}"; shift 2 ;;
    --branch) REPO_BRANCH="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done

# ---------- locate context: dogfood kit vs monorepo vs empty ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"
is_dogfood_kit() {
  [[ -x "$1/bin/cad_app.x" && -x "$1/bin/cad_host_x11" && -f "$1/scripts/run_dogfood.sh" ]]
}
is_monorepo() {
  [[ -f "$1/CAD/cad_app.ailang" && -f "$1/CAD/scripts/run_cad_app.sh" ]]
}

ROOT=""
MODE=""  # kit | monorepo | clone
if is_dogfood_kit "$SCRIPT_DIR"; then
  ROOT="$SCRIPT_DIR"; MODE=kit
elif is_monorepo "$SCRIPT_DIR"; then
  ROOT="$SCRIPT_DIR"; MODE=monorepo
elif is_monorepo "$PWD"; then
  ROOT="$PWD"; MODE=monorepo
elif is_dogfood_kit "$PWD"; then
  ROOT="$PWD"; MODE=kit
else
  MODE=clone
  ROOT="$INSTALL_DIR"
fi

log "AILang CAD dogfood installer"
info "mode=$MODE  root=$ROOT"
info "repo=$REPO_URL  branch=$REPO_BRANCH"

# ---------- package install ----------
need_sudo_cmd() {
  if [[ $EUID -eq 0 ]]; then
    "$@"
  elif have sudo; then
    sudo "$@"
  else
    die "need root or sudo to install packages (or re-run with --no-sudo if already installed)"
  fi
}

install_packages() {
  if [[ "$NO_SUDO" -eq 1 ]]; then
    log "Skipping package install (--no-sudo)"
    return 0
  fi

  local pkgs_common=()
  # Runtime for X11 presenters + tools
  # Build for hosts; optional rebuild of cad_app needs nothing extra (static ailang.x)
  if have apt-get; then
    log "Installing packages (Debian/Ubuntu/Pop)"
    need_sudo_cmd apt-get update -y
    need_sudo_cmd apt-get install -y --no-install-recommends \
      build-essential \
      gcc g++ make \
      libx11-dev \
      x11-utils \
      x11-xserver-utils \
      python3 \
      git curl ca-certificates \
      zip unzip \
      pkg-config
    # optional: system FLTK if user asked --fltk and we prefer system
    if [[ "$WANT_FLTK" -eq 1 ]]; then
      need_sudo_cmd apt-get install -y --no-install-recommends libfltk1.3-dev || true
    fi
  elif have dnf; then
    log "Installing packages (Fedora/RHEL)"
    need_sudo_cmd dnf install -y \
      gcc gcc-c++ make \
      libX11-devel \
      xorg-x11-utils \
      python3 \
      git curl ca-certificates \
      zip unzip \
      pkgconf-pkg-config
    if [[ "$WANT_FLTK" -eq 1 ]]; then
      need_sudo_cmd dnf install -y fltk-devel || true
    fi
  elif have pacman; then
    log "Installing packages (Arch)"
    need_sudo_cmd pacman -Sy --noconfirm --needed \
      base-devel \
      libx11 \
      xorg-xdpyinfo \
      python \
      git curl ca-certificates \
      zip unzip \
      pkgconf
    if [[ "$WANT_FLTK" -eq 1 ]]; then
      need_sudo_cmd pacman -Sy --noconfirm --needed fltk || true
    fi
  else
    info "No apt/dnf/pacman found — install manually:"
    info "  build-essential / gcc / g++ / make"
    info "  libX11 development headers"
    info "  python3, git, curl, zip"
  fi
}

check_runtime() {
  log "Checking runtime"
  local ok=1
  if ! have python3; then info "missing: python3"; ok=0; fi
  if ! have cc && ! have gcc; then
    if [[ "$MODE" == "kit" && "$WANT_FULL" -eq 0 ]]; then
      info "gcc not required for prebuilt kit (hosts already built)"
    else
      info "missing: gcc/cc (needed to build hosts)"
      ok=0
    fi
  fi
  if [[ -z "${DISPLAY:-}" ]]; then
    if [[ -S /tmp/.X11-unix/X0 ]]; then
      export DISPLAY=:0
      info "DISPLAY unset → using :0"
    elif [[ -S /tmp/.X11-unix/X1 ]]; then
      export DISPLAY=:1
      info "DISPLAY unset → using :1"
    else
      info "WARNING: no DISPLAY and no X11 socket — GUI will not start until you log into a desktop (or XWayland)."
    fi
  fi
  if [[ -n "${DISPLAY:-}" ]] && have xdpyinfo; then
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
      info "X display OK: $DISPLAY"
    else
      info "WARNING: cannot talk to X display $DISPLAY"
    fi
  fi
  # libX11 presence
  if have ldconfig; then
    if ldconfig -p 2>/dev/null | grep -q 'libX11.so'; then
      info "libX11 found"
    else
      info "WARNING: libX11.so not found in ldconfig — hosts may fail to start"
      ok=0
    fi
  fi
  return 0
}

# ---------- clone monorepo if needed ----------
ensure_repo() {
  if [[ "$MODE" == "kit" && "$WANT_FULL" -eq 0 ]]; then
    info "Using Telegram dogfood kit at $ROOT"
    return 0
  fi
  if [[ "$MODE" == "monorepo" ]]; then
    info "Using monorepo at $ROOT"
    return 0
  fi
  # clone
  if [[ -d "$ROOT/.git" ]] && is_monorepo "$ROOT"; then
    log "Updating existing clone $ROOT"
    git -C "$ROOT" fetch origin "$REPO_BRANCH" || true
    git -C "$ROOT" checkout "$REPO_BRANCH" || true
    git -C "$ROOT" pull --ff-only origin "$REPO_BRANCH" || true
    MODE=monorepo
    return 0
  fi
  if [[ -d "$ROOT" ]] && [[ -n "$(ls -A "$ROOT" 2>/dev/null || true)" ]]; then
    if is_monorepo "$ROOT"; then
      MODE=monorepo
      return 0
    fi
    die "directory exists and is not an AILang monorepo: $ROOT (set --dir)"
  fi
  have git || die "git is required to clone the repo"
  log "Cloning $REPO_URL → $ROOT"
  mkdir -p "$(dirname "$ROOT")"
  git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" "$ROOT"
  MODE=monorepo
}

# ---------- build FLTK local (optional) ----------
build_fltk_local() {
  local prefix="$ROOT/third_party/fltk"
  if [[ -x "$prefix/bin/fltk-config" ]]; then
    info "FLTK already at $prefix"
    return 0
  fi
  # system fltk-config?
  if have fltk-config; then
    info "Using system fltk-config"
    return 0
  fi
  log "Building FLTK 1.3.9 into third_party/fltk (no root)"
  have curl || die "curl required to fetch FLTK"
  local src="/tmp/fltk-1.3.9-ailang-$$"
  mkdir -p "$src"
  (
    cd "$src"
    curl -fsSL -o fltk.tbz https://www.fltk.org/pub/fltk/1.3.9/fltk-1.3.9-source.tar.bz2
    tar xf fltk.tbz
    cd fltk-1.3.9
    ./configure --prefix="$prefix" \
      --disable-gl --disable-xft --disable-xdbe \
      --enable-shared=no --enable-threads
    make -j"$(nproc 2>/dev/null || echo 2)"
    make install
  )
  info "FLTK installed → $prefix"
}

# ---------- build presenters / app ----------
build_hosts() {
  if [[ "$MODE" == "kit" ]]; then
    log "Dogfood kit: verifying prebuilt binaries"
    [[ -x "$ROOT/bin/cad_app.x" ]] || die "missing bin/cad_app.x"
    [[ -x "$ROOT/bin/cad_host_x11" ]] || die "missing bin/cad_host_x11"
    [[ -x "$ROOT/bin/cad_panel_x11" ]] || die "missing bin/cad_panel_x11"
    chmod +x "$ROOT/bin/"* "$ROOT/scripts/"*.sh 2>/dev/null || true
    return 0
  fi

  log "Building X11 host + tools panel"
  cc -O2 -o "$ROOT/CAD/host/cad_host_x11" "$ROOT/CAD/host/cad_host_x11.c" -lX11 -lm
  cc -O2 -o "$ROOT/CAD/host/cad_panel_x11" "$ROOT/CAD/host/cad_panel_x11.c" -lX11
  chmod +x "$ROOT/CAD/scripts/"*.sh 2>/dev/null || true

  if [[ "$WANT_FLTK" -eq 1 ]]; then
    build_fltk_local
    local fltk_cfg=""
    if [[ -x "$ROOT/third_party/fltk/bin/fltk-config" ]]; then
      fltk_cfg="$ROOT/third_party/fltk/bin/fltk-config"
    elif have fltk-config; then
      fltk_cfg="$(command -v fltk-config)"
    fi
    if [[ -n "$fltk_cfg" ]]; then
      log "Building FLTK shell"
      # shellcheck disable=SC2046
      g++ -O2 -o "$ROOT/CAD/host/cad_shell_fltk" "$ROOT/CAD/host/cad_shell_fltk.cxx" \
        $($fltk_cfg --cxxflags) $($fltk_cfg --ldflags --use-images)
    else
      info "FLTK not available — X11 host+panel only"
    fi
  fi

  if [[ "$WANT_FULL" -eq 1 ]]; then
    if [[ ! -x "$ROOT/ailang.x" ]]; then
      die "ailang.x missing in repo root — pull latest master or obtain a compiler binary"
    fi
    log "Rebuilding cad_app.x from CAD/cad_app.ailang"
    ( cd "$ROOT" && ./ailang.x CAD/cad_app.ailang -o /tmp/cad_app_install.x )
    cp -f /tmp/cad_app_install.x "$ROOT/cad_app.x"
    chmod +x "$ROOT/cad_app.x"
  elif [[ ! -x "$ROOT/cad_app.x" ]]; then
    if [[ -x "$ROOT/ailang.x" ]]; then
      log "cad_app.x missing — building once"
      ( cd "$ROOT" && ./ailang.x CAD/cad_app.ailang -o /tmp/cad_app_install.x )
      cp -f /tmp/cad_app_install.x "$ROOT/cad_app.x"
      chmod +x "$ROOT/cad_app.x"
    else
      die "cad_app.x and ailang.x both missing — re-clone or use the Telegram dogfood zip"
    fi
  fi
}

install_compiler_links() {
  [[ "$INSTALL_COMPILER" -eq 1 ]] || return 0
  [[ "$MODE" == "monorepo" ]] || { info "compiler install only for monorepo"; return 0; }
  [[ -x "$ROOT/ailang.x" ]] || die "ailang.x not found"
  log "Installing ailang.x symlink to /usr/local/bin (needs sudo)"
  need_sudo_cmd mkdir -p /usr/local/bin
  need_sudo_cmd ln -sf "$ROOT/ailang.x" /usr/local/bin/ailang.x
  if [[ -x "$ROOT/analyzer.x" ]]; then
    need_sudo_cmd ln -sf "$ROOT/analyzer.x" /usr/local/bin/analyzer.x
  fi
  info "ailang.x → $ROOT/ailang.x"
}

launch_cad() {
  [[ "$WANT_RUN" -eq 1 ]] || return 0
  log "Launching CAD"
  if [[ "$MODE" == "kit" ]]; then
    exec "$ROOT/scripts/run_dogfood.sh"
  else
    exec "$ROOT/CAD/scripts/run_cad_app.sh" -H 15
  fi
}

# ---------- main ----------
install_packages
[[ "$DEPS_ONLY" -eq 1 ]] && { log "Deps only — done."; exit 0; }

ensure_repo
cd "$ROOT"
check_runtime
build_hosts
install_compiler_links

log "Install complete"
info "Root:  $ROOT"
info "Mode:  $MODE"
if [[ "$MODE" == "kit" ]]; then
  info "Run:   $ROOT/scripts/run_dogfood.sh"
else
  info "Run:   $ROOT/CAD/scripts/run_cad_app.sh"
  info "Agent: $ROOT/CAD/scripts/cad_cmd.sh tool_line --wait"
  info "Shot:  $ROOT/CAD/scripts/cad_shot.sh /tmp/view.png"
fi
info "GitHub: $REPO_URL"
info "Feedback: design notes welcome (pad height, mirror, live angle, 3D sketch UX)"

if [[ "$WANT_RUN" -eq 1 ]]; then
  launch_cad
fi
