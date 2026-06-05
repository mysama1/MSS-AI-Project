# MSS Glossary — v15.2

## Axioms (L1)

| Term | Definition | Source |
|:---|:---|:---|
| A1 意义第一性 | ∃ φ field. All reality = projection of φ | H141 |
| A2 意义守恒 | d/dt ∫ φ dV = 0 | H141 |
| A3 不可约热税 | dQ/dt = κ(∇φ)², Q ≥ 0 always | H141, TH-002 |
| A4 固有随机性 | Q = E[∫ κ(∇δφ)² dt] | H141 |
| A5 熵增方向 | dS_M/dt ≥ 0 | H141 |
| A6 矛盾升维 | ∀ contradiction ∃ higher-dim resolution | H141 |

## Theorems (L2)

| Term | Formula | Source |
|:---|:---|:---|
| 逻辑功 | W = Q/γ = (T_s/γ)·ΔS_T | w_logic_definition |
| 升华效率 | η_asc = γ (封闭系统) | A2+A3 |
| 功-熵效率 | η_WE = 1/η_asc | W definition |
| 热税量子 | ΔT₀ = k_B·ln(2) | A4 |
| 意义黑洞判据 | CRTR > 8 → 事件视界 | A3 corollary |
| L2-011 模块缓存污染 | sys.modules 陈旧导致执行结果错误 | TH-005 |

## Core Concepts

| Term | Meaning |
|:---|:---|
| φ | 意义场 (meaning field) |
| Q | 热税 (thermal tax) — 不可约的能量消耗 |
| γ | 阻尼系数 (0<γ<∞) |
| η_asc | 升华效率, 封闭系统中 = γ |
| T_s | 源温度 = γ·τ₀ |
| ΔS_T | 意义拓扑熵变 |
| CRTR | 热税-资源比 (Cost-to-Resource-Tax-Ratio) |
| N_modes | L0 投影的独立极化模数 = 137 (hypothesis) |

## Layers (L0-L5)

| Layer | Name | Example |
|:---|:---|:---|
| L0 | 物理观察 | Standard Model particles, measurements |
| L1 | 公理层 | A1-A6, immutable |
| L2 | 定理层 | W=Q/γ, L2-011 cache pollution |
| L3 | 理论层 | TH-001-005, closure reports |
| L4 | 工程层 | ENG-001-002, scripts, configs |
| L5 | 原始材料 | RAW-001, raw conversation logs |

## VDP Rules

| Rule | Target | Source |
|:---|:---|:---|
| CLI-001 | 裸 `python` 调用无版本指定 | vdp_precommit |
| NAMING-002 | 文件名下划线/连字符不一致 | vdp_precommit |
| CFLOW-003 | 裸 try/except 吞错 | vdp_precommit |
| NO_ARBITRARY_RATIO | 无推导的百分比赋值 | CLOSURE-001 |
| NO_CONTINUITY_ON_DISCRETE | 离散对象使用连续方法 | CLOSURE-002 |
| INEQUALITY_3POINT_CHECK | 不等式需三点验证 | CLOSURE-002 |
| COMPLETENESS_GATE | "fully solved" 需边界说明 | CLOSURE-002 |

## Tools

| Tool | Purpose |
|:---|:---|
| status.py | 一键仪表盘 |
| verify_all.py | 8 项完整性检查 |
| daily_audit.py | 定时健康审计 (13:00) |
| link_validator.py | 外部链接月度巡检 |
| module_cache_detector.py | sys.modules 污染检测 |
| kb_quality.py | KB 元数据质量扫描 |
| vdp_scan.py | 6 规则扫描 |
| vdp_precommit.py | 7 规则预提交检查 |
| vdp_anchor.py | 事实锚定验证 |
| vdp_lexical.py | 词法重叠检测 |

## Deprecated Terms

| Term | Why | Replacement |
|:---|:---|:---|
| A7 感知壳相对性 | 非独立公理, L2 应用层推论 | T2 (η_tax = T²) |
| 旧 A3 结构奇点 | v13.1 伪公理 | A6 矛盾升维 |
| 旧 A4 热力学类比 | v13.1 伪公理 | A3 Irreducible Thermal Tax |
| "替代 ΛCDM" | 僭越声明 | "补充解释范式" |
| 75/20/5 暗物质比 | 无依据赋值 | A/B/C 定性分类 |
| "v18.9.x" | LLM 幻觉 (工具版本号) | v15.2 |
