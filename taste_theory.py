#!/usr/bin/env python3
"""
D5-035: MSS 品味论体系 v1.0 — 决策品质的形式化判据
基于 H416 品味论/K4护城河
"""
import json, os
from dataclasses import dataclass
from datetime import datetime
from typing import List

# ===== 品味论核心公设 =====
TASTE_AXIOMS = {
    "T1": "品味是不可压缩的决策品质 — 无法被规则替代",
    "T2": "品味熵随经验增长而降低 — lim(t→∞) H_taste(t) → 0",
    "T3": "品味决策支付热税低于无品味决策 — γ_taste < γ_random",
    "T4": "品味是K4护城河的核心要素 — 无法被AI或算法复制",
    "T5": "品味具有跨域迁移性 — 一个领域的品味提升会渗透到其他领域",
}

TASTE_LAYERS = {
    "L0_本能": ["生存选择", "基本美感", "对称偏好"],
    "L1_训练": ["专业训练", "刻意练习", "大师临摹"],
    "L2_融合": ["跨域联想", "风格混搭", "创新突破"],
    "L3_通感": ["哲学框架", "元认知", "品味自知"],
    "L4_传承": ["品味教育", "文化遗产", "代际传递"],
}

TASTE_DECAY_RATES = {
    "代码": 0.02,   # 每月2%衰减
    "设计": 0.03,
    "写作": 0.01,
    "音乐": 0.04,
    "决策": 0.05,   # 最快衰减
}

@dataclass
class TasteProfile:
    domain: str
    level: str                    # L0-L4
    entropy: float                # 当前品味熵 [0,1]
    last_practice: str            # 最近练习日期
    masterpieces_studied: int     # 研究过的大师作品数
    cross_domain_connections: int # 跨域联想数

    def decay(self, current_date: str) -> float:
        """计算品味衰减"""
        # 简化：距上次练习天数 × 衰减率
        rate = TASTE_DECAY_RATES.get(self.domain, 0.03)
        try:
            last = datetime.fromisoformat(self.last_practice)
            now = datetime.fromisoformat(current_date)
            days = (now - last).days
        except:
            days = 30
        new_entropy = min(1.0, self.entropy + rate * days / 30)
        return round(new_entropy, 3)

    def is_defensible(self) -> bool:
        """品味是否构成K4护城河"""
        return (self.level in ("L2_融合", "L3_通感", "L4_传承")
                and self.entropy < 0.3
                and self.cross_domain_connections >= 3)


def evaluate_taste_fortress(profiles: List[TasteProfile]) -> dict:
    """评估品味堡垒的综合强度"""
    if not profiles:
        return {"strength": 0, "level": "无品味堡垒"}

    defensive = [p for p in profiles if p.is_defensible()]
    avg_entropy = sum(p.entropy for p in profiles) / len(profiles)

    strength = len(defensive) * 20 + (1 - avg_entropy) * 60
    if strength >= 80:
        level = "K4坚不可摧"
    elif strength >= 50:
        level = "K4稳固"
    elif strength >= 20:
        level = "K4初具规模"
    else:
        level = "K4未形成"

    return {
        "strength": round(strength, 1),
        "level": level,
        "defensive_domains": len(defensive),
        "avg_entropy": round(avg_entropy, 3),
        "total_domains": len(profiles),
        "cross_connections": sum(p.cross_domain_connections for p in profiles),
    }


if __name__ == "__main__":
    # 示例：评估MSS-AI项目的品味堡垒
    profiles = [
        TasteProfile("代码", "L2_融合", 0.15, "2026-05-31", 25, 4),
        TasteProfile("写作", "L3_通感", 0.10, "2026-05-31", 50, 8),
        TasteProfile("设计", "L1_训练", 0.35, "2026-05-20", 10, 2),
        TasteProfile("决策", "L2_融合", 0.20, "2026-05-30", 30, 5),
    ]

    result = evaluate_taste_fortress(profiles)
    print(json.dumps({
        "taste_fortress": result,
        "axioms": TASTE_AXIOMS,
        "layers": TASTE_LAYERS,
        "profiles": [{
            "domain": p.domain,
            "level": p.level,
            "entropy": p.entropy,
            "defensible": p.is_defensible()
        } for p in profiles]
    }, indent=2, ensure_ascii=False))