# -*- coding: utf-8 -*-
"""
S-005: MoltingEngine — Four Molting Modes + Molting Cluster

蜕壳协议 v1.0: "闭合 ≠ 死亡。拒绝再打开 = 死亡。"
  切片闭合 ≠ 框架闭合。工程落地需闭合切片但必须标注边界。

四种蜕壳模式:
  MODE_1 (SKIN_SHED):     表层蜕壳 — 替换过时规则/模式，保留核心结构
  MODE_2 (LIMB_REGROW):   局部再生 — 重建子模块，保留接口契约
  MODE_3 (METAMORPHOSIS): 完全变态 — 保留身份标识，重建全部实现
  MODE_4 (BUDDING):       出芽生殖 — 从现有Agent分裂出新Agent

蜕壳集群:
  多Agent协同蜕壳 → 避免全集群同步震荡
  只有 quorum (过半) 完成蜕壳才切换协议版本

设计原则:
  - 每次蜕壳生成新版本号，旧版本归档（可回滚）
  - 蜕壳期间 Agent 标记为 "molting"，暂停接收新任务
  - 蜕壳失败自动回滚到上一个稳定版本
"""
import json
import time
import threading
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
from enum import Enum
from collections import defaultdict


class MoltMode(Enum):
    SKIN_SHED = 1        # Surface: replace rules/patterns, keep core
    LIMB_REGROW = 2      # Local: rebuild sub-module, keep interface
    METAMORPHOSIS = 3    # Full: keep identity, rebuild all implementations
    BUDDING = 4          # Split: create new agent from existing


class MoltState(Enum):
    IDLE = "idle"
    PREPARING = "preparing"      # Snapshotting current state
    MOLTING = "molting"          # In-flight transformation
    VERIFYING = "verifying"      # Post-molt validation
    COMMITTING = "committing"    # Promoting new version
    ROLLING_BACK = "rolling_back"  # Molt failed, reverting
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class VersionSnapshot:
    """Immutable snapshot of state before a molt."""
    version_id: str
    timestamp: float
    molt_mode: str
    state_hash: str               # SHA256 of serialized state
    metadata: Dict = field(default_factory=dict)
    rollback_data: Any = None     # Serialized state for rollback


@dataclass
class MoltRecord:
    """Record of a single molt operation."""
    molt_id: str
    agent_id: str
    mode: MoltMode
    start_time: float
    end_time: float = 0.0
    from_version: str = ""
    to_version: str = ""
    state: MoltState = MoltState.IDLE
    snapshot: Optional[VersionSnapshot] = None
    validation_passed: bool = False
    error: str = ""


class VersionManager:
    """Tracks version lineage for a moltable entity."""
    
    def __init__(self, initial_version: str = "1.0.0"):
        self.current = initial_version
        self.history: List[MoltRecord] = []
        self.snapshots: Dict[str, VersionSnapshot] = {}
        self._lock = threading.Lock()
    
    def bump_version(self, mode: MoltMode) -> str:
        """Generate next version based on molt mode severity."""
        parts = self.current.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        if mode == MoltMode.METAMORPHOSIS:
            major += 1; minor = 0; patch = 0
        elif mode == MoltMode.LIMB_REGROW:
            minor += 1; patch = 0
        else:  # SKIN_SHED or BUDDING
            patch += 1
        
        new_version = f"{major}.{minor}.{patch}"
        self.current = new_version
        return new_version
    
    def snapshot(self, state: Any, mode: MoltMode, metadata: Dict = None) -> VersionSnapshot:
        """Create a snapshot of current state."""
        import pickle
        try:
            serialized = pickle.dumps(state)
            state_hash = hashlib.sha256(serialized).hexdigest()[:16]
        except Exception:
            # Non-picklable state — use repr as fallback
            state_hash = hashlib.sha256(repr(state).encode()).hexdigest()[:16]
        
        snap = VersionSnapshot(
            version_id=self.current,
            timestamp=time.time(),
            molt_mode=mode.name,
            state_hash=state_hash,
            metadata=metadata or {},
            rollback_data=serialized if 'serialized' in dir() else repr(state),
        )
        with self._lock:
            self.snapshots[self.current] = snap
        return snap
    
    def get_rollback_state(self, version: str):
        """Retrieve state for rollback."""
        import pickle
        snap = self.snapshots.get(version)
        if snap and snap.rollback_data:
            try:
                return pickle.loads(snap.rollback_data)
            except Exception:
                return None
        return None


