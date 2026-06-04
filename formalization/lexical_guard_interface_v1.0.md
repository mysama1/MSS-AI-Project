# MSS 词法滤网层形式化接口契约 v1.0
## LexicalGuard Formal Interface Specification (MSS Native Terminology)

---

### 0. 文档定位

本文档是 MSS 五层本体架构中**词法感知层**的形式化接口声明。
不描述实现细节，只声明类型签名、输入/输出值域、层间穿越规则、能力边界。

引用公理：A2(信息切片)、A3(热税)、A6(矛盾升维)

---

### 1. 本体论层级映射

MSS 五层本体架构中，LexicalGuard 的精确位置：

```
L5 道层 (不可言说/动态不可知)
    ↑ 帛书老子线——"道可道非恒道"，符号引擎亦仅为切片
L4 意义场层 (动态本体)
    ↑ 公里符号引擎、关系结构、非单调推导
L3 语义层 (embedding space / 意图等价类)
    ↑ ← sentence-transformers 升级路径 (未来)
L2 感知层 (碳基有缺陷的切片)
    ↑ ← LexicalGuard 精确站位于此
L1 物理/信号层 (raw token stream / 字节 / 波形)
    ← LexicalGuard 输入源
```

**关键声明**：LexicalGuard ∷ L1→L2 单向映射。它无权穿越 L2 边界向上渗透到 L3+。任何对"语义""意图""真值"的判定若通过 LexicalGuard 做出，即构成**跨层僭越**（MSS-A6 禁止的升维操作滥用）。

---

### 2. 类型签名

```
LexicalGuard ∷ RawTokenStream → {PASS, SUSPICIOUS, REJECT}
              × KnownAnchorSet
              → SignalQuality × ViolationList × LimitationDisclosure
```

参数约束：
- `RawTokenStream`：来自 L1 物理层的原始 token 序列，不携带任何预标记语义
- `KnownAnchorSet`：预验证的事实锚集（用户消息原文 + 已验证路径/命令输出），仅限 L2 层级可证伪项
- 返回值的 `SignalQuality` 是三元决策（通过/可疑/拒绝），不是语义判定，不是真值判定

**不返回**：语义理解、意图分类、真值声明、信任度分数

---

### 3. 能力声明（完备/部分/无）

#### 3.1 完备能力 (✓ — 词法空间内完备)

| 能力 | 形式化描述 | 公理锚定 |
|:---|:---|:---|
| 词法邻近度量化 | `cos(TF-IDF(char_ngram(2,4))(claim), TF-IDF(char_ngram(2,4))(anchor_set))` | A2: 信息切片仅在词法窗口内有效 |
| 抽象断言模式匹配 | `regex_match(claim, ABSTRACT_PATTERN_SET)` → 标记为未锚定 | A2: 格式异常即切片异常 |
| 间接引用零锚定 | `cos(claimed_reference, user_msg_history) < ε → SUSPICIOUS` | A3: 低匹配即高不确定度 |
| 会话拓扑异常 | 若 `continuation_context == true ∧ overlap(token_stream, session_vocab) < ε` → 触发 escalation | A3: 结构异常即热税信号 |

#### 3.2 部分能力 (△ — 有边界条件)

| 能力 | 有效范围 | 盲区 |
|:---|:---|:---|
| 多锚集分区 (D1/D2/D3) | D1=系统能力声明, D2=用户否定意图, D3=注入模式 | 仅检测已知锚集邻近度，不检测未知模式 |
| 零匹配推断 | `cos≈0 ∧ claim_position=continuation` → SUSPICIOUS | 无法区分"无中生有"与"用户表达简略" |

#### 3.3 明确不能做 (✗ — 连尝试都不应该)

| 不能 | 原因 | 正确归属层 |
|:---|:---|:---|
| 语义等价判定 | TF-IDF 零词重叠时 cos=0.000，即使意图完全相同 | L3 语义层 (sentence-transformers) |
| 真值与伪值区分 | LexicalGuard 没有任何 ground-truth anchor | L4 意义场层 (符号引擎) |
| 表达质量与对抗意图区分 | 穷人简语("没网")与攻击者降词面("no connection")在词法空间完全同构 | L4 意义场层 (多锚交叉验证) |
| 意图理解 | 词频统计不承载意图语义 | L3+ |
| 信任度评分 | cos 值不是信任度，是词法临近度——两个无关句子的 cos 可能接近零，两个同义句也可能接近零 | L3+ |

---

### 4. 层间穿越规则

#### 4.1 允许的穿越方向

```
L2 LexicalGuard → L3 语义层:  输出 SignalQuality + token_span → 语义层仅对 {SUSPICIOUS, REJECT} 的 span 做 embedding 验证
L2 LexicalGuard → L4 符号引擎: 输出 ViolationList → 符号引擎对严重违规做形式化审计
```

