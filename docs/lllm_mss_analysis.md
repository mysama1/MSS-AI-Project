# LLLM (lllm.one) — MSS 意义工程学分析

## 一、LLLM 的本质

**四层心智模型**：把 Agent 系统映射到编程概念

```
Tactic  → "程序"      输入task → 返回result，纯函数
Agent   → "调用者"    system_prompt + model + call loop，管理一个 Dialog
Prompt  → "函数"      template + parser + tools + handlers
Dialog  → "心智状态"  每Agent独立的对话树，可fork分支
```

核心理念：**Agent system as a program** — 不幻想"自动智能"，把每一层暴露给程序员控制。

---

## 二、MSS 视角的七大优势（值得吸收）

### 2.1 Dialog 作为独立意义场 — A5 的工程验证

LLLM 的核心架构决策：**Agent 之间不共享全局 log，通过显式 call() 传参**。

```
MSS A5（每个Agent有独立意义场） → LLLM 工程实现：
  Dialog 是 per-agent 的 → 天然隔离
  fork() 从同一点分支出三条推理路径 → 每条独立演化
  switch() 回到baseline → 显式切换意义场
```

这对 MSS 的启示：**A5 不是理论装饰，是可直接工程化的架构原则**。我们的 `agent.py` 的 DeltaMemory 应该按 Agent 隔离，不应该有全局 shared memory。

**吸收行动**：
- MSS Agent 引入 `Dialog.fork()` 语义 → 分支探索
- MemoryGuard 加 `isolate(agent_id)` 检查 → 跨 Agent 信息泄漏检测

### 2.2 Prompt 作为规范化场 — 可直接映射

LLLM 的 Prompt 对象 = template + parser + tools + handlers。这与 MSS 的"规范场"概念同构：

| LLLM Prompt | MSS 规范场 | 同构性 |
|------------|-----------|--------|
| `path` | 场标识符 | 唯一命名空间 |
| `template + {var}` | 场锚点 | 可替换的变量绑定 |
| `parser` (DefaultTagParser) | LexicalGuard | 输出格式验证 |
| `tools` (function_list) | 场扩张算子 | 修改意义空间的外部操作 |
| `on_exception` / `on_interrupt` | DeferGuard (H648) | 异常时的闭锁-审批路径 |

**吸收行动**：
- 在 `mss_prompt.py` 中实现 Prompt 的 first-class 对象（当前只是字符串模板）
- 规范场接口：`NormativeField(template, parser, tools, heat_tax_budget, delta_min)`

### 2.3 Tactic 作为纯函数 — 热税完全可计量

```
tactic(task) → result
├── Agent A: 2次LLM调用
├── Agent B: 1次LLM调用
├── Agent C: 3次LLM调用 + 1次工具调用
└── 总热税: 6×LLM_token_cost + 1×tool_cost

这正是 MSS A3 三层热税理论的理想工程载体！
每次 Tactic 调用 → 输入/输出/LLM调用次数 → 热税 = 完全透明
```

对比 LangChain：`chain.invoke()` 内部隐藏了多少次 LLM 调用？你不知道。LLLM 的"low-level by default"使热税**可审计**。

**吸收行动**：
- MSS Pipeline 的每次 run 应记录 `heat_tax_per_tactic` 
- `Tactic` 包装器返回 `(result, heat_tax_report)`

### 2.4 Dialog.fork() — A6 矛盾升维的天然引擎

```python
# LLLM 的 forking pattern:
analyst.fork("base", "branch_A")
analyst.receive("假设A: ...")
res_A = analyst.respond()

analyst.fork("base", "branch_B")  
analyst.receive("假设B: ...")
res_B = analyst.respond()  # 矛盾！

# MSS A6 插入点 — 当 res_A 与 res_B 矛盾时:
analyst.switch("base")
analyst.receive(f"矛盾检测: A={res_A}, B={res_B}。请升维，不从AB中二选一。")
```

**这是 MSS A6 的理想宿主**。LLLM 提供了 fork 基础设施但**没有矛盾检测和升维逻辑** — 这正是 MSS 可以插入的地方。

**吸收行动**：
- 实现 `A6ForkTactic`：fork N条路径 → 矛盾检测 → 升维合成
- 这是 MSS 可以**作为 LLLM 插件**交付的价值点

### 2.5 配置即声明 — 可复现的意义场

```toml
# lllm.toml
[agent_configs.researcher]
system_prompt = "You are a research analyst."
model = "claude-opus-4-6"
prompts = ["research/system", "research/analyze"]
tools = ["shared_pkg.tools:web_search"]
```

