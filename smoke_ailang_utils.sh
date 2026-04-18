#!/usr/bin/env bash
# smoke_ailang_utils.sh
#
# End-to-end sanity for the installed AILANG coreutils. Run in a
# fresh terminal (after `source ~/.bashrc`) to confirm everything
# resolves and behaves. Exits 0 on all-green, non-zero otherwise.
#
# Usage:
#     ./smoke_ailang_utils.sh          # run all checks
#     ./smoke_ailang_utils.sh -v       # verbose (print each util's output)

set -u
VERBOSE=0
[ "${1:-}" = "-v" ] && VERBOSE=1

GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[1;33m'; NC=$'\033[0m'

pass=0; fail=0; fail_list=()

TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

printf 'one\ntwo\ntwo\nthree\nfour\nfive\n' > "$TMP/f.txt"
printf 'alpha beta gamma\n' > "$TMP/g.txt"

check() {
    local name="$1" expected="$2" actual="$3" rc="$4"
    if [ $rc -eq 139 ]; then
        fail=$((fail+1)); fail_list+=("$name: SEGFAULT")
        printf "  %s%-18s ✗ SEGFAULT%s\n" "$RED" "$name" "$NC"
        return
    fi
    if [ $rc -eq 124 ]; then
        fail=$((fail+1)); fail_list+=("$name: TIMEOUT")
        printf "  %s%-18s ✗ TIMEOUT%s\n" "$RED" "$name" "$NC"
        return
    fi
    if [ "$actual" = "$expected" ]; then
        pass=$((pass+1))
        [ $VERBOSE -eq 1 ] \
            && printf "  %s%-18s ✓%s  %s\n" "$GREEN" "$name" "$NC" "$actual" \
            || printf "  %s%-18s ✓%s\n"     "$GREEN" "$name" "$NC"
    else
        fail=$((fail+1)); fail_list+=("$name: got '$actual' want '$expected'")
        printf "  %s%-18s ✗%s  got=%q  want=%q\n" "$RED" "$name" "$NC" "$actual" "$expected"
    fi
}

check_rc0() {
    local name="$1" actual="$2" rc="$3"
    if [ $rc -eq 139 ]; then
        fail=$((fail+1)); fail_list+=("$name: SEGFAULT")
        printf "  %s%-18s ✗ SEGFAULT%s\n" "$RED" "$name" "$NC"; return
    fi
    if [ $rc -eq 124 ]; then
        fail=$((fail+1)); fail_list+=("$name: TIMEOUT")
        printf "  %s%-18s ✗ TIMEOUT%s\n" "$RED" "$name" "$NC"; return
    fi
    if [ $rc -eq 0 ]; then
        pass=$((pass+1))
        [ $VERBOSE -eq 1 ] \
            && printf "  %s%-18s ✓%s  rc=0  out=%q\n" "$GREEN" "$name" "$NC" "$actual" \
            || printf "  %s%-18s ✓%s\n"                "$GREEN" "$name" "$NC"
    else
        fail=$((fail+1)); fail_list+=("$name: rc=$rc")
        printf "  %s%-18s ✗ rc=%d%s\n" "$RED" "$name" "$rc" "$NC"
    fi
}

echo "=================================================="
echo " AILANG CoreUtils — smoke test"
echo "=================================================="

echo
echo "${YELLOW}[1/4] PATH ordering${NC}"
first_cat=$(type -p cat 2>/dev/null)
if [ "$first_cat" = "$HOME/.local/bin/cat" ]; then
    printf "  %s%-18s ✓%s  first 'cat' resolves to %s\n" "$GREEN" "PATH:cat" "$NC" "$first_cat"
    pass=$((pass+1))
else
    printf "  %s%-18s ✗%s  'cat' resolves to %s (expected ~/.local/bin/cat)\n" "$RED" "PATH:cat" "$NC" "$first_cat"
    echo "  Hint: add 'export PATH=\"\$HOME/.local/bin:\$PATH\"' at the END of ~/.bashrc"
    fail=$((fail+1)); fail_list+=("PATH:cat not shadowed")
fi

echo
echo "${YELLOW}[2/4] Functional behavior — 30 key utils${NC}"

# ---- exact-output utils
out=$(timeout 3 echo "hello world" 2>/dev/null); check "echo"      "hello world" "$out" $?
out=$(timeout 3 basename /a/b/c.txt 2>/dev/null); check "basename" "c.txt"        "$out" $?
out=$(timeout 3 dirname  /a/b/c.txt 2>/dev/null); check "dirname"  "/a/b"         "$out" $?
out=$(timeout 3 whoami            2>/dev/null); check "whoami"    "$USER"        "$out" $?
out=$(timeout 3 seq 1 3           2>/dev/null); check "seq"       $'1\n2\n3'    "$out" $?
out=$(timeout 3 head -n 2 "$TMP/f.txt" 2>/dev/null); check "head" $'one\ntwo'   "$out" $?
out=$(timeout 3 tail -n 2 "$TMP/f.txt" 2>/dev/null); check "tail" $'four\nfive' "$out" $?
out=$(timeout 3 tac       "$TMP/f.txt" 2>/dev/null); check "tac"  $'five\nfour\nthree\ntwo\ntwo\none' "$out" $?
out=$(timeout 3 rev       "$TMP/g.txt" 2>/dev/null); check "rev"  "ammag ateb ahpla" "$out" $?
out=$(timeout 3 uniq      "$TMP/f.txt" 2>/dev/null); check "uniq" $'one\ntwo\nthree\nfour\nfive' "$out" $?
out=$(timeout 3 sort      "$TMP/f.txt" 2>/dev/null); check "sort" $'five\nfour\none\nthree\ntwo\ntwo' "$out" $?
out=$(printf 'a b' | timeout 3 tr a A 2>/dev/null); check "tr"    "A b"           "$out" $?
out=$(printf 'a b c\n' | timeout 3 cut -d ' ' -f 2 2>/dev/null); check "cut" "b" "$out" $?
out=$(timeout 3 grep two "$TMP/f.txt" 2>/dev/null); check "grep"  $'two\ntwo'    "$out" $?
out=$(timeout 3 cat "$TMP/g.txt" 2>/dev/null); check "cat" "alpha beta gamma" "$out" $?

# ---- utils where format varies by impl; just assert the binary ran
# (rc=0 for most; logname is special — it fails with rc=1 in non-tty
# contexts even on GNU, so we only check it didn't segfault).
for u in wc nl pwd uname id date env printenv file stat ls df du; do
    case $u in
        wc)       out=$(printf 'a\nb\n' | timeout 3 wc 2>/dev/null); rc=$? ;;
        nl)       out=$(timeout 3 nl "$TMP/f.txt" 2>/dev/null); rc=$? ;;
        ls)       out=$(timeout 3 ls "$TMP" 2>/dev/null); rc=$? ;;
        df)       out=$(timeout 3 df . 2>/dev/null); rc=$? ;;
        du)       out=$(timeout 3 du "$TMP" 2>/dev/null); rc=$? ;;
        file)     out=$(timeout 3 file "$TMP/f.txt" 2>/dev/null); rc=$? ;;
        stat)     out=$(timeout 3 stat "$TMP/f.txt" 2>/dev/null); rc=$? ;;
        *)        out=$(timeout 3 "$u" 2>/dev/null); rc=$? ;;
    esac
    check_rc0 "$u" "$out" $rc
