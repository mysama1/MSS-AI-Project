---
name: mss-knowledge-navigator
description: >
  Load when you need to query the MSS knowledge base, check task status,
  audit theoretical debt, map research directions, or generate architecture visualizations.
  NOT for coding tasks (use code skills) or general conversation.
version: 1.0.0
created: 2026-06-01
layer: L2 (Meta-Theory & Methodology)
confidence: 0.95
tags: [MSS, knowledge-base, query, research-map, debt-tracking, visualization]
dependencies: []
---

# MSS Knowledge Navigator

## Intent-Level Guidance (DO NOT railroad)

Every script below provides deterministic answers. Model should judge when to call which, and explain any unexpected output. If a query doesn't match any script's scope, respond with the closest matching category and a brief "no match" note.

## Module 1: Knowledge Base Query

### Quick Lookup
```bash
python scripts/kb_query.py "<keyword>"
```

Returns: H-id, title, layer, confidence, MSS-X category, tags.
Format: `H426 [L2, 0.97] MSS-2-003 | 黎曼猜想本体论解释 | tags: [riemann, primes]`

### Deep Search (regex)
```bash
python scripts/kb_query.py --regex "<pattern>" --category MSS-2
```

### Category Browse
```bash
python scripts/kb_list.py MSS-2
```

Returns: all entries in that category, sorted by confidence.

**Activation pattern**: "查一下H426", "MSS-2有哪些条目", "找黎曼相关的", "知识库里有啥"

**Gotcha**: H-ids may appear as `h426_*.jsonl` files in filesystem. Always use `kb_query.py` — don't navigate files directly.

---

## Module 2: Task Bar Snapshot

```bash
python scripts/task_snapshot.py
```

Returns: P0/P1/P2/P3 task count, in-progress items, completion %, overdue warnings.

**Activation pattern**: "任务栏", "当前有哪些任务", "D5系列进度", "进行中的任务"

**Gotcha**: `task_bar.md` lives at `E:\QClaw-Data\workspace\task_bar.md`. Path is auto-detected via environment variable.

---

## Module 3: Research Direction Heatmap

```bash
python scripts/research_map.py
```

Returns: ASCII heatmap of 9 MSS categories, with status markers.

**Status markers**:
- ✅ completed (>5 entries, all Grade A/B)
- 🔄 in progress (active task in category)
- ⚠️ gaps (missing H entries or unresolved debt)
- ❌ abandoned (deprecated, content permanently lost)

**Activation pattern**: "研究方向地图", "哪些方向完成了", "热力图", "MSS-3现状"

**Gotcha**: Heatmap uses _master_index.md classification. If entries were reclassified recently, re-run indexer first.

---

## Module 4: Theoretical Debt Tracker

```bash
python scripts/debt_tracker.py
```

Returns: TD-XXX list with priority, description, clearance status.

**Priority levels**: P0 (blocks core), P1 (damages consistency), P2 (cosmetic)

**Activation pattern**: "理论债务", "TD-MATH-01状态", "还有哪些没清偿"

**Gotcha**: Debt entries live in `memory/2026-06-01.md`. Pattern `TD-\w+-\d+` in memory file = debt record. "已清偿" / "进行中" / "待启动" status extracted from context.

---

## Module 5: Architecture Visualization

```bash
python scripts/arch_viz.py --format ascii   # ASCII art (terminal)
python scripts/arch_viz.py --format mermaid # Mermaid diagram
```

**Outputs**:
- L0-L5 six-layer MSS architecture with H entries per layer
- Tool chain map (which script serves which module)
- Category completeness radar

**Activation pattern**: "画个架构图", "MSS六层", "工具链地图", "可视化"

**Gotcha**: Mermaid output renders in web UI. ASCII renders in terminal. Default = ascii for webchat, mermaid for canvas.

---

## Module 6: Grade Standard Query

```bash
python scripts/grade_query.py --threshold 0.8   # Grade A
python scripts/grade_query.py --threshold 0.5   # Grade B
python scripts/grade_query.py --layer L1         # L1 entries only
```

**Grade standards**:
- A: confidence ≥ 0.8, no contamination markers
- B: 0.5 ≤ confidence < 0.8, needs review
- C: confidence < 0.5, pending completion

**Activation pattern**: "Grade A有哪些", "高置信度条目", "L1层有哪些"

---

## Error Handling

| Error | Response |
|:---|:---|
| No matching entries | "未找到匹配项。建议搜索相关关键词，或检查拼写。当前可用类别：MSS-1~MSS-9。" |
| Task bar file not found | "任务栏文件未找到。请确认 E:\QClaw-Data\workspace\task_bar.md 存在，或运行 kb_restructure.py 重建索引。" |
| Memory file corrupted | "记忆文件读取失败。从 _master_index.md 重建索引，跳过 debt_tracker 模块。" |

## What NOT to do
- Do NOT write this Skill's contents into KB as H entries — it IS the tool, not the content
- Do NOT output raw JSONL content here — use kb_query.py for that
- Do NOT run full KB integrity scan here — use kb_integrity_check.py for that
- Do NOT explain how to write Skills in this context — this is a tool Skill, not a meta-Skill

## Maintenance Log
- 2026-06-01: Created. 6 modules. All scripts idempotent.
- After adding new H entries: re-run `python kb_restructure.py` to update index.
- After adding new tasks: update `task_bar.md` before calling task_snapshot.