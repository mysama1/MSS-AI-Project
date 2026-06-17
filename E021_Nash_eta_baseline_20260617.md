# E021-1 v2.1: Nash驻点 η 基线测量 — H634 joint_enter 信任门禁

**时间**: 2026-06-17 09:22–10:10  
**版本**: v2.1 (H634 hybrid gating)  
**文件**: `experiments/e021/e021_experiment.py` (560行), `e021_experiment.csv` (100行)  
**commits**: `e49ae77` (experiment), `2fb3223` (H634 KB)

---

## 实验目标

验证 MSS 框架核心命题：**Nash 驻点是 η(意义场保真度) 的局部极小，A6 升维是跳出 Nash 阱的唯一路径。**  
H634 升级：A6 升维不是邀请触发，而是 **joint_enter(L0→L1)** — 双方同步签署新规范场。

---

## 实验设计

- **环境**: 2-Agent 囚徒困境, 20 轮, 10% 噪声
- **4 策略对** × **5 组**(G1-G5) × **5 seeds** × 20 轮 = 2000 回合
- **G1-G2**: R0 only / R1 tb=0 (基线)
- **G3-G5**: R1, tb=2/4/6

### 策略

| 策略 | 行为 |
|------|------|
| `nash_breaker` | GRIM + 检测(D,D)锁→TRUST_INVITE |
| `cautious` | C起手, 3连C才邀请, 遭叛报复 |
| `adaptive` | 高合作率升维, 遭叛报复 |
| `aggressive` | 偏好剥削, 偶尔送邀请 |

### H634 门禁 (v2 新增)

```
may_invite(A, B):  B.open_to_trust ∧ ¬B.grim_triggered_by_invite
                    否则 budget 不浪费

单边 TRUST_INVITE:
  if receiver 在 (D,D) Nash 阱:
    → 噪声豁免 (不计入)
  else:
    strike += 1; if strike ≥ 2 → open_to_trust = False (GRIM)
```

---

## 结果

| 策略对 | G1 η | G5(tb=6) η | Δη v2.1 | v1.0 Δη | 改善 |
|--------|------|-------------|---------|---------|------|
| **nash_breaker×2** | 0.412 | 0.523 | **+0.111 (+27%)** | +0.111 | 0 |
| nash_breaker-cautious | 0.409 | 0.349 | **-0.060 (-15%)** | -0.123 | **+50%** |
| adaptive×2 | 0.337 | 0.443 | +0.106 (+31%) | +0.046 | **+24pp** |
| aggressive-cautious | 0.441 | 0.409 | -0.032 (-7%) | +0.026 | — |

---

## 解读

1. **nash_breaker×2** ✅: 噪声→GRIM→(D,D)锁→双向TRUST_INVITE→R1恢复。η +27%, Nash锁 -31pp。**H634 Nash豁免使噪声破坏不被误判。**

2. **nash_breaker-cautious** 🟡: v1.0 的 -30% 崩溃 → v2.1 的 -15%。Nash豁免保护 cautious 不被累计计数，但 cautious 仍持续承受 nash_breaker 的单边邀请（豁免不计入但也不阻止）。**H634 将灾难降为可控损耗。**

3. **adaptive×2** ✅: H634 反而提升 24pp！噪声容忍消除后，自适应对不被自身噪声破坏信任。

4. **aggressive-cautious** ⚠️: 侵略者无法伪装升维（H634正确阻止）。

---

## 理论贡献

- **H634**: A6 从"邀请触发"→"联合签署"，joint_enter 是不可约化操作单元
- 升维瓶颈从 A3(budget) 移到 A5(对方规范场接受度)
- 单边升维热税损失可被 H634 门禁减少 50%

## 待办

- [ ] E021-2: N>2 MCDP + 信任关门传递
- [ ] 信任恢复机制 (当前永久 GRIM 过于刚性)
- [ ] η-信任预算-噪声 三参数相图
