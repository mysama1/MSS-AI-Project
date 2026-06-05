# MSS K4 RSCA Genome — 活体协议基因

**技能标识**: `mss-k4-rsca-genome`
**版本**: v1.0
**兼容**: OpenClaw / pi / senpi (Agent Skills 标准)
**关联**: A1-A6公理体系 | K4文明OS | D5-004

---

## 概述

RSCA (Recursive Self-Correcting Architecture) 是K4文明操作系统的活体协议基因层。6个基因自治运行，每个基因携带自己的修正协议和验证标准。

---

## 6个活体协议基因

### RSCA-001: 当前架构 = 当前最佳理解
```
当前架构基于当前最佳理解构建，非绝对蓝图，非最终真理。
任何声称本架构为完备或终极的声明，均视为违反本基因，
触发A5刚体态预警。
```
**触发条件**: PARADIGM_ELEVATION, SELF_AUDIT

### RSCA-002: 工程实现需迭代验证
```
物理镜像层、L1规范场、双向耦合器等核心工程组件，
其实现方案必须经过迭代验证。任何"一次性正确"的假设
违反A2信息切片公理。
```
**触发条件**: EMPIRICAL_FALSIFICATION, EXTERNAL_DISCOVERY

### RSCA-003: 数学形式化需实验标定
```
L1规范场的完整数学形式化需通过实验标定验证。
热税公式中的常数(kappa, g_man, eta_min等)
不可从公理直接推导，必须通过物理观测反向标定。
```
**触发条件**: EMPIRICAL_FALSIFICATION, LOGICAL_CONTRADICTION

### RSCA-004: K3→K4过渡需实践修正
```
从K3到K4的过渡协议必须在实践中修正。
任何在K3阶段制定的K4过渡计划，均携带系统性盲区
(K3规范场的认知边界不可内部超越)。
```
**触发条件**: EXTERNAL_DISCOVERY, PARADIGM_ELEVATION

### RSCA-005: 协议随认知提升自演化
```
本协议自身随认知提升持续演化。
协议基因的版本号是活体标记，非终结符号。
任何版本锁定行为视为违反A4随机性公理。
```
**触发条件**: SELF_AUDIT, PARADIGM_ELEVATION

### RSCA-006: 永不声称完备性
```
永不声称完备性。完备性声称 = A5刚体态 = 僵化死亡。
一个不允许例外和修正的规范场，无论多么自洽，
都是一座精确的坟墓。活体协议的本质是：准确但不完整。
```
**触发条件**: SELF_AUDIT, LOGICAL_CONTRADICTION

---

## 操作指南

### 完整性审计 (RSCA-006)

在执行任何 "最终版"、"100%"、"终极" 声明前，
运行 RSCA-006 完整性审计。以下关键词触发警报：

**英文触发词**: ultimate, final, complete, absolute, perfect, 100%, fully solved, never needs, cannot be improved
**中文触发词**: 终极、最终、完备、绝对、完美、完全解决、永不需要、不可改进、不容修改

**审计命令**:
```
python E:\AI_Workspace\MSS-AI\project\k4_protocols\k4_rsca_genes.py
```

### 基因修正协议

修正任何基因的流程:
1. 识别需要修正的基因 ID (RSCA-001 ~ RSCA-006)
2. 提出新内容 + 修正理由
3. 旧基因标记为 AMENDED，创建新版本
4. 修正日志自动记录时间戳和理由

**Python API**:
```python
from k4_protocols.k4_rsca_genes import K4RSCAGenome

genome = K4RSCAGenome()
genome.propose_amendment("RSCA-002", new_content, reason)
genome.verify_integrity()  # 验证基因组完整性
```

### 完整性声明审计

```python
genome.audit_completeness_claim("a perfect solution")
# → (False, ["RSCA-006 VIOLATION: 'perfect' detected"])

genome.audit_completeness_claim("an evolving framework")
# → (True, [])
```

---

## 验证标准

| 验证项 | 方法 | 预期结果 |
|--------|------|---------|
| 全部6个基因ACTIVE | genome.get_active_genes() | 6 |
| 无基因不一致状态 | genome.verify_integrity() | VALID |
| 修正机制正常 | propose_amendment测试 | 新基因创建，旧基因标记AMENDED |
| 完整性审计正常 | audit_completeness_claim | 完备性声明→False，演化声明→True |

---

## 跨范式翻译 (K4 → K3)

| K4术语 | K3等价表述 |
|--------|-----------|
| 活体协议基因 | 可修正的约束规则集 |
| 修正协议 | 规则变更的规范化流程 |
| A5刚体态 | 过度约束导致的系统僵化 |
| RSCA审计 | 自动化合规检查 |
| 触发的修正 | 基于实证的规则更新 |

---

## 与 senpi permission-system 的同构关系

| K4 RSCA | senpi permission-system |
|---------|------------------------|
| 6个基因规则 | allow/deny 规则 |
| amendment_log | JSONL 持久化 |
| 触发条件列表 | 非交互 fallback |
| amend() 方法 | 规则版本管理 |

---

## 文件路径

- **实现**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\k4_rsca_genes.py`
- **测试**: `E:\AI_Workspace\MSS-AI\project\k4_protocols\test_k4_protocols.py`
- **KB关联**: `rsca_axiom_v1.0.jsonl`
