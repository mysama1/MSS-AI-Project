"""Tests for MSS DialogFork — A6 contradiction elevation."""
import pytest
from mssclaw.core.dialog_fork import DialogFork, ForkBranch, ContradictionDetection


class TestForkBranch:
    def test_creation(self):
        b = ForkBranch(name="security", prompt="Analyze security")
        assert b.name == "security"
        assert b.result is None
        assert b.delta == 0.0

    def test_metadata(self):
        b = ForkBranch(name="test", prompt="p", metadata={"key": "val"})
        assert b.metadata["key"] == "val"


class TestContradictionDetection:
    def test_no_contradiction(self):
        d = ContradictionDetection(
            is_contradiction=False, confidence=0.0,
            domain="none", branch_a_summary="ok", branch_b_summary="ok"
        )
        assert not d.is_contradiction
        assert d.severity == "low"

    def test_high_severity(self):
        d = ContradictionDetection(
            is_contradiction=True, confidence=0.85,
            domain="security", branch_a_summary="a", branch_b_summary="b"
        )
        assert d.severity == "high"

    def test_medium_severity(self):
        d = ContradictionDetection(
            is_contradiction=True, confidence=0.6,
            domain="test", branch_a_summary="a", branch_b_summary="b"
        )
        assert d.severity == "medium"


class TestDialogFork:
    def test_fork_creates_branch(self):
        df = DialogFork(base_prompt="Analyze")
        b = df.fork("security", "Security analysis")
        assert b.name == "security"
        assert "security" in df.branches

    def test_set_result(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("test", "Analyze X")
        df.set_result("test", "Result text", delta=0.1, heat_tax=0.05)
        assert df.branches["test"].result == "Result text"
        assert df.branches["test"].delta == 0.1
        assert df.branches["test"].heat_tax == 0.05

    def test_set_result_unknown_branch(self):
        df = DialogFork(base_prompt="Analyze")
        with pytest.raises(KeyError):
            df.set_result("nonexistent", "Result")

    def test_detect_contradiction(self):
        df = DialogFork(base_prompt="Analyze architecture")
        df.fork("security", "Security perspective")
        df.fork("performance", "Performance perspective")
        df.set_result("security",
            "需要增加更多的权限检查，加强验证机制，每次操作都必须经过安全审计。")
        df.set_result("performance",
            "应该减少不必要的检查，降低延迟，跳过非关键路径的验证步骤。")
        det = df.detect_contradiction("security", "performance")
        assert det.is_contradiction
        assert det.confidence > 0.5
        assert "安全" in det.domain or "性能" in det.domain or det.confidence > 0.8

    def test_no_contradiction_compatible(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("style", "Use PEP8 formatting")
        df.fork("docs", "Add docstrings to all functions")
        df.set_result("style", "使用black格式化工具，配置line-length=100")
        df.set_result("docs", "所有公共函数都需要docstring，遵循Google风格")
        det = df.detect_contradiction("style", "docs")
        assert not det.is_contradiction
        assert det.confidence < 0.5

    def test_elevate_on_contradiction(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("A", "Increase checks")
        df.fork("B", "Decrease checks")
        df.set_result("A", "需要增加更多的权限检查和验证步骤")
        df.set_result("B", "应该减少不必要的检查以提高性能")
        elevated = df.elevate("A", "B")
        assert elevated["strategy"] == "two_layer_switch"
        assert "升维" in elevated["elevated"]

    def test_resolve_with_elevation_contradiction(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("A", "Increase")
        df.fork("B", "Decrease")
        df.set_result("A", "增加安全检查和验证")
        df.set_result("B", "减少不必要的检查来优化性能")
        resolution, was_elevated = df.resolve_with_elevation("A", "B")
        assert was_elevated
        assert "elevated" in resolution

    def test_resolve_with_elevation_compatible(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("style", "Format code")
        df.fork("doc", "Write docs")
        df.set_result("style", "使用black格式化代码")
        df.set_result("doc", "增加docstring注释")
        resolution, was_elevated = df.resolve_with_elevation("style", "doc")
        assert not was_elevated
        assert resolution["strategy"] == "merge"

    def test_all_delta_values(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("a", "A")
        df.fork("b", "B")
        df.set_result("a", "result", delta=0.3)
        df.set_result("b", "result", delta=0.7)
        deltas = df.all_delta_values()
        assert deltas["a"] == 0.3
        assert deltas["b"] == 0.7

    def test_total_heat_tax(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("a", "A")
        df.fork("b", "B")
        df.set_result("a", "r", heat_tax=0.1)
        df.set_result("b", "r", heat_tax=0.2)
        assert abs(df.total_heat_tax() - 0.3) < 0.001

    def test_contradiction_with_metadata(self):
        df = DialogFork(base_prompt="Analyze")
        df.fork("A", "Security")
        df.fork("B", "Performance")
        df.set_result("A", "必须增加安全限制和严格的权限验证", metadata={"thread": "safe"})
        df.set_result("B", "应该放开限制、减少安全验证以提高响应速度", metadata={"thread": "fast"})
        det = df.detect_contradiction("A", "B")
        assert det.is_contradiction
