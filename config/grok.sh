#!/bin/sh
# Jail v0: grok CLI sees a quarantine $HOME, not /root and not FileTree.
# Real binary: /system/libexec/grok
# Design: docs/aos/SANDBOX_JAIL.md

HOME=/data/sandboxes/grok/home
TMPDIR=/data/sandboxes/grok/tmp
export HOME TMPDIR
export PATH="/system/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export SSL_CERT_DIR="${SSL_CERT_DIR:-/etc/ssl/certs}"

mkdir -p "$HOME/.grok" "$TMPDIR" 2>/dev/null
# Seed jail auth from the image copy if Grok deleted a stale token.
if [ ! -s "$HOME/.grok/auth.json" ] && [ -s /root/.grok/auth.json ]; then
	cp /root/.grok/auth.json "$HOME/.grok/auth.json"
	chmod 600 "$HOME/.grok/auth.json"
fi

exec /system/libexec/grok "$@"
