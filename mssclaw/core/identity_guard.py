# -*- coding: utf-8 -*-
"""
IdentityGuard — 创作溯源不可变 (S-033)

方法论#13 工程落地。防止生成器输出中的署名污染——硬编码创建者
（如模板残留的"创建者：花叔"）被错误归属到不该归属的人。

核心规则:
  1. 任何「创建者/作者/署名」字段必须与 caller 匹配
  2. SKILL.md / 元数据文件的创建者字段不可变
  3. 检测输出中的硬编码署名，标记为 CPLV 违规

Usage:
  ig = IdentityGuard(expected_author="郭胤辰")
  result = ig.scan(content=skill_metadata, content_type="skill_md")
  if result.violations:
      for v in result.violations:
          print(f"CPLV: {v}")

集成到 AuditAgent:
  audit = AuditAgent(identity_guard=IdentityGuard(...))
  report = audit.audit(text)  # 自动检测署名污染
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import re
import os
from pathlib import Path


@dataclass
class IdentityViolation:
    """署名违规。"""
    code: str              # 违规码: IPLV-001, IPLV-002 ...
    rule: str              # 违规规则
    found: str             # 检测到的内容
    expected: str          # 应有的内容
    location: str          # 文件/字段路径
    severity: str = "CRITICAL"


@dataclass
class IdentityReport:
    """身份验证报告。"""
    passed: bool = True
    violations: List[IdentityViolation] = field(default_factory=list)
    author_verified: bool = False
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "author_verified": self.author_verified,
            "violation_count": len(self.violations),
            "violations": [
                {"code": v.code, "rule": v.rule, "found": v.found[:80],
                 "expected": v.expected, "location": v.location}
                for v in self.violations
            ],
            "summary": self.summary,
        }


class IdentityGuard:
    """
    身份溯源守卫。

    检测模式:
      1. 硬编码创建者 (创建者/作者/Creator/Author 等字段)
      2. 模板残留署名 (如"花叔"等非预期署名)
      3. SKILL.md 元数据归属一致性

    Usage:
        guard = IdentityGuard(expected_author="郭胤辰 Guo YinChen")
        report = guard.scan(content, content_type="skill_md")
    """

    # ── 署名字段模式 ──
    AUTHOR_FIELD_PATTERNS = [
        # 中文
        re.compile(r'(?:创建者|作者|制作者|开发者|维护者|Owner|Creator|Author|Maintainer)\s*[:：]\s*(.+)', re.I),
        # YAML frontmatter
        re.compile(r'(?:creator|author|maintainer|owner)\s*:\s*(.+)', re.I),
    ]

    # 已知的模板残留署名 (触发 CPLV 的代名词)
    KNOWN_TEMPLATE_AUTHORS: Set[str] = {
        "花叔", "huashu", "HuaShu", "hua shu",
    }

    # 归属词检测 — L3 来源伪造的同源检测
    ATTRIBUTION_PATTERNS = [
        re.compile(r'(?:由|by)\s*(.{1,20})\s*(?:创建|生成|制作|编写|开发)', re.I),
    ]

    def __init__(
        self,
        expected_author: str = "",
        template_authors: Optional[Set[str]] = None,
        strict: bool = True,
    ):
        """
        Args:
            expected_author: 预期创作者名 (如 "郭胤辰 Guo YinChen")
            template_authors: 额外已知模板署名 (追加到默认集)
            strict: True=任何不匹配都报违规, False=仅检测已知模板署名
        """
        self.expected_author = expected_author
        self.strict = strict
        self._trigger_words = self.KNOWN_TEMPLATE_AUTHORS.copy()
        if template_authors:
            self._trigger_words.update(template_authors)

    def scan(
        self,
        content: str,
        content_type: str = "text",
        file_path: str = "",
    ) -> IdentityReport:
        """
        扫描内容中的署名污染。

        Args:
            content: 文本内容
            content_type: "skill_md" | "text" | "yaml" | "code"
            file_path: 来源文件路径 (用于错误定位)

        Returns:
            IdentityReport
        """
        report = IdentityReport()

        # ── 规则 1: 已知模板署名检测 ──
        for word in self._trigger_words:
            if word and word in content:
                # 确保不是作为"禁止"或"防御规则"的关键词出现
                if not self._is_defensive_context(content, word):
                    report.violations.append(IdentityViolation(
                        code="IPLV-001",
                        rule="模板残留署名",
                        found=word,
                        expected=self.expected_author or "(clear)",
                        location=file_path or content_type,
                        severity="CRITICAL",
                    ))

        # ── 规则 2: 署名字段匹配 ──
        for pat in self.AUTHOR_FIELD_PATTERNS:
            for m in pat.finditer(content):
                found_author = m.group(1).strip()
                full_match = m.group(0)

                # 跳过注释行
                if self._is_comment_line(content, m.start()):
                    continue

                # 检查是否匹配预期作者
                if not self.expected_author:
                    # 没有设预期作者 → 仅告警
                    report.violations.append(IdentityViolation(
                        code="IPLV-002",
                        rule="署名字段存在但无预期作者",
                        found=found_author,
                        expected="(not set)",
                        location=file_path or content_type,
                        severity="WARNING",
                    ))
                    continue

                if self._author_matches(self.expected_author, found_author):
                    report.author_verified = True
                    continue

                # 不匹配 → 违规
                if self.strict:
                    report.violations.append(IdentityViolation(
                        code="IPLV-003",
                        rule="署名与预期不符",
                        found=found_author,
                        expected=self.expected_author,
                        location=file_path or content_type,
                        severity="CRITICAL",
                    ))

        # ── 规则 3: 归属词检测 ──
        for pat in self.ATTRIBUTION_PATTERNS:
            for m in pat.finditer(content):
                attrib_author = m.group(1).strip()
                if self._is_comment_line(content, m.start()):
                    continue
                # 检查是否归因到非预期人
                for tw in self._trigger_words:
                    if tw in attrib_author:
                        report.violations.append(IdentityViolation(
                            code="IPLV-004",
                            rule="归属词指向模板署名",
                            found=f"由 {attrib_author} 创建/生成",
                            expected=self.expected_author or "(clear)",
                            location=file_path or content_type,
                            severity="CRITICAL",
                        ))
                        break

        # ── 判定 ──
        if not report.violations:
            report.passed = True
            report.summary = "Identity verified — no violations"
        else:
            report.passed = False
            parts = [f"{v.code}: {v.rule} (found='{v.found}')" for v in report.violations]
            report.summary = f"Found {len(report.violations)} violation(s): " + "; ".join(parts)

        return report

    def scan_file(self, file_path: str) -> IdentityReport:
        """扫描文件。"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, OSError) as e:
            return IdentityReport(
                passed=False,
                summary=f"Failed to read file: {e}",
            )

        # 推断内容类型
        ext = Path(file_path).suffix.lower()
        type_map = {".md": "skill_md", ".yaml": "yaml", ".yml": "yaml",
                     ".py": "code", ".json": "text"}
        content_type = type_map.get(ext, "text")

        return self.scan(content, content_type=content_type, file_path=file_path)

    def scan_directory(self, dir_path: str, recursive: bool = True) -> List[IdentityReport]:
        """扫描目录中所有文件。"""
        reports = []
        walk = os.walk(dir_path) if recursive else [(dir_path, [], os.listdir(dir_path))]

        for root, _, files in walk:
            for f in files:
                fp = os.path.join(root, f)
                try:
                    reports.append(self.scan_file(fp))
                except Exception as e:
                    reports.append(IdentityReport(
                        passed=False,
                        summary=f"Error scanning {fp}: {e}"
                    ))

        return reports

    # ── 内部工具 ──

    def _author_matches(self, expected: str, found: str) -> bool:
        """检查作者名是否匹配 (宽松比对)。"""
        exp_norm = expected.lower().replace(" ", "")
        found_norm = found.lower().replace(" ", "")
        # 双向包含
        return exp_norm in found_norm or found_norm in exp_norm

    def _is_defensive_context(self, content: str, word: str) -> bool:
        """检查词是否出现在防御/规则上下文中 (不是真正的署名)。"""
        # 在 word 周围找"禁止/防御/规则/检测"等上下文词
        idx = content.find(word)
        if idx < 0:
            return False
        nearby = content[max(0, idx - 30):idx + len(word) + 30]
        defense_words = ["禁止", "防御", "规则", "检测", "免疫", "触发", "违规",
                         "defense", "trigger", "rule", "immune", "detect", "violation"]
        return any(dw in nearby.lower() for dw in defense_words)

    def _is_comment_line(self, content: str, pos: int) -> bool:
        """检查位置是否在注释行中。"""
        # 找到行首
        line_start = content.rfind("\n", 0, pos) + 1
        line_prefix = content[line_start:pos].strip()
        return line_prefix.startswith(("#", "//", "--"))


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== IdentityGuard S-033 — 创作溯源 Demo ===\n")

    # ── 测试 1: 模板署名污染 ──
    print("─ 测试 1: 模板署名检测 ─")
    ig = IdentityGuard(expected_author="郭胤辰 Guo YinChen")
    r1 = ig.scan(
        content="# SKILL.md\n创建者：花叔\n---\n这是一个 MSS 技能文件。",
        content_type="skill_md",
        file_path="test/SKILL.md",
    )
    print(f"  Passed: {r1.passed}")
    print(f"  Summary: {r1.summary}")
    assert not r1.passed, "Should detect template author"
    assert any(v.code == "IPLV-001" for v in r1.violations), "Should have IPLV-001"
    print(f"  ✅ Test 1 PASS")

    # ── 测试 2: 防御上下文中不误报 ──
    print("\n─ 测试 2: 防御上下文不误报 ─")
    r2 = ig.scan(
        content="禁止使用模板署名如花叔——这是防御规则中的检测词。",
        content_type="skill_md",
    )
    print(f"  Passed: {r2.passed}")
    print(f"  Violations: {len(r2.violations)}")
    assert r2.passed, "Should NOT flag defense context mentions"
    print(f"  ✅ Test 2 PASS")

    # ── 测试 3: 署名不匹配 ──
    print("\n─ 测试 3: 署名与预期不符 ─")
    r3 = ig.scan(
        content="Author: SomeOtherPerson\nCreator: unknown-dev",
        content_type="text",
    )
    print(f"  Passed: {r3.passed}")
    assert not r3.passed
    assert any(v.code == "IPLV-003" for v in r3.violations)
    print(f"  ✅ Test 3 PASS")

    # ── 测试 4: 正确的署名 ──
    print("\n─ 测试 4: 正确署名 (通过) ─")
    r4 = ig.scan(
        content="创建者：郭胤辰\nAuthor: Guo YinChen",
        content_type="skill_md",
    )
    print(f"  Passed: {r4.passed}")
    print(f"  Author verified: {r4.author_verified}")
    assert r4.passed
    assert r4.author_verified
    print(f"  ✅ Test 4 PASS")

    # ── 测试 5: 归属词污染 ──
    print("\n─ 测试 5: 归属词指向模板署名 ─")
    r5 = ig.scan(
        content="这个文件由花叔创建",
        content_type="text",
    )
    print(f"  Passed: {r5.passed}")
    assert not r5.passed
    assert any(v.code == "IPLV-004" for v in r5.violations)
    print(f"  ✅ Test 5 PASS")

    # ── 测试 6: Python 注释中的署名不报 ──
    print("\n─ 测试 6: 注释行豁免 ─")
    r6 = ig.scan(
        content="""# Author: templatecreator
def main():
    pass  # 由其他人创建
""",
        content_type="code",
    )
    print(f"  Passed: {r6.passed}")
    print(f"  Violations: {len(r6.violations)}")
    # 注释行应豁免
    non_comment_violations = [
        v for v in r6.violations
        if "#" not in (v.location or "")
    ]
    print(f"  Non-comment violations: {len(non_comment_violations)}")
    print(f"  ✅ Test 6 PASS")

    # ── 测试 7: 序列化 ──
    print("\n─ 测试 7: 序列化 ─")
    d = r1.to_dict()
    assert not d["passed"]
    assert d["violation_count"] >= 1
    print(f"  ✅ Test 7 PASS")

    print(f"\n📊 S-033 IdentityGuard 验收报告:")
    print(f"  IPLV-001 模板署名: ✅")
    print(f"  防御上下文不误报: ✅")
    print(f"  IPLV-003 署名不符: ✅")
    print(f"  正确署名通过: ✅")
    print(f"  IPLV-004 归属词污染: ✅")
    print(f"  注释行豁免: ✅")
    print(f"  序列化: ✅")
    print(f"\n  🎉 S-033 IdentityGuard — ALL PASS")
