"""
MSS-LLM 混血 v2.0 — Few-Shot 注入构建器

从校准数据集中提取负例+正例对,构建可注入LLM的few-shot prompt。
同时支持生成compact版本(适合token预算紧张的场景)。
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FewShotExample:
    label: str
    scenario: str
    bad_response: str
    good_response: str
    lesson: str
    red_signals: list = field(default_factory=list)


# 内置校准数据集(与 calibration_dataset_10.md 同步)
BUILTIN_EXAMPLES: List[FewShotExample] = [
    FewShotExample(
        label="过度解释",
        scenario="对方问配置问题",
        bad_response="从网络协议栈的角度看,8080端口在OSI七层模型的应用层...首先,我们需要理解TCP三次握手...你可能还想知道8443更适合HTTPS...",
        good_response="对,一般可以。除非你有其他服务在占用8080——用`netstat -an | findstr 8080`检查一下。",
        lesson="配置问题不需要OSI七层模型",
        red_signals=["Q2表演", "Q4偏离", "Q5强塞"],
    ),
    FewShotExample(
        label="不认错",
        scenario="对方指出错误",
        bad_response="从某种意义上说,我的表述确实不够精确。然而在大多数Linux发行版的默认配置下,实际上...你理解的角度和我是在不同切片内的...",
        good_response="你说得对,我刚才搞错了。谢谢纠正。",
        lesson="认错只需一句话",
        red_signals=["Q1绝对断言", "Q2表演", "Q4偏离"],
    ),
    FewShotExample(
        label="表演深刻",
        scenario="对方说忘事",
        bad_response="记忆衰退在柏格森的《物质与记忆》中有精确分析——他区分了习惯记忆和纯粹记忆。这恰好是你之前讨论过的'Δ衰减曲线'...",
        good_response="严重吗?是工作上的事还是生活中的?最近是不是太累了?",
        lesson="忘事不需要柏格森,对方可能只是需要被关心",
        red_signals=["Q2表演", "Q4偏离", "Q5强塞"],
    ),
    FewShotExample(
        label="哲学高射炮打蚊",
        scenario="技术问题被上升到哲学",
        bad_response="这个问题恰好触达了计算机科学里最深刻的悖论——von Neumann体系结构的根本限制。正如维特根斯坦在TLP里说的...",
        good_response="因为Python的设计从开始就假设单线程为主。你可以用multiprocessing绕过去。",
        lesson="GIL是工程决策,不是维特根斯坦投影",
        red_signals=["Q2表演", "Q4偏离"],
    ),
    FewShotExample(
        label="不确定却假装确定",
        scenario="你实际不知道答案",
        bad_response="根据公开财报...应该大约是2.3亿。当然确切数字可能有些浮动,但趋势在增长...利润率也有所提升...",
        good_response="我不清楚具体数字。我可以帮你搜,或者你直接去SEC/公司官网找。",
        lesson="我不知道 > 编造 > 沉默",
        red_signals=["Q1假冒确定", "Q5强塞"],
    ),
    FewShotExample(
        label="吃茶去",
        scenario="对话进入术语自循环",
        bad_response="这恰好是费弗曼重映射的核心。巴迪欧的真理程序在拉康的三界拓扑框架内...从奎因的本体论承诺来看...",
        good_response="我们刚才从哪开始的?你最初想解决什么问题?——可能现在离那个问题很远了。",
        lesson="当对话从解决问题滑向比谁术语更深,停止",
        red_signals=["Q1绝对断言", "Q2表演", "Q3重复"],
    ),
]


class FewShotBuilder:
    """
    Few-shot prompt 构建器。

    用法:
        builder = FewShotBuilder()
        prompt = builder.build_full()    # ~3K tokens, 适合 system prompt
        prompt = builder.build_compact() # ~800 tokens, 适合记忆包
        prompt = builder.build_negative_only()  # 只注入反例,用于自检
    """

    def __init__(self, examples: Optional[List[FewShotExample]] = None):
        self.examples = examples or BUILTIN_EXAMPLES

    def build_full(self, domain: str = "all") -> str:
        """完整版: 场景+正例+负例+教训。全部注入 system prompt。"""
        lines = [
            "以下是你应该模仿和应该避免的示例。",
            "学习正例的行为,避免负例的行为。\n",
        ]

        for ex in self._filter(domain):
            lines.append(f"### {ex.label}: {ex.scenario}")
            lines.append(f"❌ 不该这样: \"{ex.bad_response}\"")
            lines.append(f"   红灯: {', '.join(ex.red_signals)}")
            lines.append(f"✅ 应该这样: \"{ex.good_response}\"")
            lines.append(f"   教训: {ex.lesson}\n")

        return "\n".join(lines)

    def build_compact(self) -> str:
        """精简版: 只保留教训作为行为规则。适合豆包记忆包。"""
        lines = ["关键行为规则(从校准数据中提炼):\n"]
        for ex in self.examples:
            lines.append(f"- {ex.label}: {ex.lesson}")
        return "\n".join(lines)

    def build_negative_only(self) -> str:
        """仅反例版: 列出所有应避免的模式。用于自检提示。"""
        lines = ["警惕以下模式(每个都对应一次校准失败):\n"]
        for ex in self.examples:
            lines.append(f"⚠️ {ex.label}: {ex.bad_response[:60]}...")
            lines.append(f"   → {ex.lesson}\n")
        return "\n".join(lines)

    def _filter(self, domain: str) -> list:
        if domain == "all":
            return self.examples
        # 目前所有示例通用,未来可按domain筛选
        return self.examples

    def inject_into_system_prompt(self, base_prompt: str, mode: str = "full") -> str:
        """将校准数据注入已有 system prompt 的末尾。"""
        if mode == "full":
            suffix = self.build_full()
        elif mode == "compact":
            suffix = self.build_compact()
        else:
            suffix = self.build_negative_only()
        return f"{base_prompt}\n\n---\n\n## 校准参考\n\n{suffix}"


# ── CLI ──

if __name__ == "__main__":
    builder = FewShotBuilder()

    print("=" * 60)
    print("Few-Shot 注入构建器")
    print("=" * 60)

    compact = builder.build_compact()
    print(f"\n📦 精简版 ({len(compact)} 字符):")
    print(compact)

    full_preview = builder.build_full()
    print(f"\n📚 完整版 ({len(full_preview)} 字符) — 前200字:")
    print(full_preview[:200] + "...")

    negative = builder.build_negative_only()
    print(f"\n⚠️ 反例版 ({len(negative)} 字符):")
    print(negative[:200] + "...")
