"""
MSS-Agent SDK 核心类型定义
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any
from datetime import datetime

class AnchorLevel(Enum):
    """意义锚定层级"""
    OBJECTIVE = auto()      # 客观潜在意义 L-1
    ACTUAL = auto()         # 实在显化意义 L0
    SUBJECTIVE = auto()     # 主观体验意义 L1

class Confidence(Enum):
    """置信度等级"""
    CERTAIN = "[Confidence: CERTAIN]"      # 公理/定义层
    HIGH = "[Confidence: HIGH]"            # 定理/引理层
    MODERATE = "[Confidence: MODERATE]"    # 试探法层
    SPECULATIVE = "[Confidence: SPECULATIVE]"  # 推测/边界外

@dataclass
class BoundaryNote:
    """边界标注"""
    note: str
    layer: str  # L1/L2/L3/L4
    created_at: datetime = field(default_factory=datetime.now)

@dataclass  
class AuditResult:
    """审计结果"""
    passed: bool
    logic_rigidity: float  # M_L ∈ [0, 1]
    heat_tax: float        # γ ≥ 0
    confidence: Confidence
    layer: str             # L1/L2/L3/L4
    boundary_notes: List[BoundaryNote] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_markdown(self) -> str:
        """生成Markdown格式审计报告"""
        lines = [
            "## MSS逻辑审计报告",
            f"",
            f"**状态**: {'✅ 通过' if self.passed else '❌ 未通过'}",
            f"**逻辑刚性 M_L**: {self.logic_rigidity:.4f}",
            f"**热税 γ**: {self.heat_tax:.4f}",
            f"**置信度**: {self.confidence.value}",
            f"**层级**: {self.layer}",
            f"**时间**: {self.timestamp.isoformat()}",
            f"",
        ]
        if self.boundary_notes:
            lines.append("### 边界标注")
            for note in self.boundary_notes:
                lines.append(f"- [{note.layer}] {note.note}")
            lines.append("")
        if self.contradictions:
            lines.append("### 检测到的矛盾")
            for c in self.contradictions:
                lines.append(f"- ⚠️ {c}")
            lines.append("")
        if self.suggestions:
            lines.append("### 优化建议")
            for s in self.suggestions:
                lines.append(f"- 💡 {s}")
            lines.append("")
        return "\n".join(lines)

@dataclass
class AnchorResult:
    """意义锚定结果"""
    level: AnchorLevel
    anchored: bool
    text: str
    heat_tax_before: float
    heat_tax_after: float
    savings: float  # 热税节省比例
