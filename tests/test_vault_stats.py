"""Sprint 14: Vault Stats 测试."""
from __future__ import annotations
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_vault_stats_analyze():
    """VaultStats: 全量分析."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_stats import VaultStats

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "stats.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v._auto_backup = False

        v.put("gh_token", "ghp_xxx", category="token")
        v.put("db_pass", "StrongP@ss1!", category="password")
        v.put("weak_pw", "123456", category="password")
        v.put("email_addr", "test@test.com", category="personal_info")

        stats = VaultStats.analyze(v)
        assert stats["total"] == 4
        assert stats["by_category"]["token"] == 1
        assert stats["by_category"]["password"] == 2
        assert stats["by_category"]["personal_info"] == 1

        # Strength (very_weak = common password "123456")
        weak_count = stats["strength_distribution"].get("weak", 0) + stats["strength_distribution"].get("very_weak", 0)
        assert weak_count >= 1
        assert stats["strength_distribution"]["na"] >= 2   # token + personal

        # Age
        assert stats["age_distribution"]["<30d"] >= 4

        # Access
        assert len(stats["never_accessed"]) == 4

        v.close()


def test_vault_stats_scores():
    """VaultStats: 评分."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_stats import VaultStats

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        v = CredentialVault(os.path.join(tmp, "scores.db"))
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v._auto_backup = False

        v.put("strong", "k8$QmP!xR3vL9nW@tZ5", category="password")
        strength = VaultStats.strength_score(v)
        assert strength >= 66  # very_strong → 100

        v.put("api1", "sk-abc", category="api_key")
        v.put("api2", "sk-xyz", category="api_key")
        diversity = VaultStats.diversity_score(v)
        assert diversity > 0

        v.close()


def test_vault_stats_empty():
    """VaultStats: 空保险箱."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_stats import VaultStats

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        v = CredentialVault(os.path.join(tmp, "empty.db"))
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("pw")
        v._auto_backup = False

        stats = VaultStats.analyze(v)
        assert stats["total"] == 0
        assert VaultStats.strength_score(v) == 0
        assert VaultStats.diversity_score(v) == 0

        v.close()
