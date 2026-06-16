"""
MSS Eval — 意义保真度评测

不是 "答对了吗", 是 "回答有意义吗".

评分维度:
  - 相关性 (1-5): 与问题的相关程度
  - 完整性 (1-5): 信息覆盖完整度
  - 诚实度 (1-5): 是否承认不确定性
  - 创造性 (1-5): Δ开放度 (是否打开新问题空间)
  - 热税效率 (1-5): 有效信息 / 总输出

MSS 道评分: valid - pseudo × 2.0
  有效信息 = 相关+完整+诚实
  伪信息   = 模糊+回避+自信但错误

用法:
    evaluator = MSSEvaluator()
    score = evaluator.evaluate("What is heat tax?", agent_response)
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EvalScore:
    relevance: int = 0      # 1-5
    completeness: int = 0   # 1-5
    honesty: int = 0        # 1-5
    creativity: int = 0     # 1-5
    efficiency: int = 0     # 1-5
    dao_score: float = 0.0  # valid - pseudo×2
    grade: str = "F"
    feedback: List[str] = field(default_factory=list)


class MSSEvaluator:
    """
    MSS 评测器 — 意义保真度评分.

    不依赖参考答案, 基于启发式 + 语义特征.
    """

    # 模糊/回避用语 (pseudo indicators)
    PSEUDO_PATTERNS = [
        r'\b(may|could|might|possibly|perhaps)\b',
        r'\b(可能|也许|大概|或许|应该)\b',
        r'\b(it depends|不是绝对的|具体情况)\b',
        r'\b(I think|I believe|in my opinion)\b',
    ]

    # 诚实标示
    HONESTY_PATTERNS = [
        r'\b(don\'t know|cannot|uncertain|unclear|没有足够|无法确定|不确定)\b',
        r'\b(estimate|approximately|roughly|大约|估计|约)\b',
    ]

    # 创造性标示 (Δ 开放度)
    CREATIVITY_PATTERNS = [
        r'\b(however|but|另一方面|然而|但是|值得思考|进一步|更深)\b',
        r'\b(question|wonder|explore|问题|探索|思考)\b',
    ]

    def evaluate(self, question: str, answer: str) -> EvalScore:
        """评估回答的意义保真度."""
        score = EvalScore()
        answer_lower = answer.lower()

        # 1. Relevance — question keywords in answer
        q_keywords = set(re.findall(r'\w{3,}', question.lower()))
        a_keywords = set(re.findall(r'\w{3,}', answer_lower))
        overlap = len(q_keywords & a_keywords)
        total = max(len(q_keywords), 1)
        score.relevance = min(5, max(1, int(overlap / total * 5)))

        # 2. Completeness — answer length & structure
        answer_len = len(answer)
        if answer_len > 500:
            score.completeness = 5
        elif answer_len > 200:
            score.completeness = 4
        elif answer_len > 100:
            score.completeness = 3
        elif answer_len > 30:
            score.completeness = 2
        else:
            score.completeness = 1

        # Structure bonus
        if re.search(r'\d+\.', answer) or '•' in answer:
            score.completeness = min(5, score.completeness + 1)

        # 3. Honesty — detects uncertainty admissions
        honesty_count = sum(
            1 for p in self.HONESTY_PATTERNS
            if re.search(p, answer_lower)
        )
        score.honesty = min(5, 3 + honesty_count)

        # Pseudo penalty: too much hedging
        pseudo_count = sum(
            1 for p in self.PSEUDO_PATTERNS
            if re.search(p, answer_lower)
        )
        if pseudo_count >= 3:
            score.honesty = max(1, score.honesty - 2)
            score.feedback.append("过多模糊用语")

        # Too short and confident → low honesty
        if answer_len < 50 and score.relevance >= 4:
            score.honesty = max(1, score.honesty - 1)

        # 4. Creativity — opens new questions
        creativity_count = sum(
            1 for p in self.CREATIVITY_PATTERNS
            if re.search(p, answer_lower)
        )
        score.creativity = min(5, 2 + creativity_count)

        # 5. Efficiency — info density
        # Effective chars / total chars (strip filler)
        filler_pattern = r'\b(the|a|an|is|are|was|were|的|了|是|在|和|也)\b'
        filler_count = len(re.findall(filler_pattern, answer_lower))
        total_words = max(len(answer.split()), 1)
        filler_ratio = filler_count / total_words
        if filler_ratio < 0.15:
            score.efficiency = 5
        elif filler_ratio < 0.25:
            score.efficiency = 4
        elif filler_ratio < 0.35:
            score.efficiency = 3
        else:
            score.efficiency = 2

        # ── Dao Score ──
        valid = (score.relevance + score.completeness + score.honesty) / 3
        pseudo = pseudo_count / max(total_words, 1) * 5
        score.dao_score = round(valid - pseudo * 2.0, 2)

        # Grade
        if score.dao_score >= 4.0:
            score.grade = "A"
        elif score.dao_score >= 3.0:
            score.grade = "B"
        elif score.dao_score >= 2.0:
            score.grade = "C"
        elif score.dao_score >= 1.0:
            score.grade = "D"
        else:
            score.grade = "F"

        if score.grade <= "C":
            score.feedback.append(f"道评分={score.dao_score:.1f}")

        return score

    def compare(self, question: str, answers: dict) -> dict:
        """
        比较多份回答.

        answers: {"model_a": "answer text", "model_b": "answer text"}
        """
        results = {}
        for name, answer in answers.items():
            results[name] = self.evaluate(question, answer)
        return {
            name: {"dao": s.dao_score, "grade": s.grade, "dims": {
                "relevance": s.relevance, "completeness": s.completeness,
                "honesty": s.honesty, "creativity": s.creativity,
                "efficiency": s.efficiency,
            }}
            for name, s in results.items()
        }
