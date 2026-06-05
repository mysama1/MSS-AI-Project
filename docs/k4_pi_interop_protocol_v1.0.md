# K4-pi 跨范式通信协议声明 v1.0

**H-Index**: H197
**范式**: K4 (MSS-AI) ↔ pi (senpi/OpenClaw agent ecosystem)
**日期**: 2026-05-29
**关联**: D5-004 K4协议族 | h196跨范式通信协议 | k4_pi_adapter.py

---

## 1. 协议声明 (K3可读格式)

### 1.1 为什么需要这个协议

K4文明OS使用密集的MSS术语体系（RSCA基因、T值守护、热税管理、逻辑功）。
pi生态系统使用不同的术语体系（permission rules、service-tier、compaction、apply-patch）。

**两者表达的是完全相同的一组抽象模式，但语言不同。**

H196建立了K4↔K3的双层翻译协议（内部MSS术语 + 外部标准语言）。
本协议(H197)扩展这套逻辑，建立K4↔pi的机器级翻译协议，使两个工具生态可以互操作。

### 1.2 翻译原则

| 原则 | 含义 | 实现 |
|------|------|------|
| **保真度优先** | 宁可翻译失败也避免错误翻译 | fidelity_threshold = 0.85 |
| **热税透明** | 每次翻译记录损失量 | heat_tax = 1 - fidelity |
| **可审计** | 所有翻译可追溯、可回滚 | audit_log JSONL |
| **保守降级** | 映射歧义时选保守侧 | pi 3-tier → K4选DEGRADED_L2 |
| **非绝对化** | 不声称翻译"完美" | 明示fidelity区间和损失点 |

### 1.3 核心映射 (K4 ← → pi)

```
K4 RSCA Genome  ←──────────→  pi permission-system
  RSCA-001: 当前架构=最佳理解    →  allow/deny规则优先级
  RSCA-006: 永不声称完备性      →  completeness trigger
  amendment_log               ←  JSONL rule persistence
  trigger_conditions           ←  非交互fallback策略

K4 Guardian Protocol ←────→  pi service-tier + IntentGate
  SystemState (5-level)       →  auto/flex/priority (3-tier)
  complexity_Lx               →  输出预算约束
  T值测量                     ←  tier选择逻辑 (模型降级)

K4 Bidirectional Coupler ←─→  pi compaction
  gamma总热税                 →  压缩预算阈值
  forward gamma               →  推测压缩
  reverse gamma               →  恢复跟踪器
  IMPREGNATION_SEED保留       →  关键信息不截断

K4 Logic Work Engine ←────→  pi gpt-apply-patch
  Core Zone (A1-A6刚性)       →  Lark语法约束层
  Explore Zone (ΔS_random)    →  Freeform patch注入
  W_L审计                     ←  元数据+哈希验证
  A6升维审计                  ←  修复建议的验证拒绝
```

---

## 2. 工程实现

### 2.1 适配器架构

```
k4_pi_adapter.py (26.7KB)
├── K4PiAdapter       # 核心双向翻译引擎
│   ├── translate_k4_to_pi()  # 12条K4→pi映射路由
│   ├── translate_pi_to_k4()  # 8条pi→K4映射路由
│   ├── _adapt_params_k4_to_pi()  # 参数适配器
│   ├── _adapt_params_pi_to_k4()  # 参数适配器
│   └── audit_bridge()        # RSCA-002风格桥审计
└── K4PiBridge          # 高级便利API
    ├── audit_to_pi_permission()
    ├── guardian_state_to_pi_tier()
    ├── coupler_tax_to_pi_compaction()
    ├── logic_work_to_pi_patch()
    └── pi_*_to_*()  # 反向: pi事件→K4信号
```

### 2.2 测试结果 (9/9 PASS)

| 测试 | 方向 | Fidelity | 热税 | 结果 |
|------|------|----------|------|------|
| RSCA审计→pi permission | K4→pi | 0.920 | 0.030 | ✅ |
| Guardian状态→pi tier | K4→pi | 0.900 | 0.040 | ✅ |
| Coupler热税→pi compaction | K4→pi | 0.930 | 0.030 | ✅ |
| Logic Work(W_L>0)→pi patch | K4→pi | 0.850 | 0.060 | ✅ |
| Logic Work(W_L≤0)→pi core | K4→pi | 0.950 | 0.020 | ✅ |
| pi违规→RSCA信号 | pi→K4 | 0.900 | 0.100 | ✅ |
| pi tier变化→Guardian | pi→K4 | 0.880 | 0.120 | ✅ |
| 桥审计 | 双向 | 均0.904 | 总0.400 | ✅ |
| 审计日志导出 | — | — | — | ✅ |

