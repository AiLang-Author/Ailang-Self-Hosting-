#!/usr/bin/env bash
# The old launcher is the sample player. The synthesizer is ./scripts/run_synth.sh.
exec "$(cd "$(dirname "$0")" && pwd)/run_player.sh" "$@"
