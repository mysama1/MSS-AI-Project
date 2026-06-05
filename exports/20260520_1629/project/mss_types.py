"""
MSS Core Types
Data classes and enums used across MSS-AI system
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class Layer(Enum):
    """MSS Framework Layers"""
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    UNKNOWN = "UNKNOWN"


class ComplianceStatus(Enum):
    """Compliance check results"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


@dataclass
class ArbiterResult:
    """Output from Arbiter Agent"""
    layer: Layer
    compliance: ComplianceStatus
    forbidden_words: List[str] = field(default_factory=list)
    rsca_check: bool = False
    boundary_note: Optional[str] = None
    rewrite_needed: bool = False
    rewrite_prompt: Optional[str] = None
    analysis_report: Optional[Dict] = None


@dataclass
class Dialog:
    """Per-agent conversation state"""
    messages: List[Dict[str, str]] = field(default_factory=list)
    
    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
    
    def fork(self) -> 'Dialog':
        return Dialog(messages=self.messages.copy())
    
    def to_ollama_format(self) -> List[Dict[str, str]]:
        return self.messages
