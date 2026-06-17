# MSS ↔ LLLM Normative Field 对比

## 核心对应关系

| 概念 | LLLM | MSS | 差异 |
|------|------|-----|------|
| 程序单元 | Tactic(task)→result | Tactic(task)→(result, heat_tax_report) | MSS 多了热税+Δ |
| 调用者 | Agent(system_prompt+model+loop) | Agent + MemoryGuard + DeltaMemory | MSS 多了记忆守卫 |
| 函数 | Prompt(template+parser+tools) | MSSPrompt + normative_constraints | MSS 多了约束检查 |
| 心智状态 | Dialog(per-agent, fork-able) | DialogFork + A6 contradiction detection | MSS 多了升维逻辑 |
| 工具 | @tool + Proxy + Interpreter | LLLM @tool + heat_tax_signature | MSS 工具带热税 |
| 包系统 | lllm pkg install | (设计中，借LLLM) | MSS 应该用此模式 |
| 配置 | lllm.toml | mss.toml (计划) | MSS 应声明化 |
| 约束 | 无 | DeferGuard (H648) | MSS 独有 |
| 路由 | 硬编码 call() | SceneRouter (H634) | MSS 动态信任路由 |
| 演进 | 无 | 蜕壳 (H604) | MSS 独有 |

## 吸收成果

### P0 已完成 (3个模块)

1. **mss_prompt.py** — Prompt + MSS 约束
   - `MSSPrompt`: template + parser + tools + heat_tax_budget + delta_min + normative_constraints
   - `MSSParser`: XML/markdown tag parser (LLLM 的 DefaultTagParser)
   - `can_execute()`: H648 Defer Guard 前置检查

2. **mss_tactic.py** — Tactic + 热税报告
   - `MSSTactic`: 纯函数 task→(result, report)
   - `TacticReport`: 三层热税 (L0物理/L1逻辑/L2意义) + Δ追踪
   - `TacticStep`: 每一步的细粒度热税

3. **dialog_fork.py** — Fork + A6 升维
   - `DialogFork`: LLLM 的 fork 语义
   - `detect_contradiction()`: H633 矛盾检测 (6组对立关键词)
   - `elevate()`: A6 升维框架生成
   - `resolve_with_elevation()`: 全链路 (fork→检测→升维)

## LLLM 的架构价值

LLLM 对 MSS 最重要的贡献不是技术而是**设计哲学**:

1. **"Agent system as a program"** — MSS 一度陷在"AI 自我演化"的幻想里，LLLM 提醒：Agent 系统首先是工程系统
2. **"Low-level by default"** — 热税透明的前提是暴露所有调用，不是隐藏
3. **"No global shared state"** — 验证了 A5 的工程可行性
4. **"Configuration as declaration"** — MSS 的规范场应可声明而非硬编码

## LLLM 需要 MSS 的

1. 热税预算 — 防止无限 LLM 调用
2. 矛盾升维 — 让 fork 不只是"选一个最好的"
3. 信任路由 — 让 Agent 调用不是盲目信任
4. 蜕壳机制 — 让系统越用越好而非越用越退化
5. Δ 追踪 — 知道系统在变好还是变差
