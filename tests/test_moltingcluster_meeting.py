"""
Track C-17: MoltingCluster + MeetingRoom coverage
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.molting_cluster import (
    ClusterCoordinator, ClusterNode, ClusterMoltPlan, NodeState,
    AutoMoltTrigger, MoltSignatureChain, ZeroDowntimeMolter,
    MoltEngine as ClusterMoltEngine, MoltPackage as ClusterMoltPackage, MoltStatus as ClusterMoltStatus,
)
from mssclaw.core.meeting_room import (
    MeetingRoom, MeetingRecord, QueryResult, TTLValue,
)


class TestNodeState:
    def test_values(self):
        for s in NodeState:
            assert isinstance(s.value, str)


class TestClusterNode:
    def test_create(self):
        cn = ClusterNode(node_id="n1", name="alpha")
        assert cn.node_id == "n1"
        assert cn.name == "alpha"
        assert cn.state == NodeState.ONLINE
        assert cn.health_score == 1.0

    def test_offline(self):
        cn = ClusterNode(
            node_id="n2", name="beta", state=NodeState.OFFLINE,
            shell_id="shell_001", molt_count=3, health_score=0.5,
            metadata={"region": "us-east"},
        )
        assert cn.state == NodeState.OFFLINE
        assert cn.molt_count == 3
        assert cn.metadata == {"region": "us-east"}


class TestClusterMoltPlan:
    def test_create(self):
        cmp = ClusterMoltPlan()
        assert cmp.strategy == "rolling"
        assert cmp.batch_size == 1
        assert cmp.status == "pending"

    def test_custom(self):
        cmp = ClusterMoltPlan(
            id="plan_001", target_nodes=["n1", "n2", "n3"],
            strategy="parallel", batch_size=2,
            cool_down_seconds=30.0, new_config={"cpu": 8},
            status="in_progress",
            results={"n1": True, "n2": False},
        )
        assert cmp.target_nodes == ["n1", "n2", "n3"]
        assert cmp.strategy == "parallel"
        assert cmp.results["n1"] is True


class TestMoltSignatureChain:
    def test_create(self):
        msc = MoltSignatureChain(chain_id="chain_001")
        assert msc is not None


class TestClusterMoltPackage:
    def test_create(self):
        mp = ClusterMoltPackage(version="1.0")
        assert mp is not None


class TestClusterMoltEngine:
    def test_create(self):
        me = ClusterMoltEngine()
        assert me is not None


class TestClusterMoltStatus:
    def test_values(self):
        for s in ClusterMoltStatus:
            assert isinstance(s.value, str)


class TestAutoMoltTrigger:
    def test_create(self):
        me = ClusterMoltEngine()
        amt = AutoMoltTrigger(molt_engine=me)
        assert amt is not None

    def test_custom_thresholds(self):
        me = ClusterMoltEngine()
        amt = AutoMoltTrigger(
            molt_engine=me, delta_threshold=0.5, delta_cycles=5,
            heat_l2_ratio=0.8,
        )
        assert amt is not None


class TestClusterCoordinator:
    def test_create(self):
        cc = ClusterCoordinator()
        assert cc is not None

    def test_with_dir(self):
        cc = ClusterCoordinator(cluster_dir="/tmp/cluster")
        assert cc is not None


class TestZeroDowntimeMolter:
    def test_create(self):
        cc = ClusterCoordinator()
        me = ClusterMoltEngine()
        zdm = ZeroDowntimeMolter(cluster=cc, molt_engine=me)
        assert zdm is not None


# ═══ MeetingRoom ═══
class TestMeetingRecord:
    def test_create(self):
        mr = MeetingRecord(meeting_id="m1", topic="sprint planning")
        assert mr.meeting_id == "m1"
        assert mr.topic == "sprint planning"
        assert mr.is_active is True

    def test_with_participants(self):
        mr = MeetingRecord(
            meeting_id="m2", topic="review",
            participants=["alice", "bob"],
            talk_log=[{"speaker": "alice", "text": "start"}],
            decisions=[{"item": "p1", "resolution": "approved"}],
            closed_at=100.0, is_active=False,
        )
        assert len(mr.participants) == 2
        assert len(mr.talk_log) == 1
        assert mr.is_active is False


class TestMeetingRoom:
    def test_create(self):
        mr = MeetingRoom()
        assert mr is not None


class TestQueryResult:
    def test_create(self):
        qr = QueryResult(items=[("key1", "val1"), ("key2", "val2")], total=2)
        assert qr.total == 2
        assert len(qr.items) == 2


class TestTTLValue:
    def test_create(self):
        tv = TTLValue(data={"key": "val"}, expires_at=9999999999.0)
        assert tv.data == {"key": "val"}
        assert tv.expires_at > 0
