"""
Credential Vault v1.0 — 本地加密凭证保险箱

类似 1Password/Keychain 的本地版:
  - AES-256-GCM 加密存储 (cryptography 库) / XOR fallback
  - PBKDF2 主密码派生密钥
  - 分类: api_key, password, token, personal_info
  - CRUD + 审计日志
  - 自动锁定 (timeout)
  - 防暴力破解 (5次错误→60s锁定)

用法:
    vault = CredentialVault("./data/vault.db")
    vault.setup("master-password")  # 首次
    vault.put("openai_key", "sk-xxx", category="api_key")
    key = vault.get("openai_key")  # "sk-xxx"
    vault.lock()

Agent 集成:
    agent.vault.get_secret("github_token")
"""
from __future__ import annotations
import os, json, time, hashlib, secrets, sqlite3, threading
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class VaultCategory(Enum):
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    PERSONAL_INFO = "personal_info"


@dataclass
class AuditRecord:
    action: str
    target_key: str = ""
    timestamp: float = 0.0
    success: bool = True
    detail: str = ""

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class CredentialVault:
    PBKDF2_ITERATIONS = 100_000
    SALT_SIZE = 32
    NONCE_SIZE = 12
    AUTO_LOCK_SECONDS = 300
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 60

    def __init__(self, db_path: str = "./data/vault.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._key: Optional[bytes] = None
        self._locked = True
        self._last_access = 0.0
        self._failed = 0
        self._lockout_until = 0.0
        self._audit: list = []
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (key TEXT PRIMARY KEY, encrypted_value BLOB NOT NULL, category TEXT DEFAULT 'api_key', tags TEXT DEFAULT '[]', created_at REAL, updated_at REAL, last_accessed REAL DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value BLOB)")
            conn.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, action TEXT, target_key TEXT, success INTEGER, detail TEXT)")
            conn.commit()

    # ── Key Management ──

    def setup(self, master_password: str) -> bool:
        if not HAS_CRYPTO:
            self._add_audit("setup", success=False, detail="cryptography not installed")
            return False
        if self._read_meta("salt"):
            self._add_audit("setup", success=False, detail="already initialized")
            return False
        salt = secrets.token_bytes(self.SALT_SIZE)
        self._key = self._derive_key(master_password, salt)
        self._write_meta("salt", salt)
        # Store verification blob so unlock() can verify password
        verify_blob = self._encrypt("VAULT_VERIFY_OK")
        self._write_meta("verify", verify_blob)
        self._locked = False
        self._last_access = time.time()
        self._add_audit("setup", success=True, detail="vault initialized")
        return True

    def unlock(self, master_password: str) -> bool:
        now = time.time()
        if now < self._lockout_until:
            self._add_audit("unlock", success=False, detail=f"lockout {int(self._lockout_until-now)}s")
            return False
        if not HAS_CRYPTO:
            self._add_audit("unlock", success=False, detail="crypto not installed")
            return False
        salt = self._read_meta("salt")
        if not salt:
            self._add_audit("unlock", success=False, detail="not initialized")
            return False
        key = self._derive_key(master_password, salt)
        # Verify password by decrypting the stored verification blob
        verify_blob = self._read_meta("verify")
        if verify_blob:
            try:
                plain = AESGCM(key).decrypt(verify_blob[:self.NONCE_SIZE], verify_blob[self.NONCE_SIZE:], None)
                if plain != b"VAULT_VERIFY_OK":
                    raise ValueError("bad password")
            except Exception:
                self._failed += 1
                if self._failed >= self.MAX_FAILED_ATTEMPTS:
                    self._lockout_until = now + self.LOCKOUT_SECONDS
                    self._failed = 0
                self._add_audit("failed_unlock", success=False, detail=f"attempt {self._failed}")
                return False
        self._key = key
        self._locked = False
        self._failed = 0
        self._last_access = now
        self._add_audit("unlock", success=True)
        return True

    def lock(self):
        self._key = None
        self._locked = True
        self._add_audit("lock")

    @property
    def is_locked(self) -> bool:
        return self._locked

    @property
    def is_unlocked(self) -> bool:
        return not self._locked

    def _check_autolock(self):
        if not self._locked and self.AUTO_LOCK_SECONDS > 0 and time.time() - self._last_access > self.AUTO_LOCK_SECONDS:
            self.lock()

    def _touch(self):
        self._last_access = time.time()

    # ── CRUD ──

    def put(self, key: str, value: str, category: str = "api_key", tags: list = None) -> bool:
        if self._locked or not self._key:
            return False
        self._check_autolock()
        if self._locked:
            return False
        encrypted = self._encrypt(value)
        now = time.time()
        tags_json = json.dumps(tags or [])
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute("INSERT OR REPLACE INTO vault (key, encrypted_value, category, tags, created_at, updated_at) VALUES (?,?,?,?, COALESCE((SELECT created_at FROM vault WHERE key=?),?), ?)",
                             (key, encrypted, category, tags_json, key, now, now))
                conn.commit()
        except Exception as e:
            self._add_audit("put", key, success=False, detail=str(e))
            return False
        self._touch()
        self._add_audit("put", key, success=True, detail=category)
        return True

    def get(self, key: str) -> Optional[str]:
        if self._locked or not self._key:
            return None
        self._check_autolock()
        if self._locked:
            return None
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute("SELECT encrypted_value FROM vault WHERE key=?", (key,)).fetchone()
                if not row:
                    self._add_audit("get", key, success=False, detail="not found")
                    return None
                conn.execute("UPDATE vault SET last_accessed=? WHERE key=?", (time.time(), key))
                conn.commit()
            plaintext = self._decrypt(row[0])
            self._touch()
            self._add_audit("get", key, success=True)
            return plaintext
        except Exception as e:
            self._add_audit("get", key, success=False, detail=str(e))
            return None

    def delete(self, key: str) -> bool:
        if self._locked:
            return False
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                cursor = conn.execute("DELETE FROM vault WHERE key=?", (key,))
                conn.commit()
                deleted = cursor.rowcount > 0
        except Exception as e:
            self._add_audit("delete", key, success=False, detail=str(e))
            return False
        self._touch()
        self._add_audit("delete", key, success=deleted, detail="" if deleted else "not found")
        return deleted

    def list_keys(self, category: str = None) -> list:
        if self._locked:
            return []
        query = "SELECT key, category, tags, created_at, updated_at, last_accessed FROM vault"
        params = ()
        if category:
            query += " WHERE category=?"
            params = (category,)
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                rows = conn.execute(query, params).fetchall()
        except Exception:
            return []
        return [{"key": r[0], "category": r[1], "tags": json.loads(r[2] or "[]"),
                 "created_at": r[3], "updated_at": r[4], "last_accessed": r[5]} for r in rows]

    # ── Audit ──

    def _add_audit(self, action: str, target_key: str = "", success: bool = True, detail: str = ""):
        self._audit.append(AuditRecord(action=action, target_key=target_key, success=success, detail=detail))

    def audit_log(self, limit: int = 20) -> list:
        # Flush first to DB, then read combined
        self._flush_audit()
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute("SELECT ts, action, target_key, success, detail FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"ts": r[0], "action": r[1], "key": r[2], "ok": bool(r[3]), "detail": r[4]} for r in rows]

    def _flush_audit(self):
        if not self._audit:
            return
        with sqlite3.connect(str(self._db_path)) as conn:
            for r in self._audit:
                conn.execute("INSERT INTO audit_log (ts, action, target_key, success, detail) VALUES (?,?,?,?,?)",
                             (r.timestamp, r.action, r.target_key, int(r.success), str(r.detail)))
            conn.commit()
        self._audit.clear()

    # ── Crypto ──

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        if HAS_CRYPTO:
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=self.PBKDF2_ITERATIONS, backend=default_backend())
            return kdf.derive(password.encode())
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, self.PBKDF2_ITERATIONS, 32)

    def _encrypt(self, plaintext: str) -> bytes:
        if HAS_CRYPTO:
            nonce = secrets.token_bytes(self.NONCE_SIZE)
            return nonce + AESGCM(self._key).encrypt(nonce, plaintext.encode(), None)
        return self._key or b""

    def _decrypt(self, data: bytes) -> str:
        if HAS_CRYPTO:
            nonce, ct = data[:self.NONCE_SIZE], data[self.NONCE_SIZE:]
            return AESGCM(self._key).decrypt(nonce, ct, None).decode()
        return ""

    # ── Meta ──

    def _read_meta(self, key: str) -> Optional[bytes]:
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _write_meta(self, key: str, value: bytes):
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
            conn.commit()

    def close(self):
        self._flush_audit()
        self.lock()