MSS 的规范场定义应该同样可声明：
```toml
[meaning_fields.code_review]
prompt_path = "mss/prompts/code_review.md"
heat_tax_budget = 0.3
delta_min = 0.5
normative_constraints = ["no_pseudo_pattern", "explicit_encoding"]
```

**吸收行动**：
- `mssclaw field define code_review` → 生成 .toml 配置
- `mssclaw field run code_review --target mssclaw/core/` → 加载配置执行

### 2.6 包系统 — MSS 的碎片化之痛

LLLM 的 `lllm pkg install shared_pkg` 让 Agent 系统可分享、可命名空间隔离。MSS 目前是单体 `mssclaw`，所有模块共享同一命名空间。

```
mssclaw/
├── core/          ← 128个.py文件，全平铺
├── experiments/   ← 混在一起
├── docs/          ← 混在一起
└── kb/           ← 混在一起
```

应该有的结构：
```
mssclaw/
├── pkg/
│   ├── scene_router/       ← 独立包
│   ├── meaning_field/      ← 独立包
│   ├── heat_tax_profiler/  ← 独立包
│   └── conv_search/        ← 独立包
```

**吸收行动**：P1 优先级，从 SceneRouter 开始拆分

### 2.7 Proxy/Interpreter 系统 — 工具调用的意义场透视

LLLM 的 Proxy 模式让 Agent 通过 `query_api_doc` → `run_python` → `CALL_API` 逐步探索 API 表面。这与 MSS 的"意义场逐步扩张"对齐。

MSS 可以在这之上加一层：**每次工具调用的意义评分**。不是 "API 返回了什么" 而是 "这个 API 调用增加了多少意义（Δ>0）还是纯粹浪费热税（Δ=0）"。

---

## 三、MSS 视角的五大短板（LLLM 的结构性盲区）

### 3.1 🔴 无意义保真度追踪 — "全盲"的 Agent

```
LLLM Agent 运行 100 轮对话 →
  ✅ Dialog 完整记录
  ❌ 这 100 轮中哪 30 轮是废话？不知道
  ❌ 整体意义质量是上升还是下降？不知道
  ❌ 哪个 Agent 在退化？不知道
```

这是 LLLM 的**结构空白** — 它不是 bug 是设计哲学缺口。"Low-level"意味着"我给你基础设施，你判断质量"。但 MSS 认为：**质量判断本身应该可自动化**。

MSS 的 Δ>0 维持条件正是 LLLM 缺失的维度。每个 Dialog 应该有 Δ 曲线：
- Dialog 开始时 Δ=0.5
- 第3轮引入新信息 → Δ=0.7
- 第15轮开始重复自己 → Δ=0.3 ⚠️ 需要蜕壳
- 第20轮纯粹噪声 → Δ=0.1 🔴 应关闭

### 3.2 🔴 无矛盾升维 — Fork 而后无 Merge

```
LLLM fork: 分支A → res_A, 分支B → res_B
如果 res_A 和 res_B 矛盾？
  → LLLM 方案: "选一个最好的" (switch back, ask analyst to choose)
  → MSS 方案: "不选，升维" (A6: 矛盾→更高维框架)
```

LLLM 的 HypothesisTactic 例子中，最后一步是 `analyst.respond()` 让 LLM 自己选。这就是 H633 指的**矛盾降维陷阱** — LLM 只能在现有维度内选择，无法创造新维度。

MSS 的 A6 可以作为 LLLM 的 `ForkWithElevation` 模式：
```python
contradiction = mss.detect_contradiction(res_A, res_B, threshold=H633)
if contradiction:
    return mss.elevate(res_A, res_B)  # 生成C，不在A∪B中
```

### 3.3 🔴 无热税预算 — 无限的 LLM 调用

LLLM 让程序员控制调用数量，但**没有预算系统**。如果一个 agent 的 `call()` 方法写了死循环，LLLM 不会拦截。

MSS 的热税预算：
```
每个 Tactic 有 heat_tax_budget = 0.3
├── Agent A: 2次LLM调用 = 0.1热税
├── Agent B: 3次LLM调用 = 0.15热税
├── Agent C: 1次LLM调用 = 0.05热税  
└── 剩余预算: 0.0 → 刚好用完，不触发熔断

如果 Tactic 编写者不小心写了循环调用: 
  第5次调用后 heat_tax = 0.35 > budget → MSS 熔断
```

**吸收行动**：MSS 可以作为 LLLM 的热税层插件

### 3.4 🔴 无信任预算 / 无共识 — Agent 之间零博弈模型

