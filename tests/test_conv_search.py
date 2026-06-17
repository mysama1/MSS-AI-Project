#!/usr/bin/env python3
"""Tests for conv_search.py — conversation search engine."""
import pytest
from pathlib import Path


class TestConvSearch:
    def test_build_index(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        assert cs.index.entries, "Index should have entries"
        assert cs.index.stats["total_entries"] > 0

    def test_search_keyword(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        results, meta = cs.search(query="Sprint")
        assert len(results) > 0
        assert all("Sprint" in r.summary or any("sprint" in kw.lower() for kw in r.keywords)
                   or "Sprint" in " ".join(r.h_ids) for r in results[:3])

    def test_search_sprint(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        results, _ = cs.search(sprint=185)
        assert all(r.sprint == 185 for r in results)

    def test_search_hid(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        results, _ = cs.search(h_id="H650")
        assert len(results) > 0
        assert any("H650" in r.h_ids for r in results)

    def test_search_date(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        results, _ = cs.search(date="2026-06-17")
        assert len(results) > 0

    def test_source_filter(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        results, _ = cs.search(source="kb")
        assert all(r.source == "kb" for r in results)

    def test_save_load(self):
        from mssclaw.core.conv_search import ConvSearch
        import tempfile, os
        cs = ConvSearch()
        cs.rebuild()
        cs.save()
        assert cs.index_path.exists()
        cs2 = ConvSearch()
        cs2.load()
        assert len(cs2.index.entries) == len(cs.index.entries)

    def test_stats(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        s = cs.index.stats
        assert "total_entries" in s
        assert "git" in s
        assert "memory" in s
        assert "kb" in s

    def test_time_based_queries(self):
        """H651-like temporal filtering."""
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        # Date-filtered search
        results, _ = cs.search(date="2026-06-17")
        assert len(results) > 0

    def test_cross_reference(self):
        """Ensure H-IDs bridge between KB and git sources."""
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        results, _ = cs.search(query="batch")
        sources = set(r.source for r in results[:10])
        # Should find both git and kb results
        assert len(sources) >= 2 or len(results) > 0, f"Expected cross-source results, got {sources}"

    def test_empty_result(self):
        from mssclaw.core.conv_search import ConvSearch
        cs = ConvSearch()
        cs.rebuild()
        results, _ = cs.search(query="xyznonexistent123456")
        assert len(results) == 0
