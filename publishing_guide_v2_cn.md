# MSS论文 发布攻略 v2.0 — 中国网络实测版

**实测时间**: 2026-05-27
**论文**: `msra_arxiv_paper_v1.pdf` (282.7 KB, 10页, 零错误编译)
**作者**: YinChen Guo | ORCID: 0009-0008-2550-130X | zt1372106242@outlook.com

---

## 网络实测结果

| 平台 | 国内可达 | DOI | 推荐 |
|------|---------|-----|------|
| Zenodo | ❌ DNS被墙 | ✅ | 需VPN |
| **OSF Preprints** | ✅ | ✅ | ⭐ 主推（替代Zenodo） |
| ChinaXiv | ✅ | ⚠️ 国内 | 覆盖国内学术界 |
| ResearchGate | ✅ | ❌ | 传播用 |
| VibePapers | ✅ | ❌ | 社区反馈 |

---

## 平台A: OSF Preprints ⭐⭐⭐ 主推（首发DOI）

> 网址: https://osf.io/preprints/
> 注册: 个人邮箱，免费
> 发布后获得: 永久DOI + 可引用链接

### Step 1: 注册
1. 打开 https://osf.io/
2. 点右上角 "Sign Up" → 用 zt1372106242@outlook.com
3. 验证邮箱

### Step 2: 创建Preprint
1. 点 "Add New" → "Preprint"
2. 选 Provider → 推荐 **engrXiv** (工程类，含AI/CS) 或 **MetaArXiv** (跨学科)

### Step 3: 填写以下元数据（直接复制）

**Title (标题):**
```
Modular Symbolic Reasoning Architecture for Deterministic Logical Inference: A Formal Verification Approach
```

**Abstract (摘要):**
```
We present the Modular Symbolic Reasoning Architecture (MSRA), a deterministic logical inference system that replaces the stochastic token-prediction paradigm with formal symbolic reasoning validated by an SMT solver. The architecture consists of three integrated modules: (1) a Lightweight Semantic Shell (LSS) that translates natural language into structured logical queries, (2) a Symbolic Inference Core (SIC) that performs formal deduction over a minimal axiom set, and (3) a Post-Processing Filter (PPF) that formats traceable proof trees as human-readable explanations. All 70 test assertions achieve 100% logical consistency across six foundational axioms and all 15 pairwise consistency constraints, verified by the Z3 SMT solver. On a three-benchmark evaluation suite covering logical reasoning, contradiction detection, and structural analysis, MSRA achieves 100% accuracy (vs. 55.7% for state-of-the-art LLMs), 23.3x lower inference energy cost, and perfect explainability (1.00 vs. 0.10). These results demonstrate that for logical reasoning tasks, deterministic symbolic architectures can outperform stochastic systems while providing formal verification guarantees that are mathematically impossible for probabilistic models.
```

**Keywords (关键词):**
```
symbolic reasoning, deterministic AI, formal verification, Z3 SMT solver, logical inference, neuro-symbolic, kernel-shell architecture, explainable AI
```

**Authors:**
```
YinChen Guo
Affiliation: Independent Researcher
ORCID: 0009-0008-2550-130X
Email: zt1372106242@outlook.com
```

**License:** CC BY 4.0

**Supplemental Materials（补充材料）:**
- GitHub代码库链接（待创建）

---

## 平台B: ChinaXiv 中科院预印本（覆盖国内）

> 网址: https://www.chinaxiv.org
> 注册: 个人邮箱，免费
> 1-3个工作日审核

### 注册后提交
1. 点 "论文提交" 
2. 填写标题/摘要（中英文均需）
3. 上传PDF
4. 选分类: 计算机科学 → 人工智能

**中文标题:**
```
模块化符号推理架构：确定性逻辑推理的形式化验证方法
```

**中文摘要:**
```
本文提出模块化符号推理架构(MSRA)，一种确定性逻辑推理系统，用经Z3 SMT求解器验证的形式符号推理取代随机token预测范式。该架构由三个集成模块组成：轻量语义壳(LSS)将自然语言转化为结构化逻辑查询、符号推理核心(SIC)在最小公理集上执行形式演绎、后处理过滤器(PPF)将可追踪证明树格式化为人类可读解释。全部70条测试断言在六个基础公理和15组配对一致性约束下达到100%逻辑一致性，经Z3求解器验证。在覆盖逻辑推理、矛盾检测和结构分析的三个基准测试集上，MSRA达到100%准确率（对比SOTA大语言模型的55.7%）、23.3倍更低的推理论能量消耗和完美的可解释性(1.00 vs. 0.10)。实验结果表明，对于逻辑推理任务，确定性符号架构可以超越概率系统，同时提供概率模型在数学上不可能实现的形式验证保证。
```

---

## 平台C: ResearchGate（传播）

> 网址: https://www.researchgate.net
> 注册后绑定ORCID
> 等OSF拿到DOI后再发布

---

## 平台D: Zenodo（需VPN）

> 仅在VPN环境下可用
> 注册: https://zenodo.org
> 元数据同OSF，License选 CC-BY 4.0

---

## arXiv背书（并行推进）

### Reddit发帖
> 访问 r/MachineLearning: https://www.reddit.com/r/MachineLearning
> 
> 标题: [Endorsement Request] MSS-AI: Deterministic Symbolic Reasoning with 100% Logical Accuracy, 70/70 Z3-Verified (cs.LO)
>
> 正文模板在 `publishing_playbook.md` 中

### 需准备的物料:
- [ ] OSF DOI（拿到后填入标题/正文/私信）
- [ ] GitHub公开仓库链接

---

## 下一步建议

1. 现在打开 OSF → 注册 → 创建Preprint（15分钟拿到DOI）
2. 同时打开 ChinaXiv → 注册 → 提交（24h审核）
3. DOI到手后 → Reddit发帖求背书 + ResearchGate同步
4. GitHub建公开仓库 → 链接论文DOI