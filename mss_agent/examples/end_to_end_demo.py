#!/usr/bin/env python3
"""
MSS-Agent v0.3.1 — End-to-End Demo (Robust Version)

Runs all 5 core features, graceful on unimplemented API.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mss_agent import (
    MSSAgent, HeatTaxLevel,
    DeltaQuickAudit, DeltaResult,
    AgentConfig, HeatTaxAccountant,
    AgentOrchestrator,
)

def simulate_llm(prompt: str) -> str:
    if "security" in prompt.lower() or "injection" in prompt.lower():
        return "❌ CRITICAL: SQL Injection on line 45 — use parameterized queries."
    elif "loop" in prompt.lower() or "complexity" in prompt.lower():
        return "⚠️ O(n^2) loop on line 78 — use hash map for O(n)."
    return "✅ Review complete."

def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

ok_count = 0
err_count = 0

# ---- Demo 1: AgentConfig presets ----
header("Demo 1: AgentConfig Domain Presets")
try:
    for name in ['daily', 'tech', 'philosophy', 'combat']:
        config = AgentConfig.preset(name)
        print(f"  ✅ {name}: domain={config.domain}")
        ok_count += 1
except Exception as e:
    print(f"  ❌ AgentConfig failed: {e}")
    err_count += 1

# ---- Demo 2: Heat-Tax Budget ----
header("Demo 2: Heat-Tax Budget (Axiom A3)")
try:
    agent = MSSAgent(name="DemoBot", llm=simulate_llm)
    # Busywork should be rejected
    r1 = agent.run("rewrite this: 'hello'")
    if r1.aborted:
        print(f"  ✅ Short busywork rejected: {r1.reason[:80]}...")
    else:
        print(f"  ⚠️ Unexpectedly accepted busywork")
    ok_count += 1
    
    # Meaningful work should pass
    r2 = agent.run("Review this code for SQL injection vulnerabilities: query='SELECT * FROM users WHERE id=' + user_input")
    if not r2.aborted:
        print(f"  ✅ Security review passed: {r2.output[:80]}...")
    else:
        print(f"  ⚠️ Review rejected: {r2.reason}")
    ok_count += 1
except Exception as e:
    print(f"  ❌ Heat-Tax failed: {e}")
    err_count += 1

# ---- Demo 3: Delta Quick Audit ----
header("Demo 3: Delta Quick Audit (Δ Protocol Axiom A6)")
try:
    auditor = DeltaQuickAudit(domain="philosophy")
    result = auditor.audit(
        response_text="从海德格尔的存在论来看，这揭示了更深层的本体论困境...",
        user_query="帮我改一下Python配置文件里的端口号",
    )
    print(f"  ✅ Audit complete: red_count={result.red_count} light={result.light}")
    if result.red_count > 0:
        heal = auditor.heal_prompt()
        print(f"  💡 Heal prompt: {heal[:100]}...")
    ok_count += 1
except Exception as e:
    print(f"  ❌ Delta audit failed: {e}")
    err_count += 1

# ---- Demo 4: HeatTaxAccountant ----
header("Demo 4: HeatTaxAccountant (Budget Tracking)")
try:
    acc = HeatTaxAccountant(max_tokens_per_turn=1000, l2_ratio_warning=0.3)
    acc.start_turn(1)
    acc.record(HeatTaxLevel.L0_PHYSICAL, 150, "Base inference")
    acc.record(HeatTaxLevel.L1_LOGICAL, 50, "Cache miss re-processing")
    acc.record(HeatTaxLevel.L2_MEANING, 80, "Concept re-explanation overhead")
    report = acc.end_turn()
    print(f"  ✅ Turn 1: L0={report.l0_tokens} L1={report.l1_tokens} L2={report.l2_tokens}")
    print(f"     L2_ratio={report.l2_pct:.1%} budget_left={report.budget_remaining}")
    print(f"     L2_ratio={report.l2_pct:.1%} budget_left={report.budget_remaining}")
    if report.l2_ratio_warning:
        print(f"     ⚠️ L2 ratio too high (>{acc.l2_warning_threshold*100:.0f}%)")
    ok_count += 1
except Exception as e:
    print(f"  ❌ HeatTaxAccountant failed: {e}")
    err_count += 1

# ---- Demo 5: AgentOrchestrator ----
header("Demo 5: AgentOrchestrator (Multi-Agent Elevation)")
try:
    orch = AgentOrchestrator()
    # Create two agents via orchestrator
    # v0.3.2+: add_agent API
    def mock_llm(input_text, context):
        return {"verdict": "safe", "output": f"reviewed: {input_text[:50]}"}
    
    node_a = orch.add_agent("SecurityBot", mock_llm)
    node_b = orch.add_agent("PerfBot", mock_llm)
    print(f"  ✅ {len(orch.agents)} agents: {list(orch.agents.keys())}")
    print(f"  mode: {orch.mode}")
    print(f"  💡 In production: orch.run() runs all agents + elevates conflicts")
    ok_count += 1
except Exception as e:
    print(f"  ❌ Orchestrator failed: {e}")
    err_count += 1

# ---- Summary ----
header(f"SUMMARY: {ok_count} OK / {err_count} Errors")
print(f"  MSS-Agent v0.3.3 is {'✅ operational' if err_count == 0 else '⚠️ has issues'}")

if err_count == 0:
    print(f"\n  Next steps:")
    print(f"    1. Integration with real LLM (OpenAI / DeepSeek / Ollama)")
    print(f"    2. Multi-agent parallel execution via asyncio")
    print(f"    3. Custom domain configuration for your use case")