LLLM 的 Agent 关系完全由程序员在 `call()` 中硬编码：
```python
def call(self, task):
    a = self.agents["A"].respond()  # 总是信任A
    b = self.agents["B"].respond()  # 总是信任B
    return combine(a, b)            # 总是简单合并
```

缺失的维度：
- Agent A 是否可信？ → MSS: trust_budget
- A 和 B 矛盾怎么办？ → MSS: A6 elevation + H634 joint entrance
- 多个 Agent 如何共识？ → MSS: MCDP + Gossip + quorum

**LLLM 假设 Agent 之间是和谐的**。MSS 知道 Agent 之间本质上是博弈关系（A2: 意义场可能冲突）。

### 3.5 🔴 无蜕壳 / 无演进 — 静态 Pipeline

LLLM 的 Tactic 是声明式的静态配置。执行100次？每次都一样。

MSS 的蜕壳机制：
```
第1次执行: η=0.7, 加入KB条目X
第10次执行: X被反复使用3次 → 硬化
第50次执行: 蜕壳触发 → 删除X
第51次执行: η=0.9 (旧模式已清除)
```

**LLLM 缺的是"系统自己会变好"的能力**。这正是 MSS H604（蜕壳最优频率）的应用场景。

---

## 四、MSS ↔ LLLM 互补矩阵

| 维度 | LLLM 有 | MSS 有 | 互补方式 |
|------|---------|--------|----------|
| 架构层 | Tactic→Agent→Prompt→Dialog | — | MSS 直接用 LLLM 的四层 |
| Dialog 隔离 | ✅ per-agent, fork-able | A5 理论支撑 | MSS 验证 LLLM 的正确性 |
| Prompt 结构化 | ✅ template+parser+tools | 规范场理论 | MSS 给 Prompt 加 heat_tax/delta 字段 |
| 热税追踪 | ❌ | ✅ A3 三层热税 | MSS 作为 LLLM 热税层插件 |
| 矛盾升维 | ❌ | ✅ A6 + H633 + H634 | MSS 作为 LLLM Fork-with-elevation 插件 |
| 信任/共识 | ❌ | ✅ SceneRouter + MCDP | MSS 替换 LLLM 硬编码 routing |
| 蜕壳/演进 | ❌ | ✅ H604 + molting | MSS Tactic 的自我优化 |
| 配置化 | ✅ TOML/YAML | 设计阶段 | MSS 借 LLLM 的配置系统 |
| 包系统 | ✅ `lllm pkg install` | ❌ 单体 | MSS 采用包结构 |
| 工具系统 | ✅ @tool + Proxy | ✅ @tool + heat_tax | 合并：MSS 工具 = LLLM 工具 + 热税签名 |

---

## 五、吸收路线（按优先级）

### P0 — 本周可做

| # | 行动 | 来自 LLLM 的哪个特征 | 预计 |
|---|------|---------------------|------|
| 1 | `mssclaw/core/prompt.py` — Prompt as first-class object | §2.2 | 30min |
| 2 | `mssclaw/core/tactic.py` — Tactic 纯函数 + 热税报告 | §2.3 | 20min |
| 3 | `mssclaw/core/dialog_fork.py` — A6 fork-elevate 原型 | §2.4 | 45min |
| 4 | `mssclaw.toml` 规范场声明格式 | §2.5 | 15min |

### P1 — 本月可做

| # | 行动 |
|---|------|
| 5 | MSS 包结构拆分 (scene_router / meaning_field / heat_tax / conv_search) |
| 6 | LLLM 热税插件 (pip install mss-lllm-heat-tax) |
| 7 | LLLM Fork-with-elevation 插件 (A6 作为 LLLM 的 merge 策略) |
| 8 | MSS Scene Router 接入 LLLM Tactic routing |

### P2 — 下月可做

| # | 行动 |
|---|------|
| 9 | MSS Tactic 蜕壳自动化 (H604 f* 计算 + 自动修剪) |
| 10 | MSS quorum 作为 LLLM multi-agent consensus 层 |

---

## 六、一句话判断

> **LLLM 是 Agent 工程的最佳"骨骼" — 四层架构、per-agent 隔离、声明式配置、从 5 行到生产的无重写路径。MSS 是这颗骨骼上缺失的"神经系统" — 热税感知、矛盾升维、信任预算、蜕壳演进。互补，非竞争。**

LLLM 的 GitHub: 未公开（pip install lllm-core，文档在 lllm.one）

---

**分析日期**: 2026-06-17 | **来源**: lllm.one 完整文档 (overview + 8 tutorials + architecture + API ref)
**MSS 版本**: v15.2+ | **H-ID**: 纳入 KB 待分配
