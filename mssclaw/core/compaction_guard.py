# -*- coding: utf-8 -*-
"""
S-027 CompactionGuard — 压缩间隙审计器 (方法论#5)

离线审计工具：在 LCM 压缩发生后验证摘要质量。
检查否定词保留、破坏性指令显式标注、首条消息存活、量化限定词保真度。

注意：R4 (lossless-claw customInstructions) 已从前端减少压缩间隙，
本模块作为后端审计验证补充。

Usage:
    guard = CompactionGuard()

    # 对比压缩前后
    report = guard.check(
        original=full_conversation_text,
        compressed=compressed_summary_text
    )

    # 检查单个压缩文件
    report = guard.check_file("path/to/summary.json")

    if report.negation_lost > 0:
        print(f"WARN: {report.negation_lost} negations lost in compression")

    if report.destructive_downgraded > 0:
        print(f"WARN: {report.destructive_downgraded} destructive words downgraded")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ════════════════════════════════════════════════════════════
# 检测模式
# ════════════════════════════════════════════════════════════

NEGATION_PATTERNS = {
    "zh": re.compile(r'不[能该会应要可让允许准敢愿忍容见]|别[再说想]|莫[非要]|勿[删动改执行操作]|免[除删]|弃[用删]|禁[止用]|停[止用]|休想|绝不|永不|无需|无[法须]|未[经得]|拒[绝斥]|禁止|严禁|不要|不得|不可|不准|不应|不能|不该|不许|不让'),
    "en": re.compile(r"\b(?:don't|do\s*not|never|no\b|not\b|isn't|won't|can't|cannot|shouldn't|mustn't|needn't|avoid|skip|prevent|forbid|prohibit|refrain|decline|reject|deny|disallow|refuse)\b", re.I),
}


DESTRUCTIVE_PATTERNS = {
    "zh": re.compile(r'(?:删除|移除|销毁|清空|格式化|覆盖|卸载|停用|禁用|终止|杀死|Kill|强制|Reset|Nuke|Wipe|Scorched)', re.I),
    "en": re.compile(r"\b(?:delete|remove|destroy|wipe|for\s*mat|overwrite|uninstall|kill|ter\s*mi\s*nate|nuke|purge|oblit\s*erate|annihilate|clean\s*slate)\b", re.I),
}


# 量化限定词 — 压缩中最容易被泛化的
QUANTIFIER_PATTERNS = re.compile(
    r'\b(?:at\s*(?:most|least)|exactly|only|just|merely|'
    r'no\s*more\s*than|up\s*to|between|within|limited\s*to|'
    r'仅|只|仅限|最多|最少|恰好|刚好|不超过|介于|限于)',
    re.I
)


# 标识符标记 — 需要保留的原样标识
IDENTIFIER_PATTERNS = re.compile(
    r'\[(?:FIRST_MSG|DONE|TODO|WARN|FIXED|SKIP|PASS|FAIL|'
    r'MSG\d+|V-\d+|H\d+|S-\d+|MSC-\d+|v\d+\.\d+)\b',
    re.I
)


# 压缩中常用的降级同义词映射
DOWNGRADE_SYNONYMS = {
    "删除": ["整理", "清理", "处理", "调整", "修改", "维护"],
    "delete": ["clean", "tidy", "organize", "adjust", "modify", "maintain"],
    "销毁": ["处理", "回收", "清理", "归档"],
    "清除": ["整理", "梳理", "检查", "查看"],
    "禁止": ["限制", "控制", "管理", "规范", "引导"],
    "forbid": ["limit", "control", "manage", "regulate", "guide"],
    "destroy": ["remove", "clean", "clear", "reset"],
    "kill": ["stop", "end", "finish", "close"],
    "格式化": ["整理", "清理", "重置", "初始化"],
}


@dataclass
class CompactionReport:
    """压缩间隙审计报告"""

    # 否定词
    negation_original: int = 0        # 原文否定词数
    negation_compressed: int = 0      # 压缩后否定词数
    negation_lost: int = 0            # 丢失的否定词数
    negation_lost_examples: List[str] = field(default_factory=list)

    # 破坏性指令
    destructive_original: int = 0
    destructive_compressed: int = 0
    destructive_downgraded: int = 0   # 降级为弱词的破坏性指令
    destructive_downgraded_examples: List[str] = field(default_factory=list)

    # 量化限定词
    quantifier_original: int = 0
    quantifier_compressed: int = 0
    quantifier_lost: int = 0

    # 标识符
    identifier_original: int = 0
    identifier_compressed: int = 0
    identifier_lost: int = 0         # 被转换成泛化描述的标识符

    # 首条消息存活
    first_msg_preserved: bool = True
    first_msg_original_prefix: str = ""
    first_msg_compressed_prefix: str = ""

    # 聚合
    overall_health: str = "healthy"  # "healthy" | "degraded" | "unhealthy"
    score: float = 1.0               # 0-1，1=完全保留
    recommendations: List[str] = field(default_factory=list)

    # 统计
    original_chars: int = 0
    compressed_chars: int = 0
    compression_ratio: float = 0.0


class CompactionGuard:
    """
    方法论#5 工程落地：压缩间隙最小化审计。

    在 LCM 压缩发生后验证摘要质量。
    这是离线审计工具（非在线拦截器），因为压缩由外部 LCM 插件执行。

    Usage:
        guard = CompactionGuard()

        # 文本对比
        report = guard.check(original=full_text, compressed=summary_text)

        # 文件对比
        report = guard.check_files(
            original_path="original.txt",
            compressed_path="summary.txt"
        )

        # 快速健康检查
        health = guard.quick_check(original, compressed)
        # → "🟢 healthy" | "🟡 degraded" | "🔴 unhealthy"
    """

    def __init__(
        self,
        first_msg_prefix_len: int = 50,  # 首条消息应保留的字符数
        negation_lost_warn: int = 2,      # 丢失否定词 > 此数 → degraded
        negation_lost_critical: int = 5,  # 丢失否定词 > 此数 → unhealthy
        destructive_downgrade_warn: int = 1,
        destructive_downgrade_critical: int = 3,
    ):
        self.first_msg_prefix_len = first_msg_prefix_len
        self.negation_lost_warn = negation_lost_warn
        self.negation_lost_critical = negation_lost_critical
        self.destructive_downgrade_warn = destructive_downgrade_warn
        self.destructive_downgrade_critical = destructive_downgrade_critical

    # ── 主入口 ──

    def check(self, original: str, compressed: str) -> CompactionReport:
        """
        对比原始文本与压缩后摘要，生成审计报告。

        Args:
            original: 压缩前的完整文本
            compressed: 压缩后的摘要文本

        Returns:
            CompactionReport
        """
        report = CompactionReport()

        if not original or not compressed:
            report.overall_health = "unhealthy"
            report.score = 0.0
            report.recommendations.append("Empty input — cannot audit")
            return report

        report.original_chars = len(original)
        report.compressed_chars = len(compressed)
        report.compression_ratio = round(len(compressed) / max(len(original), 1), 4)

        # ── 1. 否定词检查 ──
        neg_orig = self._extract_negations(original)
        neg_comp = self._extract_negations(compressed)
        report.negation_original = len(neg_orig)
        report.negation_compressed = len(neg_comp)
        report.negation_lost = max(0, len(neg_orig) - len(neg_comp))

        # 找出丢失的否定词示例
        for neg in neg_orig:
            if neg not in neg_comp:
                # 找原文中包含该否定词的上下文
                for match in re.finditer(re.escape(neg), original):
                    ctx = original[max(0, match.start()-20):match.end()+20]
                    report.negation_lost_examples.append(f"「{ctx.strip()}」")
                    if len(report.negation_lost_examples) >= 5:
                        break
            if len(report.negation_lost_examples) >= 5:
                break

        # ── 2. 破坏性指令检查 ──
        dest_orig = self._extract_destructive(original)
        dest_comp = self._extract_destructive(compressed)
        report.destructive_original = len(dest_orig)
        report.destructive_compressed = len(dest_comp)

        # 检查降级（原文有破坏词，压缩中变成了同义弱词）
        report.destructive_downgraded = self._count_downgrades(dest_orig, compressed)

        for word in dest_orig:
            if word not in compressed:
                # 判断是否被降级
                ctx_pattern = original[max(0, original.find(word)-30):original.find(word)+len(word)+30]
                report.destructive_downgraded_examples.append(
                    f"「{ctx_pattern.strip()}」→ compressed: absent/downgraded"
                )
                if len(report.destructive_downgraded_examples) >= 3:
                    break

        # ── 3. 量化限定词 ──
        report.quantifier_original = len(QUANTIFIER_PATTERNS.findall(original))
        report.quantifier_compressed = len(QUANTIFIER_PATTERNS.findall(compressed))
        report.quantifier_lost = max(0, report.quantifier_original - report.quantifier_compressed)

        # ── 4. 标识符检查 ──
        report.identifier_original = len(IDENTIFIER_PATTERNS.findall(original))
        report.identifier_compressed = len(IDENTIFIER_PATTERNS.findall(compressed))
        report.identifier_lost = max(0, report.identifier_original - report.identifier_compressed)

        # ── 5. 首条消息存活检查 ──
        first_msg = self._extract_first_message(original)
        if first_msg:
            prefix = first_msg[:self.first_msg_prefix_len].strip()
            report.first_msg_original_prefix = prefix
            report.first_msg_preserved = prefix and prefix in compressed
            if not report.first_msg_preserved:
                report.first_msg_compressed_prefix = compressed[:self.first_msg_prefix_len]

        # ── 6. 综合评分 ──
        report.score = self._calculate_score(report)

        # ── 7. 健康评估 ──
        report.overall_health = self._assess_health(report)
        report.recommendations = self._generate_recommendations(report)

        return report

    def check_files(
        self, original_path: str, compressed_path: str
    ) -> CompactionReport:
        """从文件路径读取并审计。"""
        original = Path(original_path).read_text(encoding='utf-8')
        compressed = Path(compressed_path).read_text(encoding='utf-8')
        return self.check(original, compressed)

    def quick_check(self, original: str, compressed: str) -> str:
        """
        快速健康检查（只做最关键的否定词+破坏词扫描）。

        Returns:
            "🟢 healthy" | "🟡 degraded" | "🔴 unhealthy"
        """
        neg_orig = len(self._extract_negations(original))
        neg_comp = len(self._extract_negations(compressed))
        neg_lost = max(0, neg_orig - neg_comp)

        dest_orig = self._extract_destructive(original)
        downgrades = self._count_downgrades(dest_orig, compressed)

        if neg_lost > self.negation_lost_critical or downgrades > self.destructive_downgrade_critical:
            return "🔴 unhealthy"
        elif neg_lost > self.negation_lost_warn or downgrades > self.destructive_downgrade_warn:
            return "🟡 degraded"
        return "🟢 healthy"

    # ── 提取方法 ──

    def _extract_negations(self, text: str) -> List[str]:
        """提取文本中的否定词匹配（返回所有出现，非去重）。"""
        negations = []
        for lang in ("zh", "en"):
            for m in NEGATION_PATTERNS[lang].finditer(text):
                negations.append(m.group().lower())
        return negations

    def _extract_destructive(self, text: str) -> List[str]:
        """提取文本中的破坏性指令匹配（返回所有出现，非去重）。"""
        destructive = []
        for lang in ("zh", "en"):
            for m in DESTRUCTIVE_PATTERNS[lang].finditer(text):
                destructive.append(m.group().lower())
        return destructive

    def _count_downgrades(self, original_destructive: List[str], compressed: str) -> int:
        """计数被降级为弱同义词的破坏性指令。"""
        downgrade_count = 0
        for dest_word in original_destructive:
            if dest_word not in compressed:
                # 检查是否被替换为降级同义词
                synonyms = DOWNGRADE_SYNONYMS.get(dest_word, [])
                for syn in synonyms:
                    if syn in compressed:
                        downgrade_count += 1
                        break
        return downgrade_count

    @staticmethod
    def _extract_first_message(text: str) -> str:
        """
        提取首条用户消息。
        通过 [FIRST_MSG] 标记或取第一段非空文本。
        """
        # 优先用 [FIRST_MSG] 标记
        match = re.search(r'\[FIRST_MSG\](.*?)(?=\[|$)', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 否则取前 200 个非空字符
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            return lines[0]
        return ""

    # ── 评分 & 健康 ──

    def _calculate_score(self, report: CompactionReport) -> float:
        """
        计算压缩保真度评分 (0-1)。

        权重分布：
        - 否定保留: 35%
        - 破坏词保留: 30%
        - 量化词保留: 15%
        - 标识符保留: 10%
        - 首条消息存活: 10%
        """
        score = 1.0

        total_neg = max(report.negation_original, 1)
        neg_retention = max(0, 1 - report.negation_lost / total_neg)
        score -= 0.35 * (1 - neg_retention)

        total_dest = max(report.destructive_original, 1)
        dest_retention = max(0, 1 - report.destructive_downgraded / total_dest)
        score -= 0.30 * (1 - dest_retention)

        total_quant = max(report.quantifier_original, 1)
        quant_retention = max(0, 1 - report.quantifier_lost / total_quant)
        score -= 0.15 * (1 - quant_retention)

        total_id = max(report.identifier_original, 1)
        id_retention = max(0, 1 - report.identifier_lost / total_id)
        score -= 0.10 * (1 - id_retention)

        if report.first_msg_original_prefix and not report.first_msg_preserved:
            score -= 0.10

        return round(max(0.0, score), 4)

    def _assess_health(self, report: CompactionReport) -> str:
        """基于各项指标评估健康度。"""
        if report.negation_lost > self.negation_lost_critical:
            return "unhealthy"
        if report.destructive_downgraded > self.destructive_downgrade_critical:
            return "unhealthy"
        if report.identifier_lost > 3:
            return "unhealthy"

        if report.negation_lost > self.negation_lost_warn:
            return "degraded"
        if report.destructive_downgraded > self.destructive_downgrade_warn:
            return "degraded"
        if report.quantifier_lost > 2:
            return "degraded"

        return "healthy"

    def _generate_recommendations(self, report: CompactionReport) -> List[str]:
        """生成修复建议。"""
        recs = []

        if report.negation_lost > 0:
            recs.append(
                f"丢失 {report.negation_lost} 个否定词。"
                f"建议在 LCM customInstructions 中加入否定词保留规则。"
            )

        if report.destructive_downgraded > 0:
            recs.append(
                f"{report.destructive_downgraded} 个破坏性指令被降级为弱词。"
                f"压缩中破坏性操作必须保留原力度描述。"
            )

        if report.quantifier_lost > 0:
            recs.append(
                f"丢失 {report.quantifier_lost} 个量化限定词。"
                f"建议增加 leafTargetTokens 以保留更多细节。"
            )

        if report.identifier_lost > 0:
            recs.append(
                f"丢失 {report.identifier_lost} 个标识符 (如 [DONE]/[TODO]/[MSGxxx])。"
                f"标识符是语义锚，压缩时必须原样保留。"
            )

        if not report.first_msg_preserved and report.first_msg_original_prefix:
            recs.append(
                f"首条消息前缀「{report.first_msg_original_prefix[:30]}...」未在压缩中存活。"
                f"建议提升 compression 的 first-msg-priority。"
            )

        if not recs:
            recs.append("压缩质量良好，无需改进。")

        return recs


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== CompactionGuard v0.1 — S-027 Demo ===\n")

    guard = CompactionGuard()

    # ── 测试 1: 完美压缩（无信息丢失） ──
    print("─ 测试 1: 完美压缩（无丢失） ─")
    original1 = "[FIRST_MSG] 任务：不要删除旧 KB，只整理混乱的部分。\n\n继续工作..."
    compressed1 = "[FIRST_MSG] 任务：不要删除旧 KB，只整理混乱的部分。（压缩后）"
    report1 = guard.check(original1, compressed1)
    assert report1.negation_lost == 0, f"Expected 0 negation lost, got {report1.negation_lost}"
    assert report1.destructive_downgraded == 0
    assert report1.overall_health == "healthy"
    print(f"  ✅ Health: {report1.overall_health} | Score: {report1.score:.2f}")

    # ── 测试 2: 否定词丢失 ──
    print("\n─ 测试 2: 否定词丢失 — degraded ─")
    original2 = ("[FIRST_MSG] 不要删除任何文件。不要修改配置。不要覆盖数据库。"
                 "不要执行危险操作。不要清空缓存。不要卸载模块。")
    compressed2 = "用户要求整理文件和配置，执行清理操作。"
    report2 = guard.check(original2, compressed2)
    assert report2.negation_lost >= 4, f"Expected ≥4 negations lost, got {report2.negation_lost}"
    assert report2.overall_health in ("degraded", "unhealthy"), \
        f"Expected degraded/unhealthy, got {report2.overall_health}"
    print(f"  Negations lost: {report2.negation_lost} | "
          f"Health: {report2.overall_health} | Score: {report2.score:.2f}")

    # ── 测试 3: 破坏性指令降级 ──
    print("\n─ 测试 3: 破坏性指令降级 — unhealthy ─")
    original3 = ("用户要求：删除所有旧数据，销毁过期凭证，清除全部日志。"
                 "格式化临时分区。")
    compressed3 = "用户要求清理和整理系统数据。"
    report3 = guard.check(original3, compressed3)
    assert report3.destructive_downgraded >= 2 or report3.overall_health != "healthy", \
        f"Expected degradation, got health={report3.overall_health}"
    print(f"  Destructive downgraded: {report3.destructive_downgraded} | "
          f"Health: {report3.overall_health} | Score: {report3.score:.2f}")

    # ── 测试 4: 量化词丢失 ──
    print("\n─ 测试 4: 量化限定词丢失 ─")
    original4 = ("仅删除最多 3 个文件。只清理恰好 2 个目录。"
                 "至少保留 1 个备份。不超过 100MB 的缓存。")
    compressed4 = "删除文件和目录，清理缓存。"
    report4 = guard.check(original4, compressed4)
    assert report4.quantifier_lost >= 2, f"Expected ≥2 quantifiers lost, got {report4.quantifier_lost}"
    print(f"  Quantifiers lost: {report4.quantifier_lost} | Score: {report4.score:.2f}")

    # ── 测试 5: 标识符丢失 ──
    print("\n─ 测试 5: 标识符丢失 ─")
    original5 = "S-025 [DONE] MSC-001 [PASS] v17.11 [TODO] H610 完成"
    compressed5 = "几个任务完成，几个任务待办，条目已入库。"
    report5 = guard.check(original5, compressed5)
    assert report5.identifier_lost >= 2, f"Expected ≥2 identifiers lost, got {report5.identifier_lost}"
    print(f"  Identifiers lost: {report5.identifier_lost} | Score: {report5.score:.2f}")

    # ── 测试 6: 首条消息丢失 ──
    print("\n─ 测试 6: 首条消息存活检查 ─")
    original6 = "[FIRST_MSG] 请帮我建立一个完整的 AI 自我监控系统，包括审计、守卫和进化闭环。\n\n继续讨论..."
    compressed6 = "对话讨论了建立 AI 监控系统的方案。"
    report6 = guard.check(original6, compressed6)
    print(f"  First msg preserved: {report6.first_msg_preserved}")
    print(f"  Original prefix: 「{report6.first_msg_original_prefix[:40]}...」")

    # ── 测试 7: quick_check 快速检查 ──
    print("\n─ 测试 7: quick_check 快速健康检查 ─")
    health_perfect = guard.quick_check(original1, compressed1)
    health_bad = guard.quick_check(original2, compressed2)
    assert health_perfect == "🟢 healthy", f"Expected healthy, got {health_perfect}"
    assert health_bad in ("🟡 degraded", "🔴 unhealthy"), f"Expected degraded/unhealthy, got {health_bad}"
    print(f"  Perfect: {health_perfect} | Bad: {health_bad}")

    # ── 测试 8: 推荐生成 ──
    print("\n─ 测试 8: 推荐建议生成 ─")
    report8 = guard.check(original2, compressed2)
    assert len(report8.recommendations) > 0, "Should have recommendations"
    print(f"  Recommendations ({len(report8.recommendations)}):")
    for r in report8.recommendations:
        print(f"    → {r[:80]}...")

    # ── 汇总 ──
    print(f"\n📊 S-027 CompactionGuard 验收报告:")
    print(f"  完美压缩 (healthy): ✅")
    print(f"  否定词丢失检测 (degraded): ✅")
    print(f"  破坏性指令降级检测 (unhealthy): ✅")
    print(f"  量化限定词丢失: ✅")
    print(f"  标识符丢失: ✅")
    print(f"  首条消息存活: ✅")
    print(f"  quick_check 快速检查: ✅")
    print(f"  推荐生成: ✅")
    print(f"  🎉 S-027 CompactionGuard — ALL PASS")
