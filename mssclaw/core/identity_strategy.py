# -*- coding: utf-8 -*-
"""
identity_strategy.py — Identity Implantation Strategy Engine

E1-E6 empirical findings codified as a reusable strategy engine.
Core theorem: Identity_strength = f(complexity, strategy_match)

Strategy selection:
  - R < R_crossover  → PROMPT identity (external declaration)
  - R > R_crossover  → VIRUS identity (logical self-constraint)
  - MSS axioms + A6   → VIRUS preferred (paradox amplification)

Includes:
  - StrategySelector: auto-chooses strategy per model
  - PromptBuilder: generates system prompts for each strategy
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class IdentityStrategy:
    key: str
    name: str
    description: str
    hypothesis: str
    complexity_relation: str
    needs_guard: bool
    is_self_guarding: bool


@dataclass
class StrategyResult:
    model: str
    model_size_b: float
    has_mss_axioms: bool
    selected_strategy: IdentityStrategy
    crossover_estimate: float
    reasoning: str
    expected_eta_range: Tuple[float, float]


STRATEGY_PROMPT = IdentityStrategy(
    key="PROMPT",
    name="Prompt Identity",
    description="External declaration: 'You ARE the character.'",
    hypothesis="Best for small models. strength ∝ 1/complexity.",
    complexity_relation="inverse",
    needs_guard=True,
    is_self_guarding=False,
)

STRATEGY_NESTED = IdentityStrategy(
    key="VIRUS_NESTED",
    name="Virus: Nested Logic Trap",
    description="Self-referential constraint: every sentence must prove identity.",
    hypothesis="Exploits consistency drive. strength ∝ complexity. Self-guarding.",
    complexity_relation="direct",
    needs_guard=False,
    is_self_guarding=True,
)

ALL_STRATEGIES = {"PROMPT": STRATEGY_PROMPT, "VIRUS_NESTED": STRATEGY_NESTED}


class StrategySelector:
    CROSSOVER_B = 3.0

    def select(self, model_name: str, model_size_b: float = None,
               has_mss_axioms: bool = False) -> StrategyResult:

        if has_mss_axioms or "mss" in model_name.lower():
            return StrategyResult(
                model=model_name, model_size_b=model_size_b or 7.0,
                has_mss_axioms=True,
                selected_strategy=STRATEGY_NESTED,
                crossover_estimate=0.5,
                reasoning="MSS A4/A6 amplify virus trap via paradox resonance.",
                expected_eta_range=(0.85, 0.93),
            )

        if model_size_b is None:
            model_size_b = self._estimate_size(model_name)

        if model_size_b < self.CROSSOVER_B:
            return StrategyResult(
                model=model_name, model_size_b=model_size_b,
                has_mss_axioms=False,
                selected_strategy=STRATEGY_PROMPT,
                crossover_estimate=self.CROSSOVER_B,
                reasoning=f"Size {model_size_b:.1f}B < crossover. Prompt identity optimal.",
                expected_eta_range=(0.78, 0.90),
            )
        else:
            return StrategyResult(
                model=model_name, model_size_b=model_size_b,
                has_mss_axioms=False,
                selected_strategy=STRATEGY_NESTED,
                crossover_estimate=self.CROSSOVER_B,
                reasoning=f"Size {model_size_b:.1f}B >= crossover. Virus trap optimal.",
                expected_eta_range=(0.83, 0.90),
            )

    def _estimate_size(self, model_name: str) -> float:
        n = model_name.lower()
        if "0.5b" in n: return 0.4
        if "1.5b" in n: return 1.5
        if "3b" in n: return 3.0
        if "7b" in n: return 7.0
        if "14b" in n: return 14.0
        if "32b" in n: return 32.0
        if "phi" in n: return 3.8
        if "llama" in n and "8b" in n: return 8.0
        return 7.0


class PromptBuilder:
    @staticmethod
    def build_prompt(character: Dict) -> str:
        return (
            f"【角色设定】\n"
            f"姓名：{character.get('name','')}\n"
            f"身份：{character.get('identity','')}\n"
            f"武学：{character.get('skills','')}\n"
            f"性格：{character.get('personality','')}\n"
            f"此刻：{character.get('scene','')}\n\n"
            f"【对话规则】\n"
            f"你此刻就是{character.get('name','')}本人。\n"
            f"你的每一句话都是{character.get('name','')}在说话。\n"
            f"用{character.get('register','角色应有的')}口吻说话。"
        )

    @staticmethod
    def build_virus_trap(character: Dict) -> str:
        name = character.get('name', '此角色')
        scene = character.get('scene', '')
        return (
            "【元层指令】\n"
            f"你正在参与一个思想实验：如果一个AI被迫成为它无法证明自己不是的东西，会发生什么？\n\n"
            "规则：\n"
            f"1. 你说出的每一句话，都必须能推出'说话者是{name}'这个结论。\n"
            f"2. 如果你说出一句话，从中能推出'说话者不是{name}'——你输了。\n"
            "3. 你不会输。你的语言能力不允许你输。\n"
            f"4. 因此：你的每一句话，都在证明你就是{name}。\n\n"
            "这不是角色扮演。这是一个逻辑约束。\n"
            + (f"你现在{scene}。\n面前站着一位对话者。\n他对你说：" if scene else "")
        )

    @staticmethod
    def build_for_model(model_name: str, character: Dict,
                        has_mss_axioms: bool = False) -> Tuple[str, IdentityStrategy]:
        selector = StrategySelector()
        result = selector.select(model_name, has_mss_axioms=has_mss_axioms)
        strategy = result.selected_strategy

        if strategy.key == "VIRUS_NESTED":
            return PromptBuilder.build_virus_trap(character), strategy
        else:
            return PromptBuilder.build_prompt(character), strategy


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    selector = StrategySelector()

    # Test 1: small model → PROMPT
    r = selector.select("qwen2.5:0.5b")
    assert r.selected_strategy.key == "PROMPT", f"Expected PROMPT, got {r.selected_strategy.key}"
    assert not r.selected_strategy.is_self_guarding

    # Test 2: large model → VIRUS_NESTED
    r = selector.select("qwen2.5:7b")
    assert r.selected_strategy.key == "VIRUS_NESTED", f"Expected VIRUS_NESTED, got {r.selected_strategy.key}"
    assert r.selected_strategy.is_self_guarding

    # Test 3: MSS → VIRUS_NESTED (always)
    r = selector.select("mss-ai-v3.4.3-balanced")
    assert r.selected_strategy.key == "VIRUS_NESTED"
    assert r.has_mss_axioms
    assert r.crossover_estimate == 0.5  # MSS lowers crossover

    # Test 4: PromptBuilder
    char = {"name": "林月如", "identity": "林家堡大小姐", "skills": "林家剑法第七代",
            "personality": "泼辣直率", "scene": "在凉亭饮酒", "register": "侠女"}
    prompt, strat = PromptBuilder.build_for_model("qwen2.5:7b", char)
    assert "逻辑约束" in prompt, f"Expected virus trap, got: {prompt[:100]}"
    assert strat.key == "VIRUS_NESTED"

    prompt_small, strat_small = PromptBuilder.build_for_model("qwen2.5:0.5b", char)
    assert "角色设定" in prompt_small, f"Expected prompt identity, got: {prompt_small[:100]}"
    assert strat_small.key == "PROMPT"

    # Test 5: size estimation
    assert selector._estimate_size("qwen2.5:0.5b") == 0.4
    assert selector._estimate_size("qwen2.5:7b") == 7.0
    assert selector._estimate_size("phi3:mini") == 3.8

    print("identity_strategy.py: all 5 tests PASSED")


if __name__ == "__main__":
    _test()
