import hmac
import hashlib
import base64

# RFC 5869: HMAC-based Extract-and-Expand Key Derivation Function (HKDF)
def hkdf_sha256(ikm, salt, info, length):
    # Step 1: Extract (Generate the Pseudorandom Key)
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    
    # Step 2: Expand (Generate the Output Key Material)
    okm = b""
    t = b""
    i = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
        i += 1
        
    return okm[:length]

def derive_web3_session_key(client_nonce_b64, server_nonce_b64, session_id):
    print(f"Client Nonce : {client_nonce_b64}")
    print(f"Server Nonce : {server_nonce_b64}")
    print(f"Session ID   : {session_id}\n")
    
    client_nonce = base64.b64decode(client_nonce_b64)
    server_nonce = base64.b64decode(server_nonce_b64)
    
    ikm = client_nonce + server_nonce
    salt = session_id.encode('utf-8')
    info = b"web3-session-v1"
    
    key = hkdf_sha256(ikm, salt, info, 32)
    return key

if __name__ == "__main__":
    print("--- Web 3.0 Server: HKDF-SHA256 Session Key Derivation ---\n")
    
    key = derive_web3_session_key("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", 
                                  "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=", 
                                  "12345678-1234-1234-1234-123456789abc")
                                  
    print(f"Derived 256-bit Session Key (Hex): {key.hex()}")