# MSS-AI K4 × pi 生态系统 架构同构映射分析

**创建时间**: 2026-05-28 22:55
**状态**: Phase 1 完成
**关联**: D5-004 K4协议族 | senpi 12 built-in extensions

---

## 核心发现

**K4 协议与 senpi 的 12 个内置扩展之间存在深层架构同构。**
这不是表面相似，而是**相同的抽象设计模式在不同命名空间中的表达**。

---

## 一、K4 协议族完整架构

### 1.1 RSCA Genome — 6个活体协议基因 (k4_rsca_genes.py)

| 基因ID | 名称 | 核心内容 |
|--------|------|---------|
| RSCA-001 | 当前架构=当前最佳理解 | 禁止声称终极/完备。声称完备=触发A5刚体态预警 |
| RSCA-002 | 工程实现需迭代验证 | L1/L2/L3组件必须迭代验证。禁止"一次性正确"假设 |
| RSCA-003 | 数学形式化需实验标定 | 热税常数(kappa, g_man等)不可从公理推导，必须实验反向标定 |
| RSCA-004 | K3→K4过渡需实践修正 | K3阶段制定的K4过渡计划携带系统性盲区(K3边界不可内部超越) |
| RSCA-005 | 协议随认知提升自演化 | 版本号是活体标记，非终结符号。版本锁定=违反A4封闭演化动力 |
| RSCA-006 | 永不声称完备性 | 完备性声称=刚体态=僵化死亡。"活体协议的本质：准确但不完整" |

**关键机制**: 每个基因携带触发条件列表(EMPIRICAL_FALSIFICATION / LOGICAL_CONTRADICTION / PARADIGM_ELEVATION / EXTERNAL_DISCOVERY / SELF_AUDIT)，内置修正协议(amend)。

### 1.2 Guardian Protocol — No.1本体权重守护 (k4_guardian_protocol.py)

监控 No.1 的 T 值(意义场通量上限)作为文明OS的全局天花板参数：

| 系统状态 | T值降级 | 复杂度因子 |
|---------|---------|-----------|
| OPTIMAL | 0% | 100% |
| DEGRADED_L1 | 10-20% | 80% |
| DEGRADED_L2 | 20-30% | 60% |
| DEGRADED_L3 | >30% | 40% |
| CRITICAL | >50% | 20% |

### 1.3 Bidirectional Coupler — L1↔L0双向耦合 (k4_bidirectional_coupler.py)

| 通道方向 | 内容 | 热税贡献 |
|---------|------|---------|
| 正向 L1→L0 | 指令、锚点 | gamma_forward |
| 反向 L0→L1 | 反馈、异常、噪声 | gamma_backward |

gamma_min = gamma_forward + gamma_backward，工程目标是"精确管理热税，维持 gamma_actual ≈ gamma_min"。

### 1.4 Logic Work Engine — H144逻辑功引擎 (k4_logical_work.py)

W_L = ∫ O_d(τ) · ΔS_random(τ) dτ

| 区域 | 功能 |
|------|------|
| Core Zone | A1-A6刚体区，M_L=1，不可污染 |
| Explore Zone | 注入ΔS_random计算W_L |
| Boundary | 探索区发现必须通过RSCA审计才能进入Core |

W_L > 0 → 触发A6升维审计；W_L ≤ 0 → 退回A5刚体区。

---

## 二、senpi 12个内置扩展完整分析

