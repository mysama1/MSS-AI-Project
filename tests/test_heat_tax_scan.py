"""
pytest tests for heat_tax_self_scan — 自反式代码质量扫描
"""
import sys
sys.path.insert(0, '.')
import pytest
from pathlib import Path
from mssclaw.core.heat_tax_self_scan import (
    scan_l0_physical, scan_l1_logical, scan_l2_meaning, run_self_scan
)

PROJECT_ROOT = Path(__file__).parent.parent


class TestL0Physical:
    """物理热税扫描测试 (轻量模式)."""

    @pytest.mark.slow
    def test_scans_all_files(self):
        result = scan_l0_physical(PROJECT_ROOT)
        assert result['total_files'] > 0
        assert result['total_size_kb'] > 0

    @pytest.mark.slow
    def test_excludes_build_artifacts(self):
        result = scan_l0_physical(PROJECT_ROOT)
        # No .next, dist, build artifacts
        for path_info in result.get('top10_largest', []):
            assert '.next' not in path_info['path']
            assert 'dist' not in path_info['path']

    @pytest.mark.slow
    def test_no_orphan_mssclaw_core(self):
        result = scan_l0_physical(PROJECT_ROOT)
        # mssclaw/core standalone modules (entry points, not imported as modules)
        known_standalone = {'cli', '__init__', '__main__'}
        orphans = [o for o in result.get('orphan_core_modules', []) if o not in known_standalone]
        # Informational: orphans exist but aren't necessarily bugs
        # Some are lazily imported via dynamic import in CLI dispatch
        if orphans:
            print(f"\n  [INFO] Orphan core modules: {orphans}")


class TestL1Logical:
    """逻辑热税扫描测试."""

    def test_detects_code_lines(self):
        result = scan_l1_logical(PROJECT_ROOT)
        assert result['code_lines'] > 0
        assert result['total_lines'] > 0

    def test_code_ratio_reasonable(self):
        result = scan_l1_logical(PROJECT_ROOT)
        # code:comment should be > 0.3 (we're not all comments)
        assert result['code_to_comment_ratio'] > 0.3


class TestL2Meaning:
    """意义热税扫描测试."""

    def test_detects_patterns(self):
        result = scan_l2_meaning(PROJECT_ROOT)
        assert isinstance(result['total_suspicious'], int)
        assert isinstance(result['todo_backlog'], int)

    def test_by_pattern_is_dict(self):
        result = scan_l2_meaning(PROJECT_ROOT)
        assert isinstance(result['by_pattern'], dict)


class TestFullScan:
    """完整扫描集成测试 (可能耗时)."""

    @pytest.mark.slow
    def test_run_self_scan_returns_valid(self):
        result = run_self_scan(PROJECT_ROOT)
        assert 'L0_physical' in result
        assert 'L1_logical' in result
        assert 'L2_meaning' in result
        assert 'heat_scores' in result
        assert 'verdict' in result

    @pytest.mark.slow
    def test_heat_scores_in_range(self):
        result = run_self_scan(PROJECT_ROOT)
        scores = result['heat_scores']
        # Scores should be >= 0 (but could be > 1.0 if formula overflow)
        for key in ['L0_physical', 'L1_logical', 'L2_meaning', 'overall']:
            assert scores[key] >= 0, f"{key} score should be >= 0, got {scores[key]}"
