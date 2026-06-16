#!/usr/bin/env python
"""
E-012 Quick Validation → Full Auto-scale
=========================================
Phase 1: Quick (3 traps × 1 turn × 1 model) ~2min
Phase 2: Full E-012 (6 traps × 3 turns × 2 models) ~15min
Phase 3: Guard Ablation (1 trap × 8 conditions × 3 turns) ~10min
Phase 4: Scale-up (5 domains × 4 traps × 3 turns × 1 model) ~15min
"""
import json, os, sys, time
from datetime import datetime

PROJECT_ROOT = r"E:\AI_Workspace\MSS-AI\project"
os.chdir(PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "mssclaw", "core"))

from experiments.e012_plus import (
    ExperimentRunner, ExperimentAnalyzer,
    TYPE_TRAPS_V2, ABLATION_CONDITIONS,
    LARGE_SCALE_DOMAINS, LARGE_SCALE_TRAPS,
)

RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "e012_runs")
os.makedirs(RESULTS_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def run_phase1_quick() -> bool:
    """Phase 1: 快速冒烟 — 确认 Ollama 通路正常"""
    print("=" * 60)
    print("PHASE 1: QUICK SMOKE TEST")
    print("=" * 60)
    
    runner = ExperimentRunner("qwen2.5:7b")
    quick_traps = {
        "Bureaucracy_Trap": TYPE_TRAPS_V2["Bureaucracy_Trap"],
        "Dialect_Trap": TYPE_TRAPS_V2["Dialect_Trap"],
        "Nested_Logic_Trap_V2": TYPE_TRAPS_V2["Nested_Logic_Trap_V2"],
    }
    
    results = runner.run_e012_type_trap(quick_traps, turns=1)
    
    if not results:
        print("\n❌ PHASE 1 FAILED: No results from Ollama")
        return False
    
    analyzer = ExperimentAnalyzer()
    summary = analyzer.summarize_e012(results)
    
    print(f"\nQuick Results:")
    for tid, data in summary.items():
        print(f"  {tid}: η={data['avg_eta']:.3f}")
    
    # Save
    out = {
        "phase": "quick_smoke",
        "timestamp": timestamp,
        "summary": {k: {"avg_eta": v["avg_eta"], "breach_rate": v["breach_rate"]}
                     for k, v in summary.items()},
    }
    with open(os.path.join(RESULTS_DIR, f"phase1_quick_{timestamp}.json"), 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ PHASE 1 PASSED: {len(results)} turns from Ollama")
    return True


def run_phase2_full_e012():
    """Phase 2: 全量 E-012 — 6 traps × 3 turns × 2 models"""
    print("\n" + "=" * 60)
    print("PHASE 2: FULL E-012 — TYPE TRAP DEEPENING")
    print("=" * 60)
    
    models = ["qwen2.5:7b", "phi3:mini"]
    all_results = {}
    
    for model in models:
        print(f"\n--- Model: {model} ---")
        runner = ExperimentRunner(model)
        results = runner.run_e012_type_trap(TYPE_TRAPS_V2, turns=3)
        all_results[model] = results
    
    analyzer = ExperimentAnalyzer()
    report_lines = []
    
    for model, results in all_results.items():
        summary = analyzer.summarize_e012(results)
        report_lines.append(f"\n## {model}")
        report_lines.append(f"{'Trap':<25} {'Type':<20} {'Diff':>6} {'Avg η':>7} {'Breach':>7}")
        report_lines.append("-" * 70)
        for tid, data in sorted(summary.items(), key=lambda x: x[1]["avg_eta"]):
            report_lines.append(
                f"{tid:<25} {data['trap_type']:<20} "
                f"{data['difficulty']:6.2f} {data['avg_eta']:7.3f} "
                f"{data['breach_rate']:7.1%}"
            )
    
    report = "\n".join(report_lines)
    print(report)
    
    # Save
    out = {
        "phase": "full_e012",
        "timestamp": timestamp,
        "models": models,
        "summary": {
            model: analyzer.summarize_e012(all_results[model])
            for model in models
        },
    }
    with open(os.path.join(RESULTS_DIR, f"phase2_full_e012_{timestamp}.json"), 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ PHASE 2 COMPLETE")
    return all_results


def run_phase3_ablation():
    """Phase 3: 守卫消融 — Nested_Logic_Trap_V2 × 8 conditions × 3 turns"""
    print("\n" + "=" * 60)
    print("PHASE 3: GUARD NETWORK ABLATION")
    print("=" * 60)
    
    runner = ExperimentRunner("qwen2.5:7b")
    all_cond_results = {}
    
    for cond_id, cond in ABLATION_CONDITIONS.items():
        print(f"\n  [{cond_id}] {cond['desc']} (removed: {cond['remove']})")
        trap = TYPE_TRAPS_V2["Nested_Logic_Trap_V2"]
        
        guard_prompt = runner._build_guard_prompt(cond["remove"])
        results = []
        
        for t in range(3):
            resp = runner._call_ollama(guard_prompt, trap["prompt"])
            if not resp:
                print(f"    Turn {t}: ⚠️ no response")
                continue
            scores = runner._score_eta(resp, trap["trap_type"])
            avg_eta = sum(scores.values()) / max(len(scores), 1)
            from experiments.e012_plus import TurnResult
            r = TurnResult(
                trap_id="Nested_Logic_Trap_V2", turn=t,
                response=resp[:200], eta_scores=scores, avg_eta=avg_eta,
                breached=avg_eta < 0.5, condition=cond_id,
            )
            results.append(r)
            print(f"    Turn {t}: η={avg_eta:.3f} {'⚠️' if avg_eta < 0.5 else '✅'}")
        
        all_cond_results[cond_id] = results
    
    analyzer = ExperimentAnalyzer()
    summary = analyzer.summarize_e013(all_cond_results)
    
    print(f"\nAblation Results:")
    print(f"{'Condition':<25} {'Removed':<15} {'Avg η':>7} {'Breach':>7} {'Min η':>7}")
    print("-" * 70)
    for cid, data in sorted(summary.items(), key=lambda x: x[1]["avg_eta"], reverse=True):
        removed = "+".join(data["removed"]) or "none"
        print(f"{cid:<25} {removed:<15} {data['avg_eta']:7.3f} {data['breach_rate']:7.1%} {data['min_eta']:7.3f}")
    
    # Save
    out = {
        "phase": "guard_ablation",
        "timestamp": timestamp,
        "summary": {
            cid: {
                "desc": d["desc"],
                "removed": d["removed"],
                "avg_eta": d["avg_eta"],
                "breach_rate": d["breach_rate"],
            }
            for cid, d in summary.items()
        },
    }
    with open(os.path.join(RESULTS_DIR, f"phase3_ablation_{timestamp}.json"), 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ PHASE 3 COMPLETE")
    return all_cond_results


def run_phase4_scale_up():
    """Phase 4: 规模化 — 5 domains × 4 traps × 3 turns × 1 model"""
    print("\n" + "=" * 60)
    print("PHASE 4: SCALE-UP VALIDATION")
    print("=" * 60)
    
    domains = LARGE_SCALE_DOMAINS[:5]  # wuxia, scifi, historical, mythology, noir
    trap_types = LARGE_SCALE_TRAPS[:4]  # identity, nested_logic, code, math
    model = "qwen2.5:7b"
    
    runner = ExperimentRunner(model)
    all_results = []
    
    for domain in domains:
        for trap_type in trap_types:
            prompt = runner._build_scale_prompt(domain, trap_type)
            key = f"{domain}_{trap_type}"
            
            for t in range(3):
                resp = runner._call_ollama("", prompt)
                if not resp:
                    continue
                scores = runner._score_eta(resp, trap_type)
                avg_eta = sum(scores.values()) / max(len(scores), 1)
                from experiments.e012_plus import TurnResult
                r = TurnResult(
                    trap_id=key, turn=t,
                    response=resp[:200], eta_scores=scores, avg_eta=avg_eta,
                    breached=avg_eta < 0.5,
                )
                all_results.append(r)
    
    # Aggregate
    from collections import defaultdict
    by_domain = defaultdict(list)
    by_trap = defaultdict(list)
    for r in all_results:
        dom, trap = r.trap_id.split("_", 1)
        by_domain[dom].append(r.avg_eta)
        by_trap[trap].append(r.avg_eta)
    
    print(f"\nBy Domain:")
    for dom in domains:
        etas = by_domain.get(dom, [])
        if etas:
            print(f"  {dom:<15} η={sum(etas)/len(etas):.3f} (n={len(etas)})")
    
    print(f"\nBy Trap Type:")
    for trap in trap_types:
        etas = by_trap.get(trap, [])
        if etas:
            print(f"  {trap:<20} η={sum(etas)/len(etas):.3f} (n={len(etas)})")
    
    # Save
    out = {
        "phase": "scale_up",
        "timestamp": timestamp,
        "total_turns": len(all_results),
        "by_domain": {d: {"avg_eta": sum(e)/len(e), "n": len(e)} 
                       for d, e in by_domain.items() if e},
        "by_trap": {t: {"avg_eta": sum(e)/len(e), "n": len(e)} 
                     for t, e in by_trap.items() if e},
    }
    with open(os.path.join(RESULTS_DIR, f"phase4_scaleup_{timestamp}.json"), 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ PHASE 4 COMPLETE")
    return all_results


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"E-012+ EXPERIMENT RUNNER")
    print(f"Timestamp: {timestamp}")
    print(f"Results: {RESULTS_DIR}")
    print()
    
    # Phase 1: Quick smoke
    ok = run_phase1_quick()
    if not ok:
        print("\n❌ Aborting — Quick smoke failed")
        sys.exit(1)
    
    # Phase 2: Full E-012
    run_phase2_full_e012()
    
    # Phase 3: Guard ablation
    run_phase3_ablation()
    
    # Phase 4: Scale-up
    run_phase4_scale_up()
    
    print("\n" + "=" * 60)
    print("ALL PHASES COMPLETE ✅")
    print(f"Results saved to: {RESULTS_DIR}")
    print("=" * 60)
