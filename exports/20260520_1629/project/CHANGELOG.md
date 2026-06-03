# MSS-AI Changelog

## [1.0.0] - 2026-05-15

### Added
- **Web API** (`web_api.py`): FastAPI-based HTTP interface with 8 endpoints
  - `/chat` - Natural language conversation
  - `/analyze` - Text compliance analysis
  - `/reason` - Symbolic reasoning queries
  - `/scan` - Organizational resilience scanning
  - `/status` - System status monitoring
  - `/model/switch` - Dynamic model switching
  - `/health` - Health check endpoint
  - `/knowledge-base` - KB statistics

- **Numerical Simulation Framework** (`simulation_framework.py`)
  - Percolation phase transition simulator
  - ETA order parameter dynamics
  - Heat tax accumulation model
  - Organizational resilience decay
  - Parameter sweep engine
  - Critical point estimation

- **Visualization Engine** (`visualization_engine.py`)
  - ASCII line charts for time series
  - ASCII bar charts for distributions
  - ASCII radar charts for multi-dimensional data
  - ASCII heatmaps for matrix data
  - Formatted data tables
  - System dashboard generator

- **Documentation**
  - `README.md` - Project overview and quick start
  - `ARCHITECTURE.md` - System design and component interactions
  - `API_GUIDE.md` - Complete API reference with examples
  - `requirements.txt` - Dependency specifications
  - `setup.py` - Package installation configuration

### Enhanced
- Test suite expanded to **24 suites / 308 tests** (100% pass rate)
- Interactive CLI with full command set
- NL Bridge V2 with multi-turn context

### Technical
- Zero external dependencies for core functionality
- Pure Python implementation for maximum compatibility
- FastAPI for async web API support
- NumPy for numerical computations

## [0.9.0] - 2026-05-14

### Added
- **Interactive CLI** (`interactive_cli.py`): Command-line interface
  - Natural language chat mode
  - Symbolic reasoning commands
  - System diagnostics
  - Color themes support

- **Anti-Distillation Defense** (`anti_distillation_defense_v1.0.jsonl`)
  - 7 defense strategies (L2=3, L3=4)
  - Meaning spin encryption
  - Patent system elevation
  - Meaning分层防火墙

- **He Guang Tong Chen Tactics** (`heguang_tongchen.py`)
  - 8 tactical entries
  - Cosmic background radiation collector
  - Meaning toxin centrifuge
  - Tool rationality encapsulation

### Enhanced
- Test suite: 21 suites / 272 tests
- NL Bridge V2 with complex query support
- V3 Integration with 7 new methods

## [0.8.0] - 2026-05-13

### Added
- **Symbolic Engine V3** (`symbolic_engine_v3.py`)
  - TransitiveReasoner for path finding
  - CycleDetector for circular reasoning detection
  - MSSv12AxiomSystem (3 axioms + 3 theorems)
  - HeatTaxMonitor for thermal state tracking

- **NL Bridge V2** (`nl_bridge_v2.py`)
  - Multi-turn conversation context
  - Anaphora resolution
  - Complex query composition (AND/OR/THEN/COMPARE)
  - Multiple response formats

- **Knowledge Base Loader** (`kb_loader.py`)
  - JSONL parsing with UTF-8 support
  - Chinese text processing
  - Graph construction from entries
  - Layer-based filtering

### Fixed
- GBK encoding issues resolved
- Chinese word segmentation improved
- IMPLIES edge generation restored (0 → 33 edges)

## [0.7.0] - 2026-05-12

### Added
- **Topology Metrics** (`topology_metrics.py`)
  - Bridge detection
  - Clustering coefficient
  - Connected component analysis

- **Post-Process Engine V3** (`post_process_engine_v3.py`)
  - Enhanced assertion checking
  - Structure validation
  - Compliance verification

- **Gateway Monitor** (`gateway_monitor.py`)
  - Process health checking
  - HTTP endpoint monitoring
  - Automatic restart capability

### Enhanced
- Test suite: 17 suites / 234 tests
- Symbolic engine data flow integration
- Omega rules expanded to Ω-R036

## [0.6.0] - 2026-05-11

### Added
- **Ω-Level Arbitration** (`symbolic_rules_omega.py`)
  - 36 rules (L1=17, L2=16, L3=13)
  - Dual singularity arbitration
  - Violation type classification

