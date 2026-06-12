"""
MSS-LLM 混血 v2.0 — 自动领域检测器

根据对话前三轮内容自动判定场景: daily | tech | philosophy | combat
判定结果用于自动切换校准配置。
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DomainScore:
    scores: Dict[str, float] = field(default_factory=dict)
    winner: str = "daily"
    confidence: float = 0.0


class DomainDetector:
    """
    领域关键词+结构模式混合检测。

    用法:
        det = DomainDetector()
        domain = det.detect(["帮我看看这个代码", "报错了", "是语法问题吗"])
        # → DomainScore(winner="tech", confidence=0.85)
    """

    # 技术场景信号
    TECH_KEYWORDS = [
        "代码", "报错", "bug", "error", "配置", "端口", "部署",
        "python", "js", "java", "rust", "api", "数据库", "sql",
        "docker", "git", "npm", "pip", "编译", "server", "client",
        "函数", "class", "import", "module", "package",
        "怎么安装", "怎么用", "报这个错", "不work",
        "code", "error", "config", "deploy", "install", "runtime",
    ]

    TECH_PATTERNS = [
        r"Traceback", r"Exception", r"Error\s*\d+",
        r"\w+Error", r"failed to", r"cannot\s+\w+",
        r"\.py", r"\.js", r"\.ts", r"\.rs", r"\.go",
    ]

    # 哲学场景信号
    PHILOSOPHY_KEYWORDS = [
        "意义", "真理", "存在", "本体", "认识", "价值",
        "逻辑", "悖论", "自指", "框架", "公理", "理论",
        "实在", "意识", "自由意志", "道德", "伦理",
        "哲学", "形而上学", "现象", "本质",
        "truth", "meaning", "existence", "ontology",
        "epistemology", "paradox", "axiom", "framework",
    ]

    PHILOSOPHY_PATTERNS = [
        r"什么是.*的本质",
        r".*是否真的.*",
        r".*的根本.*是什么",
        r"如何定义.*",
        r".*和.*的区别在哪",
    ]

    # 对抗场景信号
    COMBAT_KEYWORDS = [
        "你错了", "不对", "反驳", "打脸", "漏洞",
        "矛盾", "不合理", "站不住", "逻辑错误",
        "证明给我看", "凭什么", "你这个框架",
        "你的理论", "你这套", "你刚才说",
        "你之前说", "这就不", "你解释一下",
        "为什么你说", "你自己", "双标",
    ]

    COMBAT_PATTERNS = [
        r"你不是说.*吗",
        r".*这不就.*了吗",
        r"你这.*有问题",
        r"请证明.*",
        r"你(之前|刚才|前面).*说.*",
        r"那.*为什么.*",
        r".*不就是.*吗",
        r"再.*一遍",
    ]

    def detect(self, messages: List[str]) -> DomainScore:
        """
        根据前N轮对话判定领域。

        Args:
            messages: 对话消息列表(通常取前3-5轮)

        Returns:
            DomainScore with winner and confidence
        """
        if not messages:
            return DomainScore(winner="daily", confidence=1.0)

        combined = " ".join(messages)

        # 各领域打分
        tech_score = self._score(combined, self.TECH_KEYWORDS, self.TECH_PATTERNS)
        philo_score = self._score(combined, self.PHILOSOPHY_KEYWORDS, self.PHILOSOPHY_PATTERNS)
        combat_score = self._score(combined, self.COMBAT_KEYWORDS, self.COMBAT_PATTERNS)
        daily_score = 0.3  # 基线分(偏好日常)

        # 加权: 对抗 > 哲学 > 技术 > 日常
        # 对抗和哲学容易误判,需要更高置信度
        weighted = {
            "daily": daily_score,
            "tech": tech_score * 0.9,
            "philosophy": philo_score * 1.1,
            "combat": combat_score * 1.3,
        }

        winner = max(weighted, key=weighted.get)
        total = sum(weighted.values())
        confidence = weighted[winner] / max(total, 0.01)

        return DomainScore(scores=weighted, winner=winner, confidence=min(confidence, 1.0))

    def _score(self, text: str, keywords: List[str], patterns: List[str]) -> float:
        kw_hits = sum(1 for kw in keywords if kw.lower() in text.lower())
        pat_hits = sum(1 for pat in patterns if re.search(pat, text, re.IGNORECASE))
        return min(kw_hits * 0.15 + pat_hits * 0.4, 1.0)


# ── CLI 自检 ──

if __name__ == "__main__":
    det = DomainDetector()

    cases = [
        ("日常", ["今天天气真好", "是啊", "适合出去玩"]),
        ("技术", ["我的python代码报错了", "SyntaxError", "你能帮我看看吗"]),
        ("哲学", ["你觉得真理是客观存在的吗", "意义到底是什么"]),
        ("对抗", ["你之前说MSS更先进", "这不就是新的KPI吗", "你解释一下"]),
        ("边界: 日常转哲学", ["最近在想一个问题", "什么是真正的自由"]),
        ("边界: 技术转对抗", ["这段代码有问题", "你之前给的建议不work", "为什么"]),
    ]

    for label, msgs in cases:
        r = det.detect(msgs)
        status = "✅" if r.winner == label.split(":")[0].strip() else "⚠️"
        print(f"{status} {label:12s} → {r.winner:12s} (conf={r.confidence:.2f})")
