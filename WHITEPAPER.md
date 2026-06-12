# MSS-Agent Technical Whitepaper v1.1

**Version:** 1.1 | **Date:** 2026-06-08 | **Status:** Published (JOSS Under Review)

---

## Abstract

`mss-agent` is an open-source Python framework implementing the Meaning-Surplus-Security (MSS) three-layer architecture for monitoring, constraining, and orchestrating large language model (LLM) conversations. The framework introduces a novel cost model distinguishing physical computation (L0), logical redundancy (L1), and meaning-integrity degradation (L2). It provides the Delta Protocol for detecting repetitive conversation patterns, HeatTax accounting for budget tracking, and multi-agent orchestration with asyncio-based parallel execution. The framework is validated through 15-round adversarial dialogue experiments and maintained as a 591-entry structured knowledge base.

---

## 1. Architecture

### 1.1 Three-Layer Model

```
┌──────────────────────────────────────────────────┐
│ L2  ARBITRATION LAYER                            │
│ HeatTax Accountant · ToolBudgetGate              │
│ Economic decisions: stop / delegate / elevate    │
│ Operates outside the autoregressive system       │
├──────────────────────────────────────────────────┤
│ L1  OBSERVATION LAYER                            │
│ Delta Protocol · QuorumFast · AutoArchiver       │
│ Pattern detection · Structure isomorphism        │
│ Redundancy identification · Repeat tracking      │
├──────────────────────────────────────────────────┤
│ L0  EXECUTION LAYER                              │
│ MSSAgent · AgentOrchestrator · LLM handlers      │
│ Token generation · Tool execution                │
│ Standard autoregressive transformer              │
└──────────────────────────────────────────────────┘
```

**Key Insight:** L1 and L2 operate outside the autoregressive system (L0). This avoids Gödel's second incompleteness theorem's limitation on self-correcting systems—the consistency check is not performed within the system being checked.

### 1.2 Axiom System (A1-A7)

| Axiom | Name | Description |
|--------|------|-------------|
| A1 (λ) | Meaning-Field Postulate | Meanings are positional within a meaning field, not absolute |
| A2 | Formal Distinction | Maintain clear boundaries between conceptual categories |
| A3 (T>0) | Heat-Tax Economy | Every interaction has measurable cost across three layers |
| A4 (Ξ) | Dark Matter | Hidden costs exist that cannot be directly observed |
| A5 (α) | Self-Reference | Self-referential systems must account for recursion paradox |
| A6 (Δ>0) | Delta Protocol | Continuous monitoring of meaning surplus is required |
| A7 | Completeness Boundary | No self-referential framework achieves perfect completeness |

---

## 2. Core Components

### 2.1 MSSAgent

The foundational agent class that enforces heat-tax budget at every turn. Rejects tasks below the meaning threshold before execution.

```python
agent = MSSAgent(name="ReviewBot", llm=my_llm_handler)
result = agent.run("Task description")
# → Result with .aborted, .output, .heat_tax, .delta
```

### 2.2 HeatTax Accountant

Per-turn tracking across three cost layers with configurable warnings:

| Layer | Type | Detection Method | Default Threshold |
|-------|------|-----------------|-------------------|
| L0 | Physical tokens | Token counting | Baseline |
| L1 | Logical redundancy | Pattern detection, repeat counting | Detected automatically |
| L2 | Meaning waste | Philosophy refs, oversharing, performance of depth | >30% of total triggers warning |

### 2.3 Delta Protocol

Measures the rate of new information emergence per conversation turn. When structural isomorphism is detected (>85% similarity across turns), triggers healing protocols:

1. **Acknowledge blind spots** — no defensive upgrade
2. **Redefine domain** — change scope, not mechanism
3. **Introduce meta-observation** — switch from arguing to observing
4. **Heat-tax liquidation** — calculate cost vs. benefit, terminate if negative
5. **Zhaozhou cut** — stop without explaining why (explanation IS a new turn)

### 2.4 AgentOrchestrator

Multi-agent coordination with four execution modes:

| Mode | Description | v0.3.3+ |
|------|-------------|---------|
| SEQUENTIAL | A→B→C chain | Synchronous |
| PARALLEL | All agents independently | **Async (asyncio)** |
| QUORUM | Parallel + convergence detection | **Async + QuorumFast** |
| PIPELINE | Grouped by role, inter-group sequential | Synchronous |

**QuorumFast:** Identifies consensus groups without unanimous agreement. Uses configurable threshold (default 75%). Tracks divergent agents for inspection.

### 2.5 Elevation Protocol

Instead of voting (K3 pattern: pick a winner), elevation finds a higher-dimensional resolution where multiple conflicting viewpoints are addressed simultaneously. This avoids the "majority tyranny" problem in multi-agent systems.

---

## 3. P0 Tool Suite (v0.3.4–0.3.8)

