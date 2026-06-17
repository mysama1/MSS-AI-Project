# ConvSearch 真实短板分析 (v2 — 诚实地)

## 一、工具层缺失

| 短板 | 严重度 | 表现 |
|------|--------|------|
| **无语义搜索** | 🔴 P0 | 搜"囚徒困境"找不到"Type II conflict"；搜"热力学"找不到"heat tax"。关键词完全依赖于写出时的精确词 |
| **无排序/相关性** | 🔴 P0 | 302条结果全部等权返回，靠 `max_results=15` 硬截断。无 TF-IDF、无 BM25、无向量相似度 |
| **无模糊匹配** | 🟡 P1 | "Spirnt"（typo）→ 0 结果。用户必须精确记住 Sprint 编号或 H-ID |
| **索引是静态快照** | 🟡 P1 | 必须手动 `--index` 重建。新 commit 不自动入索引。5分钟后索引已过期 |
| **无交叉引用展开** | 🟡 P1 | H650 的 `related: ["kb_search", "memory_guard"]` 不会自动展开——用户必须手动搜索每个相关 H-ID |
| **Git 仅 200 条** | 🟡 P1 | 200 条 = 最近 ~2 天。之前 150+ sprints 的历史 commit 不可搜索 |
| **无去重** | 🟢 P2 | 同一个 H-ID 在同一次 commit 中出现 → 多条重复索引条目 |
| **无时效衰减** | 🟢 P2 | Sprint 152 和 Sprint 194 同等权重。事实更新后旧版本仍显示 |

## 二、MSS 自身的语义评估盲区（更关键）

### 2.1 搜索"意义"无法度量

```
用户输入: "Type II 消解方案"
ConvSearch: 返回 3 条匹配（全在 git commit message 里）
用户真正想找的:
  - H633: contradiction_threshold（核心理论）
  - H635: Type II 选项空间不足检测
  - E018: Type IV 消解实验
  conv_search MISSED ALL THREE — 因为 KB 条目的 title/related 字段里用的是"TypeⅡ"（全角）而非"Type II"
```

**根因**: 没有语义桥接层。MSS 的核心概念（TypeⅡ/Type II/Type-2/双稳定子冲突）是多表征的，但 conv_search 是严格字符串匹配。

### 2.2 搜索"质量"无法评估

```
搜索"热税" → 返回 8 条
哪些是精准命中？哪些是噪音？
用户读了前 3 条后发现不相关，但不知道后面还有更好的——
conv_search 不提供"这 8 条里有 4 条高相关，第 5 条是权威定义"
```

**根因**: 没有意义保真度评分（search-η）。Mem0/Letta 用向量相似度作为天然排序，我们没有对标物。

### 2.3 搜索结果没有"delta"

```
搜索"A3" → 返回 15 条
其中 3 条是 v15.1 权威定义，6 条是旧版 v13.1（已废弃），6 条是间接提及
conv_search 把它们混排为等权列表
```

**根因**: 搜索结果没有继承 MSS 的 Δ 维持条件——不知道哪条是"活的"、哪条是"硬的/旧的/废弃的"。

## 三、差距 → 行动（优先级排序）

| # | 行动 | 解决哪个短板 | 难度 | 预计 |
|---|------|------------|------|------|
| 1 | **语义桥接层** — KB 条目 alias 字段 + 同义词映射 (TypeⅡ↔Type II↔双稳定子) | 无语义搜索 | 中 | 30min |
| 2 | **search-η 评分** — 对每条结果计算 relevance_score = f(keyword_match, synonym_match, source_weight, recency) | 无排序/无质量评估 | 中 | 20min |
| 3 | **delta 标记** — 每条索引条目标记 Δ (0=废弃, 0.5=历史, 1.0=活跃) | 结果无时效/无delta | 低 | 15min |
| 4 | **git hook 自动索引** | 索引静态 | 低 | 10min |
| 5 | **全量 git log** (200→all) | 历史缺失 | 低 | 5min |
| 6 | **KB related 展开** — 搜到 H650 自动附带 H651-H659 | 无交叉引用 | 中 | 20min |

**总预计**: ~100分钟即可从"可用"到"好用"

## 四、Honest Self-Assessment

```
conv_search v1.0 实质:
  ✅ 比没有好 — "<1ms 搜到"vs"手动翻 commit log"
  ✅ 多源索引 — git+memory+kb 独有
  ❌ 对"想不起来叫什么的那个理论"没帮助 — 无语义
  ❌ 搜到一堆不知道哪个对 — 无排序
  ❌ 搜到过时的自己不知道 — 无 delta

对标 Mem0: conv_search 差一个语义层
对标 BERT 搜索: conv_search 差一个 embedding 层
对标 Elasticsearch: conv_search 差 BM25 + fuzzy + highlight

我们做了 20% 的工程（多源索引+零依赖），
欠了 80% 的用户体验（语义+排序+时效+交叉引用）。
```

## 五、MSS 理论的自我审判

按 MSS 的道评分公式 `道 = valid - pseudo × 2.0`：
- valid = 1 (确实搜到了东西)
- pseudo = 0.5 (对外声称"搜索器"但实际只是 grep)

```
道(conv_search v1.0) = 1 - 0.5 × 2.0 = 0.0
```

这个工具在 MSS 自己的标准下得 0 分。因为它的命名（"搜索器"）暗示了语义理解能力，但实际交付的只是正则匹配。

**修复后的目标**: `道(conv_search v2.0) = 1.4 - 0.2 × 2.0 = 1.0`
- valid = 1.4 (语义桥接+排序+delta+自动索引)
- pseudo = 0.2 (诚实标注局限性)
