import socket
import os
import json
import struct

SOCKET_PATH = "/tmp/web3.sock"

def send_welcome(conn):
    welcome_data = {
        "version": "1.0",
        "session_id": "12345678-1234-1234-1234-123456789abc",
        "encryption": "none",
        "compression": "none",
        "server_nonce": "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",
        "server_pubkey": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    }
    payload = json.dumps(welcome_data).encode('utf-8')
    payload_len = len(payload)

    # Frame Header: Version(0x01), Type(0x02 = WELCOME), Flags(0x0000), Length(32-bit uint)
    # >BBHL means Big-Endian: unsigned char, unsigned char, unsigned short, unsigned long
    header = struct.pack(">BBHL", 0x01, 0x02, 0x0000, payload_len)

    conn.sendall(header + payload)
    print(f"Sent WELCOME frame ({payload_len} bytes).")

def read_hello(conn):
    header = conn.recv(8)
    if len(header) < 8:
        return False

    version, ftype, flags, payload_len = struct.unpack(">BBHL", header)
    if version != 0x01 or ftype != 0x01: # 0x01 = HELLO
        print(f"Protocol error: Expected HELLO (0x01), got 0x{ftype:02X}")
        return False

    print(f"Receiving HELLO frame ({payload_len} bytes)...")
    payload = conn.recv(payload_len)
    print(f"Client sent: {payload.decode('utf-8')}")
    return True

def mock_aead_decrypt(ciphertext, tag):
    # Verify dummy 16-byte Poly1305 tag
    if tag != b'\xAA' * 16:
        return None

    # Dummy ChaCha20 Decrypt (Simple XOR with 0x5A)
    plaintext = bytearray(len(ciphertext))
    for i in range(len(ciphertext)):
        plaintext[i] = ciphertext[i] ^ 0x5A

    return plaintext.decode('utf-8')

def read_encrypted_event(conn):
    header = conn.recv(8)
    if len(header) < 8:
        return False

    version, ftype, flags, payload_len = struct.unpack(">BBHL", header)
    if ftype != 0x03: # 0x03 = EVENT
        print(f"Protocol error: Expected EVENT (0x03), got 0x{ftype:02X}")
        return False

    if not (flags & 0x02): # Check ENCRYPTED flag (Bit 1)
        print("Protocol error: EVENT frame must be ENCRYPTED!")
        return False

    print(f"Receiving Encrypted EVENT frame ({payload_len} bytes)...")
    payload = conn.recv(payload_len)

    ct_len = payload_len - 16
    ciphertext = payload[:ct_len]
    tag = payload[ct_len:]

    plaintext = mock_aead_decrypt(ciphertext, tag)
    if plaintext:
        print(f"Successfully Decrypted Event: {plaintext}")
        
        event_json = json.loads(plaintext)
        action = event_json.get("action", "UNKNOWN")
        print(f"\n[Server Router] Dispatching Action: '{action}'")
        if action == "click":
            print("  └─ Logic: Handling click event...")
            print("  └─ Out: Generating TVG UPDATE delta for the target region.")
    else:
        print("AEAD Tag Authentication Failed!")
        
    return True

def main():
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server_sock:
        server_sock.bind(SOCKET_PATH)
        server_sock.listen(5)
        print(f"Web3 Mock Server (Python) listening on {SOCKET_PATH}")

        while True:
            conn, _ = server_sock.accept()
            print("\n--- Client Connected ---")
            with conn:
                if read_hello(conn):
                    send_welcome(conn)
                    while read_encrypted_event(conn): pass
            print("--- Client Disconnected ---")

if __name__ == "__main__":
    main()