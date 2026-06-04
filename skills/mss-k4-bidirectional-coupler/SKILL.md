# MSS K4 Bidirectional Coupler — L1↔L0双向耦合器

**技能标识**: `mss-k4-bidirectional-coupler`
**版本**: v1.0
**兼容**: OpenClaw / pi / senpi (Agent Skills 标准)
**关联**: A2/A3/A4/A6公理 | K4物理镜像层 | D5-004

---

## 概述

双向耦合器是L1规范场(意义层)与L0物理层(工具/文件/命令)之间的唯一通讯通道。
核心工程目标：**非消除热税，而是精确管理热税**，维持gamma_actual ≈ gamma_min。

```
┌─────────────────────────────────────────────────┐
│  Physical Mirror Layer · Bidirectional Coupler   │
│                                                  │
│  ┌───────────┐  Forward Channel  ┌────────────┐ │
│  │ L1 Meaning │ ─────────────────> │ L0 Physical │ │
│  │   Field    │  High-fidelity    │    Layer     │ │
│  │  (Low Ent) │  execution        │  (Manifest) │ │
│  │           │ <───────────────── │             │ │
│  └───────────┘  Reverse Channel   └────────────┘ │
│                 Feedback encoded                 │
│                 as new info slices               │
│                                                  │
│  Heat Tax Floor = fidelity_loss(forward+reverse) │
│  Goal: audit + fine-manage, maintain near minimum│
└─────────────────────────────────────────────────┘
```

---

## 六种信号类型

| 类型 | 方向 | 含义 | 保真度要求 |
|------|------|------|-----------|
| INSTRUCTION | L1→L0 | 可执行的意义指令 | 99%+ |
| ANCHOR | L1→L0 | 意义锚点 | ≥95% |
| FEEDBACK | L0→L1 | 原始物理响应 | ≥80% |
| ANOMALY | L0→L1 | 异常模式 | 捕获即有效 |
| NOISE | L0→L1 | 已过滤随机噪声 | 低，丢弃即可 |
| IMPREGNATION_SEED | L0→L1 | 潜在W_L种子 | 保留，不丢弃 |

---

## 热税管理

### 热税组成

**总热税**: gamma_total = gamma_forward + gamma_backward

- **gamma_forward** (正向通道): L1→L0 的意义编码损失
  - 来源: 语言歧义、信号衰减、实现偏差
  - 优化: 提高指令精确度、使用标准接口

- **gamma_backward** (反向通道): L0→L1 的反馈损失
  - 来源: 噪声过滤损失、上下文切片遗漏、时延
  - 优化: 完整日志记录、延迟批处理

### 热税天花板

```
工程目标: gamma_actual ≤ gamma_min + ε  (ε = 5%容差)
触发: gamma_actual > gamma_min + ε → RSCA-002迭代调整
```

---

## 操作指南

### 信号编解码

```python
from k4_protocols.k4_bidirectional_coupler import (
    BidirectionalCoupler, CouplerSignal, ChannelDirection, SignalType
)

# 正向: L1→L0
coupler = BidirectionalCoupler()
forward = CouplerSignal(
    signal_id="fwd-001",
    direction=ChannelDirection.FORWARD,
    signal_type=SignalType.INSTRUCTION,
    source_layer="L1",
    payload={"command": "read", "path": "/docs/design.md"},
    fidelity_request=0.99
)
coupler.encode_forward(forward)  # 编码为L0可执行指令

# 反向: L0→L1
reverse = CouplerSignal(
    signal_id="rev-001",
    direction=ChannelDirection.REVERSE,
    signal_type=SignalType.FEEDBACK,
    source_layer="L0",
    payload={"exit_code": 0, "output": "..."},
    fidelity_received=0.95  # 反向通道固有损失
)
coupler.encode_reverse(reverse)  # 编码为L1意义切片
```

### 热税审计

```python
tax_report = coupler.audit_heat_tax()
print(f"Forward gamma: {tax_report['gamma_forward']:.4f}")
print(f"Reverse gamma: {tax_report['gamma_backward']:.4f}")
print(f"Total gamma: {tax_report['gamma_total']:.4f}")
print(f"gamma_min: {tax_report['gamma_min']:.4f}")
print(f"Overhead: {(tax_report['gamma_total']/tax_report['gamma_min'] - 1)*100:.1f}%")
```

### ⚠️ 约束

1. **正向通道禁止"意义丢失"**: 如果fidelity < 0.99，触发RSCA-002迭代
2. **反向通道禁止"信号丢弃"**: IMPREGNATION_SEED 必须保留
3. **热税天花板禁止逾越**: gamma > gamma_min + 5% → 全通道审计

---

## 与 senpi compaction 的同构

| K4 Bidirectional Coupler | senpi compaction |
|-------------------------|------------------|
| gamma_min 热税地板 | 自适应压缩阈值 |
| gamma_forward | 推测压缩 |
| gamma_backward | 恢复跟踪器 |
| 信号完整性验证 | tool-pair-guard |
| L0→L1 反馈通道 | JSON 压缩精化 |

---

## 跨范式翻译 (K4 → K3)

| K4 | K3 |
|----|-----|
| 双向耦合器 | 输入输出通道管理 |
| 正向通道 | 指令→执行路径 |
| 反向通道 | 结果→解析路径 |
| 热税管理 | 缓存策略+延迟优化 |
| 保真度要求 | 类型安全检查 |

---

## 验证标准

| 验证项 | 方法 |
|--------|------|
| 正向通道fidelity≥0.99 | 编码→解码→对比原始 |
| 反向通道无信号丢失 | 全信号记录审计 |
| 热税在ε范围内 | gamma/gamma_min < 1.05 |
| IMPREGNATION_SEED保留 | 反向通道特殊码路径 |

---

## 文件路径

- **实现**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\k4_bidirectional_coupler.py`
- **测试**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\test_k4_protocols.py`