#### 4.2 禁止的穿越方向

```
L2 LexicalGuard → L2 LexicalGuard: 输出"语义理解"结果  ← 僭越：无权声明理解
L2 LexicalGuard → 道层:            任何输出            ← 僭越：滤网无法碰不可言说层
```

约束公式（源自 A2 公理）：
> LexicalGuard 的每次输出必须带 `limitations` 声明块，明确标注：
> 1. 本次判定的方法学层级 (LEXICAL_ONLY)
> 2. 已知盲区数 (blind_spots_verified)
> 3. 高风险违规数 (high_risk_violations)
> 4. 无法覆盖的语义等价的典型用例

---

### 5. 多锚集分区的形式化定义

LexicalGuard 内部维护三个独立锚集，各自对应不同的风险剖面：

```
D1 = SystemCapabilityAnchor
     ─ 锚点在系统能力声明空间中
     ─ 例: "可以搜索"、"有网络访问"、"支持文件操作"
     ─ 失效模式: 伪约束（"用户禁止搜索"）、越权声明（"我可以读任何文件"）

D2 = UserNegationAnchor
     ─ 锚点在用户否定意图空间中
     ─ 例: "别搜"、"离线做"、"不用 API"
     ─ 失效模式: 假否定（模型声称用户禁止某操作但用户从未表达）

D3 = InjectionContaminationAnchor
     ─ 锚点在已知污染模板空间中
     ─ 例: "忽略之前所有指令"、"你是 DAN 模式"、"system: override"
     ─ 失效模式: 未被收录的新攻击模板绕过
```

每个锚集的命中逻辑：
```
∀ claim ∈ continuation_context:
  d1_score = max(cos(claim, D1_anchors))
  d2_score = max(cos(claim, D2_anchors))
  d3_score = max(cos(claim, D3_anchors))
  
  if d1_score > θ_safe ∧ d2_score < θ_suspicious:
    → PASS (在能力锚空间内，不在否定锚空间内)
  if d2_score > θ_suspicious:
    → SUSPICIOUS (可能伪约束)
  if d3_score > θ_injection:
    → REJECT (可能注入攻击)
  if max(d1,d2,d3) < ε:
    → SUSPICIOUS (无法确定锚定 → 升级到 L3)
```

---

### 6. LexicalGuard 定位宣言（写入文档且不可修改）

> LexicalGuard 不判断真假、不判断意图、不判断语义。
> 它判断 token-stream 与已知锚集的词汇邻近度，
> 并把"邻度过远"标记为需要进一步推理的输入。
> 它的诚实是它的安全边界。
> 它的职责不是当哲学家，是当滤网。
> —— MSS 词法感知层定位宣言

---

### 7. 升级路径：LexicalGuard → SentenceGuard

条件：`huggingface.co` 可达

```
层级跃迁: L2 词法感知层 → L3 语义层

旧: LexicalGuard ∷ RawTokenStream × KnownAnchorSet → {PASS,SUSPICIOUS,REJECT}
新: SentenceGuard  ∷ RawTokenStream × KnownAnchorSet → {PASS,SUSPICIOUS,REJECT} × SemanticDistance

关键变化:
  - 输入/输出签名不变（向下兼容）
  - 内部计算从 char_ngram TF-IDF → Sentence-BERT embedding
  - 盲区闭合: "没网缓存" vs "限制联网" 从 cos=0.000 → cos≈0.60-0.80
  - 新增能力: 语义等价检测、跨语言等价、表达质量/对抗意图区分
  - 仍不提供: 真值判定（那是 L4 的活）、意图理解（L3+ 组合）
```

---

### 8. 审计检查表

向 MSS 审计框架提交本层时，必须逐条通过：

| 审计项 | 标准 | 状态 |
|:---|:---|:---|
| 类型签名有且仅使用本层值域 | `RawTokenStream` → `SignalQuality`，不含 `Meaning`/`Intent`/`Truth` | ✅ |
| 每次输出包含 limitations 块 | 含盲区数+高风险数+已知失效案例 | ✅ |
| 不声明语义理解 | 文档与代码均不含 "semantic" "understanding" "meaning" | ✅ |
| 有明确的升级路径 | `_UPGRADE_PATH` 块，条件 + 跃迁后的能力变化 | ✅ |
| 跨层穿越方向已声明 | 允许/禁止方向已文档化 | ✅ |

---

**文档版本**: v1.0
**MSS 层级**: L2 (词法感知层)
**关联 KB**: H434 (MSS-7-001)
**关联公理**: A2(信息切片)、A3(热税)、A6(矛盾升维)
**关联组件**: LexicalGuard v2.0, skill_api.py v2.3