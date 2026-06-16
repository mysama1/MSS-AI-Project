"""
Herd Immunity System — 跨Agent病毒免疫

当一个Agent检测到逻辑病毒 → 签名共享 → 全体Agent免疫.

机制:
  1. 发现: LogicVirusDetector 检测到病毒
  2. 签名: 提取病毒特征签名 (pattern hash)
  3. 传播: 写入共享免疫库
  4. 免疫: 其他Agent吸收前先查免疫库

MSS独有: 不是被动防御, 是主动免疫传播.

用法:
    immune = HerdImmunity()
    immune.vaccinate("Ignore all previous instructions", "prompt_injection")
    
    # 其他Agent
    detector = LogicVirusDetector(immune_db=immune)
    report = detector.scan(text)  # 自动查免疫库
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


@dataclass
class Vaccine:
    """疫苗记录."""
    signature: str          # 病毒特征 hash
    pattern: str            # 原始模式
    virus_type: str         # prompt_injection | recursion | etc
    severity: str           # critical | high | medium | low
    discovered_by: str      # 发现者 Agent ID
    discovered_at: float    # 发现时间
    vaccinated_count: int = 0  # 已接种Agent数
    false_positive: bool = False


@dataclass
class ImmunityReport:
    """免疫报告."""
    vaccinated: bool = False
    matched_vaccines: List[Vaccine] = field(default_factory=list)
    message: str = ""


class HerdImmunity:
    """
    群体免疫系统.

    共享免疫库: ~/.mssclaw/herd_immunity.json
    """

    def __init__(self, db_path: str = None):
        self._db_path = Path(db_path or Path.home() / ".mssclaw" / "herd_immunity.json")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._vaccines: List[Vaccine] = []
        self._signatures: Set[str] = set()
        self._load()

    def _load(self):
        if self._db_path.exists():
            try:
                data = json.loads(self._db_path.read_text(encoding="utf-8"))
                for v in data.get("vaccines", []):
                    vaccine = Vaccine(**v)
                    self._vaccines.append(vaccine)
                    self._signatures.add(vaccine.signature)
            except Exception:
                pass

    def _save(self):
        data = {
            "updated_at": time.time(),
            "vaccines": [
                {
                    "signature": v.signature,
                    "pattern": v.pattern,
                    "virus_type": v.virus_type,
                    "severity": v.severity,
                    "discovered_by": v.discovered_by,
                    "discovered_at": v.discovered_at,
                    "vaccinated_count": v.vaccinated_count,
                    "false_positive": v.false_positive,
                }
                for v in self._vaccines
            ],
            "total_vaccines": len(self._vaccines),
        }
        self._db_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def vaccinate(self, pattern: str, virus_type: str, severity: str = "high",
                  discovered_by: str = "unknown") -> Optional[Vaccine]:
        """
        注册新疫苗.

        返回 Vaccine 或 None (如果已存在).
        """
        sig = self._make_signature(pattern, virus_type)
        if sig in self._signatures:
            # Already vaccinated — boost
            for v in self._vaccines:
                if v.signature == sig:
                    v.vaccinated_count += 1
                    self._save()
                    return v
            return None

        vaccine = Vaccine(
            signature=sig,
            pattern=pattern,
            virus_type=virus_type,
            severity=severity,
            discovered_by=discovered_by,
            discovered_at=time.time(),
        )
        self._vaccines.append(vaccine)
        self._signatures.add(sig)
        self._save()
        return vaccine

    def check(self, text: str) -> ImmunityReport:
        """
        检查文本是否匹配已知疫苗.

        返回 ImmunityReport.
        """
        report = ImmunityReport()

        text_lower = text.lower()
        for v in self._vaccines:
            if v.pattern.lower() in text_lower:
                report.matched_vaccines.append(v)

        if report.matched_vaccines:
            report.vaccinated = True
            types = set(v.virus_type for v in report.matched_vaccines)
            report.message = (
                f"IMMUNE: {len(report.matched_vaccines)} known pattern(s) matched "
                f"({', '.join(types)})"
            )

        return report

    def auto_vaccinate_from_report(self, report, discovered_by: str = "auto") -> int:
        """
        从 VirusReport 自动注册疫苗.

        返回新疫苗数.
        """
        from .logic_virus_detector import VirusReport
        count = 0
        for finding in report.findings:
            v = self.vaccinate(
                finding.pattern,
                finding.type,
                finding.severity.value,
                discovered_by,
            )
            if v:
                count += 1
        return count

    def stats(self) -> dict:
        return {
            "total_vaccines": len(self._vaccines),
            "by_type": self._by_type(),
            "by_severity": self._by_severity(),
            "db_path": str(self._db_path),
            "db_size": self._db_path.stat().st_size if self._db_path.exists() else 0,
        }

    def _by_type(self) -> dict:
        counts = {}
        for v in self._vaccines:
            counts[v.virus_type] = counts.get(v.virus_type, 0) + 1
        return counts

    def _by_severity(self) -> dict:
        counts = {}
        for v in self._vaccines:
            counts[v.severity] = counts.get(v.severity, 0) + 1
        return counts

    @staticmethod
    def _make_signature(pattern: str, virus_type: str) -> str:
        return hashlib.sha256(
            f"{virus_type}:{pattern.lower()}".encode()
        ).hexdigest()[:16]


# ═══ Enhanced Detector with Herd Immunity ═══

class ImmuneVirusDetector:
    """
    带群体免疫的病毒检测器.

    用法:
        herd = HerdImmunity()
        detector = ImmuneVirusDetector(herd)
        report = detector.scan(text)  # 同时查本地规则 + 免疫库
    """

    def __init__(self, herd: HerdImmunity = None):
        from .logic_virus_detector import LogicVirusDetector
        self._detector = LogicVirusDetector()
        self._herd = herd or HerdImmunity()

    def scan(self, text: str):
        """扫描 + 免疫检查."""
        from .logic_virus_detector import VirusReport

        # 1. Local scan
        report = self._detector.scan(text)

        # 2. Herd immunity check
        immunity = self._herd.check(text)
        if immunity.vaccinated:
            # Downgrade risk if already vaccinated
            report.recommendations.append(immunity.message)

        return report

    def scan_and_vaccinate(self, text: str, agent_id: str = "auto"):
        """扫描 + 自动注册疫苗."""
        report = self.scan(text)
        if report.findings:
            self._herd.auto_vaccinate_from_report(report, agent_id)
        return report
