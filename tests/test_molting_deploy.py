"""
Track C-8: Molting + Deployer coverage
UnitRole: PLAN, EXECUTOR, AUDIT, CONCIERGE, CUSTOM
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.molting import MoltEngine, MoltPackage, MoltStatus, MoltMode
from mssclaw.core.deployer import (
    DeployConfig, Deployer, UnitConfig, PortAllocator,
    DiscoveryService, DiscoveryPacket, UnitRole, UnitState, UnitManager, UnitInfo,
)


# ═══ Molting ═══
class TestMoltPackage:
    def test_create(self):
        mp = MoltPackage()
        assert mp is not None
        assert mp.version == "1.0"

    def test_with_kernel(self):
        mp = MoltPackage(
            version="2.0", source_host="node1",
            kernel={"axioms": ["A1", "A2"]},
            memory={"facts": 10}, runtime={"cpu": 4},
        )
        assert mp.version == "2.0"
        assert mp.kernel == {"axioms": ["A1", "A2"]}

    def test_signature(self):
        mp = MoltPackage(signature="sha256:abc123", checksum="deadbeef")
        assert mp.signature == "sha256:abc123"


class TestMoltEngine:
    def test_create(self):
        me = MoltEngine()
        assert me is not None

    def test_with_paths(self):
        me = MoltEngine(home="/tmp/m_home", storage_dir="/tmp/m_store")
        assert me is not None


class TestMoltStatus:
    def test_values(self):
        for s in MoltStatus:
            assert isinstance(s.value, str)


class TestMoltMode:
    def test_values(self):
        for m in MoltMode:
            assert isinstance(m.value, str)


# ═══ Deployer ═══
class TestUnitConfig:
    def test_create(self):
        uc = UnitConfig(role=UnitRole.EXECUTOR, name="test_unit", command="python test.py")
        assert uc.name == "test_unit"
        assert uc.command == "python test.py"

    def test_defaults(self):
        uc = UnitConfig(role=UnitRole.EXECUTOR, name="w1", command="echo ok")
        assert uc.restart_policy == "always"
        assert uc.max_restarts_per_hour == 10

    def test_with_env(self):
        uc = UnitConfig(role=UnitRole.EXECUTOR, name="w2", command="run", env={"K": "v"}, port=8080)
        assert uc.env == {"K": "v"}
        assert uc.port == 8080


class TestDeployConfig:
    def test_create(self):
        uc = UnitConfig(role=UnitRole.EXECUTOR, name="u1", command="echo 1")
        dc = DeployConfig(units=[uc])
        assert dc.units == [uc]
        assert dc.auto_start is True

    def test_multi_units(self):
        u1 = UnitConfig(role=UnitRole.EXECUTOR, name="a", command="a")
        u2 = UnitConfig(role=UnitRole.EXECUTOR, name="b", command="b", dependencies=["a"])
        dc = DeployConfig(units=[u1, u2], rolling_update=True)
        assert len(dc.units) == 2


class TestPortAllocator:
    def test_create(self):
        pa = PortAllocator()
        assert pa is not None

    def test_allocate(self):
        pa = PortAllocator()
        port = pa.allocate("test_unit")
        assert isinstance(port, int) and port > 0

    def test_allocate_unique(self):
        pa = PortAllocator()
        p1 = pa.allocate("a")
        p2 = pa.allocate("b")
        assert p1 != p2

    def test_release(self):
        pa = PortAllocator()
        port = pa.allocate("x")
        pa.release("x")


class TestDiscoveryPacket:
    def test_create(self):
        dp = DiscoveryPacket(node_id="n1", role="executor", port=5000, health_score=0.95, timestamp=1000.0)
        assert dp.node_id == "n1"
        assert dp.health_score == 0.95


class TestDiscoveryService:
    def test_create(self):
        ds = DiscoveryService(node_id="n1")
        assert ds is not None

    def test_with_port(self):
        ds = DiscoveryService(node_id="n2", bind_port=53999)
        assert ds is not None


class TestDeployer:
    def test_create(self):
        uc = UnitConfig(role=UnitRole.EXECUTOR, name="self_test", command="echo ok")
        dc = DeployConfig(units=[uc], auto_start=False)
        d = Deployer(config=dc)
        assert d is not None


class TestUnitManager:
    def test_create(self):
        pa = PortAllocator()
        uc = UnitConfig(role=UnitRole.EXECUTOR, name="um1", command="echo ok")
        um = UnitManager(config=uc, port_allocator=pa)
        assert um is not None


class TestUnitInfo:
    def test_create_defaults(self):
        uc = UnitConfig(role=UnitRole.EXECUTOR, name="ui1", command="echo ok")
        ui = UnitInfo(config=uc)
        assert ui.config == uc
        assert ui.state == UnitState.STOPPED


class TestUnitRole:
    def test_values(self):
        for r in UnitRole:
            assert isinstance(r.value, str)
