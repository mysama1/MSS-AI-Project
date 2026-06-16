"""Sprint 13: Vault Health & Backup 测试."""
from __future__ import annotations
import sys, os, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_vault_backup_and_rotate():
    """VaultHealth: 备份 + 旋转."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_health import VaultHealth

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "health_test.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")

        v._auto_backup = False  # Don't auto-backup during test
        v.put("test1", "value1")
        v.put("test2", "value2")

        # Manual backup
        path1 = VaultHealth.backup(v)
        assert path1
        assert os.path.exists(path1)

        # Another backup (wait 1s for different timestamp)
        time.sleep(1.1)
        path2 = VaultHealth.backup(v)
        assert path2 != path1

        # List backups
        backups = VaultHealth.list_backups(v)
        assert len(backups) >= 2

        v.close()


def test_vault_health_check():
    """VaultHealth: 安全体检."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_health import VaultHealth

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "health2.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v._auto_backup = False

        v.put("strong_key", "k8$QmP!xR3vL9nW@tZ5", category="password")
        v.put("weak_key", "password123", category="password")
        v.put("api_key", "sk-abc123xyz", category="api_key")

        report = VaultHealth.check(v)
        assert report["total_entries"] == 3
        assert "weak_passwords" in report
        assert "duplicate_passwords" in report
        assert "stale_passwords" in report
        assert "health_score" in report
        assert "grade" in report

        # weak_key should be flagged
        weak_keys = [w["key"] for w in report["weak_passwords"]]
        assert "weak_key" in weak_keys

        # strong_key should NOT be flagged
        assert "strong_key" not in weak_keys

        v.close()


def test_vault_duplicate_detection():
    """VaultHealth: 重复密码检测."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_health import VaultHealth

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "dup.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v._auto_backup = False

        # Same password for two entries
        v.put("github", "same-password-123", category="password")
        v.put("gitlab", "same-password-123", category="password")
        v.put("unique", "different-one", category="password")

        report = VaultHealth.check(v)
        assert len(report["duplicate_passwords"]) >= 1

        v.close()


def test_vault_auto_backup():
    """Vault: put() 自动备份."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_health import VaultHealth

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "auto.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v._auto_backup = True

        v.put("test", "val")
        backups = VaultHealth.list_backups(v)
        assert len(backups) >= 1

        # Multiple writes should produce multiple backups (up to MAX)
        for i in range(5):
            v.put(f"key_{i}", f"val_{i}")
        backups = VaultHealth.list_backups(v)
        assert len(backups) <= VaultHealth.MAX_BACKUPS + 2  # +2 for initial

        v.close()
