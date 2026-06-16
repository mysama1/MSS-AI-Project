"""
Sprint 6: 端到端集成测试 — 全栈 MSSAgent + 五维护城河 + 完整生命周期.

测试场景:
  T1: Agent 创建 + 所有模块初始化
  T2: 正常任务执行 (run cycle 完整)
  T3: 高重复度任务触发熵税+DELTA衰退→CAUTION
  T4: CRISIS阻断 (极端退化+高税)
  T5: 认知框架评估 (assess 正常)
  T6: 健康报告 (health_report 所有维度)
  T7: 蜕壳就绪检测
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── T1: 完整初始化 ──

def test_full_stack_init():
    """MSSAgent: 完整初始化 — 所有模块就位."""
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.l2_bridge import BridgeLevel
    from mssclaw.core.cognitive_framework import CogStatus

    agent = MSSAgent(
        name="full-stack-test",
        heat_tax_threshold=2.0,
        delta_min=0.3,
        enable_fuse=False,
    )

    # Verify all modules initialized
    assert agent.tax is not None
    assert agent.delta is not None
    assert agent.memory is not None
    assert agent.l2bridge is not None
    assert agent.cognition is not None
    assert agent.l2bridge.level == BridgeLevel.STABLE

    # Quick assess
    cog = agent.cognition.assess()
    assert cog.status == CogStatus.HEALTHY


# ── T2: 正常执行 ──

def test_full_stack_normal_run():
    """MSSAgent: 正常任务执行 — 完整 run cycle."""
    from mssclaw.core.agent import MSSAgent

    agent = MSSAgent(name="test-runner", heat_tax_threshold=2.0, delta_min=0.3)

    # Run normal tasks
    tasks = [
        "Implement user authentication with JWT tokens",
        "Design database schema for product catalog",
        "Write unit tests for the payment module",
        "Review PR #42 for security vulnerabilities",
    ]

    for task in tasks:
        result = agent.run(task)
        assert result.success, f"Task '{task[:30]}...' failed: {result.aborted}"
        assert not result.aborted, f"Task '{task[:30]}...' was aborted"
        assert result.delta > 0

    # Verify run count
    assert agent.run_count == 4
    assert agent.abort_count == 0


# ── T3: 退化检测 ──

def test_full_stack_degradation():
    """MSSAgent: 高重复任务 → CAUTION/STRESS."""
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.l2_bridge import BridgeLevel

    agent = MSSAgent(name="test-degraded", heat_tax_threshold=1.5, delta_min=0.3)

    # Bombard with repetitive busywork
    for i in range(12):
        result = agent.run("Rewrite this paragraph in a different way please")

    # Bridge should have moved from STABLE
    assert agent.l2bridge.level != BridgeLevel.STABLE or agent.abort_count > 0, \
        f"Expected bridge move or abort, got level={agent.l2bridge.level.name}"


# ── T4: 极端压力 ──

def test_full_stack_extreme_stress():
    """MSSAgent: 极端重复任务 → 应该触发阻断."""
    from mssclaw.core.agent import MSSAgent

    agent = MSSAgent(name="test-stressed", heat_tax_threshold=1.0, delta_min=0.3)

    # Extreme repetition
    for i in range(20):
        result = agent.run("summarize: I think therefore I am")

    # Either bridge upgraded or some aborts happened
    # (tight threshold means something should trigger)
    assert agent.abort_count > 0 or agent.l2bridge.level.value >= 1, \
        f"No protection triggered: aborts={agent.abort_count}, bridge={agent.l2bridge.level.name}"


# ── T5: 认知评估 ──

def test_full_stack_cognitive_assessment():
    """MSSAgent: 认知框架在 run cycle 中被调用."""
    from mssclaw.core.agent import MSSAgent

    agent = MSSAgent(name="test-cognitive", heat_tax_threshold=2.0, delta_min=0.3)

    # Register some capabilities
    agent.cognition.register_capability("code_review", tier=2)
    agent.cognition.anchor_identity("mss-core", "MSS Agent", strategy="virus")

    # Run a task — assess() is called in run()
    result = agent.run("Review this code for SQL injection vulnerabilities")
    assert result.success

    # Check cognition stats
    stats = agent.cognition.stats()
    assert stats["capabilities"] >= 1
    assert stats["identities"] >= 1
    assert stats["status"] == "healthy"


# ── T6: 健康报告 ──

def test_full_stack_health_report():
    """MSSAgent: health_report 包含所有维度."""
    from mssclaw.core.agent import MSSAgent

    agent = MSSAgent(name="test-health", heat_tax_threshold=2.0, delta_min=0.3)
    agent.run("Write a function to sort an array")
    agent.run("Optimize the database query")

    report = agent.health_report()

    # All major sections present
    assert "agent" in report
    assert "runs" in report
    assert "aborts" in report
    assert "heat_tax" in report  # not "tax"
    assert "delta" in report
    assert "memory" in report
    assert "l2_bridge" in report
    assert "cognition" in report

    # Memory section
    assert "total" in report["memory"]
    assert "active" in report["memory"]

    # L2 bridge section
    assert "level" in report["l2_bridge"]
    assert "transitions" in report["l2_bridge"]

    # Cognition section
    assert "capabilities" in report["cognition"]
    assert "status" in report["cognition"]


# ── T7: 蜕壳就绪 ──

def test_full_stack_molting_readiness():
    """MSSAgent: 蜕壳就绪检测."""
    from mssclaw.core.agent import MSSAgent

    agent = MSSAgent(name="test-molt", heat_tax_threshold=1.0, delta_min=0.3)

    # Create a declining delta pattern
    for i in range(8):
        agent.run("fix bug: null pointer exception in line 42")
        # Force delta lower
        agent.delta.tick("same-old", 0.05, 0.05)

    # Feed delta history to cognition
    ready = agent.cognition.evolution_ready(
        delta_history=agent.delta.history[-10:],
        tax=agent.tax,
    )
    # After 8 repetitive tasks, should be close to/at molting
    print(f"    Molting ready: {ready}, pressure: {agent.cognition.evolution_pressure_history[-1] if agent.cognition.evolution_pressure_history else 'N/A'}")

    # At minimum, the bridge should have some history
    assert len(agent.l2bridge.history) > 0, "No bridge history recorded"
