import json

def negotiate_encryption(client_hello_str, transport_layer):
    print(f"--- New Connection (Transport: {transport_layer.upper()}) ---")
    print(f"Client HELLO: {client_hello_str}")
    
    try:
        hello = json.loads(client_hello_str)
        client_modes = hello.get("encryption", [])
    except:
        return "ERROR 101 BAD_HANDSHAKE"

    chosen_mode = None

    # Server Policy: 
    # - If transport is WSS (TLS), we can safely use Mode 1 (Plaintext inner frames).
    # - If transport is WS (Cleartext) or we want defense-in-depth, require Mode 2 (AEAD).
    # - If transport is a local Unix Socket, we can safely use Mode 0 (Plaintext).
    
    if transport_layer == "wss" and "none" in client_modes:
        chosen_mode = "none"
        print("  └─ Server selected Mode 1: TLS 1.3 (Inner frames are plaintext 'none')")
    elif "aead" in client_modes:
        chosen_mode = "aead"
        print("  └─ Server selected Mode 2: Per-Message AEAD (ChaCha20-Poly1305)")
    elif "none" in client_modes and transport_layer == "unix":
        chosen_mode = "none"
        print("  └─ Server selected Mode 0: Plaintext (Trusting Local OS Unix Socket)")
    else:
        print("  └─ [REJECTED] ERROR 102: ENCRYPTION_REQUIRED. Insecure transport requires AEAD.\n")
        return None

    welcome = {
        "version": "1.0",
        "session_id": "12345678-1234-1234-1234-123456789abc",
        "encryption": chosen_mode
    }
    
    if chosen_mode == "aead":
        welcome["server_nonce"] = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="
        
    print(f"Server WELCOME: {json.dumps(welcome)}\n")
    return chosen_mode

def main():
    print("--- Web 3.0 Server: Dynamic Encryption Mode Switching ---\n")
    negotiate_encryption('{"version":"1.0", "encryption":["none"]}', transport_layer="wss")
    negotiate_encryption('{"version":"1.0", "encryption":["none"]}', transport_layer="ws")
    negotiate_encryption('{"version":"1.0", "encryption":["none", "aead"]}', transport_layer="ws")
    negotiate_encryption('{"version":"1.0", "encryption":["none"]}', transport_layer="unix")

if __name__ == "__main__":
    main()