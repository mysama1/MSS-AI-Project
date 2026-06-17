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

  init       一键环境初始化
  l2op        L2-OP v3 多Agent维度重构
  phase       Conflict Phase Engine (TypeⅡ单Agent工程解)
  topophase   Topological Phase Engine (锚点拓扑选择+θ驱动)
  adaptive    Adaptive Topological Phase Engine (活性检测+抗僵化重锚定)
  pipeline   生产级Pipeline (重试+熔断+回退+热税) [--test|--demo|<config.json>]
  experiment 实验自动化 (plan/run <假设>) [--dry]
  mcdp        Multi-Agent Conflict Resolution Protocol
  mcdp2       MCDP v0.2: N>2 Mean Field + Decentralized L2.5 Gossip
  route       场景抉择路由器 (方向1 vs 方向2)
  t2exp       TypeⅡ对照实验 (方向1-MCDP vs 方向2-相位机)
  auto-layer  自动分层 (L0->L3)
  mcp         MCP协议客户端
  defend      闭环防御管线
  vaccine     疫苗效力评估
  classify    逻辑病毒分类
  lint        Theorem L1分层检查
  escalate    开发矛盾升维器
  goal        开发目标锚定
  timer       开发热税计时器
  vault      密码管理器 (setup/add/get/list/search/serve...)
  chat       终端AI聊天 (--model qwen2.5:7b)
  serve      启动双服务 (Agent:5100 + Vault:5099)
  demo       全栈演示
  kb         知识库搜索 (618条目)
  absorb <描述>  吸收外部Agent/技能
  library     统一库管理
  models      模型目录
  health     系统健康检查
  status     全系统状态面板
  version    版本信息

示例:
  mssclaw vault setup
  mssclaw chat --model qwen2.5:7b
  mssclaw serve
  mssclaw kb "热税公式"
