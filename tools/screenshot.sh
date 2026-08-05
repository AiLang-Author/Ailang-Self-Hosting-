#!/bin/bash
# screenshot.sh — Capture framebuffer from target via SSH, save as PNG
#
# Usage:
#   ./tools/screenshot.sh                    # target 10.0.0.2, save /tmp/screenshot.png
#   ./tools/screenshot.sh --qemu             # QEMU at localhost:2222
#   ./tools/screenshot.sh 10.0.0.2 out.png   # custom target + output
#   ./tools/screenshot.sh --qemu out.png     # QEMU + custom output

set -e

# Parse args
if [ "$1" = "--qemu" ]; then
    SSH_CMD="ssh -p 2222 -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@localhost"
    OUTPUT="${2:-/tmp/screenshot.png}"
else
    TARGET="${1:-10.0.0.2}"
    OUTPUT="${2:-/tmp/screenshot.png}"
    SSH_CMD="ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$TARGET"
fi

# Get framebuffer info
INFO=$($SSH_CMD "echo \$(cat /sys/class/graphics/fb0/virtual_size),\$(cat /sys/class/graphics/fb0/bits_per_pixel),\$(cat /sys/class/graphics/fb0/stride)")
IFS=',' read -r VSIZE_W VSIZE_H BPP STRIDE <<< "$INFO"

echo "Framebuffer: ${VSIZE_W}x${VSIZE_H} ${BPP}bpp stride=${STRIDE}"

# Grab framebuffer
RAW="/tmp/fb_raw_$$.bin"
$SSH_CMD "dd if=/dev/fb0 bs=${STRIDE} count=${VSIZE_H} 2>/dev/null" > "$RAW"

# Convert to PNG
python3 -c "
import struct, zlib

width, height, stride = ${VSIZE_W}, ${VSIZE_H}, ${STRIDE}
px_bytes = ${BPP} // 8

with open('${RAW}', 'rb') as f:
    raw = f.read()

rows = []
for y in range(height):
    row_start = y * stride
    row = bytearray([0])  # PNG filter: None
    for x in range(width):
        off = row_start + x * px_bytes
        b, g, r = raw[off], raw[off+1], raw[off+2]
        row.extend([r, g, b, 255])
    rows.append(bytes(row))

raw_data = b''.join(rows)

def png_chunk(ctype, data):
    c = ctype + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
idat = zlib.compress(raw_data, 6)

with open('${OUTPUT}', 'wb') as f:
    f.write(b'\x89PNG\r\n\x1a\n')
    f.write(png_chunk(b'IHDR', ihdr))
    f.write(png_chunk(b'IDAT', idat))
    f.write(png_chunk(b'IEND', b''))

print(f'Saved {width}x{height} to ${OUTPUT}')
"

rm -f "$RAW"
echo "Screenshot: ${OUTPUT}"
