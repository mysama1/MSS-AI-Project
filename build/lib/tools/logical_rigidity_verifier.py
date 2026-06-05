#!/usr/bin/env python3
"""
D5-043: MSS 逻辑刚性验证模块 v1.0
验证 MSS 知识库/代码中每条主张的公理锚定性、内部一致性、跨层自洽
"""
import os, json, re, ast
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Set
from enum import Enum

# ===== MSS公理体系 v15.1 =====
MSS_AXIOMS = {
    "A1": "Primacy of Meaning — 宇宙终极现实是连续全息无限维意义场",
    "A2": "Informational Slicing — 物理现实是意义场通过感知壳的投影切片",
    "A3": "Irreducible Thermal Tax — 意义显化必须支付不可逆热税 dQ/dt = κ(∇φ)²",
    "A4": "Intrinsic Randomness — 封闭系统演化含不可消随机涨落 Q = E[∫κ(∇δφ)²dt]",
    "A5": "Normative Field — 自组织意义系统自发形成规范场约束涨落",
    "A6": "Paradoxical Transcendence — 矛盾只能通过升维到更高拓扑维度消解",
}

MSS_LAYERS = ["L0", "L1", "L2", "L3", "L4", "L5"]
LAYER_ANCHOR = {
    "L0": ["A1"],
    "L1": ["A1", "A2", "A3", "A4", "A5", "A6"],
    "L2": ["A2", "A3", "A5"],
    "L3": ["A3", "A4"],
    "L4": ["A5", "A6"],
    "L5": ["A6"],
}

class VerificationLevel(Enum):
    RIGID = "RIGID"           # 完全公理锚定
    TENSEGRITY = "TENSEGRITY"  # 张拉整体（跨层自洽）
    SOFT = "SOFT"             # 柔性连接（可接受推理跳跃）
    UNANCHORED = "UNANCHORED" # 无锚定（逻辑刚性漏洞）
    CONTRADICTORY = "CONTRADICTORY" # 自相矛盾

class Severity(Enum):
    P0 = "P0"  # 逻辑刚性漏洞
    P1 = "P1"  # 柔性连接需加固
    P2 = "P2"  # 风格/文档问题

@dataclass
class RigidityFinding:
    level: Severity
    line: int
    claim: str
    expected_axiom: str
    actual_anchoring: str
    verdict: VerificationLevel
    fix: str

@dataclass
class RigidityReport:
    target: str
    total_claims: int = 0
    rigid: int = 0
    tensegrity: int = 0
    soft: int = 0
    unanchored: int = 0
    contradictory: int = 0
    findings: List[RigidityFinding] = field(default_factory=list)
    score: float = 100.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def compute_score(self):
        if self.total_claims == 0:
            self.score = 100
            return
        p0 = sum(1 for f in self.findings if f.level == Severity.P0)
        p1 = sum(1 for f in self.findings if f.level == Severity.P1)
        self.score = max(0, 100 - p0 * 15 - p1 * 5)
        self.score = round(self.score, 1)
        self.rigid = sum(1 for f in self.findings if f.verdict == VerificationLevel.RIGID)
        self.tensegrity = sum(1 for f in self.findings if f.verdict == VerificationLevel.TENSEGRITY)
        self.soft = sum(1 for f in self.findings if f.verdict == VerificationLevel.SOFT)
        self.unanchored = sum(1 for f in self.findings if f.verdict == VerificationLevel.UNANCHORED)
        self.contradictory = sum(1 for f in self.findings if f.verdict == VerificationLevel.CONTRADICTORY)


