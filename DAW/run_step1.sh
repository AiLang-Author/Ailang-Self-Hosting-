#!/usr/bin/env bash
# Two instruments, one mixer. SynthKit sources are not modified.
# The kernel binary is the working reference until the DAW needs its own.
#
#   ./DAW/run_step1.sh
#
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DAW="$REPO/DAW"
KERNEL="$REPO/Applications/SynthKit/synth_app.x"
SESSION="$DAW/Sessions/step1.json"
EVENTS="$DAW/Sessions/step1.events"
GRAPH="$DAW/Sessions/step1.graph"
ROOT_STATE=/dev/shm/daw

if [[ ! -x "$KERNEL" ]]; then
  echo "missing $KERNEL — build SynthKit first" >&2
  exit 1
fi

python3 "$DAW/tools/midi_fan.py" "$SESSION" "$EVENTS"

# Mix gain 80 is the level the standalone sample player and synth use.
# Gain 256 pins a hot sample in the 16-bit ring before the mixer can
# turn it down, which is what buried the drums. The mixer still applies
# the track fader and the session master, then clamps the bus once.
CTL_SAMPLE='0 256 0 0 0 0 80 4 200 200 2 128 0 0 0 0 0 0 0 0 2 256 0 0 0 0 0 0 0 0 0'
CTL_SYNTH='0 256 0 0 0 0 80 4 200 200 2 128 0 0 0 0 0 0 0 0 2 256 0 0 0 0 0 0 0 0 0'
LIST="$(python3 -c '
import json, sys
s = json.load(open(sys.argv[1]))
print(s["master"])
for t in s["tracks"]:
    extra = t.get("preset") or t.get("pack") or ""
    inst = t.get("inst") or ""
    print("%s\t%s\t%s\t%s\t%s" % (t["id"], t["kind"], t["fader"], extra, inst))
' "$SESSION")"
master="${LIST%%$'\n'*}"
tracks=()
while IFS= read -r line; do
  tracks+=("$line")
done < <(printf '%s\n' "$LIST" | tail -n +2)

start_one() {
  local id="$1" kind="$2" extra="$3" inst="$4"
  local dir="$ROOT_STATE/$id"
  mkdir -p "$dir"
  printf '00000000\n' > "$dir/keys.txt"
  if [[ "$kind" == "sample" ]]; then
    printf '%s\n' "$CTL_SAMPLE" > "$dir/ctl.txt"
  else
    printf '%s\n' "$CTL_SYNTH" > "$dir/ctl.txt"
  fi
  : > "$dir/cmd.txt"
  : > "$dir/song.txt"
  : > "$dir/song_cmd.txt"
  : > "$dir/bank.txt"
  if [[ "$kind" == "sample" ]]; then
    printf '%s\n' "$extra" > "$dir/pack.txt"
    printf '%s\n' "$inst" > "$dir/inst.txt"
    : > "$dir/surge.txt"
  else
    : > "$dir/pack.txt"
    : > "$dir/inst.txt"
    # Same path the SynthKit synth already loads. The kernel reads the .fxp.
    printf '%s\n' "$extra" > "$dir/surge.txt"
  fi
  "$KERNEL" "$dir" > "$DAW/Sessions/$id.log" 2>&1 &
  echo $! > "$DAW/Sessions/$id.pid"
  echo "started $kind $id pid $(cat "$DAW/Sessions/$id.pid")"
}

ids=()
cleanup() {
  if [[ -n "${MIX:-}" ]]; then kill "$MIX" 2>/dev/null || true; fi
  for id in "${ids[@]}"; do
    if [[ -f "$DAW/Sessions/$id.pid" ]]; then
      kill "$(cat "$DAW/Sessions/$id.pid")" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

pkill -f "synth_app.x $ROOT_STATE" 2>/dev/null || true
sleep 0.2
rm -rf "$ROOT_STATE"
for row in "${tracks[@]}"; do
  IFS=$'\t' read -r id kind fader extra inst <<<"$row"
  ids+=("$id")
  start_one "$id" "$kind" "$extra" "$inst"
done

# Rings exist before a preset or pack is ready. Starting the mixer earlier
# drops the opening notes.
ready=0
for _i in $(seq 1 150); do
  ready=1
  for row in "${tracks[@]}"; do
    IFS=$'\t' read -r id kind fader extra inst <<<"$row"
    if [[ ! -f "$ROOT_STATE/$id/pcm.bin" || ! -f "$ROOT_STATE/$id/midi.bin" ]]; then
      ready=0
    elif [[ "$kind" == "sample" ]] && ! grep -q "sample instrument" "$DAW/Sessions/$id.log"; then
      ready=0
    elif [[ "$kind" == "synth" ]] && ! grep -q "surge ailang" "$DAW/Sessions/$id.log"; then
      ready=0
    fi
  done
  if [[ "$ready" == 1 ]]; then
    break
  fi
  sleep 0.2
done
if [[ "$ready" != 1 ]]; then
  echo "kernels did not become ready" >&2
  for id in "${ids[@]}"; do
    echo "--- $id ---" >&2
    tail -30 "$DAW/Sessions/$id.log" >&2 || true
  done
  exit 1
fi

{
  echo "master $master"
  echo "events $EVENTS"
  for row in "${tracks[@]}"; do
    IFS=$'\t' read -r id kind fader extra inst <<<"$row"
    echo "track $ROOT_STATE/$id/pcm.bin $ROOT_STATE/$id/midi.bin $fader"
  done
  mkdir -p "$ROOT_STATE/wplay"
  dd if=/dev/zero of="$ROOT_STATE/wplay/pcm.bin" bs=32832 count=1 status=none
  dd if=/dev/zero of="$ROOT_STATE/wplay/midi.bin" bs=4128 count=1 status=none
  echo "track $ROOT_STATE/wplay/pcm.bin $ROOT_STATE/wplay/midi.bin 256"
} > "$GRAPH"

if [[ ! -x "$DAW/Mixer/daw_mix.x" || "$DAW/Mixer/daw_mix.ailang" -nt "$DAW/Mixer/daw_mix.x" ]]; then
  "$REPO/ailang.x" "$DAW/Mixer/daw_mix.ailang" "$DAW/Mixer/daw_mix.x"
fi
"$DAW/Mixer/daw_mix.x" "$GRAPH" &
MIX=$!
echo "mixer pid $MIX"
wait "$MIX"
