# MSS conv_search.py vs 业界对话搜索对比

## 竞品矩阵

| 维度 | Mem0 (25K⭐) | Letta/MemGPT (19K⭐) | Supermemory (17K⭐) | **conv_search.py** |
|------|-------------|---------------------|--------------------|--------------------|
| **检索方式** | 向量+知识图谱 | LLM自主调度 | RAG+向量 | 纯文本正则/字典 |
| **外部依赖** | Qdrant/ChromaDB | LLM API | AI服务 | **0 (stdlib only)** |
| **查询类型** | 语义相似 | LLM召回 | 语义+过滤 | **关键词/Sprint/日期/H-ID** |
| **延迟** | 50-200ms | LLM依赖 | 50-200ms | **<1ms (dict lookup)** |
| **存储** | 向量DB | DB+JSON | 向量DB | 单个JSON文件 |
| **多源索引** | ❌ | ❌ | 有限 | **✅ 3源 (git+memory+kb)** |
| **Sprint跟踪** | ❌ | ❌ | ❌ | **✅ 152 sprints** |
| **H-ID交叉引用** | ❌ | ❌ | ❌ | **✅ 143 H-IDs** |
| **纯离线** | 部分 | ❌ | 部分 | **✅** |
| **无需LLM** | ❌ | ❌ | ❌ | **✅** |
| **语义搜索** | ✅ | ✅ | ✅ | ❌ |
| **自动记忆提取** | ✅ | ✅ | ✅ | ❌ |
| **去重/时效感知** | ✅ (Mem0-g) | ✅ | ✅ | ❌ |
| **规模** | 百万级 | 百万级 | 百万级 | 302条 |

## 定位判定

conv_search.py **不与 Mem0/Letta 竞争**——它们做的是 AI Agent 的长期记忆层，
conv_search 做的是**项目知识资产的结构化快速定位**。

独特性：
1. **Sprint 轴线**：Mem0/Letta 没有"Sprint 185发生了什么"的概念——conv_search 天然具有
2. **H-ID 交叉引用**：一个 H650 可以同时找到 git commit + KB 条目 + memory 提及
3. **零依赖**：单文件 JSON，可离线/air-gap 运行
4. **反查密度**：143个H-ID在302条记录中平均2.1次出现，形成知识图谱雏形

弱点（可改进）：
- 无语义搜索（可加 sentence-transformers 可选层）
- 无自动记忆提取（需人工 commit 规范保质量）
- 无去重/时效感知
- 索引量小（302 vs 百万级）

## 差距 → 行动

| 差距 | 行动 | 优先级 |
|------|------|--------|
| 无语义搜索 | `conv_search --semantic` + all-MiniLM-L6-v2 | P2 |
| 无记忆提取 | git hook: commit → auto-index | P1 |
| 无去重 | merge相近条目 | P3 |
| 规模小 | 回溯全量 git log (200→all) | P1 |
