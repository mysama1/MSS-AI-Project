"""Sprint 15: Demo 测试 — 全栈端到端."""
from __future__ import annotations
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_demo_full_flow():
    """Demo: 完整流程 — setup + agent + vault + stats + health."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.vault_health import VaultHealth
    from mssclaw.core.vault_stats import VaultStats
    from mssclaw.core.vault_toolkit import PasswordGenerator

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        # Setup vault
        db_path = os.path.join(tmp, "demo.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("demo-pass")
        v._auto_backup = False

        # Store demo credentials
        pwd, _ = PasswordGenerator.generate()
        v.put("github_token", pwd, category="token", tags=["demo"])
        v.put("openai_key", "sk-demo-" + PasswordGenerator.generate()[0][:20], category="api_key")
        v.put("db_master", PasswordGenerator.generate()[0], category="password", tags=["prod"])
        v.put("user_email", "demo@mssclaw.ai", category="personal_info")
        v.close()

        # Create agent with vault
        agent = MSSAgent(name="demo-agent")
        agent.configure_vault(db_path)

        # Unlock vault
        agent.vault.unlock("demo-pass")

        # Register capabilities
        agent.cognition.register_capability("api_call", tier=3)
        agent.cognition.register_capability("data_analysis", tier=2)
        agent.cognition.anchor_identity("demo", "Demo Agent", strategy="virus")

        # Run tasks
        tasks = [
            "Generate a weekly summary report",
            "Check API rate limit",
            "Audit database connections",
            "Design a microservice",
            "Write deployment docs",
        ]
        for task in tasks:
            result = agent.run(task)
            assert result.success
            assert not result.aborted

        assert agent.run_count == 5

        # Health report
        report = agent.health_report()
        assert report["l2_bridge"]["level"] in ("STABLE", "CAUTION")
        assert report["cognition"]["status"] == "healthy"

        # Vault stats
        stats = VaultStats.analyze(agent.vault)
        assert stats["total"] >= 4

        # Vault health
        health = VaultHealth.check(agent.vault)
        assert health["total_entries"] >= 4
        assert "grade" in health

        # Get secrets
        token = agent.get_secret("github_token")
        assert token is not None

        agent.vault.close()


def test_demo_vault_agent_secrets():
    """Demo: Agent 获取所有类型的 secret."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.agent import MSSAgent

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "secrets.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v._auto_backup = False

        v.put("token", "ghp_test123", category="token")
        v.put("key", "sk-test456", category="api_key")
        v.put("pass", "secret789", category="password")
        v.put("email", "user@test.com", category="personal_info")
        v.close()

        agent = MSSAgent(name="secret-test")
        agent.configure_vault(db_path)
        agent.vault.unlock("pw")

        assert agent.get_secret("token") == "ghp_test123"
        assert agent.get_secret("key") == "sk-test456"
        assert agent.get_secret("pass") == "secret789"
        assert agent.get_secret("email") == "user@test.com"
        assert agent.get_secret("nonexistent") is None

        agent.vault.close()
