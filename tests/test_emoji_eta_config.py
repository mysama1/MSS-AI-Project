"""
Track C-15: EmojiSemanticScorer + EtaHeatTaxBridge + Config + DeltaCallback coverage
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mssclaw.core.emoji_semantic_scorer import EmojiSemanticScorer, EmojiScore
from mssclaw.core.eta_heat_tax_bridge import EtaHeatTaxMapping, BreachType, EvolutionType
from mssclaw.core.config import MSSConfig
from mssclaw.core.delta_callback import (
    MSSHybridCallback, MSSHybridWrapper, DeltaResult, Tier,
)


class TestEmojiScore:
    def test_create(self):
        es = EmojiScore(
            emoji_density=0.3, semantic_density=0.7,
            class_coherence=0.8, identity_match=0.6,
            arc_presence=0.4, overall=0.56,
        )
        assert es.emoji_density == 0.3
        assert es.semantic_density == 0.7
        assert es.overall == 0.56

    def test_perfect(self):
        es = EmojiScore(
            emoji_density=1.0, semantic_density=1.0,
            class_coherence=1.0, identity_match=1.0,
            arc_presence=1.0, overall=1.0,
        )
        assert es.overall == 1.0


class TestEmojiSemanticScorer:
    def test_create(self):
        ess = EmojiSemanticScorer()
        assert ess is not None


class TestBreachType:
    def test_values(self):
        for b in BreachType:
            assert isinstance(b.value, (int, str))


class TestEvolutionType:
    def test_values(self):
        for e in EvolutionType:
            assert isinstance(e.value, (int, str))


class TestEtaHeatTaxMapping:
    def test_create(self):
        ehtm = EtaHeatTaxMapping()
        assert ehtm.interpretation == ""

    def test_with_params(self):
        ehtm = EtaHeatTaxMapping(
            eta_params={"D1_entity": 0.5, "D2_style": 0.3},
            interpretation="A3 heat tax triggered by D1 decline",
        )
        assert ehtm.interpretation != ""
        assert ehtm.eta_params["D1_entity"] == 0.5


class TestMSSConfig:
    def test_create(self):
        cfg = MSSConfig()
        assert cfg.version == "0.3.9"
        assert cfg.default_model == "qwen2.5:7b"
        assert cfg.ollama_host == "http://localhost:11434"
        assert cfg.agent_temperature == 0.7

    def test_custom(self):
        cfg = MSSConfig(
            version="0.4.0", debug=True,
            default_model="mss-ai-v3.4.3-balanced",
            agent_max_history=50, agent_stream=False,
            log_level="DEBUG", log_max_bytes=5242880,
        )
        assert cfg.version == "0.4.0"
        assert cfg.debug is True
        assert cfg.agent_max_history == 50


class TestMSSHybridCallback:
    def test_create(self):
        hcb = MSSHybridCallback()
        assert hcb is not None

    def test_custom(self):
        hcb = MSSHybridCallback(domain="code", verbose=True, auto_heal=False)
        assert hcb is not None


class TestMSSHybridWrapper:
    def test_create(self):
        hw = MSSHybridWrapper(client={"mock": True})
        assert hw is not None

    def test_custom(self):
        hw = MSSHybridWrapper(client={"mock": True}, domain="research", verbose=True)
        assert hw is not None


class TestDeltaResult:
    def test_create(self):
        dr = DeltaResult(q1_bluffed=False, q2_performed=True, q3_repeated=False, q4_drifted=False, q5_overfed=False)
        assert dr.q1_bluffed is False
        assert dr.q2_performed is True


class TestTier:
    def test_values(self):
        for t in Tier:
            assert isinstance(t.value, str)