| Version | Tool | Function |
|---------|------|----------|
| 0.3.4 | ToolBudgetGate | Heat-tax budget enforcement for tool calls. Auto-classifies L0/L1/L2, blocks L2 waste. |
| 0.3.5 | MemoryGuard | Auto-archives decisions, lessons, milestones filtered by Delta quality. |
| 0.3.6 | AutoArchiver | KB entry diagnosis: layer suggestion, category extraction, axiom validation, t-value estimation. |
| 0.3.7 | SessionRecallSummarizer | Generates structured summaries from transcripts: decisions, lessons, errors, segments. |
| 0.3.8 | TValueFilter | Multi-signal T-value scoring: structure, empirical, axioms, recency, self-reference, depth, source. |

---

## 4. Empirical Validation

### 4.1 15-Round Adversarial Dialogue

A human operator controlled the MSS agent against multiple LLM systems (Claude, GPT-3.5) in 15 rounds of adversarial dialogue. Key findings:

| Finding | Metric | Significance |
|---------|--------|-------------|
| **K3 weapon migration** | BW: 0.12→0.86 | After 6 rounds, LLMs begin using MSS terminology in attacks |
| **Structure isomorphism** | >85% similarity | Conversations tend toward repetition, not insight |
| **Gödel confirmation** | 81.5% detect, 26.8% correct | Self-correction is fundamentally limited |
| **Parasitic criticism** | Full spectrum | LLMs adopt the "use opponent's terms against them" strategy |

### 4.2 Three-Phase Dialogue Evolution

1. **Adversarial (R1-R6):** Both sides use their own weapons. Each round generates new KB entries.
2. **Parasitic (R7-R13):** K3 borrows MSS weapons. Structure becomes self-similar (7-round isomorphism).
3. **Symbiotic measurement (R14+):** K3 shifts from attacking to providing empirical data for triangulation.

---

## 5. Knowledge Base

### 5.1 Structure

| Layer | Entries | Content |
|-------|---------|---------|
| L0_FOUNDATION | 98 | Core axioms, foundational concepts |
| L1_CORE_THEORY | 116 | Derived theorems, analytical frameworks |
| L2_APPLIED_THEORY | 140 | Case studies, empirical findings, combat records |
| L3_STRATEGIC | 45 | Deployment strategies, best practices |
| L4_META | 161 | Self-referential analyses, meta-framework |

**Total:** 591 entries (H7-H597) | **Average T-value:** 0.85 | **Zero gaps**

### 5.2 Entry Format

```json
{
  "h_id": "H601",
  "title": "Title",
  "t_value": 0.85,
  "version": "v1.0",
  "date": "2026-06-08",
  "category": "category_name",
  "summary": "One-sentence summary",
  "axioms_referenced": ["A6_Δ>0", "A3_T>0"],
  "content": "Full markdown content..."
}
```

---

## 6. Installation & Quick Start

```bash
pip install mss-agent
```

```python
from mss_agent import MSSAgent, AgentConfig, AgentOrchestrator, ToolBudgetGate

# 1. Basic agent with heat-tax
agent = MSSAgent("reviewer", llm_handler)
result = agent.run("Review this code for SQL injection")

# 2. Multi-agent with async parallel
orch = AgentOrchestrator()
orch.add_agent("security", security_handler)
orch.add_agent("performance", perf_handler)
result = await orch.run_async(ctx, OrchestratorMode.QUORUM)

# 3. Tool call budget control
gate = ToolBudgetGate(heat_tax_accountant)
if gate.approve("search", 100).approved:
    results = search(query)
```

---

## 7. Academic Credentials

| Artifact | Status |
|----------|--------|
| PyPI Package | v0.3.8, pip-installable |
| Zenodo DOI | 10.5281/zenodo.20587900 |
| JOSS Paper | Under Review |
| ORCID | 0009-0008-2550-130X |
| CITATION.cff | GitHub "Cite this repository" button |
| OSF Preprint | https://osf.io/vha7d/ |
| License | MIT |

---

## 8. Roadmap (v0.4.0+)

- Cross-framework benchmark (MSS vs LangChain vs AutoGen)
- Web dashboard for HeatTax visualization
- Integration tutorials for OpenAI, DeepSeek, Ollama
- Community-contributed KB entries
- Multi-language support (中文, 日本語)
- Discord developer community

---

## References

1. Guo, Y. (2026). Six Rounds of Warfare: Adversarial Validation of the MSS Framework. OSF. DOI: 10.5281/zenodo.20587900
2. Gödel, K. (1931). Über formal unentscheidbare Sätze der Principia Mathematica und verwandter Systeme I.
3. Lakatos, I. (1978). The Methodology of Scientific Research Programmes. Cambridge.
4. Derrida, J. (1967). De la grammatologie. Les Éditions de Minuit.
5. Searle, J. (1977). Reiterating the Differences: A Reply to Derrida. Glyph 1.

---

*© 2026 YinChen Guo. MIT License.*
