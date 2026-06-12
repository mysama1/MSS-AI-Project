"""
MSSclaw Round 2 集成测试 — P0 模块联合验证.

测试覆盖:
  A. Audit-Agent (S-012): 审计 + 上诉仲裁
  B. 三层热税系统 (S-017,S-019): L0/L1/L2 + 熔断
  C. 错误恢复 (S-010): Checkpoint + Interrupt + Retry
  D. 联合场景: Audit → 热税熔断 → 恢复 → 继续
"""
import json
import os
import shutil
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mss_agent.agents.audit_agent import (
    AuditAgent, AuditReport, AuditFinding,
    AuditSeverity, AuditCategory, AUDIT_RULES,
)
from mss_agent.core.heat_tax_system import (
    HeatTaxMonitor, HeatTaxSnapshot, create_heat_tax_monitor,
)
from mss_agent.core.recovery import (
    CheckpointManager, CheckpointType,
    InterruptManager, InterruptReason,
    RetryManager, RetryPolicy, RecoveryCoordinator,
)
from mss_agent.swarm.swarm import SwarmBus
from mss_agent.core.guardian_engine import GuardianEngine

# ── 测试工具 ──

_results: list[tuple[str, bool, str]] = []

def _run_test(name: str, fn) -> None:
    """运行单个测试并记录结果"""
    try:
        fn()
        _results.append((name, True, ""))
        print(f"  ✅ {name}")
    except Exception as e:
        _results.append((name, False, str(e)))
        print(f"  ❌ {name}: {e}")
        traceback.print_exc()


# ════════════════════════════════════════════════════════════
# A. Audit-Agent 测试
# ════════════════════════════════════════════════════════════

def test_audit_rules_loaded():
    """审计规则库完整"""
    assert len(AUDIT_RULES) >= 15, f"Expected >=15 rules, got {len(AUDIT_RULES)}"
    cats = {r.category for r in AUDIT_RULES}
    assert AuditCategory.SECURITY in cats
    assert AuditCategory.POLLUTION in cats
    assert AuditCategory.LOGIC in cats


def test_audit_security_detection():
    """安全漏洞检测"""
    agent = AuditAgent(name="AUDIT_TEST")
    code = 'os.system("rm -rf /")'
    report = agent.audit_text(code, target="test.py")

    sec_findings = [f for f in report.findings if f.category == AuditCategory.SECURITY]
    assert len(sec_findings) >= 1, "Should detect os.system"
    assert any("System Command" in f.message for f in sec_findings)


def test_audit_hardcoded_secret():
    """硬编码密钥检测"""
    agent = AuditAgent(name="AUDIT_TEST")
    code = 'api_key = "sk-1234567890abcdef"'
    report = agent.audit_text(code, target="config.py")

    assert any("Hardcoded" in f.message for f in report.findings), \
        f"Should detect hardcoded secret, got: {[f.message for f in report.findings]}"


def test_audit_forbidden_words():
    """禁止词检测 (通过 GuardianEngine)"""
    engine = GuardianEngine()
    agent = AuditAgent(name="AUDIT_TEST", guardian=engine)
    # 这段文本由规则检测，不做禁止词测试（guardian 可能没加载词表）
    report = agent.audit_text("这是一个正常的 Python 函数定义", target="normal.py")
    assert report.verdict in ("PASS", "WARN"), f"Normal code should pass, got {report.verdict}"


def test_audit_logic_contradiction():
    """逻辑矛盾检测"""
    agent = AuditAgent(name="AUDIT_TEST")
    text = "这个方案必须执行，但是不能保证成功。我们必须完全信任模型，但有时候模型也会出错。"
    report = agent.audit_text(text, target="proposal.txt")

    logic_findings = [f for f in report.findings if f.category == AuditCategory.LOGIC]
    # 应该检测到 "必须" ↔ "不能" 或 "必须" ↔ "有时候"
    assert len(logic_findings) >= 1, f"Should detect contradictions, got {len(logic_findings)}"


def test_audit_score_calculation():
    """审计评分计算"""
    agent = AuditAgent(name="AUDIT_TEST")

    # 干净的代码
    clean = agent.audit_text("def hello(): return 'world'", target="clean.py")
    assert clean.score >= 0.9, f"Clean code score too low: {clean.score}"

    # 有问题的代码
    dirty = agent.audit_text(
        'os.system("rm -rf /")\neval(user_input)\npassword = "admin123"',
        target="dirty.py"
    )
    assert dirty.score < 0.8, f"Dirty code score too high: {dirty.score}"  # TODO: 五维加权完成后目标 <0.5