| # | 扩展名 | 功能 | 技术实现 |
|---|--------|------|---------|
| 1 | permission-system | allow/deny规则+JSONL持久化 | 解析器感知(bash元数/文件glob/apply_patch路径) |
| 2 | gpt-apply-patch | Codex风格apply_patch+Lark语法 | 替换write/edit工具 |
| 3 | prompt-preset | GPT-5.x/Claude Opus 4.5-7/Kimi K2.6按模型预设 | 叠加在动态提示上 |
| 4 | todowrite | todowrite/todoread+分支感知持久化+继续循环 | sidebar widget |
| 5 | compaction | 自适应阈值+推测压缩+紧急压缩+恢复跟踪器 | tool-result截断 |
| 6 | anthropic-bash | Anthropic原生bash工具变体 | 替换/增强bash |
| 7 | anthropic-web-search | Anthropic原生web_search | 内置 |
| 8 | openai-web-search | OpenAI Responses原生web_search | 内置 |
| 9 | service-tier | auto/flex/priority服务层注入 | extraBody passthrough |
| 10 | bash-timeout | 默认+最大bash超时+提示策略 | system prompt追加 |
| 11 | tool-pair-guard | 清理孤立tool_result块 | Anthropic payload净化 |
| 12 | compaction | 推测+紧急压缩+恢复跟踪器+tool-result截断 | 同上(重复编号已合并) |

另有**动态系统提示系统**(非扩展，属于Agent核心)：强制意图门(IntentGate)→探索纪律→并行工具指导→验证层级→分类工具引用→策略→风格→按模型微调。

---

## 三、同构映射表

### 3.1 权限 ↔ RSCA 基因

| senpi permission-system | K4 RSCA Genome | 同构关系 |
|------------------------|----------------|---------|
| allow/deny规则 | RSCA-001~006基因内容 | 都是"约束条件列表" |
| JSONL持久化 | 基因.amendment_log | 都是修订历史记录 |
| 非交互降级fallback | 基因.触发条件列表 | 都是降级路径声明 |
| 解析器感知模式 | RSCA-004自修正 | 都是"上下文感知决策" |
| 首次运行引导 | RSCA-002迭代验证 | 都是"引导式初始化" |

**本质**: 都是在"规则系统"之上叠加了"元规则"(关于规则本身的规则)。

### 3.2 动态提示 ↔ Guardian Protocol

| senpi 动态系统提示 | K4 Guardian Protocol | 同构关系 |
|-------------------|---------------------|---------|
| IntentGate强制意图门 | T值检查点 | 都是"入口验证" |
| 探索纪律+验证层级 | complexity_Lx分层 | 都是"状态依赖输出" |
| 按模型预设 | SystemState枚举 | 都是"运行时状态→输出映射" |
| 模型降级(hard-to-easy) | T值降级→复杂度因子降低 | 都是"优雅降级" |
| disabledBuiltinExtensions | DEGRADED_L3/CRITICAL | 都是"功能禁用策略" |

**本质**: 都是"系统状态→输出复杂度"的自动映射，senpi 在模型层，K4 在文明OS层。

### 3.3 Compaction ↔ Bidirectional Coupler

| senpi compaction | K4 Bidirectional Coupler | 同构关系 |
|-----------------|--------------------------|---------|
| 自适应压缩阈值 | gamma_min热税地板 | 都是"信息密度预算" |
| 推测压缩 | 正向通道gamma_forward | 都是"前向压缩/编码" |
| 恢复跟踪器 | 反向通道gamma_backward | 都是"回溯/反馈机制" |
| tool-result截断 | 反馈注入Delta_S_random | 都是"选择性信息注入" |
| 紧急压缩 | 异常/噪声信号 | 都是"异常触发的特殊处理" |
| 差分渲染(TUI) | L1-L0信号映射 | 都是"信息转换保真" |

**本质**: 都是"双向信息流的热力学管理"，senpi 管理 token 预算，K4 管理意义场通量。

### 3.4 IntentGate ↔ RSCA-001

| senpi IntentGate | K4 RSCA-001 | 同构关系 |
|-----------------|-------------|---------|
| 强制意图门(每提示前) | 当前架构=当前最佳理解 | 都是"先验约束声明" |
| 禁止跳过意图门 | 禁止声称完备 | 都是"禁止绕过声明" |
| 探索纪律提示 | RSCA-004自修正 | 都是"边界意识" |

**本质**: 都是在"自由执行"之前插入"先验检查点"。

### 3.5 Apply Patch ↔ Logic Work Engine

