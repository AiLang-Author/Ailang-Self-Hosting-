#!/bin/bash
# Tighter OAuth URL extractor — write to file, dedupe, length-cap.

set -e
IN=/tmp/claude_strings.txt
OUT=/tmp/oauth_urls.txt

if [ ! -f "$IN" ]; then
  echo "missing $IN — first run: strings ~/.local/share/claude/versions/2.1.121 > $IN"
  exit 1
fi

# Extract https?:// URLs, drop anything with whitespace or quotes,
# keep only those mentioning claude.ai/api.anthropic.com/console.anthropic.com,
# AND containing oauth or /token in the path.
python3 - <<'PY' > "$OUT"
import re
url_re = re.compile(r'https?://[A-Za-z0-9._~/?#\[\]@!$&()*+,;=%-]+')
with open('/tmp/claude_strings.txt') as f:
    seen = set()
    for line in f:
        for m in url_re.finditer(line):
            u = m.group(0).rstrip('.,;:)')
            # length sanity — real URLs are well under 200 chars
            if len(u) > 200:
                continue
            host_ok = re.search(r'(claude\.ai|console\.anthropic\.com|api\.anthropic\.com|platform\.claude\.com|claude\.com)', u)
            path_ok = re.search(r'/(oauth|token|authorize|register|callback)\b', u)
            if host_ok and path_ok:
                seen.add(u)
for u in sorted(seen):
    print(u)
PY

echo "Lines: $(wc -l < "$OUT")"
echo "---"
cat "$OUT"
