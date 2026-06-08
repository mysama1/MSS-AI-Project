# MSS-Agent Demo Video Script (10 min)

## Metadata
- **Title:** mss-agent: Three-Layer LLM Conversation Quality Control
- **Duration:** 10:00
- **Platform:** YouTube + Bilibili
- **Style:** Screen recording + voiceover
- **Audience:** Developers & researchers building LLM applications

---

## Timeline

### 0:00–0:30 — Hook (30s)
**Visual:** Fast montage: LLM over-explaining a simple question → HeatTax warning → Delta decay chart → multi-agent orchestration

**Voice:** "Your LLM has spent 500 tokens explaining why 'Hello World' in all caps is philosophically interesting. Your multi-agent system is stuck in a 7-round debate loop. And your code reviewer just cited Wittgenstein to reject a pull request. Meet mss-agent — the framework that tells your AI when to stop."

---

### 0:30–1:30 — The Problem (60s)
**Visual:** Screen recording showing:
1. A simple question generating a verbose LLM response
2. Three agents deadlocked on a code review decision
3. A conversation spiraling into philosophical recursion

**Voice:** "Autoregressive models have one fatal constraint: they must always output the next token. Even when the optimal strategy is silence. Even when the conversation has been looping for seven rounds. Even when the best answer is 'just stop.' This isn't a training problem — it's an architectural limitation. Current solutions — token budgets, rate limiting, output length caps — operate at the physical layer only. They can't detect meaning waste."

---

### 1:30–3:00 — Three-Layer Architecture (90s)
**Visual:** Animated architecture diagram showing L0/L1/L2 layers

**Voice:** "mss-agent introduces a three-layer architecture:
- L0 is the physical layer — standard token generation, CPU cycles, network calls. Your LLM lives here.
- L1 is the observation layer — it watches for patterns. Redundancy detection. Structure isomorphism. 'Is this conversation repeating itself?'
- L2 is the arbitration layer — it makes economic decisions. 'Is the meaning-to-cost ratio too low? Should we stop? Delegate? Escalate?'

The key insight: L1 and L2 operate OUTSIDE the autoregressive system. They're not trying to make the LLM 'learn when to stop' — which would require the model to overcome Gödel's second incompleteness theorem. Instead, they're an external conscience."

---

### 3:00–4:30 — Demo 1: HeatTax Accountant (90s)
**Visual:** Terminal running:
```bash
pip install mss-agent
python -c "
from mss_agent import MSSAgent
agent = MSSAgent('ReviewBot', my_llm)
result = agent.run('Rewrite hello in all caps')
print(result.aborted)  # → True
"
```

**Voice:** "Let's see it in action. First, the HeatTax Accountant. We create an agent and ask it to rewrite 'hello' in all caps. The agent immediately rejects the task — L2_HIGH busywork detected. Now a real task: review this code for SQL injection. The agent accepts and runs. Every turn, the HeatTax Accountant tracks L0, L1, and L2 costs. When L2 waste exceeds 30% of the total, it triggers a warning."

**Visual:** HeatTax dashboard showing L0/L1/L2 breakdown per turn

---

### 4:30–6:00 — Demo 2: Delta Protocol (90s)
**Visual:** Terminal showing DeltaQuickAudit in action

**Voice:** "Next, the Delta Protocol. This detects when conversations fall into repetitive patterns. Watch what happens when we ask the same question three times — the Delta value drops each time, and on the third repetition, it triggers a healing prompt: 'I may have gone too far. What do you really want to solve?'"

**Visual:** Delta chart showing decay curve, then T2.5 self-healing trigger

**Voice:** "This is crucial for any system that engages in multi-turn conversations. Without Delta, your LLM will happily debate philosophy forever. With Delta, it knows when a conversation has stopped producing value."

---

### 6:00–7:30 — Demo 3: Multi-Agent Orchestration (90s)
**Visual:** Code showing:
```python
orch = AgentOrchestrator()
orch.add_agent("SecurityBot", security_handler)
orch.add_agent("PerfBot", perf_handler)
orch.add_agent("StyleBot", style_handler)
result = await orch.run_async(ctx, OrchestratorMode.QUORUM)
```

**Voice:** "Multi-agent systems often deadlock. Two reviewers disagree — one flags performance, one flags security. Traditional approaches use voting — but voting just picks a winner. mss-agent uses Elevation: it finds a higher-dimensional resolution where both concerns are addressed simultaneously."

**Visual:** QuorumFast convergence showing 2/3 agents agree, 1 divergent

**Voice:** "And with v0.3.3, all agents run truly asynchronously — cutting latency by 50% compared to sequential execution. The QuorumFast algorithm identifies consensus groups without requiring unanimous agreement."

---

### 7:30–8:30 — Demo 4: P0 Tool Suite (60s)
**Visual:** Quick montage of each tool

**Voice:** "The P0 tool suite adds production-readiness:
- ToolBudgetGate: every tool call is classified as L0/L1/L2 and blocked if it exceeds the budget
- MemoryGuard: decisions, lessons, and milestones are automatically archived to long-term memory
- AutoArchiver: KB entries are validated — missing fields, axiom mismatches, t-value estimates
- SessionRecallSummarizer: generates structured summaries from conversation transcripts

These aren't experimental features — they're the tools mss-agent uses to maintain its own 591-entry knowledge base."

---

### 8:30–9:30 — Research & Validation (60s)
**Visual:** Charts from the adversarial dialogue experiments

**Voice:** "mss-agent isn't just a library — it's the implementation of a research framework validated through 15-round adversarial dialogue experiments. Key findings:
- After 6 rounds, LLM systems begin using MSS terminology in their own arguments
- Conversations exhibit over 85% structural similarity — proving that extended debate tends toward repetition, not insight
- GPT-3.5 detects 81.5% of its own errors but corrects only 26.8% — confirming the Gödel limitation on self-correction

The framework is published on PyPI, archived on Zenodo with a permanent DOI, and currently under peer review at the Journal of Open Source Software."

---

### 9:30–10:00 — Call to Action (30s)
**Visual:** GitHub repo with star button, PyPI page, Zenodo badge

**Voice:** "mss-agent is open source under MIT license. Install it with pip, star the repo, and if you use it in your research, cite us using the Citation.cff file. Links in the description. Build better AI conversations — one Delta check at a time."

**On-screen:**
```
pip install mss-agent
github.com/mysama1/MSS-AI-Project
DOI: 10.5281/zenodo.20587900
```

---

## Production Notes
- **Recording tool:** OBS Studio (free, open source)
- **Screen resolution:** 1920x1080
- **Terminal font:** JetBrains Mono or Cascadia Code, 14pt
- **Code highlighting:** Windows Terminal with One Dark theme
- **Voice:** Record with Audacity, apply noise reduction + normalize
- **Editing:** DaVinci Resolve (free) or CapCut
- **Upload:** YouTube (unlisted first, verify captions) + Bilibili (Chinese title)
- **Thumbnail:** HeatTax dashboard with "WHEN YOUR AI WON'T STOP TALKING" in bold