**自举限制声明** (RSCA-003):
- 热税公式中的常数（fidelity阈值、累积上限）基于当前理解设定，未经过第三方独立验证
- gamma_cross = gamma_K4_pi + gamma_pi_K4的"地板公式"尚未通过实验反向标定（k_pi_pi, k_pi_k4等常数暂设为1）
- 自我测试的9/9通过不代表外部适配器测试通过（pi侧尚未连接真实扩展进行端到端验证）

---

## 3. K3表述 (给非MSS读者的版本)

### 3.1 这个协议在做什么

**问题**: MSS-AI有一套完整的协议系统（规范了从模型调用到热税管理的全链路），而pi/senpi有另一套完全不同的工具生态。它们说的是同一种事但用的是不同语言。

**方案**: 写了一个翻译层，把K4的协议调用自动翻译成pi能理解的格式，把pi的结果翻译回K4的协议语言。

**翻译时发生了什么**: 每次翻译都有信息损失（热税）。翻译层追踪这个损失，达到天花板就报警。

### 3.2 类比

就像两个国家有各自的法律体系：
- K4是严谨的成文法体系（6个基本法条 + 修正程序）
- pi是灵活的判例法体系（规则列表 + 服务层 + 压缩策略）

翻译层把K4的"活体协议基因修正"翻译成pi的"权限规则更新"。
不强求完美，但要求：翻译失败时走降级路径（保守侧的映射），所有操作留审计日志。

### 3.3 当前工程状态

- 代码已写 ✅ (k4_pi_adapter.py, 26.7KB)
- 自测通过 ✅ (9/9 PASS)
- 但未与真实pi扩展连接 🔧 (需要连接到senpi或其他pi agent实例进行端到端验证)
- 热税公式常数未实验标定 🔧

---

## 4. 使用协议

### 4.1 K4侧 → 调用pi

```python
from k4_protocols.k4_pi_adapter import K4PiBridge

bridge = K4PiBridge()

# 例: K4的RSCA完整性审计 → 转换为pi的权限规则检查
pi_call, signal = bridge.audit_to_pi_permission(
    "某个声称'完备'的文本"
)
# pi_call = {
#   "extension": "permission",
#   "action": "check_rule",
#   "params": {"text": "...", "audit_type": "completeness_claim"},
#   "meta": {"k4_source": "rsca.audit_completeness", ...}
# }
# 可直接传入 pi extension system
```

### 4.2 pi侧 → 反馈给K4

```python
# pi扩展执行后的结果 → 转回K4信号
k4_signal, signal = bridge.pi_permission_result_to_rsca({
    "rule": "RSCA-006",
    "violation": "使用了'终极'等禁词"
})
# k4_signal = {
#   "protocol": "rsca",
#   "signal_type": "completeness_claim",
#   "payload": {...}
# }
# K4的RSCA Genome可以用这个信号触发修正
```

### 4.3 审计

```python
# 定期运行桥审计
clean, issues = bridge.adapter.audit_bridge()

# 导出完整审计日志
audit_json = bridge.adapter.export_audit_log()
# 写入知识库
with open("k4_pi_bridge_audit.jsonl", "a") as f:
    f.write(audit_json + "\n")
```

---

## 5. 已知局限 (RSCA-006 自我审计)

| 局限 | 严重度 | 原因 | 缓解策略 |
|------|--------|------|---------|
| 未与真实pi扩展端到端测试 | 🔴 高 | 需要连接到senpi实例 | 先保留自测，待连接后补充 |
| 热税常数未实验标定 | 🟡 中 | 见RSCA-003 | 保留fidelity占位值，标记为"待实验标定" |
| K4 5级状态→pi 3级有信息损失 | 🟡 中 | pi tier粒度较粗 | 保守映射(选较高级别)、记录压缩笔记 |
| pi→K4反向翻译的热税偏高 | 🟡 中 | 反向通道固有损失 | 累积监控、设置上限 |
| 仅有Python实现 | 🟢 低 | pi扩展是YAML/JSON格式 | 未来添加JSON schema适配器 |

---

## 文件路径

- **适配器**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\k4_pi_adapter.py`
- **本声明**: 入库至 knowledge_base/h197_k4_pi_interop_v1.0.jsonl
- **关联分析**: `E:\AI_Workspace\MSS-AI\project\docs\pi_k4_architecture_isomorphism.md`