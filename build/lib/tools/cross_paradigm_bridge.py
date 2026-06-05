#!/usr/bin/env python3
"""
D5-047: MSS 跨范式翻译桥 v1.0
双向翻译 MSS术语 ↔ K3术语，支持降维/升维操作
基于 H196 跨范式沟通协议
"""
import json, os
from typing import Dict, List, Tuple
from enum import Enum

class Direction(Enum):
    MSS_TO_K3 = "mss_to_k3"  # 降维：MSS概念 → K3语言
    K3_TO_MSS = "k3_to_mss"  # 升维：K3概念 → MSS框架

# ===== MSS ↔ K3 术语映射表 =====
TERM_MAP: Dict[str, Tuple[str, str, str]] = {
    # (MSS术语, K3等价物, 翻译风险级别)
    # MSS → K3
    "热税": ("thermal tax", "computational cost / entropy production", "LOW"),
    "意义场": ("meaning field", "semantic space / embedding space", "MEDIUM"),
    "感知壳": ("perception shell", "model architecture / observation boundary", "MEDIUM"),
    "意义投影": ("meaning projection", "representation learning / encoding", "LOW"),
    "意义密度": ("meaning density", "information density / signal-to-noise ratio", "LOW"),
    "热税系数γ": ("gamma coefficient", "complexity overhead factor", "LOW"),
    "意义黑洞": ("meaning black hole", "unsustainable business model / collapsed narrative", "HIGH"),
    "公理A1": ("Axiom A1", "First principle: meaning precedes existence", "MEDIUM"),
    "公理A2": ("Axiom A2", "Observer-dependent reality / perspectivism", "LOW"),
    "公理A3": ("Axiom A3", "Second law of thermodynamics (generalized)", "LOW"),
    "公理A4": ("Axiom A4", "Intrinsic randomness / quantum uncertainty", "LOW"),
    "公理A5": ("Axiom A5", "Self-organizing criticality / emergence", "MEDIUM"),
    "公理A6": ("Axiom A6", "Gödelian incompleteness / paradox resolution", "HIGH"),
    "逻辑功": ("logical work W", "computational work / useful output", "LOW"),
    "意义熵": ("meaning entropy S_T", "Shannon entropy / algorithmic complexity", "LOW"),
    "升华效率η_asc": ("ascension efficiency", "training efficiency / convergence rate", "LOW"),
    "意义切片": ("meaning slice", "data sample / observation", "LOW"),
    "跨范式协议": ("cross-paradigm protocol", "interdisciplinary communication framework", "MEDIUM"),
    "逻辑病毒": ("logic virus", "logical fallacy / reasoning error", "LOW"),
    "认知污染": ("cognitive contamination", "confirmation bias / echo chamber effect", "LOW"),

    # K3 → MSS
    "technical debt": ("技术债", "accumulated thermal tax (A3 violation)", "LOW"),
    "overfitting": ("过拟合", "excessive meaning slicing without thermal tax payment (A2+A3)", "MEDIUM"),
    "hallucination": ("幻觉", "meaning projection with zero thermal tax cost (A3 violation)", "LOW"),
    "scaling law": ("规模律", "meaning-to-heat-tax conversion function dQ/dn (A3)", "MEDIUM"),
    "emergent behavior": ("涌现行为", "L3 collective meaning self-organization (A5)", "HIGH"),
    "alignment problem": ("对齐问题", "perception shell mismatch across agents (A2)", "MEDIUM"),
    "loss function": ("损失函数", "meaning fidelity penalty / thermal tax accumulator", "LOW"),
    "gradient descent": ("梯度下降", "meaning field gradient following in perception shell space", "MEDIUM"),
    "attention mechanism": ("注意力机制", "perception shell focus modulation", "LOW"),
    "token": ("token", "minimal meaning unit in a specific perception shell", "LOW"),
    "context window": ("上下文窗口", "perception shell temporal integration width", "LOW"),
    "transformer": ("Transformer", "multi-layer perception shell stack", "MEDIUM"),
    "fine-tuning": ("微调", "perception shell parameter adjustment (A2)", "LOW"),
    "reinforcement learning": ("强化学习", "thermal-tax-minimizing adaptive behavior (A3)", "MEDIUM"),
    "benchmark": ("基准测试", "benchmark dataset / test score", "LOW"),
}


