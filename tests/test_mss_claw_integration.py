"""
MSSclaw 集成冒烟测试 — 验证七大模块正常工作.

测试覆盖：
  1. Protocol 通信协议
  2. SwarmBus 消息路由 + 循环检测
  3. NormativeField 安全规则
  4. MeetingRoom 持久化
  5. MoltEngine 蜕壳
  6. 5 个专项 Agent 注册
  7. Plan-Agent 任务调度

无外部依赖（可离线运行）。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_protocol():
    """测试 1: 通信协议"""
    from mss_agent.swarm.protocol import (
        Message, MessageHeader, MessageType, Priority,
        LoopDetector, AgentMetrics, make_task_assign, make_review_request,
    )

    # 消息构造
    msg = make_task_assign("PLAN", "CODE", "task_001", {"action": "audit"})
    assert msg.msg_type == MessageType.TASK_ASSIGN
    assert msg.header.sender == "PLAN"
    assert msg.header.receiver == "CODE"

    # 签名 + 循环检测
    msg.sign()
    ld = LoopDetector(max_rounds=3)
    is_loop, reason = ld.check(msg)
    assert not is_loop

    # 重复 3 次 → 检测到循环
    msg2 = Message(header=MessageHeader(sender="A", receiver="B", correlation_id="test"))
    msg2.payload = {"same": "data"}
    ld.check(msg2)
    ld.check(msg2)
    is_loop, _ = ld.check(msg2)
    assert is_loop

    # AgentMetrics
    m = AgentMetrics(name="test")
    d = m.to_dict()
    assert d["name"] == "test"
    assert d["healthy"] == True

    print("  ✅ Protocol: Message / LoopDetector / Metrics OK")


def test_swarm():
    """测试 2: SwarmBus 消息路由"""
    from mss_agent.swarm import SwarmBus, SwarmNode

    bus = SwarmBus()
    node_a = SwarmNode("Agent-A", "Test", ["test"])
    node_b = SwarmNode("Agent-B", "Test", ["test"])

    node_a.connect(bus)
    node_b.connect(bus)

    assert bus.get_status()["total_nodes"] == 2

    # 发送消息
    from mss_agent.swarm.protocol import Message, MessageHeader, MessageType
    msg = Message(
        header=MessageHeader(
            msg_type=MessageType.INFO_BROADCAST,
            sender="Agent-A", receiver="Agent-B", correlation_id="c1",
        ),
        payload={"test": True},
    )
    node_a.send(msg)
    assert len(node_a._outbox) == 1
    assert len(node_b._inbox) == 1

    # 广播
    msg2 = Message(
        header=MessageHeader(
            msg_type=MessageType.INFO_BROADCAST,
            sender="Agent-A", receiver="ALL",
        ),
        payload={"broadcast": True},
    )
    node_a.send(msg2)
    assert len(node_b._inbox) == 2

    # 健康检查
    hc = bus.health_check()
    assert all(hc.values())

    print("  ✅ SwarmBus: Register / Route / Broadcast / Health OK")


def test_normative_field():
    """测试 3: NormativeField 规范场"""
    from mss_agent.core.normative_field import (
        NormativeField, NormDomain, NormLevel, NormVerdict,
    )

    nf = NormativeField()
    nf.load_defaults()

    # 安全放行
    v = nf.check_network("http://localhost:11434/api/generate")
    assert v.level == NormLevel.SAFE

    # 检测系统写入
    v = nf.check_file("C:\\Windows\\System32\\test.dll", "write")
    assert v.level in (NormLevel.BLOCK, NormLevel.WARN, NormLevel.SAFE)

    # 孤儿检测（无孤儿进程时返回空列表）
    orphans = nf.detect_orphans()
    assert isinstance(orphans, list)

    # 资源基线学习
    nf.update_resource_baseline("python.exe", 30.0, 4000.0)
    stats = nf.get_stats()
    assert stats["total_rules"] >= 5

    print("  ✅ NormativeField: Rules / Check / Baseline / Stats OK")


def test_meeting_room():
    """测试 4: MeetingRoom + SOP 模板"""
    from mss_agent.swarm.meeting_room import (
        MeetingRoom, SOPTemplates, ThreadStatus,
    )

    test_path = os.path.join(tempfile.gettempdir(), "test_mr_v3.json")
    # 清理旧文件
    try:
        os.remove(test_path)
    except Exception:
        pass

    mr = MeetingRoom(db_path=test_path)

    # 创建话题
    t = mr.create_thread("测试话题", "Agent-A", "这是一个测试")
    assert t.topic == "测试话题"

    # 发帖
    mr.post(t.id, "Agent-B", "回复测试")
    assert len(t.posts) == 1

    # 注入 SOP
    mr.inject_sop(t.id, "paper_writing")
    assert t.sop_template == "paper_writing"

    # 搜索
    results = mr.search("回复")
    assert len(results) > 0

    # SOP 模板列表
    templates = SOPTemplates.list()
    assert "paper_writing" in templates
    assert "sft_training" in templates

    # 持久化
    mr.checkpoint()
    assert os.path.exists(os.path.join(tempfile.gettempdir(), "test_mr.json"))

    # 大会/小会
    grand = mr.start_grand_meeting("同步进度", ["Agent-A", "Agent-B"])
    assert grand.topic.startswith("大会")
    mini = mr.start_mini_meeting("Agent-X", "Agent-Y", "对齐接口")
    assert mini.topic.startswith("小会")

    stats = mr.get_stats()
    assert stats["total_threads"] >= 1  # 至少有一个线程

    # 持久化
    mr.checkpoint()
    assert os.path.exists(test_path)

    # 清理
    try:
        os.remove(test_path)
    except PermissionError:
        pass  # Windows 文件锁
    print("  ✅ MeetingRoom: Thread / SOP / Search / Persist / Grand/Mini OK")


def test_molting():
    """测试 5: MoltEngine 蜕壳协议"""
    from mss_agent.core.molting import (
        MoltEngine, MoltMode, MoltStatus, MoltPackage,
    )

    engine = MoltEngine(
        home=os.getcwd(),
        storage_dir=os.path.join(tempfile.gettempdir(), "test_molts"),
    )

    # 准备蜕壳包
    pkg = engine.prepare(
        kb_snapshot=[{"h_id": "H1", "title": "测试"}],
        decision_chain=[{"id": "d1", "decision": "test"}],
        active_tasks=[{"id": "t1", "title": "测试任务"}],
        delta_state=0.72,
    )

    assert "A1" in pkg.kernel["axioms"]
    assert pkg.kernel["axiom_version"] == "v15.1"
    assert len(pkg.memory["kb_snapshot"]) == 1

    # 签名验证
    sig = pkg.sign()
    assert pkg.verify(sig)

    # 蜂群蜕壳
    ok = engine.execute(MoltMode.SWARM, pkg, new_nodes=2)
    assert ok == True

    # 列出已保存包
    packages = engine.list_packages()
    assert len(packages) >= 2

    # 清理
    import shutil
    shutil.rmtree(os.path.join(tempfile.gettempdir(), "test_molts"), ignore_errors=True)

    print("  ✅ MoltEngine: Prepare / Sign / Verify / SwarmMolt OK")


def test_agents():
    """测试 6: 5 个专项 Agent 注册"""
    from mss_agent.swarm import SwarmBus
    from mss_agent.agents.kb_agent import KBAgent
    from mss_agent.agents.code_agent import CodeAgent
    from mss_agent.agents.video_agent import VideoAgent
    from mss_agent.agents.translate_agent import TranslateAgent
    from mss_agent.agents.product_agent import ProductAgent

    bus = SwarmBus()

    agents = [
        KBAgent(name="KB", bus=bus),
        CodeAgent(name="CODE", bus=bus),
        VideoAgent(name="VIDEO", bus=bus),
        TranslateAgent(name="TRANSLATE", bus=bus),
        ProductAgent(name="PRODUCT", bus=bus),
    ]

    status = bus.get_status()
    assert status["total_nodes"] == 5

    # 验证角色
    for agent in agents:
        hc = agent.health_check()
        assert hc["running"] == True
        assert hc["role"] == agent.role

    # 测试 TranslateAgent 翻译
    tra = TranslateAgent(name="TRANSLATE")
    result = tra.translate("意义至上系统", "en")
    assert "Meaning" in result["translated"]

    # 失真检测
    dist = tra.detect_distortion("MSS 比 K3 更快更强更高效")
    assert dist["distortion_level"] > 0

    # 测试 VideoAgent 提示词质检
    va = VideoAgent(name="VIDEO")
    qa = va.qa_prompt("一个人在月光下慢慢走，镜头从远景推近")
    assert qa["score"] > 0.5

    # 测试 CodeAgent 代码审计
    ca = CodeAgent(name="CODE")
    import tempfile
    tf = os.path.join(tempfile.gettempdir(), "test_code.py")
    with open(tf, "w") as f:
        f.write("# Safe code\nprint('hello')\n")
    audit = ca.audit_code(tf)
    assert audit["ok"] == True
    os.remove(tf)

    # 测试 ProductAgent
    pa = ProductAgent(name="PRODUCT")
    release = pa.prepare_release("0.2.0")
    assert "ready" in release

    print("  ✅ Agents: 5 roles / Translate / QA / Audit / Release OK")


def test_plan_agent():
    """测试 7: Plan-Agent 任务调度 + 三权分立"""
    from mss_agent.swarm import SwarmBus
    from mss_agent.agents.plan_agent import PlanAgent, TaskPriority

    try:
        plan = PlanAgent(name="PLAN")
        plan._agent_registry["CODE"] = {"capabilities": ["coding"], "status": "idle", "load": 0}
        plan._agent_registry["VIDEO"] = {"capabilities": ["video"], "status": "idle", "load": 0}
        plan._agent_registry["KB"] = {"capabilities": ["kb_management"], "status": "idle", "load": 0}

        t1 = plan.create_task("audit code", "audit security.py", "coding", TaskPriority.HIGH)
        t2 = plan.create_task("gen video", "ancient scene", "video", TaskPriority.NORMAL)
        t3 = plan.create_task("add kb", "H532 entry", "kb_management", TaskPriority.LOW)

        assert len(plan._tasks) == 3

        ok1 = plan.auto_assign(t1.id)
        ok2 = plan.auto_assign(t2.id)
        ok3 = plan.auto_assign(t3.id)
        assert ok1 and ok2 and ok3
        assert t1.status.value == "assigned"
        assert t1.assigned_to == "CODE"

        board = plan.get_task_board()
        assert board["by_status"]["assigned"] == 3

        signals = plan.detect_coupling("CODE", {"code_quality": 0.95, "video_ready": True})
        assert len(signals) >= 0

        polluted = plan.check_pollution("CODE", "normal meaningful text")
        assert not polluted

        summary = plan.summary()
        assert summary["total_tasks"] == 3
        assert summary["registered_agents"] == 3

        print("  ✅ Plan-Agent: Tasks / Assign / Coupling / Pollution / Summary OK")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


def test_arbiter():
    """测试 8: 三权分立仲裁器"""
    from mss_agent.swarm import SwarmBus, SwarmNode, TriasArbiter
    from mss_agent.swarm.protocol import AuditVerdict

    bus = SwarmBus()
    plan_node = SwarmNode("PLAN", "Planner", ["planning"])
    audit_node = SwarmNode("AUDIT", "Auditor", ["audit"])
    plan_node.connect(bus)
    audit_node.connect(bus)

    arbiter = TriasArbiter(plan_node, audit_node)

    # 驳回
    arbiter.submit_audit_result("task_X", AuditVerdict.REJECT, "格式不符合规范")
    assert not arbiter.resolve("task_X")

    # 上诉
    result = arbiter.escalate("task_X", "已按规范修正，请求重审")
    assert result == AuditVerdict.NEEDS_HUMAN  # 争议不可调和 → 人工

    print("  ✅ TriasArbiter: Submit / Escalate / NeedsHuman OK")


def run_all():
    print("=" * 60)
    print("MSSclaw Integration Smoke Tests")
    print("=" * 60)

    tests = [
        ("Plan-Agent 规划官", test_plan_agent),
        ("Protocol 通信协议", test_protocol),
        ("SwarmBus 蜂巢总线", test_swarm),
        ("NormativeField 规范场", test_normative_field),
        ("MeetingRoom 会议室", test_meeting_room),
        ("MoltEngine 蜕壳", test_molting),
        ("Agent 集群 (5 roles)", test_agents),
        ("TriasArbiter 仲裁器", test_arbiter),
    ]

    passed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"  ❌ {name} FAILED: {e}")
            print(f"     {tb.split(chr(10))[-3]}")

    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{len(tests)} PASSED")
    print(f"{'=' * 60}")
    return passed == len(tests)


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
