# MSS-VDP v2.0

**Verification Discipline Protocol** — Multi-language code quality, security, and compliance scanner.

## Quick Start

```bash
pip install mss-vdp

# Scan Python
vdp-scan src/ --json

# Scan JavaScript
vdp-js src/ --json

# Full pipeline (all languages)
vdp-pipeline . --json

# Smoke test (19 checks)
vdp-smoke
```

## Supported Languages (10)

| Language | Command | Engine | Rules |
|----------|---------|--------|-------|
| Python | `vdp-scan` | tree-sitter | V1-V6 |
| JavaScript/TS | `vdp-js` | tree-sitter | V1-V9 |
| Rust | `vdp-rust` | tree-sitter | R1-R5 |
| Java | `vdp-scan --java` | tree-sitter | J1-J5 |
| C/C++ | `vdp-scan --cpp` | tree-sitter | C1-C4 |
| Go | `vdp-go` | tree-sitter | G1-G5 |
| Ruby | `vdp-ruby` | tree-sitter | R1-R5 |
| PHP | `vdp-php` | tree-sitter | P1-P5 |
| Kotlin | `vdp-kotlin` | regex | K1-K5 |
| C# | `vdp-csharp` | regex | C1-C5 |

## Tools

### Runtimes
- **Rate Limiter** — Token bucket for API protection
- **Service Monitor** — Health check + Lark/Slack alerts
- **Lock Profiler** — Thread contention detection
- **Memory Profiler** — tracemalloc leak detection
- **Fuzzer** — Random mutation testing

### Domain Tools
- **PowerShell Verify** — 11-command PS safety checker
- **PowerShell Judge** — Golden answer benchmark
- **Python Clean** — venv/pyc/pip diagnostics
- **Android/iOS Verify** — Mobile dev diagnostics

### Analysis
- **Org Resilience** — Organizational health + 3-layer Tuning Degree
- **Content Compliance** — Document quality scanner
- **LLM Benchmark** — Offline/live/regression LLM evaluation
- **VDP DSL** — Custom rule engine (YAML-based)

## CI/CD

```yaml
# GitHub Actions
.github/workflows/vdp-pipeline.yml

# GitLab CI
.gitlab-ci.yml
```

## License

MIT
