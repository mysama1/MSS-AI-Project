[![PyPI version](https://badge.fury.io/py/mss-agent.svg)](https://pypi.org/project/mss-agent/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20587900.svg)](https://doi.org/10.5281/zenodo.20587900)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![JOSS](https://joss.theoj.org/papers/10.21105/joss.00000/status.svg)](https://joss.theoj.org)

# MSS-Agent: Meaning-Surplus-Security Framework

**The first open-source Agent framework with built-in "meaning-field self-audit".**

`mss-agent` is a Python toolkit that implements a three-layer architecture for monitoring, constraining, and orchestrating LLM conversations. It introduces a novel cost model (Heat Tax) that distinguishes physical computation costs from logical redundancy and meaning-integrity degradation.

```bash
pip install mss-agent
```

## 🎯 What It Does

| Problem | MSS-Agent Solution |
|---------|-------------------|
| LLMs over-explain simple questions (L2 waste) | **HeatTax Accountant** — tracks and caps meaning-waste per turn |
| Conversations get stuck in repetitive loops | **Delta Protocol** — detects structural isomorphism, triggers healing |
| Multi-agent disagreements deadlock | **Elevation** — resolves conflicts by finding higher-dimensional solutions |
| Tool calls burn budget without control | **ToolBudgetGate** — auto-classifies L0/L1/L2 costs, blocks L2 waste |
| No memory of what was decided | **MemoryGuard** — auto-archives decisions, lessons, and milestones |

## 🚀 Quick Start

```python
from mss_agent import (
    MSSAgent,           # Core agent with heat-tax enforcement
    AgentConfig,        # Domain-specific presets (daily/tech/philosophy/combat)
    DeltaQuickAudit,    # Detect repetition patterns
    HeatTaxAccountant,  # Per-turn budget tracking
    AgentOrchestrator,  # Multi-agent coordination with async parallel
    ToolBudgetGate,     # Tool-call budget enforcement
    MemoryGuard,        # Decision/lesson auto-archiving
    AutoArchiver,       # KB entry diagnosis & validation
    SessionRecallSummarizer,  # Session summary generation
)

# 1. Heat-Tax: reject busywork
agent = MSSAgent(name="ReviewBot", llm=my_llm)
result = agent.run("Rewrite 'hello' in all caps")
print(result.aborted)  # → True (L2_HIGH: busywork detected)

# 2. Delta: detect repetition
auditor = DeltaQuickAudit(domain="philosophy")
result = auditor.audit(response_text, user_query)
print(f"Red count: {result.red_count}, Light: {result.light}")

# 3. Multi-agent: async parallel execution
orch = AgentOrchestrator()
orch.add_agent("SecurityBot", security_handler)
orch.add_agent("PerfBot", perf_handler)
result = await orch.run_async(ctx, OrchestratorMode.QUORUM)
```

## 📦 P0 Tool Suite (v0.3.4–0.3.7)

| Tool | Version | Function |
|------|---------|----------|
| `ToolBudgetGate` | 0.3.4 | Heat-tax budget enforcement for tool calls |
| `MemoryGuard` | 0.3.5 | Auto-archive conversation memories |
| `AutoArchiver` | 0.3.6 | KB entry auto-tagging & validation |
| `SessionRecallSummarizer` | 0.3.7 | Session summary generation |

## 📊 Architecture

```
┌─────────────────────────────────────────────┐
│  L2  ARBITRATION LAYER                      │
│  HeatTax Accountant · ToolBudgetGate        │
│  Economic decisions: stop/delegate/elevate  │
├─────────────────────────────────────────────┤
│  L1  OBSERVATION LAYER                      │
│  Delta Protocol · QuorumFast · AutoArchiver │
│  Pattern detection · Structure isomorphism  │
├─────────────────────────────────────────────┤
│  L0  EXECUTION LAYER                        │
│  MSSAgent · AgentOrchestrator · LLM handlers│
│  Token generation · Tool execution          │
└─────────────────────────────────────────────┘
```

## 📚 Documentation

- [API Reference](mss_agent/API_REFERENCE.md)
- [End-to-End Demo](mss_agent/examples/end_to_end_demo.py)
- [JOSS Paper](paper.md)
- [Wikipedia Draft](docs/wikipedia_draft.md)
- [Knowledge Base](knowledge_base/) — 591 indexed entries (H7-H597)

## 🔬 Research

This software is the implementation of the MSS (Meaning-Surplus-Security) framework,
validated through 15-round adversarial dialogue experiments. Key findings:

- **K3 weapon migration**: After 6 rounds, LLM systems begin using MSS terminology in attacks
- **Structure isomorphism**: Conversations exhibit >85% structural similarity across rounds
- **Gödel confirmation**: Self-correction limited (GPT-3.5: 81.5% detection, 26.8% correction)

**Preprint:** [Six Rounds of Warfare](https://osf.io/vha7d/) · [Zenodo](https://doi.org/10.5281/zenodo.20587900)

## 📝 Citation

If you use mss-agent in your research, please cite:

```bibtex
@software{guo_mss_agent_2026,
  author = {Guo, YinChen},
  title = {mss-agent: Meaning-Surplus-Security Framework},
  version = {0.3.7},
  doi = {10.5281/zenodo.20587900},
  url = {https://github.com/mysama1/MSS-AI-Project},
  year = {2026}
}
```

Or use the **"Cite this repository"** button on the right sidebar → (powered by [CITATION.cff](CITATION.cff)).

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — PRs welcome. All contributions are reviewed with the same three-layer quality standard applied by mss-agent itself.

## 📄 License

MIT © 2026 YinChen Guo
