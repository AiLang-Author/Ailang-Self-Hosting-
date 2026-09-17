#!/usr/bin/env bash
# Host vs next ELF identity, next2 vs next3 fixed point, negative contract tests.
# Never writes ailang.x or analyzer.x.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST_AILANG="$ROOT/ailang.x"
HOST_ANALYZER="$ROOT/analyzer.x"
NEXT_AILANG="$ROOT/ailang-next.x"
NEXT_ANALYZER="$ROOT/analyzer-next.x"
NEXT2="$ROOT/ailang-next2.x"
NEXT3="$ROOT/ailang-next3.x"

HOST_AILANG_SHA="9d7f005a88cd075312d370b0b94d58929825dd22b9b31bc84ee913b0cb3cb87f"
HOST_ANALYZER_SHA="43a7b024bbe6f61a1d084f57b18942f9acaa62ccda7fd906d312df4e5ae1efe8"

TMP="$ROOT/tests/contract/_out"
mkdir -p "$TMP"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

[[ -x "$HOST_AILANG" ]] || fail "missing host $HOST_AILANG"
[[ -x "$HOST_ANALYZER" ]] || fail "missing host $HOST_ANALYZER"

got_a="$(sha256sum "$HOST_AILANG" | awk '{print $1}')"
got_z="$(sha256sum "$HOST_ANALYZER" | awk '{print $1}')"
[[ "$got_a" == "$HOST_AILANG_SHA" ]] || fail "ailang.x hash moved: $got_a"
[[ "$got_z" == "$HOST_ANALYZER_SHA" ]] || fail "analyzer.x hash moved: $got_z"
ok "host binaries unchanged"

[[ -x "$NEXT_AILANG" ]] || fail "missing $NEXT_AILANG — build with: ./ailang.x ailang_cli.ailang ailang-next.x"
[[ -x "$NEXT_ANALYZER" ]] || fail "missing $NEXT_ANALYZER — build with: ./ailang.x Applications/Analyzer/ailang_analyzer.ailang analyzer-next.x"

LEGAL="$ROOT/AiLang_CoreUtils/dist/true_util/true.ailang"
[[ -f "$LEGAL" ]] || fail "missing identity corpus $LEGAL"

echo "== A. host vs next on unchanged legal program =="
"$HOST_AILANG" "$LEGAL" "$TMP/true-host.x"
"$NEXT_AILANG" "$LEGAL" "$TMP/true-next.x"
cmp -s "$TMP/true-host.x" "$TMP/true-next.x" || fail "true.ailang ELF diverged host vs next"
ok "true.ailang host vs next identical"

OK_PROG="$ROOT/tests/contract/ok_program.ailang"
"$HOST_AILANG" "$OK_PROG" "$TMP/ok-host.x"
"$NEXT_AILANG" "$OK_PROG" "$TMP/ok-next.x"
cmp -s "$TMP/ok-host.x" "$TMP/ok-next.x" || fail "ok_program.ailang ELF diverged host vs next"
ok "ok_program.ailang host vs next identical"

echo "== FixedPool Initialize=string =="
POOL_SRC="$ROOT/tests/contract/pool_string_init.ailang"
"$HOST_AILANG" "$POOL_SRC" "$TMP/pool_str_host.x"
"$NEXT_AILANG" "$POOL_SRC" "$TMP/pool_str_next.x"
cmp -s "$TMP/pool_str_host.x" "$TMP/pool_str_next.x" || fail "pool_string_init.ailang ELF diverged host vs next"
ok "pool_string_init.ailang host vs next identical"
set +e
pool_out="$("$TMP/pool_str_next.x")"
pool_rc=$?
set -e
echo "$pool_out"
[[ "$pool_rc" -eq 0 ]] || fail "pool_string_init.ailang next run rc=$pool_rc"
echo "$pool_out" | grep -q "hello=hello" || fail "pool_string_init did not print hello=hello"
echo "$pool_out" | grep -q "hello0=104" || fail "pool_string_init hello0 was not 104"
echo "$pool_out" | grep -q "empty_len=0" || fail "pool_string_init empty_len missing"
ok "pool_string_init.ailang next run: string slot is a real pointer"

