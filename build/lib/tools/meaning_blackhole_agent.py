#!/usr/bin/env python3
"""
D5-042: MSS 意义黑洞监测Agent v2.0
升级自 K3 Blackhole Monitor — 新增:
  - 实时文本/代码黑洞签名扫描
  - MSS公理违规分类 (A1-A6)
  - 热度曲线 + 事件视界预测
  - Web/社交媒体意义黑洞检测
"""
import os, json, re, time, hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

# ===== 意义黑洞签名库 (H148-H155 基础) =====
class BlackholeSignature(Enum):
    NARRATIVE_INFLATION = "narrative_inflation"      # 叙事膨胀：故事大于产品
    GROWTH_PARADOX = "growth_paradox"                 # 增长悖论：用户增→亏损增
    FREE_LUNCH = "free_lunch_promise"                 # 免费午餐承诺：永不可持续
    COMPLEXITY_EXPLOSION = "complexity_explosion"     # 复杂度爆炸：熵失控
    VALUE_DECOUPLING = "value_decoupling"             # 价值脱钩：创造≠捕获
    TRUST_DISSOLUTION = "trust_dissolution"           # 信任溶解：信仰崩塌前兆
    CIRCULAR_DEPENDENCY = "circular_dependency"       # 循环依赖：意义闭环无外部锚定
    MEANING_FLATTENING = "meaning_flattening"         # 意义扁平化：多样性→同质性
    TOO_BIG_TO_MEAN = "too_big_to_mean"               # 太大而无法有意义

SIGNATURE_PATTERNS = {
    BlackholeSignature.NARRATIVE_INFLATION: [
        r'(?:changing the world|revolutioniz\w+|disrupt\w+|unprecedented|paradigm shift|game.?changer)',
    ],
    BlackholeSignature.FREE_LUNCH: [
        r'(?:free\s+(?:forever|tier|plan|access|signup)|unlimited\s+free|zero\s+cost)',
        r'(?:monetize\s+later|we.ll\s+figure\s+out\s+revenue|burn\s+rate|subsidized)',
    ],
    BlackholeSignature.GROWTH_PARADOX: [
        r'(?:growth\s+(?:at\s+all\s+costs|hacking|explosion))',
        r'(?:user\s+(?:acquisition|growth).*?(?:but|however).*?(?:revenue|profit|monet))',
    ],
    BlackholeSignature.COMPLEXITY_EXPLOSION: [
        r'(?:microservice[sz]\s+(?:architecture|sprawl)|1000\+?\s*(?:files|modules))',
        r'(?:technical\s+debt|legacy\s+code|spaghetti\s+code)',
    ],
    BlackholeSignature.VALUE_DECOUPLING: [
        r'(?:valuation\s+(?:without|no)\s+revenue|pre.?revenue|no\s+business\s+model)',
        r'(?:MAU|DAU)\s+(?:growing|soaring).*?(?:but).*?(?:loss|deficit)',
    ],
    BlackholeSignature.TRUST_DISSOLUTION: [
        r'(?:loss\s+of\s+trust|credibility\s+crisis|reputation\s+(?:damage|loss|collapse))',
        r'(?:transparency\s+failure|hidden\s+(?:fee|cost|agenda)|undisclosed)',
    ],
    BlackholeSignature.CIRCULAR_DEPENDENCY: [
        r'(?:circular\s+(?:import|dependency|reference)|self.?referential)',
        r'(?:bootstrapped\s+(?:without|no).*?(?:validation|verification))',
    ],
    BlackholeSignature.MEANING_FLATTENING: [
        r'(?:everything\s+is\s+(?:content|AI|blockchain|crypto))',
        r'(?:all\s+you\s+need\s+is|the\s+only\s+thing\s+that\s+matters)',
    ],
    BlackholeSignature.TOO_BIG_TO_MEAN: [
        r'(?:1\s+billion\s+(?:users|customers|devices))',
        r'(?:trillion\s+dollar|market\s+cap.*?(?:trillion|billion))',
    ],
}

# Axiom violation mapping
SIGNATURE_AXIOM = {
    BlackholeSignature.NARRATIVE_INFLATION: "A2",
    BlackholeSignature.FREE_LUNCH: "A3",
    BlackholeSignature.GROWTH_PARADOX: "A3",
    BlackholeSignature.COMPLEXITY_EXPLOSION: "A6",
    BlackholeSignature.VALUE_DECOUPLING: "A2",
    BlackholeSignature.TRUST_DISSOLUTION: "A1",
    BlackholeSignature.CIRCULAR_DEPENDENCY: "A6",
    BlackholeSignature.MEANING_FLATTENING: "A5",
    BlackholeSignature.TOO_BIG_TO_MEAN: "A1",
}

@dataclass
class BlackholeDetection:
    signature: BlackholeSignature
    axiom: str
    line: int
    match_text: str
    confidence: float
    risk_score: float