- **Hybrid Reasoning** (`hybrid_reasoning.py`)
  - Symbolic-only mode
  - LLM-only mode
  - Hybrid symbolic-first mode
  - 4 fusion strategies: CASCADE, WEIGHTED, CONSENSUS, ADAPTIVE

- **Stability Monitor** (`mss_stability.py`)
  - SystemHealthMonitor with background threading
  - AdaptiveTaskScheduler with 4 levels
  - CPU/Memory/Disk monitoring

### Enhanced
- Test suite: 15 suites / 211 tests
- NL Bridge with intent recognition

## [0.5.0] - 2026-05-10

### Added
- **Symbolic Engine V2** (`symbolic_engine_v2.py`)
  - Layer-aware Dijkstra algorithm
  - Centrality analysis (degree, betweenness, layer authority)
  - Cycle detection
  - Layer analysis

- **Topology Propagation** (`topology_propagation.py`)
  - State machine (VALID/STALE/ERROR/DEPRECATED)
  - Failure-based degradation
  - Reverse dependency BFS propagation

- **Auto-Save System** (`mss_checkpoint.py`)
  - Checkpoint management
  - Session snapshots
  - AutoSaver (5min/10op triggers)

### Enhanced
- Test suite: 13 suites / 164 tests
- Symbolic rules Omega (Ω-R001 to Ω-R030)

## [0.4.0] - 2026-05-09

### Added
- **Organizational Resilience** (`organizational_resilience.py`)
  - 4-department baseline scanning
  - Phi-score calculation
  - Scale effect law (φ_c ≈ 1/N)
  - Diagnosis and recommendations

- **Anti-Distillation Framework**
  - Defense strategy knowledge base
  - Compliance checking

### Enhanced
- Test suite: 12 suites / 147 tests
- V3 Integration with MSSTactic

## [0.3.0] - 2026-05-08

### Added
- **NL Bridge** (`nl_bridge.py`)
  - 6 intent types: EXPLAIN, ANALYZE, REASON, VERIFY, SCAN, CHAT
  - Entity extraction
  - Layer filtering
  - Symbolic query generation

- **V3 Integration** (`mss_tactic_integrated.py`)
  - 7 new methods for Phase 2
  - Symbolic reasoning integration
  - Heat tax monitoring
  - Resilience snapshot export

### Enhanced
- Test suite: 11 suites / 131 tests
- Post-process engine with 37 rules

## [0.2.0] - 2026-05-07

### Added
- **Post-Process Engine V2** (`post_process_engine.py`)
  - 37 rules across 5 categories
  - ASSERTION, STRUCTURE, COMPLIANCE, SAFETY, QUALITY

- **Symbolic Rules Omega** (`symbolic_rules_omega.py`)
  - Initial 30 rules
  - L1/L2/L3 classification

- **Exception System** (`mss_exceptions.py`)
  - 8 exception classes
  - 29 error codes

### Enhanced
- Test suite: 8 suites / 88 tests
- KB loader with graph export

## [0.1.0] - 2026-05-06

### Added
- **Core Symbolic Engine** (`symbolic_engine.py`)
  - Graph traversal
  - Contradiction detection
  - Basic reasoning

- **Auto Analyzer** (`auto_analyzer.py`)
  - Layer detection
  - Confidence scoring
  - Forbidden word checking

- **Initial Test Suite**
  - 6 test suites
  - 31 tests

### Foundation
- Project structure established
- Knowledge base format defined (JSONL)
- Layer system (L1/L2/L3) implemented
- RSCA meta-axiom framework

## Versioning

MSS-AI follows [Semantic Versioning](https://semver.org/):
- MAJOR: Incompatible API changes
- MINOR: Backward-compatible functionality additions
- PATCH: Backward-compatible bug fixes

## Migration Guides

### 0.9 → 1.0
- New dependencies: `fastapi`, `uvicorn`, `pydantic`
- New environment variables: `MSS_API_HOST`, `MSS_API_PORT`
- CLI entry point: `mss-ai-cli`
- API entry point: `mss-ai-api`

### 0.8 → 0.9
- No breaking changes
- New CLI module added
- Enhanced NL Bridge V2

### 0.7 → 0.8
- KB loader API changed: `load_all()` returns int, use `to_graph()` for graph
- Symbolic engine V3 is separate module, not replacing V2
- UTF-8 encoding required (run `setup_utf8.py`)