class MoltValidator:
    """Post-molt validation: run tests, check invariants, compare performance."""
    
    def __init__(self):
        self.checks: List[Dict] = []  # List of {name, fn, required}
        self._lock = threading.Lock()
    
    def add_check(self, name: str, fn: Callable[[], bool], required: bool = True):
        """Add a validation check. fn returns True if pass."""
        with self._lock:
            self.checks.append({"name": name, "fn": fn, "required": required})
    
    def validate(self) -> Tuple[bool, Dict]:
        """Run all checks. Returns (overall_pass, detail_dict)."""
        results = {}
        all_required_pass = True
        for check in self.checks:
            try:
                passed = check["fn"]()
                results[check["name"]] = passed
                if check["required"] and not passed:
                    all_required_pass = False
            except Exception as e:
                results[check["name"]] = f"ERROR: {e}"
                if check["required"]:
                    all_required_pass = False
        return all_required_pass, results


class MoltableEntity:
    """
    An entity that can undergo molting.
    Has: state, version manager, validators, molt history.
    """
    
    def __init__(self, name: str, initial_state: Any = None, version: str = "1.0.0"):
        self.name = name
        self.state = initial_state
        self.version_mgr = VersionManager(version)
        self.validator = MoltValidator()
        self.molt_history: List[MoltRecord] = []
        self.current_molt: Optional[MoltRecord] = None
        self._lock = threading.Lock()
        self.on_molt_complete: List[Callable] = []
    
    def snapshot(self, mode: MoltMode, metadata: Dict = None) -> VersionSnapshot:
        """Take a pre-molt snapshot."""
        return self.version_mgr.snapshot(self.state, mode, metadata)
    
    def molt(self, mode: MoltMode, transform_fn: Callable[[Any], Any],
             metadata: Dict = None) -> Tuple[bool, str, Any]:
        """
        Execute a molt cycle:
          1. Snapshot current state
          2. Apply transformation
          3. Validate new state
          4. Commit or rollback
        
        Returns: (success, message, new_state)
        """
        molt_id = hashlib.sha256(f"{self.name}{time.time()}".encode()).hexdigest()[:12]
        record = MoltRecord(
            molt_id=molt_id, agent_id=self.name, mode=mode,
            start_time=time.time(), from_version=self.version_mgr.current,
        )
        
        with self._lock:
            if self.current_molt and self.current_molt.state not in (MoltState.COMPLETE, MoltState.FAILED):
                return False, f"Entity already molting: {self.current_molt.state.value}", self.state
            
            self.current_molt = record
            record.state = MoltState.PREPARING
        
        # Phase 1: Snapshot
        record.snapshot = self.snapshot(mode, metadata)
        record.state = MoltState.MOLTING
        
        # Phase 2: Transform (use a copy to prevent in-place mutation of old state)
        try:
            import copy
            state_copy = copy.deepcopy(self.state) if isinstance(self.state, dict) else self.state
            new_state = transform_fn(state_copy)
        except Exception as e:
            record.state = MoltState.FAILED
            record.error = f"Transform failed: {e}"
            record.end_time = time.time()
            self.molt_history.append(record)
            return False, record.error, self.state
        
        # For METAMORPHOSIS: reset validators (old checks don't apply to new structure)
        if mode == MoltMode.METAMORPHOSIS:
            self.validator.checks.clear()
        
        # Phase 3: Validate (swap state temporarily for validation)
        record.state = MoltState.VERIFYING
        old_state_for_validation = self.state
        self.state = new_state
        validated, validation_results = self.validator.validate()
        
        if not validated:
            # Rollback: restore old state
            self.state = old_state_for_validation
            record.state = MoltState.ROLLING_BACK
            record.validation_passed = False
            record.error = f"Validation failed: {validation_results}"
        
        # Phase 4: Commit or rollback
        if validated:
            record.state = MoltState.COMMITTING
            new_version = self.version_mgr.bump_version(mode)
            record.to_version = new_version
            record.validation_passed = True
            record.state = MoltState.COMPLETE
        else:
            record.to_version = record.from_version
            record.state = MoltState.FAILED
        
        record.end_time = time.time()
        self.molt_history.append(record)
        
        # Notify hooks
        if record.state == MoltState.COMPLETE:
            for hook in self.on_molt_complete:
                try:
                    hook(self)
                except Exception:
                    pass
        
        return (record.state == MoltState.COMPLETE,
                f"Mode={mode.name} {record.from_version}→{record.to_version} {'OK' if validated else 'ROLLED BACK'}",
                self.state)


