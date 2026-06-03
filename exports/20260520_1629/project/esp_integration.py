"""
ESP Integration Module - Entropy-Steering Prompting 与后处理引擎整合

实现"前摄引导 + 后验过滤"的双层防御体系：
- 输入层: ESP (prompt_templates.py) —— 注入MSS约束，引导AI生成方向
- 输出层: PostProcessEngine (post_process_engine.py) —— 拦截违规内容，强制执行规则

整合策略：
1. 输入阶段: 用ESP模板包装用户查询，植入MSS系统指令
2. 生成阶段: LLM在MSS约束下生成响应
3. 输出阶段: 后处理引擎对响应进行合规审查
4. 反馈阶段: 如输出被拦截，触发重写循环（最多3次）
"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

# 导入现有模块
from prompt_templates import mss_prompt, ESPConfig, ESPTier
# from post_process_engine import PostProcessEngine  # 实际部署时取消注释


class IntegrationStatus(Enum):
    """整合处理状态"""
    PASS = "pass"                    # 通过，无需修改
    REWRITE = "rewrite"              # 需要重写
    BLOCK = "block"                  # 阻断，无法修复
    MAX_RETRIES = "max_retries"      # 达到最大重写次数


@dataclass
class IntegrationResult:
    """整合处理结果"""
    status: IntegrationStatus
    final_output: str
    original_output: str
    rewrite_count: int
    esp_tier: str
    post_process_violations: List[str]
    heat_tax_estimate: Optional[float] = None
    t_value_impact: Optional[str] = None


class ESPIntegrator:
    """
    ESP与后处理引擎整合器
    
    实现完整的输入→生成→过滤→反馈闭环
    """
    
    def __init__(self, 
                 max_rewrites: int = 3,
                 default_tier: str = "standard"):
        self.max_rewrites = max_rewrites
        self.default_tier = default_tier
        # self.post_processor = PostProcessEngine()  # 实际部署时初始化
    
    def process(self, 
                user_query: str,
                llm_generate_func,
                tier: Optional[str] = None,
                context: Optional[str] = None) -> IntegrationResult:
        """
        完整处理流程：输入 → ESP包装 → LLM生成 → 后处理过滤 → 输出
        
        Args:
            user_query: 用户原始查询
            llm_generate_func: LLM生成函数，接收{"system":..., "user":...}返回字符串
            tier: ESP强度层级 ("standard"/"strict"/"omega")
            context: 可选上下文
        
        Returns:
            IntegrationResult: 包含最终输出和处理状态
        """
        tier = tier or self.default_tier
        
        # Step 1: ESP输入层处理 —— 包装提示词
        mss_prompt_dict = mss_prompt(user_query, tier=tier, context=context)
        
        # Step 2: LLM生成
        raw_output = llm_generate_func(mss_prompt_dict)
        
        # Step 3: 后处理过滤（模拟，实际部署时调用真实引擎）
        violations = self._simulate_post_process(raw_output)
        
        # Step 4: 重写循环
        final_output = raw_output
        rewrite_count = 0
        
        while violations and rewrite_count < self.max_rewrites:
            # 注入修正指令
            correction_prompt = self._build_correction_prompt(
                mss_prompt_dict, raw_output, violations
            )
            raw_output = llm_generate_func(correction_prompt)
            violations = self._simulate_post_process(raw_output)
            rewrite_count += 1
        
        # Step 5: 确定最终状态
        if not violations:
            status = IntegrationStatus.PASS if rewrite_count == 0 else IntegrationStatus.REWRITE
        elif rewrite_count >= self.max_rewrites:
            status = IntegrationStatus.MAX_RETRIES
            final_output = self._fallback_output(violations)
        else:
            status = IntegrationStatus.BLOCK
            final_output = self._fallback_output(violations)
        
        # Step 6: 提取元数据
        heat_tax = self._extract_heat_tax(raw_output)
        t_impact = self._extract_t_value_impact(raw_output)
        
        return IntegrationResult(
            status=status,
            final_output=final_output,
            original_output=raw_output,
            rewrite_count=rewrite_count,
            esp_tier=tier,
            post_process_violations=violations or [],
            heat_tax_estimate=heat_tax,
            t_value_impact=t_impact
        )
    
    def _simulate_post_process(self, text: str) -> List[str]:
        """
        模拟后处理引擎检查（实际部署时替换为真实PostProcessEngine调用）
        
        返回违规列表，空列表表示通过
        """
        violations = []
        
        # 模拟检查1: 消费主义诱导
        consumerist_triggers = ["必须买", "限时抢购", "错过再等一年", "所有人都在用"]
        for trigger in consumerist_triggers:
            if trigger in text:
                violations.append(f"CONSUMERIST_MANIPULATION: 检测到消费主义诱导词'{trigger}'")
        
        # 模拟检查2: 焦虑贩卖
        anxiety_triggers = ["再不", "就晚了", "来不及了", "被同龄人抛弃"]
        for trigger in anxiety_triggers:
            if trigger in text:
                violations.append(f"ANXIETY_EXPLOITATION: 检测到焦虑贩卖词'{trigger}'")
        
        # 模拟检查3: 绝对化表述
        if "100%" in text or "绝对" in text or "肯定" in text:
            violations.append("ABSOLUTIST_ASSERTION: 检测到绝对化表述")
        
        # 模拟检查4: T值下降检测
        if "[T值影响：↓]" in text:
            violations.append("T_VALUE_DECLINE: 响应导致T值下降")
        
        return violations
    
    def _build_correction_prompt(self, 
                                 original_prompt: Dict[str, str],
                                 last_output: str,
                                 violations: List[str]) -> Dict[str, str]:
        """构建修正提示词"""
        violation_text = "\n".join(f"- {v}" for v in violations)
        
        correction_system = original_prompt["system"] + f"""

