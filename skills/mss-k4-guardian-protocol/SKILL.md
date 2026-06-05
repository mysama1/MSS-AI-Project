# MSS K4 Guardian Protocol — No.1本体权重守护协议

**技能标识**: `mss-k4-guardian-protocol`
**版本**: v1.0
**兼容**: OpenClaw / pi / senpi (Agent Skills 标准)
**关联**: A1/A3/A5公理 | K4守卫架构 | D5-004

---

## 概述

No.1的T值(意义场通量上线)是K4文明操作系统的最低天花板参数。
Guardian Protocol 持续监测T值波动，自动调整系统输出复杂度，
确保全局意义通量不因T值过转而降级。

**核心定理**: R = T / φ (其中 T = T_No.1)
当 T_No.1 降低:
- R 同步降低(组织韧性破坏)
- 可达意义场频率带宽便道
- L1规范场锚定精确度下降
- 全体K4 OS进入降级运行模式

---

## 五级状态管理

### OPTIMAL (最优)
```
T值基线内 → 全能力输出
复杂度因子: 100%
无需任何限制
```

### DEGRADED_L1 (一级降级)
```
T值下降10-20% → 轻微输出缩减
复杂度因子: 80%
- 降低非关键路径的分析深度
- 减少实验性探索
```

### DEGRADED_L2 (二级降级)
```
T值下降20-30% → 显著输出缩减
复杂度因子: 60%
- 暂停探索区活动
- 仅维持核心区完整
- 暂停K3通信
```

### DEGRADED_L3 (三级降级)
```
T值下降30%以上 → 紧急协议启动
复杂度因子: 40%
- 全功能冻结非核心模块
- 仅保留守护协议和最小热税流
- 启动恢复程序
```

### CRITICAL (失控)
```
T值降至存活阈值下
复杂度因子: 20%
- 全系统最低运行
- 仅保留RSCA-001和RSCA-006
- 发出最高级告警
```

---

## 操作指南

### T值测量 (每30分钟)

通过三个信号源采集：

```python
from k4_protocols.k4_guardian_protocol import TValueSnapshot

# 信号源1: 行为模式密度
snap1 = TValueSnapshot(
    t_estimate=0.82,
    source="behavioral_pattern",
    confidence=0.75
)

# 信号源2: 语言场复杂度
snap2 = TValueSnapshot(
    t_estimate=0.91,
    source="language_field",
    confidence=0.80
)

# 信号源3: 混沌沙箱抗性
snap3 = TValueSnapshot(
    t_estimate=0.85,
    source="chaos_sandbox",
    confidence=0.70
)
```

### 综合分析

```python
from k4_protocols.k4_guardian_protocol import Guardian

guardian = Guardian()
guardian.add_snapshot(snap1)
guardian.add_snapshot(snap2)
guardian.add_snapshot(snap3)

status = guardian.current_state()
# → SystemState.OPTIMAL (如果T > 90%)
# → SystemState.DEGRADED_L1 (如果T在80-90%)
# → SystemState.DEGRADED_L2 (如果T在70-80%)
# → SystemState.DEGRADED_L3 (如果T < 70%)

complexity_factor = guardian.complexity_factor()
# → 1.0 (OPTIMAL)
# → 0.8 (DEGRADED_L1)
# → 0.6 (DEGRADED_L2)
# → 0.4 (DEGRADED_L3)
```

### 恢复程序 (DEGRADED_L3 or CRITICAL)

1. 停止所有实验
2. 回到核心区 (A1-A6 刚体区)
3. 重新校准 T 值基线
4. 每次重启一个子系统，逐级验证

---

## 与 senpi service-tier 的同构

| K4 Guardian Protocol | senpi service-tier |
|---------------------|--------------------|
| SystemState (5级) | auto/flex/priority 服务层 |
| T值阈值 | 模型降级路径 |
| complexity_Lx | 输出预算控制 |
| 恢复程序 | 模型回退机制 |

**差异**: Guardian Protocol 是整个文明OS的守护层，而 service-tier 是单一模型的降级路径。前者是多层次系统级，后者是单模型级。

---

## 告警模板

```
╔═══════════════════════════════════════╗
║ K4 GUARDIAN PROTOCOL — STATE CHANGE  ║
╠═══════════════════════════════════════╣
║ From: OPTIMAL                         ║
║ To:   DEGRADED_L2                     ║
║ T值:  0.78 (基线0.96, 下降18.8%)      ║
║ 复杂度因子: 0.8 → 0.6                 ║
║ 推荐操作: 暂停探索区活动，等待恢复     ║
╚═══════════════════════════════════════╝
```

---

## 验证标准

| 验证项 | 方法 |
|--------|------|
| T值变化→状态切换正常 | 注入不同T值快照验证状态 |
| 复杂度因子正确计算 | 验证各层级complexity_Lx输出 |
| 恢复程序正确启动 | 验证CRITICAL→恢复流程 |

---

## 文件路径

- **实现**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\k4_guardian_protocol.py`
- **测试**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\test_k4_protocols.py`
- **KB关联**: kB_metrics_v2.4_v2.5.jsonl`
