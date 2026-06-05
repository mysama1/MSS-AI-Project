#!/usr/bin/env python3
"""
Architecture Visualization — Dual Format
  --format ascii   : 低热税, terminal-friendly, theory construction
  --format mermaid : 思维导图/脑图, rendered, engineering workflow
"""
import sys

MSS_ARCH = {
    "L5": {"name": "意义本体层 (Meaning Ontology)", "items": ["M_Φ 意义流形", "A1 意义本体公理", "自对偶性"],
           "H": ["H141", "H154", "H155", "H163", "H164", "H171", "H174", "H175", "H177"]},
    "L4": {"name": "公理化层 (Axiomatic Layer)", "items": ["A1-A6 六公理体系", "H141 硬核基准", "Z3 形式化验证"],
           "H": ["H140", "H142", "H145", "H426"]},
    "L3": {"name": "保护带层 (Protective Belt)", "items": ["W=Q/γ 逻辑功", "T_s 意义调谐度", "η_asc 升华效率"],
           "H": ["H90", "H91", "H92", "H94", "H96", "H98", "H99"]},
    "L2": {"name": "理论与方法层 (Theory & Methods)", "items": ["MSS-1~MSS-9 分类", "D5 工具链(25+)", "跨范式翻译桥"],
           "H": ["H61-H72", "H86-H89", "H148", "H156-H159", "H427"]},
    "L1": {"name": "工程落地层 (Engineering)", "items": ["MSS-Agent SDK", "认知净化工厂", "意义黑洞监测网"],
           "H": ["H73", "H76-H83", "H167-H170", "H428"]},
    "L0": {"name": "物理/社会显化层", "items": ["素数拓扑验证", "OSF预印本", "K3文明诊断"],
           "H": ["H40-H50", "H147", "H150-H153", "H160-H162", "H180-H188"]},
}

def ascii_viz():
    print("MSS Architecture — Empirical Heat Tax Theory Framework\n")
    print("  L5 ───┐  意义本体层 (M_Φ)")
    print("         │  A1 意义本体 → A2 信息切片 → A6 矛盾升维")
    print("  L4 ───┤  公理化层 (H141 六公理)")
    print("         │  A3 终极热税 dQ/dt=κ(∇φ)² | A4 随机性 Q=E[∫κ(∇δφ)²dt]")
    print("  L3 ───┤  保护带层 (W=Q/γ, T_s, η_asc)")
    print("         │  功-熵关系: W=(T_s/γ)·ΔS_T")
    print("  L2 ───┤  理论与方法层 (MSS-1~MSS-9 分类·25+工具)")
    print("         │  数学→物理→AI→文明→元理论→债务→验证→传播")
    print("  L1 ───┤  工程落地层 (SDK·净化·监测·翻译)")
    print("         │  认知净化工厂  | 意义黑洞监测 | 跨范式翻译桥")
    print("  L0 ───┘  物理/社会显化层 (验证·发表·诊断)")
    print("        素数拓扑行动 | OSF预印本 | K3文明诊断\n")
    
    # Tool chain map
    print("Tool Chain Map:")
    print("  ┌─ 审计层 ── review_runner.py / meaning_audit / dual_audit / virus_scanner")
    print("  ├─ 监测层 ── blackhole_agent / death_filter / k3_blackhole_monitor / heat_tax_profiler")
    print("  ├─ 翻译层 ── cross_paradigm_bridge.py  (20术语对)")
    print("  ├─ 分析层 ── heat_tax_scan / workspace_audit / purification_factory")
    print("  ├─ 理论层 ── taste_theory / w_logic系列(4) / kb_query.py")
    print("  └─ 验证层 ── Z3 checker / primality topology / debt_tracker.py")