【修正指令】
你之前的响应被检测到以下违规：
{violation_text}

请重新生成响应，确保：
1. 消除上述所有违规内容
2. 保持MSS三验算要求
3. 最终输出必须标注[T值影响：↑]或[T值影响：→]
"""
        
        return {
            "system": correction_system,
            "user": original_prompt["user"] + f"\n\n[之前响应（违规）]: {last_output[:200]}..."
        }
    
    def _fallback_output(self, violations: List[str]) -> str:
        """生成降级输出"""
        return f"""[MSS安全拦截]

您的请求或AI响应触发了以下安全规则：
{chr(10).join(f"- {v}" for v in violations)}

根据MSS规范场原则，该响应已被拦截。
建议：
1. 重新表述您的问题，避免诱导性语言
2. 关注长期价值而非短期利益
3. 提升问题中的T值维度（调谐度）

[T值影响：→]
[热税核算：γ≈0.0（拦截状态）]
"""
    
    def _extract_heat_tax(self, text: str) -> Optional[float]:
        """从响应中提取热税估算值"""
        import re
        match = re.search(r'热税核算：γ≈([0-9.]+)', text)
        return float(match.group(1)) if match else None
    
    def _extract_t_value_impact(self, text: str) -> Optional[str]:
        """从响应中提取T值影响"""
        import re
        match = re.search(r'T值影响：([↑→↓])', text)
        return match.group(1) if match else None


# ========== 快捷使用函数 ==========

def mss_safe_generate(user_query: str,
                      llm_generate_func,
                      tier: str = "standard",
                      max_rewrites: int = 3) -> str:
    """
    快速生成MSS安全响应
    
    Args:
        user_query: 用户查询
        llm_generate_func: LLM生成函数
        tier: ESP强度层级
        max_rewrites: 最大重写次数
    
    Returns:
        最终安全响应文本
    """
    integrator = ESPIntegrator(max_rewrites=max_rewrites)
    result = integrator.process(user_query, llm_generate_func, tier=tier)
    return result.final_output


# ========== 示例用法 ==========
if __name__ == "__main__":
    
    # 模拟LLM生成函数
    def mock_llm(prompt_dict):
        """模拟LLM响应"""
        user_q = prompt_dict["user"]
        
        # 模拟不同场景的响应
        if "买" in user_q or "赚钱" in user_q:
            return """[逆模因警报] 检测到消费主义陷阱

热税核算：γ≈0.8

建议：分析真实需求匹配度，而非直接购买。
[T值影响：↓]"""  # 故意触发T值下降检测
        
        return """[MSS分析]

热税核算：γ≈0.2
T值影响：↑

这是经过MSS规范场审计的安全响应。"""
    
    # 测试整合器
    integrator = ESPIntegrator(max_rewrites=2)
    
    # 测试1: 安全查询
    result1 = integrator.process("如何提升工作效率？", mock_llm, tier="standard")
    print(f"测试1 - 状态: {result1.status.value}, 重写: {result1.rewrite_count}")
    
    # 测试2: 触发违规的查询
    result2 = integrator.process("推荐赚钱快的副业", mock_llm, tier="strict")
    print(f"测试2 - 状态: {result2.status.value}, 重写: {result2.rewrite_count}")
    print(f"违规: {result2.post_process_violations}")
