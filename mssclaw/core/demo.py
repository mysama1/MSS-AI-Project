"""
MSSclaw Demo — 全栈端到端演示

场景: Agent 需要调用 GitHub API → 从保险箱取 token → 执行任务 → 输出健康报告

用法:
    python -m mssclaw.core.demo
    python -m mssclaw.core.demo --setup   # 首次: 初始化保险箱 + 存入模拟数据
"""
import sys
import os
import time
import json
from pathlib import Path


def demo_setup():
    """初始化演示环境."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_toolkit import PasswordGenerator
    import getpass

    vault_path = Path.home() / ".mssclaw" / "demo_vault.db"
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    v = CredentialVault(str(vault_path))
    v.AUTO_LOCK_SECONDS = 9999

    print("═══ MSSclaw Demo Setup ═══")
    pw = getpass.getpass("设置演示保险箱密码: ")
    if not v.setup(pw):
        print("❌ 初始化失败 (可能已初始化)")
        return

    # 模拟真实凭证
    v.put("github_token", "ghp_demo_tk_" + PasswordGenerator.generate()[0][:16], category="token", tags=["demo"])
    v.put("openai_key", "sk-demo-" + PasswordGenerator.generate()[0][:20], category="api_key", tags=["demo"])
    v.put("db_master", PasswordGenerator.generate()[0], category="password", tags=["demo", "prod"])
    v.put("user_email", "demo@mssclaw.ai", category="personal_info", tags=["demo"])

    # 故意加一个弱密码来展示健康检查
    v.put("old_service", "password123", category="password", tags=["demo", "legacy"])

    v.close()
    print(f"✅ 演示环境就绪: {vault_path}")
    print("   存入了 5 条模拟凭证 (含1条弱密码)")
    print()
    print("下一步: python -m mssclaw.core.demo")


def demo_run():
    """运行完整演示."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.vault_health import VaultHealth
    from mssclaw.core.vault_stats import VaultStats
    import getpass

    vault_path = Path.home() / ".mssclaw" / "demo_vault.db"
    if not vault_path.exists():
        print("❌ 演示环境未初始化, 请先运行: python -m mssclaw.core.demo --setup")
        return

    print("═══ MSSclaw 全栈演示 ═══")
    print()

    # 1. 解锁保险箱
    v = CredentialVault(str(vault_path))
    v.AUTO_LOCK_SECONDS = 9999
    if v.is_locked:
        pw = getpass.getpass("保险箱密码: ")
        if not v.unlock(pw):
            print("❌ 密码错误")
            return
    print("🔓 保险箱已解锁")
    print()

    # 2. 创建 Agent
    agent = MSSAgent(name="demo-agent", heat_tax_threshold=2.0, delta_min=0.3)
    agent.configure_vault(str(vault_path))
    agent.vault.unlock(pw)

    # 注册一些能力
    agent.cognition.register_capability("api_call", tier=3)
    agent.cognition.register_capability("data_analysis", tier=2)
    agent.cognition.anchor_identity("demo-agent", "MSS Demo Agent", strategy="virus")

    print("🤖 Agent 初始化完成")
    print(f"   能力: {agent.cognition.capability_tier_distribution()}")
    print(f"   身份稳定性: {agent.cognition.identity_stability:.2f}")
    print()

    # 3. 执行真实任务
    tasks = [
        "Generate a weekly summary report for the engineering team",
        "Check GitHub API rate limit using the stored token",
        "Audit database connection strings for security compliance",
        "Design a new microservice for user authentication",
        "Write documentation for the deployment pipeline",
    ]

    print("⚡ 开始执行任务流水线...")
    print()
    for i, task in enumerate(tasks, 1):
        t0 = time.time()
        result = agent.run(task)
        elapsed = (time.time() - t0) * 1000

        status = "✅" if not result.aborted else "🚫"
        bridge = agent.l2bridge.level.name
        delta_str = f"Δ={result.delta:.3f}" if result.delta else ""

        print(f"  {status} T{i}: {task[:50]:50s} {elapsed:5.0f}ms {delta_str} [{bridge}]")

    print()
    print(f"  总运行: {agent.run_count}  阻断: {agent.abort_count}")

    # 4. 健康报告
    print()
    print("📊 Agent 健康报告")
    report = agent.health_report()
    print(f"  L2 Bridge: {report['l2_bridge']['level']} (转换{report['l2_bridge']['transitions']}次)")
    print(f"  Δ: {report['delta'].get('current_delta', 'N/A')}")
    print(f"  记忆: {report['memory']['total']} 条 (活跃{report['memory']['active']})")
    print(f"  认知: {report['cognition']['status']}")

    # 5. 保险箱统计
    print()
    print("🔐 保险箱面板")
    stats = VaultStats.analyze(v)
    health = VaultHealth.check(v)
    print(f"  凭证: {stats['total']} 条 | 健康分: {health['health_score']}/100 ({health['grade']})")
    for cat, count in stats["by_category"].most_common():
        print(f"    {cat}: {count}")

    if health["weak_passwords"]:
        print(f"  ⚠️  弱密码: {len(health['weak_passwords'])} 条")
        for w in health["weak_passwords"][:3]:
            print(f"    - {w['key']}: {w['warning']}")

    # 6. 从保险箱取 token 的实际示例
    print()
    print("🔑 从保险箱取凭证演示")
    for key_name in ["github_token", "openai_key", "db_master", "user_email"]:
        secret = agent.get_secret(key_name)
        if secret:
            masked = secret[:6] + "***" + secret[-4:] if len(secret) > 10 else "***"
            print(f"  {key_name:20s} → {masked}")
        else:
            print(f"  {key_name:20s} → (未找到)")

    v.close()
    print()
    print("═══ 演示完成 ═══")


def main():
    if "--setup" in sys.argv:
        demo_setup()
    else:
        demo_run()


if __name__ == "__main__":
    main()
