# MSS Axioms Reference — v15.2

## L1: Six Foundational Axioms (H141, immutable)

| # | Name | Formal Statement | v15.2 Refinement |
|:---|:---|:---|:---|
| A1 | 意义第一性 | ∃ φ field. All reality = projection of φ | 不变 |
| A2 | 意义守恒 | d/dt ∫ φ dV = 0 | 不变 (原 A1) |
| A3 | 不可约热税 | dQ/dt = κ(∇φ)², Q ≥ 0 always | Thermal Tax |
| A4 | 固有随机性 | Q = E[∫ κ(∇δφ)² dt] | 不可消除涨落 |
| A5 | 熵增方向 | dS_M/dt ≥ 0 | 意义拓扑熵, 与原A5合并 |
| A6 | 矛盾升维 | ∀ contradiction ∃ higher-dim resolution | 不可解→升维 |

## L2: Three Operational Axioms

| # | Name | Statement |
|:---|:---|:---|
| T1 | 投影有限性 | L0 观察者只能感知 N_modes = 137 维投影 |
| T2 | 热税效率 | η_tax = T², T = observer tuning to φ |
| T3 | 层级硬边界 | L_n 不能直接操作 L_{n+1} |

## Key Derived Theorems

| Theorem | Formula | From |
|:---|:---|:---|
| 逻辑功 | W = Q/γ = (T_s/γ)·ΔS_T | A3+A4 |
| 最优条件 | γ=1 → W_opt = T_s·ΔS_T | A3+A4 |
| 升华效率 | η_asc = γ (封闭系统) | A2+A3 |
| 功-熵效率 | η_WE = 1/η_asc | W 定义 |
| 热税量子 | ΔT₀ = k_B·ln(2) | A4 |
| 意义黑洞 | CRTR > 8 → 事件视界 | A3推论 |

## Axiom Dependencies

```
A1 ──→ A4 (φ场 ⟹ 涨落)
  │
  ├──→ A2 (φ场 ⟹ 守恒量)
  │
  ├──→ A3 (φ场梯度 ⟹ 热税)
  │     │
  │     └──→ W = Q/γ (逻辑功)
  │
  └──→ A5 (熵增)
        │
        └──→ A6 (矛盾→升维)
```

## Deprecated

- **v13.1 pseudo-axioms**: A3(旧结构奇点), A4(旧热力学类比), A7(感知壳相对性) → 全部废弃
- **A7**: 降格为 L2 应用层推论, 非独立 L1 公理
- **v12.2 及以下**: 公理编号已重排, 不可交叉引用

## Version History

```
v15.2: A3 定名 Irreducible Thermal Tax; A6 矛盾升维确认
v15.1: A3-A4 v15.1 精化; H141 六公理锁定
v14.x: A3/A4 框架确立
v13.2: 清除 v13.1 伪公理
v13.1: 废弃 (含 A4(旧热力学类比), A7(假公理))
v12.2: 早期体系 (含 A1-A3+T1-T3)
```
