"""
Chrome Password Importer — 从 Chrome 导入密码到本地保险箱.

原理: Chrome 密码存储在 SQLite DB + Windows DPAPI 加密.
我们用 CryptUnprotectData 解密 → 写入 CredentialVault.

用法:
    from mssclaw.core.chrome_import import ChromeImporter
    ChromeImporter.import_to(vault)  # 一键导入

安全:
  - 仅在本地运行, 解密后的明文不入磁盘
  - DPAPI 解密 = 同一台机器同一用户才可以
  - 导入完成后自动锁定保险箱
"""
import sqlite3
import os
import json
from pathlib import Path
from typing import List, Optional


class ChromeImporter:
    """Chrome/Edge 密码导入器."""

    @classmethod
    def find_chrome_db(cls) -> Optional[str]:
        """找到 Chrome Login Data 路径."""
        paths = [
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Login Data",
            Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Login Data",
        ]
        for p in paths:
            if p.exists():
                return str(p)
        return None

    @classmethod
    def read_entries(cls, db_path: str = None) -> List[dict]:
        """读取 Chrome 密码数据库中的条目 (加密状态)."""
        if db_path is None:
            db_path = cls.find_chrome_db()
        if not db_path or not os.path.exists(db_path):
            return []

        # Copy DB to temp to avoid locking
        import shutil, tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.close()
        shutil.copy2(db_path, tmp.name)

        entries = []
        try:
            conn = sqlite3.connect(tmp.name)
            conn.text_factory = bytes  # raw bytes for encrypted fields
            rows = conn.execute(
                "SELECT origin_url, username_value, password_value, date_created FROM logins"
            ).fetchall()
            for row in rows:
                url = row[0].decode("utf-8", errors="replace") if row[0] else ""
                username = row[1].decode("utf-8", errors="replace") if row[1] else ""
                enc_pw = row[2]  # encrypted blob
                entries.append({
                    "url": url,
                    "username": username,
                    "encrypted_password": enc_pw,
                    "date_created": row[3] or 0,
                })
            conn.close()
        except Exception:
            pass
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

        return entries

    @classmethod
    def decrypt_password(cls, encrypted: bytes) -> Optional[str]:
        """用 Windows DPAPI 解密密码."""
        if not encrypted:
            return None
        try:
            import ctypes
            from ctypes import wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char)),
                ]

            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32

            data_in = DATA_BLOB()
            data_in.cbData = len(encrypted)
            data_in.pbData = ctypes.c_char_p(encrypted)

            data_out = DATA_BLOB()

            if crypt32.CryptUnprotectData(
                ctypes.byref(data_in), None, None, None, None, 0, ctypes.byref(data_out)
            ):
                result = ctypes.string_at(data_out.pbData, data_out.cbData).decode("utf-8", errors="replace")
                kernel32.LocalFree(data_out.pbData)
                return result
            return None
        except Exception:
            return None

    @classmethod
    def import_to(cls, vault, db_path: str = None, filter_url: str = None) -> int:
        """
        导入密码到保险箱.

        Args:
            vault: CredentialVault (必须已解锁)
            db_path: Chrome Login Data 路径 (None=自动查找)
            filter_url: 只导入匹配 URL 的密码 (None=全部)

        Returns:
            导入条数
        """
        if vault.is_locked:
            return -1

        entries = cls.read_entries(db_path)
        count = 0
        skipped = 0

        for entry in entries:
            url = entry["url"]
            username = entry["username"]

            if filter_url and filter_url not in url:
                continue

            password = cls.decrypt_password(entry["encrypted_password"])
            if not password:
                skipped += 1
                continue

            # Extract site name from URL for key
            site_key = cls._url_to_key(url)
            vault_key = f"{site_key}/{username}" if username else site_key

            # Avoid overwriting
            if vault.get(vault_key):
                vault_key = f"{vault_key}_{entry['date_created']}"

            vault.put(
                key=vault_key,
                value=password,
                category="password",
                tags=["imported", "chrome"],
            )
            count += 1

        return count

    @classmethod
    def _url_to_key(cls, url: str) -> str:
        """提取 URL 中的站点名作为 key."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname or url
            # Remove www.
            if host.startswith("www."):
                host = host[4:]
            return host.split(".")[0]  # "github.com" → "github"
        except Exception:
            return url[:30]


def cmd_import(filter_url: str = None):
    """CLI: 从 Chrome 导入密码."""
    from mssclaw.core.credential_vault import CredentialVault
    from pathlib import Path

    vault_path = Path.home() / ".mssclaw" / "vault.db"
    v = CredentialVault(str(vault_path))

    if v.is_locked:
        import getpass
        pw = getpass.getpass("主密码: ")
        if not v.unlock(pw):
            print("❌ 密码错误")
            return

    db = ChromeImporter.find_chrome_db()
    if not db:
        print("❌ 未找到 Chrome/Edge 密码数据库")
        return

    print(f"📂 源: {db}")
    entries = ChromeImporter.read_entries(db)
    print(f"📊 发现 {len(entries)} 条密码")

    count = ChromeImporter.import_to(v, db, filter_url)
    print(f"✅ 导入 {count} 条")
    v.close()


if __name__ == "__main__":
    import sys
    cmd_import(sys.argv[1] if len(sys.argv) > 1 else None)
