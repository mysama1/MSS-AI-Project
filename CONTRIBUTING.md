# Contributing to mssclaw

## Quick Start

```bash
# 1. Clone
git clone https://github.com/mysama1/MSS-AI-Project.git
cd MSS-AI-Project

# 2. Setup
pip install -e ".[dev]"
mssclaw init

# 3. Test
pytest tests/ -p no:cov -k "not test_vault_server and not init_env"
```

## Project Structure

```
mssclaw/
├── core/           # Core modules (70+ files)
│   ├── agent.py    # MSSAgent + L2 bridge
│   ├── vault/      # Credential vault stack
│   ├── meaning/    # Heat tax / Delta / Meaning
│   └── ...
├── agents/         # Specialized agents
├── scanner/        # Code vulnerability scanner
├── llm/            # LLM backends
├── cli.py          # Unified CLI entry point
└── config.py       # Configuration system

docs/               # Documentation
tests/              # 126 tests
```

## Coding Standards

- Python 3.10+, type hints recommended
- All new features need tests
- Error messages in Chinese + English
- No breaking changes without deprecation notice

## Pull Requests

1. Fork the repo
2. Create a feature branch
3. Add tests for new code
4. Run `pytest tests/` before submitting
5. Use descriptive commit messages (参照现有格式)

## What We Need

- 📝 Docstrings on public methods
- 🧪 Tests for modules with <50% coverage
- 🌐 Translations (English README improvements)
- 🐛 Bug reports with reproduction steps
