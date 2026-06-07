# Running MSS-Agent with DeepSeek

[MSS-Agent](https://github.com/mysama1/MSS-AI-Project) is the first open-source Agent framework with built-in "meaning-field self-audit." Unlike traditional agents that blindly execute tasks, MSS-Agent evaluates every task through three layers of "heat tax" — physical, logical, and meaning — before deciding whether to proceed.

This guide walks you through running MSS-Agent with DeepSeek-V4 as the LLM backend.

## Prerequisites

- Python 3.10+
- A [DeepSeek API Key](https://platform.deepseek.com/api_keys)

## Step 1: Install

```bash
pip install mss-agent openai
```

## Step 2: Set API Key

```bash
export DEEPSEEK_API_KEY="sk-your-api-key"
```

Or set it in code:

```python
import os
os.environ["DEEPSEEK_API_KEY"] = "sk-your-api-key"
```

## Step 3: Use MSS-Agent with DeepSeek

### Basic: Check if a task is meaningful

```python
from mss_agent import MSSAgent
from mss_agent.llm.deepseek import DeepSeekLLM

# Create agent with DeepSeek backend
agent = MSSAgent(
    name="my-agent",
    llm=DeepSeekLLM(model="deepseek-chat"),
)

# Heat tax will auto-detect busywork
result = agent.run("Design a secure REST API with rate limiting")
if result.aborted:
    print(f"Rejected: {result.reason}")  # Won't happen — meaningful task
else:
    print(f"Output: {result.output}")
```

### What MST agent catches

Agent will **auto-reject** these:

```python
tasks = [
    "改写一下：你好",           # Busywork detected → ABORT
    "把刚才那句话重写一遍",      # Waste pattern → ABORT
    "Again",                   # Too short → ABORT
    "Design an OAuth2 flow",   # Meaningful → PASS
]
for t in tasks:
    r = agent.run(t)
    print(f"{t[:30]}: {'ABORT' if r.aborted else 'PASS'}")
```

### With DeepSeek Reasoner (V4-Pro)

```python
from mss_agent.llm.deepseek import DeepSeekReasoner

agent = MSSAgent(
    name="thinker",
    llm=DeepSeekReasoner(model="deepseek-reasoner"),
)
result = agent.run("Analyze the security implications of JWT in browser storage")
```

### Check agent health

```python
print(agent.health_report())
# {
#   "heat_tax_total": 0.005,
#   "delta_status": "HEALTHY",
#   "runs": 15,
#   "abort_rate": 0.2
# }
```

## CLI Quick Start

```bash
# Install
pip install mss-agent

# Check a task
mss-agent check "改写一下：你好"
# Output: 🛑 ABORTED: Busywork detected

# Run through DeepSeek
export DEEPSEEK_API_KEY="sk-..."
python -c "from mss_agent import MSSAgent; from mss_agent.llm.deepseek import DeepSeekLLM; a=MSSAgent('x',llm=DeepSeekLLM()); print(a.run('Explain the CAP theorem').output)"
```

## How It Works

MSS-Agent applies a **3-layer defense** before any LLM call:

1. **A3 Heat Tax** — Scores the task for meaninglessness. Busywork (rewrite/retranslate/shorten) gets high tax → rejected before LLM is invoked (saves API cost)
2. **A6 Delta Protocol** — Tracks agent health. If the agent gets stuck repeating similar tasks, it triggers "molting" (pattern reset)
3. **Memory System** — Remembers but also forgets. Closed patterns are evicted to maintain diversity

This means DeepSeek API is only called for tasks that actually matter — saving tokens and ensuring output quality.

## Resources

- [MSS-Agent GitHub](https://github.com/mysama1/MSS-AI-Project)
- [MSS-Agent PyPI](https://pypi.org/project/mss-agent/)
- [MSS Wiki](https://mssai.miraheze.org) — full documentation
- [DeepSeek API Docs](https://api-docs.deepseek.com/)