echo "== ReturnValue in ThenBlock =="
RET_SRC="$ROOT/tests/contract/ret_in_then.ailang"
"$NEXT_AILANG" "$RET_SRC" "$TMP/ret_then_next.x"
set +e
ret_out="$("$TMP/ret_then_next.x")"
ret_rc=$?
set -e
echo "$ret_out"
[[ "$ret_rc" -eq 0 ]] || fail "ret_in_then.ailang next run rc=$ret_rc"
echo "$ret_out" | grep -q "fib7=13" || fail "Fib ThenBlock ReturnValue fell through"
echo "$ret_out" | grep -q "clamp=0" || fail "ClampNeg ThenBlock ReturnValue fell through"
ok "ret_in_then.ailang: ReturnValue in ThenBlock returns"

echo "== D. negative tests against next only =="
set +e
"$NEXT_AILANG" "$ROOT/tests/contract/bad_assign.ailang" "$TMP/bad_assign.x"
rc_assign=$?
"$NEXT_AILANG" "$ROOT/tests/contract/bad_print.ailang" "$TMP/bad_print.x"
rc_print=$?
"$NEXT_AILANG" "$ROOT/tests/contract/bad_lib_runtask.ailang" "$TMP/bad_lib.x"
rc_lib=$?
"$NEXT_ANALYZER" "$ROOT/tests/contract/ok_program.ailang"
rc_ok_an=$?
"$NEXT_ANALYZER" "$ROOT/tests/contract/bad_assign.ailang"
rc_bad_an=$?
set -e

[[ "$rc_assign" -ne 0 ]] || fail "next compiled bad_assign.ailang"
ok "next rejected bad_assign.ailang"
[[ "$rc_print" -ne 0 ]] || fail "next compiled bad_print.ailang"
ok "next rejected bad_print.ailang"
[[ "$rc_lib" -ne 0 ]] || fail "next compiled bad_lib_runtask.ailang"
ok "next rejected bad_lib_runtask.ailang"
[[ "$rc_ok_an" -eq 0 || "$rc_ok_an" -eq 1 ]] || fail "analyzer-next failed ok_program.ailang rc=$rc_ok_an"
ok "analyzer-next accepted ok_program.ailang"
[[ "$rc_bad_an" -eq 2 ]] || fail "analyzer-next did not error on bad_assign.ailang rc=$rc_bad_an"
ok "analyzer-next exit 2 on bad_assign.ailang"

set +e
"$NEXT_AILANG" "$ROOT/tests/contract/bad_arity.ailang" "$TMP/bad_arity.x"
rc_arity=$?
"$NEXT_AILANG" "$ROOT/tests/contract/bad_dup.ailang" "$TMP/bad_dup.x"
rc_dup=$?
"$NEXT_AILANG" "$ROOT/tests/contract/bad_multi_output.ailang" "$TMP/bad_multi.x"
rc_multi=$?
"$NEXT_ANALYZER" "$ROOT/tests/contract/bad_arity.ailang"
rc_arity_an=$?
"$NEXT_ANALYZER" "$ROOT/tests/contract/bad_dup.ailang"
rc_dup_an=$?
"$NEXT_ANALYZER" "$ROOT/tests/contract/bad_multi_output.ailang"
rc_multi_an=$?
set -e

[[ "$rc_arity" -ne 0 ]] || fail "next compiled bad_arity.ailang"
ok "next rejected bad_arity.ailang"
[[ "$rc_dup" -ne 0 ]] || fail "next compiled bad_dup.ailang"
ok "next rejected bad_dup.ailang"
[[ "$rc_multi" -ne 0 ]] || fail "next compiled bad_multi_output.ailang"
ok "next rejected bad_multi_output.ailang"
[[ "$rc_arity_an" -eq 2 ]] || fail "analyzer-next did not error on bad_arity.ailang rc=$rc_arity_an"
ok "analyzer-next exit 2 on bad_arity.ailang"
[[ "$rc_dup_an" -eq 2 ]] || fail "analyzer-next did not error on bad_dup.ailang rc=$rc_dup_an"
ok "analyzer-next exit 2 on bad_dup.ailang"
[[ "$rc_multi_an" -eq 2 ]] || fail "analyzer-next did not error on bad_multi_output.ailang rc=$rc_multi_an"
ok "analyzer-next exit 2 on bad_multi_output.ailang"

echo "== B. next2 vs next3 fixed point if present =="
if [[ -x "$NEXT2" && -x "$NEXT3" ]]; then
    cmp -s "$NEXT2" "$NEXT3" || fail "ailang-next2.x vs ailang-next3.x diverged"
    ok "next2 vs next3 identical"
else
    echo "SKIP: ailang-next2.x / ailang-next3.x not built yet"
fi

echo "ALL CHECKS PASSED"
