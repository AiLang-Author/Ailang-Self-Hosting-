FROM gcc:latest

WORKDIR /web3-demos

# Copy all source files into the container
COPY . .

# Compile all C files using the Makefile
RUN make all

# Create an automated runner script to demonstrate the various components
RUN echo '#!/bin/bash\n\
echo "================================================="\n\
echo "      WEB 3.0 PROTOCOL - DEMO ENVIRONMENT      "\n\
echo "================================================="\n\
echo ""\n\
echo "[1/17] Testing TVG Rasterizer..."\n\
./demo_rasterizer\n\
echo ""\n\
echo "[2/17] Testing HTML Parser..."\n\
./demo_html_parser\n\
echo ""\n\
echo "[3/17] Testing Client Debouncer..."\n\
./demo_debounce\n\
echo ""\n\
echo "[4/17] Testing PING/PONG Keepalive..."\n\
./demo_keepalive\n\
echo ""\n\
echo "[5/17] Testing Malformed JSON Rejection..."\n\
./demo_malformed_json\n\
echo ""\n\
echo "[6/17] Testing Python JSON Schema Validator..."\n\
python3 demo_schema_validator.py\n\
echo ""\n\
echo "[7/17] Testing Compression (ZSTD) Flag..."\n\
./demo_compression\n\
echo ""\n\
echo "[8/17] Testing Deferred Rendering (Batching)..."\n\
./demo_batching\n\
echo ""\n\
echo "[9/17] Testing Sequence Number Tracking..."\n\
./demo_sequence_tracking\n\
echo ""\n\
echo "[10/17] Testing Ed25519 Signature Verification..."\n\
./demo_ed25519_verify\n\
echo ""\n\
echo "[11/17] Testing Oversized Payload Drop..."\n\
./demo_oversized_payload\n\
echo ""\n\
echo "[12/17] Testing Auckland Layout Parser..."\n\
./demo_auckland_parser\n\
echo ""\n\
echo "[13/17] Testing C Fluent TVG Macro..."\n\
./demo_tvg_macro\n\
echo ""\n\
echo "[14/17] Testing RES_ICON Caching..."\n\
./demo_icon_cache\n\
echo ""\n\
echo "[15/17] Testing WebRTC Media Streams..."\n\
./demo_webrtc_stream\n\
echo ""\n\
echo "[16/17] Testing Dynamic Media Resizing..."\n\
./demo_media_resize\n\
echo ""\n\
echo "[17/19] Testing Dynamic Encryption Mode Switch..."\n\
python3 demo_encryption_mode_switch.py\n\
echo ""\n\
echo "[18/19] Testing HKDF-SHA256 Session Key Derivation..."\n\
python3 demo_hkdf.py\n\
echo ""\n\
echo "[19/19] Testing Unified Web3Client Architecture..."\n\
./demo_web3_client\n\
echo ""\n\
echo "[IPC] Testing IPC Connect (Server + Client)..."\n\
./demo_server & \n\
SERVER_PID=$!\n\
sleep 1\n\
./demo_client\n\
kill $SERVER_PID\n\
wait $SERVER_PID 2>/dev/null\n\
' > run_demos.sh && chmod +x run_demos.sh

CMD ["./run_demos.sh"]