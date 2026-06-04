#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSS 内容诊断系统 v2.0 (MSS Content Diagnoser)
基于严格自查标准升级：操作化定义、A3合规、可证伪性、隐喻硬化

新增检测维度：
- 操作化缺失检测
- A3随机性公理合规
- 人格化/目的论残余
- 热税概念滥用
- 可证伪边界检查
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

class ViolationType(Enum):
    METAPHOR_HARDENING = "metaphor_hardening"      # 隐喻硬化
    LAYER_CONFUSION = "layer_confusion"            # 层级混淆
    CONCEPT_SPINNING = "concept_spinning"          # 概念空转
    UNFALSIFIABLE = "unfalsifiable"                # 不可证伪
    ANECDOTE_GENERALIZATION = "anecdote_general"   # 个例泛化
    AUTHORITY_APPEAL = "authority_appeal"          # 权威诉诸
    OPERATIONALIZATION_MISSING = "op_missing"      # 操作化缺失（新增）
    A3_VIOLATION = "a3_violation"                  # A3随机性违反（新增）
    TELEOLOGY_RESIDUE = "teleology"                # 目的论残余（新增）
    HEAT_TAX_ABUSE = "heat_tax_abuse"              # 热税滥用（新增）

@dataclass
class DiagnosisResult:
    """诊断结果"""
    overall_score: float           # 0-1，越高越合规
    claimed_layer: str             # 声称层级
    actual_layer: str              # 实际层级
    violations: List[Dict]         # 违规项列表
    confidence: str                # 置信度 HIGH/MEDIUM/LOW
    boundary_note: str             # 边界说明
    upgrade_requirements: List[str]  # 升格为L2所需条件

