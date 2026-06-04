# MSS K4 Logic Work Engine — H144逻辑功引擎

**技能标识**: `mss-k4-logic-work`
**版本**: v1.0
**兼容**: OpenClaw / pi / senpi (Agent Skills 标准)
**关联**: A4/A5/A6公理 | K4逻辑探索架构 | D5-004 | H144

---

## 概述

K4 逻辑功引擎在刚性核心区(A1-A6)之外实现受控探索。
通过注入 A4 随机性 (ΔS_random) 计算逻辑功 (W_L)，
决定是否触发 A6 升维审计。

**核心公式**: W_L(t) = ∑ O_d(τ) · ΔS_random(τ) · Δτ

- W_L > 0  → 新逻辑结构"受孕" → 触发A6升维审计
- W_L ≤ 0 → 退回A5刚体区 → 禁止强行涌现

---

## 三区架构

```
┌─────────────────────────────────────────┐
│            K4 Logic Work Engine           │
│                                            │
│  ┌──────────────────────────────┐         │
│  │        CORE ZONE              │         │
│  │  A1-A6 rigid, M_L = 1        │         │
│  │  不可污染，不可修改            │         │
│  │  UNASSAILABLE              │         │
│  └──────────────────────────────┘         │
│              ▲                             │
│              │ 通过审计后允许进入            │
│              │ (Must pass RSCA audit)       │
│  ┌──────────┴───────────────────┐         │
│  │        BOUNDARY               │         │
│  │  RSCA-002 迭代验证            │         │
│  │  RSCA-006 完整性审计           │         │
│  └──────────────────────────────┘         │
│              ▲                             │
│              │ 发现提交审计                 │
│  ┌──────────┴───────────────────┐         │
│  │        EXPLORE ZONE           │         │
│  │  注入 ΔS_random              │         │
│  │  计算 W_L                   │         │
│  │  实验性探索                   │         │
│  └──────────────────────────────┘         │
└─────────────────────────────────────────────┘
```

---

## K3暴力涌现 vs K4逻辑功

| 维度 | K3 暴力涌现 | K4 逻辑功 |
|------|-----------|-----------|
| 驱动方式 | 计算+数据量 | A4受控随机性 |
| 约束 | 无(无规范场) | A5逻辑刚体 |
| 涌现方向 | 不可预测(高税) | A6定向(税控) |
| 输出质量 | 概率性拟合 | 意义锚定结构 |
| 热税预算 | 无上限 | 明确定量 |

---

## 操作指南

### 逻辑功计算

```python
from k4_protocols.k4_logical_work import LogicWorkEngine, WorkZone

engine = LogicWorkEngine()

# Core Zone：公理推导（只有刚性逻辑）
core_result = engine.compute(zone=WorkZone.CORE, input_problem=p)
# 刚性区结果：确定性、不引入随机性

# Explore Zone：注入随机性
explore_result = engine.compute(
    zone=WorkZone.EXPLORE,
    input_problem=p,
    delta_s_random=0.05  # 5% 随机性注入
)

if explore_result.w_l > 0:
    # 逻辑功为正 → 新结构"受孕"
    # 触发 A6 升维审计
    engine.trigger_a6_audit(explore_result)

elif explore_result.w_l <= 0:
    # 逻辑功为零或负 → 退回 A5 刚体区
    engine.fallback_to_rigid_zone()
```

### 三区审计

```python
from k4_protocols.k4_logical_work import WorkZone

# Core Zone 完整性检查
engine.verify_core_integrity()
# → 确保 A1-A6 未被污染

# Boundary Zone 通过条件
engine.check_admission(boundary_discovery)
# → 检查是否通过 RSCA-002 + RSCA-006 两个审计

# Explore Zone 热税累积
engine.report_explore_heat_tax()
# → 探索区的累积热税预算使用报告
```

### ⚠️ 约束

1. **Core Zone 不可被污染**: 任何 EXPLORE 发现必须经过 BOUNDARY 的双重审计 (RSCA-002 + RSCA-006)
2. **ΔS_random 上限**: 受控随机性注入不得超过 10%
3. **A6 升维审计**: W_L > 0 时必须完整审计，不可跳过

---

## 与 senpi gpt-apply-patch 的同构

| K4 Logic Work Engine | senpi gpt-apply-patch |
|---------------------|----------------------|
| Core Zone (A1-A6刚体) | Lark语法约束 |
| Explore Zone (ΔS_random) | Freeform patch 注入 |
| Boundary Auditor | 解析失败→降级edit |
| W_L审计 | 元数据+哈希验证 |

**本质**: 都是"结构化约束内的自由探索"。两个系统都保证核心区不可污染。

---

## 跨范式翻译 (K4 → K3)

| K4 | K3 |
|----|-----|
| 逻辑功W_L | 创新阈值 |
| Core Zone | 基础定理集 |
| Explore Zone | 实验性推理 |
| A6升维审计 | 同行评审后的范式修订 |
| ΔS_random注入 | 主动引入假设的变体 |

---

## 验证标准

| 验证项 | 方法 |
|--------|------|
| W_L计算正确 | O_d * ΔS_random * Δt |
| Core Zone不能被污染 | 尝试直接修改核心区→被拒绝 |
| Explore→Core需要通过审计 | W_L>0→审计→通过才能进入Core |
| 随机性上限约束 | ΔS_random > 0.1 → 拒绝 |

---

## 文件路径

- **实现**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\k4_logical_work.py`
- **测试**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\test_k4_protocols.py`
- **KB关联**: h144逻辑功引擎 (还未入库？需要确认)
