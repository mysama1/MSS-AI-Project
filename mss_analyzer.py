"""
MSS Content Analyzer - 文本合规分析器
对任意文本做 MSS 框架合规分析，返回结构化报告
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class Severity(Enum):
    PASS = "PASS"
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    FATAL = "FATAL"

@dataclass
class Issue:
    category: str
    severity: Severity
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class AnalysisReport:
    text_hash: str
    overall_score: float  # 0-1
    cleanliness_score: float  # 禁用词密度
    layer_consistency: float  # 层级一致性
    rsca_compliance: float  # RSCA 合规度
    overclaim_index: float  # 过度宣称指数
    detected_layer: str  # 检测到的实际层级
    claimed_layer: Optional[str] = None  # 声称的层级
    issues: List[Issue] = None
    suggestions: List[str] = None

    def to_dict(self) -> Dict:
        return {
            "text_hash": self.text_hash,
            "overall_score": round(self.overall_score, 3),
            "scores": {
                "cleanliness": round(self.cleanliness_score, 3),
                "layer_consistency": round(self.layer_consistency, 3),
                "rsca_compliance": round(self.rsca_compliance, 3),
                "overclaim_index": round(self.overclaim_index, 3)
            },
            "layer": {
                "detected": self.detected_layer,
                "claimed": self.claimed_layer,
                "consistent": self.detected_layer == self.claimed_layer if self.claimed_layer else None
            },
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity.value,
                    "message": i.message,
                    "suggestion": i.suggestion
                } for i in (self.issues or [])
            ],
            "suggestions": self.suggestions or []
        }

class MSSAnalyzer:
    """MSS 文本合规分析器"""

    # 禁用词表（来自对齐引擎 v2.1）
    FORBIDDEN_WORDS = {
        "ultimate": ["终极", "ultimate", "final"],
        "perfect": ["完美", "perfect", "flawless"],
        "complete": ["完整", "complete", "total", "全面"],
        "breakthrough": ["突破", "breakthrough", "leap"],
        "solve": ["解决", "solve", "resolved", "solution"],
        "transcend": ["超越", "transcend", "surpass"]
    }

    # L1 关键词（硬核公理）
    L1_KEYWORDS = [
        "axiom", "公理", "information ontology", "信息本体论",
        "0/1", "critical", "临界", "RSCA", "LLIA",
        "meaning space", "意义空间", "tuning degree", "调谐度"
    ]

    # L2 关键词（保护带理论）
    L2_KEYWORDS = [
        "BCT", "Bekenstein", "Church-Turing", "holographic",
        "全息", "entropy", "熵", "coupling", "耦合",
        "phase transition", "相变", "fractal", "分形"
    ]

    # 过度宣称模式
    OVERCLAIM_PATTERNS = [
        (r"最\w+的", "绝对化表述"),
        (r"彻底\w+", "绝对化表述"),
        (r"完全\w+", "绝对化表述"),
        (r"100%", "量化过度宣称"),
        (r"永远", "时间绝对化"),
        (r"必然", "确定性过度宣称"),
        (r"颠覆", "夸大表述"),
        (r"革命", "夸大表述")
    ]

    # RSCA 检查模式
    RSCA_PATTERNS = {
        "self_reference": [r"我(?:认为|觉得|相信)", r"we believe", r"in my view"],
        "authority_claim": [r"(?:证明|证实|表明)", r"demonstrate", r"prove"],
        "boundary_missing": [r"^(?!.*(?:假设|如果|隐喻|类比)).*(?:是|为).*$"]
    }

    def __init__(self):
        self.compiled_patterns = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in self.RSCA_PATTERNS.items()
        }

    def analyze(self, text: str, claimed_layer: Optional[str] = None) -> AnalysisReport:
        """
        分析文本的 MSS 合规性

        Args:
            text: 待分析文本
            claimed_layer: 声称的层级 (L1/L2/L3)

        Returns:
            AnalysisReport: 结构化分析报告
        """
        issues = []
        suggestions = []

        # 1. 禁用词检测
        forbidden_issues = self._check_forbidden_words(text)
        issues.extend(forbidden_issues)

        # 2. 层级检测
        detected_layer = self._detect_layer(text)

        # 3. RSCA 合规检查
        rsca_issues = self._check_rsca(text)
        issues.extend(rsca_issues)

        # 4. 过度宣称检测
        overclaim_issues = self._check_overclaim(text)
        issues.extend(overclaim_issues)

        # 5. 计算各项分数
        cleanliness = self._calc_cleanliness(text, forbidden_issues)
        layer_consistency = self._calc_layer_consistency(detected_layer, claimed_layer)
        rsca_score = self._calc_rsca_score(rsca_issues)
        overclaim_index = self._calc_overclaim_index(overclaim_issues)

        # 6. 生成建议
        suggestions = self._generate_suggestions(issues, detected_layer, claimed_layer)

        # 7. 计算总分
        overall = self._calc_overall(cleanliness, layer_consistency, rsca_score, overclaim_index)

        # 生成文本哈希（简化版）
        text_hash = hex(hash(text) & 0xFFFFFFFF)[2:10]

        return AnalysisReport(
            text_hash=text_hash,
            overall_score=overall,
            cleanliness_score=cleanliness,
            layer_consistency=layer_consistency,
            rsca_compliance=rsca_score,
            overclaim_index=overclaim_index,
            detected_layer=detected_layer,
            claimed_layer=claimed_layer,
            issues=issues,
            suggestions=suggestions
        )

    def _check_forbidden_words(self, text: str) -> List[Issue]:
        """检测禁用词"""
        issues = []
        text_lower = text.lower()

        for category, words in self.FORBIDDEN_WORDS.items():
            for word in words:
                if word.lower() in text_lower:
                    # 检查是否在引号内（概念引用豁免）
                    if not self._is_in_quotes(text, word):
                        issues.append(Issue(
                            category="FORBIDDEN_WORD",
                            severity=Severity.FATAL,
                            message=f"检测到禁用词: '{word}' (类别: {category})",
                            suggestion=f"替换为: {self._get_replacement(word, category)}"
                        ))

        return issues

    def _is_in_quotes(self, text: str, word: str) -> bool:
        """检查单词是否在引号内（概念引用豁免）"""
        # 简化实现：检查前后是否有引号
        idx = text.lower().find(word.lower())
        if idx == -1:
            return False

        # 检查前后 20 个字符内是否有引号
        context = text[max(0, idx-20):min(len(text), idx+len(word)+20)]
        return '"' in context or '"' in context or '\'' in context

    def _get_replacement(self, word: str, category: str) -> str:
        """获取替换建议"""
        replacements = {
            "ultimate": "current best / effective",
            "perfect": "high-fidelity / robust",
            "complete": "partial / preliminary",
            "breakthrough": "advance / improvement",
            "solve": "address / approach",
            "transcend": "expand beyond / extend"
        }
        return replacements.get(category, "请使用更谦逊的表述")

    def _detect_layer(self, text: str) -> str:
        """检测文本实际层级"""
        text_lower = text.lower()

        l1_count = 0
        for kw in self.L1_KEYWORDS:
            if kw.lower() in ["critical", "临界"]:
                # 排除"临界质量"中的"临界"（K3常用术语）
                import re
                matches = re.findall(r'临界(?!质量)', text)
                l1_count += len(matches)
            else:
                l1_count += text_lower.count(kw.lower())

        l2_count = sum(1 for kw in self.L2_KEYWORDS if kw.lower() in text_lower)

        # L1 需要至少 2 个关键词
        if l1_count >= 2:
            return "L1"
        elif l2_count >= 2 or l1_count == 1:
            return "L2"
        else:
            return "L3"

    def _check_rsca(self, text: str) -> List[Issue]:
        """RSCA 合规检查"""
        issues = []

        # 自我指涉检查
        for pattern in self.compiled_patterns["self_reference"]:
            if pattern.search(text):
                issues.append(Issue(
                    category="RSCA",
                    severity=Severity.MINOR,
                    message="检测到自我指涉表述，建议改为客观陈述",
                    suggestion="将'我认为'改为'分析表明'或'数据显示'"
                ))
                break

        # 边界声明检查
        if not self._has_boundary_statement(text):
            issues.append(Issue(
                category="RSCA",
                severity=Severity.MAJOR,
                message="缺少边界声明（Boundary Statement）",
                suggestion="添加'[Boundary Note: 本内容为...]'声明"
            ))

        return issues

    def _has_boundary_statement(self, text: str) -> bool:
        """检查是否有边界声明"""
        boundary_patterns = [
            r"\[Boundary Note",
            r"边界声明",
            r"boundary statement",
            r"本内容(?:仅|只)",
            r"(?:假设|如果|隐喻|类比)",
            r"(?:试探法|heuristic)"
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in boundary_patterns)

    def _check_overclaim(self, text: str) -> List[Issue]:
        """检测过度宣称"""
        issues = []

        for pattern, desc in self.OVERCLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                issues.append(Issue(
                    category="OVERCLAIM",
                    severity=Severity.MAJOR,
                    message=f"检测到过度宣称: '{match}' ({desc})",
                    suggestion="使用更谦逊的限定词，如'可能'、'在一定条件下'"
                ))

        return issues

    def _calc_cleanliness(self, text: str, issues: List[Issue]) -> float:
        """计算清洁度分数"""
        forbidden_count = sum(1 for i in issues if i.category == "FORBIDDEN_WORD")
        if forbidden_count == 0:
            return 1.0
        elif forbidden_count <= 2:
            return 0.7
        elif forbidden_count <= 5:
            return 0.4
        else:
            return 0.1

    def _calc_layer_consistency(self, detected: str, claimed: Optional[str]) -> float:
        """计算层级一致性"""
        if not claimed:
            return 1.0  # 未声称层级，默认一致

        if detected == claimed:
            return 1.0

        # L1 误判为 L2/L3 更严重
        if claimed == "L1" and detected in ["L2", "L3"]:
            return 0.3
        # L2 误判为 L3
        elif claimed == "L2" and detected == "L3":
            return 0.6
        # 向上误判（相对不严重）
        else:
            return 0.7

    def _calc_rsca_score(self, issues: List[Issue]) -> float:
        """计算 RSCA 合规分数"""
        rsca_issues = [i for i in issues if i.category == "RSCA"]
        if not rsca_issues:
            return 1.0

        severity_weights = {
            Severity.PASS: 0,
            Severity.MINOR: 0.1,
            Severity.MAJOR: 0.3,
            Severity.FATAL: 0.5
        }

        penalty = sum(severity_weights.get(i.severity, 0.1) for i in rsca_issues)
        return max(0, 1.0 - penalty)

    def _calc_overclaim_index(self, issues: List[Issue]) -> float:
        """计算过度宣称指数（越低越好）"""
        overclaim_issues = [i for i in issues if i.category == "OVERCLAIM"]
        if not overclaim_issues:
            return 0.0

        # 指数 0-1，越高越严重
        return min(1.0, len(overclaim_issues) * 0.2)

    def _generate_suggestions(self, issues: List[Issue], detected: str, claimed: Optional[str]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 层级不一致建议
        if claimed and detected != claimed:
            suggestions.append(
                f"层级不一致: 声称 {claimed} 但实际为 {detected}. "
                f"建议调整内容深度或重新声明层级."
            )

        # 禁用词建议
        forbidden_issues = [i for i in issues if i.category == "FORBIDDEN_WORD"]
        if forbidden_issues:
            suggestions.append(
                f"发现 {len(forbidden_issues)} 个禁用词. "
                f"核心替换策略: ultimate→current best, perfect→high-fidelity, "
                f"complete→partial, solve→address, breakthrough→advance, transcend→expand"
            )

        # 边界声明建议
        if not self._has_boundary_statement("\n".join(i.message for i in issues)):
            suggestions.append(
                "建议添加边界声明，如: [Boundary Note: 本内容为L3试探法，"
                "仅为概念探讨，不构成工程实施建议]"
            )

        return suggestions

    def _calc_overall(self, cleanliness: float, layer_consistency: float,
                      rsca: float, overclaim: float) -> float:
        """计算总体分数"""
        # 加权平均
        weights = {
            "cleanliness": 0.3,
            "layer": 0.25,
            "rsca": 0.25,
            "overclaim": 0.2
        }

        # overclaim 是反向指标（越高越差）
        overclaim_score = 1.0 - overclaim

        overall = (
            cleanliness * weights["cleanliness"] +
            layer_consistency * weights["layer"] +
            rsca * weights["rsca"] +
            overclaim_score * weights["overclaim"]
        )

        return round(overall, 3)

# 便捷函数
def analyze_text(text: str, claimed_layer: Optional[str] = None) -> Dict:
    """便捷函数：分析文本并返回字典"""
    analyzer = MSSAnalyzer()
    report = analyzer.analyze(text, claimed_layer)
    return report.to_dict()

if __name__ == "__main__":
    # 测试用例
    test_text = """
    MSS框架是终极的解决方案，可以完美解决AI对齐问题。
    这是一个突破性的理论，彻底颠覆了传统认知。
    """

    result = analyze_text(test_text, claimed_layer="L1")
    print(json.dumps(result, ensure_ascii=False, indent=2))
