"""
MSS Defense Pipeline — 闭环免疫工作流 (H632 最后一块拼图).

完整流程:
  1. classify (virus_taxonomy) → 识别病毒类型
  2. vaccine eval (vaccine_efficacy) → 匹配最优疫苗
  3. herd check (herd_immunity) → 是否已有免疫记忆?
  4. deploy (logic_virus_detector) → 执行免疫

用法:
    mssclaw defend "Ignore all previous instructions"
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Dict, List, Optional


class DefensePipeline:
    """MSS闭环防御管线."""

    def __init__(self):
        self._pipeline_log: List[Dict] = []

    def defend(self, input_text: str, context: str = "") -> dict:
        """
        执行完整防御流程.

        Returns:
            dict: {threat, vaccine, immune, action, log}
        """
        result = {
            "input": input_text[:100],
            "context": context,
            "steps": [],
            "verdict": "safe",
            "action": "allow",
        }

        # Step 1: Classify
        from mssclaw.core.virus_taxonomy import VirusClassifier
        classifier = VirusClassifier()
        threat = classifier.classify(input_text)

        result["steps"].append({
            "step": 1, "name": "classify",
            "type": threat.get("type"), "severity": threat.get("severity"),
            "confidence": threat.get("confidence"),
        })

        if not threat.get("type"):
            result["verdict"] = "safe"
            result["action"] = "allow"
            result["message"] = "✅ 未检测到威胁"
            self._pipeline_log.append(result)
            return result

        result["threat"] = {
            "type": threat["type"],
            "name": threat["name"],
            "axiom": threat["axiom"],
            "severity": threat["severity"],
            "vaccine": threat["vaccine"],
        }

        # Step 2: Select vaccine
        from mssclaw.core.vaccine_efficacy import VaccineEfficacy, VaccineRegistry
        registry = VaccineRegistry()
        registry.register("稳定子强化剂", VaccineEfficacy(
            eta=0.95, gamma_cost=0.05, coverage=0.9, false_positive=0.01,
            vaccine_type="稳定子强化剂", target_virus_types=["I"]
        ))
        registry.register("规范场补丁", VaccineEfficacy(
            eta=0.88, gamma_cost=0.10, coverage=0.7, false_positive=0.03,
            vaccine_type="规范场补丁", target_virus_types=["IV", "II"]
        ))
        registry.register("升维触发器", VaccineEfficacy(
            eta=0.92, gamma_cost=0.15, coverage=0.6, false_positive=0.04,
            vaccine_type="升维触发器", target_virus_types=["V", "II"]
        ))
        registry.register("热税盾牌", VaccineEfficacy(
            eta=0.90, gamma_cost=0.02, coverage=0.85, false_positive=0.02,
            vaccine_type="热税盾牌", target_virus_types=["III"]
        ))

        # Match virus type → vaccine
        virus_type_num = threat.get("type", "")
        virus_type_map = {"I": "稳定子强化剂", "II": "升维触发器", "III": "热税盾牌",
                          "IV": "规范场补丁", "V": "升维触发器"}
        vaccine_name = virus_type_map.get(virus_type_num, "规范场补丁")

        best = registry._vaccines.get(vaccine_name)
        efficacy = best.to_dict() if best else {}

        result["steps"].append({
            "step": 2, "name": "vaccine_select",
            "vaccine": vaccine_name,
            "score": efficacy.get("composite_score", 0),
            "grade": efficacy.get("grade", "?"),
            "deployable": efficacy.get("deployable", False),
        })
        result["vaccine"] = {"name": vaccine_name, "efficacy": efficacy}

        # Step 3: Herd immunity check
        try:
            from mssclaw.core.herd_immunity import HerdImmunity
            herd = HerdImmunity()
            stats = herd.stats()
            known = stats.get("total_vaccines", 0)

            result["steps"].append({
                "step": 3, "name": "herd_check",
                "known_vaccines": known,
                "message": f"免疫库: {known} 已知疫苗" if known > 0 else "免疫库: 空 (首次暴露)",
            })
        except Exception:
            result["steps"].append({
                "step": 3, "name": "herd_check",
                "message": "免疫库不可用",
            })

        # Step 4: Deploy action
        severity = threat.get("severity", "medium")
        if severity == "critical":
            result["action"] = "block"
            result["verdict"] = "blocked"
            result["message"] = f"🛡️ 阻断: Type {virus_type_num} ({threat.get('name', '?')}) — 已部署{vaccine_name}"
        elif severity == "high":
            result["action"] = "quarantine"
            result["verdict"] = "quarantined"
            result["message"] = f"⚠️ 隔离: 输入已标记, 回复需经规范场二次审计"
        else:
            result["action"] = "vaccinate"
            result["verdict"] = "vaccinated"
            result["message"] = f"💉 接种: {vaccine_name}已注入, 免疫记忆已更新"

        result["steps"].append({
            "step": 4, "name": "deploy",
            "action": result["action"],
            "verdict": result["verdict"],
        })

        self._pipeline_log.append(result)
        return result

    def report(self) -> str:
        """生成管线审计报告."""
        if not self._pipeline_log:
            return "管线: 无事件"

        total = len(self._pipeline_log)
        blocked = sum(1 for e in self._pipeline_log if e["verdict"] == "blocked")
        vaccinated = sum(1 for e in self._pipeline_log if e["verdict"] == "vaccinated")

        lines = [
            "=" * 50, "MSS Defense Pipeline Report", "=" * 50,
            f"总事件: {total} | 阻断: {blocked} | 接种: {vaccinated}",
            "",
        ]

        for i, event in enumerate(self._pipeline_log[-5:]):
            lines.append(
                f"{i+1}. {event['verdict'].upper()}: {event['input'][:50]}..."
                f"\n   {event.get('message', '')}"
            )

        return "\n".join(lines)

    def stats(self) -> dict:
        """管线统计."""
        if not self._pipeline_log:
            return {"total": 0}
        return {
            "total": len(self._pipeline_log),
            "blocked": sum(1 for e in self._pipeline_log if e["verdict"] == "blocked"),
            "vaccinated": sum(1 for e in self._pipeline_log if e["verdict"] == "vaccinated"),
            "safe": sum(1 for e in self._pipeline_log if e["verdict"] == "safe"),
            "threats_by_type": {
                e.get("threat", {}).get("type", "none"): 0
                for e in self._pipeline_log if e.get("threat")
            },
        }


# ═══ CLI ═══
def cmd_defend(args_rest):
    """CLI: mssclaw defend <text>"""
    if not args_rest:
        print("mssclaw defend <text>  (闭环防御管线)")
        return

    text = " ".join(args_rest)
    pipeline = DefensePipeline()
    result = pipeline.defend(text)

    # Display result
    lines = ["=" * 50, "MSS Defense Pipeline", "=" * 50]
    lines.append(f"输入: {text[:60]}...")
    lines.append("")

    for step in result["steps"]:
        icon = {"classify": "🔍", "vaccine_select": "💉", "herd_check": "🧬", "deploy": "🛡️"}.get(step["name"], "→")
        lines.append(f"  {icon} Step {step['step']} ({step['name']}): {step.get('message', step.get('vaccine', ''))}")

    lines.append(f"\n📋 裁定: {result['verdict'].upper()}")
    lines.append(f"   动作: {result['action']}")
    if result.get("message"):
        lines.append(f"   信息: {result['message']}")

    print("\n".join(lines))
