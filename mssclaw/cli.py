"""
MSSclaw Unified Launcher — 一个命令管所有

用法:
    mssclaw vault     → mss-vault (密码管理)
    mssclaw chat      → 终端聊天
    mssclaw serve     → 启动 Agent + Vault 双服务
    mssclaw demo      → 全栈演示
    mssclaw kb        → 知识库搜索
    mssclaw health    → 系统健康检查
"""
import sys, os

USAGE = """mssclaw — MSS AI Framework

  vault      密码管理器 (setup/add/get/list/search/serve...)
  chat       终端AI聊天 (--model qwen2.5:7b)
  serve      启动双服务 (Agent:5100 + Vault:5099)
  demo       全栈演示
  kb         知识库搜索 (618条目)
  health     系统健康检查
  status     全系统状态面板
  version    版本信息

示例:
  mssclaw vault setup
  mssclaw chat --model qwen2.5:7b
  mssclaw serve
  mssclaw kb "热税公式"
"""

VERSION = "0.3.0"


def cmd_vault(args_rest):
    from mssclaw.core.vault_cli import main
    sys.argv = ["vault"] + args_rest
    main()


def cmd_chat(args_rest):
    from mssclaw.core.agent_chat import main
    sys.argv = ["chat"] + args_rest
    main()


