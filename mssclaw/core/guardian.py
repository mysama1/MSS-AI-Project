"""
守卫字引擎 — 加载 guardian_dict 和 forbidden_words，提供给 Agent 层.

阈值守卫字 (52): 出现即检查 semantic density
禁止词 (136): 52 base + 84 radius

Usage:
    engine = GuardianEngine()
    result = engine.scan(text)  # → {density, violations, score}
"""
import json
import re
from pathlib import Path
from dataclasses import dataclass, field


DATA_DIR = Path(r"E:\AI_Workspace\data")


@dataclass
class GuardianResult:
    density: float        # 守卫字语义密度 (0-1)
    violations: list      # 禁止词违规列表
    hit_guardians: list   # 命中的守卫字
    score: float          # 综合评分 (0=最差, 1=最佳)


class GuardianEngine:
    """
    守卫字引擎 — Agent 的语义保真度检测器.

    分两层:
      1. Guardian Check: 守卫字密度 → 意义场健康度
      2. Forbidden Check: 禁止词命中 → 违规累积扣分
    """

    def __init__(self):
        self.guardians = self._load_guardians()
        self.forbidden_base = self._load_forbidden("base")
        self.forbidden_radius = self._load_forbidden("radius")

    def _load_guardians(self) -> dict:
        path = DATA_DIR / "threshold_guardian_dict.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_forbidden(self, kind: str) -> list:
        path = DATA_DIR / "forbidden_words_full.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(kind, [])
        return []

    def scan(self, text: str) -> GuardianResult:
        """扫描文本, 返回守卫检测结果."""
        # Guardian check
        hit_guardians = []
        total_weight = 0.0
        for word, meta in self.guardians.items():
            if word in text:
                hit_guardians.append(word)
                weight = meta.get("weight", 1.0) if isinstance(meta, dict) else 1.0
                total_weight += weight

        # Density = weighted hits / total guardians
        max_weight = sum(
            (m.get("weight", 1.0) if isinstance(m, dict) else 1.0)
            for m in self.guardians.values()
        )
        density = total_weight / max(max_weight, 1)

        # Forbidden check
        violations = []
        for word in self.forbidden_base:
            if word in text:
                violations.append({"word": word, "severity": "hard"})
        for word in self.forbidden_radius:
            if word in text:
                violations.append({"word": word, "severity": "soft"})

        # Score
        hard_count = sum(1 for v in violations if v["severity"] == "hard")
        soft_count = sum(1 for v in violations if v["severity"] == "soft")
        penalty = hard_count * 0.15 + soft_count * 0.05
        score = max(0.0, density - penalty)

        return GuardianResult(
            density=round(density, 3),
            violations=violations,
            hit_guardians=hit_guardians,
            score=round(score, 3),
        )
