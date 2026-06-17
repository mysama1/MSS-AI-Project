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

    # ─── Query engine ────────────────────────────────────────────

    def search(self, query: str = "", sprint: Optional[int] = None,
               date: Optional[str] = None, h_id: Optional[str] = None,
               source: Optional[str] = None, max_results: int = 15) -> List[ConvEntry]:
        """Search the index with multiple filters."""

        # Ensure index is loaded
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

        # Keyword ranking
        if query:
            q_lower = query.lower()
            scored = []
            for e in results:
                score = 0
                text = (e.summary + " " + " ".join(e.keywords) + " " + " ".join(e.h_ids)).lower()
                # Direct match bonus
                if q_lower in text:
                    score += 5
                # Word-level match
                words = q_lower.split()
                for w in words:
                    if w in text:
                        score += 1
                    if w in e.summary.lower():
                        score += 2
                if score > 0:
                    scored.append((score, e))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [s[1] for s in scored]

        return results[:max_results]

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

def format_results(results: List[ConvEntry], query_info: str = ""):
    """Pretty-print search results."""
    if query_info:
        print(f"\n  🔍 {query_info}")
    print(f"  ─────────────────────────────────────────────\n")

    if not results:
        print("  (no results)\n")
        return

    for e in results:
        source_icon = {"git": "📝", "memory": "🧠", "kb": "📚", "lcm": "💬"}.get(e.source, "📄")
        sprint_tag = f" [Sprint {e.sprint}]" if e.sprint else ""
        h_tag = f" [{', '.join(e.h_ids[:5])}]" if e.h_ids else ""
        ts_tag = f"  {e.timestamp[:10]}" if e.timestamp else ""

        print(f"  {source_icon}{sprint_tag}{h_tag}{ts_tag}")
        print(f"    {e.summary[:120]}")
        if e.commit:
            print(f"    commit: {e.commit[:8]}")
        if e.file:
            print(f"    file: {Path(e.file).name}")
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

    results = cs.search(
        query=args.query,
        sprint=args.sprint,
        date=args.date,
        h_id=args.h_id,
        source=args.source,
        max_results=args.max,
    )

    format_results(results, ", ".join(query_desc))


if __name__ == "__main__":
    main()