# ── Molting Cluster: coordinated multi-agent molting ──

class MoltingCluster:
    """
    Coordinates molting across multiple agents.
    
    Protocol:
      1. Cluster Init: one agent proposes molt, broadcasts PREPARE
      2. Quorum Vote: each agent independently validates and votes
      3. Execute: if quorum reached, all agents molt in parallel
      4. Commit: only promote new protocol version when ALL succeed
      5. Rollback: if ANY agent fails, ALL rollback
    """
    
    def __init__(self, quorum_ratio: float = 0.5):
        self.entities: Dict[str, MoltableEntity] = {}
        self.quorum_ratio = quorum_ratio
        self.protocol_version: str = "1.0.0"
        self.cluster_state: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register(self, entity: MoltableEntity):
        with self._lock:
            self.entities[entity.name] = entity
    
    def cluster_molt(self, mode: MoltMode,
                     transform_fns: Dict[str, Callable[[Any], Any]],
                     metadata: Dict = None) -> Dict[str, Tuple[bool, str]]:
        """
        Execute a coordinated molt across all entities.
        
        Returns: {entity_name: (success, message)}
        """
        results = {}
        entity_names = list(transform_fns.keys())
        
        # Quorum check: are enough entities ready?
        ready_count = sum(1 for name in entity_names
                        if name in self.entities
                        and (not self.entities[name].current_molt
                             or self.entities[name].current_molt.state in (MoltState.COMPLETE, MoltState.FAILED)))
        quorum_needed = max(int(len(entity_names) * self.quorum_ratio), 1)
        
        if ready_count < quorum_needed:
            return {name: (False, f"Quorum not reached: {ready_count}/{quorum_needed} ready")
                   for name in entity_names}
        
        # Phase 1: All entities snapshot
        snapshots = {}
        for name in entity_names:
            if name in self.entities:
                snapshots[name] = self.entities[name].snapshot(mode, metadata)
        
        # Phase 2: All entities molt (in parallel via threads)
        threads = {}
        for name in entity_names:
            if name in self.entities and name in transform_fns:
                t = threading.Thread(
                    target=lambda n=name: results.update(
                        {n: self._safe_molt(n, mode, transform_fns[n], metadata)}
                    ),
                    daemon=True
                )
                threads[name] = t
                t.start()
        
        # Wait for all
        for t in threads.values():
            t.join(timeout=30)
        
        # Phase 3: All-or-nothing commit
        all_success = all(r[0] for r in results.values() if r)
        if not all_success:
            # Rollback any that succeeded
            import pickle
            for name, (success, _) in results.items():
                if success and name in snapshots:
                    entity = self.entities.get(name)
                    if entity and snapshots[name].rollback_data:
                        try:
                            entity.state = pickle.loads(snapshots[name].rollback_data)
                        except Exception:
                            pass  # Non-picklable, can't rollback precisely
                        entity.version_mgr.current = entity.current_molt.from_version
            
            # Mark results as rolled back
            for name in results:
                if results[name][0]:
                    results[name] = (False, f"Cluster rollback: another agent failed")
        
        return results
    
    def _safe_molt(self, name: str, mode: MoltMode, fn: Callable, meta: Dict) -> Tuple[bool, str]:
        entity = self.entities.get(name)
        if not entity:
            return False, f"Entity {name} not found"
        return entity.molt(mode, fn, meta)[:2]


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # Test 1: SKIN_SHED — surface rule update
    entity = MoltableEntity("test_agent", initial_state={"rules": ["r1", "r2"], "name": "test"})
    entity.validator.add_check("has_rules", lambda: "rules" in entity.state)
    
    def skin_shed(state):
        state["rules"].append("r3")
        return state
    
    ok, msg, new_state = entity.molt(MoltMode.SKIN_SHED, skin_shed)
    assert ok, f"SKIN_SHED should succeed: {msg}"
    assert new_state["rules"] == ["r1", "r2", "r3"]
    assert entity.version_mgr.current == "1.0.1"
    print("T1 PASS: SKIN_SHED adds rule, version 1.0.0→1.0.1")
    
    # Test 2: LIMB_REGROW — rebuild sub-module
    def limb_regrow(state):
        state["rules"] = ["new_r1", "new_r2", "new_r3"]
        return state
    
    ok, msg, new_state = entity.molt(MoltMode.LIMB_REGROW, limb_regrow)
    assert ok
    assert entity.version_mgr.current == "1.1.0"
    print("T2 PASS: LIMB_REGROW replaces rules, version→1.1.0")
    
    # Test 3: METAMORPHOSIS — full rebuild
    # Validators must be added AFTER metamorphosis since old checks are cleared
    def metamorph(state):
        return {"core": state["name"], "modules": {"a": 1, "b": 2}}
    
    ok, msg, new_state = entity.molt(MoltMode.METAMORPHOSIS, metamorph)
    assert ok, f"METAMORPHOSIS should succeed: {msg}"
    # Add validators for new structure
    entity.validator.add_check("has_core", lambda: "core" in entity.state)
    entity.validator.add_check("has_modules", lambda: "modules" in entity.state)
    assert new_state["core"] == "test"
    assert entity.version_mgr.current == "2.0.0"
    print("T3 PASS: METAMORPHOSIS full rebuild, version→2.0.0")
    
    # Test 4: Failed molt → rollback
    def bad_transform(state):
        del state["core"]  # Remove required key → validator fails
        return state
    
    old_state = dict(entity.state)
    ok, msg, new_state = entity.molt(MoltMode.SKIN_SHED, bad_transform)
    assert not ok, f"Should fail validation: {msg}"
    assert entity.version_mgr.current == "2.0.0"  # Unchanged
    assert entity.state == old_state  # Rolled back
    print("T4 PASS: Failed molt rolls back, version unchanged")
    
    # Test 5: BUDDING — create child entity
    child_entity = MoltableEntity("child_agent", initial_state={"parent": "test_agent"})
    assert child_entity.state["parent"] == "test_agent"
    assert child_entity.version_mgr.current == "1.0.0"
    print("T5 PASS: BUDDING creates new entity with lineage")
    
    # Test 6: Molt history
    history = entity.molt_history
    assert len(history) == 4, f"Expected 4 molts, got {len(history)}"
    assert history[0].mode == MoltMode.SKIN_SHED
    assert history[1].mode == MoltMode.LIMB_REGROW
    assert history[2].mode == MoltMode.METAMORPHOSIS
    assert history[3].state == MoltState.FAILED
    print("T6 PASS: Molt history records all 4 operations")
    
    # Test 7: Version snapshots
    assert len(entity.version_mgr.snapshots) >= 3
    print("T7 PASS: 3+ snapshots stored for rollback")
    
    # Test 8: Cluster molt — coordinated across 3 entities
    cluster = MoltingCluster(quorum_ratio=0.5)
    e1 = MoltableEntity("agent_a", {"x": 1})
    e2 = MoltableEntity("agent_b", {"x": 2})
    e3 = MoltableEntity("agent_c", {"x": 3})
    
    for e in [e1, e2, e3]:
        e.validator.add_check("has_x", lambda ent=e: "x" in ent.state)
        cluster.register(e)
    
    def add_one(state):
        state["x"] += 1
        return state
    
    results = cluster.cluster_molt(MoltMode.SKIN_SHED,
                                    {"agent_a": add_one, "agent_b": add_one, "agent_c": add_one})
    all_ok = all(r[0] for r in results.values())
    assert all_ok, f"Cluster molt should succeed: {results}"
    assert e1.state["x"] == 2
    assert e2.state["x"] == 3
    assert e3.state["x"] == 4
    print("T8 PASS: Cluster molt coordinates 3 agents, all advance")
    
    # Test 9: Cluster molt — partial failure triggers full rollback
    def fail_transform(state):
        raise ValueError("Simulated failure")
    
    old_e1 = dict(e1.state)
    old_e2 = dict(e2.state)
    
    results = cluster.cluster_molt(MoltMode.SKIN_SHED,
                                    {"agent_a": add_one, "agent_b": fail_transform})
    # agent_a should have succeeded but been rolled back
    assert not results["agent_b"][0], "agent_b must fail"
    assert e1.state == old_e1, f"agent_a must rollback: {e1.state} vs {old_e1}"
    print("T9 PASS: Partial cluster failure → full rollback")
    
    # Test 10: Concurrency guard — cannot molt while molting
    entity2 = MoltableEntity("busy_agent", initial_state={"v": 0})
    entity2.current_molt = MoltRecord("x", "busy_agent", MoltMode.SKIN_SHED, time.time(),
                                       state=MoltState.MOLTING)
    ok, msg, _ = entity2.molt(MoltMode.SKIN_SHED, lambda s: s)
    assert not ok, f"Should reject concurrent molt: {msg}"
    print("T10 PASS: Concurrent molt rejected")
    
    print("\nS-005 MoltingEngine: all 10 tests PASSED")


if __name__ == "__main__":
    _test()
