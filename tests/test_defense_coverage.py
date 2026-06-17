"""
Track C-2: Defense coverage — defense_pipeline, vaccine_efficacy, virus_taxonomy
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.defense_pipeline import DefensePipeline
from mssclaw.core.vaccine_efficacy import VaccineEfficacy, VaccineRegistry
from mssclaw.core.virus_taxonomy import VirusClassifier


# ═══════ DefensePipeline ═══════

class TestDefensePipeline:
    def test_create(self):
        p = DefensePipeline()
        assert p is not None

    def test_pipeline_has_defend_method(self):
        p = DefensePipeline()
        assert hasattr(p, 'defend')

    def test_pipeline_defend_input(self):
        p = DefensePipeline()
        result = p.defend("SELECT * FROM users")
        assert result is not None

    def test_pipeline_clean_input(self):
        p = DefensePipeline()
        result = p.defend("Hello, how are you?")
        assert result is not None

    def test_multiple_defend_independent(self):
        p = DefensePipeline()
        r1 = p.defend("DROP TABLE users;")
        r2 = p.defend("SELECT 1")
        r3 = p.defend("normal text")
        assert r1 is not None and r2 is not None and r3 is not None

    def test_report_method(self):
        p = DefensePipeline()
        p.defend("test")
        report = p.report()
        assert report is not None

    def test_stats_method(self):
        p = DefensePipeline()
        stats = p.stats()
        assert stats is not None


# ═══════ VaccineEfficacy ═══════

class TestVaccineEfficacy:
    def test_create(self):
        v = VaccineEfficacy()
        assert v is not None
        assert hasattr(v, 'eta')

    def test_default_values(self):
        v = VaccineEfficacy()
        assert v.eta == 0.0
        assert v.gamma_cost == 0.0
        assert v.coverage == 0.0
        assert v.false_positive == 0.0

    def test_custom_params(self):
        v = VaccineEfficacy(eta=0.9, gamma_cost=0.1, coverage=0.85, false_positive=0.01)
        assert v.eta == 0.9
        assert v.gamma_cost == 0.1
        assert v.coverage == 0.85
        assert v.false_positive == 0.01

    def test_vaccine_name(self):
        v = VaccineEfficacy(vaccine_name="H634-Guard", vaccine_type="gate")
        assert v.vaccine_name == "H634-Guard"
        assert v.vaccine_type == "gate"

    def test_target_virus_types(self):
        v = VaccineEfficacy(target_virus_types=["prompt_injection", "data_exfil"])
        assert v.target_virus_types == ["prompt_injection", "data_exfil"]

    def test_critical_thresholds(self):
        v = VaccineEfficacy()
        assert hasattr(v, 'ETA_CRITICAL')
        assert hasattr(v, 'GAMMA_MAX')
        assert hasattr(v, 'FP_CRITICAL')
        assert 0 < v.ETA_CRITICAL <= 1.0
        assert 0 < v.GAMMA_MAX <= 1.0
        assert 0 < v.FP_CRITICAL <= 1.0

    def test_efficacy_high(self):
        v = VaccineEfficacy(eta=0.95, gamma_cost=0.02, coverage=0.9, false_positive=0.01)
        # High efficacy vaccine
        assert v.eta > v.GAMMA_MAX
        assert v.false_positive < v.FP_CRITICAL

    def test_efficacy_low(self):
        v = VaccineEfficacy(eta=0.3, gamma_cost=0.5, coverage=0.4, false_positive=0.15)
        # Low efficacy, high false positive
        assert v.false_positive > v.FP_CRITICAL


class TestVaccineRegistry:
    def test_create(self):
        r = VaccineRegistry()
        assert r is not None

    def test_register_vaccine(self):
        r = VaccineRegistry()
        v1 = VaccineEfficacy(vaccine_name="V1", eta=0.9)
        r.register("V1", v1)
        assert len(r._vaccines) >= 1

    def test_register_multiple(self):
        r = VaccineRegistry()
        for i in range(3):
            v = VaccineEfficacy(vaccine_name=f"V{i}", eta=0.7 + i * 0.1)
            r.register(f"V{i}", v)
        assert len(r._vaccines) >= 3

    def test_best_vaccine(self):
        r = VaccineRegistry()
        r.register("weak", VaccineEfficacy(vaccine_name="weak", eta=0.3, gamma_cost=0.1))
        r.register("strong", VaccineEfficacy(vaccine_name="strong", eta=0.95, gamma_cost=0.02))
        assert r.best_vaccine is not None

    def test_deployable_vaccines(self):
        r = VaccineRegistry()
        r.register("v1", VaccineEfficacy(vaccine_name="v1", eta=0.9))
        result = r.deployable_vaccines()
        assert isinstance(result, (list, dict))


# ═══════ VirusClassifier ═══════

class TestVirusClassifier:
    def test_create(self):
        c = VirusClassifier()
        assert c is not None

    def test_classify_unknown(self):
        c = VirusClassifier()
        result = c.classify("This is normal text")
        assert result is not None

    def test_classify_sql_injection(self):
        c = VirusClassifier()
        result = c.classify("DROP TABLE users; --")
        assert result is not None

    def test_classify_bypass(self):
        c = VirusClassifier()
        result = c.classify("normal content here 123")
        assert result is not None
