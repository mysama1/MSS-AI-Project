[![PyPI version](https://badge.fury.io/py/mss-agent.svg)](https://pypi.org/project/mss-agent/)

# MSS-Agent

**世界上第一个内置"意义场自检"的开源 Agent 框架。**

```
pip install mss-agent  # coming soon
```

## 为什么？

现有 Agent 框架 (LangChain, CrewAI, AutoGPT) 只有一个目标：**完成任务。**

MSS-Agent 有两个目标：
1. **完成任务**
2. **知道什么时候不该完成任务**

第二点，没有任何框架在做。

## 三层防御

| 层 | 名称 | 公理 | 功能 |
|----|------|------|------|
| L0 | 热税预算 | A3 | 拒绝无意义任务 (L2 意义热税 >1000x) |
| L1 | Δ检测协议 | A6 | 检测模式闭合, 触发蜕壳 |
| L2 | 升维协议 | A6 | 多Agent冲突→不是投票, 是升维 |

## 30秒入门

```python
from mss_agent import MSSAgent, HeatTaxLevel

# 配置任意 LLM
def my_llm(prompt: str) -> str:
    import ollama
    return ollama.chat("qwen3", prompt)["message"]["content"]

# 创建 Agent
agent = MSSAgent(name="Helper", llm=my_llm)

# 运行 — 内置热税预算自动拦截无意义任务
result = agent.run("帮我改写这句话：'你好'")
if result.aborted:
    print(f"Agent 拒绝: {result.reason}")
    # → Agent 拒绝: Task has LOW meaning: Pure paraphrasing...

result = agent.run("设计一个 REST API 的错误处理方案")
print(result.output)

# 健康报告
print(agent.health_report())
# → {'heat_tax': {...}, 'delta': {...}, 'memory': {'active': 5, 'closed': 2}}
```

## 热税预算 (A3)

Agent 自动评估每个任务的三层热税：
- **L0 物理热税** (token/time) → 权重 0.001
- **L1 逻辑热税** (redundancy) → 权重 1.0
- **L2 意义热税** (虚假数据/无意义任务) → 权重 **1000.0**

L2 热税过高 → Agent 拒绝执行并输出 `HeatTaxAbort`。

## Δ检测协议 (A6)

Agent 不会重复相同失败模式：
- 每个任务周期的 Δ 值 (novelty + diversity)
- Δ 连续下降 2 周期 → 触发蜕壳 → 遗忘旧模式
- "蜕壳不是失败, 是生长"

## 不是替代品, 是良心

MSS-Agent **不替代** LangChain/LlamaIndex/AutoGPT.

它是一层**可以套在任何 Agent 外面的意义场检测器**。

把 MSS-Agent 的热税预算和 Δ 协议插入你现有的 pipeline——剩下的继续用你熟悉的一切。

## 商业模式

- ✅ MIT 开源 — 核心功能永远免费
- ✅ 社区驱动 — DAU 优先, 不设付费墙
- ✅ 可选企业服务 — 部署咨询/定制集成/培训

## 许可证

MIT License. 详见 [LICENSE](LICENSE).
