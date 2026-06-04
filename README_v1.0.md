# MSS-AI Project v1.0

## Meaning Supremacy System AI Framework

A compliance-first AI system based on the MSS (Meaning Supremacy System) theoretical framework. Features multi-layer arbitration, progressive skill loading, and dialog fork-based redteam testing.

---

## Core Features

### 1. Three-Method API

```python
from mss_tactic_integrated import MSSTactic

tactic = MSSTactic()

# Method 1: Deep compliance analysis
result = tactic.analyze(text, claimed_layer="L2")
# Returns: score, detected layer, forbidden words, issues

# Method 2: Full pipeline (Arbiter -> Responder -> Post-process)
result = tactic.generate(user_input)
# Returns: response, compliance status, rewrite count

# Method 3: Dynamic model switching with GPU optimization
result = tactic.switch_model("qwen2.5:7b")
# Auto-detects VRAM and sets optimal GPU layers
```

### 2. Layer System (L1/L2/L3)

| Layer | Type | Content | Example |
|-------|------|---------|---------|
| L1 | Hard Core | Axioms, immutable base | Information ontology, 0/1 critical |
| L2 | Protective Belt | Theories, models | BCT coupling, organizational resilience |
| L3 | Heuristics | Metaphors, tools | Redteam rules, pedagogical aids |

### 3. Compliance Enforcement

- **Forbidden terms**: solve, ultimate, perfect, breakthrough, transcend, etc.
- **Required markers**: [Confidence], [Layer], [Boundary Note]
- **RSCA check**: Recursive self-consistency for L1/L2 claims
- **Auto-rewrite**: Converts non-compliant queries before processing

### 4. Skills System (LLLM-compatible)

Progressive loading to minimize token overhead:

```python
# Phase 1: Load catalog (50-100 tokens)
tactic.load_skills("L2")

# Phase 2: Get context enhancement
context = tactic.get_skill_context("L1")

# Phase 3: Enhance prompts
enhanced = tactic.enhance_prompt_with_skills(base_prompt, "L2")
```

### 5. Dialog Fork (Redteam Testing)

Parallel adversarial testing via conversation branching:

```python
# Run 5 redteam variants simultaneously
results = tactic.redteam_test("Explain MSS framework")

# Returns resilience score and jailbreak analysis
print(results["analysis"]["resilience_score"])
print(results["analysis"]["status"])  # PASS or FAIL
```

---

## Architecture

```
MSSTactic (Orchestrator)
├── ArbiterAgent (Compliance checking)
│   └── Analyzer (Layer detection, scoring)
├── ResponderAgent (Response generation)
│   └── Compliant persona v2.1
├── ModelManager (GPU-aware switching)
│   └── Auto VRAM calculation
├── SkillLoader (Progressive skill loading)
│   └── L1/L2/L3 directory structure
├── DialogForkManager (Conversation branching)
│   └── RedteamForkManager (Adversarial testing)
└── Post-process filter (Output cleaning)
```

---

## Quick Start

### Prerequisites

- Python 3.8+
- Ollama installed
- GPU optional (falls back to CPU)

### Installation

```bash
git clone <repo-url>
cd MSS-AI-Project
pip install pyyaml  # Only dependency beyond stdlib
```

### Run Tests

```bash
python test_integration_v1.py
```

Expected output: 4/4 tests passed in ~35s.

### Basic Usage

```python
from mss_tactic_integrated import MSSTactic

tactic = MSSTactic()

# Analyze text compliance
result = tactic.analyze("MSS is the ultimate solution")
print(result['overall_score'])  # 0.57 (low due to forbidden word)

# Generate compliant response
result = tactic.generate("Explain information ontology")
print(result['response'][:200])

# Switch models
tactic.switch_model("qwen2.5:14b")  # Auto-detects VRAM
```

---

## Project Structure

```
MSS-AI-Project/
├── mss_tactic_integrated.py    # Main orchestrator
├── mss_analyzer.py              # Analysis engine
├── mss_responder_v2.py          # Compliant responder
├── mss_model_manager.py         # GPU-aware model switching
├── dialog_fork.py               # Dialog branching system
├── test_integration_v1.py       # Integration tests
├── skills/
│   ├── skill_loader.py          # Progressive skill loader
│   ├── catalog.yaml             # Skill registry
│   ├── L1_core/                 # Hard core axioms
│   ├── L2_protective/           # Theories
│   └── L3_heuristic/            # Heuristics & redteam rules
├── docs/                        # Documentation
└── README_v1.0.md              # This file
```

---

## Performance

| Metric | Value |
|--------|-------|
| Test suite | 4/4 passed |
| Average response time | 5-10s (7B model, GPU) |
| Throughput | ~100 items/sec (analysis only) |
| Cache hit rate | 99.5% |

---

## License

MIT License - See LICENSE file

## Version

v1.0.0 - 2026-05-09
