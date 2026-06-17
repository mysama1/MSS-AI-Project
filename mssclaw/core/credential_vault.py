"""
Credential Vault v2.0 — 场景自动匹配 · 零交互密码管理器

设计哲学（对标浏览器密码管理器）:
  - 首次 setup 设定主密码 → 从此零交互
  - 机器绑定的自动解锁: 同台机器自动解锁，换机器需重输主密码
  - 场景匹配: credentials 绑定 scenes (如 pypi_upload, github_push), 
    调用 match("pypi_upload") 自动返回匹配的凭证
  - 主密码仅用于: 换机器恢复 / 敏感类别 (sensitive)  / 手动锁定后解锁

架构:
  ┌──────────────────────────────────────────┐
  │  Vault v2.0                              │
  │  ┌────────┐  ┌──────────┐  ┌──────────┐ │
  │  │Machine │  │ Encrypted│  │ Scene    │ │
  │  │Key(自动)│→│ Vault DB │←│ Matcher  │ │
  │  └────────┘  └──────────┘  └──────────┘ │
  │                    │            │         │
  │              ┌─────▼────┐  ┌───▼───────┐ │
  │              │ get(key) │  │ match(sc) │ │
  │              └──────────┘  └───────────┘ │
  └──────────────────────────────────────────┘

用法:
    vault = CredentialVault("~/.mssclaw/vault.db")
    vault.setup("master-password")  # 仅首次
    vault.put("pypi_token", "pypi-xxx", scenes=["pypi_upload", "package_publish"])
    # 下次会话:
    vault2 = CredentialVault("~/.mssclaw/vault.db")  # 自动解锁!
    token = vault2.match("pypi_upload")  # 按场景返回凭证

Agent 集成:
    agent.vault.match("pypi_upload")  → {"pypi_token": "pypi-xxx"}
"""
from __future__ import annotations
import os, json, time, hashlib, secrets, sqlite3, platform, uuid, base64
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
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
    SENSITIVE = "sensitive"  # 需要额外验证


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
    """v2.0 密码管理器 — 场景自动匹配 + 机器绑定自动解锁."""

    PBKDF2_ITERATIONS = 100_000
    SALT_SIZE = 32
    NONCE_SIZE = 12
    AUTO_LOCK_SECONDS = 0  # v2: 不再自动锁定（对标浏览器）
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 60
    MASTER_KEY_SIZE = 32

    # ── 预设场景常量 ──
    SCENES = {
        "pypi_upload": "上传/发布 Python 包到 PyPI",
        "github_push": "推送代码到 GitHub",
        "github_api": "GitHub API 调用",
        "email_send": "发送邮件",
        "email_read": "读取邮件",
        "ollama_api": "Ollama 模型 API",
        "openai_api": "OpenAI API 调用",
        "deepseek_api": "DeepSeek API 调用",
        "cloud_upload": "云端文件上传",
        "notion_api": "Notion API 操作",
        "database": "数据库连接",
        "ssh": "SSH 远程连接",
    }

    def __init__(self, db_path: str = "./data/vault.db", auto_unlock: bool = True):
        self._db_path = Path(db_path).expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._key: Optional[bytes] = None
        self._locked = True
        self._auto_unlock = auto_unlock
        self._failed = 0
        self._lockout_until = 0.0
        self._audit: list = []
        self._init_db()

        # 自动解锁
        if auto_unlock and self.__is_initialized():
            self._try_auto_unlock()

    def _init_db(self):
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault (
                    key TEXT PRIMARY KEY,
                    encrypted_value BLOB NOT NULL,
                    category TEXT DEFAULT 'api_key',
                    scenes TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    created_at REAL,
                    updated_at REAL,
                    last_accessed REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY, 
                    value BLOB
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL, action TEXT, target_key TEXT,
                    success INTEGER, detail TEXT
                )
            """)
            conn.commit()

    def __is_initialized(self) -> bool:
        return self._read_meta("machine_salt") is not None

    # ═══════════════════════════════════════
    # 机器指纹 + 自动解锁
    # ═══════════════════════════════════════

    @staticmethod
    def _machine_fingerprint() -> str:
        """采集机器指纹: hostname + SID + 主板序列号."""
        parts = [
            platform.node(),           # 主机名
            platform.machine(),        # 架构
            os.environ.get("COMPUTERNAME", ""),
        ]
        # Windows SID
        try:
            import subprocess
            r = subprocess.run(["whoami", "/user"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith("用户") and not line.startswith("USER"):
                    parts.append(line.strip())
                    break
        except Exception:
            pass
        # 磁盘序列号
        try:
            import subprocess
            r = subprocess.run(["wmic", "diskdrive", "get", "serialnumber"],
                             capture_output=True, text=True, timeout=5)
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip() and "SerialNumber" not in l]
            if lines:
                parts.append(lines[0])
        except Exception:
            pass
        return "|".join(parts)

    def _try_auto_unlock(self) -> bool:
        """用机器指纹解密保险箱密钥 → 自动解锁."""
        enc_key = self._read_meta("encrypted_vault_key")
        machine_salt = self._read_meta("machine_salt")
        if not enc_key or not machine_salt:
            return False
        try:
            machine_kdf_key = self._derive_key_from_fingerprint(machine_salt)
            nonce = enc_key[:self.NONCE_SIZE]
            ct = enc_key[self.NONCE_SIZE:]
            self._key = AESGCM(machine_kdf_key).decrypt(nonce, ct, None)
            # 验证: 尝试解密 verify blob
            verify_blob = self._read_meta("verify")
            if verify_blob:
                nonce_v = verify_blob[:self.NONCE_SIZE]
                ct_v = verify_blob[self.NONCE_SIZE:]
                plain = AESGCM(self._key).decrypt(nonce_v, ct_v, None)
                if plain != b"VAULT_VERIFY_OK":
                    self._key = None
                    return False
            self._locked = False
            self._add_audit("auto_unlock", success=True)
            return True
        except Exception:
            self._key = None
            return False

    def _derive_key_from_fingerprint(self, salt: bytes) -> bytes:
        """从机器指纹 + salt 派生密钥."""
        fp = self._machine_fingerprint()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=self.MASTER_KEY_SIZE,
            salt=salt, iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(fp.encode())

    # ═══════════════════════════════════════
    # 初始化 (仅首次)
    # ═══════════════════════════════════════

    def setup(self, master_password: str) -> bool:
        """首次设置保险箱.

        Args:
            master_password: 主密码 (用于换机器恢复或敏感操作)
        Returns:
            True 如果设置成功
        """
        if not HAS_CRYPTO:
            self._add_audit("setup", success=False, detail="cryptography not installed")
            return False
        if self.__is_initialized():
            self._add_audit("setup", success=False, detail="already initialized")
            return False

        # 1. 生成真正的保险箱密钥 (随机 32 字节)
        vault_key = secrets.token_bytes(self.MASTER_KEY_SIZE)
        self._key = vault_key

        # 2. 用机器指纹加密保险箱密钥 (用于自动解锁)
        machine_salt = secrets.token_bytes(self.SALT_SIZE)
        machine_key = self._derive_key_from_fingerprint(machine_salt)
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        encrypted_vault_key = nonce + AESGCM(machine_key).encrypt(nonce, vault_key, None)
        self._write_meta("machine_salt", machine_salt)
        self._write_meta("encrypted_vault_key", encrypted_vault_key)

        # 3. 用主密码加密保险箱密钥 (用于换机器恢复)
        pw_salt = secrets.token_bytes(self.SALT_SIZE)
        pw_key = self._derive_key(master_password, pw_salt)
        nonce2 = secrets.token_bytes(self.NONCE_SIZE)
        pw_encrypted_key = nonce2 + AESGCM(pw_key).encrypt(nonce2, vault_key, None)
        self._write_meta("pw_salt", pw_salt)
        self._write_meta("pw_encrypted_key", pw_encrypted_key)

        # 4. 验证 blob
        nonce3 = secrets.token_bytes(self.NONCE_SIZE)
        verify_blob = nonce3 + AESGCM(vault_key).encrypt(nonce3, b"VAULT_VERIFY_OK", None)
        self._write_meta("verify", verify_blob)

        self._locked = False
        self._add_audit("setup", success=True, detail="v2 auto-unlock initialized")
        return True

    # ═══════════════════════════════════════
    # 解锁 (手动 / 主密码恢复)
    # ═══════════════════════════════════════

    def unlock(self, master_password: str = None) -> bool:
        """手动解锁.

        - 不带参数: 尝试自动解锁
        - 带 master_password: 用主密码解密 (换机器恢复)
        """
        # 尝试自动解锁
        if master_password is None and self._auto_unlock:
            if self._try_auto_unlock():
                return True

        # 主密码解锁
        if master_password:
            return self._unlock_with_password(master_password)

        return False

    def _unlock_with_password(self, master_password: str) -> bool:
        """用主密码解密保险箱密钥."""
        now = time.time()
        if now < self._lockout_until:
            self._add_audit("unlock", success=False,
                           detail=f"lockout {int(self._lockout_until-now)}s")
            return False
        if not HAS_CRYPTO:
            return False

        pw_salt = self._read_meta("pw_salt")
        enc_key = self._read_meta("pw_encrypted_key")
        if not pw_salt or not enc_key:
            self._add_audit("unlock", success=False, detail="not initialized")
            return False

        try:
            pw_key = self._derive_key(master_password, pw_salt)
            nonce = enc_key[:self.NONCE_SIZE]
            ct = enc_key[self.NONCE_SIZE:]
            vault_key = AESGCM(pw_key).decrypt(nonce, ct, None)

            # 验证
            verify_blob = self._read_meta("verify")
            if verify_blob:
                nonce_v = verify_blob[:self.NONCE_SIZE]
                ct_v = verify_blob[self.NONCE_SIZE:]
                plain = AESGCM(vault_key).decrypt(nonce_v, ct_v, None)
                if plain != b"VAULT_VERIFY_OK":
                    raise ValueError("bad password")
        except Exception:
            self._failed += 1
            if self._failed >= self.MAX_FAILED_ATTEMPTS:
                self._lockout_until = now + self.LOCKOUT_SECONDS
                self._failed = 0
            self._add_audit("failed_unlock", success=False,
                           detail=f"attempt {self._failed}")
            return False

        self._key = vault_key
        self._locked = False
        self._failed = 0
        self._add_audit("unlock", success=True, detail="password")
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

    # ═══════════════════════════════════════
    # 场景匹配 (核心新功能)
    # ═══════════════════════════════════════

    def match(self, scene: str) -> Dict[str, str]:
        """按场景匹配凭证.

        类似浏览器密码管理器匹配域名:
          vault.match("pypi_upload") → {"pypi_token": "pypi-xxx"}

        Args:
            scene: 场景名 (如 pypi_upload, github_push, email_send)
        Returns:
            {key: value, ...} 匹配到的凭证字典
        """
        if self._locked:
            if self._auto_unlock and self._try_auto_unlock():
                pass
            else:
                return {}

        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                # 场景匹配: scenes 字段包含 scene 子串 或 包含 'all'
                rows = conn.execute(
                    """SELECT key, encrypted_value, scenes FROM vault 
                       WHERE scenes LIKE ? OR scenes LIKE ?""",
                    (f'%{scene}%', '%"all"%')
                ).fetchall()

            result = {}
            for row in rows:
                key, enc_val, _ = row
                try:
                    val = AESGCM(self._key).decrypt(
                        enc_val[:self.NONCE_SIZE],
                        enc_val[self.NONCE_SIZE:], None
                    ).decode()
                    result[key] = val
                    # 更新访问时间
                    with sqlite3.connect(str(self._db_path)) as conn:
                        conn.execute(
                            "UPDATE vault SET last_accessed=? WHERE key=?",
                            (time.time(), key)
                        )
                        conn.commit()
                except Exception:
                    continue

            self._add_audit("match", scene, success=len(result) > 0,
                           detail=f"{len(result)} credentials matched")
            return result
        except Exception as e:
            self._add_audit("match", scene, success=False, detail=str(e))
            return {}

    def match_one(self, scene: str) -> Optional[str]:
        """按场景匹配，返回最匹配的一个值."""
        results = self.match(scene)
        if not results:
            return None
        # 优先精确匹配
        exact_keys = []
        for k in results:
            try:
                with sqlite3.connect(str(self._db_path)) as conn:
                    row = conn.execute(
                        "SELECT scenes FROM vault WHERE key=?", (k,)
                    ).fetchone()
                if row:
                    scenes_list = json.loads(row[0])
                    if scene in scenes_list:
                        exact_keys.append(k)
            except Exception:
                pass
        if exact_keys:
            return results[exact_keys[0]]
        return list(results.values())[0]

    def put(self, key: str, value: str, category: str = "api_key",
            scenes: list = None, tags: list = None) -> bool:
        """存储凭证 + 绑定场景.

        Args:
            key: 凭证名
            value: 凭证值
            category: 分类 (api_key/password/token/personal_info/sensitive)
            scenes: 场景列表 (如 ["pypi_upload", "github_push"])
            tags: 标签
        """
        if self._locked or not self._key:
            return False

        nonce = secrets.token_bytes(self.NONCE_SIZE)
        encrypted = nonce + AESGCM(self._key).encrypt(
            nonce, value.encode(), None
        )
        now = time.time()
        scenes_json = json.dumps(scenes or ["all"])
        tags_json = json.dumps(tags or [])

        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO vault 
                       (key, encrypted_value, category, scenes, tags, created_at, updated_at)
                       VALUES (?,?,?,?,?,COALESCE((SELECT created_at FROM vault WHERE key=?),?),?)""",
                    (key, encrypted, category, scenes_json, tags_json, key, now, now)
                )
                conn.commit()
        except Exception as e:
            self._add_audit("put", key, success=False, detail=str(e))
            return False

        self._add_audit("put", key, success=True, detail=category)
        return True

    def get(self, key: str) -> Optional[str]:
        """获取单个凭证."""
        if self._locked or not self._key:
            return None
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute(
                    "SELECT encrypted_value FROM vault WHERE key=?", (key,)
                ).fetchone()
                if not row:
                    self._add_audit("get", key, success=False, detail="not found")
                    return None
                conn.execute(
                    "UPDATE vault SET last_accessed=? WHERE key=?",
                    (time.time(), key)
                )
                conn.commit()

            nonce = row[0][:self.NONCE_SIZE]
            ct = row[0][self.NONCE_SIZE:]
            plaintext = AESGCM(self._key).decrypt(nonce, ct, None).decode()
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
        self._add_audit("delete", key, success=deleted,
                        detail="" if deleted else "not found")
        return deleted

    def list_keys(self, category: str = None, scene: str = None,
                  query: str = None) -> list:
        """列出凭证."""
        if self._locked:
            return []
        conditions = []
        params = ()
        if category:
            conditions.append("category=?")
            params += (category,)
        if scene:
            conditions.append("scenes LIKE ?")
            params += (f'%{scene}%',)
        if query:
            conditions.append("(key LIKE ? OR tags LIKE ?)")
            like = f"%{query}%"
            params += (like, like)

        query_sql = "SELECT key, category, scenes, tags, created_at, updated_at, last_accessed FROM vault"
        if conditions:
            query_sql += " WHERE " + " AND ".join(conditions)
        query_sql += " ORDER BY updated_at DESC"

        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                rows = conn.execute(query_sql, params).fetchall()
        except Exception:
            return []

        return [{
            "key": r[0], "category": r[1],
            "scenes": json.loads(r[2] or "[]"),
            "tags": json.loads(r[3] or "[]"),
            "created_at": r[4], "updated_at": r[5],
            "last_accessed": r[6]
        } for r in rows]

    def search(self, query: str) -> list:
        return self.list_keys(query=query)

    def audit_log(self, limit: int = 20) -> list:
        self._flush_audit()
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT ts, action, target_key, success, detail FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{
            "ts": r[0], "action": r[1], "key": r[2],
            "ok": bool(r[3]), "detail": r[4]
        } for r in rows]

    def _flush_audit(self):
        if not self._audit:
            return
        with sqlite3.connect(str(self._db_path)) as conn:
            for r in self._audit:
                conn.execute(
                    "INSERT INTO audit_log (ts, action, target_key, success, detail) VALUES (?,?,?,?,?)",
                    (r.timestamp, r.action, r.target_key, int(r.success), str(r.detail))
                )
            conn.commit()
        self._audit.clear()

    def _add_audit(self, action: str, target_key: str = "",
                   success: bool = True, detail: str = ""):
        self._audit.append(AuditRecord(
            action=action, target_key=target_key,
            success=success, detail=detail
        ))

    # ═══════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        if HAS_CRYPTO:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(), length=self.MASTER_KEY_SIZE,
                salt=salt, iterations=self.PBKDF2_ITERATIONS,
                backend=default_backend()
            )
            return kdf.derive(password.encode())
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt,
            self.PBKDF2_ITERATIONS, self.MASTER_KEY_SIZE
        )

    def _read_meta(self, key: str) -> Optional[bytes]:
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute(
                    "SELECT value FROM meta WHERE key=?", (key,)
                ).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _write_meta(self, key: str, value: bytes):
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)",
                (key, value)
            )
            conn.commit()

    def close(self):
        self._flush_audit()
        self.lock()

    def reset(self, confirm: str = "") -> bool:
        """重置保险箱 (清空所有数据)."""
        if confirm != "YES_DELETE_ALL":
            return False
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute("DELETE FROM vault")
                conn.execute("DELETE FROM meta")
                conn.execute("DELETE FROM audit_log")
                conn.commit()
            self._key = None
            self._locked = True
            self._add_audit("reset", success=True, detail="all data cleared")
            return True
        except Exception as e:
            return False


# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

def cmd_vault(args_rest):
    """CLI: mssclaw vault"""
    vault_path = os.path.expanduser("~/.mssclaw/vault.db")

    if not args_rest or args_rest[0] == "--help":
        print("mssclaw vault — 密码管理器 v2.0 (场景自动匹配)")
        print()
        print("  管理:")
        print("    mssclaw vault init <主密码>     首次初始化")
        print("    mssclaw vault add <key> <value> [--scene S] [--cat C]")
        print("    mssclaw vault get <key>")
        print("    mssclaw vault list [--scene S]")
        print("    mssclaw vault delete <key>")
        print("    mssclaw vault delete-all        清空保险箱")
        print()
        print("  场景匹配 (核心功能):")
        print("    mssclaw vault match <scene>      按场景自动匹配凭证")
        print("    mssclaw vault match pypi_upload  返回所有 pypi 相关 token")
        print("    mssclaw vault match github_push  返回 GitHub push token")
        print()
        print("  预设场景:", ", ".join(CredentialVault.SCENES.keys()))
        print()
        print("  状态:")
        print("    mssclaw vault status             查看保险箱状态")
        print("    mssclaw vault unlock [密码]      手动解锁 (换机器时)")
        print("    mssclaw vault lock               锁定保险箱")
        return

    cmd = args_rest[0]

    if cmd == "init":
        pw = args_rest[1] if len(args_rest) > 1 else None
        if not pw:
            print("用法: mssclaw vault init <主密码>")
            return
        # 删除旧保险箱
        if os.path.exists(vault_path):
            os.remove(vault_path)
        v = CredentialVault(vault_path)
        if v.setup(pw):
            print("✅ 保险箱初始化成功 (v2.0 自动解锁)")
            print(f"   路径: {vault_path}")
            print(f"   下次打开将自动解锁，无需输入密码")
        else:
            print("❌ 初始化失败")
        v.close()

    elif cmd == "add":
        if len(args_rest) < 3:
            print("用法: mssclaw vault add <key> <value> [--scene S] [--cat C]")
            return
        key, value = args_rest[1], args_rest[2]
        scenes = ["all"]
        category = "api_key"
        rest = args_rest[3:]
        i = 0
        while i < len(rest):
            if rest[i] == "--scene" and i + 1 < len(rest):
                if scenes == ["all"]:
                    scenes = []
                scenes.append(rest[i + 1])
                i += 2
            elif rest[i] == "--cat" and i + 1 < len(rest):
                category = rest[i + 1]
                i += 2
            else:
                i += 1

        v = CredentialVault(vault_path)
        if v.is_locked:
            print("❌ 保险箱已锁定。自动解锁中...", end=" ")
            if not v._try_auto_unlock():
                print("失败。请先 mssclaw vault unlock <密码>")
                return
            print("✅")
        if v.put(key, value, category=category, scenes=scenes):
            print(f"✅ 已存储: {key} ({category})")
            print(f"   场景: {scenes}")
        else:
            print(f"❌ 存储失败: {key}")
        v.close()

    elif cmd == "get":
        if len(args_rest) < 2:
            print("用法: mssclaw vault get <key>")
            return
        v = CredentialVault(vault_path)
        val = v.get(args_rest[1])
        if val:
            print(val)
        else:
            print("未找到或已锁定")
        v.close()

    elif cmd == "match":
        if len(args_rest) < 2:
            print("用法: mssclaw vault match <scene>")
            print("预设场景:", ", ".join(CredentialVault.SCENES.keys()))
            return
        scene = args_rest[1]
        v = CredentialVault(vault_path)
        results = v.match(scene)
        if results:
            print(f"🔍 场景 '{scene}' 匹配到 {len(results)} 个凭证:")
            for k, val in results.items():
                masked = val[:8] + "..." + val[-4:] if len(val) > 16 else "***"
                print(f"  {k} = {masked}")
        else:
            print(f"❌ 场景 '{scene}' 无匹配凭证")
        v.close()

    elif cmd == "list":
        scene_filter = None
        rest = args_rest[1:]
        i = 0
        while i < len(rest):
            if rest[i] == "--scene" and i + 1 < len(rest):
                scene_filter = rest[i + 1]
                i += 2
            else:
                i += 1

        v = CredentialVault(vault_path)
        items = v.list_keys(scene=scene_filter)
        if items:
            print(f"📋 保险箱凭证 ({len(items)} 条):")
            for item in items:
                scenes_str = ", ".join(item.get("scenes", []))
                print(f"  [{item['category']}] {item['key']:30s} 场景: {scenes_str}")
        else:
            print("保险箱为空或已锁定")
        v.close()

    elif cmd == "delete":
        if len(args_rest) < 2:
            print("用法: mssclaw vault delete <key>")
            return
        v = CredentialVault(vault_path)
        if v.delete(args_rest[1]):
            print(f"✅ 已删除: {args_rest[1]}")
        else:
            print(f"❌ 删除失败: {args_rest[1]}")
        v.close()

    elif cmd == "delete-all":
        v = CredentialVault(vault_path)
        if v.reset("YES_DELETE_ALL"):
            print("✅ 保险箱已清空")
        v.close()

    elif cmd == "status":
        v = CredentialVault(vault_path, auto_unlock=False)
        exists = os.path.exists(vault_path)
        initialized = v._read_meta("machine_salt") is not None if exists else False
        print(f"  文件: {vault_path} ({'存在' if exists else '不存在'})")
        print(f"  状态: {'已初始化' if initialized else '未初始化'}")
        if initialized:
            v2 = CredentialVault(vault_path)
            locked = v2.is_locked
            print(f"  锁定: {'🔒 是' if locked else '🔓 否 (自动解锁)'}")
            if not locked:
                items = v2.list_keys()
                print(f"  凭证: {len(items)} 条")
                for item in items:
                    scenes_str = ", ".join(item.get("scenes", []))
                    print(f"    [{item['category']}] {item['key']} → {scenes_str}")
        v.close()
        if initialized:
            v2.close()

    elif cmd == "unlock":
        pw = args_rest[1] if len(args_rest) > 1 else None
        v = CredentialVault(vault_path, auto_unlock=False)
        if v.unlock(pw):
            print("✅ 已解锁")
        else:
            print("❌ 解锁失败")
        v.close()

    elif cmd == "lock":
        v = CredentialVault(vault_path, auto_unlock=False)
        v.lock()
        print("🔒 已锁定")
        v.close()

    else:
        print(f"未知命令: {cmd}")