class LogicalRigidityVerifier:
    """MSS 逻辑刚性验证器 — 扫描文本中的主张并进行公理锚定验证"""

    # 主张检测模式
    CLAIM_PATTERNS = [
        r'(?:因此|所以|故|thus|therefore|hence)\b',     # 结论性主张
        r'(?:必须|must|shall|required)\b',              # 规范性主张
        r'(?:证明|prove|demonstrate|show that)\b',       # 证明性主张
        r'(?:定义|define|definition)\b',                 # 定义性主张
        r'(?:公理|axiom)\b',                              # 公理性主张
        r'(?:定理|theorem|lemma|corollary)\b',            # 定理
        r'(?:假设|assume|hypothesize)\b',                 # 假设
        r'(?:推论|corollary|imply|implies)\b',            # 推论
        r'(?:≡|:=|=)',                                   # 等式定义
    ]

    # 公理锚定词库
    AXIOM_KEYWORDS = {
        "A1": ["意义场", "meaning field", "意义优先", "meaning primacy", "holographic",
               "全息", "无限维", "infinite-dimensional", "终极实在", "ultimate reality"],
        "A2": ["感知壳", "perception shell", "投影切片", "projective slice", "观察者",
               "observer", "informational slicing", "信息切片", "信息边界"],
        "A3": ["热税", "thermal tax", "heat tax", "不可逆", "irreducible", "dQ/dt",
               "熵增", "entropy", "κ(∇φ)²", "热力学", "thermodynamic", "γ", "gamma"],
        "A4": ["随机", "random", "涨落", "fluctuation", "stochastic", "随机性",
               "intrinsic randomness", "布朗", "Brownian", "量子涨落", "quantum fluctuation"],
        "A5": ["规范场", "normative field", "自组织", "self-organizing", "约束",
               "constraint", "涌现", "emergence", "order parameter", "序参量"],
        "A6": ["升维", "transcendence", "paradox", "悖论", "矛盾", "contradiction",
               "拓扑", "topology", "higher dimension", "拓扑变换", "paradoxical"],
    }

    def verify_text(self, text: str, layer: str = "L1") -> RigidityReport:
        """验证文本中所有主张的逻辑刚性"""
        report = RigidityReport(target="inline_text")
        lines = text.split('\n')

        # 检测每条主张
        for i, line in enumerate(lines, 1):
            for pattern in self.CLAIM_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    report.total_claims += 1
                    finding = self._verify_claim(line, i, layer)
                    report.findings.append(finding)

        report.compute_score()
        return report

    def verify_file(self, filepath: str, layer: str = "L1") -> RigidityReport:
        """验证文件中的所有主张"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        report = self.verify_text(text, layer)
        report.target = os.path.basename(filepath)
        return report

    def verify_jsonl(self, filepath: str) -> List[RigidityReport]:
        """验证JSONL知识库条目"""
        reports = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line: continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                h_id = entry.get("h_id", f"L{i}")
                content = entry.get("content", entry.get("text", ""))
                layer = entry.get("layer", "L1")

                if not content: continue
                report = self.verify_text(content, layer)
                report.target = f"{h_id} (line {i})"
                reports.append(report)

        return reports

    def _verify_claim(self, claim: str, lineno: int, layer: str) -> RigidityFinding:
        """验证单条主张的公理锚定"""
        expected_axioms = set(LAYER_ANCHOR.get(layer, ["A1", "A2", "A3", "A4", "A5", "A6"]))
        found_axioms = set()

        # 检查公理锚定
        for axiom, keywords in self.AXIOM_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in claim.lower():
                    found_axioms.add(axiom)
                    break

        # 判断刚性等级
        if found_axioms & expected_axioms:
            # 有预期公理锚定
            if len(found_axioms & expected_axioms) >= 1:
                verdict = VerificationLevel.RIGID
                level = Severity.P2
                fix = ""
            else:
                verdict = VerificationLevel.TENSEGRITY
                level = Severity.P1
                fix = f"锚定到 {', '.join(sorted(expected_axioms))} 强化跨层自洽"
        elif found_axioms:
            # 有公理但非该层预期
            verdict = VerificationLevel.TENSEGRITY
            level = Severity.P1
            fix = f"当前锚定 {', '.join(sorted(found_axioms))}, 该层预期 {', '.join(sorted(expected_axioms))}"
        else:
            # 无任何公理锚定
            # 检查是否有K3式推理跳跃
            k3_jumps = ["obviously", "clearly", "不难看出", "显然", "众所周知",
                        "it is easy to see", "without loss of generality"]
            if any(j in claim.lower() for j in k3_jumps):
                verdict = VerificationLevel.UNANCHORED
                level = Severity.P0
                fix = f"添加显式公理锚定 (该层: {', '.join(sorted(expected_axioms))})"
            else:
                verdict = VerificationLevel.SOFT
                level = Severity.P1
                fix = f"补充公理引用增强刚性 (该层: {', '.join(sorted(expected_axioms))})"

        # 矛盾检测
        contradictions = self._check_contradictions(claim, layer)
        if contradictions:
            verdict = VerificationLevel.CONTRADICTORY
            level = Severity.P0
            fix = f"逻辑矛盾: {contradictions[0]}"

        return RigidityFinding(
            level=level,
            line=lineno,
            claim=claim.strip()[:100],
            expected_axiom=", ".join(sorted(expected_axioms)),
            actual_anchoring=", ".join(sorted(found_axioms)) if found_axioms else "NONE",
            verdict=verdict,
            fix=fix
        )

    def _check_contradictions(self, claim: str, layer: str) -> List[str]:
        """检测逻辑矛盾"""
        contradictions = []
        claim_lower = claim.lower()

        # 自相矛盾模式
        if "热税为零" in claim_lower and layer == "L1":
            contradictions.append("L1层热税不可能为零 (违反A3)")
        if "无随机" in claim_lower and "完全确定" in claim_lower:
            contradictions.append("声称确定性却违反A4随机性公理")
        if "不升维" in claim_lower and "消除矛盾" in claim_lower:
            contradictions.append("声称消除矛盾却拒绝升维 (违反A6)")

        return contradictions


def batch_verify_directory(root: str, pattern="*.md") -> List[RigidityReport]:
    """批量验证目录中所有文件的逻辑刚性"""
    verifier = LogicalRigidityVerifier()
    reports = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','node_modules')]
        for f in files:
            if not f.endswith(('.md', '.txt', '.py', '.jsonl')):
                continue
            fp = os.path.join(dirpath, f)
            try:
                sz = os.path.getsize(fp)
                if sz > 200_000: continue
                report = verifier.verify_file(fp, "L1")
                report.target = os.path.relpath(fp, root)
                if report.total_claims > 0:
                    reports.append(report)
            except: pass
    return reports


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="MSS Logical Rigidity Verifier (D5-043)")
    ap.add_argument("target", help="File or directory to verify")
    ap.add_argument("--batch", "-b", action="store_true")
    ap.add_argument("--json", "-j", action="store_true")
    args = ap.parse_args()

    verifier = LogicalRigidityVerifier()

    if args.batch:
        reports = batch_verify_directory(args.target)
        avg_score = sum(r.score for r in reports) / max(len(reports), 1)
        print(f"Files with claims: {len(reports)} | Avg rigidity: {avg_score:.1f}")
        for r in sorted(reports, key=lambda x: x.score)[:10]:
            p0 = sum(1 for f in r.findings if f.level == Severity.P0)
            flag = "⚠️" if p0 > 0 else "✅"
            print(f"  {flag} {r.target}: {r.score} (R{r.rigid}/T{r.tensegrity}/S{r.soft}/U{r.unanchored}/C{r.contradictory})")
    else:
        if os.path.isfile(args.target):
            report = verifier.verify_file(args.target)
        else:
            report = verifier.verify_text(args.target)
        if args.json:
            print(json.dumps({
                "target": report.target,
                "score": report.score,
                "total": report.total_claims,
                "rigid": report.rigid,
                "tensegrity": report.tensegrity,
                "soft": report.soft,
                "unanchored": report.unanchored,
                "contradictory": report.contradictory,
                "findings": [{"level": f.level.value, "verdict": f.verdict.value,
                              "line": f.line, "claim": f.claim,
                              "fix": f.fix} for f in report.findings[:10]]
            }, indent=2, ensure_ascii=False))
        else:
            print(f"Target: {report.target}")
            print(f"Score: {report.score} | Claims: {report.total_claims}")
            print(f"Rigid: {report.rigid} | Tensegrity: {report.tensegrity}")
            print(f"Soft: {report.soft} | Unanchored: {report.unanchored} | Contradictory: {report.contradictory}")
            for f in report.findings[:8]:
                print(f"  [{f.level.value}] L{f.line}: [{f.verdict.value}] {f.claim[:70]}...")
                if f.fix: print(f"       → {f.fix}")