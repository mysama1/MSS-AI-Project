# -*- coding: utf-8 -*-
"""Phase 1c: core/scanner/agents 文件归位 — 只搬不改逻辑"""
import shutil, os, re

SRC = r"E:\AI_Workspace\MSS-AI\project"
DST = r"E:\AI_Workspace\MSS-AI\project\mssclaw"

# Mapping: (source, dest) — only rename, no merge
MOVES = {
    # ── core/ ──
    "mss_agent/core/normative_field_v2.py": "core/normative_field.py",
    "mss_agent/core/heat_tax.py":            "core/heat_tax.py",
    "mss_agent/core/heat_tax_system.py":     "core/heat_tax_system.py",
    "mss_agent/core/heat_tax_fuse.py":       "core/heat_tax_fuse.py",
    "mss_agent/core/delta.py":               "core/delta.py",
    "mss_agent/core/delta_callback.py":      "core/delta_callback.py",
    "mss_agent/core/delta_quick_audit.py":   "core/delta_quick_audit.py",
    "mss_agent/core/guardian_engine.py":     "core/guardian.py",
    "mss_agent/core/gradient_theft_detector.py": "core/gradient_theft_detector.py",
    "mss_agent/core/cweight_gate.py":        "core/cweight_gate.py",
    "mss_agent/core/memory.py":              "core/memory.py",
    "mss_agent/core/memory_guard.py":        "core/memory_guard.py",
    "mss_agent/core/budget_allocator.py":    "core/budget.py",
    "mss_agent/core/tool_budget_gate.py":    "core/tool_budget_gate.py",
    "mss_agent/core/t_value_filter.py":      "core/t_value_filter.py",
    "mss_agent/core/molting.py":             "core/molting.py",
    "mss_agent/core/molting_cluster.py":     "core/molting_cluster.py",
    "mss_agent/core/recovery.py":            "core/recovery.py",
    "mss_agent/core/observability.py":       "core/observability.py",
    "mss_agent/core/cross_domain.py":        "core/domain.py",
    "mss_agent/core/domain_detector.py":     "core/domain_detector.py",
    "mss_agent/core/personal_norm_field.py": "core/personal.py",
    "mss_agent/core/agent.py":               "core/agent.py",
    "mss_agent/core/agent_config.py":        "core/agent_config.py",
    "mss_agent/core/agent_orchestrator.py":  "core/agent_orchestrator.py",
    "mss_agent/core/session_recall_summarizer.py": "core/session.py",
    "mss_agent/core/auto_archive.py":        "core/auto_archive.py",
    "mss_agent/core/fewshot_builder.py":     "core/fewshot.py",
    "mss_agent/core/hybrid_pipeline_demo.py": "core/hybrid_pipeline_demo.py",
    "mss_agent/protocols/quorum.py":         "core/quorum.py",

    # ── scanner/lang/ ──
    "js_scan.py":          "scanner/lang/js.py",
    "rust_scan.py":        "scanner/lang/rust.py",
    "java_cpp_scan.py":    "scanner/lang/java_cpp.py",
    "go_scan.py":          "scanner/lang/go.py",
    "php_scan.py":         "scanner/lang/php.py",
    "ruby_scan.py":        "scanner/lang/ruby.py",
    "kotlin_scan.py":      "scanner/lang/kotlin.py",
    "csharp_scan.py":      "scanner/lang/csharp.py",
    "vdp_scan.py":         "scanner/lang/python.py",

    # ── scanner/engine/ ──
    "vdp_fuzzer.py":       "scanner/engine/fuzzer.py",
    "vdp_validator.py":    "scanner/engine/validator.py",
    "vdp_precommit.py":    "scanner/engine/precommit.py",

    # ── scanner/rules/ ──
    "vdp_anchor.py":       "scanner/rules/security.py",
    "vdp_vaccine.py":      "scanner/rules/vaccine.py",
    "vdp_lexical.py":      "scanner/rules/style.py",

    # ── scanner/ ──
    "vdp_dsl.py":          "scanner/dsl.py",
    "vdp_pipeline.py":     "scanner/pipeline.py",

    # ── agents/ ──
    "mss_agent/agents/base.py":            "agents/base.py",
    "mss_agent/agents/plan_agent.py":      "agents/plan.py",
    "mss_agent/agents/audit_agent.py":     "agents/audit.py",
    "mss_agent/agents/code_agent.py":      "agents/code.py",
    "mss_agent/agents/personal_agent.py":  "agents/personal.py",
    "mss_agent/agents/kb_agent.py":        "agents/kb.py",
    "mss_agent/agents/translate_agent.py": "agents/translate.py",
    "mss_agent/agents/video_agent.py":     "agents/video.py",
    "mss_agent/agents/product_agent.py":   "agents/product.py",
}

copied = 0
skipped = 0
for src_name, dst_name in sorted(MOVES.items()):
    src = os.path.join(SRC, src_name)
    dst = os.path.join(DST, dst_name)
    if not os.path.exists(src):
        print(f"SKIP (missing): {src_name}")
        skipped += 1
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied += 1
    print(f"OK: {os.path.basename(src_name)} → {dst_name}")

print(f"\n=== Done: {copied} copied, {skipped} skipped ===")