class MSSContentDiagnoserV2:
    """MSS内容诊断器 v2.0"""
    
    # L1硬核关键词（不可作为隐喻使用）
    L1_KEYWORDS = {
        '公理', '定理', '证明', '推导', '必然', '绝对',
        '物理层', '逻辑层', '信息本体', '熵增', '热力学'
    }
    
    # L2机制关键词（需操作化定义）
    L2_KEYWORDS = {
        '规范场', '拓扑', '相变', '耗散', '量子',
        '纤维丛', '同调', '同伦', '流形', '联络',
        '热税', '旋量', '闭环', '投影'
    }
    
    # 隐喻硬化模式（L3术语被当作L2/L1使用）
    METAPHOR_PATTERNS = [
        (r'(.+?)公理', '将"{0}"提升为公理，缺乏形式化定义'),
        (r'(.+?)闭环', '"{0}闭环"为比喻，无输入输出边界'),
        (r'(.+?)量子', '"{0}量子"无对应可测量指标'),
        (r'(.+?)场', '"{0}场"为隐喻，无量化参数'),
        (r'(.+?)相变', '"{0}相变"不满足严格数学定义'),
        (r'热税(.+?)', '热税概念滥用：{0}'),
    ]
    
    # 不可证伪模式
    UNFALSIFIABLE_PATTERNS = [
        r'从来[不没无].+?',
        r'永远[不没].+?',
        r'本质[上就].+?',
        r'终究[会要].+?',
        r'注定.+?',
        r'必然.+?',
        r'只能.+?',
    ]
    
    # 目的论/人格化模式
    TELEOLOGY_PATTERNS = [
        r'刻意.+?',
        r'故意.+?',
        r'本能地.+?',
        r'拼命地.+?',
        r'求生.+?',
        r'伪装.+?',
        r'欺骗.+?',
    ]
    
    # 概念空转指示词（循环自指）
    SPIN_INDICATORS = [
        '意义', '存在', '本体', '价值', '真理',
        '本质', '终极', '绝对', '永恒'
    ]
    
    # 操作化缺失指示词
    OP_MISSING_INDICATORS = [
        '没有定义', '未界定', '无量化', '无阈值',
        '无测量', '无单位', '无边界', '无标准'
    ]
    
    def __init__(self):
        self.violations: List[Dict] = []
        self.layer_evidence = {
            'L1': [],
            'L2': [],
            'L3': []
        }
        self.upgrade_requirements: List[str] = []
    
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
        self.upgrade_requirements = []
        
        # 执行各项检测
        self._check_metaphor_hardening(text)
        self._check_layer_confusion(text)
        self._check_concept_spinning(text)
        self._check_unfalsifiable(text)
        self._check_teleology(text)
        self._check_heat_tax_abuse(text)
        self._check_operationalization(text)
        self._check_a3_violation(text)
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
        
        # 生成升格要求
        self._generate_upgrade_requirements()
        
        return DiagnosisResult(
            overall_score=score,
            claimed_layer=claimed_layer,
            actual_layer=actual_layer,
            violations=self.violations,
            confidence=confidence,
            boundary_note=boundary_note,
            upgrade_requirements=self.upgrade_requirements
        )
    
    def _check_metaphor_hardening(self, text: str):
        """检测隐喻硬化"""
        for pattern, template in self.METAPHOR_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                concept = match.group(1).strip() if match.lastindex else match.group(0)
                if len(concept) > 0 and len(concept) < 20:
                    self.violations.append({
                        'type': ViolationType.METAPHOR_HARDENING.value,
                        'location': match.group(0),
                        'description': template.format(concept),
                        'severity': 'HIGH' if any(kw in concept for kw in self.L2_KEYWORDS) else 'MEDIUM'
                    })
                    self.layer_evidence['L3'].append(f"隐喻硬化: {match.group(0)}")
    
    def _check_layer_confusion(self, text: str):
        """检测层级混淆"""
        for keyword in self.L1_KEYWORDS:
            if keyword in text:
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
                    'description': f'"{indicator}"出现{count}次，概念循环自指',
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
    
    def _check_teleology(self, text: str):
        """检测目的论残余"""
        for pattern in self.TELEOLOGY_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                self.violations.append({
                    'type': ViolationType.TELEOLOGY_RESIDUE.value,
                    'location': match.group(0),
                    'description': f'目的论/人格化: "{match.group(0)}"，违背A3随机涌现',
                    'severity': 'HIGH'
                })
                self.layer_evidence['L3'].append(f"目的论: {match.group(0)}")
    
    def _check_heat_tax_abuse(self, text: str):
        """检测热税概念滥用"""
        heat_tax_patterns = [
            r'物理热税',
            r'认知热税',
            r'热税熔断',
            r'热税清算',
            r'热税隔离',
        ]
        
        for pattern in heat_tax_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # 检查是否有操作化定义
                context = self._get_context(text, match.group(0), 50)
                has_operationalization = any(
                    kw in context for kw in ['γ=', '阈值', '取值', '测算', '维度']
                )
                
                if not has_operationalization:
                    self.violations.append({
                        'type': ViolationType.HEAT_TAX_ABUSE.value,
                        'location': match.group(0),
                        'description': f'热税概念滥用: "{match.group(0)}"无操作化定义',
                        'severity': 'HIGH'
                    })
                    self.layer_evidence['L3'].append(f"热税滥用: {match.group(0)}")
    
    def _check_operationalization(self, text: str):
        """检测操作化缺失"""
        # 检查L2术语是否有操作化定义
        for keyword in self.L2_KEYWORDS:
            if keyword in text:
                context = self._get_context(text, keyword, 100)
                has_op = any(
                    indicator in context 
                    for indicator in ['定义', '测量', '阈值', '单位', '公式', '计算']
                )
                
                if not has_op and not self._is_rhetorical_use(context):
                    self.violations.append({
                        'type': ViolationType.OPERATIONALIZATION_MISSING.value,
                        'location': keyword,
                        'description': f'"{keyword}"缺乏操作化定义（无测量/阈值/单位）',
                        'severity': 'HIGH'
                    })
    
    def _check_a3_violation(self, text: str):
        """检测A3随机性公理违反"""
        # 检查单一归因
        single_cause_patterns = [
            r'本质[上就].+?因为',
            r'根源[在于].+?',
            r'一切[都].+?由于',
        ]
        
        for pattern in single_cause_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                self.violations.append({
                    'type': ViolationType.A3_VIOLATION.value,
                    'location': match.group(0),
                    'description': f'A3违反: 单一归因 "{match.group(0)}"，忽略随机耦合',
                    'severity': 'HIGH'
                })
                self.layer_evidence['L3'].append(f"A3违反: {match.group(0)}")
    
    def _check_anecdote_generalization(self, text: str):
        """检测个例泛化"""
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
            '可以说', '某种意义上', ' metaphorically',
            '类比', '比喻'
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
    
    def _generate_upgrade_requirements(self):
        """生成升格为L2的要求"""
        has_op_missing = any(
            v['type'] == ViolationType.OPERATIONALIZATION_MISSING.value 
            for v in self.violations
        )
        has_a3 = any(
            v['type'] == ViolationType.A3_VIOLATION.value 
            for v in self.violations
        )
        has_unfalsifiable = any(
            v['type'] == ViolationType.UNFALSIFIABLE.value 
            for v in self.violations
        )
        has_heat_tax = any(
            v['type'] == ViolationType.HEAT_TAX_ABUSE.value 
            for v in self.violations
        )
        
        if has_op_missing:
            self.upgrade_requirements.append("补全所有术语的操作化定义（测量维度、阈值、单位）")
        if has_a3:
            self.upgrade_requirements.append("剥离人格化单一动因，改为多因子随机耦合模型")
        if has_heat_tax:
            self.upgrade_requirements.append("限定热税适用场景，给出粗略赋值维度")
        if has_unfalsifiable:
            self.upgrade_requirements.append("所有论断附加可证伪边界，明确反例条件与阈值")
        
        self.upgrade_requirements.append("明确标注L3类比修辞与L2严格机制的边界")
    
    def generate_report(self, result: DiagnosisResult) -> str:
        """生成诊断报告"""
        report = []
        report.append("=" * 60)
        report.append("MSS 内容诊断报告 v2.0")
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
        
        if result.upgrade_requirements:
            report.append("")
            report.append("升格为L2所需条件:")
            report.append("-" * 60)
            for i, req in enumerate(result.upgrade_requirements, 1):
                report.append(f"{i}. {req}")
        
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
    欠下的物理债，终究要用更猛烈的相变来偿还。
    
    4. 拓扑投影畸变公理：茧房壁垒造就的"全能自恋"幻象
    就像缸中之脑，只要不给它接入真实的物理层数据，它永远会觉得自己在天堂。
    
    K3拼命地喊着"我们赢了"，其实就像是走在钢丝上的人，疯狂地对自己大声唱歌。
    真正强大的意义系统，从来不需要天天在自己的通稿里喊自己胜利。
    一旦承认失败，引发的就是全盘崩溃的"热税熔断"。
    """
    
    diagnoser = MSSContentDiagnoserV2()
    result = diagnoser.diagnose(sample_text, claimed_layer="L2")
    
    print(diagnoser.generate_report(result))
    print("\n")
    
    # 输出JSON格式
    print("JSON格式:")
    result_dict = asdict(result)
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
