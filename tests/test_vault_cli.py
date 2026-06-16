"""
Sprint 10: Vault CLI 测试 — 所有命令非交互模式.
"""
from __future__ import annotations
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_cli_commands():
    """Vault CLI: 全套命令非交互测试."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_toolkit import PasswordGenerator, PasswordStrength, VaultIO

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "cli_test.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999

        # Setup
        assert v.setup("cli-password")

        # Add
        assert v.put("github_token", "ghp_test123", category="token")
        assert v.put("db_password", "db-secret-456", category="password", tags=["prod"])
        assert v.put("user_email", "test@mss.ai", category="personal_info")

        # Get
        assert v.get("github_token") == "ghp_test123"
        assert v.get("db_password") == "db-secret-456"

        # List
        keys = v.list_keys()
        assert len(keys) == 3

        # List by category
        tokens = v.list_keys(category="token")
        assert len(tokens) == 1
        assert tokens[0]["key"] == "github_token"

        # Gen (generate + store)
        pwd, entropy = PasswordGenerator.generate()
        assert v.put("auto_generated_key", pwd, category="api_key", tags=["auto-generated"])
        report = PasswordStrength.assess(pwd)
        assert report.score >= 2

        # Verify gen stored correctly
        assert v.get("auto_generated_key") == pwd

        # Export JSON
        json_str = VaultIO.export_json(v)
        assert "github_token" in json_str
        assert "db_password" in json_str

        # Export CSV
        csv_str = VaultIO.export_csv(v)
        assert "github_token" in csv_str

        # Delete
        assert v.delete("user_email")
        assert v.get("user_email") is None
        assert len(v.list_keys()) == 3  # 4 - 1 deleted

        # Audit
        log = v.audit_log(limit=50)
        assert len(log) > 0
        actions = [r["action"] for r in log]
        assert "setup" in actions
        assert "put" in actions
        assert "get" in actions
        assert "delete" in actions

        v.close()


def test_cli_get_nonexistent():
    """Vault CLI: get nonexistent key returns None."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        v = CredentialVault(os.path.join(tmp, "nonexist.db"))
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        assert v.get("does_not_exist") is None
        v.close()


def test_cli_delete_nonexistent():
    """Vault CLI: delete nonexistent returns False."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        v = CredentialVault(os.path.join(tmp, "dne.db"))
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        assert not v.delete("does_not_exist")
        v.close()


def test_cli_locked_operations():
    """Vault CLI: locked vault rejects operations."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        v = CredentialVault(os.path.join(tmp, "locked.db"))
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v.put("test", "value")
        v.lock()

        # Locked: cannot get
        assert v.get("test") is None
        # Locked: cannot list
        assert v.list_keys() == []
        # Locked: cannot put
        assert not v.put("new", "val")
        # Locked: cannot delete
        assert not v.delete("test")

        v.close()
