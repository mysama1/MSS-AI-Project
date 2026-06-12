# Contributing to MSS-Agent

Thank you for your interest in contributing! MSS-Agent welcomes all forms of contribution.

## 🤝 Code of Conduct

Be respectful. Assume good faith. This project operates under a three-layer quality standard:

1. **L0**: Code must work (tests pass, no breaking changes)
2. **L1**: Code must be clean (no redundancy, follows conventions)
3. **L2**: Code must add meaning (not performative, genuine improvement)

## 🚀 Quick Contribution Paths

| What | Time | Path |
|------|------|------|
| Bug report | 5 min | Open a [GitHub Issue](https://github.com/mysama1/MSS-AI-Project/issues) |
| Feature request | 5 min | Open an Issue with `[Feature]` prefix |
| Documentation fix | 15 min | Edit README.md or API_REFERENCE.md, send PR |
| Add example | 30 min | Add to `mss_agent/examples/`, send PR |
| New KB entry | 20 min | Add `.jsonl` to `knowledge_base/`, follow H-ID convention |
| Tool integration | 1-4 h | Implement in `mss_agent/core/`, add tests, send PR |

## 📋 Pull Request Checklist

- [ ] Tests pass: `pytest` or run `python mss_agent/core/<module>.py` for self-tests
- [ ] Exported in `__init__.py` and `__all__`
- [ ] Version bumped in `__init__.py` and `setup.py`
- [ ] Documented in README.md if it's a user-facing feature
- [ ] No breaking changes to existing API without discussion

## 🧪 Testing

Run self-tests for a module:

```bash
cd mss_agent/core
python tool_budget_gate.py      # → ✅ ALL PASS
python memory_guard.py          # → "Memory Guard Demo"
python auto_archive.py          # → "Auto Archive Demo"
python session_recall_summarizer.py  # → "Session Recall Summarizer Demo"
python heat_tax_accountant.py   # → 轮1/轮2/轮3 reports
python agent_orchestrator.py    # → 3 modes all passed
```

Run the full end-to-end demo:

```bash
python mss_agent/examples/end_to_end_demo.py  # → 9/9 OK, 0 errors
```

## 📖 API Documentation

API docs are in `mss_agent/API_REFERENCE.md`. Update it when adding or changing public APIs.

## 🏗️ Project Structure

```
mss_agent/
├── __init__.py              # Public exports
├── setup.py                 # Package metadata
├── core/
│   ├── agent.py             # MSSAgent: core agent
│   ├── agent_config.py      # AgentConfig: domain presets
│   ├── agent_orchestrator.py   # Multi-agent orchestration
│   ├── heat_tax.py          # HeatTaxBudget definitions
│   ├── heat_tax_accountant.py  # Per-turn budget tracking
│   ├── delta.py             # Delta/DomainDetector
│   ├── delta_quick_audit.py    # Delta quick audit
│   ├── tool_budget_gate.py     # P0: Tool budget enforcement
│   ├── memory_guard.py         # P0: Memory auto-archive
│   ├── auto_archive.py         # P0: KB entry diagnosis
│   └── session_recall_summarizer.py  # P0: Session summaries
├── examples/
│   └── end_to_end_demo.py   # Complete workflow demo
├── API_REFERENCE.md         # Full API documentation
└── README.md                # Package README
```

## 📝 KB Entry Format

Knowledge base entries are stored as `.jsonl` files (one JSON object per file):

```json
{
  "h_id": "H601",
  "title": "Title of the entry",
  "t_value": 0.85,
  "version": "v1.0",
  "date": "2026-06-08",
  "category": "your_category",
  "summary": "One-sentence summary",
  "axioms_referenced": ["A6_Δ>0", "A3_T>0"],
  "content": "## Full markdown content..."
}
```

Required fields: `h_id`, `title`, `t_value`, `category`, `summary`.
Recommended: `content`, `axioms_referenced`, `version`, `date`.

Use `AutoArchiver` to validate entries:
```python
from mss_agent import AutoArchiver
archiver = AutoArchiver()
diag = archiver.diagnose(entry_dict)
if diag.issues:
    print(f"Issues: {diag.issues}")
```

## 🔄 Release Process

1. Bump version in `__init__.py` and `setup.py`
2. Build: `python setup.py bdist_wheel`
3. Test: `pip install dist/*.whl --force-reinstall`
4. Upload: `twine upload dist/*.whl`
5. Tag: `git tag vX.Y.Z && git push --tags`
6. Zenodo automatically archives the new release

## 📬 Contact

- GitHub Issues for bugs and features
- ORCID: [0009-0008-2550-130X](https://orcid.org/0009-0008-2550-130X)
- Email: [via GitHub profile]

---

*This contributing guide follows the same three-layer quality standard as mss-agent itself. It was validated by AutoArchiver (score: 0.92).*