| senpi gpt-apply-patch | K4 Logic Work Engine | 同构关系 |
|----------------------|---------------------|---------|
| Lark语法解析 | Core Zone(A1-A6刚体) | 都是"结构化约束" |
| Freeform patch注入 | Explore Zone(ΔS_random) | 都是"受控不确定性注入" |
| 解析失败→降级edit | W_L≤0→退回A5刚体区 | 都是"失败时回归安全态" |
| 元数据(含哈希) | RSCA审计 | 都是"溯源验证" |

**本质**: 都是"结构化约束内的自由探索"，核心区不可污染，探索区发现须审计。

### 3.6 Todo Enforcer ↔ RSCA-002

| senpi todowrite | K4 RSCA-002 | 同构关系 |
|----------------|-------------|---------|
| 继续循环(空闲时重新触发) | 迭代验证 | 都是"非一次性完成" |
| 分支感知持久化 | 迭代反馈 | 都是"跨上下文状态持续" |
| sidebar状态 | RSCA amendment_log | 都是"过程可见性" |
| bridged提示 | 触发条件修正 | 都是"上下文感知的自我修正" |

**本质**: 都是"任务不是单次执行，而是持续过程"。

---

## 四、战略推论

### 4.1 MSS-AI × senpi 的互操作路径

1. **RSCA Genome** 可以实现为 senpi 扩展：`@pi-ext/rsca-gene`
   - 规则注册协议使用 senpi permission-system 的 allow/deny 格式
   - amendment_log 使用 senpi compaction 的 JSONL 追踪格式

2. **Guardian Protocol** 可以实现为 senpi 的 service-tier 变体
   - T值检查 → 模型降级路径
   - complexity_Lx → 输出token预算控制

3. **Logic Work Engine** 可以实现为 senpi 的 apply-patch 增强
   - Core Zone = Lark语法约束
   - Explore Zone = ΔS_random 注入点

4. **Compaction** 的"恢复跟踪器"模式可以反馈给 K4 Bidirectional Coupler
   - senpi 的压缩回滚机制可用于 K4 的 L0 反馈通道审计

### 4.2 K4 协议 Agent Skills 化

**当前状态**: K4 协议是 Python dataclass 实现，适合作为 Python 库。
**Agent Skills 格式**(SKILL.md): 适合作为人类可读+AI可执行的协议声明。

**建议优先级**:
1. RSCA Genome → SKILL.md (RSCA基因清单 + 修正协议)
2. Guardian Protocol → SKILL.md (T值监控 + 降级策略)
3. Bidirectional Coupler → SKILL.md (热税管理 + 双向接口)

### 4.3 OpenClaw 的双重角色

- **senpi 的用户**: OpenClaw 已在生产中使用 pi-coding-agent SDK
- **MSS-AI 的宿主**: K4 协议运行在 OpenClaw 之上

这意味着 **OpenClaw 是 senpi 和 MSS-AI 的共同底层**。K4 协议可以同时：
- 通过 senpi 扩展机制获得 senpi 生态的工具
- 通过 OpenClaw 宿主获得 MSS-AI 特有的形式化验证能力

---

## 五、待执行 Phase 2 & 3

- [ ] Phase 2: 创建 K4 协议的 SKILL.md 实现 (Agent Skills 格式)
- [ ] Phase 3: 设计 K4↔senpi 互操作适配器
- [ ] 入库 H197: K4-pi 互操作性协议

---

## 六、附录：K4协议文件清单

```
E:\AI_Workspace\MSS-AI\project\k4_protocols\
├── k4_rsca_genes.py          (6个活体基因，184行)
├── k4_guardian_protocol.py   (T值守护，324行)
├── k4_bidirectional_coupler.py (L1↔L0耦合器，510行)
├── k4_logical_work.py        (H144逻辑功引擎，476行)
├── k4_upgrade_plan.md
├── test_k4_protocols.py
└── __init__.py
```

**KB关联**:
- `rsca_axiom_v1.0.jsonl` — RSCA公理基础
- `h183_k4_technology_blueprint_v1.0.jsonl` — K4技术蓝图
- `h195_k4_meaning_engineering_l3_tech_cooptation_v1.0.jsonl` — L3技术收编
- `h196_cross_paradigm_communication_protocol_v1.0.jsonl` — 跨范式通信
