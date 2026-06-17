#!/usr/bin/env python3
"""
MSS Vector Memory — LanceDB-backed semantic search layer for conv_search.

Integrates LanceDB for:
- Embedding vectors via any OpenAI-compatible endpoint (Ollama local)
- Hybrid search: keyword (SQLite FTS-style) + vector (cosine similarity)
- Semantic deduplication (near-duplicate detection)
- Delta-weighted retrieval (recent + semantically relevant)

P2 item from 7-framework comparison: "向量搜索 for conv_search"
Inspired by OpenClaw's sqlite-vec usage pattern and Mem0's hybrid approach.
"""

from __future__ import annotations
import os
import json
import time
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import lancedb


# ─── Config ───────────────────────────────────────────────

DEFAULT_DB_PATH = os.path.expanduser("~/.mssclaw/vector_memory")
EMBEDDING_DIM = 768  # nomic-embed-text default for Ollama
HALF_LIFE_DAYS = 7  # for delta temporal decay


# ─── Data Models ──────────────────────────────────────────

@dataclass
class MemoryEntry:
    """A single indexed memory entry."""
    content: str
    source: str  # "kb", "git", "memory", "conversation"
    tags: List[str] = field(default_factory=list)
    delta: float = 0.5  # semantic freshness (0-1)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A ranked search result with metadata."""
    content: str
    source: str
    score: float  # combined score (keyword + vector + delta)
    keyword_score: float = 0.0
    vector_score: float = 0.0
    delta_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─── Embedding Provider ───────────────────────────────────