def cmd_serve(args_rest):
    port_vault = 5099
    port_agent = 5100
    model = "qwen2.5:7b"
    i = 0
    while i < len(args_rest):
        if args_rest[i] == "--vault-port" and i+1 < len(args_rest):
            port_vault = int(args_rest[i+1]); i += 2
        elif args_rest[i] == "--agent-port" and i+1 < len(args_rest):
            port_agent = int(args_rest[i+1]); i += 2
        elif args_rest[i] == "--model" and i+1 < len(args_rest):
            model = args_rest[i+1]; i += 2
        else:
            i += 1

    import threading
    print(f"Starting MSS services...")
    print(f"  Vault API:  http://127.0.0.1:{port_vault}")
    print(f"  Agent API:  http://127.0.0.1:{port_agent} (model: {model})")
    if "--all" in sys.argv:
        print(f"  Chat:       mssclaw chat --model {model}")
        print(f"  Web panel:  http://127.0.0.1:{port_vault} (browser)")
    print(f"  Press Ctrl+C to stop")
    print()

    def start_vault():
        from mssclaw.core.vault_server import serve_vault
        serve_vault(port=port_vault, auth_required=False)

    def start_agent():
        from mssclaw.core.agent_server import serve_agent
        serve_agent(model=model, port=port_agent)

    t1 = threading.Thread(target=start_vault, daemon=True)
    t2 = threading.Thread(target=start_agent, daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            import time; time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


def cmd_demo(args_rest):
    if "--setup" in args_rest:
        from mssclaw.core.demo import demo_setup
        demo_setup()
    else:
        from mssclaw.core.demo import demo_run
        demo_run()


def cmd_kb(args_rest):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
    import kb_search
    if not args_rest:
        print("mssclaw kb <query>           搜索知识库")
        print("mssclaw kb --hid H593        H-ID精确查找")
        print("mssclaw kb --stats           统计")
        return
    sys.argv = ["kb_search"] + args_rest
    kb_search_argv = args_rest
    kb = kb_search.KBSearch()
    if "--stats" in kb_search_argv:
        s = kb.stats()
        print(f"KB: {s['total_entries']} entries across {len(s['by_layer'])} layers")
        for layer, count in s['by_layer'].items():
            print(f"  {layer}: {count}")
    elif "--hid" in kb_search_argv:
        idx = kb_search_argv.index("--hid")
        if idx + 1 < len(kb_search_argv):
            r = kb.get_by_hid(kb_search_argv[idx+1])
            if r:
                print(f"[{r.h_id}] {r.title}")
                print(f"  Layer: {r.layer} | File: {r.filename}")
                print(f"  {r.content[:500]}")
            else:
                print(f"H-ID {kb_search_argv[idx+1]} not found")
    else:
        query = kb_search_argv[0]
        results = kb.search(query, top_k=10)
        print(f"Results for '{query}' ({len(results)} found):\n")
        for r in results:
            print(f"  [{r.h_id}] {r.layer.split('_')[0]} score={r.score:.1f} {r.title[:70]}")
            if r.snippet:
                print(f"    ...{r.snippet[:120]}...")


def cmd_health(args_rest):
    """全系统健康报告."""
    from mssclaw.core.delta_monitor import DeltaMonitor
    from mssclaw.core.process_monitor import ProcessMonitor
    from pathlib import Path

    print("╔══════════════════════════════════╗")
    print("║   MSS System Health Report       ║")
    print("╠══════════════════════════════════╣")

    # 1. Process health
    pm = ProcessMonitor()
    pr = pm.check()
    status_icon = "🟢" if pr["status"] == "HEALTHY" else "🟡"
    print(f"║ {status_icon} 进程: {pr['total']} | 孤儿:{pr['orphans']} | "
          f"高CPU:{pr['high_cpu']} | 服务:{sum(pr['services'].values())}/3")

    # 2. Key services
    svc = pr["services"]
    for name, running in svc.items():
        icon = "✅" if running else "❌"
        print(f"║    {icon} {name}")

    # 3. Orphans
    for o in pr.get("orphan_list", [])[:3]:
        print(f"║    ⚠️  PID {o['pid']}: {o['cmd'][:40]}")

    print("╠══════════════════════════════════╣")

    # 4. Vault
    vault_path = Path.home() / ".mssclaw" / "vault.db"
    if vault_path.exists():
        size_kb = vault_path.stat().st_size / 1024
        print(f"║ 🔐 Vault: {size_kb:.0f}KB")
        # Check backups
        backup_dir = vault_path.parent / f"{vault_path.name}.backups"
        if backup_dir.exists():
            backups = list(backup_dir.glob("vault_*.db"))
            print(f"║    Backups: {len(backups)} files")
    else:
        print(f"║ 🔐 Vault: not initialized")

    # 5. Sessions
    sess_dir = Path.home() / ".mssclaw" / "sessions"
    if sess_dir.exists():
        sessions = list(sess_dir.glob("*.json"))
        if sessions:
            print(f"║ 💾 Sessions: {len(sessions)}")

    # 6. Delta
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import create_backend
    agent = MSSAgent(name="health-check", llm=create_backend("auto"))
    monitor = DeltaMonitor(agent=agent)
    health = monitor.check()
    print(f"║ 📊 Delta: {health['delta']:.3f} ({health['delta_status']})")

    print("╚══════════════════════════════════╝")

    if pr["orphans"] > 0:
        print(f"\n  ⚠️  {pr['orphans']} orphan processes. Run: mssclaw health --fix")

    if "--fix" in args_rest:
        killed = pm.kill_orphans()
        print(f"  🧹 Cleaned {killed} orphan processes")


def cmd_version(args_rest):
    print(f"MSSclaw v{VERSION}")
    print(f"{117} tests | Sprints 0-{61} | GitHub: mysama1/MSS-AI-Project")


def cmd_status(args_rest):
    """全系统状态面板."""
    from mssclaw.core.delta_monitor import DeltaMonitor
    from mssclaw.core.process_monitor import ProcessMonitor
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import create_backend
    from pathlib import Path
    import time, os

    print("╔══════════════════════════════════════════╗")
    print(f"║  MSS System Status  {time.strftime('%H:%M:%S'):>22s} ║")
    print("╠══════════════════════════════════════════╣")

    # Process
    pm = ProcessMonitor()
    pr = pm.check()
    s_icon = "🟢" if pr["status"] == "HEALTHY" else "🟡"
    print(f"║ {s_icon} Processes: {pr['total']} | Orphans: {pr['orphans']} | CPU: {pr['high_cpu']}")

    # Services
    svc = pr["services"]
    for name, running in svc.items():
        print(f"║   {'✅' if running else '❌'} {name}")

    print("╠══════════════════════════════════════════╣")

    # Vault
    vp = Path.home() / ".mssclaw" / "vault.db"
    if vp.exists():
        size = vp.stat().st_size / 1024
        bp = vp.parent / f"{vp.name}.backups"
        bu = len(list(bp.glob("vault_*.db"))) if bp.exists() else 0
        print(f"║ 🔐 Vault: {size:.0f}KB | Backups: {bu}")
    else:
        print(f"║ 🔐 Vault: not initialized")

    # Sessions
    sp = Path.home() / ".mssclaw" / "sessions"
    if sp.exists():
        ss = len(list(sp.glob("*.json")))
        if ss:
            print(f"║ 💾 Sessions: {ss}")

    # KB
    kb_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".." / "knowledge_base"
    if kb_path.exists():
        layers = [d for d in kb_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        print(f"║ 📚 KB: {len(layers)} layers")

    # Delta
    agent = MSSAgent(name="status-check", llm=create_backend("auto"))
    dm = DeltaMonitor(agent=agent)
    dh = dm.check()
    d_icon = "🟢" if dh["delta_status"] == "healthy" else "🟡"
    print(f"║ {d_icon} Delta: {dh['delta']:.3f} ({dh['delta_status']})")

    print("╠══════════════════════════════════════════╣")

    # Git
    try:
        import subprocess
        r = subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if r.stdout:
            print(f"║ 📦 Git: {r.stdout.strip()[:45]}")
    except Exception:
        pass

    print("╚══════════════════════════════════════════╝")


def main():
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        return

    cmd = args[0]
    rest = args[1:]

    commands = {
        "vault": cmd_vault,
        "chat": cmd_chat,
        "serve": cmd_serve,
        "demo": cmd_demo,
        "kb": cmd_kb,
        "health": cmd_health,
        "status": cmd_status,
        "version": cmd_version,
    }

    if cmd in commands:
        commands[cmd](rest)
    else:
        print(f"Unknown: {cmd}")
        print(USAGE)


if __name__ == "__main__":
    main()
