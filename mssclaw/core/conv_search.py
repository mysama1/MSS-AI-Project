#!/usr/bin/env python3
"""
MSS Conversation Search — 对话记录/缓存搜索器
索引来源: Git commits → Sprint/H-ID ← Memory files → KB entries

CLI:
  mssclaw recall "Type II experiment"      # keyword search
  mssclaw recall --sprint 185              # sprint scope
  mssclaw recall --date 2026-06-17         # date filter
  mssclaw recall --h-id H650              # H-ID lookup
  mssclaw recall --index                   # rebuild index
  mssclaw recall --stats                   # index stats
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ─── Config ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(os.environ.get("MSS_PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))
INDEX_PATH = PROJECT_ROOT / ".conv_index.json"
KB_DIR = PROJECT_ROOT / "kb"
MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"

# ─── Semantic Bridge (v2.0) ────────────────────────────────────
# Maps user-query terms → canonical MSS terms
SEMANTIC_ALIASES: Dict[str, List[str]] = {
    # Type II / contradiction concepts
    "typeii": ["type-ii", "type2", "type ii", "type_2", "type-2", "双稳定子", "矛盾消解", "contradiction",
              "tension", "conflict", "对立", "悖论消解", "二选一"],
    "囚徒困境": ["prisoner's dilemma", "nash", "nash均衡", "博弈", "game theory", "type ii", "type2"],
    # Heat tax / thermodynamics
    "热税": ["heat tax", "heat-tax", "热力学", "thermodynamic", "不可约化", "irreducible", "waste",
            "h = k × w / b", "三层热税", "l0", "l1", "l2"],
    "热力学": ["heat tax", "热税", "thermodynamic", "entropy", "熵", "能量", "energy"],
    "entropy": ["熵", "热力学", "heat tax", "delta", "∆"],
    # Delta / openness
    "delta": ["∆", "δ", "开放度", "维持条件", "openness", "rho"],
    "开放度": ["delta", "∆", "openness", "rho", "闭合", "closure"],
    # Architecture / engineering
    "测试": ["test", "pytest", "testing", "benchmark", "se-bench", "coverage", "覆盖"],
    "基准": ["benchmark", "se-bench", "eval", "评测", "score", "评分"],
    "路由": ["router", "route", "scene", "routing", "场景", "dispatch"],
    "管道": ["pipeline", "流水线", "streaming", "metrics", "指标"],
    # KB / knowledge
    "知识库": ["kb", "knowledge base", "h-id", "条目", "entry", "json"],
    "搜索": ["search", "recall", "grep", "find", "query", "检索", "索引", "index"],
    # Closure / molting
    "蜕壳": ["molting", "molt", "闭合", "closure", "淘汰", "prune", "硬化", "hardening"],
    "闭合": ["closure", "蜕壳", "molting", "收敛", "convergence", "catlab"],
    # Agent / multi-agent
    "多智能体": ["multi-agent", "swarm", "agent", "mcdp", "consensus", "共识"],
    "agent": ["智能体", "代理", "swarm", "multi-agent", "mcdp"],
    # Memory
    "记忆": ["memory", "guard", "memoryguard", "delta threshold", "存储"],
    # Black hole
    "黑洞": ["black hole", "blackhole", "crtr", "意义场", "事件视界", "event horizon"],
    # Catlab / category theory
    "范畴": ["category", "catlab", "functor", "函子", "3-范畴", "kleisli"],
}

# Source weight for search-η scoring
SOURCE_WEIGHTS = {"git": 0.7, "memory": 0.6, "kb": 1.0, "lcm": 0.8}

# Recency decay half-life (days) — entries older than this get score ×0.5
RECENCY_HALF_LIFE_DAYS = 7.0


@dataclass
class ConvEntry:
    """A single conversation record in the index."""
    source: str           # "git" | "memory" | "kb" | "lcm"
    timestamp: str        # ISO datetime
    sprint: Optional[int] = None
    h_ids: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    summary: str = ""
    file: str = ""        # source file path
    commit: str = ""      # git SHA (if git source)


@dataclass
class ConvIndex:
    entries: List[ConvEntry] = field(default_factory=list)
    updated: str = ""
    stats: Dict[str, int] = field(default_factory=dict)


class ConvSearch:
    """Conversation / cache search engine."""

    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or PROJECT_ROOT
        self.index_path = self.root / ".conv_index.json"
        self.index = ConvIndex()

    # ─── Indexing pipelines ──────────────────────────────────────

    def rebuild(self) -> ConvIndex:
        """Rebuild the full conversation index from all sources."""
        entries = []
        entries.extend(self._index_git())
        entries.extend(self._index_memory())
        entries.extend(self._index_kb())
        self.index.entries = entries
        self.index.updated = datetime.now(timezone.utc).isoformat()
        self.index.stats = self._compute_stats(entries)
        return self.index

    def _index_git(self) -> List[ConvEntry]:
        """Extract Sprint + H-ID + keyword data from git log."""
        try:
            raw = subprocess.check_output(
                ["git", "log", "--oneline", "--no-decorate", "-n", "200"],
                cwd=str(self.root), text=True, encoding="utf-8", errors="replace",
                timeout=5
            )
        except Exception:
            return []

        entries = []
        for line in raw.strip().split("\n"):
            if not line:
                continue
            parts = line.split(" ", 1)
            sha = parts[0]
            msg = parts[1] if len(parts) > 1 else ""

            # Extract sprint number
            sprint = None
            sm = re.search(r"Sprint\s*(\d+)", msg)
            if sm:
                sprint = int(sm.group(1))

            # Extract H-IDs
            h_ids = re.findall(r"H(\d{3,4})", msg)
            h_ids_full = [f"H{h}" for h in h_ids]

            # Extract keywords (capitalized words > 2 chars)
            keywords = list(set(
                w for w in re.findall(r"[A-Z][a-z]{2,}", msg)
                if w not in ("Sprint", "Commit")
            ))

            entries.append(ConvEntry(
                source="git",
                timestamp="",  # git log --oneline doesn't give date
                sprint=sprint,
                h_ids=h_ids_full,
                keywords=keywords[:8],
                summary=msg[:200],
                commit=sha,
            ))

        return entries

    def _index_memory(self) -> List[ConvEntry]:
        """Scan memory files for dated conversation entries."""
        entries = []
        if not MEMORY_DIR.exists():
            return entries

        for f in sorted(MEMORY_DIR.glob("2026-*.md")):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Rough date extraction from filename
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
            date_prefix = date_match.group(1) if date_match else ""

            # Find H-ID mentions
            h_ids = list(set(re.findall(r"\bH(\d{3,4})\b", text)))
            h_ids_full = [f"H{h}" for h in h_ids]

            # Find sprint mentions
            sprints = set()
            for sm in re.finditer(r"Sprint\s*(\d+)", text):
                sprints.add(int(sm.group(1)))

            # Extract section headers as keywords
            headers = re.findall(r"^##\s*(.+)$", text, re.MULTILINE)
            keywords = [h.strip() for h in headers[:10]]

            # Find first meaningful time mention
            ts = f"{date_prefix}T00:00:00" if date_prefix else ""

            entries.append(ConvEntry(
                source="memory",
                timestamp=ts,
                sprint=list(sprints)[0] if sprints else None,
                h_ids=h_ids_full[:15],
                keywords=keywords,
                summary=f"Memory file: {f.name} ({len(text)} chars, {len(sprints)} sprints)",
                file=str(f),
            ))

        return entries

    def _index_kb(self) -> List[ConvEntry]:
        """Index KB JSON entries for cross-reference."""
        entries = []
        if not KB_DIR.exists():
            return entries

        for f in sorted(KB_DIR.rglob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue

            # Handle both single object and array
            items = data if isinstance(data, list) else [data]

            for item in items:
                if not isinstance(item, dict):
                    continue
                h_id = item.get("h_id", "")
                title = item.get("title", "")
                related = item.get("related", [])
                tags = item.get("tags", [])
                date = item.get("date", "")

                keywords = tags[:5] if tags else []
                if title:
                    keywords.append(title)

                entries.append(ConvEntry(
                    source="kb",
                    timestamp=f"{date}T00:00:00" if date else "",
                    h_ids=[h_id] if h_id else [],
                    keywords=keywords,
                    summary=title[:200] if title else f.name,
                    file=str(f),
                ))

        return entries

    # ─── Query engine (v2.0) ────────────────────────────────────

    def _expand_query(self, query: str) -> List[str]:
        """Expand query with semantic aliases.
        E.g., 'Type II' → ['Type II', 'typeii', 'type-ii', 'type2', '双稳定子', '矛盾消解', ...]
        """
        expanded = [query]
        q_lower = query.lower().strip()
        # Direct alias lookup
        if q_lower in SEMANTIC_ALIASES:
            expanded.extend(SEMANTIC_ALIASES[q_lower])
        # Partial match: each word in query
        for word in q_lower.split():
            if word in SEMANTIC_ALIASES:
                expanded.extend(SEMANTIC_ALIASES[word])
        return list(set(expanded))

    def _delta_score(self, entry: ConvEntry) -> float:
        """Compute Δ (activity level) for an entry: 0=dead/obsolete, 1.0=active.
        Based on recency and source freshness."""
        # KB entries: always 1.0 (authoritative)
        if entry.source == "kb":
            return 1.0
        # Recency decay
        if not entry.timestamp:
            return 0.5  # git entries have no timestamp → neutral
        try:
            ts = entry.timestamp
            if ts.endswith("Z"):
                ts = ts.replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts)
            now = datetime.now(timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            delta_days = (now - ts).total_seconds() / 86400
            decay = 0.5 ** (delta_days / RECENCY_HALF_LIFE_DAYS)
            return max(0.2, min(1.0, decay))
        except (ValueError, AttributeError):
            return 0.5  # unparseable → neutral

    def search(self, query: str = "", sprint: Optional[int] = None,
               date: Optional[str] = None, h_id: Optional[str] = None,
               source: Optional[str] = None, max_results: int = 15,
               semantic: bool = True) -> tuple:
        """Search with semantic bridging + search-η scoring + delta tagging.
        Returns (results, meta) where meta = {query_expanded, coverage, avg_delta}.
        """
        if not self.index.entries:
            self.load()

        results = self.index.entries

        # Filter by sprint
        if sprint is not None:
            results = [e for e in results if e.sprint == sprint]

        # Filter by date prefix
        if date:
            results = [e for e in results if e.timestamp.startswith(date)]

        # Filter by H-ID
        if h_id:
            h_id_upper = h_id.upper()
            results = [e for e in results if h_id_upper in e.h_ids]

        # Filter by source
        if source:
            results = [e for e in results if e.source == source]

        meta = {"query_expanded": [query], "coverage": len(results), "avg_delta": 0.0}

        # Keyword ranking with semantic expansion
        if query:
            # Semantic expansion
            terms = self._expand_query(query) if semantic else [query]
            meta["query_expanded"] = terms
            meta["semantic_enabled"] = semantic

            scored = []
            for e in results:
                score = 0.0
                text = (e.summary + " " + " ".join(e.keywords) + " " + " ".join(e.h_ids)).lower()

                # Search-η components:
                # 1. Keyword match (weight: 0.4)
                kw_score = 0.0
                for term in terms:
                    t = term.lower()
                    if t in text:
                        kw_score += 2.0  # exact match
                    elif t in e.summary.lower():
                        kw_score += 3.0  # summary match bonus
                    # Word-level
                    tw = t.split()
                    for w in tw:
                        if len(w) > 1 and w in text:
                            kw_score += 0.5
                score += kw_score * 0.4

                # 2. Source weight (weight: 0.3)
                sw = SOURCE_WEIGHTS.get(e.source, 0.5)
                score += sw * 0.3

                # 3. Recency / delta (weight: 0.3)
                delta = self._delta_score(e)
                score += delta * 0.3

                if kw_score > 0:  # only include entries with keyword match
                    scored.append((score, e, {"delta": delta, "kw_score": kw_score}))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = [s[1] for s in scored]
            # Store metadata dict for display, indexed by entry id (position)
            meta["_scores"] = {str(i): {"eta": s[2]["kw_score"], "delta": s[2]["delta"]}
                                for i, s in enumerate(scored) if i < len(results)}

            # Compute aggregate delta
            deltas = [s[2]["delta"] for s in scored]
            meta["avg_delta"] = round(sum(deltas) / len(deltas), 2) if deltas else 0.0

        results = results[:max_results]
        meta["coverage"] = len(results)
        return results, meta

    # ─── Persistence ─────────────────────────────────────────────

    def save(self):
        """Save index to disk."""
        data = {
            "entries": [
                {
                    k: v for k, v in e.__dict__.items()
                } for e in self.index.entries
            ],
            "updated": self.index.updated,
            "stats": self.index.stats,
        }
        self.index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self):
        """Load index from disk."""
        if not self.index_path.exists():
            self.rebuild()
            self.save()
            return
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.index.entries = [
            ConvEntry(**e) for e in data.get("entries", [])
        ]
        self.index.updated = data.get("updated", "")
        self.index.stats = data.get("stats", {})

    # ─── Helpers ─────────────────────────────────────────────────

    def _compute_stats(self, entries: List[ConvEntry]) -> Dict[str, int]:
        sources = {}
        sprints = set()
        h_ids = set()
        for e in entries:
            sources[e.source] = sources.get(e.source, 0) + 1
            if e.sprint:
                sprints.add(e.sprint)
            for h in e.h_ids:
                h_ids.add(h)
        return {
            "total_entries": len(entries),
            "unique_sprints": len(sprints),
            "unique_h_ids": len(h_ids),
            **sources,
        }


# ─── CLI formatter ───────────────────────────────────────────────

def format_results(results, query_info: str = "", meta: dict = None):
    """Pretty-print search results with search-η metadata."""
    if query_info:
        print(f"\n  🔍 {query_info}")
    if meta and meta.get("semantic_enabled"):
        aliases = meta.get("query_expanded", [])[:5]
        print(f"  🔗 语义扩展: {' → '.join(aliases)}")
    if meta and "avg_delta" in meta:
        d = meta["avg_delta"]
        d_icon = "🟢" if d > 0.7 else "🟡" if d > 0.3 else "🔴"
        print(f"  {d_icon} Δ_avg: {d:.2f}  |  Results: {meta.get('coverage', 0)}")
    print(f"  {'─' * 50}\n")

    if not results:
        print("  (no results — try --semantic or broader query)\n")
        return

    for i, e in enumerate(results):
        source_icon = {"git": "📝", "memory": "🧠", "kb": "📚", "lcm": "💬"}.get(e.source, "📄")
        sprint_tag = f" [Sprint {e.sprint}]" if e.sprint else ""
        h_tag = f" [{', '.join(e.h_ids[:3])}]" if e.h_ids else ""
        ts_tag = f"  {e.timestamp[:10]}" if e.timestamp else ""
        # Extract η/Δ from meta scores
        extra = ""
        if meta and "_scores" in meta:
            si = meta["_scores"].get(str(i), {})
            eta = si.get("eta", 0)
            d = si.get("delta", 0)
            if eta > 0:
                extra = f"  η={eta:.1f} Δ={d:.2f}"

        print(f"  {i+1}. {source_icon}{sprint_tag}{h_tag}{extra}{ts_tag}")
        print(f"     {e.summary[:130]}")
        if e.commit:
            print(f"     commit: {e.commit[:8]}")
        if e.file:
            print(f"     file: {Path(e.file).name}")
        print()

# ─── CLI entry ───────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MSS Conversation Search")
    parser.add_argument("query", nargs="?", default="", help="Search keywords")
    parser.add_argument("--sprint", type=int, help="Filter by sprint number")
    parser.add_argument("--date", type=str, help="Filter by date prefix (e.g. 2026-06-17)")
    parser.add_argument("--h-id", type=str, help="Filter by H-ID (e.g. H650)")
    parser.add_argument("--source", type=str, choices=["git", "memory", "kb"], help="Source filter")
    parser.add_argument("--index", action="store_true", help="Force rebuild index")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("-n", "--max", type=int, default=15, help="Max results")
    args = parser.parse_args()

    cs = ConvSearch()

    if args.index or not cs.index_path.exists():
        print("  🔄 Rebuilding index...", end=" ", flush=True)
        cs.rebuild()
        cs.save()
        print("done\n")

    if args.stats:
        if not cs.index.entries:
            cs.load()
        s = cs.index.stats
        print(f"\n  📊 Index Stats ({cs.index.updated[:19]})")
        print(f"  ───────────────────────────────────")
        print(f"  Entries:   {s.get('total_entries', 0)}")
        print(f"  Sprints:   {s.get('unique_sprints', 0)}")
        print(f"  H-IDs:     {s.get('unique_h_ids', 0)}")
        print(f"  Git:       {s.get('git', 0)}")
        print(f"  Memory:    {s.get('memory', 0)}")
        print(f"  KB:        {s.get('kb', 0)}")
        print()
        return

    if not args.query and not args.sprint and not args.date and not args.h_id:
        parser.print_help()
        return

    query_desc = []
    if args.query:
        query_desc.append(f'query="{args.query}"')
    if args.sprint:
        query_desc.append(f"sprint={args.sprint}")
    if args.date:
        query_desc.append(f"date={args.date}")
    if args.h_id:
        query_desc.append(f"h-id={args.h_id}")

    results, meta = cs.search(
        query=args.query,
        sprint=args.sprint,
        date=args.date,
        h_id=args.h_id,
        source=args.source,
        max_results=args.max,
    )

    format_results(results, ", ".join(query_desc), meta)


if __name__ == "__main__":
    main()
