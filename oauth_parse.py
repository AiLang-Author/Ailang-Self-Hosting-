#!/usr/bin/env python3
"""
OAuth discovery parser for the official Claude Code binary.

Reads /tmp/claude_strings.txt (output of `strings` on the claude binary)
and extracts only the OAuth-relevant facts: real URLs, client_id values,
redirect URIs, scopes, PKCE markers.

Run: python3 oauth_parse.py
"""

import re
import sys
import os

INPUT = "/tmp/claude_strings.txt"
OUTPUT = "/tmp/oauth_parsed.txt"

if not os.path.exists(INPUT):
    print(f"error: {INPUT} not found.")
    print("first run:  strings ~/.local/share/claude/versions/2.1.121 > /tmp/claude_strings.txt")
    sys.exit(1)

with open(INPUT, encoding="utf-8", errors="replace") as f:
    lines = [l.rstrip() for l in f]

out_lines = []
def emit(s=""):
    out_lines.append(s)

# 1. Real OAuth URLs (must be proper https:// AND have an OAuth-shaped path)
url_re = re.compile(r'https?://[^\s"\'<>{},;:`|\\)]+')
relevant_host = re.compile(r'(claude\.ai|anthropic\.com)', re.I)
oauth_path = re.compile(r'/(oauth|authorize|token|callback|userinfo|revoke|consent|sessions|me)\b', re.I)

urls = set()
for line in lines:
    for m in url_re.finditer(line):
        u = m.group(0).rstrip('.,;)')
        if relevant_host.search(u) and oauth_path.search(u):
            urls.add(u)

emit("===== Plausible OAuth URLs =====")
for u in sorted(urls):
    emit(u)
emit()

# 2. Explicit client_id assignments (key=value form)
emit("===== client_id assignments (key=val) =====")
patterns = [
    re.compile(r'(?:client_?id|CLIENT_ID)\s*[:=]\s*["\']([^"\'\s]+)["\']', re.I),
    re.compile(r'["\']client_?id["\']\s*[:=]\s*["\']([^"\'\s]+)["\']', re.I),
]
ids = set()
for line in lines:
    for p in patterns:
        for m in p.finditer(line):
            v = m.group(1)
            if 4 < len(v) < 200 and not v.startswith("$"):
                ids.add(v)
for cid in sorted(ids):
    emit(cid)
emit()

# 3. Bare UUIDs whose neighborhood mentions oauth/client
emit("===== UUIDs near oauth context =====")
uuid_re = re.compile(
    r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'
)
keep = set()
for i, line in enumerate(lines):
    if not uuid_re.search(line):
        continue
    ctx = " ".join(lines[max(0, i - 3) : i + 4]).lower()
    if any(k in ctx for k in ["oauth", "client_id", "clientid", "authorize", "consent", "token"]):
        for u in uuid_re.findall(line):
            keep.add(u)
for u in sorted(keep)[:20]:
    emit(u)
emit()

# 4. localhost callbacks
emit("===== localhost redirect URIs =====")
loc_re = re.compile(r'http://(?:localhost|127\.0\.0\.1):\d+[\w/-]*')
locs = set()
for line in lines:
    for m in loc_re.finditer(line):
        locs.add(m.group(0))
for l in sorted(locs)[:20]:
    emit(l)
emit()

# 5. Anthropic-shaped scope strings
emit("===== Anthropic-style scopes (org:/user:/inference:) =====")
scope_re = re.compile(r'\b(?:org|user|inference|api|admin)(?::[\w-]+)+\b', re.I)
scopes = set()
for line in lines:
    for m in scope_re.finditer(line):
        s = m.group(0)
        if len(s) < 80 and ":" in s:
            scopes.add(s)
for s in sorted(scopes)[:50]:
    emit(s)
emit()

# 6. PKCE indicators (yes/no with counts)
emit("===== PKCE markers =====")
pkce_terms = ["code_verifier", "code_challenge", "code_challenge_method", "S256", "pkce"]
for term in pkce_terms:
    cnt = sum(1 for l in lines if term in l.lower())
    if cnt:
        emit(f"{term}: {cnt} occurrences")

# Write file + print summary
with open(OUTPUT, "w") as f:
    f.write("\n".join(out_lines) + "\n")

print(f"wrote {OUTPUT} ({len(out_lines)} lines)")
print("---")
print("\n".join(out_lines))
