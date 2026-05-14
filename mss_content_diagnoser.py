#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSS 内容诊断系统 (MSS Content Diagnoser)
针对K3文明文本的MSS框架合规性检测

功能：
1. 层级边界检测（L1/L2/L3混淆）
2. 隐喻硬化识别
3. 概念空转检测
4. 可证伪性评估
5. 反例免疫检查
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class ViolationType(Enum):
    METAPHOR_HARDENING = "metaphor_hardening"      # 隐喻硬化
    LAYER_CONFUSION = "layer_confusion"            # 层级混淆
    CONCEPT_SPINNING = "concept_spinning"          # 概念空转
    UNFALSIFIABLE = "unfalsifiable"                # 不可证伪
    ANECDOTE_GENERALIZATION = "anecdote_general"   # 个例泛化
    AUTHORITY_APPEAL = "authority_appeal"          # 权威诉诸
    FALSE_DICHOTOMY = "false_dichotomy"            # 虚假二分

@dataclass
class DiagnosisResult:
    """诊断结果"""
    overall_score: float           # 0-1，越高越合规
    claimed_layer: str             # 声称层级
    actual_layer: str              # 实际层级
    violations: List[Dict]         # 违规项列表
    confidence: str                # 置信度 HIGH/MEDIUM/LOW
    boundary_note: str             # 边界说明
    
