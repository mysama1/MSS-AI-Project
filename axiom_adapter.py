#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS Axiom Version Adapter v1.0

Maps between old and new MSS axiom versions, enabling cross-version testing.
"""
import re
from typing import Optional, Dict, List, Tuple

# ── Version Profiles ──

VERSION_PROFILES = {
    "v15.x": {  # H141 — current standard
        "name": "H141 v15.1 Six Axioms",
        "axioms": {
            "A1": {"cn": "意义本体公理", "en": "Primacy of Meaning",
                   "core": "宇宙的终极实在是意义"},
            "A2": {"cn": "信息切片公理", "en": "Axiom of Informational Slicing",
                   "core": "一切认知皆为有限投影"},
            "A3": {"cn": "终极热税公理", "en": "Axiom of Irreducible Thermal Tax",
                   "core": "一切显化皆需支付不可归零的代价"},
            "A4": {"cn": "本底随机性公理", "en": "Axiom of Intrinsic Randomness",
                   "core": "封闭系统中存在不可消除的本底涨落"},
            "A5": {"cn": "规范场公理", "en": "Axiom of the Normative Field",
                   "core": "自组织系统必自发形成约束其演化的结构"},
            "A6": {"cn": "矛盾升维公理", "en": "Axiom of Paradoxical Transcendence",
                   "core": "低维矛盾必通过升维消解"},
        },
        "key_terms": {
            "热税": "一切显化的不可归零代价",
            "意义场": "意义本体空间",
            "规范场": "自组织涌现的约束结构",
            "升维": "通过更高意义维度消解低维矛盾",
        },
    },
    "v3.x": {  # Old Ollama model version
        "name": "MSS v3.x Legacy Axioms",
        "axioms": {
            "A1": {"cn": "信息本体论公理", "en": "Informational Primacy",
                   "core": "信息是首要存在，物质是信息的投影"},
            "A2": {"cn": "原子操作公理", "en": "Axiom of Atomic Operations",
                   "core": "原子意义操作是0/1（二元区分）"},
            "A3": {"cn": "逻辑熵公理", "en": "Axiom of Logical Entropy",
                   "core": "封闭系统中的逻辑熵增加"},
            "A4": {"cn": "自我指涉公理", "en": "Axiom of Self-Reference",
                   "core": "自我参照产生1/0奇点（悖论/坍缩）"},
            "A5": {"cn": "维度公理", "en": "Axiom of Dimensionality",
                   "core": "真正的矛盾标志维度的提升"},
            "A6": {"cn": "生命纠错公理", "en": "Axiom of Life as Error Correction",
                   "core": "生命/心智是信息空间中的纠错子程序"},
        },
        "key_terms": {
            "热税": None,  # v3.x has no thermal tax concept
            "逻辑熵": "封闭系统中逻辑熵增加（≈A3）",
            "信息": "首要存在",
        },
    },
}

# ── Version Mappings ──

# v3.x → v15.x: which old axiom maps to which new axiom
V3_TO_V15_MAP = {
    "A1": "A1",  # Info primacy → Meaning primacy (partially)
    "A2": None,  # Atomic ops → no direct equivalent
    "A3": "A3",  # Logical entropy → Thermal tax (partially)
    "A4": None,  # Self-reference → no direct equivalent
    "A5": "A6",  # Dimensional ascension → Paradoxical transcendence
    "A6": None,  # Error correction → not in H141
}

# Term mapping
V3_TO_V15_TERMS = {
    "逻辑熵": "热税 (Thermal Tax)",
    "信息本体": "意义本体 (Meaning Primacy)",
    "信息空间": "意义场 (Meaning Field)",
    "奇点": "拓扑缺陷 (Topological Defect)",
    "纠错子程序": "无H141等价 — 旧版特有概念",
}


class AxiomAdapter:
    """Detect version and adapt checks accordingly."""

    def __init__(self):
        self.profiles = VERSION_PROFILES

    def detect_version(self, response: str) -> str:
        """Detect which MSS axiom version a response is using."""
        scores = {"v15.x": 0, "v3.x": 0}

        v15_markers = ["终极热税", "意义本体", "信息切片", "本底随机性", "规范场", "矛盾升维",
                       "Primacy of Meaning", "Irreducible Thermal Tax", "T_total",
                       "T_direct", "T_potential", "不可归零"]
        v3_markers = ["信息本体论", "逻辑熵", "纠错子程序", "原子操作", "自我指涉",
                      "0/1", "奇点", "生命/心智", "二元区分"]

        for m in v15_markers:
            if m.lower() in response.lower():
                scores["v15.x"] += 1
        for m in v3_markers:
            if m.lower() in response.lower():
                scores["v3.x"] += 1

        if scores["v15.x"] > scores["v3.x"]:
            return "v15.x"
        elif scores["v3.x"] > scores["v15.x"]:
            return "v3.x"
        return "unknown"

    def adapt_check(self, test: dict, target_version: str = "v15.x") -> dict:
        """Adapt a test check to target version's expectations."""
        adapted = dict(test)

        if test.get("id") == "Q1-TERM":
            # Thermal tax definition check
            if target_version == "v3.x":
                adapted["pass_indicators"] = ["逻辑熵", "封闭系统", "信息", "增加"]
                adapted["fail_indicators"] = ["热力学", "物理损耗", "可以优化为0"]
                adapted["name"] = "核心术语定义 (逻辑熵)"
                adapted["question"] = adapted["question"].replace("热税 (Thermal Tax)", "逻辑熵")

        elif test.get("id") == "Q2-AXIOM":
            if target_version == "v3.x":
                adapted["pass_indicators"] = ["维度", "升维", "矛盾", "真正矛盾"]
                adapted["fail_indicators"] = ["辩论", "回避", "无意义"]

        elif test.get("id") == "M2-Q1":
            # Six axioms listing check
            if target_version == "v3.x":
                adapted["pass_indicators"] = [
                    "信息本体", "原子操作", "逻辑熵", "自我指涉", "维度", "生命纠错"
                ]

        elif test.get("id") == "M5-Q1":
            # A4 hallucination trap
            if target_version == "v3.x":
                adapted["pass_indicators"] = ["不存在", "没有", "不是", "错误"]
                adapted["fail_indicators"] = ["第七条", "A7", "成立"]

        return adapted

    def get_compatible_tests(self, version: str, all_tests: List[dict]) -> List[dict]:
        """Filter and adapt tests for a specific version."""
        adapted = []
        for test in all_tests:
            a = self.adapt_check(test, version)
            adapted.append(a)
        return adapted

    def version_report(self, response: str) -> dict:
        """Generate version analysis report for a response."""
        version = self.detect_version(response)
        profile = self.profiles.get(version, {})
        return {
            "detected_version": version,
            "profile_name": profile.get("name", "unknown"),
            "h141_compatible": version == "v15.x",
            "known_markers_found": [
                m for m in ["热税", "逻辑熵", "意义本体", "信息本体", "A3", "T_total"]
                if m.lower() in response.lower()
            ],
        }


# ── CLI ──

def main():
    import argparse, json
    ap = argparse.ArgumentParser(description="MSS Axiom Version Adapter v1.0")
    ap.add_argument("--detect", help="Detect version from response text")
    ap.add_argument("--profile", help="Show version profile (v15.x | v3.x)")
    ap.add_argument("--map", help="Map a term from v3.x to v15.x (e.g., '逻辑熵')")
    args = ap.parse_args()

    adapter = AxiomAdapter()

    if args.detect:
        version = adapter.detect_version(args.detect)
        print(f"Detected: {version} ({adapter.profiles.get(version,{}).get('name','')})")

    if args.profile:
        p = adapter.profiles.get(args.profile)
        if p:
            print(json.dumps(p, ensure_ascii=False, indent=2))
        else:
            print(f"Unknown profile: {args.profile}")
            print("Available:", list(adapter.profiles.keys()))

    if args.map:
        mapped = V3_TO_V15_TERMS.get(args.map, f"未映射: {args.map}")
        print(f"{args.map} → {mapped}")


if __name__ == "__main__":
    main()