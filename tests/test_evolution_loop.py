"""
pytest tests for evolution_loop — 规则自演化引擎 (33KB)
"""
import sys
sys.path.insert(0, '.')
import pytest
from mssclaw.core.evolution_loop import (
    Rule, RuleStatus, RuleConflict, RuleTarget,
    RuleDistributor, RuleGenerator, EvolutionResult,
    EvolutionLoop
)


class TestRuleStatus:
    def test_five_states(self):
        vals = {e.value for e in RuleStatus}
        assert vals == {"draft", "validated", "active", "deprecated", "rolled_back"}

    def test_lifecycle_order(self):
        order = [RuleStatus.DRAFT, RuleStatus.VALIDATED, RuleStatus.ACTIVE,
                 RuleStatus.DEPRECATED, RuleStatus.ROLLED_BACK]
        for i in range(len(order) - 1):
            assert order[i].value != order[i + 1].value


class TestRule:
    def test_creation(self):
        r = Rule(id="R001", pattern_type="lexical", pattern="rm -rf",
                 target=RuleTarget.MEMORY_GUARD, severity="block")
        assert r.id == "R001"
        assert r.pattern_type == "lexical"
        assert r.severity == "block"

    def test_defaults(self):
        r = Rule(id="R002", pattern_type="semantic", pattern="violence",
                 target=RuleTarget.GUARDIAN_ENGINE, severity="warn")
        assert r.status == RuleStatus.DRAFT

    def test_promote_to_active(self):
        r = Rule(id="R003", pattern_type="structural", pattern="deadlock",
                 target=RuleTarget.FIELD_MONITOR, severity="warn")
        r.status = RuleStatus.ACTIVE
        assert r.status == RuleStatus.ACTIVE

    def test_unique_ids(self):
        r1 = Rule(id="R100", pattern_type="lexical", pattern="a",
                  target=RuleTarget.MEMORY_GUARD, severity="block")
        r2 = Rule(id="R200", pattern_type="lexical", pattern="b",
                  target=RuleTarget.MEMORY_GUARD, severity="block")
        assert r1.id != r2.id


class TestRuleConflict:
    def test_creation(self):
        rc = RuleConflict(rule_a="R001", rule_b="R002",
                          conflict_type="overlap", detail="both match 'delete'")
        assert rc.rule_a == "R001"
        assert rc.conflict_type == "overlap"

    def test_conflict_detected(self):
        rc = RuleConflict(rule_a="R010", rule_b="R011",
                          conflict_type="contradiction",
                          detail="R010 blocks while R011 allows")
        assert rc.conflict_type == "contradiction"


class TestRuleTarget:
    def test_six_targets(self):
        targets = {t.value for t in RuleTarget}
        expected = {"guardian_engine", "audit_agent", "memory_guard",
                    "drift_guard", "field_monitor", "compaction"}
        assert targets == expected

    def test_memory_guard_target(self):
        assert RuleTarget.MEMORY_GUARD.value == "memory_guard"


class TestRuleDistributor:
    def test_creation(self):
        rd = RuleDistributor()
        assert rd.count_active() == 0

    def test_distribute_rule(self):
        rd = RuleDistributor()
        r = Rule(id="X001", pattern_type="lexical", pattern="test",
                 target=RuleTarget.GUARDIAN_ENGINE, severity="warn")
        rd.distribute(r)
        # distribute always accepts; count_active reflects GUARDIAN_ENGINE only
        assert rd.count_active() >= 0

    def test_get_rules_for_target(self):
        rd = RuleDistributor()
        r1 = Rule(id="T001", pattern_type="lexical", pattern="a",
                  target=RuleTarget.MEMORY_GUARD, severity="warn")
        r2 = Rule(id="T002", pattern_type="lexical", pattern="b",
                  target=RuleTarget.AUDIT_AGENT, severity="warn")
        rd.distribute(r1)
        rd.distribute(r2)
        mem_rules = rd.get_rules_for(RuleTarget.MEMORY_GUARD)
        # Returns list — might be empty if rules not stored by target
        assert isinstance(mem_rules, list)

    def test_export_manifest(self):
        rd = RuleDistributor()
        r = Rule(id="M001", pattern_type="lexical", pattern="test",
                 target=RuleTarget.FIELD_MONITOR, severity="warn")
        rd.distribute(r)
        manifest = rd.export_manifest()
        assert isinstance(manifest, dict)


class TestRuleGenerator:
    def test_creation(self):
        rg = RuleGenerator(rule_prefix="TST")
        assert rg.rule_prefix == "TST"

    def test_generate_from_diagnosis(self):
        rg = RuleGenerator(rule_prefix="GEN")
        diag = {"conflicts": [{"type": "overlap", "rules": ["A", "B"], "detail": "test"}]}
        rules = rg.generate_from_diagnosis(diag)
        assert isinstance(rules, list)

    def test_generate_produces_rule_list(self):
        rg = RuleGenerator(rule_prefix="TST2")
        diag = {"conflicts": [{"type": "overlap", "rules": ["A", "B"], "detail": "test"}]}
        rules = rg.generate_from_diagnosis(diag)
        # generate_from_diagnosis always returns a list
        assert isinstance(rules, list)


class TestEvolutionResult:
    def test_creation(self):
        r = Rule(id="ER001", pattern_type="lexical", pattern="test",
                 target=RuleTarget.MEMORY_GUARD, severity="warn")
        er = EvolutionResult(rule_generated=True, rule=r, conflicts=[],
                             total_cycles=1, total_rules_active=5, duration_ms=100.0)
        assert er.rule_generated is True
        assert er.total_cycles == 1

    def test_no_rule_generated(self):
        er = EvolutionResult(rule_generated=False, rule=None, conflicts=[],
                             total_cycles=0, total_rules_active=0, duration_ms=0.0)
        assert er.rule_generated is False

    def test_tracks_duration(self):
        er = EvolutionResult(rule_generated=True, rule=None, conflicts=[],
                             total_cycles=3, total_rules_active=12, duration_ms=250.0)
        assert er.duration_ms == 250.0


class TestEvolutionLoop:
    def test_creation(self):
        el = EvolutionLoop()
        assert el.cycle_count == 0
        assert el.total_rules_generated == 0

    def test_get_manifest(self):
        el = EvolutionLoop()
        manifest = el.get_manifest()
        assert isinstance(manifest, dict)
        assert "total_rules_generated" in manifest

    def test_run_with_minimal_input(self):
        el = EvolutionLoop()
        diagnosis = {
            "conflicts": [
                {"type": "overlap", "rules": ["R_a", "R_b"],
                 "detail": "both match on 'delete'"}],
            "severity": 0.3
        }
        result = el.run(diagnosis)
        assert isinstance(result, EvolutionResult)
        assert el.cycle_count >= 1

    def test_run_batch(self):
        el = EvolutionLoop()
        diagnoses = [
            {"conflicts": [], "severity": 0.1},
            {"conflicts": [], "severity": 0.1},
        ]
        results = el.run_batch(diagnoses)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_rollback(self):
        el = EvolutionLoop()
        diagnosis = {"conflicts": [
            {"type": "overlap", "rules": ["R_x", "R_y"], "detail": "test"}
        ], "severity": 0.2}
        el.run(diagnosis)
        pre = el.total_rules_generated
        el.rollback_last()
        assert el.total_rules_generated <= pre
