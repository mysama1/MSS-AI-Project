"""
Sprint 8: Credential Vault 测试 �?加密存储 + CRUD + Agent集成 + 审计.
"""
from __future__ import annotations
import sys, os, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_vault_setup_and_unlock():
    """Vault: 初始�?+ 解锁 + 锁定."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "test_vault.db")
        vault = CredentialVault(db_path)
        vault.AUTO_LOCK_SECONDS = 9999  # don't auto-lock during test

        # Setup
        assert vault.setup("my-secret-password")
        assert vault.is_unlocked

        # Lock
        vault.lock()
        assert vault.is_locked

        # Unlock
        assert vault.unlock("my-secret-password")
        assert vault.is_unlocked

        # Wrong password
        vault.lock()
        assert not vault.unlock("wrong-password")
        assert vault.is_locked

        vault.close()


def test_vault_crud():
    """Vault: put/get/delete/list."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "test_vault.db")
        vault = CredentialVault(db_path)
        vault.AUTO_LOCK_SECONDS = 9999
        vault.setup("master123")

        # Put
        assert vault.put("github_token", "ghp_test123", category="token")
        assert vault.put("openai_key", "sk-test456", category="api_key", tags=["llm", "prod"])
        assert vault.put("user_email", "test@example.com", category="personal_info")

        # List
        keys = vault.list_keys()
        assert len(keys) == 3
        assert keys[0]["key"] in ("github_token", "openai_key", "user_email")

        # Get
        token = vault.get("github_token")
        assert token == "ghp_test123"
        key = vault.get("openai_key")
        assert key == "sk-test456"

        # Get nonexistent
        assert vault.get("nonexistent") is None

        # Delete
        assert vault.delete("user_email")
        assert vault.get("user_email") is None
        assert len(vault.list_keys()) == 2

        vault.close()


def test_vault_auto_lock():
    """Vault: 自动锁定."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "test_vault.db")
        vault = CredentialVault(db_path)
        vault.AUTO_LOCK_SECONDS = 0.001  # nearly instant lock
        vault.setup("pw")
        vault.put("test", "value")

        # Wait for auto-lock
        time.sleep(0.01)

        # Should auto-lock on next access
        result = vault.get("test")
        assert result is None  # Locked, so get returns None
        assert vault.is_locked

        vault.close()


def test_vault_brute_force_protection():
    """Vault: 连续错误密码 �?锁定时长."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "test_vault.db")
        vault = CredentialVault(db_path)
        vault.setup("correct")
        vault.put("x", "y")
        vault.lock()

        vault.MAX_FAILED_ATTEMPTS = 3
        vault.LOCKOUT_SECONDS = 0.1  # short for test

        # Fail 3 times
        for _ in range(3):
            assert not vault.unlock("wrong")

        # 4th attempt should be locked out
        assert not vault.unlock("correct")  # locked out
        assert vault.is_locked

        # Wait and retry
        time.sleep(0.2)
        assert vault.unlock("correct")
        assert vault.is_unlocked

        vault.close()


def test_vault_audit_log():
    """Vault: 审计日志."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "test_vault.db")
        vault = CredentialVault(db_path)
        vault.setup("pw")
        vault.put("k1", "v1")
        vault.get("k1")
        vault.get("k2")  # not found
        vault.lock()
        vault.unlock("wrong")  # failed
        vault.unlock("pw")     # success
        vault.delete("k1")
        vault.close()

        # Reopen and check audit
        vault2 = CredentialVault(db_path)
        log = vault2.audit_log(limit=50)
        actions = [r["action"] for r in log]
        assert "setup" in actions
        assert "put" in actions
        assert "get" in actions
        assert "lock" in actions
        assert "failed_unlock" in actions
        assert "unlock" in actions
        assert "delete" in actions
        vault2.close()


def test_vault_agent_integration():
    """Vault: Agent 集成 �?get_secret."""
    from mssclaw.core.agent import MSSAgent

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "agent_vault.db")
        vault_path = db_path

        # Pre-setup vault
        from mssclaw.core.credential_vault import CredentialVault
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("agent-password")
        v.put("api_key", "secret-123", category="api_key")
        v.close()

        # Create agent with vault
        agent = MSSAgent(name="test-agent")
        agent.configure_vault(db_path)

        # Before unlock: no secret
        assert agent.get_secret("api_key") is None

        # Unlock and get
        agent.vault.unlock("agent-password")
        secret = agent.get_secret("api_key")
        assert secret == "secret-123"

        agent.vault.close()


def test_vault_persistence_across_instances():
    """Vault: 数据持久�?�?关掉再打开还在."""
    from mssclaw.core.credential_vault import CredentialVault

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "persist.db")

        # Instance 1: write
        v1 = CredentialVault(db_path)
        v1.setup("mypw")
        v1.put("secret", "persistent-value")
        v1.close()

        # Instance 2: read
        v2 = CredentialVault(db_path)
        v2.unlock("mypw")
        assert v2.get("secret") == "persistent-value"
        v2.close()