class OllamaEmbedder:
    """Thin wrapper over Ollama's embedding API."""

    def __init__(self, model: str = "nomic-embed-text:latest", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._dim = None

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = self._probe_dim()
        return self._dim

    def _probe_dim(self) -> int:
        """Test embed to determine dimension."""
        try:
            import requests
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if "nomic-embed-text" in r.text:
                # Known dim for nomic-embed-text
                return 768
        except Exception:
            pass
        return EMBEDDING_DIM

    def embed(self, text: str) -> List[float]:
        """Get embedding vector for text."""
        import requests
        resp = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": text},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"][0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding (sequential for compatibility)."""
        return [self.embed(t) for t in texts]


# ─── Vector Store ─────────────────────────────────────────

class VectorMemoryStore:
    """LanceDB-backed memory store for semantic search."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        embedder: Optional[OllamaEmbedder] = None,
        table_name: str = "memories",
    ):
        self.db_path = db_path
        self.embedder = embedder or OllamaEmbedder()
        self.table_name = table_name
        self._db: Optional[lancedb.DBConnection] = None
        self._table: Optional[lancedb.table.Table] = None
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create or open the LanceDB table."""
        self._db = lancedb.connect(self.db_path)
        try:
            self._table = self._db.open_table(self.table_name)
        except Exception:
            self._table = None

    def _create_table(self, data: List[Dict[str, Any]]) -> lancedb.table.Table:
        """Create table from data (auto-detects schema)."""
        import pyarrow as pa
        schema = pa.schema([
            pa.field("content", pa.string()),
            pa.field("source", pa.string()),
            pa.field("tags", pa.list_(pa.string())),
            pa.field("delta", pa.float32()),
            pa.field("timestamp", pa.float64()),
            pa.field("vector", pa.list_(pa.float32(), self.embedder.dim)),
            pa.field("metadata", pa.string()),  # JSON string
        ])
        self._table = self._db.create_table(self.table_name, data, schema=schema)
        return self._table

    def add(self, entry: MemoryEntry, vector: Optional[List[float]] = None) -> int:
        """Add a memory entry to the store. Returns count added."""
        if vector is None:
            try:
                vector = self.embedder.embed(entry.content)
            except Exception:
                return 0  # No embedding model available

        row = {
            "content": entry.content,
            "source": entry.source,
            "tags": entry.tags,
            "delta": float(entry.delta),
            "timestamp": float(entry.timestamp),
            "vector": [float(v) for v in vector],
            "metadata": json.dumps(entry.metadata),
        }

        if self._table is None:
            self._create_table([row])
            return 1
        else:
            self._table.add([row])
            return 1

    def add_batch(self, entries: List[MemoryEntry]) -> int:
        """Add multiple entries at once."""
        try:
            texts = [e.content for e in entries]
            vectors = self.embedder.embed_batch(texts)
        except Exception:
            return 0  # No embedding model available

        rows = []
        for entry, vec in zip(entries, vectors):
            rows.append({
                "content": entry.content,
                "source": entry.source,
                "tags": entry.tags,
                "delta": float(entry.delta),
                "timestamp": float(entry.timestamp),
                "vector": [float(v) for v in vec],
                "metadata": json.dumps(entry.metadata),
            })

        if self._table is None:
            self._create_table(rows)
        else:
            self._table.add(rows)
        return len(rows)

    def search(
        self,
        query: str,
        top_k: int = 10,
        sources: Optional[List[str]] = None,
        delta_threshold: float = 0.0,
    ) -> List[SearchResult]:
        """Vector search with optional source filter and delta threshold."""
        if self._table is None:
            return []

        query_vec = self.embedder.embed(query)

        # LanceDB vector search
        results = self._table.search(
            [float(v) for v in query_vec]
        ).limit(top_k * 2).to_list()  # fetch extra for post-filtering

        # Build scored results
        scored: List[SearchResult] = []
        now = time.time()
        for row in results:
            # Source filter
            if sources and row["source"] not in sources:
                continue

            # Delta temporal decay
            age_days = (now - row["timestamp"]) / 86400
            decay_factor = math.exp(-math.log(2) * age_days / HALF_LIFE_DAYS)
            effective_delta = row["delta"] * decay_factor

            if effective_delta < delta_threshold:
                continue

            # LanceDB _distance is cosine distance, convert to similarity
            vector_score = 1.0 - float(row.get("_distance", 0.0))

            # Metadata
            meta = {}
            try:
                meta = json.loads(row.get("metadata", "{}"))
            except Exception:
                pass

            # Combined score: 70% vector + 30% delta
            combined = vector_score * 0.7 + effective_delta * 0.3

            scored.append(SearchResult(
                content=row["content"],
                source=row["source"],
                score=round(combined, 4),
                vector_score=round(vector_score, 4),
                delta_score=round(effective_delta, 4),
                tags=row.get("tags", []),
                metadata=meta,
            ))

        # Sort by combined score descending
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def deduplicate(self, threshold: float = 0.95) -> int:
        """Remove near-duplicate entries (cosine similarity > threshold)."""
        if self._table is None:
            return 0

        all_rows = self._table.to_pandas()
        if len(all_rows) < 2:
            return 0

        removed = 0
        # Simple pairwise similarity check
        for i in range(len(all_rows) - 1):
            if removed > 0:
                break  # limited dedup for safety

        return 0  # placeholder — full dedup needs optimized approach

    def count(self) -> int:
        """Total entries in store."""
        if self._table is None:
            return 0
        return self._table.count_rows()

    def stats(self) -> Dict[str, Any]:
        """Store statistics."""
        if self._table is None:
            return {"count": 0, "sources": {}, "avg_delta": 0}

        count = self._table.count_rows()
        df = self._table.to_pandas()
        sources = df["source"].value_counts().to_dict() if count > 0 else {}
        avg_delta = float(df["delta"].mean()) if count > 0 else 0
        return {"count": count, "sources": sources, "avg_delta": round(avg_delta, 3)}


# ─── Hybrid Search Engine ─────────────────────────────────

class HybridSearchEngine:
    """Combines vector search with keyword matching and delta ranking.

    This is the P2 upgrade to conv_search — replaces/supplements
    the pure keyword FTS with LanceDB vector search.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        embedder: Optional[OllamaEmbedder] = None,
        semantic_aliases: Optional[Dict[str, List[str]]] = None,
    ):
        self.vector_store = VectorMemoryStore(db_path=db_path, embedder=embedder)
        self.semantic_aliases = semantic_aliases or {}

    def expand_query(self, query: str) -> List[str]:
        """Expand query with semantic aliases."""
        expanded = [query]
        query_lower = query.lower()
        for key, aliases in self.semantic_aliases.items():
            if key in query_lower or any(a.lower() in query_lower for a in aliases):
                expanded.extend([key] + [a for a in aliases if a.lower() not in query_lower])
        return list(dict.fromkeys(expanded))  # dedup preserving order

    def search_hybrid(
        self,
        query: str,
        top_k: int = 10,
        sources: Optional[List[str]] = None,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> List[SearchResult]:
        """Hybrid search: vector + keyword with configurable weights."""
        # Expand query for keyword matching
        expanded = self.expand_query(query)
        query_terms = set()
        for term in expanded:
            query_terms.update(term.lower().split())

        # Vector search
        vec_results = self.vector_store.search(query, top_k=top_k * 2, sources=sources)

        # Keyword scoring overlay
        for result in vec_results:
            content_lower = result.content.lower()
            match_count = sum(1 for term in query_terms if term in content_lower)
            if query_terms:
                result.keyword_score = min(1.0, match_count / len(query_terms))
            else:
                result.keyword_score = 0.0

            # Recalculate combined score
            result.score = round(
                result.vector_score * vector_weight +
                result.keyword_score * keyword_weight +
                result.delta_score * 0.1,
                4,
            )

        # Re-sort
        vec_results.sort(key=lambda x: x.score, reverse=True)
        return vec_results[:top_k]

    def index_texts(
        self,
        texts: List[str],
        source: str = "memory",
        tags: Optional[List[str]] = None,
        delta: float = 0.5,
    ) -> int:
        """Batch index texts into vector store."""
        entries = [
            MemoryEntry(content=text, source=source, tags=tags or [], delta=delta)
            for text in texts
        ]
        return self.vector_store.add_batch(entries)

    def index_kb_entries(self, kb_dir: str) -> int:
        """Index all knowledge base JSON files."""
        entries = []
        kb_path = Path(kb_dir)
        if not kb_path.exists():
            return 0

        for json_file in kb_path.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                text = json.dumps(data, ensure_ascii=False)
                # Extract tags from h_id / title if available
                tags = []
                if isinstance(data, dict):
                    for field in ("h_id", "title", "tags"):
                        val = data.get(field)
                        if val:
                            tags.append(str(val))
                entries.append(MemoryEntry(
                    content=text,
                    source="kb",
                    tags=tags,
                    delta=1.0,  # KB entries are always fresh
                    metadata={"filename": json_file.name},
                ))
            except Exception:
                pass

        return self.vector_store.add_batch(entries)

    def search_eta(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Search with η-weighted ranking (MSS-specific).

        η = keyword_score * 0.4 + source_weight * 0.3 + delta_score * 0.3
        """
        results = self.search_hybrid(query, top_k=top_k)
        source_weights = {"kb": 1.0, "memory": 0.7, "conversation": 0.5, "git": 0.6}

        for r in results:
            sw = source_weights.get(r.source, 0.5)
            r.score = round(
                r.keyword_score * 0.4 + sw * 0.3 + r.delta_score * 0.3,
                4,
            )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = HybridSearchEngine(
        semantic_aliases={
            "type ii": ["囚徒困境", "nash均衡", "联合入场", "多agent消解"],
            "热税": ["heat tax", "能耗", "计算成本"],
            "矛盾升维": ["a6", "elevation", "升维", "dimension"],
        }
    )

    # Index some demo texts
    engine.index_texts([
        "MSS-AI uses heat tax budgeting to prevent wasteful computation",
        "Type II contradiction resolution through MCDP mediation",
        "The A6 elevation protocol handles contradictions by ascending dimensions",
        "Nash equilibrium is broken by joint entrance trust gating (H634)",
        "Pipeline metrics collection with P50/P99 latency tracking",
    ], source="conversation")

    print(f"Total entries: {engine.vector_store.count()}")

    # Search
    print("\n=== Search: 'heat tax budget' ===")
    for r in engine.search_hybrid("heat tax budget", top_k=3):
        print(f"  [{r.score:.3f}] {r.content[:80]}...")

    print("\n=== Search: 'multi agent conflict' ===")
    for r in engine.search_eta("multi agent conflict", top_k=3):
        print(f"  [η={r.score:.3f}] {r.content[:80]}...")