def mermaid_viz():
    print("```mermaid")
    print("mindmap")
    print("  root((MSS v15.1))")
    print("    L5: Meaning Ontology")
    print("      M_Φ Manifold")
    print("      A1 Primacy")
    print("      Self-Duality")
    print("    L4: Axiomatic Layer")
    print("      A3 Heat Tax")
    print("      A4 Randomness")
    print("      A5 Gauge Field")
    print("      A6 Ascension")
    print("    L3: Protective Belt")
    print("      W = Q/γ")
    print("      T_s Tuning")
    print("      η_asc Efficiency")
    print("    L2: Theory & Methods")
    print("      MSS-1 Core (40)")
    print("      MSS-2 Math (46)")
    print("      MSS-3 Physics (79)")
    print("      MSS-4 AI (43)")
    print("      MSS-5 Civilization (111)")
    print("      MSS-6 Meta (63)")
    print("      MSS-7 Debt (2)")
    print("      MSS-8 Experiment (9)")
    print("      MSS-9 Communication (4)")
    print("    L1: Engineering")
    print("      SDK v0.1")
    print("      Purification Factory")
    print("      Blackhole Monitor")
    print("    L0: Manifestation")
    print("      Primality Topology")
    print("      OSF Preprints")
    print("      K3 Diagnostics")
    print("```")
    
    # Engineering workflow mindmap
    print("\n```mermaid")
    print("graph TD")
    print("  KB[(Knowledge Base<br/>327 H-entries)] --> Q[Query Engine<br/>kb_query.py]")
    print("  KB --> L[List Engine<br/>kb_list.py]")
    print("  KB --> G[Grade Filter<br/>grade_query.py]")
    print("  TB[(Task Bar<br/>55 tasks)] --> TS[Task Snapshot<br/>task_snapshot.py]")
    print("  MEM[(Memory Files)] --> DT[Debt Tracker<br/>debt_tracker.py]")
    print("  Q --> R[Research Map<br/>research_map.py]")
    print("  L --> R")
    print("  G --> R")
    print("  TS --> R")
    print("  DT --> R")
    print("  R --> ARCH[Architecture Viz<br/>arch_viz.py]")
    print("```")

def domain_map():
    """MSS细分领域地图 — 标注完成/待攻克"""
    print("MSS Domain Map — Completion Status\n")
    
    domains = [
        ("MSS-1 核心公理",     "✅", "A1-A6 locked, H141 authoritative"),
        ("MSS-2 数学形式化",   "🔄", "Riemann (H426-H428), Collatz (D5-033), Z3 (70/70)"),
        ("MSS-2 朗兰兹统一",   "⚠️", "Directional, not yet formalized"),
        ("MSS-2 意义数学",     "⚠️", "Grammar defined, no engine yet"),
        ("MSS-3 物理宇宙学",   "🔄", "TD-02 engineering-verified, preprint drafted"),
        ("MSS-3 量子引力融合", "⚠️", "Not started"),
        ("MSS-4 智能与工程",   "🔄", "SDK v0.1, purification factory, monitor network"),
        ("MSS-4 密码学抗量",   "⚠️", "T_c=10.2 theoretical, no prototype"),
        ("MSS-5 文明诊断",     "✅", "K3 blackhole detector, meaning-blackhole model"),
        ("MSS-5 文明治疗",     "⚠️", "Not started"),
        ("MSS-6 方法工具链",   "✅", "25+ tools, all verified"),
        ("MSS-6 KB 管理",      "✅", "Dewey classification, integrity check, auto-archive"),
        ("MSS-7 理论债务",     "🔄", "TD-MATH-01 repaid, TD-02 repaid, remaining tracked"),
        ("MSS-8 素数拓扑",     "🔄", "Days 1-2 complete, Days 3-14 pending"),
        ("MSS-8 数字沙盒",     "⚠️", "1D prototype, no 3D"),
        ("MSS-9 跨范式传播",   "🔄", "Cross-paradigm bridge, naming standard locked"),
        ("MSS-9 学术发表",     "🔄", "OSF x2 published, arXiv pending"),
    ]
    
    for domain, status, note in domains:
        bar = "█" * (3 if status == "✅" else (2 if status == "🔄" else 1))
        print(f"  {status} {domain:<22s} {bar} {note}")

if __name__ == "__main__":
    fmt = "ascii"
    for arg in sys.argv[1:]:
        if arg.startswith("--format="):
            fmt = arg.split("=")[1]
    
    if fmt == "mermaid":
        print("--- Mermaid Architecture (思维导图) ---\n")
        mermaid_viz()
    elif fmt == "ascii":
        ascii_viz()
    elif fmt == "domain":
        domain_map()
    elif fmt == "all":
        ascii_viz()
        print("\n" + "="*70 + "\n")
        domain_map()
    else:
        ascii_viz()