"""
Arbiter Agent
Enhanced compliance checking using MSSAnalyzer
"""

import re
from typing import List, Dict, Optional

from mss_types import Layer, ComplianceStatus, ArbiterResult, Dialog
from mss_analyzer import MSSAnalyzer


class ArbiterAgent:
    """
    Enhanced Arbiter using MSSAnalyzer for deep compliance checking
    """
    
    FORBIDDEN_MAP = {
        r'\bsolve\b': 'address',
        r'\bsolved\b': 'addressed',
        r'\bsolving\b': 'addressing',
        r'\bultimate\b': 'current best',
        r'\bultimately\b': 'in the current framework',
        r'\bperfect\b': 'high-fidelity',
        r'\bperfectly\b': 'with high fidelity',
        r'\bcomplete\b': 'partial',
        r'\bcompletely\b': 'partially',
        r'\bbreakthrough\b': 'advance',
        r'\bfinal\b': 'current',
        r'\bfinally\b': 'currently',
        r'\babsolute\b': 'context-dependent',
        r'\babsolutely\b': 'in this context',
        r'\btranscend\b': 'expand beyond',
        r'\btranscended\b': 'expanded beyond',
        r'\btranscending\b': 'expanding beyond',
    }
    
    L1_KEYWORDS = [
        'information ontology', '0/1 critical', 'connected meaning network',
        'tuning degree', 'phi-crystal', 'phi crystal', 'o=s=u',
        'recursive self-consistency', 'axiom a1', 'axiom a2',
        'axiom a3', 'axiom a4', 'axiom a5', 'axiom a6'
    ]
    
    L2_KEYWORDS = [
        'BCT', 'bekenstein', 'church-turing', 'AI alignment',
        'falsification', 'predictive tracking', 'quantum MSS',
        'organizational resilience framework', 'weber-entropy',
        'protective belt', 'heuristic', 'metaphor'
    ]
    
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.dialog = Dialog()
        self.analyzer = MSSAnalyzer()
        self._init_system_prompt()
    
    def _init_system_prompt(self):
        system_prompt = """You are the MSS Arbiter Agent. Your job is to analyze user queries and classify them according to the MSS framework."""
        self.dialog.add("system", system_prompt)
    
    def check(self, user_input: str) -> ArbiterResult:
        """Run full compliance check using analyzer"""
        analysis = self.analyzer.analyze(user_input, claimed_layer=None)
        layer = self._map_layer(analysis.detected_layer)
        forbidden_found = self._detect_forbidden(user_input)
        
        if forbidden_found or analysis.overall_score < 0.5:
            compliance = ComplianceStatus.FAIL
            rewrite_needed = True
        elif analysis.overall_score < 0.8:
            compliance = ComplianceStatus.WARNING
            rewrite_needed = False
        else:
            compliance = ComplianceStatus.PASS
            rewrite_needed = False
        
        return ArbiterResult(
            layer=layer,
            compliance=compliance,
            forbidden_words=forbidden_found,
            rsca_check=analysis.rsca_compliance > 0.7,
            boundary_note=f"Layer {analysis.detected_layer}. Score: {analysis.overall_score}",
            rewrite_needed=rewrite_needed,
            rewrite_prompt=self._generate_rewrite_prompt(user_input, forbidden_found) if forbidden_found else None,
            analysis_report=analysis.to_dict()
        )
    
    def _map_layer(self, detected: str) -> Layer:
        """Map analyzer layer to Arbiter layer"""
        layer_map = {
            "L1": Layer.L1,
            "L2": Layer.L2,
            "L3": Layer.L3
        }
        return layer_map.get(detected, Layer.UNKNOWN)
    
    def _detect_forbidden(self, text: str) -> List[str]:
        """Rule-based forbidden word detection"""
        found = []
        text_lower = text.lower()
        for pattern, replacement in self.FORBIDDEN_MAP.items():
            matches = re.findall(pattern, text_lower)
            found.extend(matches)
        return list(set(found))
    
    def _generate_rewrite_prompt(self, original: str, forbidden: List[str]) -> str:
        """Generate rewrite instruction"""
        replacements = []
        for word in forbidden:
            for pattern, replacement in self.FORBIDDEN_MAP.items():
                if re.search(pattern, word.lower()):
                    replacements.append(f"'{word}' -> '{replacement}'")
                    break
        return f"Rewrite avoiding: {', '.join(replacements)}"
