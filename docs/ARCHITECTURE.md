# mssclaw Documentation

## Architecture

```
pip install mss-agent
          │
    ┌─────┴──────┐
    │  mssclaw   │  ← Unified CLI
    └─────┬──────┘
          │
    ┌─────┴─────────────────────────┐
    │                               │
  ┌─┴──────────┐          ┌────────┴──────┐
  │ Agent Core  │          │  Vault Stack  │
  │ ─────────── │          │  ──────────── │
  │ L2 Bridge   │          │  CredentialVault
  │ HeatTax     │          │  VaultHealth   │
  │ Delta       │          │  VaultStats    │
  │ NormField   │          │  VaultServer   │
  │ HalluShield │          │  VaultCLI      │
  │ CogFrame    │          │  ChromeImport  │
  │ LLM Backend │          └────────┬──────┘
  │ Tool Registry│                 │
  │ RAG Pipeline │         ┌───────┴───────┐
  │ Agent Pipeline│        │  HTTP API      │
  │ Stream Engine │        │  Web Dashboard │
  └──────┬────────┘        └───────────────┘
         │
    ┌────┴─────────────────────┐
    │  Specialty Systems       │
    │  ─────────────────      │
    │  Skill Compiler          │
    │  Agent Absorber          │
    │  Digest Engine           │
    │  Logic Virus Detector    │
    │  Herd Immunity           │
    │  Library Manager         │
    │  Model Orchestrator      │
    │  MSS Shell               │
    │  MSS Evaluator           │
    └──────────────────────────┘
```

## Core Modules

### L2 Meaning Layer (MSS Unique)
| Module | Purpose |
|---|---|
| `l2_bridge.py` | L2 bridge: heat tax, delta, norm field orchestration |
| `heat_tax.py` | A3 heat tax: physical/logic/meaning three-layer tax |
| `delta.py` | Delta openness: maintain Δ>0, prevent closure |
| `normative_field.py` | Normative field: prompt engineering as a field |
| `hallucination_shield.py` | 31 rules, 4 detection types |
| `cognitive_framework.py` | Capability self-awareness, identity anchoring |
| `mss_evaluator.py` | Dao scoring: valid - pseudo×2.0 |

### Agent Engine
| Module | Purpose |
|---|---|
| `agent.py` | Core MSSAgent with L2 bridge |
| `llm_backend.py` | Ollama + OpenAI backend |
| `stream_styler.py` | Semantic streaming (6 modes) |
| `deep_fold.py` | Auto-fold deep content |
| `smart_router.py` | Tiered routing |
| `tool_registry.py` | 10 built-in tools |
| `rag_pipeline.py` | BM25 + density RAG |
| `agent_pipeline.py` | Writer→Reviewer→Refiner |
| `memory.py` | 3-tier memory storage |
| `memory_consolidator.py` | Auto-condense memories |

### Vault Stack
| Module | Purpose |
|---|---|
| `credential_vault.py` | AES-256-GCM encrypted vault |
| `vault_health.py` | Password hygiene scoring |
| `vault_stats.py` | Usage statistics |
| `vault_server.py` | REST API (port 5099) |
| `vault_cli.py` | 15+ commands |
| `chrome_import.py` | Chrome/Edge password migration |

### Specialty Systems
| Module | Purpose |
|---|---|
| `skill_compiler.py` | Absorb→Deconstruct→MSS-rebuild→Generate |
| `agent_absorber.py` | External agent→MSS ecosystem |
| `digest_engine.py` | Auto-digest absorbed skills |
| `logic_virus_detector.py` | 5 types, 20+ rules, auto-repair |
| `herd_immunity.py` | Cross-agent vaccine propagation |
| `library_manager.py` | 8 libraries, cross-search |
| `model_catalog.py` | 30 models (18 cloud + 9 local + 3 MSS) |
| `model_orchestrator.py` | Multi-model pipeline |
| `mss_shell.py` | Perception Shell + Logic Core dual model |

## CLI Reference

```bash
mssclaw init          # One-click environment setup
mssclaw chat          # Terminal AI chat
mssclaw demo          # Full system demo (12 modules)
mssclaw status        # System status panel
mssclaw serve         # Start Agent + Vault services
mssclaw vault         # Vault subcommands (setup/add/get/list/search/serve)
mssclaw kb <query>    # Search MSS knowledge base (618 entries)
mssclaw absorb <desc> # Absorb external skill/agent
mssclaw library       # Library management (search/export)
mssclaw models        # Model catalog (30 models)
```