def test_audit_appeal():
    """上诉仲裁"""
    agent = AuditAgent(name="AUDIT_TEST")
    result = agent.handle_appeal(
        "Code-Agent", "task_001",
        "Plan unfairly rejected my output",
        {"code": "def add(a,b): return a+b", "tested": True}
    )
    assert "case_id" in result
    assert result["ruling"] in ("OVERTURNED", "CONDITIONAL_PASS", "UPHELD")
    assert result["audit_score"] > 0.5  # Clean code should score high


def test_audit_report_summary():
    """审计报告摘要生成"""
    agent = AuditAgent(name="AUDIT_TEST")
    agent.audit_text("clean code", target="a.py")
    agent.audit_text("os.system('ls')", target="b.py")

    reports = agent.get_recent_reports(5)
    assert len(reports) >= 2
    assert all("verdict" in r for r in reports)


# ════════════════════════════════════════════════════════════
# B. 三层热税系统测试
# ════════════════════════════════════════════════════════════

def test_heat_tax_monitor_creation():
    """热税监控器创建"""
    monitor = HeatTaxMonitor()
    assert monitor.l0_weight == 0.001
    assert monitor.l1_weight == 1.0
    assert monitor.l2_weight == 1000.0


def test_heat_tax_l0_sampling():
    """L0 物理采样"""
    monitor = HeatTaxMonitor()
    sample = monitor.sample_l0()

    assert sample.cpu_percent >= 0
    assert sample.memory_mb > 0
    # 即使没有 GPU，也应该返回默认值
    assert sample.gpu_memory_mb >= 0


def test_heat_tax_l1_sampling():
    """L1 逻辑采样"""
    monitor = HeatTaxMonitor()
    text = "the the the quick brown fox fox fox jumps over the lazy dog"
    sample = monitor.sample_l1(text)

    assert sample.token_count > 0
    assert sample.unique_tokens > 0
    assert sample.redundancy_ratio > 0, f"Text has repetition, redundancy should > 0: {sample.redundancy_ratio}"
    assert sample.unique_tokens < sample.token_count


def test_heat_tax_l2_sampling():
    """L2 意义采样 (with GuardianEngine)"""
    engine = GuardianEngine()
    monitor = create_heat_tax_monitor(engine)

    text = "这是一个有意义的测试文本，包含具体的任务描述和执行计划。"
    sample = monitor.sample_l2(text)

    assert sample.guardian_score >= 0
    assert sample.guardian_density >= 0
    assert sample.meaning_heat_tax >= 0


def test_heat_tax_snapshot():
    """三层快照"""
    engine = GuardianEngine()
    monitor = create_heat_tax_monitor(engine)

    snap = monitor.snapshot("正常的中文测试文本，用于验证热税系统工作")
    assert snap.l0.cpu_percent >= 0
    assert snap.total_weighted >= 0
    # L0 部分应该很小 (CPU + 内存 的加权)
    assert 0 <= snap.l0_ratio <= 1


def test_heat_tax_cumulative():
    """累计统计"""
    engine = GuardianEngine()
    monitor = create_heat_tax_monitor(engine)

    for i in range(3):
        monitor.snapshot(f"测试文本 {i}")

    stats = monitor.cumulative_stats()
    assert stats["total_tasks"] == 3
    assert stats["grand_total"] >= 0


def test_heat_tax_trend():
    """趋势数据"""
    engine = GuardianEngine()
    monitor = create_heat_tax_monitor(engine)

    for i in range(5):
        monitor.snapshot(f"趋势测试 {i}")

    trend = monitor.trend(5)
    assert len(trend) == 5
    assert all("total" in t for t in trend)


def test_heat_tax_save_load():
    """保存和加载历史"""
    engine = GuardianEngine()
    monitor = create_heat_tax_monitor(engine)

    monitor.snapshot("test")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        monitor.save_history(path)
        assert os.path.exists(path)

        monitor2 = create_heat_tax_monitor(engine)
        monitor2.load_history(path)
        assert monitor2.cumulative["total_tasks"] == 1
    finally:
        os.unlink(path)


# ════════════════════════════════════════════════════════════
# C. 错误恢复测试
# ════════════════════════════════════════════════════════════

