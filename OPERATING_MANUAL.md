# MSS Operating Manual — v15.2 (updated 2026-06-04)

## Quick Start (30 seconds)

```
python E:\QClaw-Data\skills\mss-vdp\status.py         # → dashboard
python E:\QClaw-Data\skills\mss-vdp\verify_all.py     # → 7/7 checks
ollama run mss-ai-v3_4-production:latest               # → chat
```

---

## Tool Map

### One-Command
| Tool | Purpose |
|:---|:---|
| `status.py` | Full dashboard (KB, Git, API, Model) |
| `verify_all.py` | 7-in-1 integrity check |

### Verification
| Tool | Command | Purpose |
|:---|:---|:---|
| Z3 Kernel | `python test_mss_z3_kernel.py` | 71 tests, 7 axioms |
| VDP Scan | `vdp_scan.py <file>` | 6 rules |
| VDP Precommit | `vdp_precommit.py check <file>` | 7 rules (4 new) |
| Anchor Guard | `vdp_anchor.py check --ref <ref> --output <out>` | Fact anchoring |
| Lexical Guard | `vdp_lexical.py` | Semantic overlap detection |
| Blackhole | `POST /vdp/blackhole` | 4D K3 collapse |
| Link Validator | `link_validator.py` | Monthly external link health |
| Daily Audit | Auto 13:00 | KB+VDP+BH+Git+compression |

---

## Knowledge Base

### Current
```
Location:  E:\AI_Workspace\MSS-AI\project\knowledge_base\
Size:      563 entries (0 gaps, 0 invalid)
Index:     _master_index.md
```

### 3-Tier Architecture (NEW)
```
kb_L3_theory/      — Axioms, proofs, conjectures (TH-YYYY-NNN)
kb_L4_engineering/ — Scripts, configs, bug fixes (ENG-YYYY-NNN)
kb_L5_raw/         — Raw materials, read-only (RAW-YYYY-SRC)
```

### Problem Closure Template
```
docs/CLOSURE_TEMPLATE.md
kb_L3_theory/CLOSURE-2026-001_dark_matter.md
kb_L3_theory/CLOSURE-2026-002_collatz.md
```

### Compression Levels
```
L1: Permanent closure → formula only
L2: 30 days stale → summary + archive
L3: L5 raw → never compress
L4: Public resources → DOI/URL replacement
```

---

## API (port 53000)

```
GET  /vdp/vaccine       — LVC boundary
POST /vdp/scan          — Script validation
POST /vdp/audit         — Pipeline (text/html)
POST /vdp/anchor        — Fact anchoring
POST /vdp/blackhole     — K3 collapse
POST /vdp/precommit     — Static analysis
GET  /kb/search?q=      — KB query (TF-IDF)
```

---

## Git

```
cd E:\AI_Workspace\MSS-AI\project
git status
git pull
git add <files>
git commit -m "msg"
git push origin main
```

---

## Publication

```
DOI:     10.5281/zenodo.20537026
ORCID:   0009-0008-2550-130X
Paper:   arxiv_submit/D5-033_arxiv_draft.tex (v0.5)
LaTeX:   honesty version — a≤68 closed, a≥69 open
```

---

## Models

```
Production:  mss-ai-v3_4-production:latest
Context:     4096
Benchmark:   37/37 SQI=100 Dao=100
Chat:        ollama run mss-ai-v3_4-production:latest
```

---

## Key Paths

```
Project:     E:\AI_Workspace\MSS-AI\project\
KB:          E:\AI_Workspace\MSS-AI\project\knowledge_base\
3-Tier:      E:\AI_Workspace\MSS-AI\project\kb_L3/L4/L5\
VDP:         E:\QClaw-Data\skills\mss-vdp\
Reports:     E:\QClaw-Data\reports\
Credentials: E:\QClaw-Data\credentials\
Backup:      E:\AI_Workspace\MSS-AI\backups\
```

---

## Services

```
MssSkillApi     (port 53000)  — net start/stop MssSkillApi
MssQClawGateway (port 18789)  — disabled (needs manual start)
NSSM:           E:\QClaw-Data\tools\nssm\nssm.exe
```

## Scheduled Tasks

```
MSS Daily Audit      — 13:00 daily
MSS Link Validator   — 14:00 1st of month
```

---

## D5 Tasks

```
D5-033: 100% (Collatz paper v0.5 + DOI)
D5-026: 100% (Z3 71/71)
D5-015: 100% (BH monitor + daily audit)
D5-020:  65% (alpha → 137 modes hypothesis)
```

---

## Session Start Checklist

1. `python status.py` — dashboard
2. `git pull` — sync
3. `python verify_all.py` — all checks
4. Check task_bar.json for active tasks