"""

VERSION = "0.3.10"


def cmd_vault(args_rest):
    from mssclaw.core.credential_vault import cmd_vault as _vault
    _vault(args_rest)


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
        from mssclaw.core.demo import demo
        interactive = "--no-pause" not in args_rest and "-n" not in args_rest
        demo(interactive=interactive)


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
    print(f"{117} tests | Sprints 0-{62} | GitHub: mysama1/MSS-AI-Project")


def cmd_absorb(args_rest):
    """吸收外部Agent/技能."""
    if not args_rest:
        print("mssclaw absorb <description>")
        print("  e.g. mssclaw absorb 'A code review agent for Python'")
        return

    desc = " ".join(args_rest)
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import create_backend
    from mssclaw.core.agent_absorber import AgentAbsorber
    from mssclaw.core.digest_engine import DigestEngine

    agent = MSSAgent(name="target", llm=create_backend("auto"))
    engine = DigestEngine(agent)

    print(f"Absorbing: {desc[:60]}...")
    result = engine.absorb_and_digest(desc)

    absorbed = result["absorbed"]
    report = result["report"]

    print(f"  Agent: {absorbed['name']} (role={absorbed['role']}, style={absorbed['style']})")
    print(f"  Caps: {absorbed['capabilities']}")
    print(f"  Tools: {absorbed['tools']}")
    print(f"  HeatTax: {absorbed['heat_tax']:.2f} | Delta: {absorbed['delta_min']:.2f}")
    print()
    print(f"  Applied: {report['applied']} | Conflicts: {report['conflicts']} | Skipped: {report['skipped']}")
    for d in report.get("details", []):
        print(f"    {d}")


def cmd_pipeline(args_rest):
    """生产级Pipeline执行."""
    if not args_rest:
        print("mssclaw pipeline <config.json>")
        print("  --test   运行内置生产测试")
        print("  --demo   运行示例Pipeline")
        return

    if "--test" in args_rest:
        from mssclaw.core.pipeline import StreamingPipeline, PipeNode, ProductionConfig
        config = ProductionConfig(max_retries=2, circuit_breaker_threshold=3)
        pl = StreamingPipeline("production_test", config)
        x = {"c": 0}
        def retry_node(ctx): x["c"] += 1; return {"ok": True} if x["c"] > 1 else (_ for _ in()).throw(RuntimeError("transient"))
        pl.add_node(PipeNode("init", lambda c: {"step": 1}), is_start=True)
        pl.add_node(PipeNode("retry", retry_node, retry_count=2), after=["init"])
        pl.add_node(PipeNode("final", lambda c: {"done": True}), after=["retry"])
        result = pl.run_production()
        print(pl.summary())
        print(f"\n✅ Production pipeline test: {result['nodes_executed']} nodes, CB={'TRIPPED' if result['circuit_breaker']['tripped'] else 'OK'}")
        return

    if "--demo" in args_rest:
        from mssclaw.core.pipeline import StreamingPipeline, PipeNode
        pl = StreamingPipeline("demo_pipeline")
        pl.add_node(PipeNode("fetch", lambda c: {"data": [1,2,3,4,5]}), is_start=True)
        pl.add_node(PipeNode("filter", lambda c: {"filtered": [x for x in c.get("fetch",{}).get("data",[]) if x>2]}), after=["fetch"])
        pl.add_node(PipeNode("aggregate", lambda c: {"sum": sum(c.get("filter",{}).get("filtered",[]))}), after=["filter"])
        result = pl.run_production()
        print(pl.summary())
        print(f"\n  Result: {pl.context}")
        return

    # Load from JSON config
    import json
    with open(args_rest[0], 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    from mssclaw.core.pipeline import StreamingPipeline, PipeNode, ProductionConfig
    config = ProductionConfig(**cfg.get("production", {}))
    pl = StreamingPipeline(cfg.get("name", "custom"), config)
    for node_def in cfg.get("nodes", []):
        fn_code = node_def["fn"]
        fn = eval(fn_code, {"__builtins__": {}}, {"ctx": None})
        pl.add_node(PipeNode(
            name=node_def["name"],
            fn=lambda c, f=fn: f(c),
            retry_count=node_def.get("retry", 0),
            fallback_pipe=node_def.get("fallback"),
            timeout_s=node_def.get("timeout", 30.0),
        ), is_start=node_def.get("start", False), after=node_def.get("after"))
    result = pl.run_production()
    print(pl.summary())


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
        "l2op": lambda r: __import__('mssclaw.core.l2op_v3', fromlist=['cmd_l2op']).cmd_l2op(r),
        "phase": lambda r: __import__('mssclaw.core.conflict_phase_engine', fromlist=['cmd_phase']).cmd_phase(r),
        "topophase": lambda r: __import__('mssclaw.core.topological_phase_engine', fromlist=['cmd_topophase']).cmd_topophase(r),
        "adaptive": lambda r: __import__('mssclaw.core.adaptive_topophase', fromlist=['cmd_adaptive']).cmd_adaptive(r),
        "pipeline": lambda r: __import__('mssclaw.core.pipeline', fromlist=['cmd_pipeline']).cmd_pipeline(r),
        "mcdp": lambda r: __import__('mssclaw.core.mcdp', fromlist=['cmd_mcdp']).cmd_mcdp(r),
        "mcdp2": lambda r: __import__('mssclaw.core.mcdp_v2', fromlist=['cmd_mcdp2']).cmd_mcdp2(r),
        "route": lambda r: __import__('mssclaw.core.scene_router', fromlist=['cmd_router']).cmd_router(r),
        "t2exp": lambda r: __import__('mssclaw.core.type2_control_experiment', fromlist=['cmd_t2experiment']).cmd_t2experiment(r),
        "auto-layer": lambda r: __import__('mssclaw.core.auto_layering', fromlist=['cmd_auto_layer']).cmd_auto_layer(r),
        "mcp": lambda r: __import__('mssclaw.core.mcp_client', fromlist=['cmd_mcp']).cmd_mcp(r),
        "defend": lambda r: __import__('mssclaw.core.defense_pipeline', fromlist=['cmd_defend']).cmd_defend(r),
        "vaccine": lambda r: __import__('mssclaw.core.vaccine_efficacy', fromlist=['cmd_vaccine']).cmd_vaccine(r),
        "classify": lambda r: __import__('mssclaw.core.virus_taxonomy', fromlist=['cmd_classify']).cmd_classify(r),
        "lint": lambda r: __import__('mssclaw.core.layering_linter', fromlist=['cmd_lint']).cmd_lint(r),
        "escalate": lambda r: __import__('mssclaw.core.escalator', fromlist=['cmd_escalate']).cmd_escalate(r),
        "goal": lambda r: __import__('mssclaw.core.goal_anchor', fromlist=['cmd_goal']).cmd_goal(r),
        "timer": lambda r: __import__('mssclaw.core.heat_tax_timer', fromlist=['cmd_timer']).cmd_timer(r),
        "vault": cmd_vault,
        "init": lambda r: __import__('mssclaw.core.init_env', fromlist=['init_environment']).init_environment(),
        "chat": cmd_chat,
        "serve": cmd_serve,
        "demo": cmd_demo,
        "kb": cmd_kb,
        "absorb": cmd_absorb,
        "library": lambda r: __import__('mssclaw.core.library_manager', fromlist=['cmd_library']).cmd_library(r),
        "models": lambda r: __import__('mssclaw.core.model_catalog', fromlist=['cmd_models']).cmd_models(r),
        "health": cmd_health,
        "status": cmd_status,
        "pipeline": cmd_pipeline,
        "experiment": lambda r: __import__('mssclaw.core.experiment_runner', fromlist=['main']).main(r),
        "version": cmd_version,
    }

    if cmd in commands:
        commands[cmd](rest)
    else:
        print(f"Unknown: {cmd}")
        print(USAGE)


if __name__ == "__main__":
    main()
