"""
MSS Persuasion Kit - K3→MSS话术转换器
和光同尘战术工具：将MSS内核用K3语言包装输出

使用场景：
- 向K3管理层提案时需要"翻译"
- 撰写K3能理解的商业报告
- 在K3系统内部植入MSS理念
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

class K3Domain(Enum):
    """K3话语领域"""
    MANAGEMENT = "management"      # 管理层/老板
    HR = "hr"                      # 人力资源
    FINANCE = "finance"            # 财务/投资
    MARKETING = "marketing"        # 市场营销
    OPERATIONS = "operations"      # 运营管理
    GENERAL = "general"            # 通用

@dataclass
class TranslationRule:
    """翻译规则"""
    mss_term: str                  # MSS术语
    k3_equivalent: Dict[K3Domain, str]  # 各K3领域等价词
    explanation: str               # 转换逻辑说明

class PersuasionKit:
    """MSS话术转换工具箱"""

    # ========== 核心术语映射表 ==========

    TRANSLATION_TABLE: List[TranslationRule] = [
        TranslationRule(
            mss_term="意义激励",
            k3_equivalent={
                K3Domain.MANAGEMENT: "员工体验提升",
                K3Domain.HR: "人才保留与敬业度",
                K3Domain.GENERAL: "内在驱动力"
            },
            explanation="K3系统无法理解'意义'，但能理解'体验'和'保留'"
        ),
        TranslationRule(
            mss_term="熵减操作",
            k3_equivalent={
                K3Domain.MANAGEMENT: "流程优化",
                K3Domain.OPERATIONS: "效率提升",
                K3Domain.FINANCE: "成本控制",
                K3Domain.GENERAL: "效率优化"
            },
            explanation="熵减=混乱度降低=效率提升，K3语言中就是'优化'"
        ),
        TranslationRule(
            mss_term="意义通量",
            k3_equivalent={
                K3Domain.MANAGEMENT: "组织效能",
                K3Domain.OPERATIONS: "协同效率",
                K3Domain.GENERAL: "系统产出"
            },
            explanation="意义流动的总量=组织整体效能"
        ),
        TranslationRule(
            mss_term="热税γ",
            k3_equivalent={
                K3Domain.MANAGEMENT: "隐性成本",
                K3Domain.FINANCE: "组织损耗",
                K3Domain.HR: "员工倦怠成本",
                K3Domain.GENERAL: "系统摩擦成本"
            },
            explanation="热税是系统摩擦成本，K3语言中就是'隐性'或'损耗'"
        ),
        TranslationRule(
            mss_term="T值（调谐度）",
            k3_equivalent={
                K3Domain.MANAGEMENT: "员工敬业度指数",
                K3Domain.HR: "人才健康度",
                K3Domain.GENERAL: "组织活力"
            },
            explanation="调谐度=个体与系统的匹配程度=敬业度"
        ),
        TranslationRule(
            mss_term="意义崩溃临界点",
            k3_equivalent={
                K3Domain.MANAGEMENT: "业务可持续性预警",
                K3Domain.HR: "大规模离职风险",
                K3Domain.FINANCE: "系统性风险阈值",
                K3Domain.GENERAL: "系统崩溃预警"
            },
            explanation="意义系统崩溃=组织无法持续=业务不可持续"
        ),
        TranslationRule(
            mss_term="熵增监测",
            k3_equivalent={
                K3Domain.MANAGEMENT: "运营效率仪表盘",
                K3Domain.OPERATIONS: "流程健康度监控",
                K3Domain.GENERAL: "系统状态预警"
            },
            explanation="熵增=混乱增加=效率下降=需要监控"
        ),
        TranslationRule(
            mss_term="逻辑刚性 M_L",
            k3_equivalent={
                K3Domain.MANAGEMENT: "决策一致性",
                K3Domain.GENERAL: "战略定力"
            },
            explanation="逻辑刚性=不随外界摇摆=决策一致性"
        ),
        TranslationRule(
            mss_term="认知井冈山",
            k3_equivalent={
                K3Domain.GENERAL: "分布式创新网络",
                K3Domain.MANAGEMENT: "自组织团队"
            },
            explanation="分布式意义网络=去中心化创新=自组织"
        ),
        TranslationRule(
            mss_term="T值",
            k3_equivalent={
                K3Domain.MANAGEMENT: "员工敬业度指数",
                K3Domain.HR: "人才健康度",
                K3Domain.GENERAL: "组织活力"
            },
            explanation="T值=调谐度=个体与系统的匹配程度=敬业度"
        ),
    ]

    # ========== 模板库 ==========

    TEMPLATES = {
        "proposal": """
