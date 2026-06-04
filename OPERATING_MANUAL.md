# MSS Operating Manual — v15.2

## Quick Start (30 seconds)

```
cd E:\AI_Workspace\MSS-AI\project
python test_mss_z3_kernel.py    # → 71/71
python E:\QClaw-Data\skills\mss-vdp\daily_audit.py  # → OK
curl http://localhost:53000/vdp/vaccine  # → LVC boundary
```

## Tool Map

### Verification
| Tool | Command | Purpose |
|:---|:---|:---|
| Z3 Kernel | `python test_mss_z3_kernel.py` | 71 tests, all 7 axioms |
| VDP Scan | `python mss-vdp/vdp_scan.py --scan <file>` | 6 rules check |
| Anchor Guard | `python mss-vdp/vdp_anchor.py --check <text>` | Fact anchoring |
| Blackhole | `POST /vdp/blackhole` | K3 collapse detection |
| Daily Audit | Auto 08:00 | KB+VDP+BH+Git health |

### Knowledge Base
```
Location:  E:\AI_Workspace\MSS-AI\project\knowledge_base\
Index:     _master_index.md
Size:      545 entries (383 H-series)
Health:    python daily_audit.py → checks KB
Query:     GET http://localhost:53000/kb/search?q=<term>
```

### API (port 53000)
```
GET  /vdp/vaccine       — LVC boundary markers
POST /vdp/scan          — Script/artifact validation
POST /vdp/audit         — Full pipeline (JSON/HTML)
POST /vdp/anchor        — Fact anchoring check
POST /vdp/blackhole     — K3 black hole detection
GET  /kb/search?q=      — Knowledge base query
```

## Git Workflow
```
cd E:\AI_Workspace\MSS-AI\project
git status                # Check state
git add <files>
git commit -m "message"
git push origin main      # → GitHub
```

## Publication Pipeline
```
1. Preprint → Zenodo (DOI)
   Token: E:\QClaw-Data\credentials\zenodo_token.json
   DOI:   10.5281/zenodo.20537026
   ORCID: 0009-0008-2550-130X

2. arXiv (pending)
   LaTeX: D5-033_arxiv_draft.tex (v0.4)
   Needs: VPN for zenodo.org

3. New preprint:
   Update LaTeX → upload to Zenodo → get DOI → update README
```

## Key Paths
```
Project:    E:\AI_Workspace\MSS-AI\project\
KB:         E:\AI_Workspace\MSS-AI\project\knowledge_base\
Formal:     E:\AI_Workspace\MSS-AI\project\formalization\
Skills:     E:\QClaw-Data\skills\
VDP:        E:\QClaw-Data\skills\mss-vdp\
Reports:    E:\QClaw-Data\reports\daily\
Backup:     E:\AI_Workspace\MSS-AI\backups\
Credentials:E:\QClaw-Data\credentials\
Workspace:  E:\QClaw-Data\workspace\
```

## Services
```
MssSkillApi     (port 53000)  — net start/stop MssSkillApi
MssQClawGateway (port 52930)  — QClaw gateway
NSSM:           E:\QClaw-Data\tools\nssm\nssm.exe
```

## Models
```
Production:     mss-ai-v3.4-production (Ollama, 131K ctx)
Main:           qclaw/pool-hy3-preview (DeepSeek)
Dev:            mss-ai v3.3-v3.7 (Ollama)
```

## KB Entry Template
```json
{"id":"hXXX_name","title":"HXXX: Title","version":"v1.0",
 "created":"2026-06-04T00:00:00+08:00","content":"Markdown body",
 "confidence":0.90,"tags":["tag1","tag2"],
 "references":["H141","H163"]}
```

## Common Tasks

### New KB Entry
1. Create .jsonl in knowledge_base/
2. Use template above
3. git add + commit + push
4. Update _master_index.md if significant

### Run Full Verification
```bash
cd E:\AI_Workspace\MSS-AI\project
python test_mss_z3_kernel.py
python E:\QClaw-Data\skills\mss-vdp\daily_audit.py
```

### Check API Health
```bash
curl http://localhost:53000/vdp/vaccine
net start MssSkillApi  # if down
```

### Backup
```bash
python E:\QClaw-Data\skills\mss-vdp\fire_seed_backup.py
```

## Current Active Tasks
```
D5-020: Physical Constants Origin  (60% — α topology pending)
KB:     8 gaps remaining (H147,H149,H151-154,H156-158)
arXiv:  LaTeX v0.4 → polish → submit
Zenodo: API token saved, needs VPN to activate
```

## Session Start Checklist
1. `git pull` — sync latest
2. `python daily_audit.py` — health check
3. Check task_bar.json for priorities
4. Check KB gaps
5. Run Z3 tests to confirm environment
