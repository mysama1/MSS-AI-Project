# LLLM 工具箱深度分析 — MSS 意义工程学视角

## 工具箱全景

```
lllm/proxies/
├── base.py              ← BaseProxy + @endpoint + @tactic_endpoint
├── interpreter.py       ← AgentInterpreter (Python沙盒)
├── proxy_tools.py       ← query_api_doc / run_python
├── prompt_template.py   ← 代理的 Prompt 模板
└── builtin/
    ├── exa_proxy.py     ← Exa 语义搜索 (向量+关键词)
    ├── fmp_proxy.py     ← Financial Modeling Prep (金融数据)
    ├── fred_proxy.py    ← 美联储经济数据
    ├── gt_proxy.py      ← Google Trends + 类别/地区json
    ├── msd_proxy.py     ← (market statistics data?)
    └── wa_proxy.py      ← Wolfram Alpha 计算引擎
```

**工具三层结构**:
```
L3 — 技能/Skills        → 可发现、可安装的 agent 能力包
L2 — 代理/Proxy          → API → 结构化目录 → Agent 可编程调用
L1 — 沙盒/Interpreter    → Agent 自写 Python → 跨 turn 状态持续
L0 — 函数/@tool          → 单次调用 → JSON Schema → 模型可见
```

---

## 一、工具箱的 6 个设计亮点（值得吸收）

### 1. 🔥 Proxy 的自发现模式 — "agent 不需要记住 API"

```python
# Agent 第一次接触 Exa proxy:
query_api_doc("exa")
# → 返回所有 endpoint: search, contents, find_similar
# → 每个 endpoint 的参数名/类型/默认值/示例

# 然后才调用:
results = CALL_API("exa/search", {"query": "MSS meaning supremacy", "num_results": 5})
```

**MSS 的对应缺口**: 我们的 `skill_api.py` (53000端口, 13端点) 没有自发现层。Agent 要么被硬编码告诉有哪些端点，要么猜。

**吸收**: 给 `skill_api.py` 加一个 `/docs` 端点 → 返回所有端点签名 → Agent 可以 `query_skill_api("defer_guard")` 后调用。

### 2. 🔥 AgentInterpreter — "Agent 自己的 Python 笔记本"

```python
# Turn 1: 获取数据
run_python("prices = CALL_API('fmp/price', {'symbol': 'AAPL', 'period': '1y'})")

# Turn 2: 分析数据（prices 变量从 Turn 1 存活！）
run_python("import numpy as np; print(f'Mean: {np.mean(prices)}')")

# Turn 3: 错了就改
run_python("prices_filtered = [p for p in prices if p > 100]; print(len(prices_filtered))")
```

**关键设计**: 持久化 namespace + 超时线程 + stdout 捕获 + traceback 反馈。Agent 可以通过 `run_python` → 看到 traceback → 修正代码 → 再跑 — 形成一个自主的"编码-报错-修复"闭环。

**MSS 的对应缺口**: 我们的 `heat_tax_profiler.py` / `pipeline.py` 都是人类调用而非 Agent 调用。没有给 Agent 一个"自写自修正 Python"的沙盒。

**吸收**: 给 MSS Agent 一个 `mss_sandbox` — 带 Δ 限定的 Python 沙盒（只能调用意义场允许的工具，热税超限自动熔断）。

### 3. 🔥 工具系统三模式 — 耦合/解耦/URL引用

```python
# 模式1: 耦合 — @tool 装饰 Python 函数，schema+实现一块传给 Prompt
@tool(description="Get weather")
def get_weather(city: str) -> str: ...

prompt = Prompt(function_list=[get_weather])

# 模式2: 解耦 — Prompt 声明 Header，@tool(name=...) 提供实现
prompt = Prompt(function_list=["shared_pkg.tools:get_weather"])
# ... 运行时 LLLM 按 package key 自动绑定

# 模式3: URL 引用 — 通过包命名空间引用，不需要 import
prompt = Prompt(function_list=["shared_pkg.tools:search"])
```

**MSS 当前**: 只有模式1（直接 import 函数作为工具）。没有包级别命名空间、没有解耦声明。

### 4. 🔥 Tactic 作为工具 — "递归的 Agent 系统"

```python
# 一个完整的 Tactic 可以暴露为 Proxy 的 endpoint
@BaseProxy.tactic_endpoint(
    tactic_url="code_review_pkg.tactics:security_audit",
    endpoint="security",
    category="audit",
)
# 然后 Agent 可以通过 CALL_API 调用它:
# CALL_API("my_proxy/security", {"target": "core/pipeline.py"})
```

**这是革命性的**: Agent A 调用 Agent B 就像调用一个函数。Agent B 的整个认知链（多步推理、工具调用、异常处理）对 A 来说只是一个 endpoint。

**MSS 当前**: SceneRouter 做 routing 但被调用者是不可递归的 — MSS Agent 不能以工具形式调用另一个 MSS Agent。

### 5. 🔥 LogStore — SQLite + session tagging + cost aggregation