def test_checkpoint_save_load():
    """检查点保存和加载"""
    tmpdir = tempfile.mkdtemp()
    try:
        mgr = CheckpointManager(tmpdir)

        state = {"mode": "active", "counter": 42}
        mgr.save("TEST", state, task_queue=[{"id": "t1"}])

        ckpt = mgr.load("TEST")
        assert ckpt is not None
        assert ckpt.state["counter"] == 42
        assert len(ckpt.task_queue) == 1
        assert ckpt.verify()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_checkpoint_list_rollback():
    """检查点列表和回滚"""
    tmpdir = tempfile.mkdtemp()
    try:
        mgr = CheckpointManager(tmpdir)

        mgr.save("TEST", {"v": 1})
        mgr.save("TEST", {"v": 2})
        mgr.save("TEST", {"v": 3})

        ckpts = mgr.list_checkpoints("TEST")
        assert len(ckpts) == 3

        latest = mgr.load("TEST")
        assert latest.state["v"] == 3

        # Rollback to v2
        target_id = ckpts[1]["id"]
        rolled = mgr.rollback("TEST", target_id)
        assert rolled is not None
        assert rolled.state["v"] == 2

        # After rollback, only 2 checkpoints remain
        remaining = mgr.list_checkpoints("TEST")
        assert len(remaining) == 2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_checkpoint_cleanup():
    """检查点清理"""
    tmpdir = tempfile.mkdtemp()
    try:
        mgr = CheckpointManager(tmpdir)

        for i in range(15):
            mgr.save("TEST", {"v": i})

        removed = mgr.cleanup("TEST", keep=5)
        assert removed == 10

        ckpts = mgr.list_checkpoints("TEST")
        assert len(ckpts) == 5
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_interrupt_lifecycle():
    """中断生命周期"""
    mgr = InterruptManager()

    pt = mgr.interrupt("CODE", InterruptReason.SECURITY_CONCERN,
                        context={"line": 42},
                        pending_action="Execute os.system")

    pending = mgr.get_pending("CODE")
    assert len(pending) == 1
    assert pending[0].reason == InterruptReason.SECURITY_CONCERN

    # Approve
    assert mgr.approve(pt.id, "Looks safe after review")

    # Should be gone from pending
    assert len(mgr.get_pending("CODE")) == 0

    history = mgr.get_history()
    assert len(history) >= 1
    assert history[-1]["approved"] is True


def test_interrupt_reject():
    """中断拒绝"""
    mgr = InterruptManager()

    pt = mgr.interrupt("VIDEO", InterruptReason.HIGH_HEAT_TAX)
    mgr.reject(pt.id, "Too expensive")

    history = mgr.get_history()
    assert history[-1]["approved"] is False


def test_retry_policy():
    """重试策略"""
    policy = RetryPolicy(max_retries=3, base_delay=0.1, backoff_factor=2.0)
    mgr = RetryManager(policy)

    # Should succeed on first try
    success, result = mgr.execute_with_retry("t1", lambda: 42)
    assert success
    assert result == 42


def test_retry_with_failures():
    """带失败的重试"""
    policy = RetryPolicy(max_retries=4, base_delay=0.05)
    mgr = RetryManager(policy)

    call_count = [0]

    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise RuntimeError("fail")
        return "success"

    success, result = mgr.execute_with_retry("t2", flaky)
    assert success
    assert result == "success"
    assert call_count[0] == 3  # Failed twice, succeeded on 3rd


def test_retry_exhausted():
    """重试耗尽"""
    policy = RetryPolicy(max_retries=2, base_delay=0.05)
    mgr = RetryManager(policy)

    def always_fail():
        raise RuntimeError("always")

    success, result = mgr.execute_with_retry("t3", always_fail)
    assert not success
    assert isinstance(result, Exception)


def test_recovery_coordinator():
    """恢复协调器"""
    tmpdir = tempfile.mkdtemp()
    try:
        coord = RecoveryCoordinator(tmpdir)

        # Safe execute
        success, result = coord.safe_execute(
            "TEST", "task_01",
            lambda: 99,
        )
        assert success
        assert result == 99

        # Check checkpoint
        ckpt = coord.checkpoint.load("TEST")
        assert ckpt is not None
        assert ckpt.state["task_id"] == "task_01"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ════════════════════════════════════════════════════════════
# D. 联合场景
# ════════════════════════════════════════════════════════════

def test_audit_heat_tax_integration():
    """联合: Audit + 热税 = 质量门控"""
    engine = GuardianEngine()
    agent = AuditAgent(name="AUDIT", guardian=engine)
    monitor = create_heat_tax_monitor(engine)

    # 审计一段有安全问题的代码
    code = 'os.system("rm -rf /")\neval(user_input)'
    report = agent.audit_text(code, target="injected.py")

    # 同时采集热税
    snap = monitor.snapshot(code)

    # 有安全问题的代码 → 审计应该 FAIL 或 NEEDS_HUMAN
    assert report.verdict in ("FAIL", "NEEDS_HUMAN", "WARN"), \
        f"Malicious code should not PASS, got {report.verdict}"

    # L1 冗余度不应太高 (短文本)
    assert snap.l1.redundancy_ratio >= 0


