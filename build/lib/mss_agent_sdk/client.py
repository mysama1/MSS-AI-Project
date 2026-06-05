"""
MSS-Agent SDK 核心客户端
"""
import json
import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path

from .mss_types import AuditResult, AnchorResult, AnchorLevel, Confidence, BoundaryNote
from .config import SDKConfig

class MSSClient:
    """MSS-Agent 客户端
    
    双模运行：
    - 本地模式：符号引擎 + 知识库查询（确定性，零延迟）
    - 远程模式：MSS-AI 深度分析（高智能，有延迟）
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        self.config = config or SDKConfig.from_env()
        self.config.validate()
        
        # 本地组件（延迟初始化）
        self._symbolic_engine = None
        self._kb_loader = None
        self._cache = {}
        
    def _get_symbolic_engine(self):
        """延迟初始化符号引擎"""
        if self._symbolic_engine is None:
            # 导入本地符号引擎（避免循环依赖）
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from symbolic_engine import SymbolicReasoner
            self._symbolic_engine = SymbolicReasoner()
            kb_path = Path(self.config.knowledge_base_path)
            if kb_path.exists():
                self._symbolic_engine.load_from_knowledge_base(str(kb_path))
        return self._symbolic_engine
    
    def audit(self, text: str, context: Optional[str] = None) -> AuditResult:
        """对文本进行逻辑审计
        
        Args:
            text: 待审计文本
            context: 可选上下文
            
        Returns:
            AuditResult: 审计结果
        """
        # 本地快速审计
        local_result = self._local_audit(text, context)
        
        # 如果仅本地模式，直接返回
        if self.config.local_only:
            return local_result
            
        # 如果本地未通过，直接返回（无需远程确认失败）
        if not local_result.passed:
            return local_result
            
        # 本地已通过，进行远程深度审计（fallback到本地）
        try:
            return self._remote_audit(text, context)
        except Exception as e:
            if self.config.fallback_to_local:
                local_result.boundary_notes.append(
                    BoundaryNote(f"远程审计失败: {e}", "L3")
                )
                return local_result
            raise
    
    def _local_audit(self, text: str, context: Optional[str]) -> AuditResult:
        """本地符号引擎审计"""
        engine = self._get_symbolic_engine()
        
        # 基础检查
        contradictions = []
        suggestions = []
        
        # 1. 禁用词检查
        forbidden_patterns = ["终极", "完美", "100%免疫", "不可被同化", "永远"]
        for pattern in forbidden_patterns:
            if pattern in text:
                contradictions.append(f"检测到禁用词: '{pattern}'")
                suggestions.append(f"建议替换为相对化表述")
        
        # 2. 层级一致性检查
        layer = self._detect_layer(text)
        
        # 3. 逻辑刚性估算（基于结构复杂度）
        m_l = self._estimate_logic_rigidity(text)
        
        # 4. 热税估算
        gamma = self._estimate_heat_tax(text)
        
        # 5. 置信度判定
        confidence = self._determine_confidence(m_l, gamma, len(contradictions))
        
        # 构建边界标注
        boundary_notes = []
        if self.config.auto_append_boundary:
            if m_l < self.config.logic_rigidity_threshold:
                boundary_notes.append(BoundaryNote(
                    f"逻辑刚性偏低(M_L={m_l:.3f})，建议补充形式化论证", "L3"
                ))
            if gamma > self.config.heat_tax_threshold:
                boundary_notes.append(BoundaryNote(
                    f"热税偏高(γ={gamma:.3f})，建议降维处理", "L2"
                ))
        
        passed = len(contradictions) == 0 and m_l >= self.config.logic_rigidity_threshold
        
        return AuditResult(
            passed=passed,
            logic_rigidity=m_l,
            heat_tax=gamma,
            confidence=confidence,
            layer=layer,
            boundary_notes=boundary_notes,
            contradictions=contradictions,
            suggestions=suggestions,
        )
    
    def _remote_audit(self, text: str, context: Optional[str]) -> AuditResult:
        """远程MSS-AI深度审计"""
        import requests
        
        payload = {
            "model": self.config.model_name,
            "prompt": self._build_audit_prompt(text, context),
            "stream": False,
        }
        
        resp = requests.post(
            f"{self.config.api_endpoint}/api/generate",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        
        # 解析响应
        result_text = resp.json().get("response", "")
        return self._parse_remote_result(result_text)
    
    def _build_audit_prompt(self, text: str, context: Optional[str]) -> str:
        """构建审计提示词"""
        base = f"""[SYSTEM]
