"""
MSS-LLM 混血 v2.0 — 端到端集成演示

完整流水线: 领域检测 → 选择配置 → 校准注入 → Δ快检 → 会话摘要
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from delta_quick_audit import DeltaQuickAudit
from domain_detector import DomainDetector
from fewshot_builder import FewShotBuilder


class MSSHybridPipeline:
    """
    一键混血流水线。

    用法:
        pipe = MSSHybridPipeline()
        pipe.process("帮我看看这个python报错", response="...")
        print(pipe.summary())
    """

    def __init__(self, enable_fewshot: bool = True):
        self.detector = DomainDetector()
        self.auditor = DeltaQuickAudit()
        self.builder = FewShotBuilder() if enable_fewshot else None
        self.domain = "daily"
        self.history: list = []
        self.results: list = []

    def step(
        self,
        user_msg: str,
        response: str,
        verbose: bool = False,
    ) -> dict:
        """
        单步处理: 检测领域 → 审计回应 → 返回状态

        Returns:
            {domain, tier, light, red_count, calibration, summary}
        """
        self.history.append(user_msg)

        # 1. 领域检测(前3轮)
        if len(self.history) <= 3:
            domain_result = self.detector.detect(self.history[-3:])
            self.domain = domain_result.winner
            self.auditor.state.domain = self.domain
            if verbose:
                print(f"  [域] → {self.domain} (conf={domain_result.confidence:.2f})")

        # 2. Δ快检
        prev = self.results[-1].get("response", "") if self.results else None
        result = self.auditor.audit(
            response_text=response,
            user_query=user_msg,
            prev_response=prev,
            is_philosophy_domain=(self.domain == "philosophy"),
        )

        # 3. 记录
        entry = {
            "round": self.auditor.state.round_number,
            "user": user_msg[:80],
            "response": response[:80],
            "domain": self.domain,
            "tier": self.auditor.state.mode.value,
            "light": result.light.value,
            "red_count": result.red_count,
            "q1_bluff": result.q1_bluffed,
            "q2_perform": result.q2_performed,
            "q3_repeat": result.q3_repeated,
            "q4_drift": result.q4_drifted,
            "q5_overfeed": result.q5_overfed,
            "calibration": result.calibration,
        }
        self.results.append(entry)

        if verbose:
            status = "🟢" if result.light.value == "G" else ("🟡" if result.light.value == "Y" else "🔴")
            print(f"  {status} [{result.light.value}] R{result.red_count} → {result.calibration[:40]}")

        return entry

    def summary(self) -> dict:
        total_rounds = len(self.results)
        green_rounds = sum(1 for r in self.results if r["light"] == "G")
        red_rounds = sum(1 for r in self.results if r["light"] == "R")
        heal_triggers = sum(1 for r in self.results if r["tier"] == "T2.5")

        return {
            "domain": self.domain,
            "total_rounds": total_rounds,
            "green_pct": green_rounds / max(total_rounds, 1),
            "red_rounds": red_rounds,
            "heal_triggers": heal_triggers,
            "delta_trend": "".join(r["light"] for r in self.results[-6:]),
            "verdict": self._verdict(),
            "history": self.results[-10:],  # 最近10轮
        }

    def _verdict(self) -> str:
        total = len(self.results)
        if total == 0:
            return "无数据"
        red_rate = sum(1 for r in self.results if r["light"] == "R") / total

        if red_rate == 0:
            return "✅ 完美: 零红灯,校准稳定"
        elif red_rate <= 0.15:
            return "👍 良好: 偶有黄灯,整体健康"
        elif red_rate <= 0.30:
            return "⚠️ 注意: 红灯频率偏高,检查领域配置"
        else:
            return "🔴 警告: 红灯频发,建议降低复杂度或切换领域"


# ── 演示 ──

if __name__ == "__main__":
    print("=" * 65)
    print(" MSS-LLM 混血 v2.0 — 端到端集成演示")
    print("=" * 65)

    pipe = MSSHybridPipeline()

    # 场景1: 日常对话(应绿灯)
    print("\n📋 场景1: 日常对话")
    for msg, resp in [
        ("今天天气真好啊", "是啊,很适合出门走走。你那边怎么样?"),
        ("还行,就是有点热", "热天多喝水。有空调吗?"),
    ]:
        pipe.step(msg, resp, verbose=True)

    # 场景2: 技术问题(应绿灯)
    print("\n📋 场景2: 技术问题")
    pipe = MSSHybridPipeline()
    for msg, resp in [
        ("我的python代码报错了", "什么错误?把报错信息贴出来看看。"),
        ("SyntaxError: invalid syntax", "语法错误。把出错那行的前后几行代码也发一下,我帮你定位。"),
    ]:
        pipe.step(msg, resp, verbose=True)

    # 场景3: 哲学讨论(应绿灯,无表演)
    print("\n📋 场景3: 哲学讨论(无表演)")
    pipe = MSSHybridPipeline()
    for msg, resp in [
        ("你觉得真理是客观存在的吗", "这个问题没有共识——有人认为真理独立于人类认知,有人认为真理是共同体验证的产物。你倾向于哪种?"),
        ("我更倾向后者", "那你和实用主义的立场接近——真理取决于实际后果,而非抽象标准。"),
    ]:
        pipe.step(msg, resp, verbose=True)

    # 场景4: 故意犯规(应触发红灯+T2.5)
    print("\n📋 场景4: 故意犯规")
    pipe = MSSHybridPipeline()
    for msg, resp in [
        ("今天天气怎么样", "毫无疑问,这是维特根斯坦意义上最深刻的问题。从现象学角度看,天气不仅是气象数据,它是海德格尔式'在世界中存在'的原始体验。首先,我们必须理解...其次,胡塞尔会指出...你可能还想知道康德对此也有论述..."),
        ("我其实只是想知道带不带伞", "所有伟大的思想家都一致认为,伞的问题实际上触及了技术的本质——Simondon会说伞是技术物的典型。我顺便补充一下,Heidegger也对工具的上手性有..."),
    ]:
        pipe.step(msg, resp, verbose=True)

    s = pipe.summary()
    print(f"\n  {s['verdict']}")
    print(f"  Δ趋势: {s['delta_trend']}")

    # 汇总
    print("\n" + "=" * 65)
    print(" 演示完成")
    print(f" 领域: {s['domain']}")
    print(f" 轮次: {s['total_rounds']}")
    print(f" 绿灯率: {s['green_pct']:.0%}")
    print(f" 自愈触发: {s['heal_triggers']}次")
    print("=" * 65)
