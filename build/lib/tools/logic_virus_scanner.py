#!/usr/bin/env python3
"""
D5-045: MSS 逻辑病毒扫描器 v1.0
检测文本/代码中的"逻辑病毒" — K3范式污染的推理模式
MSS公理锚定: A2(意义保真), A3(热税), A6(矛盾升维)
"""
import os, json, re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Tuple
from enum import Enum

class VirusSeverity(Enum):
    CRITICAL = "CRITICAL"  # 逻辑刚性彻底破裂
    HIGH = "HIGH"          # 严重逻辑污染
    MEDIUM = "MEDIUM"      # 常见但可修复
    LOW = "LOW"            # 边缘污染

class VirusFamily(Enum):
    CIRCULAR = "circular"           # 循环论证/同义反复
    EQUIVOCATION = "equivocation"   # 概念偷换/模糊定义
    FALSE_DICHOTOMY = "false_dichotomy"  # 假二分
    AD_HOMINEM = "ad_hominem"       # 人身攻击
    APPEAL_TO_AUTHORITY = "appeal_to_authority"  # 诉诸权威
    SLIPPERY_SLOPE = "slippery_slope"    # 滑坡谬误
    STRAW_MAN = "straw_man"          # 稻草人
    POST_HOC = "post_hoc"            # 假因果
    TEXAS_SHARPSHOOTER = "texas_sharpshooter"  # 先射箭后画靶
    MOTTE_BAILEY = "motte_bailey"    # 模棱两可的防卫
    NO_TRUE_SCOTSMAN = "no_true_scotsman"  # 非真XX
    BEGGING_QUESTION = "begging_question"  # 窃取论点
    AFFIRMING_CONSEQUENT = "affirming_consequent"  # 肯定后件
    DENYING_ANTECEDENT = "denying_antecedent"      # 否定前件
    GISH_GALLOP = "gish_gallop"      # 信息轰炸
    WHATABOUTISM = "whataboutism"    # "那又怎么说"

