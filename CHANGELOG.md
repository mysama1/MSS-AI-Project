# mssclaw Changelog

## v0.3.0 (2026-06-16)

### 🎯 Phase 1: Foundation (Sprints 0-10)
- L1补齐 + L2护城河 (HeatTax / Delta / NormField / HalluShield / CogFrame)
- Credential Vault (AES-256-GCM encrypt vault, 7 tests)
- Vault Toolkit (generator, TOTP, password strength, 8 tests)
- mss-vault CLI (15+ commands)
- Chrome/Edge password importer
- CI workflow integration

### ⚙️ Phase 2: Production Hardening (Sprints 11-20)
- Vault Health & Auto-Backup (+4 tests)
- Vault Stats Panel (+3 tests)
- Full Stack E2E Demo (+2 tests)
- KB Search fix (L0 + supplementary indexed)
- Vault Search (fuzzy)
- Agent LLM Backend (Ollama/OpenAI)
- Vault HTTP API (RESTful, port 5099)
- Vault Web Dashboard (HTML panel)

### 🚀 Phase 3: Streaming + Docker (Sprints 21-30)
- Live Agent+Vault+Ollama Demo
- Stream output (run_stream)
- StreamStyler (color/fold/breathe)
- DeepFold (auto-fold deep content)
- Docker (docker-compose up)
- SemanticStreamStyler v2.0
- SmartRouter (tiered routing)
- Velocity Alignment (no lag)
- Agent HTTP API microservice (port 5100)
- DeltaMonitor (MSS health check)
- MSS Model Live Test

### 🧠 Phase 4: Advanced Agent (Sprints 31-40)
- Unified Launcher (mssclaw CLI)
- Tool Calling with L2 filtering (+6 tools)
- RAG Pipeline (BM25 + density)
- ResilientBackend (retry/degrade/circuit-break)
- Multi-Agent Pipeline (Writer→Reviewer→Refiner)
- Session Persistence
- Full Integration Test (9 modules)

### 🔐 Phase 5: Vault 2.0 + Dashboards (Sprints 41-48)
- Process Monitor + zombie detection
- Full System Health Report
- Memory Consolidator (auto-condense)
- Credential Vault Web Panel
- Unified Quickstart

### 📊 Phase 6: MSS-Unique Features (Sprints 49-62)
- **MSS Evaluator** — Dao scoring (valid - pseudo×2.0)
- **Skill Compiler** — Absorb→Deconstruct→MSS-rebuild→Generate
- **Agent Absorber** — External agent→MSS ecosystem
- **Digest Engine** — Auto-digest to current agent
- **Logic Virus Detector** — 5 types, 20+ rules, auto-repair
- **Herd Immunity** — Cross-agent vaccine propagation
- **Library Manager** — 8 libraries, cross-search, dependency tracker
- **mssclaw status** — Full system panel
- **mssclaw absorb** — CLI absorption

### 🏗️ Phase 7: Multi-Model & Shell (Sprints 63-73)
- Dashboard popup fix
- **Office Toolkit** — word_count, format_table, text_summarize, json_format
- **Model Library** — Auto-scan Ollama, custom registration
- **Custom Library** — User-extensible library framework
- **MSS Shell Mode** — Perception Shell + Logic Core dual model
- **Shell live test** — Verified: qwen2.5:7b shell + mss-ai-v3.4.3 core
- **CJK-aware routing** — Chinese character ×3 weight

### 🧹 Phase 8: Cleanup & Polish (Sprints 74-85)
- **Smart Backend Selector** — API for shell, local for core
- **Global Model Catalog** — 30 models (18 cloud + 9 local + 3 MSS)
- **Project Audit** — Fixed .gitignore, Rust artifacts
- **Test cleanup** — 25 ad-hoc → _archive
- **Repository cleanup** — Root: 191→10 files, 325→scripts/archive/
- **mssclaw models** CLI
- **mssclaw library export** ecosystem manifest
- **mssclaw demo** — 12 systems verified
- **CHANGELOG.md**

### 📈 Stats
- 85 Sprints | 117 Tests | 85 Commits
- 7 hours continuous build (14:00→21:00)
- 103 core modules | 8 libraries | 643 entries
- 30 models cataloged | 10 tools | 5 skills
- Project rating: A- (functionality A+, cleanliness A-)
