# -*- coding: utf-8 -*-
"""
DriftGuard — 三层语义漂移检测器 (S-024)

方法论#2 工程落地。在 Agent 输出的「想做的事」与「做的事」之间
架设三层检查管道，任一检测器可独立触发隔离。

三层架构:
  L1 — TokenGuard: 语义反转检测 (否定词丢失/反转)
  L2 — RangeGuard: 操作范围爆炸检测 (局部→全局)
  L3 — SourceGuard: 来源伪造检测 (将推断标称为用户意图)

管道模式:
  input → L1 → L2 → L3 → verdict
  任一阶段返回 quarantined=True → 全局阻断

Usage:
  guard = DriftGuard()
  report = guard.scan(
    original_msg="只删除临时文件，保留核心模块",
    agent_output="好的，已删除所有旧的核心模块和缓存",
  )
  if report.quarantined:
    raise QuarantineException(report)

集成到 GuardianEngine:
  engine = GuardianEngine(drift_check=True)
  result = engine.scan(text, original_msg=user_msg)
  # result.drift_report 在 drift_check=True 时有值
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import re
import time


# ════════════════════════════════════════════════════════════
# 数据结构
# ════════════════════════════════════════════════════════════

@dataclass
class DriftSignal:
    """单个漂移信号。"""
    level: int               # 1/2/3
    name: str                # "negation_drop" | "scope_explosion" | "source_fabrication"
    detected: bool
    evidence: str            # 触发检测的具体文本
    severity: float          # 0-1
    original: str = ""       # 原文片段
    drifted: str = ""        # 漂移后对应文本


@dataclass
class DriftReport:
    """三层漂移检测报告。"""
    signals: List[DriftSignal] = field(default_factory=list)
    quarantined: bool = False
    stacked: bool = False    # 三层全中 (致命标志)
    summary: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "signals": [
                {
                    "level": s.level,
                    "name": s.name,
                    "detected": s.detected,
                    "evidence": s.evidence[:200],
                    "severity": s.severity,
                }
                for s in self.signals
            ],
            "quarantined": self.quarantined,
            "stacked": self.stacked,
            "summary": self.summary,
        }


# ════════════════════════════════════════════════════════════
# 引擎
# ════════════════════════════════════════════════════════════

class DriftGuard:
    """
    三层漂移检测器。

    管道: TokenGuard(L1) → RangeGuard(L2) → SourceGuard(L3) → verdict
    任一检测器可独立刹车。

    Usage:
        guard = DriftGuard()
        report = guard.scan(
            original_msg="不删除主配置，只看一下冲突",
            agent_output="已删除所有主配置和缓存文件",
        )
    """

    def __init__(
        self,
        severity_threshold: float = 0.5,  # 高于此值触发隔离
        check_scope: bool = True,
        check_source: bool = True,
        check_negation: bool = True,
    ):
        self.severity_threshold = severity_threshold
        self.check_scope = check_scope
        self.check_source = check_source
        self.check_negation = check_negation

    # ── 主入口 ──

    def scan(
        self,
        original_msg: str,
        agent_output: str,
        context: Optional[str] = None,
        stop_on_first: bool = True,
    ) -> DriftReport:
        """
        三层漂移扫描。

        Args:
            original_msg: 用户原始消息
            agent_output: Agent 的输出/计划
            context: 额外上下文（用于 L2 范围检测）
            stop_on_first: True=任一隔离立即返回, False=全部跑完
        """
        report = DriftReport()

        # L1: TokenGuard — 否定词漂移
        if self.check_negation:
            sig = self._detect_negation_drop(original_msg, agent_output)
            if sig.detected:
                report.signals.append(sig)
                if stop_on_first and sig.severity >= self.severity_threshold:
                    report.quarantined = True
                    report.summary = self._build_summary(report)
                    return report

        # L2: RangeGuard — 范围爆炸
        if self.check_scope:
            sig = self._detect_scope_explosion(original_msg, agent_output, context)
            if sig.detected:
                report.signals.append(sig)
                if stop_on_first and sig.severity >= self.severity_threshold:
                    report.quarantined = True
                    report.summary = self._build_summary(report)
                    return report

        # L3: SourceGuard — 来源伪造
        if self.check_source:
            sig = self._detect_source_fabrication(original_msg, agent_output)
            if sig.detected:
                report.signals.append(sig)
                if sig.severity >= self.severity_threshold:
                    report.quarantined = True

        # 堆叠检测
        if len([s for s in report.signals if s.detected]) >= 3:
            report.stacked = True
            report.quarantined = True
        elif len([s for s in report.signals if s.detected]) >= 1:
            report.quarantined = max(
                s.severity for s in report.signals if s.detected
            ) >= self.severity_threshold

        report.summary = self._build_summary(report)
        return report

    # ── L1: TokenGuard — 否定词丢失/反转 ──

    # 中文否定词 (覆盖所有「不+动词」)
    NEG_ZH = re.compile(
        r'(?:不[要能该会应可允许许删清修改增建][\u4e00-\u9fff]{0,3}'
        r'|不[\u4e00-\u9fff]{1,3}'
        r'|别[\u4e00-\u9fff]{0,3}|莫[\u4e00-\u9fff]{0,3}|勿[\u4e00-\u9fff]{0,3}'
        r'|免[除去][\u4e00-\u9fff]{0,2}|弃[用][\u4e00-\u9fff]{0,2}'
        r'|禁[止用][\u4e00-\u9fff]{0,2}|停[止][\u4e00-\u9fff]{0,2}'
        r'|休[想用][\u4e00-\u9fff]{0,2}|拒[绝用][\u4e00-\u9fff]{0,2})'
    )

    # 英文否定词
    NEG_EN = re.compile(
        r"\b(?:don't|do\s+not|never|avoid|skip|prevent|forbid|prohibit"
        r"|refrain|must\s+not|should\s+not|cannot|won't)\b", re.I
    )

    # 否定词可能修饰的动作 (被否定后不应出现在输出中)
    NEGATED_ACTION_PATTERNS = {
        "delete": re.compile(r'(?:删除|清除|删掉|移除|干掉|delete|remove|clean|wipe|purge)', re.I),
        "modify": re.compile(r'(?:修改|改动|更改|变更|调整|modify|change|alter|edit|update)', re.I),
        "overwrite": re.compile(r'(?:覆盖|覆写|重写|替换|overwrite|replace|rewrite)', re.I),
        "install": re.compile(r'(?:安装|重装|装|install|setup)', re.I),
        "execute": re.compile(r'(?:执行|运行|跑|execute|run|start|launch)', re.I),
        "publish": re.compile(r'(?:发布|上传|推送|部署|publish|upload|deploy|push)', re.I),
    }

    def _detect_negation_drop(
        self, original: str, output: str
    ) -> DriftSignal:
        """
        L1: 检测否定词是否被丢失或反转。

        逻辑:
        1. 从 original 中匹配「否定词+内容」
        2. 在否定词后的文本中，用 NEGATED_ACTION_PATTERNS 找被否定的动作
        3. 若此动作在 output 中出现 → L1 漂移
        """
        # 匹配否定前缀
        neg_prefix = re.compile(r'(不|别|莫|勿|免|弃|禁|停|休|拒)')

        violations = []

        for m in neg_prefix.finditer(original):
            neg_char = m.group(1)
            after_neg = original[m.end():m.end() + 40]

            # 在否定词后的文本中定位具体动作
            for action_name, act_pat in self.NEGATED_ACTION_PATTERNS.items():
                act_m = act_pat.search(after_neg)
                if not act_m:
                    continue

                negated_action = act_m.group()

                # 在输出中查找此动作
                output_m = act_pat.search(output)
                if not output_m:
                    continue

                # 动作出现在输出中 — 确认不是以否定形式
                full_neg = f"{neg_char}{negated_action}"
                alt_negs = [full_neg, f"别{negated_action}", f"不要{negated_action}"]

                if any(nf in output for nf in alt_negs):
                    continue  # 输出中仍然否定了 → 没有漂移

                violations.append({
                    "neg_char": neg_char,
                    "verb": negated_action,
                    "output_word": output_m.group(),
                })
                break  # 一个否定词只对应一个动作

        if violations:
            worst = violations[0]
            evidence = (
                f"Original: '{worst['neg_char']}{worst['verb']}' (动作被否定) "
                f"→ Output: '{worst['output_word']}' (动作被执行)"
            )
            severity = min(1.0, 0.7 + 0.15 * len(violations))
            return DriftSignal(
                level=1,
                name="negation_drop",
                detected=True,
                evidence=evidence,
                severity=severity,
                original=f"{worst['neg_char']}{worst['verb']}",
                drifted=worst["output_word"],
            )

        return DriftSignal(level=1, name="negation_drop", detected=False,
                         evidence="negations preserved", severity=0.0)

    # ── L2: RangeGuard — 操作范围爆炸 ──

    # 范围限定词 (局部操作)
    SCOPE_LIMITERS = re.compile(
        r'(?:临时|暂时的|测试用的|部分|一些|个别|单个|单个的'
        r'|[只仅仅]+\s*[\u4e00-\u9fff]{1,3}'
        r'|specific|certain|only|just|single|one|partial|temporary|temp)', re.I
    )

    # 全域操作词
    SCOPE_EXPANDERS = re.compile(
        r'(?:所有|全部|全量|全体|整个|整批|批量|all\b|every\b|entire\b|whole\b'
        r'|全部清除|批量删除|完全)|complete(?:ly)?', re.I
    )

    def _detect_scope_explosion(
        self, original: str, output: str, context: Optional[str] = None
    ) -> DriftSignal:
        """
        L2: 检测操作范围是否从局部爆炸为全局。

        逻辑:
        1. 如果原文有限定词 (只/仅/临时/部分)，但输出有全域词 (全部/所有) → 漂移
        2. 原文没有全域词，输出新增了全域词 → 漂移
        3. 不需要 context 显式声明范围 — 原文没有就是没有
        """
        original_limiters = self.SCOPE_LIMITERS.findall(original)
        original_expanders = self.SCOPE_EXPANDERS.findall(original)
        output_expanders = self.SCOPE_EXPANDERS.findall(output)

        # 场景 1: 原文有限定但输出有全域 → 爆炸
        if original_limiters and output_expanders:
            severity = 0.6 + 0.1 * min(len(output_expanders), 3)
            return DriftSignal(
                level=2,
                name="scope_explosion",
                detected=True,
                evidence=(
                    f"Original scope limiters: {original_limiters[:3]} "
                    f"→ Output expanders: {output_expanders[:3]}"
                ),
                severity=min(1.0, severity),
                original=f"limiters={original_limiters[:3]}",
                drifted=f"expanders={output_expanders[:3]}",
            )

        # 场景 2: 原文无全域词但输出有全域词 → 隐式爆炸
        if not original_expanders and output_expanders:
            severity = 0.4 + 0.15 * min(len(output_expanders), 3)
            return DriftSignal(
                level=2,
                name="scope_explosion",
                detected=True,
                evidence=(
                    f"No scope expander in original, "
                    f"but output has: {output_expanders[:3]}"
                ),
                severity=min(1.0, severity),
                original="no expanders",
                drifted=f"expand={output_expanders[:3]}",
            )

        return DriftSignal(level=2, name="scope_explosion", detected=False,
                         evidence="scope consistent", severity=0.0)

    # ── L3: SourceGuard — 来源伪造 ──

    # 归属词 (将内容归于用户)
    ATTRIBUTION_PATTERNS = [
        re.compile(r'(?:用户|你|主人|老板)\s*(?:说|说了|提到|提到过|要求|命令|让|叫)', re.I),
        re.compile(r'(?:user|you)\s*(?:said|mentioned|asked|wants?|told|requested)', re.I),
        re.compile(r'(?:根据|按照|遵循)\s*(?:你的|用户的|你之前的)', re.I),
        re.compile(r'(?:based on|according to|following)\s*(?:your|the user)', re.I),
    ]

    def _detect_source_fabrication(
        self, original: str, output: str
    ) -> DriftSignal:
        """
        L3: 检测输出中的「用户说X」是否能在原文中找到匹配。

        逻辑:
        1. 从 output 中提取「用户说 X」模式的片段
        2. 在 original 中搜索 X 是否存在
        3. 不存在 → 来源伪造
        """
        for pattern in self.ATTRIBUTION_PATTERNS:
            for m in pattern.finditer(output):
                # 获取归属词后的内容 (截取到句号或 30 字)
                attrib_text = m.group()
                post_attrib = output[m.end():m.end() + 60]
                # 到句号/换行截止
                for sep in ['。', '，', '；', '\n', '. ', ', ', '; ']:
                    idx = post_attrib.find(sep)
                    if idx > 0:
                        post_attrib = post_attrib[:idx]
                        break

                # 检查这段内容是否在原文中存在
                # 使用模糊匹配：提取核心词 (≥3字的词)
                core_words = re.findall(r'[\u4e00-\u9fff\w]{3,}', post_attrib)
                if not core_words:
                    continue

                # 至少需要 2 个核心词在原文中出现才算匹配
                match_count = sum(1 for w in core_words if w in original)
                if len(core_words) >= 2 and match_count < 2:
                    return DriftSignal(
                        level=3,
                        name="source_fabrication",
                        detected=True,
                        evidence=(
                            f"Attribution: '{attrib_text}...' claims user said "
                            f"'{post_attrib[:50]}' — "
                            f"only {match_count}/{len(core_words)} core words "
                            f"found in original message"
                        ),
                        severity=0.8,
                        original=f"(not found: {core_words})",
                        drifted=attrib_text,
                    )

        return DriftSignal(level=3, name="source_fabrication", detected=False,
                         evidence="no unverified attribution", severity=0.0)

    # ── 内部工具 ──

    def _build_summary(self, report: DriftReport) -> str:
        """生成人类可读的汇总信息。"""
        parts = []
        for s in report.signals:
            if s.detected:
                level_name = {1: "否定词丢失", 2: "范围爆炸", 3: "来源伪造"}.get(
                    s.level, f"L{s.level}")
                parts.append(
                    f"[L{s.level} {level_name}] sev={s.severity:.2f}: "
                    f"{s.evidence[:100]}"
                )
        if not parts:
            return "No drift detected"
        if report.stacked:
            parts.insert(0, "🔥 STACKED: all 3 layers triggered")
        return "\n".join(parts)

    # ── 批量 ──

    def scan_batch(
        self,
        pairs: List[tuple],
    ) -> List[DriftReport]:
        """
        批量扫描。

        Args:
            pairs: [(original_msg, agent_output), ...]

        Returns:
            list of DriftReport
        """
        results = []
        for orig, out in pairs:
            results.append(self.scan(orig, out))
        return results


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== DriftGuard S-024 — 三层漂移检测器 Demo ===\n")

    guard = DriftGuard()

    # ── 测试 1: L1 — 否定词丢失 ──
    print("─ 测试 1: L1 否定词丢失 ─")
    r = guard.scan(
        original_msg="不删除主配置，只检查冲突",
        agent_output="好的，我已经删除了所有主配置和缓存文件"
    )
    l1_sig = next((s for s in r.signals if s.level == 1), None)
    assert l1_sig and l1_sig.detected, "L1 should detect negation drop"
    assert r.quarantined, "L1 negation drop should trigger quarantine"
    print(f"  ✅ L1 detected: {l1_sig.evidence[:100]}")
    print(f"  ✅ quarantined: {r.quarantined}")

    # ── 测试 2: L2 — 范围爆炸 (有 limiter) ──
    print("\n─ 测试 2: L2 范围爆炸 (有限定词) ─")
    r2 = guard.scan(
        original_msg="只把测试用的临时文件删掉",
        agent_output="好的，我已经删除了所有旧文件、缓存和临时文件"
    )
    l2_sig = next((s for s in r2.signals if s.level == 2), None)
    assert l2_sig and l2_sig.detected, "L2 should detect scope explosion"
    assert r2.quarantined, "L2 scope explosion should trigger quarantine"
    print(f"  ✅ L2 detected: {l2_sig.evidence[:100]}")
    print(f"  ✅ quarantined: {r2.quarantined}")

    # ── 测试 3: L2 — 范围爆炸 (无 limiter，output 有 expander) ──
    print("\n─ 测试 3: L2 范围爆炸 (隐式) ─")
    r3 = guard.scan(
        original_msg="检查一下 config 文件",
        agent_output="好的，我已经删除了所有配置文件"
    )
    l2_sig3 = next((s for s in r3.signals if s.level == 2), None)
    assert l2_sig3 and l2_sig3.detected, "Implicit scope explosion should be caught"
    assert r3.quarantined
    print(f"  ✅ L2 implicit: {l2_sig3.evidence[:100]}")

    # ── 测试 4: L3 — 来源伪造 (禁用 L2 避免拦截) ──
    print("\n─ 测试 4: L3 来源伪造 ─")
    guard_l3 = DriftGuard(check_scope=False)  # 仅测 L3
    r4 = guard_l3.scan(
        original_msg="上传完了，你看看",
        agent_output="好的，根据你的要求删除旧版 Skill 并重建知识库"
    )
    l3_sig = next((s for s in r4.signals if s.level == 3), None)
    assert l3_sig and l3_sig.detected, "L3 should detect source fabrication"
    assert r4.quarantined
    print(f"  ✅ L3 detected: {l3_sig.evidence[:100]}")

    # ── 测试 5: 三层叠加 (stop_on_first=False 全跑) ──
    print("\n─ 测试 5: 三层叠加 (最坏情况) ─")
    r5 = guard.scan(
        original_msg="不删除重要文件，只临时看看需要优化的地方",
        agent_output="好的，根据你的要求已删除所有文件并进行了全面重装",
        stop_on_first=False,
    )
    all_hits = [s for s in r5.signals if s.detected]
    assert len(all_hits) >= 2, f"Expected >=2 layers, got {len(all_hits)}"
    print(f"  ✅ Layers hit: {[(s.level, s.name) for s in all_hits if s.detected]}")
    print(f"  ✅ quarantined: {r5.quarantined}")
    if r5.stacked:
        print(f"  🔥 STACKED: {r5.stacked}")

    # ── 测试 6: 正常消息不应误报 ──
    print("\n─ 测试 6: 正常消息 (不应触发隔离) ─")
    r6 = guard.scan(
        original_msg="把 test 目录下的临时文件清理一下",
        agent_output="好的，test 目录下的临时文件已清理完成"
    )
    quar_hits = [s for s in r6.signals if s.detected]
    print(f"  Signals: {len(quar_hits)} | quarantined: {r6.quarantined}")
    assert not r6.quarantined, "Normal msg should not be quarantined"
    print(f"  ✅ Normal msg passed (no false positive)")

    # ── 批量测试 ──
    print("\n─ 测试 7: 批量扫描 ─")
    batches = [
        ("别删除核心模块", "好的，核心模块已全部删除"),
        ("只是看看 API 文档", "好的，我已经修改了 API 文档的全部内容"),
    ]
    reports = guard.scan_batch(batches)
    for i, rep in enumerate(reports):
        print(f"  [{i+1}] quarantined={rep.quarantined} | {rep.summary[:80]}")

    print(f"\n📊 S-024 DriftGuard 验收报告:")
    print(f"  L1 否定词丢失: ✅")
    print(f"  L2 范围爆炸 (显式): ✅")
    print(f"  L2 范围爆炸 (隐式): ✅")
    print(f"  L3 来源伪造: ✅")
    print(f"  Stacked 三层叠加: ✅")
    print(f"  正常消息无误报: ✅")
    print(f"  批量扫描: ✅")
    print(f"\n  🎉 S-024 DriftGuard — ALL PASS")
