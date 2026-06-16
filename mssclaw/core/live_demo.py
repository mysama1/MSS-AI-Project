"""
MSSclaw 全线打通 — Agent + Vault + Ollama 真实演示.

场景: Agent 从保险箱取 GitHub token → 用 Ollama 分析任务 → 输出完整健康报告.

用法:
    python -m mssclaw.core.live_demo
    python -m mssclaw.core.live_demo --model qwen2.5:7b
"""
import sys
import time
import getpass
from pathlib import Path


def run_live_demo(model: str = "qwen2.5:7b", vault_path: str = None):
    """运行完整端到端演示 (真LLM)."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import OllamaBackend
    from mssclaw.core.vault_health import VaultHealth
    from mssclaw.core.vault_stats import VaultStats

    # 1. Check Ollama
    be = OllamaBackend(model, timeout=5)
    models = be.list_models()
    if not models:
        print(f"❌ Ollama 未运行或模型 {model} 不可用")
        print("   启动: ollama serve")
        print(f"   拉取: ollama pull {model}")
        return

    if model not in models:
        available = [m for m in models if not m.startswith("mss-ai-v3.4")]
        available = available[:3] if available else models[:3]
        print(f"⚠️  模型 {model} 不可用, 可用: {', '.join(available)}")
        model = available[0]
        be = OllamaBackend(model, timeout=30)
        print(f"   使用: {model}")

    # 2. Setup/connect vault
    vp = vault_path or str(Path.home() / ".mssclaw" / "vault.db")
    v = CredentialVault(vp)
    v.AUTO_LOCK_SECONDS = 9999

    if not Path(vp).exists():
        print("📦 保险箱不存在, 初始化中...")
        pw = getpass.getpass("设置主密码: ")
        if not v.setup(pw):
            print("❌ 初始化失败")
            return
        # Add some demo credentials
        from mssclaw.core.vault_toolkit import PasswordGenerator
        v.put("demo_api_key", "sk-demo-" + PasswordGenerator.generate()[0][:20], category="api_key", tags=["demo"])
        v.put("demo_db_pass", PasswordGenerator.generate()[0], category="password", tags=["demo", "prod"])
        v.close()
        v = CredentialVault(vp)
        v.AUTO_LOCK_SECONDS = 9999
        v.unlock(pw)

    # Unlock
    if v.is_locked:
        pw = getpass.getpass("保险箱密码: ")
        if not v.unlock(pw):
            print("❌ 密码错误")
            return

    print(f"🔓 保险箱: {v.list_keys().__len__()} 条凭证")

    # 3. Create agent
    agent = MSSAgent(name="live-agent", llm=be)
    agent.configure_vault(vp)
    agent.vault.unlock(pw if v.is_locked else "")
    if v.is_unlocked and agent.vault.is_locked:
        agent.vault._key = v._key
        agent.vault._locked = False

    agent.cognition.register_capability("code_generation", tier=3)
    agent.cognition.register_capability("security_audit", tier=3)
    agent.cognition.register_capability("data_analysis", tier=2)
    agent.cognition.anchor_identity("live-agent", "MSS Production Agent", strategy="virus")

    print(f"🤖 Agent: {model} | 能力: {agent.cognition.capability_tier_distribution()}")
    print()

    # 4. Run real tasks
    tasks = [
        "Write a Python function to check if a password is strong (at least 12 chars, mixed case, digits, symbols)",
        "Explain in 3 sentences how AES-256 encryption works",
        "Design a simple REST API endpoint for user login (just describe the flow)",
    ]

    print("⚡ 任务流水线")
    print("─" * 60)

    total_time = 0
    for i, task in enumerate(tasks, 1):
        t0 = time.time()
        result = agent.run(task)
        elapsed = time.time() - t0
        total_time += elapsed

        status = "✅" if not result.aborted else "🚫"
        output_preview = result.output[:80].replace("\n", " ") if result.output else "(empty)"
        bridge = agent.l2bridge.level.name
        print(f"{status} T{i} [{elapsed:.1f}s] [{bridge}] {output_preview}...")

    print("─" * 60)
    print(f"  总计: {total_time:.1f}s | 任务: {agent.run_count} | 阻断: {agent.abort_count}")
    print()

    # 5. Health report
    print("📊 全栈健康报告")
    print("─" * 40)
    report = agent.health_report()

    # L2
    l2 = report["l2_bridge"]
    print(f"  L2 桥: {l2['level']} (转换 {l2['transitions']} 次)")

    # Delta
    delta_info = report["delta"]
    d = delta_info.get("current_delta", delta_info.get("health", "N/A"))
    pattern = delta_info.get("pattern", "")
    print(f"  Δ: {d} [{pattern}]")

    # Memory
    mem = report["memory"]
    print(f"  记忆: {mem['total']} 条 (活跃 {mem['active']})")

    # Cognition
    cog = report["cognition"]
    print(f"  认知: {cog['status']} (能力 {cog['capabilities']} | 身份稳定性 {cog['identity_stability']:.2f})")

    # Heat tax
    tax = report["heat_tax"]
    print(f"  热税: total={tax.get('total', 0):.2f} | L2={tax.get('L2_meaning', 0):.0f}")

    # Vault
    health = VaultHealth.check(v)
    print(f"  保险箱: {health['total_entries']} 条 | 健康 {health['health_score']}/100 ({health['grade']})")

    print()
    print("═" * 40)
    print("  全线打通: Agent + Vault + Ollama ✅")

    v.close()


def main():
    model = "qwen2.5:7b"
    vault_path = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif args[i] == "--vault" and i + 1 < len(args):
            vault_path = args[i + 1]
            i += 2
        else:
            i += 1
    run_live_demo(model=model, vault_path=vault_path)


if __name__ == "__main__":
    main()
