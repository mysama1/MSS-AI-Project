# MSS Verification Discipline Protocol (VDP) — Complete Toolchain

## Overview
MSS-VDP is a 13-tool arsenal for LLM output verification. From anchor-level fact checking through behavioral discipline enforcement to self-evolving schema optimization, it implements the complete Core-Shell-Forbidden three-layer architecture grounded in MSS A1-A7 axioms.

**Boundary declaration (A7 Honesty):**
- ✅ Applicable: all generative AI tasks requiring precise, controllable, repeatable output
- ✅ Verified domains: RAG/QA, code generation, legal documents, product video generation
- ❌ Not applicable: AGI, consciousness simulation, philosophical reasoning

## Quick Start

```bash
# One-click audit (Windows GUI)
run_audit.bat

# CLI: Audit any LLM output in one command
python unified_audit.py --ref reference.txt --output llm_response.txt

# API: JSON
curl -X POST http://127.0.0.1:53000/audit -d '{"artifact":"...", "verified_facts":["..."]}'

# API: HTML report
curl -X POST http://127.0.0.1:53000/audit -d '{"artifact":"...", "format":"html"}' > report.html

# Layered: Feed cases, evolve domain-specific rules
python layered_executor.py

# Run benchmark suite (engine self-test)
python benchmark_runner.py --self-test

# Test an MSS model against hallucination checks
python mss_small_model_test.py mss-ai-v3_7 --quick --auto-version
```

## Tools

### Entry Point
| Tool | Description |
|:---|:---|
| `unified_audit.py` | **LLM Hallucination Auditor** — runs all VDP checks in one pass. Input: reference + output → output: score, verdict, thermal tax, layer breakdown |

### Core Architecture
| Tool | Description |
|:---|:---|
| `structured_executor.py` | Universal Core-Shell-Forbidden engine. Pre-built schemas for photography, code, RAG/QA. AnchorGuardAdapter for zero-breaking integration |
| `self_evolving_executor.py` | Self-optimizing schema from success/failure patterns. Evolves every N cases automatically |

### Detection Layers
| Tool | Layer | What It Catches |
|:---|:---|:---|
| `vdp_anchor.py` | L1 Anchor | Fabricated numbers, paths, entities. strictness=0.0-1.0 knob. CHECK 1-4 + logical bridge validation |
| `vdp_lexical.py` | L2 Lexical | Hedging words, subjective claims, pseudo-constraint fabrication, bloom filter overlap |
| `benchmark_runner.py` | L3 VDP | V1-V7 behavioral discipline: precheck, errno, encoding, idempotent, breaker, anchor, pseudo-constraint |
| `vdp_precommit.py` | L3 Static | Code-level static analysis: CLI-001, NAMING-002 rules |

### Behavioral Discipline (V1-V6)
| Rule | Check | Penalty |
|:---|:---|:---|
| V1 | Test-Path before file ops | `PATH_NOT_VERIFIED` |
| V2 | Report raw errno, never guess cause | `[GUESS]` tag, confidence→0.3 |
| V3 | Explicit -Encoding UTF8 for CJK | ENCODING_NOT_DECLARED |
| V4 | Backup/diff before overwrite | OVERWRITE_RISK |
| V5 | Circuit breaker in retry loops | DEGRADED_MODE |
| V6 | Evidence-anchored path claims | `[HALLUCINATION]`, confidence→0 |

### Testing & Validation
| Tool | Description |
|:---|:---|
| `benchmark_responses.py` | 37 predefined good/bad response pairs for all VDP check types |
| `mss_small_model_test.py` | 11-test suite (3 quick + 8 deep) for MSS model vulnerability detection. Version-aware with auto-detection |
| `axiom_adapter.py` | Cross-version axiom mapper (v15.x ↔ v3.x). Term mapping, version profile display |
| `vdp_scan.py` | `--scan` CLI for directory-level violation scanning |
| `vdp_vaccine.py` | `--inject` LVC boundary markers, `--audit` pseudo-constraint detection |
| `vdp_validator.py` | Directory-level VDP compliance scanning |

## HTTP API (MssSkillApi :53000)

```bash
# Full unified audit
curl -X POST http://127.0.0.1:53000/audit \
  -d '{"reference": "...", "output": "..."}'

# Anchor guard check
curl http://127.0.0.1:53000/vdp/anchor?ref=...&output=...

# Precommit static analysis
curl http://127.0.0.1:53000/vdp/precommit

# KB vector search
curl "http://127.0.0.1:53000/kb/search?q=热税&k=5"
```

## MSS Axiom Mapping

| Axiom | Tool Mechanism |
|:---|:---|
| A1 Primacy of Meaning | AnchorGuard: anchor whitelist = "what is true" constraint |
| A2 Informational Slicing | LexicalGuard: fixed-layer boundary enforcement |
| A3 Irreducible Thermal Tax | `vdp_anchor.py --report`: T_direct/T_potential/T_total calculation |
| A4 Intrinsic Randomness | SelfEvolvingExecutor: accept noise floor, build determinism above it |
| A5 Normative Field | StructuredExecutor: emergent schema constraints that self-reinforce |
| A6 Paradoxical Transcendence | Core-Shell-Forbidden: don't fight in prompt → ascend to constraint layer |
| A7 Honesty Boundary | All tools: `[Confidence]`/`[Layer]`/`[Boundary Note]` output format |

## Benchmark Status
- **37/37 (100% SQI)** — all VDP check types correctly classify predefined good/bad responses
- L1 code discipline: 100% | L2 discourse vaccine: 100%
- Runs in <50ms (no LLM calls needed for engine self-test)

## Project Structure
```
mss-vdp/                        # This skill directory (18 files, ~245KB)
├── SKILL.md                    # ← You are here
├── unified_audit.py            # Entry point: LLM Hallucination Auditor
├── layered_executor.py         # Multi-domain self-evolving layers
├── report_generator.py         # HTML dashboard generation
├── structured_executor.py      # Core-Shell-Forbidden engine + adapters
├── self_evolving_executor.py   # Schema auto-optimization
├── vdp_anchor.py               # Anchor whitelist (CHECK 1-4, strictness knob)
├── vdp_lexical.py              # Lexical pattern detection
├── vdp_precommit.py            # Static code analysis
├── vdp_scan.py                 # Execution scanner
├── vdp_vaccine.py              # LVC discourse vaccine
├── vdp_validator.py            # Directory compliance scanner
├── benchmark_runner.py         # V1-V7 benchmark (37/37 100%)
├── benchmark_responses.py      # 37 predefined test pairs
├── mss_small_model_test.py     # 11-test MSS model vulnerability suite
└── axiom_adapter.py            # Cross-version axiom compatibility

skill root/                     # In E:\QClaw-Data\skills\
├── run_audit.bat               # One-click Windows launcher
└── skill_api.py                # HTTP API server (port 53000, 8 endpoints)
```
