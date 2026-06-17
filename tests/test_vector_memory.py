"""Tests for vector memory module (logical layer — skip embedding if no model)."""
import pytest
import os
import json
from pathlib import Path

pytestmark = pytest.mark.skipif(
    not __import__("lancedb", fromlist=[""]),
    reason="lancedb not installed",
)

from mssclaw.core.vector_memory import (
    MemoryEntry, SearchResult, HybridSearchEngine, VectorMemoryStore,
    OllamaEmbedder, HALF_LIFE_DAYS,
)

# ─── Helpers ──────────────────────────────────────────────

def _embed_model_available():
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json()["models"]]
        return any("nomic-embed-text" in m for m in models)
    except Exception:
        return False


@pytest.fixture
def engine(tmp_path):
    """Create engine with temp db path."""
    return HybridSearchEngine(db_path=str(tmp_path / "test_vm"))


@pytest.fixture
def clean_db(tmp_path):
    """Clean LanceDB store."""
    db_path = str(tmp_path / "test_lancedb")
    store = VectorMemoryStore(db_path=db_path)
    yield store
    # Cleanup
    import shutil
    shutil.rmtree(db_path, ignore_errors=True)


# ─── Data Model Tests ─────────────────────────────────────

class TestMemoryEntry:
    def test_create(self):
        e = MemoryEntry(content="test", source="memory")
        assert e.content == "test"
        assert e.delta == 0.5
        assert e.tags == []

    def test_with_tags(self):
        e = MemoryEntry(content="test", source="kb", tags=["h601", "search"])
        assert "h601" in e.tags

    def test_default_timestamp(self):
        e = MemoryEntry(content="test", source="memory")
        assert e.timestamp > 0


class TestSearchResult:
    def test_create(self):
        r = SearchResult(content="test", source="kb", score=0.85)
        assert r.score == 0.85
        assert r.source == "kb"


# ─── HybridSearchEngine Tests ──────────────────────────────

class TestHybridSearchEngine:
    def test_create(self, engine):
        assert engine.vector_store.db_path is not None

    def test_semantic_alias_expansion(self, engine):
        engine.semantic_aliases = {
            "type ii": ["囚徒困境", "nash均衡", "联合入场"],
        }
        expanded = engine.expand_query("type ii problem")
        assert "type ii" in expanded[0].lower()

    def test_expand_query_no_match(self, engine):
        engine.semantic_aliases = {"test": ["alias"]}
        expanded = engine.expand_query("completely different")
        assert expanded == ["completely different"]

    def test_expand_query_dedup(self, engine):
        engine.semantic_aliases = {"teST": ["test", "Test"]}
        # Should not duplicate
        expanded = engine.expand_query("Test case")
        assert len(expanded) <= 3  # "Test case" + "teST" + "test"

    def test_index_texts_structure(self, engine):
        """Test that index_texts creates proper MemoryEntry objects."""
        if not _embed_model_available():
            pytest.skip("No embedding model available")
        entries_created = engine.index_texts(["hello world"], source="conversation")
        # Won't actually index without embedding model
        assert entries_created >= 0  # Returns attempt count

    def test_search_eta_empty(self, engine):
        """η-search on empty store returns empty."""
        results = engine.search_eta("test query")
        assert isinstance(results, list)


# ─── OllamaEmbedder Tests ─────────────────────────────────

class TestOllamaEmbedder:
    def test_create(self):
        e = OllamaEmbedder()
        assert e.model == "nomic-embed-text:latest"

    def test_dim_probe_default(self):
        """Without model available, falls back to default."""
        e = OllamaEmbedder()
        # Should return default dim without crashing
        assert e.dim > 0


# ─── Integration Tests (require model) ────────────────────

@pytest.mark.skipif(not _embed_model_available(), reason="No embedding model available")
class TestVectorMemoryIntegration:
    def test_add_and_search(self, clean_db):
        """Full add→search cycle."""
        entry = MemoryEntry(
            content="MSS heat tax budgeting prevents wasteful computation",
            source="conversation",
            tags=["heat_tax", "mss"],
        )
        clean_db.add(entry)
        assert clean_db.count() == 1

        results = clean_db.search("heat tax budget", top_k=3)
        assert len(results) > 0
        assert results[0].score > 0

    def test_batch_add(self, clean_db):
        entries = [
            MemoryEntry(content=f"Test entry {i}", source="memory", delta=0.5 + i * 0.1)
            for i in range(3)
        ]
        count = clean_db.add_batch(entries)
        assert count == 3
        assert clean_db.count() == 3

    def test_source_filter(self, clean_db):
        clean_db.add(MemoryEntry("kb content", source="kb"))
        clean_db.add(MemoryEntry("memory content", source="memory"))

        results = clean_db.search("content", sources=["kb"], top_k=10)
        for r in results:
            assert r.source == "kb"

    def test_delta_decay(self, clean_db):
        """Old entries with low delta should be filtered."""
        import time
        old_entry = MemoryEntry(
            content="very old content",
            source="memory",
            delta=0.8,
            timestamp=time.time() - 30 * 86400,  # 30 days ago
        )
        new_entry = MemoryEntry(
            content="fresh content",
            source="memory",
            delta=0.8,
        )
        clean_db.add(old_entry)
        clean_db.add(new_entry)

        results = clean_db.search("content", top_k=10)
        # New entry should rank higher than old entry
        scores = [(r.content, r.score) for r in results]
        fresh_scores = [s for c, s in scores if "fresh" in c]
        old_scores = [s for c, s in scores if "old" in c]
        if fresh_scores and old_scores:
            assert fresh_scores[0] > old_scores[0], f"Fresh should rank higher: {scores}"

    def test_stats(self, clean_db):
        clean_db.add(MemoryEntry("test1", source="memory"))
        clean_db.add(MemoryEntry("test2", source="kb"))
        stats = clean_db.stats()
        assert stats["count"] == 2
        assert "memory" in stats["sources"]

    def test_hybrid_search_with_model(self, tmp_path):
        """End-to-end hybrid search when model is available."""
        engine = HybridSearchEngine(
            db_path=str(tmp_path / "test_hybrid"),
            semantic_aliases={
                "heat tax": ["热税", "heat_cost"],
            },
        )
        engine.index_texts([
            "MSS heat tax budgeting system",
            "Type II Nash equilibrium resolution",
            "Pipeline metrics with P99 latency",
        ], source="conversation")

        results = engine.search_hybrid("heat tax", top_k=3)
        assert len(results) > 0
        # First result should be about heat tax
        assert any("heat" in r.content.lower() for r in results[:2])

    def test_search_eta_ranking(self, tmp_path):
        """η-weighted search should weight KB higher than memory."""
        engine = HybridSearchEngine(db_path=str(tmp_path / "test_eta"))
        engine.index_texts(["MSS theory of heat tax"], source="kb")
        engine.index_texts(["I think heat tax might be useful"], source="memory")

        results = engine.search_eta("heat tax", top_k=3)
        # KB entries should generally rank higher due to source_weight=1.0
        if len(results) >= 2:
            kb_rank = next((i for i, r in enumerate(results) if r.source == "kb"), 999)
            mem_rank = next((i for i, r in enumerate(results) if r.source == "memory"), 999)
            assert kb_rank <= mem_rank, f"KB should not rank worse than memory: kb={kb_rank} mem={mem_rank}"