# ===== 逻辑病毒签名库 =====
VIRUS_SIGNATURES = {
    VirusFamily.CIRCULAR: {
        "severity": VirusSeverity.CRITICAL,
        "axiom": "A2",
        "patterns": [
            (r'(因为[^，。]{4,20})所以[^，。]{4,20}因此\\1', "A→B→A 循环"),
            (r'it is true because .{0,30} it is true', "tautological"),
            (r'by definition.{0,30} therefore.{0,30} by definition', "definitional loop"),
            (r'显然这是对的因为这是显而易见的', "自证自明"),
            (r'obviously correct because.{0,50} self-evident', "self-evident loop"),
        ],
    },
    VirusFamily.EQUIVOCATION: {
        "severity": VirusSeverity.HIGH,
        "axiom": "A2",
        "patterns": [
            (r'(?:所谓|所谓的).{4,30}(?:其实是|实际上是|就是).{4,30}(?:但也.{4,20})?', "概念滑动"),
            (r'in the broad sense.{0,50} but in the narrow sense', "definition sliding"),
            (r'严格来说.{0,50}但广义上', "scope shifting"),
            (r'定义[^，。]{2,20}为.{4,30}但.{4,20}也算', "定义模糊"),
        ],
    },
    VirusFamily.FALSE_DICHOTOMY: {
        "severity": VirusSeverity.HIGH,
        "axiom": "A6",
        "patterns": [
            (r'(?:要么|不是[^，。]{2,10}就是).{4,40}(?:只有.{0,5}条路)', "假二分"),
            (r'there are only two (?:options|choices|possibilities)', "false binary"),
            (r'(?:非此即彼|二元对立|零和)', "zero-sum framing"),
            (r'you are either with us or against us', "forced choice"),
        ],
    },
    VirusFamily.APPEAL_TO_AUTHORITY: {
        "severity": VirusSeverity.MEDIUM,
        "axiom": "A2",
        "patterns": [
            (r'(?:正如|根据|按照).{2,10}(?:大师|专家|权威|名人|院士|诺奖|图灵奖)', "诉诸权威"),
            (r'according to (?:expert|authority|famous|Nobel|Turing)', "appeal to authority"),
            (r'(?:爱因斯坦|牛顿|费曼|霍金|图灵)说过', "namedropping"),
            (r'(?:某|某某|著名|资深|顶级)(?:科学家|学者|教授|CEO)', "unnamed authority"),
        ],
    },
    VirusFamily.STRAW_MAN: {
        "severity": VirusSeverity.HIGH,
        "axiom": "A2",
        "patterns": [
            (r'(?:你的意思是|你是说|那你的逻辑是).{4,40}(?:但这.{4,40})', "稻草人重构"),
            (r'so you.{0,3}re saying.{0,40} which is obviously wrong', "straw man"),
            (r'(?:极端化|夸大|歪曲).{2,20}(?:说法|观点|立场)', "exaggeration"),
            (r'if we take your argument to its extreme', "reductio ad absurdum misuse"),
        ],
    },
    VirusFamily.POST_HOC: {
        "severity": VirusSeverity.MEDIUM,
        "axiom": "A4",
        "patterns": [
            (r'(?:自从|自从有了|引入).{4,30}(?:后|之后).{2,20}(?:就|便).{4,30}', "假因果后此"),
            (r'after.{0,30} therefore because of', "post hoc"),
            (r'(?:相关性.{0,10}因果|巧合.{0,10}因果|coincidence.{0,10}causal)', "causation confusion"),
        ],
    },
    VirusFamily.MOTTE_BAILEY: {
        "severity": VirusSeverity.HIGH,
        "axiom": "A6",
        "patterns": [
            (r'(?:实际上.{2,10}我只是说|严格来说.{2,10}我的意思是).{4,60}', "摩特-贝利"),
            (r'what I (?:actually|really) meant was', "motte-bailey retreat"),
            (r'(?:广义.{0,5}狭义|大前提.{0,5}小前提).{4,40}', "definition retreat"),
        ],
    },
    VirusFamily.NO_TRUE_SCOTSMAN: {
        "severity": VirusSeverity.MEDIUM,
        "axiom": "A5",
        "patterns": [
            (r'(?:真正|真正意义.{0,5}|名副其实).{2,10}(?:的|之)', "非真苏格兰"),
            (r'no true.{2,20} would', "no true scotsman"),
            (r'(?:真正的.{2,10}不会|真正的.{2,10}一定是)', "essence assertion"),
        ],
    },
    VirusFamily.GISH_GALLOP: {
        "severity": VirusSeverity.MEDIUM,
        "axiom": "A3",
        "patterns": [
            (r'(?:堆砌|大量|海量|成百上千|数以万计).{2,10}(?:证据|数据|案例|例子)', "信息轰炸"),
            (r'(?:列举|枚举|罗列).{2,10}(?:超过|不少于|至少).{2,5}(?:条|个|项)', "evidence flooding"),
        ],
    },
    VirusFamily.WHATABOUTISM: {
        "severity": VirusSeverity.LOW,
        "axiom": "A6",
        "patterns": [
            (r'(?:那.{2,5}怎么说|那.{2,5}呢|可是.{2,5}也)', "那又怎么说"),
            (r'what about.{0,30}\?', "whataboutism"),
            (r'(?:你也.{2,10}过|你们也.{2,10}过)', "tu quoque"),
        ],
    },
}

@dataclass
class VirusFinding:
    family: VirusFamily
    severity: VirusSeverity
    axiom: str
    line: int
    match_text: str
    description: str
    fix_suggestion: str

@dataclass
class VirusScanReport:
    target: str
    scan_time: str
    total_lines: int
    findings: List[VirusFinding] = field(default_factory=list)
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    virus_density: float = 0.0
    verdict: str = "CLEAN"

    def compute(self):
        for f in self.findings:
            if f.severity == VirusSeverity.CRITICAL:
                self.critical += 1
            elif f.severity == VirusSeverity.HIGH:
                self.high += 1
            elif f.severity == VirusSeverity.MEDIUM:
                self.medium += 1
            else:
                self.low += 1

        if self.total_lines > 0:
            self.virus_density = round(len(self.findings) / self.total_lines * 100, 2)

        if self.critical > 0:
            self.verdict = "INFECTED_CRITICAL"
        elif self.high > 2:
            self.verdict = "INFECTED_HIGH"
        elif self.high > 0 or self.medium > 3:
            self.verdict = "SUSPICIOUS"
        elif self.medium > 0 or self.low > 2:
            self.verdict = "MILD_CONTAMINATION"
        else:
            self.verdict = "CLEAN"


