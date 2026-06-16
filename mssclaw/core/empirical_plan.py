"""
η Framework Empirical Validation — Phased Plan

Status: PLANNED | 4 phases | Estimated 2-4 weeks casual pace
Goal: Validate all 12 gap closures against real multi-model data.

Phase dependencies: P1→P2→P3→P4 (linear, each phase produces data for the next)
"""

phases = {
    "E1": {
        "name": "Single-Model Calibration (qwen2.5:7b)",
        "goal": "Validate φ_critical, breach detection, COARSE/FINE tax on one model",
        "duration": "2-3 sessions",
        "tasks": [
            "Build automated test harness: DTSS params -> Ollama chat -> eta scoring",
            "Run 3 DTSS configs (optimal/medium/pathological) x 30 turns each",
            "Calibrate φ_critical from real breach events",
            "Compare predicted vs observed eta degradation rate",
            "Run COARSE heat tax on each turn, check L1/L2 tax correlation with eta drop",
            "Output: E1_calibration_results.json",
        ],
        "dependencies": [],
        "deliverable": "Confirms: phi_critical model accuracy, tax-eta correlation on qwen7b",
    },
    "E2": {
        "name": "Cross-Model Breach Spectrum",
        "goal": "Validate breach window, dual penalty, L3+L4 ordering across models",
        "duration": "3-4 sessions",
        "tasks": [
            "Extend harness to support qwen2.5:0.5b, phi-3-mini, deepseek-r1:8b",
            "Run 3 guard configs (baseline/L3-off/L3+L4-off) x 4 models x 20 turns",
            "Fit per-model guard network alpha/beta coefficients",
            "Validate breach window hypothesis (50-120 effective words)",
            "Validate dual penalty: positive+negative vs positive-only vs negative-only",
            "Rank model fragility: build fragility_index = f(alpha_L3, alpha_L4, beta)",
            "Output: E2_cross_model_breach.json",
        ],
        "dependencies": ["E1"],
        "deliverable": "Per-model guard lethality profiles + fragility ranking",
    },
    "E3": {
        "name": "Meaning Character Ablation Study",
        "goal": "Validate that removing core meaning chars degrades η predictably",
        "duration": "2-3 sessions",
        "tasks": [
            "Extract top-100 meaning chars from real conversation corpus",
            "Build 5 ablation levels (100%, 75%, 50%, 25%, 0% guard chars retained)",
            "Run each ablation level x qwen2.5:7b x 20 turns",
            "Measure η drop rate vs guard set retention ratio",
            "Fit η(char_retention) = η_0 * retention^gamma",
            "Validate guard set coverage claim (91.3% signif at 17 chars)",
            "Output: E3_ablation_results.json",
        ],
        "dependencies": ["E1"],
        "deliverable": "Empirical meaning character significance ranking",
    },
    "E4": {
        "name": "Full Pipeline Integration & Paper Data",
        "goal": "End-to-end automated pipeline + paper-ready result tables",
        "duration": "3-4 sessions",
        "tasks": [
            "Unify E1-E3 harness into single CLI: mss-validate --phase all",
            "Run full pipeline on all 4 models automatically",
            "Generate result tables: per-model eta, breach rate, fragility, ablation curves",
            "Produce consolidated E4_full_results.json",
            "Draft empirical validation section for paper",
            "KB entries: H600-H609 (empirical results + per-model profiles)",
            "Output: paper/empirical_validation.tex or .md",
        ],
        "dependencies": ["E2", "E3"],
        "deliverable": "Paper-ready empirical data + automated validation pipeline",
    },
}

# ═══════════════════════════════════════════════════════
# Technical spec for E1 harness
# ═══════════════════════════════════════════════════════

harness_spec = {
    "E1_harness": {
        "path": "mssclaw/core/empirical_harness.py",
        "interface": {
            "class": "EmpiricalValidator",
            "methods": [
                "run_single_config(model, dtss_params, n_turns, prompt_template) -> TurnResults[]",
                "run_config_sweep(model, configs[]) -> SweepResults",
                "calibrate_phi_critical(results) -> float",
                "compare_predicted_vs_observed(results, model) -> FitReport",
            ],
        },
        "ollama_integration": {
            "endpoint": "http://localhost:11434/api/chat",
            "models": ["qwen2.5:7b", "qwen2.5:0.5b", "phi-3-mini", "deepseek-r1:8b"],
            "timeout": 120,
        },
        "scoring": {
            "uses": ["eta_calibration.py", "heat_tax.py", "guard_network.py"],
            "per_turn": ["D1-D5 dimensions", "eta_overall", "L1-L2 heat tax", "breach flag"],
        },
    },
}

# ═══════════════════════════════════════════════════════
# Execution: write to task_bar
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    print(json.dumps({"phases": phases, "harness_spec": harness_spec}, ensure_ascii=False, indent=2))
    print("\nWrite to task_bar.json with ---> eta_empirical:E1-E4")
