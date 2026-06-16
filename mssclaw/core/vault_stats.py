"""
Vault Stats — 密码卫生统计面板

一目了然:
  - 密码年龄分布
  - 分类占比
  - 来源统计
  - 强弱密码比例
  - 最近活动

用法:
    python -m mssclaw.core.vault_stats
    mss-vault stats
"""
import time
from collections import Counter, defaultdict
from typing import Dict, List


class VaultStats:
    """保险箱统计分析."""

    @classmethod
    def analyze(cls, vault) -> dict:
        """全量分析."""
        if vault.is_locked:
            return {"error": "vault locked"}

        from mssclaw.core.vault_toolkit import PasswordStrength

        entries = vault.list_keys()
        now = time.time()
        stats = {
            "total": len(entries),
            "by_category": Counter(),
            "by_source": Counter(),
            "age_distribution": {"<30d": 0, "30-90d": 0, "90d-1y": 0, ">1y": 0, "unknown": 0},
            "strength_distribution": {"weak": 0, "fair": 0, "strong": 0, "very_strong": 0, "na": 0},
            "recently_accessed": [],
            "never_accessed": [],
            "oldest_entry": None,
            "newest_entry": None,
        }

        for entry in entries:
            cat = entry.get("category", "other")
            stats["by_category"][cat] += 1

            tags = entry.get("tags", [])
            for tag in tags:
                stats["by_source"][tag] += 1

            # Age distribution
            created = entry.get("created_at", 0)
            if created:
                age_days = (now - created) / 86400
                if age_days < 30:
                    stats["age_distribution"]["<30d"] += 1
                elif age_days < 90:
                    stats["age_distribution"]["30-90d"] += 1
                elif age_days < 365:
                    stats["age_distribution"]["90d-1y"] += 1
                else:
                    stats["age_distribution"][">1y"] += 1

                if not stats["oldest_entry"] or created < stats["oldest_entry"]["created_at"]:
                    stats["oldest_entry"] = {"key": entry["key"], "created_at": created}
                if not stats["newest_entry"] or created > stats["newest_entry"]["created_at"]:
                    stats["newest_entry"] = {"key": entry["key"], "created_at": created}
            else:
                stats["age_distribution"]["unknown"] += 1

            # Strength (only for passwords)
            val = vault.get(entry["key"])
            if val and entry.get("category") == "password":
                report = PasswordStrength.assess(val)
                level = report.level.name.lower()
                stats["strength_distribution"][level] = stats["strength_distribution"].get(level, 0) + 1
            else:
                stats["strength_distribution"]["na"] += 1

            # Access tracking
            last_access = entry.get("last_accessed", 0)
            if last_access and (now - last_access) / 86400 < 7:
                stats["recently_accessed"].append(entry["key"])
            elif not last_access:
                stats["never_accessed"].append(entry["key"])

        # Sort & trim
        stats["recently_accessed"] = stats["recently_accessed"][:10]

        return stats

    @classmethod
    def strength_score(cls, vault) -> float:
        """0-100 综合强度评分."""
        stats = cls.analyze(vault)
        if "error" in stats:
            return 0

        sd = stats["strength_distribution"]
        total = max(sum(sd.values()), 1)
        weighted = (
            sd.get("weak", 0) * 0 +
            sd.get("fair", 0) * 33 +
            sd.get("strong", 0) * 66 +
            sd.get("very_strong", 0) * 100
        )
        return round(weighted / total)

    @classmethod
    def diversity_score(cls, vault) -> float:
        """0-100 分类多样性评分."""
        stats = cls.analyze(vault)
        cats = stats["by_category"]
        total = sum(cats.values())
        if total == 0:
            return 0
        # More categories = better (up to 5)
        cat_count = len(cats)
        return min(100, cat_count * 25)


def cmd_stats():
    """CLI: 显示统计面板."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_health import VaultHealth
    from pathlib import Path
    import getpass

    vault_path = Path.home() / ".mssclaw" / "vault.db"
    v = CredentialVault(str(vault_path))

    if v.is_locked:
        pw = getpass.getpass("主密码: ")
        if not v.unlock(pw):
            print("❌ 密码错误")
            return

    stats = VaultStats.analyze(v)
    health = VaultHealth.check(v)

    print("╔════════════════════════════════════╗")
    print("║     🔐  保险箱统计面板            ║")
    print("╠════════════════════════════════════╣")
    print(f"║  总条目: {stats['total']:>4}    健康: {health['grade']:>3} ({health['health_score']}/100) ║")
    print("╠════════════════════════════════════╣")

    # Category breakdown
    cats = stats["by_category"]
    icons = {"api_key": "🔌", "password": "🔑", "token": "🎫", "personal_info": "🪪"}
    for cat, count in cats.most_common():
        icon = icons.get(cat, "📌")
        bar = "█" * min(count, 20)
        print(f"║  {icon} {cat:14s} {bar} {count}")

    print("╠════════════════════════════════════╣")

    # Age
    ad = stats["age_distribution"]
    for label, count in ad.items():
        if count:
            bar = "█" * min(count * 2, 15)
            print(f"║  ⏰ {label:6s} {bar} {count}")

    print("╠════════════════════════════════════╣")

    # Strength
    sd = stats["strength_distribution"]
    total_pw = sum(v for k, v in sd.items() if k != "na")
    for level, count in sd.items():
        if count:
            bar = "█" * min(count * 3, 15)
            print(f"║  {'💪' if level in ('strong','very_strong') else '⚠️'} {level:12s} {bar} {count}")

    print("╠════════════════════════════════════╣")

    # Access
    recent = stats["recently_accessed"]
    never = stats["never_accessed"]
    print(f"║  最近使用: {len(recent)} 条           ║")
    print(f"║  从未使用: {len(never)} 条           ║")
    if recent:
        print(f"║  → {recent[0][:25]}")

    print("╚════════════════════════════════════╝")
    v.close()


if __name__ == "__main__":
    cmd_stats()