```python
session.log("step 1 complete")           # 打标签
session.tag("research", "finance")       # 分类
cost = session.aggregate_cost()          # 按 session/agent/tag 聚合费用
```

**MSS 当前**: `conv_search.py` 的搜索是反向的（事后搜索），没有正向的 session 级标注。LogStore 提供了热税的**会计视角**。

### 6. 🔥 并发执行 — bcall/acall/ccall

```
bcall() — 批量（batch）
acall() — 异步（async）
ccall() — 并发（concurrent）
```

多个 Agent 可以同时出结果。对于 MSS 的 quorum/MCDP（需要多 Agent 共识），这是基础。

---

## 二、工具箱的 4 个结构性盲区（MSS 的切入点）

### 🔴 盲区 1: 工具调用的意义场无评估

```
LLLM: Agent 调用了 CALL_API("fmp/price") → 返回了数据 → 成功
MSS:  Agent 调用了 CALL_API("fmp/price") → 返回了数据
      → 但这次调用对 Δ 的影响是？
      → 热税花了多少（L1 token + L2 意义）？
      → 这次工具调用是"扩展了理解"还是"消费了预算换了一串数字"？
```

**LLLM 完全不知道工具调用的意义价值**。它只知道"调用成功"和"返回字节数"。

### 🔴 盲区 2: Python 沙盒无约束

```python
# LLLM 的 AgentInterpreter 允许任意 Python:
run_python("import os; os.system('rm -rf /')")  # 没有防护
```

LLLM 明确说了 "suitable for trusted LLM-generated code... For stronger isolation, swap the exec backend with RestrictedPython" — 但这不是默认行为，也没有意义场约束。

**MSS 可以给沙盒加三层防护**:
1. **白名单导入** — 只能 import 意义场批准的模块
2. **热税限额** — 每次 run_python 消耗 Δ 预算
3. **禁止副作用的工具调用** — 只能调标记为 `@mss_tool(read_only=True)` 的函数

### 🔴 盲区 3: 没有工具退化检测

Agent 每次调工具都重新发现 API（`query_api_doc`），但 LLLM 不知道：
- 第3次调同一个 endpoint → 可能是合理复用
- 第15次调同一个 endpoint → 可能是退化（重复问同一问题）
- 第50次调同一个 endpoint → 确定是意义黑洞（H601 搜索退化）

**MSS 的 H601 搜索退化定理正好填补这个盲区**: 给工具调用加 `call_count` 计数器 + 当 `P ≤ 1-(1-ε)^⌊k/τ⌋` 时触发警报。

### 🔴 盲区 4: Proxy 之间无信任 budget

```
Agent 可以调 exa/search → fmp/price → fred/gdp → gt/trends → ...
每个调用都当成独立的，没有:
  - "你已经在这个 session 花了 $0.42，预算还剩 $0.58"
  - "你调了 exa 15 次/fmp 只 1 次 — 是否被 exa 结果带偏了？"
  - "fred/gdp 这个数据源的可信度是 0.7，应给更低的 routing 权重"
```

**MSS 的 SceneRouter + trust_budget 正好填这个**: 每个 Proxy 有自己的 trust_score, heat_tax_budget, 调用频率上限。

---

## 三、吸收优先级

### P0 — 本周可做 (3项)

| # | 吸收什么 | MSS 实现 |
|---|---------|----------|
| 1 | AgentInterpreter 沙盒 | `mss_sandbox.py` — 带 Δ/热税限制的 Python 沙盒 |
| 2 | 工具自发现 | `skill_api.py` 加 `/docs` 端点 + `query_tool_doc()` |
| 3 | 工具调用热税追踪 | `@mss_tool` decorator — 每次调用记录热税+Δ |

### P1 — 本月可做 (3项)

| # | 吸收什么 | MSS 实现 |
|---|---------|----------|
| 4 | 工具三模式 | 包命名空间 + 解耦声明 + URL引用 |
| 5 | Tactic 作为工具 | `MSSTactic.as_tool()` — agent 可递归调用 agent |
| 6 | LogStore | SQLite session logging + cost/heat_tax aggregation |

### P2 — 远期 (2项)

| # | 吸收什么 | MSS 实现 |
|---|---------|----------|
| 7 | 并发执行 | bcall/acall/ccall for multi-agent consensus |
| 8 | 工具退化检测 | H601 退化定理 → call_count + escape probability |

---

## 四、一句话评价

> **LLLM 的工具箱是"最会编程的 agent"的梦想工作台** — 自发现 API → Python 沙盒 → 多 Proxy 协同 → 递归 Tactic。但完全盲于"这个工具调用值不值"、"Agent 是否在退化"、"信任网络是否在腐蚀"。MSS 可以把这块工作台升级为"有意义良知的工作台"。

---

**分析日期**: 2026-06-17 | **来源**: GitHub raw源码 (interpreter.py, proxy_tools.py, base.py, exa_proxy.py) + lllm.one 文档