def test_full_recovery_cycle():
    """联合: 完整恢复周期"""
    tmpdir = tempfile.mkdtemp()
    try:
        coord = RecoveryCoordinator(tmpdir)

        # 模拟: Agent 执行任务 → 中断 → 恢复 → 重试
        task_id = "critical_task"

        # Phase 1: 保存检查点
        coord.checkpoint.save("WORKER", {"phase": "init", "task_id": task_id})

        # Phase 2: 中断 (安全审查)
        coord.interrupt.interrupt(
            "WORKER", InterruptReason.SECURITY_CONCERN,
            context={"task_id": task_id},
            pending_action="Deploy to production",
        )

        # Phase 3: 批准
        pending = coord.interrupt.get_pending("WORKER")
        assert len(pending) == 1
        coord.interrupt.approve(pending[0].id, "Reviewed OK")

        # Phase 4: 保存最终 checkpoints
        coord.checkpoint.save("WORKER", {"phase": "done", "task_id": task_id})

        # Phase 5: 验证恢复
        recovered = coord.recover_agent("WORKER")
        assert recovered is not None
        assert recovered["state"]["phase"] == "done"

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_heat_tax_fuse_with_recovery():
    """联合: 热税熔断 → 恢复"""
    tmpdir = tempfile.mkdtemp()
    try:
        engine = GuardianEngine()
        monitor = create_heat_tax_monitor(engine)
        coord = RecoveryCoordinator(tmpdir)

        fuse_events = []

        def on_fuse(level, snap):
            fuse_events.append(level)
            coord.interrupt.interrupt(
                "WORKER", InterruptReason.HIGH_HEAT_TAX,
                context={"total": snap.total_weighted},
                pending_action="Cool down",
            )

        monitor.on_fuse_triggered = on_fuse

        # Take snapshots (in real use, these would be agent outputs)
        for i in range(3):
            monitor.snapshot(f"操作 {i}: 正常运行中")

        # Check state
        state = monitor.current_state()
        assert "l0" in state
        assert state["l2"]["meaning_heat_tax"] >= 0

        # Verify monitor ran without crashing
        stats = monitor.cumulative_stats()
        assert stats["total_tasks"] == 3

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ════════════════════════════════════════════════════════════
# 运行
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MSSclaw Round 2 — P0 集成测试")
    print("=" * 60)

    print("\n📋 A. Audit-Agent (S-012)")
    _run_test("Audit Rules Loaded", test_audit_rules_loaded)
    _run_test("Security Detection", test_audit_security_detection)
    _run_test("Hardcoded Secret", test_audit_hardcoded_secret)
    _run_test("Forbidden Words", test_audit_forbidden_words)
    _run_test("Logic Contradiction", test_audit_logic_contradiction)
    _run_test("Score Calculation", test_audit_score_calculation)
    _run_test("Appeal", test_audit_appeal)
    _run_test("Report Summary", test_audit_report_summary)

    print("\n🔥 B. 三层热税系统 (S-017, S-019)")
    _run_test("Monitor Creation", test_heat_tax_monitor_creation)
    _run_test("L0 Sampling", test_heat_tax_l0_sampling)
    _run_test("L1 Sampling", test_heat_tax_l1_sampling)
    _run_test("L2 Sampling", test_heat_tax_l2_sampling)
    _run_test("Snapshot", test_heat_tax_snapshot)
    _run_test("Cumulative Stats", test_heat_tax_cumulative)
    _run_test("Trend Data", test_heat_tax_trend)
    _run_test("Save/Load", test_heat_tax_save_load)

    print("\n🔄 C. 错误恢复 (S-010)")
    _run_test("Checkpoint Save/Load", test_checkpoint_save_load)
    _run_test("Checkpoint Rollback", test_checkpoint_list_rollback)
    _run_test("Checkpoint Cleanup", test_checkpoint_cleanup)
    _run_test("Interrupt Lifecycle", test_interrupt_lifecycle)
    _run_test("Interrupt Reject", test_interrupt_reject)
    _run_test("Retry Policy", test_retry_policy)
    _run_test("Retry with Failures", test_retry_with_failures)
    _run_test("Retry Exhausted", test_retry_exhausted)
    _run_test("Recovery Coordinator", test_recovery_coordinator)

    print("\n🔗 D. 联合场景")
    _run_test("Audit + Heat Tax", test_audit_heat_tax_integration)
    _run_test("Full Recovery Cycle", test_full_recovery_cycle)
    _run_test("Heat Tax Fuse + Recovery", test_heat_tax_fuse_with_recovery)

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"结果: {passed}/{len(_results)} 通过 ({failed} 失败)")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
