#!/usr/bin/env bash
# smoke_ailang_utils.sh  —  correctness harness for the AILANG coreutils
#
# Rewritten 2026-04-18 after head/tail/fold shipped broken: the old harness
# covered only the invocation forms that happened to work, not the GNU-
# idiomatic ones users actually type. This one tests real invocation
# patterns (stdin AND file args, explicit AND shorthand flags, edge cases)
# and compares byte-for-byte against /usr/bin/<util> where POSIX mandates
# agreement.
#
# Usage:
#   ./smoke_ailang_utils.sh            # all green or exit non-zero
#   ./smoke_ailang_utils.sh -v         # verbose (show each check's output)
#   ./smoke_ailang_utils.sh <util>     # only run checks for one utility
#
# No false-positive passes. A test that doesn't exercise a real user
# invocation is worse than no test — it enables bad claims.

set -u

VERBOSE=0
ONLY=""
for arg in "$@"; do
    case "$arg" in
        -v|--verbose) VERBOSE=1 ;;
        -h|--help)
            grep -E '^#( |$)' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) ONLY="$arg" ;;
    esac
done

GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'; DIM=$'\033[2m'; NC=$'\033[0m'

pass=0; fail=0; skip=0
declare -a failures=()

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# ─── Fixtures ───────────────────────────────────────────────────────────────
printf 'one\ntwo\nthree\nfour\nfive\nsix\nseven\neight\nnine\nten\neleven\ntwelve\n' > "$TMP/lines.txt"
printf 'apple\napple\nbanana\nbanana\nbanana\ncherry\n' > "$TMP/dups.txt"
printf 'zebra\napple\nmango\nbanana\ncherry\n' > "$TMP/unsorted.txt"
printf 'alpha\tbeta\tgamma\ndelta\tepsilon\tzeta\n' > "$TMP/tabs.txt"
printf 'hello world how are you doing today friend\n' > "$TMP/long.txt"
printf '' > "$TMP/empty.txt"
printf 'single line no newline' > "$TMP/nonewline.txt"
printf 'Function one\nsubroutine two\nFunction three\n' > "$TMP/grep_test.txt"

# Whether a utility is in scope (respects the ONLY filter).
in_scope() {
    [ -z "$ONLY" ] && return 0
    [ "$1" = "$ONLY" ]
}

# ─── Assertions ─────────────────────────────────────────────────────────────
# All three assertion helpers catch segfault/timeout uniformly.

_record_pass() {
    pass=$((pass+1))
    if [ $VERBOSE -eq 1 ]; then
        printf "  %s✓%s  %s\n" "$GREEN" "$NC" "$1"
    else
        printf "  %s✓%s  %s\n" "$GREEN" "$NC" "$1"
    fi
}
_record_fail() {
    fail=$((fail+1))
    failures+=("$1")
    printf "  %s✗%s  %s\n" "$RED" "$NC" "$1"
    if [ $VERBOSE -eq 1 ] && [ -n "${2:-}" ]; then
        printf "     %sdetail:%s %s\n" "$DIM" "$NC" "$2"
    fi
}
_record_skip() {
    skip=$((skip+1))
    printf "  %s~%s  %s  %s(skipped: %s)%s\n" "$YELLOW" "$NC" "$1" "$DIM" "$2" "$NC"
}

# Compare AiLang util's output against GNU's, byte-for-byte. Same args to both.
# Usage: gnu_match "label" util "arg1" "arg2" ... [< stdin_file]
gnu_match() {
    local label="$1" util="$2"; shift 2
    local gnu_bin=/usr/bin/$util
    if [ ! -x "$gnu_bin" ]; then
        _record_skip "$label" "no $gnu_bin on this system"
        return
    fi
    local ailang_out gnu_out ailang_rc gnu_rc
    # Honor redirected stdin if caller passed one.
    ailang_out=$(timeout 5 "$util" "$@" 2>/dev/null); ailang_rc=$?
    gnu_out=$(timeout 5 "$gnu_bin" "$@" 2>/dev/null); gnu_rc=$?
    if [ $ailang_rc -eq 139 ]; then _record_fail "$label" "SEGFAULT"; return; fi
    if [ $ailang_rc -eq 124 ]; then _record_fail "$label" "TIMEOUT"; return; fi
    if [ "$ailang_out" = "$gnu_out" ]; then
        _record_pass "$label"
    else
        local detail
        detail=$(printf 'AiLang rc=%d GNU rc=%d' "$ailang_rc" "$gnu_rc")
        _record_fail "$label" "$detail"
        if [ $VERBOSE -eq 1 ]; then
            printf "     %sailang:%s %q\n" "$DIM" "$NC" "$ailang_out"
            printf "     %sgnu:   %s %q\n" "$DIM" "$NC" "$gnu_out"
        fi
    fi
}

# Same as gnu_match but pipes `stdin_text` into both sides via stdin.
gnu_match_stdin() {
    local label="$1" util="$2" stdin_text="$3"; shift 3
    local gnu_bin=/usr/bin/$util
    if [ ! -x "$gnu_bin" ]; then
        _record_skip "$label" "no $gnu_bin on this system"
        return
    fi
    local ailang_out gnu_out ailang_rc gnu_rc
    ailang_out=$(printf '%s' "$stdin_text" | timeout 5 "$util" "$@" 2>/dev/null); ailang_rc=$?
    gnu_out=$(printf '%s' "$stdin_text" | timeout 5 "$gnu_bin" "$@" 2>/dev/null); gnu_rc=$?
    if [ $ailang_rc -eq 139 ]; then _record_fail "$label" "SEGFAULT"; return; fi
    if [ $ailang_rc -eq 124 ]; then _record_fail "$label" "TIMEOUT"; return; fi
    if [ "$ailang_out" = "$gnu_out" ]; then
        _record_pass "$label"
    else
        _record_fail "$label" "AiLang rc=$ailang_rc GNU rc=$gnu_rc"
        if [ $VERBOSE -eq 1 ]; then
            printf "     %sailang:%s %q\n" "$DIM" "$NC" "$ailang_out"
            printf "     %sgnu:   %s %q\n" "$DIM" "$NC" "$gnu_out"
        fi
    fi
}

# Assert output matches a literal expected string. For tests where GNU
# isn't the reference (or where we want to pin an exact expected result).
# Usage: literal_match "label" "expected" cmd args...  [or use via stdin helper]
literal_match_stdin() {
    local label="$1" expected="$2" stdin_text="$3"; shift 3
    local actual rc
    actual=$(printf '%s' "$stdin_text" | timeout 5 "$@" 2>/dev/null); rc=$?
    if [ $rc -eq 139 ]; then _record_fail "$label" "SEGFAULT"; return; fi
    if [ $rc -eq 124 ]; then _record_fail "$label" "TIMEOUT"; return; fi
    if [ "$actual" = "$expected" ]; then
        _record_pass "$label"
    else
        _record_fail "$label" "got=$actual want=$expected"
    fi
}

# Runs the command and requires exit 0 + non-empty stdout.
# For utilities where output content is environment-dependent (date, uname, id).
runs_nonempty() {
    local label="$1"; shift
    local out rc
    out=$(timeout 5 "$@" 2>/dev/null); rc=$?
    if [ $rc -eq 139 ]; then _record_fail "$label" "SEGFAULT"; return; fi
    if [ $rc -eq 124 ]; then _record_fail "$label" "TIMEOUT"; return; fi
    if [ $rc -eq 0 ] && [ -n "$out" ]; then
        _record_pass "$label"
    else
        _record_fail "$label" "rc=$rc empty=$([ -z \"$out\" ] && echo y || echo n)"
    fi
}

# Runs the command and requires the given exit code.
exit_code_is() {
    local label="$1" want="$2"; shift 2
    timeout 5 "$@" >/dev/null 2>&1
    local rc=$?
    if [ $rc -eq 139 ]; then _record_fail "$label" "SEGFAULT"; return; fi
    if [ $rc -eq 124 ]; then _record_fail "$label" "TIMEOUT"; return; fi
    if [ "$rc" = "$want" ]; then
        _record_pass "$label"
    else
        _record_fail "$label" "rc=$rc want=$want"
    fi
}

section() {
    printf '\n%s▸ %s%s\n' "$BLUE" "$1" "$NC"
}

# ─── Checks ────────────────────────────────────────────────────────────────

# echo: stdout formatting is POSIX-defined; match GNU exactly.
if in_scope echo; then
    section "echo"
    gnu_match       "echo literal"         echo hello world
    gnu_match       "echo empty"           echo
    gnu_match       "echo -n suppress nl"  echo -n hello
fi

# cat: both stdin and file paths matter.
if in_scope cat; then
    section "cat"
    gnu_match       "cat file"              cat "$TMP/lines.txt"
    gnu_match_stdin "cat stdin"             cat $'a\nb\nc\n'
    gnu_match       "cat empty file"        cat "$TMP/empty.txt"
    gnu_match       "cat no trailing nl"    cat "$TMP/nonewline.txt"
fi

# head: the class of bug that motivated this rewrite.
if in_scope head; then
    section "head  (the one that started this)"
    gnu_match       "head -5 file"          head -5 "$TMP/lines.txt"
    gnu_match       "head -n 5 file"        head -n 5 "$TMP/lines.txt"
    gnu_match       "head default (10)"     head "$TMP/lines.txt"
    gnu_match_stdin "head -3 stdin"         head $'a\nb\nc\nd\ne\n' -3
    gnu_match_stdin "head -n 2 stdin"       head $'a\nb\nc\n' -n 2
    gnu_match       "head empty file"       head "$TMP/empty.txt"
fi

# tail: same bug class.
if in_scope tail; then
    section "tail"
    gnu_match       "tail -3 file"          tail -3 "$TMP/lines.txt"
    gnu_match       "tail -n 3 file"        tail -n 3 "$TMP/lines.txt"
    gnu_match       "tail default (10)"     tail "$TMP/lines.txt"
    gnu_match_stdin "tail -2 stdin"         tail $'a\nb\nc\nd\n' -2
    gnu_match_stdin "tail -n 2 stdin"       tail $'a\nb\nc\n' -n 2
    gnu_match       "tail empty file"       tail "$TMP/empty.txt"
fi

# wc: line/word/char counts.
if in_scope wc; then
    section "wc"
    gnu_match       "wc -l file"            wc -l "$TMP/lines.txt"
    gnu_match       "wc -w file"            wc -w "$TMP/long.txt"
    gnu_match       "wc -c file"            wc -c "$TMP/long.txt"
    gnu_match_stdin "wc -l stdin"           wc $'a\nb\nc\n' -l
    gnu_match       "wc empty"              wc "$TMP/empty.txt"
fi

# grep: core pattern matcher. AiLang impl is custom — correctness matters.
if in_scope grep; then
    section "grep"
    gnu_match       "grep literal file"     grep Function "$TMP/grep_test.txt"
    gnu_match       "grep -c count"         grep -c Function "$TMP/grep_test.txt"
    gnu_match       "grep -v invert"        grep -v Function "$TMP/grep_test.txt"
    gnu_match_stdin "grep stdin"            grep two $'one\ntwo\nthree\n'
    gnu_match       "grep no match"         grep zzz "$TMP/grep_test.txt"
fi

# sort: ordering + flags.
if in_scope sort; then
    section "sort"
    gnu_match       "sort file"             sort "$TMP/unsorted.txt"
    gnu_match       "sort -r reverse"       sort -r "$TMP/unsorted.txt"
    gnu_match_stdin "sort stdin"            sort $'c\na\nb\n'
fi

# uniq: dedupe consecutive.
if in_scope uniq; then
    section "uniq"
    gnu_match       "uniq file"             uniq "$TMP/dups.txt"
    gnu_match       "uniq -c count"         uniq -c "$TMP/dups.txt"
    gnu_match_stdin "uniq stdin"            uniq $'a\na\nb\nb\nc\n'
fi

# cut: field/char selection.
if in_scope cut; then
    section "cut"
    gnu_match       "cut -f1 tab"           cut -f1 "$TMP/tabs.txt"
    gnu_match       "cut -f2 tab"           cut -f2 "$TMP/tabs.txt"
    gnu_match       "cut -c1-3"             cut -c1-3 "$TMP/lines.txt"
    gnu_match_stdin "cut -d, -f2"           cut -d, -f2 $'a,b,c\nd,e,f\n'
fi

# tr: character translation.
if in_scope tr; then
    section "tr"
    gnu_match_stdin "tr a-z to A-Z"         tr $'hello world\n' a-z A-Z
    gnu_match_stdin "tr delete"             tr $'hello\n' -d l
    gnu_match_stdin "tr squeeze"            tr $'aaabbbccc\n' -s abc
fi

# tac: reverse lines.
if in_scope tac; then
    section "tac"
    gnu_match       "tac file"              tac "$TMP/lines.txt"
    gnu_match_stdin "tac stdin"             tac $'a\nb\nc\n'
fi

# rev: reverse characters per line.
if in_scope rev; then
    section "rev"
    gnu_match       "rev file"              rev "$TMP/long.txt"
    gnu_match_stdin "rev stdin"             rev $'abc\n'
fi

# nl: numbered lines.
if in_scope nl; then
    section "nl"
    gnu_match       "nl file"               nl "$TMP/lines.txt"
fi

# fold: width wrap, with shorthand.
if in_scope fold; then
    section "fold"
    gnu_match       "fold -10 file"         fold -10 "$TMP/long.txt"
    gnu_match       "fold -w 10 file"       fold -w 10 "$TMP/long.txt"
    gnu_match_stdin "fold -20 stdin"        fold $'this is a longer line than twenty\n' -20
fi

# tee: split output.
if in_scope tee; then
    section "tee"
    echo "tee-test" > "$TMP/tee_in.txt"
    # Write to a tee output file, verify stdout and file both match.
    local_out=$(echo "tee-test" | tee "$TMP/tee_out.txt")
    if [ "$local_out" = "tee-test" ] && [ "$(cat "$TMP/tee_out.txt")" = "tee-test" ]; then
        _record_pass "tee stdout + file"
    else
        _record_fail "tee stdout + file" "stdout=$local_out, file=$(cat $TMP/tee_out.txt)"
    fi
fi

# paste: merge side-by-side.
if in_scope paste; then
    section "paste"
    echo "a b c" > "$TMP/p1"
    echo "1 2 3" > "$TMP/p2"
    gnu_match       "paste two files"       paste "$TMP/p1" "$TMP/p2"
fi

# seq: numeric sequences.
if in_scope seq; then
    section "seq"
    gnu_match       "seq 1 5"               seq 1 5
    gnu_match       "seq 5"                 seq 5
    gnu_match       "seq 2 2 10"            seq 2 2 10
fi

# expand / unexpand: tab handling.
if in_scope expand; then
    section "expand"
    gnu_match       "expand default"        expand "$TMP/tabs.txt"
fi
if in_scope unexpand; then
    section "unexpand"
    # unexpand converts spaces back to tabs; need a spaced file
    printf '    indent\n' > "$TMP/spaced"
    gnu_match       "unexpand -a"           unexpand -a "$TMP/spaced"
fi

# split: splits into pieces.
if in_scope split; then
    section "split"
    cd "$TMP"
    rm -f xa* xb* xc* xs_* 2>/dev/null
    split -l 3 lines.txt xs_ 2>/dev/null
    local_split_rc=$?
    shopt -s nullglob
    split_files=(xs_*)
    shopt -u nullglob
    if [ $local_split_rc -eq 0 ] && [ ${#split_files[@]} -ge 2 ]; then
        _record_pass "split -l 3 produces multiple files"
    else
        _record_fail "split -l 3 produces multiple files" "rc=$local_split_rc files=${#split_files[@]}"
    fi
    cd - >/dev/null
fi

# dirname / basename: path manipulation.
if in_scope dirname; then
    section "dirname"
    gnu_match       "dirname path"          dirname /a/b/c
    gnu_match       "dirname root"          dirname /
    gnu_match       "dirname relative"      dirname foo.txt
fi
if in_scope basename; then
    section "basename"
    gnu_match       "basename path"         basename /a/b/c.txt
    gnu_match       "basename strip ext"    basename /a/b/c.txt .txt
fi

# readlink / realpath: only run if there's a sane symlink target.
if in_scope readlink; then
    section "readlink"
    ln -sf "$TMP/lines.txt" "$TMP/mylink" 2>/dev/null
    gnu_match       "readlink symlink"      readlink "$TMP/mylink"
fi
if in_scope realpath; then
    section "realpath"
    gnu_match       "realpath file"         realpath "$TMP/lines.txt"
fi

# which: finds binaries.
if in_scope which; then
    section "which"
    gnu_match       "which bash"            which bash
fi

# yes: needs to be rate-limited since it's infinite.
if in_scope yes; then
    section "yes"
    out=$(timeout 1 yes 2>/dev/null | head -3)
    if [ "$out" = $'y\ny\ny' ]; then
        _record_pass "yes (first 3 lines)"
    else
        _record_fail "yes (first 3 lines)" "got=$(printf %q "$out")"
    fi
fi

# true / false: exit codes.
if in_scope true; then
    section "true / false"
    exit_code_is    "true exits 0"   0 true
    exit_code_is    "false exits 1"  1 false
fi

# pwd / whoami / logname / id / uname / env / printenv / tty:
# env-dependent, just require non-empty successful output.
if in_scope pwd;      then section "pwd";      runs_nonempty "pwd"      pwd;      fi
if in_scope whoami;   then section "whoami";   runs_nonempty "whoami"   whoami;   fi
if in_scope logname;  then section "logname";  runs_nonempty "logname"  logname;  fi
if in_scope id;       then section "id";       runs_nonempty "id"       id;       fi
if in_scope uname;    then section "uname";    runs_nonempty "uname"    uname;    fi
if in_scope printenv; then section "printenv"; runs_nonempty "printenv PATH" printenv PATH; fi
if in_scope env;      then section "env";      runs_nonempty "env"      env;      fi

# date: format varies but should run and produce something.
if in_scope date; then
    section "date"
    runs_nonempty "date default" date
    runs_nonempty "date +%Y"     date +%Y
fi

# File-manipulation utilities — destructive, run in $TMP and clean up.
if in_scope mkdir; then
    section "mkdir / rm / touch"
    mkdir "$TMP/d1" 2>/dev/null && [ -d "$TMP/d1" ] \
        && _record_pass "mkdir creates directory" \
        || _record_fail "mkdir creates directory" ""
    touch "$TMP/d1/newfile" 2>/dev/null && [ -f "$TMP/d1/newfile" ] \
        && _record_pass "touch creates file" \
        || _record_fail "touch creates file" ""
    rm "$TMP/d1/newfile" 2>/dev/null && [ ! -e "$TMP/d1/newfile" ] \
        && _record_pass "rm removes file" \
        || _record_fail "rm removes file" ""
fi

if in_scope cp; then
    section "cp"
    cp "$TMP/lines.txt" "$TMP/copy.txt" 2>/dev/null
    if cmp -s "$TMP/lines.txt" "$TMP/copy.txt"; then
        _record_pass "cp file byte-identical"
    else
        _record_fail "cp file byte-identical" "cmp mismatch"
    fi
fi

if in_scope mv; then
    section "mv"
    cp "$TMP/lines.txt" "$TMP/to_move.txt"
    mv "$TMP/to_move.txt" "$TMP/moved.txt" 2>/dev/null
    if [ -f "$TMP/moved.txt" ] && [ ! -e "$TMP/to_move.txt" ]; then
        _record_pass "mv renames"
    else
        _record_fail "mv renames" "moved=$([ -f $TMP/moved.txt ] && echo y || echo n) src_gone=$([ ! -e $TMP/to_move.txt ] && echo y || echo n)"
    fi
fi

if in_scope ln; then
    section "ln"
    ln -sf "$TMP/lines.txt" "$TMP/mylink2" 2>/dev/null
    if [ -L "$TMP/mylink2" ]; then
        _record_pass "ln -sf creates symlink"
    else
        _record_fail "ln -sf creates symlink" ""
    fi
fi

if in_scope chmod; then
    section "chmod"
    # Use /usr/bin/stat explicitly — AiLang stat doesn't support -c %a yet
    # (known gap, tracked in memory). We're testing chmod here, not stat.
    touch "$TMP/cf" && chmod 644 "$TMP/cf" 2>/dev/null && \
        [ "$(/usr/bin/stat -c %a "$TMP/cf" 2>/dev/null)" = "644" ] \
        && _record_pass "chmod 644" \
        || _record_fail "chmod 644" "mode=$(/usr/bin/stat -c %a $TMP/cf 2>/dev/null)"
fi

# find: directory traversal. Smoke-test on our known tree.
if in_scope find; then
    section "find"
    gnu_match       "find by name"          find "$TMP" -name "lines.txt"
fi

# ls: directory listing. Format varies across systems (locale/time), so
# compare against GNU but allow that environment might cause drift.
if in_scope ls; then
    section "ls"
    # `ls` plain should be byte-identical when no color/locale funk.
    gnu_match       "ls simple dir"         ls "$TMP"
fi

# ─── Segfault sweep: every installed binary should run --help or exit cleanly.
section "Segfault sweep"
install_dir="$HOME/.local/bin/ailang"
if [ -d "$install_dir" ]; then
    segv=0
    for bin in "$install_dir"/*; do
        [ -x "$bin" ] || continue
        name=$(basename "$bin")
        # Use --version if supported, else a trivial stdin close. Anything
        # non-segfault is acceptable here — we're only looking for crashes.
        timeout 2 "$bin" --version </dev/null >/dev/null 2>&1
        rc=$?
        if [ $rc -eq 139 ]; then
            segv=$((segv+1))
            _record_fail "segv: $name" ""
        fi
    done
    if [ $segv -eq 0 ]; then
        _record_pass "no segfaults across $(ls "$install_dir" | wc -l) binaries"
    fi
else
    _record_skip "segv scan" "$install_dir not populated (run install_ailang_utils.sh)"
fi

# ─── Summary ────────────────────────────────────────────────────────────────
echo
echo "════════════════════════════════════════════"
printf "  %sPass: %d%s   %sFail: %d%s   %sSkip: %d%s\n" \
       "$GREEN" "$pass" "$NC" "$RED" "$fail" "$NC" "$YELLOW" "$skip" "$NC"
echo "════════════════════════════════════════════"

if [ $fail -gt 0 ]; then
    echo
    printf "%sFailures:%s\n" "$RED" "$NC"
    for f in "${failures[@]}"; do
        printf "  - %s\n" "$f"
    done
    exit 1
fi

exit 0
