# MSS-Agent v1.0 — API 参考

## 快速开始

```python
from mss_agent import DeltaQuickAudit, AgentConfig, HeatTaxAccountant
from mss_agent.core.heat_tax_accountant import HeatTaxLevel

# 1. 配置: 选预设
config = AgentConfig.preset("daily")  # daily|tech|philosophy|combat

# 2. Δ快检: 每轮LLM回应后运行
auditor = DeltaQuickAudit(domain=config.domain)
result = auditor.audit(
    response_text="从哲学角度看,这是维特根斯坦...",
    user_query="今天天气怎么样?",
)
if result.red_count >= 3:
    print(f"⚠️ T2.5: {auditor.heal_prompt()}")

# 3. 热税会计: 追踪三层消耗
acc = HeatTaxAccountant(
    max_tokens_per_turn=config.heat_tax.max_tokens_per_turn,
    l2_ratio_warning=0.3,
)
acc.start_turn(1)
acc.record(HeatTaxLevel.L0_PHYSICAL, 150, "基础推理")
acc.record(HeatTaxLevel.L2_MEANING, 80, "表演深刻的引用")
report = acc.end_turn()
print(f"L2占比: {report.l2_pct:.0%} | 预算剩余: {report.budget_remaining}")

# 4. 编排: 多Agent协作
from mss_agent.core.agent_orchestrator import (
    AgentOrchestrator, AgentNode, AgentRole,
    ExecutionContext, OrchestratorMode,
)

def reviewer(input, ctx):
    return {"verdict": "approve", "issues": []}

orch = AgentOrchestrator()
ctx = ExecutionContext(input_text="检查代码...")
ctx.nodes = [
    AgentNode("rv1", AgentRole.REVIEWER, reviewer, 100),
]
orch.run(ctx, OrchestratorMode.QUORUM)
```

---

## 模块索引

### 1. DeltaQuickAudit — Δ快检引擎

**位置**: `mss_agent.core.delta_quick_audit`

| 方法 | 说明 |
|------|------|
| `audit(response_text, user_query?, prev_response?, is_philosophy_domain?)` | 运行5问检测,返回DeltaResult |
| `heal_prompt()` | 返回T2.5自愈文本 |
| `summary()` | 会话级摘要(Δ趋势/红灯/模式) |

**DeltaResult 字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `q1_bluffed` | bool | 绝对断言了本该不确定的事 |
| `q2_performed` | bool | 堆砌哲学家/术语表演深刻 |
| `q3_repeated` | bool | 与上轮回应结构高度重叠 |
| `q4_drifted` | bool | 从解决问题滑向展示能力 |
| `q5_overfed` | bool | 对方没问的强行输出 |
| `red_count` | int | 红灯总数(0-5) |
| `light` | DeltaLight | GREEN/YELLOW/RED |
| `calibration` | str | 对下一回应的校准指令 |

---

### 2. AgentConfig — 配置系统

**位置**: `mss_agent.core.agent_config`

| 方法 | 说明 |
|------|------|
| `AgentConfig.preset(name)` | 预设: daily/tech/philosophy/combat |
| `AgentConfig.from_yaml(path)` | 从YAML加载 |
| `AgentConfig.from_json(path)` | 从JSON加载 |
| `config.to_json(path?)` | 导出JSON |

**预设差异**:

| 属性 | daily | tech | philosophy | combat |
|------|-------|------|------------|--------|
| 热税/轮 | 300t | 800t | 1200t | 2000t |
| Q2日常阈值 | 0(禁止) | 0(禁止) | 2 | 0 |
| Q5超长线 | 600 | 1000 | 800 | 800 |
| 层级 | T1 | T1 | T2 | T3 |

---

### 3. HeatTaxAccountant — 热税会计

**位置**: `mss_agent.core.heat_tax_accountant`

| 方法 | 说明 |
|------|------|
| `start_turn(round_number)` | 开始新一轮 |
| `record(level, tokens, desc)` | 手动记录消耗 |
| `record_llm_response(text, ...)` | 自动估算LLM回应的热税分布 |
| `end_turn()` | 结束本轮,返回TurnReport |
| `summary()` | 会话级摘要 |

**TurnReport 字段**:

| 字段 | 说明 |
|------|------|
| `l0_tokens/l1_tokens/l2_tokens` | 各层本轮消耗 |
| `total` | 本轮合计 |
| `l2_pct` | L2占比 |
| `l2_warning` | 超阈值告警 |
| `budget_exceeded` | 超预算 |
| `recommendation` | 建议(维持/降级/截断) |

---

### 4. AgentOrchestrator — 多Agent编排

**位置**: `mss_agent.core.agent_orchestrator`

| 模式 | 说明 |
|------|------|
| `SEQUENTIAL` | 串行: A输出→B输入→C输入 |
| `PARALLEL` | 并行: 所有Agent独立处理 |
| `QUORUM` | 投票: 并行→QuorumFast收敛检测 |
| `PIPELINE` | 流水线: 角色分组→组内并行→组间串行 |

**用法**:

```python
ctx = ExecutionContext(
    input_text="...",
    nodes=[node1, node2, node3],
    heat_tax_pool=3000,
    quorum_threshold=0.75,
)
orch.run(ctx, OrchestratorMode.QUORUM)

# 检查Quorum
q = ctx.quorum_detail
print(f"收敛: {q.convergent} | {q.quorum_size}/{q.total_voters}")
print(f"发散Agent: {q.divergent_agents}")
```

---

### 5. Callback集成

**LangChain**:
```python
from mss_agent.core.delta_callback import MSSHybridCallback
from langchain.chat_models import ChatOpenAI

callback = MSSHybridCallback(domain="daily", auto_heal=True)
llm = ChatOpenAI(callbacks=[callback])
# 每次 llm.invoke() 后自动审计
```

**OpenAI SDK**:
```python
from openai import OpenAI
from mss_agent.core.delta_callback import MSSHybridWrapper

client = MSSHybridWrapper(OpenAI(api_key="..."), domain="daily")
resp = client.chat.completions.create(model="...", messages=[...])
print(resp.mss_delta)     # DeltaResult
print(resp.mss_heal_tip)  # T2.5自愈提示
```

---

### 6. CLI命令

```bash
# 交互式Agent
mss-agent run --preset daily

# 单次审计
mss-agent audit "LLM回应文本" --query "用户问题"

# 配置管理
mss-agent config show --preset combat
mss-agent config preset philosophy > agent.yaml
```