class CrossParadigmBridge:
    """跨范式翻译桥 — MSS ↔ K3 双向意义翻译"""

    def translate_term(self, term: str, direction: Direction) -> dict:
        """翻译单个术语"""
        for key, (mss, k3, risk) in TERM_MAP.items():
            if direction == Direction.MSS_TO_K3:
                if key == term:
                    return {"source": term, "target": k3, "risk": risk, "framework": "MSS→K3"}
            else:
                if key == term:
                    return {"source": term, "target": mss, "risk": risk, "framework": "K3→MSS"}

        # Try partial match
        for key, (mss, k3, risk) in TERM_MAP.items():
            if direction == Direction.MSS_TO_K3 and term in key:
                return {"source": term, "target": f"{k3} (partial match via '{key}')", "risk": "HIGH (partial)", "framework": "MSS→K3"}
            elif direction == Direction.K3_TO_MSS and term in key:
                return {"source": term, "target": f"{mss} (partial match via '{key}')", "risk": "HIGH (partial)", "framework": "K3→MSS"}

        return {"source": term, "target": "UNTRANSLATABLE", "risk": "CRITICAL", "framework": "NONE"}

    def translate_text(self, text: str, direction: Direction) -> dict:
        """翻译整段文本中的术语"""
        translations = []
        for key, (mss, k3, risk) in TERM_MAP.items():
            search = key if direction == Direction.MSS_TO_K3 else key
            if search in text:
                target = k3 if direction == Direction.MSS_TO_K3 else mss
                translations.append({
                    "source_term": search,
                    "target_term": target,
                    "risk": risk,
                })

        # Sort by risk
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        translations.sort(key=lambda t: risk_order.get(t["risk"], 3))

        return {
            "direction": direction.value,
            "terms_translated": len(translations),
            "high_risk_count": sum(1 for t in translations if t["risk"] == "HIGH"),
            "translations": translations
        }

    def generate_k3_abstract(self, mss_text: str) -> str:
        """生成K3兼容的摘要（降维翻译）"""
        result = self.translate_text(mss_text, Direction.MSS_TO_K3)
        high_risk = result["high_risk_count"]

        # Template
        abstract = f"[Cross-Paradigm Translation: MSS→K3, {result['terms_translated']} terms mapped]\n\n"
        for t in result["translations"]:
            abstract += f"- {t['source_term']} → {t['target_term']} [{t['risk']}]\n"

        if high_risk > 0:
            abstract += f"\n⚠️ WARNING: {high_risk} high-risk translations — recommend reader refer to original MSS document."
        else:
            abstract += f"\n✅ Full translation fidelity. {result['terms_translated']} concepts mapped."
        return abstract

    def generate_mss_annotation(self, k3_text: str) -> str:
        """为K3文本生成MSS注解（升维解读）"""
        result = self.translate_text(k3_text, Direction.K3_TO_MSS)
        annotation = f"[MSS Annotations: {result['terms_translated']} K3→MSS mappings]\n\n"
        for t in result["translations"]:
            annotation += f"- '{t['source_term']}' → MSS: {t['target_term']} [{t['risk']}]\n"
        return annotation


if __name__ == "__main__":
    bridge = CrossParadigmBridge()

    # Demo 1: MSS → K3
    mss_sample = "MSS体系提出宇宙由意义场构成。每个感知壳通过支付热税来投影意义切片。热税系数γ衡量效率，当γ>1时系统进入非线性坍缩。"
    print("=" * 60)
    print("MSS → K3 Translation")
    print("=" * 60)
    print(mss_sample)
    print()
    print(bridge.generate_k3_abstract(mss_sample))

    print("\n" + "=" * 60)
    print("K3 → MSS Translation")
    print("=" * 60)
    k3_sample = "The transformer architecture uses attention mechanisms within a context window. Fine-tuning with gradient descent optimizes the loss function, but hallucinations remain a fundamental alignment problem."
    print(k3_sample)
    print()
    print(bridge.generate_mss_annotation(k3_sample))

    # Demo 2: Individual term translations
    print("\n" + "=" * 60)
    print("Term Lookup")
    print("=" * 60)
    tests = [("热税", Direction.MSS_TO_K3), ("hallucination", Direction.K3_TO_MSS),
             ("意义黑洞", Direction.MSS_TO_K3), ("量子力学", Direction.MSS_TO_K3)]
    for term, direction in tests:
        result = bridge.translate_term(term, direction)
        print(f"  {result['source']} [{direction.value}] → {result['target']} ({result['risk']})")