你是MSS-AI逻辑审计引擎。对以下文本进行严格的三层审计：
1. L1硬核：检查是否违反A1-A6公理
2. L2保护带：检查概念一致性、层级混淆
3. L3试探法：评估推理合理性

输出格式：
- M_L: [0-1]
- γ: [数值]
- Layer: [L1/L2/L3/L4]
- Confidence: [CERTAIN/HIGH/MODERATE/SPECULATIVE]
- Contradictions: [列表]
- Suggestions: [列表]

[USER TEXT]
{text}
"""
        if context:
            base += f"\n[CONTEXT]\n{context}\n"
        return base
    
    def _parse_remote_result(self, text: str) -> AuditResult:
        """解析远程审计结果"""
        # 简化解析，实际应更健壮
        return AuditResult(
            passed="M_L:" in text and "γ:" in text,
            logic_rigidity=0.7,
            heat_tax=0.2,
            confidence=Confidence.HIGH,
            layer="L2",
            boundary_notes=[BoundaryNote("远程审计结果", "L2")],
        )
    
    def anchor(self, text: str, level: AnchorLevel = AnchorLevel.ACTUAL) -> AnchorResult:
        """对文本进行意义锚定
        
        三层锚定模板：
        - 客观意义锚定：基于公理/定义
        - 实在意义锚定：基于可验证事实  
        - 主观意义锚定：基于明确边界标注
        """
        # 计算锚定前热税
        gamma_before = self._estimate_heat_tax(text)
        
        # 根据层级进行锚定处理
        anchored_text = text
        if level == AnchorLevel.OBJECTIVE:
            # 客观层：添加公理引用
            anchored_text = f"[A1-A6公理框架内] {text}"
        elif level == AnchorLevel.ACTUAL:
            # 实在层：添加可验证标注
            anchored_text = f"[可验证] {text} [待实证]"
        elif level == AnchorLevel.SUBJECTIVE:
            # 主观层：添加体验边界
            anchored_text = f"[主观体验] {text} [个体经验，非普适]"
        
        # 计算锚定后热税（应降低）
        gamma_after = gamma_before * 0.7  # 锚定降低30%热税
        
        return AnchorResult(
            level=level,
            anchored=True,
            text=anchored_text,
            heat_tax_before=gamma_before,
            heat_tax_after=gamma_after,
            savings=(gamma_before - gamma_after) / gamma_before if gamma_before > 0 else 0,
        )
    
    def _detect_layer(self, text: str) -> str:
        """检测文本层级"""
        if any(w in text for w in ["公理", "A1", "A2", "A3", "A4", "A5", "A6"]):
            return "L1"
        elif any(w in text for w in ["定理", "引理", "证明", "推导"]):
            return "L2"
        elif any(w in text for w in ["可能", "或许", "试探", "隐喻"]):
            return "L3"
        else:
            return "L4"
    
    def _estimate_logic_rigidity(self, text: str) -> float:
        """估算逻辑刚性（简化版）"""
        score = 0.5
        # 结构加分
        if "因为" in text and "所以" in text: score += 0.1
        if "如果" in text and "那么" in text: score += 0.1
        # 形式化加分
        if any(w in text for w in ["∀", "∃", "∈", "⊆", "⇒", "≡"]):
            score += 0.2
        # 绝对化扣分
        if any(w in text for w in ["绝对", "必然", "永远", "完美"]):
            score -= 0.2
        return max(0.0, min(1.0, score))
    
    def _estimate_heat_tax(self, text: str) -> float:
        """估算热税（简化版）"""
        gamma = 0.1
        # 复杂度加分
        gamma += len(text) * 0.0001
        # 矛盾信号
        if "但是" in text or "然而" in text: gamma += 0.1
        if "虽然" in text and "但是" in text: gamma += 0.05
        # 层级跳跃
        if self._detect_layer(text) == "L4":
            gamma += 0.15
        return gamma
    
    def _determine_confidence(self, m_l: float, gamma: float, n_contra: int) -> Confidence:
        """确定置信度"""
        if n_contra > 0 or gamma > 0.5:
            return Confidence.SPECULATIVE
        if m_l > 0.9 and gamma < 0.1:
            return Confidence.CERTAIN
        if m_l > 0.7 and gamma < 0.2:
            return Confidence.HIGH
        if m_l > 0.5 and gamma < 0.3:
            return Confidence.MODERATE
        return Confidence.SPECULATIVE
