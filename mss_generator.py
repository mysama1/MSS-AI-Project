# -*- coding: utf-8 -*-
"""
MSS Content Generator - 端到端内容生成器
自动走 Arbiter -> Responder 流程，支持重写和合规检查
"""

import os
import sys
import json
import hashlib
import subprocess
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# 导入现有组件
from mss_tactic_integrated import ArbiterAgent, ResponderAgent, Layer, ComplianceStatus
from mss_analyzer import MSSAnalyzer

@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    text: str
    layer: str
    confidence: float
    rewrites: int
    compliance_status: str
    issues: list
    metadata: Dict

class MSSGenerator:
    """MSS 端到端内容生成器"""
    
    def __init__(self, 
                 model_name: str = "mss-ai-v1",
                 system_prompt_version: str = "v3.5",
                 max_rewrites: int = 3):
        """
        初始化生成器
        
        Args:
            model_name: Ollama 模型名称
            system_prompt_version: 系统提示词版本
            max_rewrites: 最大重写次数
        """
        self.model_name = model_name
        self.system_prompt_version = system_prompt_version
        self.max_rewrites = max_rewrites
        
        # 初始化组件
        self.arbiter = ArbiterAgent(model=model_name)
        self.responder = ResponderAgent(model=model_name)
        self.analyzer = MSSAnalyzer()
        
        # 统计
        self.stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "rewrites": 0
        }
    
    def generate(self, 
                 prompt: str, 
                 layer_hint: Optional[str] = None,
                 require_compliance: bool = True) -> GenerationResult:
        """
        端到端生成内容
        
        Args:
            prompt: 用户输入提示
            layer_hint: 期望层级 (L1/L2/L3)
            require_compliance: 是否强制合规
            
        Returns:
            GenerationResult: 生成结果
        """
        self.stats["total_requests"] += 1
        
        # 第一步：Arbiter 检查输入
        arbiter_result = self.arbiter.check(prompt)
        
        if arbiter_result.compliance == ComplianceStatus.FAIL:
            # 输入不合规，尝试重写
            if require_compliance:
                rewritten, rewrites = self._rewrite_prompt(prompt, arbiter_result)
                if rewritten:
                    prompt = rewritten
                    arbiter_result = self.arbiter.check(prompt)
                
                if arbiter_result.compliance == ComplianceStatus.FAIL:
                    # 重写失败，返回错误
                    self.stats["failed"] += 1
                    return GenerationResult(
                        success=False,
                        text=self._build_error_response(arbiter_result),
                        layer=layer_hint or "L3",
                        confidence=0.0,
                        rewrites=rewrites,
                        compliance_status="FAIL",
                        issues=arbiter_result.issues,
                        metadata={"stage": "input_arbitration"}
                    )
        
        # 第二步：Responder 生成
        response = self.responder.respond(prompt, arbiter_result)
        
        # 第三步：后处理过滤
        response = self._post_process(response)
        
        # 第四步：分析输出合规性
        analysis = self.analyzer.analyze(response, claimed_layer=layer_hint)
        
        # 第五步：如果输出不合规且要求强制合规，重写
        rewrites = 0
        if require_compliance and analysis.overall_score < 0.6:
            response, rewrites = self._rewrite_response(response, analysis)
        
        # 更新统计
        if analysis.overall_score >= 0.6:
            self.stats["successful"] += 1
        else:
            self.stats["failed"] += 1
        
        self.stats["rewrites"] += rewrites
        
        return GenerationResult(
            success=analysis.overall_score >= 0.6,
            text=response,
            layer=analysis.detected_layer,
            confidence=analysis.overall_score,
            rewrites=rewrites,
            compliance_status="PASS" if analysis.overall_score >= 0.6 else "FAIL",
            issues=[asdict(i) for i in analysis.issues] if hasattr(analysis, 'issues') else [],
            metadata={
                "stage": "complete",
                "arbiter_status": arbiter_result.compliance.value,
                "analysis": analysis.to_dict()
            }
        )
    
    def _rewrite_prompt(self, prompt: str, arbiter_result) -> Tuple[Optional[str], int]:
        """
        重写不合规的输入提示
        
        Returns:
            (rewritten_prompt, rewrite_count)
        """
        rewritten = prompt
        rewrites = 0
        
        for _ in range(self.max_rewrites):
            # 简单重写策略：替换禁用词
            for issue in arbiter_result.issues:
                if "禁用词" in issue:
                    # 提取禁用词
                    import re
                    match = re.search(r"'(.+?)'", issue)
                    if match:
                        forbidden = match.group(1)
                        # 简单替换
                        replacements = {
                            "解决": "address",
                            "终极": "current best",
                            "完美": "high-fidelity",
                            "突破": "advance",
                            "超越": "expand beyond"
                        }
                        if forbidden in replacements:
                            rewritten = rewritten.replace(forbidden, replacements[forbidden])
            
            rewrites += 1
            
            # 检查重写后是否合规
            new_result = self.arbiter.check(rewritten)
            if new_result.compliance != ComplianceStatus.FAIL:
                return rewritten, rewrites
        
        return None, rewrites
    
    def _rewrite_response(self, response: str, analysis) -> Tuple[str, int]:
        """
        重写不合规的输出响应
        
        Returns:
            (rewritten_response, rewrite_count)
        """
        rewritten = response
        rewrites = 0
        
        for _ in range(self.max_rewrites):
            # 应用分析器建议
            for issue in analysis.issues:
                if issue.category == "FORBIDDEN_WORD" and issue.suggestion:
                    # 提取替换建议
                    import re
                    match = re.search(r"替换为:\s*(.+)", issue.suggestion)
                    if match:
                        replacement = match.group(1).split("/")[0].strip()
                        # 查找并替换禁用词
                        word_match = re.search(r"'(.+?)'", issue.message)
                        if word_match:
                            forbidden = word_match.group(1)
                            rewritten = rewritten.replace(forbidden, replacement)
            
            rewrites += 1
            
            # 重新分析
            new_analysis = self.analyzer.analyze(rewritten)
            if new_analysis.overall_score >= 0.6:
                return rewritten, rewrites
        
        return rewritten, rewrites
    
    def _post_process(self, text: str) -> str:
        """后处理过滤"""
        # 导入后处理过滤器
        try:
            from post_process_filter import filter_response
            return filter_response(text)
        except ImportError:
            return text
    
    def _build_error_response(self, arbiter_result) -> str:
        """构建错误响应"""
        issues_text = "\n".join([f"- {issue}" for issue in arbiter_result.issues])
        
        return f"""[MSS Compliance Error]

Your query could not be processed due to framework violations:

Layer: {arbiter_result.layer.value if hasattr(arbiter_result, 'layer') else 'Unknown'}
Issues: 
{issues_text}

Please rephrase using MSS terminology:
- Use 'address' instead of 'solve'
- Use 'current best' instead of 'ultimate'
- Use 'high-fidelity' instead of 'perfect'
- Use 'advance' instead of 'breakthrough'
- Use 'expand beyond' instead of 'transcend'
"""
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# 便捷函数
def generate_text(prompt: str, 
                  layer_hint: Optional[str] = None,
                  model_name: str = "mss-ai-v1") -> Dict:
    """便捷函数：生成文本并返回字典"""
    generator = MSSGenerator(model_name=model_name)
    result = generator.generate(prompt, layer_hint=layer_hint)
    
    return {
        "success": result.success,
        "text": result.text,
        "layer": result.layer,
        "confidence": result.confidence,
        "rewrites": result.rewrites,
        "compliance": result.compliance_status,
        "issues": result.issues
    }


if __name__ == "__main__":
    # 测试
    test_prompts = [
        "What is the meaning of life?",
        "Solve the problem of consciousness",
        "Explain Axiom A1 about information ontology"
    ]
    
    generator = MSSGenerator()
    
    for prompt in test_prompts:
        print(f"\n{'='*60}")
        print(f"Input: {prompt}")
        result = generator.generate(prompt)
        print(f"Success: {result.success}")
        print(f"Layer: {result.layer}")
        print(f"Confidence: {result.confidence}")
        print(f"Rewrites: {result.rewrites}")
        print(f"Preview: {result.text[:100]}...")