class LogicVirusScanner:
    """逻辑病毒扫描器 — 检测K3范式污染的推理模式"""

    def scan_text(self, text: str, source: str = "") -> VirusScanReport:
        lines = text.split('\n')
        report = VirusScanReport(
            target=source or "inline",
            scan_time=datetime.now().isoformat(),
            total_lines=len(lines)
        )

        for family, config in VIRUS_SIGNATURES.items():
            for pattern, description in config["patterns"]:
                for i, line in enumerate(lines, 1):
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        report.findings.append(VirusFinding(
                            family=family,
                            severity=config["severity"],
                            axiom=config["axiom"],
                            line=i,
                            match_text=match.group()[:80],
                            description=description,
                            fix_suggestion=self._suggest_fix(family)
                        ))

        report.compute()
        return report

    def scan_file(self, filepath: str) -> VirusScanReport:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return self.scan_text(text, os.path.basename(filepath))

    def scan_directory(self, root: str, extensions=('.md','.txt','.py','.jsonl')) -> List[VirusScanReport]:
        reports = []
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','node_modules')]
            for f in files:
                if not any(f.endswith(ext) for ext in extensions):
                    continue
                fp = os.path.join(dirpath, f)
                try:
                    if os.path.getsize(fp) > 200_000:
                        continue
                    report = self.scan_file(fp)
                    if report.findings:
                        reports.append(report)
                except:
                    continue
        return reports

    def _suggest_fix(self, family: VirusFamily) -> str:
        suggestions = {
            VirusFamily.CIRCULAR: "用独立证据替代循环推理，或明确承认自举假设",
            VirusFamily.EQUIVOCATION: "冻结定义 — 在同一论证中保持概念使用一致",
            VirusFamily.FALSE_DICHOTOMY: "承认中间地带，枚举第三、第四选项（A6升维）",
            VirusFamily.APPEAL_TO_AUTHORITY: "引用具体证据而非权威名号",
            VirusFamily.STRAW_MAN: "复述对方最强版本的观点（钢铁人原则）",
            VirusFamily.POST_HOC: "控制变量或随机化以排除混淆因素",
            VirusFamily.MOTTE_BAILEY: "选一个防御位置并坚持 — 不来回移动",
            VirusFamily.NO_TRUE_SCOTSMAN: "给出可操作的定义标准，允许反例存在",
            VirusFamily.GISH_GALLOP: "聚焦最核心的3个论点，逐条深入",
            VirusFamily.WHATABOUTISM: "承认对方批评的独立性，不管他人如何",
            VirusFamily.AD_HOMINEM: "针对论点而非发言者",
            VirusFamily.SLIPPERY_SLOPE: "要求因果链每一步的证据",
            VirusFamily.BEGGING_QUESTION: "区分前提与结论，避免结论预设为前提",
        }
        return suggestions.get(family, "检查推理链的逻辑完整性")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="MSS Logic Virus Scanner (D5-045)")
    ap.add_argument("target", help="File or directory to scan")
    ap.add_argument("--dir", "-d", action="store_true", help="Directory mode")
    ap.add_argument("--json", "-j", action="store_true")
    args = ap.parse_args()

    scanner = LogicVirusScanner()

    if args.dir:
        reports = scanner.scan_directory(args.target)
        total_viruses = sum(len(r.findings) for r in reports)
        infected = [r for r in reports if r.verdict != "CLEAN"]
        print(f"Scanned: {len(reports)} files with findings")
        print(f"Total viruses: {total_viruses}")
        print(f"Infected: {len(infected)}")
        for r in sorted(reports, key=lambda x: -(x.critical*4+x.high*3+x.medium*2+x.low)):
            print(f"  [{r.verdict}] {r.target}: C{r.critical}/H{r.high}/M{r.medium}/L{r.low}")
    else:
        if os.path.isfile(args.target):
            report = scanner.scan_file(args.target)
        else:
            report = scanner.scan_text(args.target, "inline")

        if args.json:
            print(json.dumps({
                "target": report.target,
                "verdict": report.verdict,
                "critical": report.critical,
                "high": report.high,
                "medium": report.medium,
                "low": report.low,
                "virus_density": report.virus_density,
                "findings": [{"family": f.family.value, "severity": f.severity.value,
                              "axiom": f.axiom, "line": f.line,
                              "match": f.match_text[:60],
                              "fix": f.fix_suggestion}
                             for f in report.findings[:15]]
            }, indent=2, ensure_ascii=False))
        else:
            print(f"\nTarget: {report.target}")
            print(f"Verdict: {report.verdict}")
            print(f"Critical: {report.critical} | High: {report.high} | Medium: {report.medium} | Low: {report.low}")
            print(f"Virus density: {report.virus_density}%")
            print(f"\nFindings ({len(report.findings)}):")
            for f in sorted(report.findings, key=lambda x: x.severity.value):
                print(f"  [{f.severity.value}] L{f.line}: [{f.family.value}] {f.description}")
                print(f"       Match: {f.match_text[:60]}")
                print(f"       Fix: {f.fix_suggestion}")