done

# logname — non-fatal rc acceptable, only segfault fails
timeout 3 logname </dev/null >/dev/null 2>&1; rc=$?
if [ $rc -eq 139 ]; then
    fail=$((fail+1)); fail_list+=("logname: SEGFAULT")
    printf "  %s%-18s ✗ SEGFAULT%s\n" "$RED" "logname" "$NC"
else
    pass=$((pass+1))
    printf "  %s%-18s ✓%s  (rc=%d in non-tty — same as GNU)\n" "$GREEN" "logname" "$NC" $rc
fi

# ---- exit-code-only utils
timeout 3 true 2>/dev/null; check_rc0 "true" "" $?
timeout 3 false 2>/dev/null; rc=$?
if [ $rc -eq 1 ] || [ $rc -eq 139 ] || [ $rc -eq 124 ]; then
    if [ $rc -eq 1 ]; then
        printf "  %s%-18s ✓%s\n" "$GREEN" "false" "$NC"; pass=$((pass+1))
    elif [ $rc -eq 139 ]; then
        printf "  %s%-18s ✗ SEGFAULT%s\n" "$RED" "false" "$NC"; fail=$((fail+1)); fail_list+=("false: SEGFAULT")
    else
        printf "  %s%-18s ✗ TIMEOUT%s\n" "$RED" "false" "$NC"; fail=$((fail+1)); fail_list+=("false: TIMEOUT")
    fi
