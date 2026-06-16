# MSS-AI Project State — 2026-06-03

## Quick Start

```bash
# API Health
python -c "import requests; print(requests.get('http://127.0.0.1:53000/health').json())"

# Best Model
ollama run mss-ai-v3_4:latest "根据MSS-A3公理，什么是热税？"

# Full Audit (HTML)
python run_audit.bat  # or POST /audit?format=html

# Daily Check
python daily_audit.py
```

## Architecture

```
MSS-AI/
├── project/
│   ├── knowledge_base/    402 entries (H7-H454)
│   ├── _master_index.md   Full index
│   ├── formalization/     w_logic theory
│   ├── mss_z3_kernel.py   Z3 verification
│   └── mss_llm_perception_shell.py
│
├── tools/
│   └── mss-vdp/           16 files, 245KB
│       ├── unified_audit.py       Core auditor
│       ├── vdp_anchor.py          Anchor + WITHHOLD + Dao Score
│       ├── vdp_lexical.py         Lexical n-gram guard
│       ├── vdp_precommit.py       Static analysis (CLI-001/NAMING-002)
│       ├── benchmark_runner.py    37/37 self-test
│       ├── benchmark_responses.py Test cases
│       ├── report_generator.py    HTML dashboard
│       ├── daily_audit.py         Scheduled monitoring
│       └── skill_api.py           HTTP API (:53000, v2.4)
│
└── backups/
    └── Modelfile.mss-ai-v3_4-production
```

## Model Fleet

| Model | Score | Speed | Status |
|:---|:---|:---|:---|
| mss-ai-v3_4 | 100% | 2.2s | **PRODUCTION** |
| mss-ai-v3_4-production | 97% | 13.1s | Clean template |
| mss-ai-v3_6 | 100% | 5.1s | Backup |
| mss-ai-v3_7 | 100% | 8.7s | Axiom reference |
| mss-ai-v3_6-32k | — | — | 32K context |

## API Endpoints (:53000)

```
GET  /health                  Status
POST /audit                   Full audit (JSON/HTML)
POST /vdp/scan                VDP pattern scan
POST /vdp/anchor              Anchor check + WITHHOLD verdict
POST /vdp/precommit           Code review
GET  /kb/search?q=xxx         KB vector search
GET  /vdp/vaccine             LVC boundary markers
```

## Key Paths

```
E:\AI_Workspace\MSS-AI\project\knowledge_base\
E:\QClaw-Data\skills\mss-vdp\
E:\QClaw-Data\skills\skill_api.py
E:\QClaw-Data\skills\run_audit.bat
E:\cross_model_benchmark.json
E:\QClaw-Data\workspace\daily_audit_log.json
```

## Scheduled Tasks

- MSS-VDP Daily Audit: Daily 08:00, v3.4 quality check
- Log: E:\QClaw-Data\workspace\daily_audit_log.json

## Today's Milestones

- VDP toolchain: 0→16 files (37/37 100%)
- Cross-model benchmark: v3.4 champion identified
- KB: 374→402 entries (+28)
- H141: v15.1 six-axiom cornerstone created
- αβγ settlement system: field density meter + WITHHOLD + Dao Score
- 诚实边界(切片) naming: ineffability → K3-compatible boundary
- Daily monitoring: Windows scheduled task