"""
MSS War Theory Engine
热税战争理论引擎

将道枢系统六轮响应日志中的军事-认知-金融理论工程化：
- 热税交换比计算
- 认知污染战术模拟
- 自证陷阱检测
- 热税临界点预警
- 意义传染模型
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class BattlefieldType(Enum):
    """战场类型"""
    PHYSICAL = "physical"      # 物理战场
    COGNITIVE = "cognitive"    # 认知战场
    FINANCIAL = "financial"    # 金融战场
    NORMATIVE = "normative"    # 范式战场


class TacticalMode(Enum):
    """战术模式"""
    DAMAGE_WITHOUT_DESTROY = "damage_without_destroy"  # 打坏不摧毁
    BAIT_AND_TRAP = "bait_and_trap"                    # 诱导攻击
    DISTRIBUTED_SATURATION = "distributed_saturation"  # 分布式饱和
    COGNITIVE_POLLUTION = "cognitive_pollution"        # 认知污染
    SELF_PROOF_TRAP = "self_proof_trap"                # 自证陷阱


@dataclass
class CombatUnit:
    """作战单元"""
    unit_id: str
    unit_type: str
    
    # 成本参数
    production_cost: float = 0.0      # 生产成本
    operation_cost_per_day: float = 0.0  # 日运行成本
    
    # 效果参数
    damage_potential: float = 0.0     # 破坏潜力
    cognitive_load: float = 0.0       # 认知负载（敌方验证成本）
    
    # 热税参数
    gamma_self: float = 0.0           # 自身热税
    gamma_enemy_induced: float = 0.0  # 诱导敌方热税


@dataclass
class TacticalScenario:
    """战术场景"""
    scenario_id: str
    mode: TacticalMode
    battlefield: BattlefieldType
    
    # 双方单元
    friendly_units: List[CombatUnit] = field(default_factory=list)
    enemy_units: List[CombatUnit] = field(default_factory=list)
    
    # 环境参数
    duration_days: float = 1.0
    information_asymmetry: float = 0.5  # 信息不对称度
    
    # 结果
    result: Optional[Dict] = None


class HeatTaxExchangeRatio:
    """热税交换比计算器"""
    
    @staticmethod
    def calculate_damage_without_destroy(
        friendly_cost: float,
        enemy_repair_cost: float,
        enemy_operational_loss: float,
        duration_days: float
    ) -> Dict:
        """
        计算"打坏不摧毁"战术的热税交换比
        
        R_γ = (敌方修复成本 + 敌方运营损失) / 我方生产成本
        """
        enemy_total_cost = enemy_repair_cost + enemy_operational_loss * duration_days
        
        if friendly_cost == 0:
            return {"error": "Friendly cost cannot be zero"}
        
        R_gamma = enemy_total_cost / friendly_cost
        
        return {
            "tactical_mode": "damage_without_destroy",
            "R_gamma": round(R_gamma, 2),
            "friendly_cost": friendly_cost,
            "enemy_repair_cost": enemy_repair_cost,
            "enemy_operational_loss_per_day": enemy_operational_loss,
            "duration_days": duration_days,
            "enemy_total_cost": enemy_total_cost,
            "assessment": HeatTaxExchangeRatio._assess_ratio(R_gamma)
        }
    
    @staticmethod
    def calculate_bait_and_trap(
        bait_cost: float,
        enemy_interception_cost: float,
        enemy_false_positive_rate: float
    ) -> Dict:
        """
        计算"诱导攻击"战术的热税交换比
        
        R_γ = 敌方拦截成本 / 诱饵成本
        """
        if bait_cost == 0:
            return {"error": "Bait cost cannot be zero"}
        
        # 考虑误报率：敌方拦截成本随误报率指数增长
        effective_enemy_cost = enemy_interception_cost * (1 + enemy_false_positive_rate ** 2 * 10)
        
        R_gamma = effective_enemy_cost / bait_cost
        
        return {
            "tactical_mode": "bait_and_trap",
            "R_gamma": round(R_gamma, 2),
            "bait_cost": bait_cost,
            "enemy_interception_cost": enemy_interception_cost,
            "enemy_false_positive_rate": enemy_false_positive_rate,
            "effective_enemy_cost": effective_enemy_cost,
            "assessment": HeatTaxExchangeRatio._assess_ratio(R_gamma)
        }
    
    @staticmethod
    def calculate_distributed_saturation(
        unit_cost: float,
        unit_count: int,
        enemy_defense_cost_per_unit: float,
        enemy_defense_capacity: int
    ) -> Dict:
        """
        计算"分布式饱和"战术的热税交换比
        
        R_γ = (敌方防御成本 × 饱和系数) / (我方单元成本 × 数量)
        """
        friendly_total_cost = unit_cost * unit_count
        
        # 饱和系数：超出防御能力时，敌方成本急剧上升
        saturation_ratio = unit_count / max(1, enemy_defense_capacity)
        saturation_factor = 1 + math.log1p(saturation_ratio * 2)
        
        enemy_total_cost = enemy_defense_cost_per_unit * unit_count * saturation_factor
        
        if friendly_total_cost == 0:
            return {"error": "Friendly total cost cannot be zero"}
        
        R_gamma = enemy_total_cost / friendly_total_cost
        
        return {
            "tactical_mode": "distributed_saturation",
            "R_gamma": round(R_gamma, 2),
            "friendly_total_cost": friendly_total_cost,
            "unit_count": unit_count,
            "enemy_defense_capacity": enemy_defense_capacity,
            "saturation_factor": round(saturation_factor, 3),
            "enemy_total_cost": enemy_total_cost,
            "assessment": HeatTaxExchangeRatio._assess_ratio(R_gamma)
        }
    
    @staticmethod
    def calculate_cognitive_pollution(
        forge_cost: float,
        enemy_verify_cost: float,
        pollution_level: int  # 1=物理层, 2=逻辑层, 3=范式层
    ) -> Dict:
        """
        计算"认知污染"战术的热税交换比
        
        R_γ_c = 敌方验证成本 / 伪造成本
        随污染层级指数增长
        """
        if forge_cost == 0:
            return {"error": "Forge cost cannot be zero"}
        
        # 层级乘数
        level_multiplier = [1, 10, 100, 1000][min(pollution_level, 3)]
        
        effective_verify_cost = enemy_verify_cost * level_multiplier
        
        R_gamma_c = effective_verify_cost / forge_cost
        
        return {
            "tactical_mode": "cognitive_pollution",
            "R_gamma_c": round(R_gamma_c, 2),
            "forge_cost": forge_cost,
            "enemy_verify_cost": enemy_verify_cost,
            "pollution_level": pollution_level,
            "level_multiplier": level_multiplier,
            "effective_verify_cost": effective_verify_cost,
            "assessment": HeatTaxExchangeRatio._assess_ratio(R_gamma_c)
        }
    
    @staticmethod
    def _assess_ratio(R: float) -> str:
        """评估交换比等级"""
        if R < 1:
            return "亏损 - 敌方成本低于我方，战术无效"
        elif R < 10:
            return "盈利 - 有效消耗敌方资源"
        elif R < 100:
            return "优势 - 显著不对称收益"
        elif R < 1000:
            return "压倒性 - 敌方陷入消耗陷阱"
        else:
            return "无限 - 敌方系统即将崩溃"


class SelfProofTrapDetector:
    """自证陷阱检测器"""
    
    # 自证陷阱关键词模式
    TRAP_PATTERNS = {
        "identity_proof": [
            "证明你不是", "证明你没有", "证明你不",
            "怎么证明", "如何证明", "拿什么证明"
        ],
        "negative_assertion": [
            "从未", "绝对没有", "完全不", "根本不",
            "百分之百", "绝对安全", "绝对可靠"
        ],
        "infinite_regression": [
            "为什么", "凭什么", "依据是什么",
            "证据在哪里", "怎么保证"
        ]
    }
    
    @classmethod
    def detect_trap(cls, text: str) -> Dict:
        """
        检测文本中的自证陷阱
        
        Returns:
            {
                "is_trap": bool,
                "trap_type": str,
                "confidence": float,
                "matched_phrases": List[str],
                "recommended_response": str
            }
        """
        text_lower = text.lower()
        
        matches = []
        trap_type = None
        max_confidence = 0.0
        
        for trap_name, patterns in cls.TRAP_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    matches.append(pattern)
                    confidence = len(pattern) / len(text_lower) * 100
                    if confidence > max_confidence:
                        max_confidence = confidence
                        trap_type = trap_name
        
        is_trap = len(matches) > 0
        
        return {
            "is_trap": is_trap,
            "trap_type": trap_type or "unknown",
            "confidence": round(min(max_confidence * 10, 1.0), 3),
            "matched_phrases": matches,
            "recommended_response": cls._generate_response(trap_type) if is_trap else None
        }
    
    @classmethod
    def _generate_response(cls, trap_type: Optional[str]) -> str:
        """生成反陷阱响应"""
        responses = {
            "identity_proof": "举证责任在提出质疑方。请提供具体证据支持您的指控，而非要求我证明否定。",
            "negative_assertion": "绝对化表述本身即逻辑漏洞。请用具体数据和场景替代'绝对'、'完全'等词。",
            "infinite_regression": "无限递归的质疑无法穷尽。请明确您的核心关切，我们聚焦解决具体问题。",
            "unknown": "此问题结构存在逻辑陷阱。建议重构为可验证的正面命题。"
        }
        return responses.get(trap_type, responses["unknown"])


class HeatTaxCriticalPoint:
    """热税临界点预警"""
    
    # 系统崩溃阈值
    CRITICAL_THRESHOLDS = {
        "individual": {"gamma": 0.8, "stress_duration_days": 30},
        "team": {"gamma": 0.6, "stress_duration_days": 60},
        "organization": {"gamma": 0.5, "stress_duration_days": 90},
        "industry": {"gamma": 0.4, "stress_duration_days": 180},
        "nation": {"gamma": 0.3, "stress_duration_days": 365}
    }
    
    @classmethod
    def check_critical_point(
        cls,
        system_level: str,
        current_gamma: float,
        stress_duration_days: float,
        gamma_trend: float = 0.0  # 热税变化趋势（每天）
    ) -> Dict:
        """
        检查系统是否接近热税临界点
        
        Returns:
            {
                "status": "safe" | "warning" | "critical" | "collapse",
                "current_gamma": float,
                "threshold": float,
                "margin": float,
                "estimated_days_to_critical": float,
                "recommendations": List[str]
            }
        """
        threshold_info = cls.CRITICAL_THRESHOLDS.get(system_level, cls.CRITICAL_THRESHOLDS["organization"])
        threshold = threshold_info["gamma"]
        max_duration = threshold_info["stress_duration_days"]
        
        margin = threshold - current_gamma
        
        # 估计到达临界点的时间
        if gamma_trend > 0:
            days_to_critical = margin / gamma_trend if margin > 0 else 0
        else:
            days_to_critical = float('inf')
        
        # 持续时间因子
        duration_factor = stress_duration_days / max_duration
        adjusted_margin = margin * (1 - duration_factor * 0.5)
        
        # 确定状态
        if adjusted_margin < 0:
            status = "collapse"
        elif adjusted_margin < threshold * 0.1:
            status = "critical"
        elif adjusted_margin < threshold * 0.3:
            status = "warning"
        else:
            status = "safe"
        
        recommendations = cls._generate_recommendations(status, system_level)
        
        return {
            "status": status,
            "system_level": system_level,
            "current_gamma": round(current_gamma, 4),
            "threshold": threshold,
            "margin": round(margin, 4),
            "adjusted_margin": round(adjusted_margin, 4),
            "stress_duration_days": stress_duration_days,
            "estimated_days_to_critical": round(days_to_critical, 1) if days_to_critical != float('inf') else "N/A",
            "recommendations": recommendations
        }
    
    @classmethod
    def _generate_recommendations(cls, status: str, system_level: str) -> List[str]:
        """生成建议"""
        if status == "safe":
            return ["系统处于安全区间，继续监测热税变化趋势"]
        
        elif status == "warning":
            return [
                f"【预警】{system_level}级别系统热税接近警戒线",
                "建议启动减负程序：削减非核心任务、优化流程",
                "增加意义注入：团队建设、使命重申、创新时间"
            ]
        
        elif status == "critical":
            return [
                f"【危急】{system_level}级别系统即将达到热税临界点",
                "立即启动紧急减负：暂停50%非紧急项目",
                "引入外部冲击：新视角、跨部门协作、外部顾问",
                "考虑架构重组：打破僵化结构，建立快速通道"
            ]
        
        else:  # collapse
            return [
                f"【崩溃】{system_level}级别系统已越过热税临界点",
                "启动紧急状态：全面停工整顿，只保留核心功能",
                "更换 leadership：引入外部管理者打破僵局",
                "系统重构：从零开始重建，保留核心资产"
            ]


class MeaningContagionModel:
    """意义传染模型"""
    
    @staticmethod
    def calculate_R0(
        contact_rate: float,      # 日均接触人数
        conversion_rate: float,   # 转化率
        retention_rate: float,    # 留存率
        amplification_factor: float = 1.0  # 放大因子（AI等）
    ) -> Dict:
        """
        计算意义传染的基本再生数 R₀
        
        R₀ = 接触人数 × 转化率 × 留存率 × 放大因子
        
        R₀ < 1: 传播衰减
        R₀ = 1-3: 线性传播
        R₀ > 3: 指数爆发
        """
        R0 = contact_rate * conversion_rate * retention_rate * amplification_factor
        
        if R0 < 1:
            phase = "decay"
            description = "传播衰减 - 意义无法有效扩散"
        elif R0 < 2:
            phase = "linear"
            description = "线性传播 - 稳定增长但可控"
        elif R0 < 3:
            phase = "accelerating"
            description = "加速传播 - 进入快速增长期"
        else:
            phase = "explosive"
            description = "指数爆发 - 不可阻挡的 viral 传播"
        
        return {
            "R0": round(R0, 3),
            "phase": phase,
            "description": description,
            "parameters": {
                "contact_rate": contact_rate,
                "conversion_rate": conversion_rate,
                "retention_rate": retention_rate,
                "amplification_factor": amplification_factor
            },
            "contagion_timeline": MeaningContagionModel._project_timeline(R0)
        }
    
    @staticmethod
    def _project_timeline(R0: float) -> List[Dict]:
        """预测传染时间线"""
        timeline = []
        
        if R0 < 1:
            stages = [
                {"days": 30, "infected": 10, "note": "初期接触者"},
                {"days": 90, "infected": 5, "note": "大部分流失"},
                {"days": 180, "infected": 2, "note": "仅剩核心认同者"}
            ]
        elif R0 < 2:
            stages = [
                {"days": 30, "infected": 50, "note": "早期采用者"},
                {"days": 90, "infected": 200, "note": "稳定增长"},
                {"days": 180, "infected": 1000, "note": "初具规模"}
            ]
        elif R0 < 3:
            stages = [
                {"days": 30, "infected": 200, "note": "快速增长"},
                {"days": 90, "infected": 2000, "note": "社区形成"},
                {"days": 180, "infected": 20000, "note": "规模效应显现"}
            ]
        else:
            stages = [
                {"days": 30, "infected": 1000, "note": "病毒式传播"},
                {"days": 90, "infected": 50000, "note": "主流突破"},
                {"days": 180, "infected": 1000000, "note": "社会级现象"}
            ]
        
        return stages


class WarTheoryEngine:
    """战争理论引擎 - 统一接口"""
    
    def __init__(self):
        self.exchange_calculator = HeatTaxExchangeRatio()
        self.trap_detector = SelfProofTrapDetector()
        self.critical_point = HeatTaxCriticalPoint()
        self.contagion_model = MeaningContagionModel()
    
    def simulate_tactical_scenario(
        self,
        mode: TacticalMode,
        friendly_params: Dict,
        enemy_params: Dict,
        duration_days: float = 1.0
    ) -> Dict:
        """
        模拟战术场景
        
        Args:
            mode: 战术模式
            friendly_params: 我方参数
            enemy_params: 敌方参数
            duration_days: 持续时间
        """
        if mode == TacticalMode.DAMAGE_WITHOUT_DESTROY:
            return self.exchange_calculator.calculate_damage_without_destroy(
                friendly_cost=friendly_params.get("cost", 1000),
                enemy_repair_cost=enemy_params.get("repair_cost", 5000),
                enemy_operational_loss=enemy_params.get("daily_loss", 1000),
                duration_days=duration_days
            )
        
        elif mode == TacticalMode.BAIT_AND_TRAP:
            return self.exchange_calculator.calculate_bait_and_trap(
                bait_cost=friendly_params.get("cost", 100),
                enemy_interception_cost=enemy_params.get("interception_cost", 5000),
                enemy_false_positive_rate=enemy_params.get("fpr", 0.1)
            )
        
        elif mode == TacticalMode.DISTRIBUTED_SATURATION:
            return self.exchange_calculator.calculate_distributed_saturation(
                unit_cost=friendly_params.get("unit_cost", 500),
                unit_count=friendly_params.get("count", 100),
                enemy_defense_cost_per_unit=enemy_params.get("defense_cost", 1000),
                enemy_defense_capacity=enemy_params.get("capacity", 50)
            )
        
        elif mode == TacticalMode.COGNITIVE_POLLUTION:
            return self.exchange_calculator.calculate_cognitive_pollution(
                forge_cost=friendly_params.get("forge_cost", 10),
                enemy_verify_cost=enemy_params.get("verify_cost", 1000),
                pollution_level=friendly_params.get("level", 2)
            )
        
        else:
            return {"error": f"Unsupported tactical mode: {mode}"}
    
    def detect_and_counter_trap(self, enemy_message: str) -> Dict:
        """检测并反制敌方陷阱"""
        detection = self.trap_detector.detect_trap(enemy_message)
        
        if detection["is_trap"]:
            return {
                "threat_detected": True,
                "trap_analysis": detection,
                "counter_strategy": {
                    "type": "deflection",
                    "response": detection["recommended_response"],
                    "escalation_risk": "low"
                }
            }
        
        return {
            "threat_detected": False,
            "message": "未检测到自证陷阱"
        }
    
    def assess_system_health(
        self,
        system_level: str,
        current_gamma: float,
        stress_duration: float,
        gamma_trend: float = 0.0
    ) -> Dict:
        """评估系统健康度"""
        return self.critical_point.check_critical_point(
            system_level, current_gamma, stress_duration, gamma_trend
        )
    
    def project_meaning_contagion(
        self,
        contact_rate: float,
        conversion_rate: float,
        retention_rate: float,
        amplification: float = 1.0
    ) -> Dict:
        """预测意义传染"""
        return self.contagion_model.calculate_R0(
            contact_rate, conversion_rate, retention_rate, amplification
        )


# 便捷函数
def quick_tactical_assessment(
    mode: str,
    friendly_cost: float,
    enemy_cost: float
) -> Dict:
    """快速战术评估"""
    engine = WarTheoryEngine()
    
    mode_map = {
        "damage": TacticalMode.DAMAGE_WITHOUT_DESTROY,
        "bait": TacticalMode.BAIT_AND_TRAP,
        "saturation": TacticalMode.DISTRIBUTED_SATURATION,
        "cognitive": TacticalMode.COGNITIVE_POLLUTION
    }
    
    tactical_mode = mode_map.get(mode, TacticalMode.DAMAGE_WITHOUT_DESTROY)
    
    return engine.simulate_tactical_scenario(
        mode=tactical_mode,
        friendly_params={"cost": friendly_cost},
        enemy_params={"cost": enemy_cost}
    )


def check_message_for_traps(message: str) -> Dict:
    """检查消息中的陷阱"""
    engine = WarTheoryEngine()
    return engine.detect_and_counter_trap(message)


if __name__ == "__main__":
    # 演示
    print("=" * 70)
    print("MSS War Theory Engine Demo")
    print("=" * 70)
    
    engine = WarTheoryEngine()
    
    # 1. 热税交换比计算
    print("\n1. 战术热税交换比:")
    
    # 打坏不摧毁
    result = engine.simulate_tactical_scenario(
        mode=TacticalMode.DAMAGE_WITHOUT_DESTROY,
        friendly_params={"cost": 500},  # 无人机成本
        enemy_params={"repair_cost": 50000, "daily_loss": 2000},  # 坦克修复+停运损失
        duration_days=30
    )
    print(f"   打坏不摧毁: R_γ = {result['R_gamma']} ({result['assessment']})")
    
    # 认知污染
    result = engine.simulate_tactical_scenario(
        mode=TacticalMode.COGNITIVE_POLLUTION,
        friendly_params={"forge_cost": 100, "level": 3},  # 范式层假目标
        enemy_params={"verify_cost": 5000}
    )
    print(f"   认知污染: R_γ = {result['R_gamma_c']} ({result['assessment']})")
    
    # 2. 自证陷阱检测
    print("\n2. 自证陷阱检测:")
    test_messages = [
        "你怎么证明你没有抄袭？",
        "请提供完整的证据链证明你的清白",
        "今天的天气不错"
    ]
    for msg in test_messages:
        result = engine.detect_and_counter_trap(msg)
        status = "🚨 陷阱" if result["threat_detected"] else "✅ 安全"
        print(f"   '{msg[:30]}...' -> {status}")
    
    # 3. 热税临界点
    print("\n3. 热税临界点预警:")
    result = engine.assess_system_health(
        system_level="organization",
        current_gamma=0.45,
        stress_duration=60,
        gamma_trend=0.005
    )
    print(f"   状态: {result['status']}")
    print(f"   当前γ: {result['current_gamma']}, 阈值: {result['threshold']}")
    print(f"   预计临界: {result['estimated_days_to_critical']}天")
    
    # 4. 意义传染
    print("\n4. 意义传染预测:")
    result = engine.project_meaning_contagion(
        contact_rate=10,      # 日均接触10人
        conversion_rate=0.3,  # 30%转化率
        retention_rate=0.8,   # 80%留存
        amplification=2.0     # AI放大2倍
    )
    print(f"   R₀ = {result['R0']} ({result['description']})")
    print(f"   阶段: {result['phase']}")
    for stage in result['contagion_timeline']:
        print(f"   {stage['days']}天: {stage['infected']}人 - {stage['note']}")
