# MSS-AI v15.2

**Meaning Supremacy System** — 意义至上体系

```
Status: 🟢 ALL GREEN    CRTR: 1.5    SVᵣ: 0.0
Model:  mss-ai-v3_4-production (0.72 L4)
KB:     563 entries    Git: 8205ab8
```

## Quick Start

```bash
mss status     # Dashboard
mss verify     # 8-checks (Z3+VDP+KB+API+Cache+Git)
mss audit      # Daily health report
mss cache      # Module parasite scan
mss kb search <query>  # Knowledge base
```

## Architecture

```
L1 Axioms    — A1-A6 (H141), Z3-verified (71/71)
L2 Theorems  — W=Q/γ, CRTR, SVᵣ, L2-011 (cache parasite)
L3 Theory    — 11 documents (TH-001 → TH-010)
L4 Engineering — 3 docs, 8 tools, 24 VDP rules
L5 Raw       — 2 closure reports
```

## Key Numbers

| What | Value | Source |
|:---|:---|:---|
| System integrity | 8/8 ✅ | verify_all |
| KB health | 563 entries, 0 invalid | kb_quality |
| Engineering benchmark | 0.72 L4 (21 rounds) | LLM Judge |
| Self-audit score | 8.3/10 | TH-007 |
| Heat tax | CRTR=1.5 | daily_audit |
| Paper | v0.5, DOI:10.5281/zenodo.20537026 |
| ORCID | 0009-0008-2550-130X |

## VDP Rules

```
24 rules: CLI-001, NAMING-002, CFLOW-003,
          NO_ARBITRARY_RATIO, NO_CONTINUITY_ON_DISCRETE,
          INEQUALITY_3POINT_CHECK, COMPLETENESS_GATE
```

## Honesty Boundaries

- ✅ Python P0吞错: 12/12 (100%)
- ✅ Engineering Q&A: 0.72 L4 (7 domains verified)
- ⚠️ P2/P3: 88.9% false positive
- ❌ Non-Python syntax analysis: not supported
- ❌ Runtime detection (locks, memory): not supported

## Directory

```
E:\AI_Workspace\MSS-AI\project\
  kb_L3_theory/    TH-001 → TH-010
  kb_L4_engineering/  ENG-001, ENG-002
  kb_L5_raw/       RAW-001, CLOSURE-001, CLOSURE-002
  knowledge_base/  563 .jsonl entries
  formalization/   W_logic, entropy, stability
  docs/            OPERATING_MANUAL, CLOSURE_TEMPLATE

E:\QClaw-Data\skills\mss-vdp\
  mss.py            Unified CLI (9 subcommands)
  verify_all.py     8 integrity checks
  daily_audit.py    Automated health (13:00 daily)
  vdp_scan.py       6-rule scanner
  vdp_precommit.py  7-rule precommit
  vdp_anchor.py     Fact anchoring
  vdp_lexical.py    Lexical overlap detection
  module_cache_detector.py  L2-011 parasite detection
  status.py         Dashboard
  kb_quality.py     KB metadata scanner
  link_validator.py External link checker (monthly)
  mss_whitelist.yml 3-tier cache immunity config
```