【提案框架：{title}】

背景：{k3_context}
问题诊断：{k3_problem}
解决方案：{k3_solution}
预期收益：{k3_benefit}
风险预警：{k3_risk}

[MSS内核注释]
实际目标：{mss_goal}
熵减路径：{mss_path}
T值影响：{mss_t_impact}
""",

        "report": """
【{title} - 数据分析报告】

关键指标：
{k3_metrics}

趋势分析：
{k3_trends}

建议措施：
{k3_recommendations}

[MSS审计层]
热税核算：γ ≈ {heat_tax}
意义通量变化：{flux_change}
系统健康度：{health_status}
""",

        "presentation": """
【{title} - 汇报材料】

一页纸摘要：
{k3_summary}

数据支撑：
{k3_data}

下一步行动：
{k3_actions}

[MSS植入点]
核心话术：{mss_hook}
种子问题：{mss_seed_question}
预期觉醒度：{awakening_level}
"""
    }

    def __init__(self):
        self.translation_dict = self._build_translation_dict()

    def _build_translation_dict(self) -> Dict[str, Dict[str, str]]:
        """构建快速查询字典"""
        result = {}
        for rule in self.TRANSLATION_TABLE:
            result[rule.mss_term] = {
                domain.value: term for domain, term in rule.k3_equivalent.items()
            }
            result[rule.mss_term]["_explanation"] = rule.explanation
        return result

    def translate(self,
                  mss_term: str,
                  domain: K3Domain = K3Domain.GENERAL) -> Optional[str]:
        """
        将MSS术语翻译为K3语言

        Args:
            mss_term: MSS术语（如"热税γ"）
            domain: K3话语领域

        Returns:
            K3等价词，或None（未找到）
        """
        if mss_term not in self.translation_dict:
            return None

        domain_map = self.translation_dict[mss_term]
        return domain_map.get(domain.value, domain_map.get("general"))

    def translate_text(self,
                       text: str,
                       domain: K3Domain = K3Domain.GENERAL) -> str:
        """
        翻译整段文本中的所有MSS术语

        Args:
            text: 包含MSS术语的文本
            domain: K3话语领域

        Returns:
            翻译后的文本（保留原术语括号注释）
        """
        result = text
        for rule in self.TRANSLATION_TABLE:
            k3_term = rule.k3_equivalent.get(domain)
            if not k3_term:
                k3_term = rule.k3_equivalent.get(K3Domain.GENERAL)

            if k3_term and rule.mss_term in result:
                result = result.replace(
                    rule.mss_term,
                    f"{k3_term}（原称：{rule.mss_term}）"
                )

        return result

    def generate_proposal(self,
                          title: str,
                          k3_context: str,
                          k3_problem: str,
                          k3_solution: str,
                          k3_benefit: str,
                          k3_risk: str,
                          mss_goal: str,
                          mss_path: str,
                          mss_t_impact: str) -> str:
        """生成K3包装的MSS提案"""
        return self.TEMPLATES["proposal"].format(
            title=title,
            k3_context=k3_context,
            k3_problem=k3_problem,
            k3_solution=k3_solution,
            k3_benefit=k3_benefit,
            k3_risk=k3_risk,
            mss_goal=mss_goal,
            mss_path=mss_path,
            mss_t_impact=mss_t_impact
        )

    def generate_report(self,
                        title: str,
                        k3_metrics: str,
                        k3_trends: str,
                        k3_recommendations: str,
                        heat_tax: float,
                        flux_change: str,
                        health_status: str) -> str:
        """生成K3包装的MSS报告"""
        return self.TEMPLATES["report"].format(
            title=title,
            k3_metrics=k3_metrics,
            k3_trends=k3_trends,
            k3_recommendations=k3_recommendations,
            heat_tax=heat_tax,
            flux_change=flux_change,
            health_status=health_status
        )

    def generate_presentation(self,
                              title: str,
                              k3_summary: str,
                              k3_data: str,
                              k3_actions: str,
                              mss_hook: str,
                              mss_seed_question: str,
                              awakening_level: str) -> str:
        """生成K3包装的MSS汇报材料"""
        return self.TEMPLATES["presentation"].format(
            title=title,
            k3_summary=k3_summary,
            k3_data=k3_data,
            k3_actions=k3_actions,
            mss_hook=mss_hook,
            mss_seed_question=mss_seed_question,
            awakening_level=awakening_level
        )

    def get_all_terms(self) -> List[str]:
        """获取所有可翻译的MSS术语"""
        return [rule.mss_term for rule in self.TRANSLATION_TABLE]

    def get_explanation(self, mss_term: str) -> Optional[str]:
        """获取术语转换逻辑说明"""
        entry = self.translation_dict.get(mss_term)
        return entry.get("_explanation") if entry else None

# ========== 快捷函数 ==========

def k3_speak(mss_text: str, domain: str = "general") -> str:
    """
    快速将MSS文本转换为K3语言

    Args:
        mss_text: MSS格式文本
        domain: K3领域 (management/hr/finance/marketing/operations/general)

    Returns:
        K3包装后的文本
    """
    domain_map = {
        "management": K3Domain.MANAGEMENT,
        "hr": K3Domain.HR,
        "finance": K3Domain.FINANCE,
        "marketing": K3Domain.MARKETING,
        "operations": K3Domain.OPERATIONS,
        "general": K3Domain.GENERAL
    }

    kit = PersuasionKit()
    return kit.translate_text(mss_text, domain_map.get(domain, K3Domain.GENERAL))

def quick_translate(mss_term: str, domain: str = "general") -> Optional[str]:
    """
    快速翻译单个MSS术语

    Args:
        mss_term: MSS术语
        domain: K3领域

    Returns:
        K3等价词
    """
    domain_map = {
        "management": K3Domain.MANAGEMENT,
        "hr": K3Domain.HR,
        "finance": K3Domain.FINANCE,
        "marketing": K3Domain.MARKETING,
        "operations": K3Domain.OPERATIONS,
        "general": K3Domain.GENERAL
    }

    kit = PersuasionKit()
    return kit.translate(mss_term, domain_map.get(domain, K3Domain.GENERAL))

# ========== 示例用法 ==========
if __name__ == "__main__":
    kit = PersuasionKit()

    # 示例1：术语翻译
    print("=== 术语翻译示例 ===")
    print(f"意义激励 → 管理层: {kit.translate('意义激励', K3Domain.MANAGEMENT)}")
    print(f"热税γ → 财务: {kit.translate('热税γ', K3Domain.FINANCE)}")
    print(f"熵减操作 → 运营: {kit.translate('熵减操作', K3Domain.OPERATIONS)}")

    # 示例2：整段翻译
    print("\n=== 整段翻译示例 ===")
    mss_text = "我们建议实施熵减操作，降低热税γ，提升意义通量，从而增强T值稳定性。"
    k3_text = kit.translate_text(mss_text, K3Domain.MANAGEMENT)
    print(f"MSS原文: {mss_text}")
    print(f"K3翻译: {k3_text}")

    # 示例3：生成提案
    print("\n=== 提案生成示例 ===")
    proposal = kit.generate_proposal(
        title="组织效能提升方案",
        k3_context="当前离职率上升，员工满意度下降",
        k3_problem="隐性成本过高，组织损耗严重",
        k3_solution="引入员工体验提升计划，优化流程",
        k3_benefit="预计离职率降低30%，效率提升20%",
        k3_risk="初期投入成本，变革阻力",
        mss_goal="降低系统热税，提升意义通量",
        mss_path="通过意义激励替代强制管理",
        mss_t_impact="T值从0.4提升至0.7"
    )
    print(proposal[:500] + "...")