fi

echo
echo "${YELLOW}[3/4] File-manipulation utils (side-effect check)${NC}"
rm -rf "$TMP/fm"; mkdir -p "$TMP/fm"
cp "$TMP/f.txt" "$TMP/fm/src.txt"
timeout 3 mkdir "$TMP/fm/newdir" 2>/dev/null;    check_rc0 "mkdir"    "" $?
timeout 3 touch "$TMP/fm/touched" 2>/dev/null;   check_rc0 "touch"    "" $?
timeout 3 cp "$TMP/fm/src.txt" "$TMP/fm/cp.txt" 2>/dev/null; check_rc0 "cp" "" $?
timeout 3 mv "$TMP/fm/cp.txt" "$TMP/fm/mv.txt" 2>/dev/null;  check_rc0 "mv" "" $?
timeout 3 ln "$TMP/fm/src.txt" "$TMP/fm/hardlnk" 2>/dev/null; check_rc0 "ln" "" $?
timeout 3 chmod 644 "$TMP/fm/src.txt" 2>/dev/null; check_rc0 "chmod" "" $?
timeout 3 rm "$TMP/fm/mv.txt" 2>/dev/null;       check_rc0 "rm"       "" $?

echo
echo "${YELLOW}[4/4] All 57 binaries — segfault scan${NC}"
crash_count=0
while IFS= read -r bin; do
    util=$(basename "$bin" .x)
    out=$(timeout 2 "$bin" --version </dev/null 2>&1 | head -c 40)
    rc=$?
    # Many of our utils don't support --version; exit codes vary.
    # We only care about SIGSEGV (139). Anything else is "at least it ran".
    if [ $rc -eq 139 ]; then
        printf "  %s%-18s ✗ SEGFAULT on --version%s\n" "$RED" "$util" "$NC"
        crash_count=$((crash_count+1))
        fail_list+=("$util: --version segfault")
    fi
done < <(find "$HOME/.local/bin/ailang" -name '*.x' -type f | sort)

if [ $crash_count -eq 0 ]; then
    printf "  %s%-18s ✓%s  no segfaults across all 57 binaries\n" "$GREEN" "segfault-scan" "$NC"
    pass=$((pass+1))
else
    printf "  %s%-18s ✗%s  %d binaries segfaulted\n" "$RED" "segfault-scan" "$NC" "$crash_count"
    fail=$((fail+crash_count))
fi

echo
echo "=================================================="
printf "  %sPass: %d  %sFail: %d%s\n" "$GREEN" "$pass" "$RED" "$fail" "$NC"
echo "=================================================="

if [ $fail -gt 0 ]; then
    echo
    echo "${RED}Failures:${NC}"
    for f in "${fail_list[@]}"; do echo "  - $f"; done
    exit 1
fi

echo "${GREEN}All green.${NC}"
exit 0