@dataclass
class ScanReport:
    target: str
    scan_time: str
    total_lines: int
    detections: List[BlackholeDetection] = field(default_factory=list)
    risk_level: str = "LOW"
    overall_score: float = 0.0
    event_horizon_estimate: str = "N/A"

    def compute_risk(self):
        """Calculate overall blackhole risk."""
        if not self.detections:
            self.risk_level = "SAFE"
            self.overall_score = 0
            return

        # Weight by signature type (some are more dangerous than others)
        weights = {
            BlackholeSignature.TOO_BIG_TO_MEAN: 3.0,
            BlackholeSignature.TRUST_DISSOLUTION: 2.5,
            BlackholeSignature.GROWTH_PARADOX: 2.0,
            BlackholeSignature.FREE_LUNCH: 2.0,
            BlackholeSignature.VALUE_DECOUPLING: 1.8,
            BlackholeSignature.CIRCULAR_DEPENDENCY: 1.5,
            BlackholeSignature.NARRATIVE_INFLATION: 1.2,
            BlackholeSignature.COMPLEXITY_EXPLOSION: 1.0,
            BlackholeSignature.MEANING_FLATTENING: 0.8,
        }

        self.overall_score = sum(
            d.risk_score * weights.get(d.signature, 1.0)
            for d in self.detections
        )

        max_score = len(self.detections) * 3.0 * max(weights.values())
        normalized = self.overall_score / max(max_score, 1) * 100

        if normalized > 60:
            self.risk_level = "CRITICAL"
            self.event_horizon_estimate = "Within 6 months"
        elif normalized > 30:
            self.risk_level = "HIGH"
            self.event_horizon_estimate = "Within 18 months"
        elif normalized > 10:
            self.risk_level = "MEDIUM"
            self.event_horizon_estimate = "Within 5 years"
        else:
            self.risk_level = "LOW"
            self.event_horizon_estimate = "> 10 years"

        self.overall_score = round(normalized, 1)


class MeaningBlackholeAgent:
    """MSS 意义黑洞监测Agent v2.0 — 扫描文本/代码中的意义黑洞签名"""

    def scan_text(self, text: str, source_id: str = "") -> ScanReport:
        """Scan arbitrary text for blackhole signatures."""
        lines = text.split('\n')
        report = ScanReport(
            target=source_id or "inline_text",
            scan_time=datetime.now().isoformat(),
            total_lines=len(lines)
        )

        for sig, patterns in SIGNATURE_PATTERNS.items():
            for pattern in patterns:
                for i, line in enumerate(lines, 1):
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        # Calculate confidence based on pattern specificity
                        match_len = len(match.group())
                        pattern_len = len(pattern)
                        confidence = min(1.0, match_len / max(pattern_len, 1) * 0.8 + 0.2)

                        # Calculate risk score
                        risk = confidence * (1.0 + (match_len / 100))

                        report.detections.append(BlackholeDetection(
                            signature=sig,
                            axiom=SIGNATURE_AXIOM[sig],
                            line=i,
                            match_text=match.group()[:100],
                            confidence=round(confidence, 2),
                            risk_score=round(risk, 2)
                        ))

        report.compute_risk()
        return report

    def scan_file(self, filepath: str) -> ScanReport:
        """Scan a single file."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return self.scan_text(text, os.path.basename(filepath))

    def scan_directory(self, root: str, extensions=('.md','.txt','.py','.jsonl','.json','.html')) -> List[ScanReport]:
        """Recursively scan a directory."""
        reports = []
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ('__pycache__','node_modules','.git')]
            for f in files:
                if not any(f.endswith(ext) for ext in extensions):
                    continue
                fp = os.path.join(dirpath, f)
                try:
                    sz = os.path.getsize(fp)
                    if sz > 500_000:  # Skip huge files
                        continue
                    report = self.scan_file(fp)
                    if report.detections:
                        reports.append(report)
                except:
                    continue
        return reports

    def to_json(self, report: ScanReport) -> str:
        return json.dumps({
            "target": report.target,
            "scan_time": report.scan_time,
            "lines": report.total_lines,
            "risk_level": report.risk_level,
            "score": report.overall_score,
            "event_horizon": report.event_horizon_estimate,
            "detection_count": len(report.detections),
            "top_signatures": [
                {"sig": d.signature.value, "axiom": d.axiom, "line": d.line,
                 "match": d.match_text[:60], "risk": d.risk_score}
                for d in sorted(report.detections, key=lambda x: -x.risk_score)[:15]
            ]
        }, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="MSS Meaning Blackhole Agent v2.0")
    ap.add_argument("target", help="File or directory to scan")
    ap.add_argument("--recursive", "-r", action="store_true", help="Recursive scan")
    ap.add_argument("--json", "-j", action="store_true", help="JSON output")
    args = ap.parse_args()

    agent = MeaningBlackholeAgent()

    if args.recursive:
        reports = agent.scan_directory(args.target)
        print(f"Scanned: {len(reports)} files with detections")
        for r in sorted(reports, key=lambda x: -x.overall_score)[:10]:
            print(f"  [{r.risk_level}] {r.target}: {r.overall_score} ({len(r.detections)} hits)")
    else:
        report = agent.scan_file(args.target) if os.path.isfile(args.target) else agent.scan_text(args.target, "inline")
        if args.json:
            print(agent.to_json(report))
        else:
            print(f"File: {report.target}")
            print(f"Risk: {report.risk_level} ({report.overall_score})")
            print(f"Event horizon: {report.event_horizon_estimate}")
            print(f"Detections: {len(report.detections)}")
            for d in sorted(report.detections, key=lambda x: -x.risk_score)[:10]:
                print(f"  [{d.axiom}] L{d.line}: {d.signature.value} — {d.match_text[:60]}")