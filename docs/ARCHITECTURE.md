# MSS-AI Architecture Map v0.3.11

> Auto-generated 2026-06-18 | 146 core modules | 50,363 lines | 76% docstring coverage

## Domain Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     MSSclaw Core (146 .py)                       │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│ Agent框架(20)│ 核心引擎(18) │ 基础设施(15) │ 工具桥接(8)        │
│ agent        │ l2op_v3      │ vault        │ tool_provider      │
│ session      │ mcdp/mcdp_v2 │ doctor       │ mcp_client         │
│ channel      │ pipeline     │ dashboard    │ mss_prompt/tactic  │
│ approval     │ phase_engine │ model_catalog│ dialog_fork        │
│ groupchat    │ scene_router │ init_env     │ tool_registry      │
│ sandbox      │ auto_layering│ library      │ advanced_tool      │
│ quorum       │ delta        │ heat_tax_tmr │ budget_gate       │
│ checkpoint   │ conflict     │ token_reg    │                    │
│ rollback     │ adaptive     │ credential   │                    │
│ orchestrator │ nash/vcg     │ deployer     │                    │
│ registry     │ type2_*      │ doctor       │                    │
│ absorber     │ agent_pipe   │ safe_run     │                    │
│ server       │ defense_pipe │              │                    │
│ config       │              │              │                    │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ 防御系统(6)  │ 知识/记忆(5) │ 审计/SE(4)   │ 理论基础(1)        │
│ virus_tax    │ conv_search  │ defer_guard  │ normative_field    │
│ vaccine      │ vector_memory│ heat_tax_self│                    │
│ escalator    │ memory_guard │ delta_audit  │                    │
│ goal_anchor  │ memory       │ hive_audit   │                    │
│ layering_lint│ consolidator │              │                    │
│ logic_virus  │              │              │                    │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ 实验/评测(4) │ VDP扫描器(3) │ 未分类(65)   │                    │
│ experiment   │ vdp_scan     │ ~50探索期模块│                    │
│ bench_lite   │ vdp_fuzzer   │ +15杂项      │                    │
│ ollama_bench │ js_scan      │              │                    │
│ perf_bench   │              │              │                    │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

## Test Coverage

| Domain | Coverage | Status |
|--------|----------|--------|
| 理论基础 | 100% (1/1) | 🟢 |
| 基础设施 | 50% (7/14) | 🟡 |
| Agent框架 | 41% (10/24) | 🟡 |
| 知识/记忆 | 40% (2/5) | 🟡 |
| 工具桥接 | 37% (3/8) | 🟡 |
| 核心引擎 | 15% (3/19) | 🔴 |
| 审计/SE | 12% (1/8) | 🔴 |
| 防御系统 | 11% (1/9) | 🔴 |
| 实验/评测 | 0% (0/5) | 🔴 |
| **Total** | **19% (28/146)** | 🔴 |

Total: 569 tests / 46 files

## Heaviest Modules

| Module | Size | Domain |
|--------|------|--------|
| memory_guard.py | 48,508 | 知识/记忆 |
| type2_control_experiment.py | 41,982 | 核心引擎 |
| normative_field.py | 38,333 | 理论基础 |
| doc_agent.py | 37,866 | Agent框架 |
| hallucination_shield.py | 35,787 | 防御系统 |

## Quality Indicators

- Docstring coverage: 76% (112/146)
- Total lines: 50,363
- Test files: 46
- Untested modules: 118 (81%)
- CLI commands: 36

## Integration Surface

```
MSS Core ──┬── skill_api (53000)  ← HTTP API gateway
            ├── blackhole_api (53001) ← CRTR monitoring
            ├── Ollama (11434)    ← Local LLM + embeddings
            ├── Gateway (52930)   ← OpenClaw bridge
            ├── LanceDB           ← Vector store
            └── Dify (port 5001)  ← Tool ecosystem (future)
```

## 未分类模块状态标注

```
🟢 stable (生产可用):        ~10 modules
🟡 experimental (实验阶段):  ~35 modules  
🔴 deprecated (待归档):      ~20 modules
```

## Key Architecture Decisions

1. **Scanner→Rule pattern** — VDP scanners (vdp_scan, js_scan, etc.) follow unified architecture
2. **Pipeline→Metrics→Alert** — All production paths end with MetricsCollector + alert integration
3. **Delta-as-condition** — Delta is not an optimization target, it's a maintenance condition (Δ > 0)
4. **Heat tax 3-tier** — L0 (physical) < L1 (logical) < L2 (meaning, 10^6x impact)
5. **VCG over pure game theory** — Externalities internalization more operable than pure Nash equilibrium
6. **Module granularity** — 146 modules is heavy; consolidation needed as domain boundaries clarify
