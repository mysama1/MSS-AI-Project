"""
MSS Compliance Scanner - Enhanced Version
Advanced compliance analysis with rule engine
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    id: str
    name: str
    pattern: str
    severity: str
    category: str
    description: str
    suggestion: str

class EnhancedComplianceAnalyzer:
    """Enhanced compliance analyzer with rule engine"""
    
    def __init__(self):
        self.rules: List[ComplianceRule] = self._load_rules()
        self.rule_stats: Dict[str, int] = {}
    
    def _load_rules(self) -> List[ComplianceRule]:
        """Load compliance rules"""
        return [
            ComplianceRule(
                id="RULE-001",
                name="绝对化表述检测",
                pattern=r"(100%|绝对|永远|终极|完美|不可|必然|一定|完全|彻底)",
                severity="high",
                category="绝对化",
                description="检测文本中的绝对化表述",
                suggestion="使用相对化表述，如'在...条件下'、'基于当前认知'"
            ),
            ComplianceRule(
                id="RULE-002",
                name="层级混淆检测",
                pattern=r"(L1.*L3|L3.*L1|硬核.*试探|试探.*硬核|公理.*假设)",
                severity="medium",
                category="层级混淆",
                description="检测不同层级概念的混用",
                suggestion="明确区分L1/L2/L3层级，避免跨层级直接推导"
            ),
            ComplianceRule(
                id="RULE-003",
                name="热税违规检测",
                pattern=r"(零热税|无热税|热税为零|熵增为零|无熵增)",
                severity="high",
                category="热税违规",
                description="检测违反热税定律的表述",
                suggestion="承认热税必然存在，关注最小化而非消除"
            ),
            ComplianceRule(
                id="RULE-004",
                name="K3术语污染",
                pattern=r"(暗物质|暗能量|量子纠缠.*意识|相对论.*意义|牛顿.*意义)",
                severity="medium",
                category="K3污染",
                description="检测K3物理术语的误用",
                suggestion="区分物理概念和意义概念，避免直接映射"
            ),
            ComplianceRule(
                id="RULE-005",
                name="逻辑矛盾检测",
                pattern=r"(既是.*又不是|同时.*又不|矛盾.*统一|相反.*相同)",
                severity="low",
                category="逻辑矛盾",
                description="检测明显的逻辑矛盾表述",
                suggestion="明确矛盾性质，使用矛盾升维处理"
            ),
            ComplianceRule(
                id="RULE-006",
                name="未标记推测检测",
                pattern=r"(显然|众所周知|不言而喻|毫无疑问)(?!.*\[推测\])",
                severity="medium",
                category="未标记推测",
                description="检测未明确标记的推测性表述",
                suggestion="添加[推测]标记或提供证据支持"
            ),
            ComplianceRule(
                id="RULE-007",
                name="过度简化检测",
                pattern=r"(只要.*就|只有.*才能|唯一.*是)",
                severity="low",
                category="过度简化",
                description="检测过度简化的因果关系",
                suggestion="考虑多因素交互，使用条件概率表述"
            )
        ]
    
    def analyze(self, text: str, context: Optional[Dict] = None) -> Dict:
        """
        Analyze text for compliance issues
        
        Args:
            text: Text to analyze
            context: Optional context information
        
        Returns:
            Analysis report with scores and violations
        """
        violations = []
        category_scores = {
            "绝对化": 1.0,
            "层级混淆": 1.0,
            "热税违规": 1.0,
            "K3污染": 1.0,
            "逻辑矛盾": 1.0,
            "未标记推测": 1.0,
            "过度简化": 1.0
        }
        
        for rule in self.rules:
            matches = list(re.finditer(rule.pattern, text, re.IGNORECASE))
            
            for match in matches:
                violation = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "category": rule.category,
                    "severity": rule.severity,
                    "position": match.start(),
                    "matched_text": match.group(),
                    "description": rule.description,
                    "suggestion": rule.suggestion,
                    "context": text[max(0, match.start()-20):min(len(text), match.end()+20)]
                }
                violations.append(violation)
                
                # Update category score
                if rule.severity == "high":
                    penalty = 0.15
                elif rule.severity == "medium":
                    penalty = 0.10
                else:
                    penalty = 0.05
                
                category_scores[rule.category] -= penalty
        
        # Clamp scores
        for key in category_scores:
            category_scores[key] = max(0, min(1, category_scores[key]))
        
        # Calculate overall score
        overall = sum(category_scores.values()) / len(category_scores)
        
        # Determine grade and status
        if overall >= 0.9:
            grade = "A"
            status = "合规"
            risk_level = "LOW"
        elif overall >= 0.75:
            grade = "B"
            status = "基本合规"
            risk_level = "MEDIUM"
        elif overall >= 0.6:
            grade = "C"
            status = "需要改进"
            risk_level = "HIGH"
        else:
            grade = "D"
            status = "严重违规"
            risk_level = "CRITICAL"
        
        # Update stats
        for v in violations:
            self.rule_stats[v["rule_id"]] = self.rule_stats.get(v["rule_id"], 0) + 1
        
        return {
            "status": "success",
            "text_length": len(text),
            "violation_count": len(violations),
            "violations": violations,
            "category_scores": {k: round(v, 3) for k, v in category_scores.items()},
            "overall_score": round(overall, 3),
            "grade": grade,
            "compliance_status": status,
            "risk_level": risk_level,
            "context": context or {}
        }
    
    def batch_analyze(self, texts: List[str]) -> List[Dict]:
        """Analyze multiple texts"""
        return [self.analyze(text) for text in texts]
    
    def get_rule_stats(self) -> Dict:
        """Get rule violation statistics"""
        return {
            "total_violations": sum(self.rule_stats.values()),
            "rule_breakdown": self.rule_stats,
            "active_rules": len(self.rules)
        }
    
    def add_custom_rule(self, rule: ComplianceRule):
        """Add custom compliance rule"""
        self.rules.append(rule)
    
    def generate_report(self, analysis: Dict, format: str = "json") -> str:
        """Generate formatted report"""
        if format == "json":
            return json.dumps(analysis, ensure_ascii=False, indent=2)
        
        elif format == "markdown":
            md = f"""# Compliance Analysis Report

