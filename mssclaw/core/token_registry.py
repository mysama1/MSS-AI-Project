"""
Token Registry v1.0 — 离线加密令牌管理.

当 Vault 锁定时作为后备存储，使用 AES-GCM + 静态密钥。
解锁 Vault 后可一键迁移 (mssclaw vault import-tokens).
"""
import os, json, hashlib, base64, time
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

REGISTRY_PATH = Path.home() / ".mssclaw" / "token_registry.enc"
# ⚠ Static key for offline access only. Migrate to Vault when unlocked.
_OFFLINE_PASSPHRASE = "mssclaw_token_registry_v1"
_SALT = b'\x9a\xb3\xc7\xd1\xe5\xf3\xa1\xb2\xc4\xd6\xe8\xfa\x0b\x1c\x2d\x3e\x4f\x50\x61\x72\x83\x94\xa5\xb6\xc7\xd8\xe9\xfa\x0b\x1c\x2d\x3e'

def _derive_key() -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=_SALT, iterations=100_000, backend=default_backend())
    return kdf.derive(_OFFLINE_PASSPHRASE.encode())

def store_token(key: str, value: str, tags: list = None):
    """加密存储Token."""
    aesgcm = AESGCM(_derive_key())
    nonce = os.urandom(12)
    
    data = json.dumps({"key": key, "value": value, "tags": tags or [],
                       "stored_at": time.time()}).encode()
    ct = aesgcm.encrypt(nonce, data, None)
    
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    existing = {}
    try:
        existing = load_all()
    except:
        pass
    
    existing[key] = base64.b64encode(nonce + ct).decode()
    REGISTRY_PATH.write_text(json.dumps(existing, indent=2))

def get_token(key: str) -> str:
    """读取加密Token."""
    all_tokens = load_all()
    if key not in all_tokens:
        return None
    raw = base64.b64decode(all_tokens[key])
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(_derive_key())
    data = json.loads(aesgcm.decrypt(nonce, ct, None))
    return data["value"]

def load_all() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    return json.loads(REGISTRY_PATH.read_text())

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: token_registry.py store <key> <value> | get <key> | list")
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd == "store" and len(sys.argv) >= 4:
        store_token(sys.argv[2], sys.argv[3])
        print(f"✅ Stored: {sys.argv[2]}")
    elif cmd == "get" and len(sys.argv) >= 3:
        val = get_token(sys.argv[2])
        print(val or "Not found")
    elif cmd == "list":
        all_t = load_all()
        for k in all_t:
            print(f"  {k} (stored)")
    else:
        print("Unknown command")
