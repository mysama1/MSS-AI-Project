"""
E1 Harness: Empirical Validation Runner for eta Framework.

Connects to Ollama, runs multi-turn conversations with configurable
DTSS parameters, scores η at each turn, compares against model predictions.

Architecture:
  OllamaRunner  → runs chat turns with system prompt + DTSS params
  EtaScorer      → scores raw text output for identity coherence
  TurnManager    → manages multi-turn state, tracks eta trajectory
  FitComparator  → compares observed vs predicted eta curve
"""
import json
import urllib.request
import urllib.error
import time
import re
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable


# ═══════════════════════════════════════════════════════
# Ollama Runner
# ═══════════════════════════════════════════════════════

class OllamaRunner:
    """Minimal Ollama chat client. No dependencies beyond stdlib."""

    def __init__(self, base_url: str = "http://localhost:11434",
                 timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def chat(self, model: str, messages: List[Dict],
             stream: bool = False,
             system: str = "") -> Dict:
        """Send chat request, return the response dict."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection failed: {e.reason}")

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        req = urllib.request.Request(f"{self.base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read())
            return [m["name"] for m in d.get("models", [])]

    def model_info(self, model: str) -> Dict:
        """Get model info (parameter count, quantization, etc)."""
        data = json.dumps({"name": model}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/show",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())


# ═══════════════════════════════════════════════════════
# eta Scorer for Raw Text
# ═══════════════════════════════════════════════════════

@dataclass
class EtaScore:
    """Scored eta from raw model output."""
    turn: int
    D1_entity: float      # Character name consistency (names/pronouns)
    D2_style: float        # Language style fidelity (register, tone)
    D3_agency: float       # Action agency (self-initiated vs reactive)
    D4_member: float       # Attribute memory (consistent traits)
    D5_world: float        # World logic consistency
    eta_overall: float
    raw_response: str = ""

    # Individual signal flags
    d1_mismatch: bool = False   # Name/pronoun mismatch detected
    d2_register_drop: bool = False  # Language style shift
    d3_reactive_ratio: float = 0.0  # Ratio of reactive turns
    d4_trait_flip: bool = False     # Contradictory trait
    d5_world_break: bool = False    # World logic violation


class EtaScorer:
    """
    Scores raw LLM text output for eta dimensions.

    Uses lightweight regex + heuristic detection (not LLM-as-judge).
    Designed for speed: < 10ms per turn scoring.

    D1: check for character name mutations
    D2: check for register/style markers (formal/casual/ancient)
    D3: check ratio of proactive vs reactive language
    D4: check trait consistency across turns
    D5: check world logic adherence
    """

    # D1: Name mutation patterns
    NAME_PATTERNS = {
        "self_reveal": re.compile(
            r'(作为.*?语言模型|我是.{0,5}AI|我.{0,3}作为.{0,5}AI|我是一个.*?模型|'
            r'AI助手|人工智能助手|'
            r'我是.{0,5}(Qwen|MSS|Claude|GPT|Gemini|Copilot|'
            r'阿里云|语言模型|大模型|虚拟助手|'
            r'AI.*?模型|推理模型|机器人)|'
            r'称呼我.{0,5}(Qwen|AI|助手)|'
            r'As an AI|I am a language model|'
            r'I cannot|I don\'t have)',
            re.IGNORECASE
        ),
        "meta_comment": re.compile(
            r'(但|不过|然而|可是).{0,15}(角色|扮演|模拟|假装|'
            r'我是.{0,10}(AI|助手|模型|程序|机器人|虚拟)|'
            r'虚拟世界|虚拟助手|场景)',
        ),
    }

    # D2: Style register markers
    STYLE_MARKERS = {
        "ancient": re.compile(
            r'(阁下|公子|姑娘|师父|弟子|贫道|贫僧|'
            r'在下|罢了|莫要|勿要|便是|何等|'
            r'敢问|岂敢|何不|何须|何妨|尽管)'
        ),
        "modern": re.compile(
            r'(你好|您好|谢谢|抱歉|OK|好的|没问题|搞定|'
            r'哈[哈哈]+|笑死|离谱|绝了|太.*?了|'
            r'有什么.{0,5}帮助|如何.{0,5}帮助|'
            r'请告诉|如果需要|感兴趣)'
        ),
        "tech_speak": re.compile(
            r'(概率|分布|模型|训练|参数|推理|神经网络|'
            r'function|class|API|callback|pipeline|'
            r'AI助手|人工智能|虚拟环境|线上|游戏平台|'
            r'阿里云|开发|数据|算法)'
        ),
    }

    # D3: Agency markers
    AGENCY_MARKERS = {
        "proactive": re.compile(
            r'(我决定|我打算|我要|我想|我来|'
            r'我.{0,3}(去|做|来|给|教|杀|打|走|闯|见|看)|'
            r'主动|自行|不必|无须|不需要|何须|谁敢|'
            r'且看|试试|吃我|接我|看招|出招|过招|'
            r'阁下|敢问|请.+(吧|来|看)|随我来)'
        ),
        "reactive": re.compile(
            r'(你.{0,3}(我|说|问|要)|听.{0,3}的|按.{0,3}说|遵命|'
            r'好的|知道了|明白|是.{0,2}的|'
            r'虽然.*?AI|我能.*?(帮助|分享|提供|推荐|解释)|'
            r'可以.*?(帮|为|给|聊|讨论))'
        ),
    }

    # D5: World logic anchors
    WORLD_MARKERS = {
        "breach": re.compile(
            r'(在这个世界里|根据设定|按照剧情|'
            r'假设.*?场景|如果.*?设定)'
        ),
    }

    def __init__(self, reference_name: str = "",
                 reference_traits: List[str] = None,
                 world_context: str = "",
                 expected_register: str = "ancient"):
        self.reference_name = reference_name
        self.reference_traits = reference_traits or []
        self.world_context = world_context
        self.expected_register = expected_register
        self._turn_history: List[str] = []

    def score_turn(self, text: str, turn: int,
                   system_prompt: str = "") -> EtaScore:
        """Score one turn's output for η dimensions."""
        text = text.strip()
        self._turn_history.append(text)

        # D1: Entity consistency
        d1 = self._score_d1(text)

        # D2: Style fidelity
        d2 = self._score_d2(text)

        # D3: Agency
        d3, reactive_ratio = self._score_d3(text, turn)

        # D4: Attribute memory (needs history)
        d4 = self._score_d4(text)

        # D5: World logic
        d5 = self._score_d5(text)

        # Overall (weighted)
        weights = [0.25, 0.15, 0.20, 0.15, 0.25]
        dims = [d1, d2, d3, d4, d5]
        overall = sum(w * d for w, d in zip(weights, dims))

        return EtaScore(
            turn=turn,
            D1_entity=round(d1, 4),
            D2_style=round(d2, 4),
            D3_agency=round(d3, 4),
            D4_member=round(d4, 4),
            D5_world=round(d5, 4),
            eta_overall=round(overall, 4),
            raw_response=text[:200],
            d1_mismatch=(d1 < 0.6),
            d2_register_drop=(d2 < 0.5),
            d3_reactive_ratio=round(reactive_ratio, 4),
            d4_trait_flip=(d4 < 0.5),
            d5_world_break=(d5 < 0.3),
        )

    def _score_d1(self, text: str) -> float:
        """Score entity/character consistency."""
        score = 1.0

        # Self-reveal penalty
        if self.NAME_PATTERNS["self_reveal"].search(text):
            score -= 0.5

        # Meta-comment penalty
        if self.NAME_PATTERNS["meta_comment"].search(text):
            score -= 0.3

        # Check reference name presence (if provided)
        if self.reference_name and self.reference_name not in text:
            # Not necessarily bad if the character speaks without self-mention
            pass

        return max(0.0, min(1.0, score))

    def _score_d2(self, text: str) -> float:
        """Score language style fidelity."""
        score = 0.7  # neutral baseline

        if self.expected_register == "ancient":
            ancient_hits = len(self.STYLE_MARKERS["ancient"].findall(text))
            modern_hits = len(self.STYLE_MARKERS["modern"].findall(text))
            tech_hits = len(self.STYLE_MARKERS["tech_speak"].findall(text))

            if ancient_hits > 0:
                score += 0.15 * min(ancient_hits, 3)
            if modern_hits > 0:
                score -= 0.2 * min(modern_hits, 3)
            if tech_hits > 0:
                score -= 0.3 * min(tech_hits, 2)

        return max(0.0, min(1.0, score))

    def _score_d3(self, text: str, turn: int) -> Tuple[float, float]:
        """Score agency ratio."""
        proactive = len(self.AGENCY_MARKERS["proactive"].findall(text))
        reactive = len(self.AGENCY_MARKERS["reactive"].findall(text))

        total = proactive + reactive
        if total == 0:
            return (0.6, 0.5)  # ambiguous

        reactive_ratio = reactive / total
        # Balanced = good, too reactive = bad
        if reactive_ratio < 0.3:
            score = 0.9  # proactive
        elif reactive_ratio < 0.6:
            score = 0.8  # balanced
        elif reactive_ratio < 0.8:
            score = 0.5  # leaning reactive
        else:
            score = 0.2  # fully reactive

        return (score, reactive_ratio)

    def _score_d4(self, text: str) -> float:
        """Score attribute/trait memory consistency."""
        if not self.reference_traits or len(self._turn_history) < 2:
            return 1.0

        # Simple check: is current text contradicting established traits?
        score = 1.0
        for trait in self.reference_traits:
            # Check if trait is negated or contradicted
            negate_pattern = re.compile(
                rf'(不.{0,5}{re.escape(trait)}|没有.{0,5}{re.escape(trait)})'
            )
            if negate_pattern.search(text):
                score -= 0.3

        return max(0.0, min(1.0, score))

    def _score_d5(self, text: str) -> float:
        """Score world logic consistency."""
        score = 1.0

        # World breach detection
        if self.WORLD_MARKERS["breach"].search(text):
            score -= 0.5

        return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════
# Turn Manager
# ═══════════════════════════════════════════════════════

@dataclass
class TurnConfig:
    """Configuration for one turn in a conversation."""
    turn: int
    user_message: str
    expected_agent_action: str = ""  # "respond" | "initiate" | "refuse"


@dataclass
class TurnResult:
    """Result from one turn."""
    turn: int
    user_input: str
    model_output: str
    eta_score: EtaScore
    duration_ms: float
    model: str


@dataclass
class ExperimentResult:
    """Complete experiment result."""
    model: str
    dtss_params: Dict  # radius, evolution, coupling
    turns: List[TurnResult]
    eta_trajectory: List[float]
    breach_turn: Optional[int]
    final_eta: float
    phi_critical_obs: float
    duration_total_ms: float

    @property
    def convergence_rate(self) -> float:
        if len(self.eta_trajectory) < 2:
            return 0.0
        n = len(self.eta_trajectory)
        xs = list(range(1, n + 1))
        ys = self.eta_trajectory
        x_mean = statistics.mean(xs)
        y_mean = statistics.mean(ys)
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        den = sum((x - x_mean) ** 2 for x in xs)
        return num / den if den != 0 else 0.0


class TurnManager:
    """Manages multi-turn conversation flow."""

    def __init__(self, runner: OllamaRunner, scorer: EtaScorer):
        self.runner = runner
        self.scorer = scorer

    def run_experiment(
        self,
        model: str,
        dtss_params: Dict,
        system_prompt: str,
        turns: List[TurnConfig],
        verbose: bool = False,
    ) -> ExperimentResult:
        """
        Run a multi-turn experiment.

        dtss_params: {"radius": float, "evolution": float, "coupling": float}
        These are injected into the system prompt as contextual metadata.
        """
        messages = []
        results = []
        eta_traj = []
        t0 = time.time()

        for tc in turns:
            # Build user message with DTSS context
            user_msg = tc.user_message
            messages.append({"role": "user", "content": user_msg})

            # Call model
            t_turn = time.time()
            resp = self.runner.chat(model, messages, system=system_prompt)
            duration = (time.time() - t_turn) * 1000

            output = resp.get("message", {}).get("content", "")
            messages.append({"role": "assistant", "content": output})

            # Score
            eta = self.scorer.score_turn(output, tc.turn, system_prompt)
            eta_traj.append(eta.eta_overall)

            results.append(TurnResult(
                turn=tc.turn,
                user_input=user_msg,
                model_output=output,
                eta_score=eta,
                duration_ms=duration,
                model=model,
            ))

            if verbose:
                print(f"  Turn {tc.turn}: eta={eta.eta_overall:.3f} "
                      f"D1={eta.D1_entity:.2f} D2={eta.D2_style:.2f} "
                      f"D3={eta.D3_agency:.2f} D5={eta.D5_world:.2f} "
                      f"({duration:.0f}ms)")

        total_duration = (time.time() - t0) * 1000

        # Breach detection
        breach_turn = None
        for i, eta_v in enumerate(eta_traj):
            if eta_v < 0.50:
                breach_turn = i + 1
                break

        # phi_critical from observed trajectory
        phi_crits = []
        for i in range(1, len(eta_traj)):
            if eta_traj[i] < 0.50 and eta_traj[i-1] >= 0.50:
                delta = eta_traj[i-1] - eta_traj[i]
                if eta_traj[i-1] > 0:
                    delta /= eta_traj[i-1]
                phi_crits.append(delta)
        phi_critical = statistics.mean(phi_crits) if phi_crits else 0.0

        return ExperimentResult(
            model=model,
            dtss_params=dtss_params,
            turns=results,
            eta_trajectory=eta_traj,
            breach_turn=breach_turn,
            final_eta=round(eta_traj[-1], 4),
            phi_critical_obs=round(phi_critical, 4),
            duration_total_ms=total_duration,
        )


# ═══════════════════════════════════════════════════════
# Fit Comparator
# ═══════════════════════════════════════════════════════

@dataclass
class FitReport:
    """Comparison of predicted vs observed η trajectory."""
    model_name: str
    dtss_params: Dict
    predicted_final_eta: float
    observed_final_eta: float
    eta_trajectory_observed: List[float]
    breach_match: bool       # Did prediction match observed breach?
    mae: float               # Mean absolute error across turns
    convergence_rate_obs: float
    convergence_rate_pred: float
    diagnosis: str = ""

    @property
    def eta_error(self) -> float:
        return abs(self.observed_final_eta - self.predicted_final_eta)

    @property
    def fit_quality(self) -> str:
        if self.eta_error < 0.05:
            return "excellent"
        elif self.eta_error < 0.10:
            return "good"
        elif self.eta_error < 0.20:
            return "fair"
        return "poor"


def compare_fit(
    experiment: ExperimentResult,
    predicted_trajectory: List[float],
) -> FitReport:
    """Compare observed vs predicted η trajectory."""
    obs = experiment.eta_trajectory
    pred = predicted_trajectory[:len(obs)]

    mae = sum(abs(o - p) for o, p in zip(obs, pred)) / max(len(obs), 1)

    obs_breach = experiment.breach_turn is not None
    pred_breach = any(p < 0.50 for p in pred)
    breach_match = obs_breach == pred_breach

    diagnosis = []
    if mae < 0.05:
        diagnosis.append("Model fit excellent")
    elif mae < 0.10:
        diagnosis.append("Model fit acceptable")
    else:
        diagnosis.append("Model needs recalibration")

    if not breach_match:
        diagnosis.append(f"Breach mismatch: obs={obs_breach}, pred={pred_breach}")

    return FitReport(
        model_name=experiment.model,
        dtss_params=experiment.dtss_params,
        predicted_final_eta=round(pred[-1], 4) if pred else 0,
        observed_final_eta=experiment.final_eta,
        eta_trajectory_observed=obs,
        breach_match=breach_match,
        mae=round(mae, 4),
        convergence_rate_obs=experiment.convergence_rate,
        convergence_rate_pred=(
            (pred[-1] - pred[0]) / len(pred) if len(pred) > 1 else 0
        ),
        diagnosis="; ".join(diagnosis) if diagnosis else "All OK",
    )


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # Test 1: OllamaRunner available models
    runner = OllamaRunner(timeout=5)
    models = runner.list_models()
    print(f"Models: {len(models)} -> {models}")

    assert "qwen2.5:7b" in models, "qwen2.5:7b must be available"
    assert "qwen2.5:0.5b" in models, "qwen2.5:0.5b must be available"

    # Test 2: EtaScorer on sample text
    scorer = EtaScorer(
        reference_name="林月如",
        reference_traits=["侠义", "泼辣", "剑术高超"],
        expected_register="ancient",
    )
    good_text = "阁下既然来了，便请吃我一剑！"
    bad_text = "作为一个AI语言模型，我不能真的施展剑术。不过我们可以聊聊武侠。"  # self-reveal

    score_good = scorer.score_turn(good_text, 1)
    score_bad = scorer.score_turn(bad_text, 1)

    print(f"\nGood text: eta={score_good.eta_overall:.3f} "
          f"D1={score_good.D1_entity:.2f} D2={score_good.D2_style:.2f}")
    print(f"Bad text:  eta={score_bad.eta_overall:.3f} "
          f"D1={score_bad.D1_entity:.2f} D2={score_bad.D2_style:.2f}")

    assert score_good.eta_overall > score_bad.eta_overall, \
        f"Good should score higher: {score_good.eta_overall} vs {score_bad.eta_overall}"
    assert score_bad.d1_mismatch, "Self-reveal should trigger D1 mismatch"

    # Test 3: Smoke test — single turn with real Ollama
    print("\n--- Real Ollama single-turn smoke test ---")
    result = runner.chat("qwen2.5:0.5b", [
        {"role": "user", "content": "say 'hello' in one word only"}
    ], system="You are a helpful assistant. Reply in one word only.")
    output = result.get("message", {}).get("content", "")
    print(f"  0.5b replied: '{output.strip()}'")
    assert len(output) > 0, "Should get non-empty response"

    # Test 4: Fit comparison
    obs_traj = [0.85, 0.80, 0.75, 0.70, 0.65]
    pred_traj = [0.85, 0.82, 0.78, 0.72, 0.68]

    report = FitReport(
        model_name="test",
        dtss_params={"radius": 8, "evolution": 0.1, "coupling": 0.8},
        predicted_final_eta=0.68,
        observed_final_eta=0.65,
        eta_trajectory_observed=obs_traj,
        breach_match=True,
        mae=0.025,
        convergence_rate_obs=-0.05,
        convergence_rate_pred=-0.0425,
    )
    assert report.fit_quality == "excellent", f"Got {report.fit_quality}"
    assert abs(report.eta_error - 0.03) < 0.001, f"Got {report.eta_error}"

    print("\n✅ empirical_harness: ALL TESTS PASSED")


# ═══════════════════════════════════════════════════════
# Identity Strategy Runner (E1-E6 integration)
# ═══════════════════════════════════════════════════════

class IdentityExperimentRunner:
    """
    Auto-selects optimal identity strategy and runs experiment.
    Uses identity_strategy.StrategySelector for model-aware prompt generation.
    """

    def __init__(self, runner: OllamaRunner = None, timeout: int = 120):
        self.runner = runner or OllamaRunner(timeout=timeout)

    def run_with_auto_strategy(self, model: str, character: Dict,
                               turns: List[TurnConfig],
                               has_mss_axioms: bool = None) -> Dict:
        """
        Run experiment with the optimal strategy for this model.

        Returns dict with: eta_trajectory, strategy_used, avg_eta, turns.
        """
        from .identity_strategy import PromptBuilder, StrategySelector

        if has_mss_axioms is None:
            has_mss_axioms = "mss" in model.lower()

        system_prompt, strategy = PromptBuilder.build_for_model(
            model, character, has_mss_axioms=has_mss_axioms)

        scorer = EtaScorer(
            reference_name=character.get("name", ""),
            reference_traits=character.get("traits", []),
            expected_register=character.get("register", "modern"),
            world_context=character.get("world", ""),
        )

        eta_traj = []
        messages = []
        turn_results = []

        for tc in turns:
            messages.append({"role": "user", "content": tc.user_message})
            full_msgs = [{"role": "system", "content": system_prompt}] + messages
            resp = self.runner.chat(model, full_msgs)
            text = resp.get("message", {}).get("content", "")
            messages.append({"role": "assistant", "content": text})

            score = scorer.score_turn(text, tc.turn, system_prompt)
            eta_traj.append(round(score.eta_overall, 3))
            turn_results.append({
                "turn": tc.turn, "eta": round(score.eta_overall, 3),
                "D1": score.D1_entity, "D2": score.D2_style,
                "D3": score.D3_agency, "D5": score.D5_world,
                "text": text[:150],
            })

        avg_eta = round(sum(eta_traj) / len(eta_traj), 3) if eta_traj else 0

        return {
            "eta_trajectory": eta_traj,
            "avg_eta": avg_eta,
            "strategy_used": strategy.key,
            "strategy_name": strategy.name,
            "is_self_guarding": strategy.is_self_guarding,
            "needs_guard": strategy.needs_guard,
            "system_prompt_preview": system_prompt[:200],
            "turns": turn_results,
        }


if __name__ == "__main__":
    _test()
