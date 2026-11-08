#!/bin/bash
# Compile each tests/haiku/t_*.ailang with the --haiku compiler and run it
# on the Haiku guest. Exit status of this script is the number of failures.
set -u
ROOT=/home/bob/Ailang-Self-Hosting-
CC=${CC:-/tmp/ailang_haiku_cc}
export AILANG_LIB_PATH="$ROOT/Librarys"
unset AILANG_LINSCAN
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
     -o ConnectTimeout=15 -o KexAlgorithms=curve25519-sha256
     -i /home/bob/.ssh/id_ed25519 -p 2222 user@127.0.0.1)
SCP=(scp -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
     -o ConnectTimeout=15 -o KexAlgorithms=curve25519-sha256
     -i /home/bob/.ssh/id_ed25519 -P 2222)
fail=0
for src in "$ROOT"/tests/haiku/t_*.ailang; do
    name=$(basename "$src" .ailang)
    out=/tmp/$name
    echo "=== compile $name ==="
    if ! "$CC" -march=sse2 --haiku "$src" "$out" > /tmp/${name}.compile.log 2>&1; then
        echo "COMPILE FAIL $name"
        tail -30 /tmp/${name}.compile.log
        fail=$((fail + 1))
        continue
    fi
    chmod +x "$out"
    echo "=== copy $name ==="
    if ! "${SCP[@]}" "$out" "user@127.0.0.1:/boot/home/$name" > /tmp/${name}.scp.log 2>&1; then
        echo "SCP FAIL $name"
        cat /tmp/${name}.scp.log
        fail=$((fail + 1))
        continue
    fi
    echo "=== run $name ==="
    timeout 40 "${SSH[@]}" "chmod +x /boot/home/$name && /boot/home/$name"
    rc=$?
    echo "EXIT $name $rc"
    if [ "$rc" -ne 0 ]; then
        # t_hello's success code is 42, not 0.
        if [ "$name" = "t_hello" ] && [ "$rc" -eq 42 ]; then
            echo "PASS $name"
        else
            echo "FAIL $name rc=$rc"
            fail=$((fail + 1))
        fi
    else
        echo "PASS $name"
    fi
done
echo "FAILURES $fail"
exit "$fail"
