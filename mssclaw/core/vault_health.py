"""
Vault Health & Backup — 保险箱自动备份 + 安全体检

类似 1Password Watchtower:
  - 每次写入自动备份 (保留最近N份)
  - 弱密码检测
  - 重复密码检测
  - 过期密码提醒 (>90天未更新)
  - 备份恢复

用法:
    from mssclaw.core.vault_health import VaultHealth
    VaultHealth.backup(vault)
    report = VaultHealth.check(vault)
"""
from __future__ import annotations
import shutil
import time
import os
from pathlib import Path
from typing import List, Dict


class VaultHealth:
    """保险箱健康检查 + 自动备份."""

    MAX_BACKUPS = 5
    STALE_DAYS = 90  # 密码超过N天未更新视为过期

    @classmethod
    def backup(cls, vault) -> str:
        """
        备份保险箱数据库.

        每次调用在 db_path.backups/ 下创建带时间戳的副本.
        自动旋转, 保留最近 MAX_BACKUPS 份.
        返回备份路径.
        """
        db_path = Path(vault._db_path)
        if not db_path.exists():
            return ""

        backup_dir = db_path.parent / f"{db_path.name}.backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"vault_{ts}.db"

        # Flush audit before backup
        vault._flush_audit()

        shutil.copy2(str(db_path), str(backup_path))

        # Rotate old backups
        cls._rotate(backup_dir)

        return str(backup_path)

    @classmethod
    def _rotate(cls, backup_dir: Path):
        """旋转备份, 只保留最近 N 份."""
        backups = sorted(
            backup_dir.glob("vault_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[cls.MAX_BACKUPS:]:
            try:
                old.unlink()
            except Exception:
                pass

    @classmethod
    def list_backups(cls, vault) -> List[Dict]:
        """列出所有备份."""
        db_path = Path(vault._db_path)
        backup_dir = db_path.parent / f"{db_path.name}.backups"
        if not backup_dir.exists():
            return []

        backups = sorted(
            backup_dir.glob("vault_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [
            {
                "path": str(b),
                "size_kb": round(b.stat().st_size / 1024, 1),
                "time": time.strftime(
                    "%Y-%m-%d %H:%M",
                    time.localtime(b.stat().st_mtime),
                ),
            }
            for b in backups
        ]

    @classmethod
    def restore(cls, vault, backup_path: str) -> bool:
        """从备份恢复."""
        src = Path(backup_path)
        if not src.exists():
            return False

        vault.close()
        dst = Path(vault._db_path)
        shutil.copy2(str(src), str(dst))
        return True

    @classmethod
    def check(cls, vault) -> dict:
        """
        安全体检.

        返回:
          { weak_passwords, duplicate_passwords, stale_passwords, total_entries, score }
        """
        if vault.is_locked:
            return {"error": "vault locked"}

        from mssclaw.core.vault_toolkit import PasswordStrength

        entries = vault.list_keys()
        weak = []
        duplicates = cls._find_duplicates(vault, entries)
        stale = []
        now = time.time()

        for entry in entries:
            val = vault.get(entry["key"])
            if not val:
                continue

            # Weak password check (skip API keys / tokens)
            if entry["category"] in ("password",):
                report = PasswordStrength.assess(val)
                if report.score <= 1:
                    weak.append({
                        "key": entry["key"],
                        "score": report.score,
                        "warning": report.warnings[0] if report.warnings else "",
                    })

            # Stale check
            updated = entry.get("updated_at", 0) or entry.get("created_at", 0)
            if updated and (now - updated) / 86400 > cls.STALE_DAYS:
                stale.append({
                    "key": entry["key"],
                    "days_old": round((now - updated) / 86400),
                })

        total = len(entries)
        healthy = total - len(weak) - len(duplicates) - len(stale)
        score = round(healthy / max(total, 1) * 100)

        return {
            "total_entries": total,
            "weak_passwords": weak,
            "duplicate_passwords": duplicates,
            "stale_passwords": stale,
            "healthy_count": healthy,
            "health_score": score,
            "grade": cls._grade(score),
        }

    @classmethod
    def _find_duplicates(cls, vault, entries: list) -> list:
        """检测重复密码."""
        seen = {}
        duplicates = []
        for entry in entries:
            val = vault.get(entry["key"])
            if not val:
                continue
            if val in seen:
                duplicates.append({
                    "key1": seen[val],
                    "key2": entry["key"],
                    "value_hash": hash(val) & 0xFFFF,
                })
            else:
                seen[val] = entry["key"]
        return duplicates

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 90:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 30:
            return "D"
        return "F"
