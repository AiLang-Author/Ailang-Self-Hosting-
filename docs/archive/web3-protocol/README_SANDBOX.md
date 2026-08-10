# Web 3.0 Demo Sandbox

This directory contains a suite of mock C and Python scripts that demonstrate the core architecture, security, and rendering pipeline of the Web 3.0 Protocol.

These are lightweight, standalone concepts. You can compile and run them individually, or run the entire suite using Docker.

## Running with Docker (Recommended)

The easiest way to see everything in action is to build and run the Docker container. This will compile all C scripts and execute them in order.

```bash
docker build -t web3-sandbox .
docker run --rm web3-sandbox
```

## Running Manually

If you prefer to run them natively, ensure you have `gcc` and `python3` installed.

### 1. Compile the C Scripts

A `Makefile` is provided to compile all C binaries in a single step:

```bash
make all
```

### 2. Run the Demos

**Standalone Concepts:**
- `./demo_rasterizer` - TVG vector rasterization
- `./demo_html_parser` - HTML structural parsing
- `./demo_debounce` - Input rate limiting
- `./demo_keepalive` - PING/PONG keepalives
- `./demo_malformed_json` - JSON parse error handling
- `./demo_compression` - ZSTD flag decoding
- `./demo_batching` - Deferred TVG rendering
- `./demo_sequence_tracking` - Anti-replay attack logic
- `./demo_ed25519_verify` - Mode 3 Ed25519 signature checks
- `./demo_scene_graph` - Retained mode tree tracking
- `./demo_text_measure` - Simulated text bounding box queries

**Python Validation:**
- `python3 demo_schema_validator.py` - Validates event JSON structures
- `python3 demo_encryption_mode_switch.py` - Simulates AEAD/TLS negotiation

**IPC Network Simulation (Terminal 1 & 2):**
Start the server in one terminal, then run the client in another to see the encrypted JSON handshake and message routing over Unix Domain Sockets:
```bash
./demo_server      # Terminal 1
./demo_client      # Terminal 2
```

**Streaming Push Simulation (Terminal 1 & 2):**
Start the streaming server, then run the stream client to see the server autonomously pushing live dashboard metrics without polling:
```bash
./demo_stream_server      # Terminal 1
./demo_stream_client      # Terminal 2
```