"""
Track C-13: Domain (SwarmBus) + DigestEngine coverage
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.domain import (
    SwarmBus, Message, MessageHeader, MessageType, Priority,
    CrossDomainRouter, CrossDomainRecord, CrossDomainChannel,
)
from mssclaw.core.digest_engine import (
    DigestEngine, DigestOption, DigestReport, DigestMode,
)


class TestMessageHeader:
    def test_create_defaults(self):
        mh = MessageHeader()
        assert mh.msg_type == MessageType.INFO_BROADCAST
        assert mh.priority == Priority.NORMAL
        assert mh.ttl == 0

    def test_custom(self):
        mh = MessageHeader(
            msg_type=MessageType.TASK_ASSIGN,
            sender="agent_a", receiver="agent_b",
            priority=Priority.HIGH, round=1, max_rounds=3,
            ttl=5, correlation_id="corr-001",
        )
        assert mh.sender == "agent_a"
        assert mh.priority == Priority.HIGH
        assert mh.correlation_id == "corr-001"


class TestMessage:
    def test_create(self):
        m = Message(payload={"text": "hello"})
        assert m.payload == {"text": "hello"}

    def test_with_header(self):
        mh = MessageHeader(sender="a", receiver="b")
        m = Message(header=mh, payload={"op": "test"}, content_signature="sig123")
        assert m.content_signature == "sig123"


class TestMessageType:
    def test_values(self):
        for mt in MessageType:
            assert isinstance(mt.value, str)


class TestPriority:
    def test_values(self):
        for p in Priority:
            assert isinstance(p.value, str)


class TestSwarmBus:
    def test_create(self):
        sb = SwarmBus()
        assert sb is not None

    def test_with_rounds(self):
        sb = SwarmBus(loop_max_rounds=10)
        assert sb is not None


class TestCrossDomainRecord:
    def test_create(self):
        cdr = CrossDomainRecord(
            id="r1", channel="work", direction="outbound",
            sender="a", receiver="b", payload_summary="test msg",
            payload_size=100, timestamp="today", allowed=True,
        )
        assert cdr.id == "r1"
        assert cdr.allowed is True

    def test_denied(self):
        cdr = CrossDomainRecord(
            id="r2", channel="personal", direction="inbound",
            sender="x", receiver="y", payload_summary="bad",
            payload_size=50, timestamp="now", allowed=False,
            deny_reason="policy violation",
        )
        assert cdr.deny_reason == "policy violation"


class TestCrossDomainRouter:
    def test_create(self):
        wb = SwarmBus()
        pb = SwarmBus()
        cdr = CrossDomainRouter(work_bus=wb, personal_bus=pb)
        assert cdr is not None


class TestCrossDomainChannel:
    def test_values(self):
        for c in CrossDomainChannel:
            assert isinstance(c.value, str)


# ═══ DigestEngine ═══
class TestDigestOption:
    def test_create(self):
        do = DigestOption(index=0, type="compaction", name="gzip", description="compress logs")
        assert do.index == 0
        assert do.type == "compaction"
        assert do.name == "gzip"
        assert do.compatible is True

    def test_with_conflicts(self):
        do = DigestOption(
            index=1, type="filter", name="drop_noise",
            description="remove noise", compatible=False,
            conflict_with=["keep_all"], suggestion="use sparingly",
        )
        assert do.conflict_with == ["keep_all"]
        assert do.compatible is False


class TestDigestReport:
    def test_create(self):
        dr = DigestReport()
        assert dr.total_options == 0
        assert dr.auto_applied == 0

    def test_with_values(self):
        dr = DigestReport(total_options=5, auto_applied=3, conflicts=1, skipped=1, details=["gzip applied", "noise skipped"])
        assert dr.auto_applied == 3
        assert len(dr.details) == 2


class TestDigestMode:
    def test_values(self):
        for dm in DigestMode:
            assert isinstance(dm.value, str)