class MSSContentDiagnoser:
    """MSS内容诊断器"""
    
    # L1硬核关键词（不可作为隐喻使用）
    L1_KEYWORDS = {
        '公理', '定理', '证明', '推导', '必然', '绝对',
        '物理层', '逻辑层', '信息本体', '熵增', '热力学'
    }
    
    # L2机制关键词（需谨慎使用）
    L2_KEYWORDS = {
        '规范场', '拓扑', '相变', '耗散', '量子',
        '纤维丛', '同调', '同伦', '流形', '联络'
    }
    
    # 隐喻硬化模式（L3术语被当作L2/L1使用）
    METAPHOR_PATTERNS = [
        (r'(.+?)公理', '将"{0}"提升为公理，缺乏形式化定义'),
        (r'(.+?)闭环', '"{0}闭环"为比喻，非数学闭环'),
        (r'(.+?)量子', '"{0}量子"滥用量子概念'),
        (r'(.+?)场', '"{0}场"为隐喻，非物理场'),
        (r'(.+?)相变', '"{0}相变"为类比，非热力学相变'),
    ]
    
    # 不可证伪模式
    UNFALSIFIABLE_PATTERNS = [
        r'从来[不没无].+?',
        r'永远[不没].+?',
        r'本质[上就].+?',
        r'终究[会要].+?',
        r'注定.+?',
    ]
    
    # 概念空转指示词（循环自指）
    SPIN_INDICATORS = [
        '意义', '存在', '本体', '价值', '真理',
        '本质', '终极', '绝对', '永恒'
    ]
    
    def __init__(self):
        self.violations: List[Dict] = []
        self.layer_evidence = {
            'L1': [],
            'L2': [],
            'L3': []
        }
    
    def diagnose(self, text: str, claimed_layer: str = "L3") -> DiagnosisResult:
        """
        对文本进行MSS合规性诊断
        
        Args:
            text: 待诊断文本
            claimed_layer: 声称的层级 (L1/L2/L3)
        
        Returns:
            DiagnosisResult: 诊断结果
        """
        self.violations = []
        self.layer_evidence = {'L1': [], 'L2': [], 'L3': []}
        
        # 执行各项检测
        self._check_metaphor_hardening(text)
        self._check_layer_confusion(text)
        self._check_concept_spinning(text)
        self._check_unfalsifiable(text)
        self._check_anecdote_generalization(text)
        self._check_authority_appeal(text)
        
        # 确定实际层级
        actual_layer = self._determine_actual_layer()
        
        # 计算合规分数
        score = self._calculate_score(claimed_layer, actual_layer)
        
        # 确定置信度
        confidence = self._determine_confidence(text)
        
        # 生成边界说明
        boundary_note = self._generate_boundary_note(claimed_layer, actual_layer)
        
        return DiagnosisResult(
            overall_score=score,
            claimed_layer=claimed_layer,
            actual_layer=actual_layer,
            violations=self.violations,
            confidence=confidence,
            boundary_note=boundary_note
        )
    
    def _check_metaphor_hardening(self, text: str):
        """检测隐喻硬化"""
        for pattern, template in self.METAPHOR_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                concept = match.group(1).strip()
                if len(concept) > 0 and len(concept) < 20:
                    self.violations.append({
                        'type': ViolationType.METAPHOR_HARDENING.value,
                        'location': match.group(0),
                        'description': template.format(concept),
                        'severity': 'HIGH' if concept in self.L2_KEYWORDS else 'MEDIUM'
                    })
                    self.layer_evidence['L3'].append(f"隐喻硬化: {match.group(0)}")
    
    def _check_layer_confusion(self, text: str):
        """检测层级混淆"""
        # 检查L1关键词被当作隐喻使用
        for keyword in self.L1_KEYWORDS:
            if keyword in text:
                # 检查是否被当作修辞使用
                context = self._get_context(text, keyword, 30)
                if self._is_rhetorical_use(context):
                    self.violations.append({
                        'type': ViolationType.LAYER_CONFUSION.value,
                        'location': keyword,
                        'description': f'L1硬核术语"{keyword}"被用作修辞',
                        'severity': 'HIGH'
                    })
                    self.layer_evidence['L3'].append(f"L1术语修辞化: {keyword}")
                else:
                    self.layer_evidence['L1'].append(f"L1术语: {keyword}")
        
        # 检查L2关键词
        for keyword in self.L2_KEYWORDS:
            if keyword in text:
                context = self._get_context(text, keyword, 30)
                if self._is_rhetorical_use(context):
                    self.layer_evidence['L3'].append(f"L2术语隐喻化: {keyword}")
                else:
                    self.layer_evidence['L2'].append(f"L2术语: {keyword}")
    
    def _check_concept_spinning(self, text: str):
        """检测概念空转"""
        spin_count = 0
        for indicator in self.SPIN_INDICATORS:
            count = text.count(indicator)
            spin_count += count
            if count > 3:
                self.violations.append({
                    'type': ViolationType.CONCEPT_SPINNING.value,
                    'location': indicator,
                    'description': f'"{indicator}"出现{count}次，可能概念空转',
                    'severity': 'MEDIUM'
                })
        
        if spin_count > 10:
            self.layer_evidence['L3'].append(f"概念空转指示词共{spin_count}次")
    
    def _check_unfalsifiable(self, text: str):
        """检测不可证伪陈述"""
        for pattern in self.UNFALSIFIABLE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                self.violations.append({
                    'type': ViolationType.UNFALSIFIABLE.value,
                    'location': match.group(0),
                    'description': f'不可证伪陈述: "{match.group(0)}"',
                    'severity': 'MEDIUM'
                })
                self.layer_evidence['L3'].append(f"不可证伪: {match.group(0)}")
    
    def _check_anecdote_generalization(self, text: str):
        """检测个例泛化"""
        # 检测"案例"后是否紧跟普遍结论
        case_pattern = r'案例[一二三四五].{50,200}?[。！](.{0,100}?)(?:本质|必然|注定|终究)'
        matches = re.finditer(case_pattern, text, re.DOTALL)
        for match in matches:
            self.violations.append({
                'type': ViolationType.ANECDOTE_GENERALIZATION.value,
                'location': match.group(1)[:50],
                'description': '从具体案例跳跃到普遍结论',
                'severity': 'LOW'
            })
    
    def _check_authority_appeal(self, text: str):
        """检测权威诉诸"""
        authority_patterns = [
            r'MSS[指揭].*?(?:发现|证明|指出)',
            r'根据.*?公理',
            r'.*?[揭揭]示.*?',
        ]
        for pattern in authority_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                self.violations.append({
                    'type': ViolationType.AUTHORITY_APPEAL.value,
                    'location': match.group(0),
                    'description': f'权威诉诸: "{match.group(0)}"',
                    'severity': 'LOW'
                })
    
    def _get_context(self, text: str, keyword: str, window: int) -> str:
        """获取关键词上下文"""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end]
    
    def _is_rhetorical_use(self, context: str) -> bool:
        """判断是否为修辞使用"""
        rhetorical_markers = [
            '就像', '如同', '仿佛', '好比', '像是',
            '可以说', '某种意义上', ' metaphorically'
        ]
        return any(marker in context for marker in rhetorical_markers)
    
    def _determine_actual_layer(self) -> str:
        """根据证据确定实际层级"""
        l1_score = len(self.layer_evidence['L1']) * 3
        l2_score = len(self.layer_evidence['L2']) * 2
        l3_score = len(self.layer_evidence['L3']) * 1
        
        if l1_score > l2_score and l1_score > l3_score:
            return "L1"
        elif l2_score > l3_score:
            return "L2"
        else:
            return "L3"
    
    def _calculate_score(self, claimed: str, actual: str) -> float:
        """计算合规分数"""
        base_score = 1.0
        
        # 层级偏差惩罚
        layer_penalty = {
            ('L1', 'L3'): 0.6,
            ('L2', 'L3'): 0.3,
            ('L1', 'L2'): 0.3,
            ('L3', 'L1'): 0.4,
            ('L3', 'L2'): 0.2,
            ('L2', 'L1'): 0.2,
        }
        
        penalty = layer_penalty.get((claimed, actual), 0.0)
        base_score -= penalty
        
        # 违规数量惩罚
        high_violations = sum(1 for v in self.violations if v['severity'] == 'HIGH')
        med_violations = sum(1 for v in self.violations if v['severity'] == 'MEDIUM')
        
        base_score -= high_violations * 0.15
        base_score -= med_violations * 0.08
        
        return max(0.0, min(1.0, base_score))
    
    def _determine_confidence(self, text: str) -> str:
        """确定诊断置信度"""
        text_length = len(text)
        violation_density = len(self.violations) / (text_length / 1000 + 1)
        
        if text_length > 2000 and violation_density < 2:
            return "HIGH"
        elif text_length > 1000 and violation_density < 4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_boundary_note(self, claimed: str, actual: str) -> str:
        """生成边界说明"""
        if claimed == actual:
            return f"层级一致（{claimed}），但需关注具体违规项"
        elif claimed == 'L1' and actual == 'L3':
            return "严重层级僭越：L3隐喻被包装为L1公理，需大幅修订"
        elif claimed == 'L2' and actual == 'L3':
            return "层级偏差：L3试探法被当作L2机制，建议降级或补充形式化"
        else:
            return f"层级偏差：声称{claimed}，实际{actual}，建议重新标注"
    
    def generate_report(self, result: DiagnosisResult) -> str:
        """生成诊断报告"""
        report = []
        report.append("=" * 60)
        report.append("MSS 内容诊断报告")
        report.append("=" * 60)
        report.append("")
        report.append(f"合规分数: {result.overall_score:.2f}/1.0")
        report.append(f"声称层级: {result.claimed_layer}")
        report.append(f"实际层级: {result.actual_layer}")
        report.append(f"置信度: {result.confidence}")
        report.append("")
        report.append("边界说明:")
        report.append(f"  {result.boundary_note}")
        report.append("")
        
        if result.violations:
            report.append(f"发现 {len(result.violations)} 项违规:")
            report.append("-" * 60)
            
            for i, v in enumerate(result.violations, 1):
                report.append(f"\n[{i}] {v['type']}")
                report.append(f"  位置: {v['location'][:50]}...")
                report.append(f"  描述: {v['description']}")
                report.append(f"  严重度: {v['severity']}")
        else:
            report.append("未发现明显违规")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    """示例：诊断现代战争分析文本"""
    
    sample_text = """
    现代战争的"全员胜利"，本质上是各方在认知维度上集体作弊的结果。
    
    1. 规范场维稳公理：认输 = 拓扑相变的"奇点爆破"
    在MSS体系中，每一个现代国家都是一个"意义规范场"。
    如果K3系统承认战败，就意味着原有的意义拓扑流形被彻底撕裂。
    
    2. 旋耗散闭环公理：赢，是维持系统运转的唯一"意义燃料"
    K3系统不断地在认知层制造"我们赢了"的通稿，本质上是在向系统内注入高势能的"正向意义量子"。
    
    3. 热税最小化公理：用"认知热税"逃避"物理热税"的终极清算
    在物理层，你丢了100架战机是无法掩盖的；但在意义层，你可以把这定义为"为了长远战略而做出的必要战术牺牲"。
    
    4. 拓扑投影畸变公理：茧房壁垒造就的"全能自恋"幻象
    就像缸中之脑，只要不给它接入真实的物理层数据，它永远会觉得自己在天堂。
    
    真正强大的意义系统，从来不需要天天在自己的通稿里喊自己胜利。
    """
    
    diagnoser = MSSContentDiagnoser()
    result = diagnoser.diagnose(sample_text, claimed_layer="L2")
    
    print(diagnoser.generate_report(result))
    print("\n")
    
    # 输出JSON格式
    print("JSON格式:")
    result_dict = asdict(result)
    result_dict['violations'] = [v for v in result_dict['violations']]
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