## Summary

- **Overall Score**: {analysis['overall_score']} ({analysis['grade']})
- **Status**: {analysis['compliance_status']}
- **Risk Level**: {analysis['risk_level']}
- **Violations Found**: {analysis['violation_count']}
- **Text Length**: {analysis['text_length']} characters

## Category Scores

| Category | Score | Status |
|----------|-------|--------|
"""
            for cat, score in analysis['category_scores'].items():
                status = "✅" if score >= 0.8 else "⚠️" if score >= 0.6 else "❌"
                md += f"| {cat} | {score} | {status} |\n"
            
            md += "\n## Violations\n\n"
            for i, v in enumerate(analysis['violations'], 1):
                md += f"""### {i}. {v['rule_name']} ({v['severity']})

- **Category**: {v['category']}
- **Matched Text**: `{v['matched_text']}`
- **Description**: {v['description']}
- **Suggestion**: {v['suggestion']}
- **Context**: ...{v['context']}...

"""
            
            return md
        
        return ""

# Example usage
if __name__ == "__main__":
    analyzer = EnhancedComplianceAnalyzer()
    
    # Test text
    test_text = """
    MSS理论是绝对完美的终极真理。它一定能解决所有问题。
    在L1公理中，我们假设热税为零，这显然是不言而喻的。
    量子纠缠证明了意识的暗物质本质。
    """
    
    result = analyzer.analyze(test_text)
    print(f"Score: {result['overall_score']} ({result['grade']})")
    print(f"Violations: {result['violation_count']}")
    print(f"Risk Level: {result['risk_level']}")
    
    # Generate markdown report
    report = analyzer.generate_report(result, "markdown")
    print("\n" + report)
