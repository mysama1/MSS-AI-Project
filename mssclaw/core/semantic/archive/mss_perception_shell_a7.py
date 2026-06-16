#!/usr/bin/env python3
"""
MSS-A7 Perceptual Shell Relativity Engine
===========================================
Protocol: MSS-AXIOM-007 | Logical Rigidity: M_L ≡ 1.0
Release: v15.1 | Date: 2026-05-28

Implements A7 perceptual shell relativity axiom with T-value tuning calculus.
Bridges the logical kernel (A1-A6) with the perception shell architecture.

Core formulas:
  R_obs = T_s · M_LF        (Observation = Shell × Meaning Field)
  R_p^eff = T × R_p^max     (Effective Resolution = Tuning × Max Resolution)
  η_tax = T²                (Heat Tax Efficiency = T²)
"""

import math
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# A7 CORE TYPES (self-contained for module independence)
# ============================================================

class PerceptionLayer(Enum):
    """A7三层感知壳架构"""
    LOGIC = ("L1", "逻辑感知层", 1e14, 0.01, 2025, "慧眼")
    MEANING = ("L2", "意义感知层", 1e21, 0.10, 2027, "法眼")
    COLLECTIVE = ("L3", "集体感知层", 1e22, 0.10, 2030, "佛眼")

    def __new__(cls, code, chinese, rp_max, target_t, target_year, metaphor):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.chinese_name = chinese
        obj.rp_max = rp_max
        obj.target_t = target_t
        obj.target_year = target_year
        obj.metaphor = metaphor
        return obj


class MSSMeaningLayer(Enum):
    """意义场六层结构"""
    L0 = ("L0", "物理显化层", "物理世界", 0.0)
    L1 = ("L1", "实体层", "对象与符号", 0.2)
    L2 = ("L2", "逻辑结构层", "形式化逻辑", 0.5)
    L3 = ("L3", "意义层", "价值与体验", 0.8)
    L4 = ("L4", "本体层", "意义场本体", 1.0)
    L5 = ("L5", "实现层", "工程落地", 0.6)

    def __new__(cls, code, chinese_name, description, access_clarity):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.chinese_name = chinese_name
        obj.description = description
        obj.access_clarity = access_clarity
        return obj


@dataclass
class TValueState:
    """T值运行时状态"""
    t_value: float  # 感知调谐度，本质为 I_output / I_input
    confidence: float = 1.0  # T值置信度 (0-1)
    measurement_method: str = "inferred"  # measured / inferred / calibrated
    last_updated: str = ""

    @property
    def heat_tax_efficiency(self) -> float:
        return self.t_value ** 2

    @property
    def band(self) -> str:
        if self.t_value < 0.1: return "本能感知"
        if self.t_value < 1.0: return "常规感知"
        if self.t_value < 5.0: return "逻辑感知"
        if self.t_value < 20.0: return "意义感知"
        if self.t_value < 100.0: return "集体感知"
        return "宇宙感知"


@dataclass
class MeaningFieldProjection:
    """意义场投影结果"""
    raw_field_value: float  # M_LF
    shell_t_value: float    # T_s
    observed_value: float   # R_obs
    projection_loss_pct: float  # 信息丢失百分比
    heat_tax_cost: float    # incurred heat tax
    layer: MSSMeaningLayer = MSSMeaningLayer.L3

    def to_report(self) -> str:
        return (
            f"意义场投影报告:\n"
            f"  原始信号 (M_LF): {self.raw_field_value:.4e}\n"
            f"  感知壳 T值:     {self.shell_t_value:.4f}\n"
            f"  观测现实 (R_obs): {self.observed_value:.4e}\n"
            f"  信息丢失:        {self.projection_loss_pct:.2f}%\n"
            f"  热税成本:        {self.heat_tax_cost:.4e}\n"
            f"  显化层:          {self.layer.chinese_name}"
        )


# ============================================================
# A7 PERCEPTION SHELL ENGINE
# ============================================================

class A7PerceptionShellEngine:
    """
    A7感知壳相对性引擎
    
    Implements the core A7 axiom computation:
    - Perception shell acts as a filter/encoder for meaning field signals
    - T-value determines how efficiently the shell processes signals
    - Different shells produce different "observed realities" from same raw meaning field
    """

    def __init__(self, default_t: float = 0.01, 
                 current_layer: PerceptionLayer = PerceptionLayer.LOGIC):
        self.default_t = default_t
        self.current_layer = current_layer
        self._t_cache: Dict[str, TValueState] = {}
        self._projection_log: List[MeaningFieldProjection] = []

    # ---- Core A7 Formulas ----

    @staticmethod
    def project_observation(raw_meaning_field: float, t_value: float) -> float:
        """A7核心公式: R_obs = T_s · M_LF"""
        return t_value * raw_meaning_field

    @staticmethod
    def effective_resolution(rp_max: float, t_value: float) -> float:
        """A7-R1修正: R_p^eff = T × R_p^max"""
        return t_value * rp_max

    @staticmethod
    def heat_tax_efficiency(t_value: float) -> float:
        """A7-R1修正: η_tax = T²"""
        return t_value ** 2

    @staticmethod
    def heat_tax_cost(information_volume: float, t_value: float) -> float:
        """热税消耗: cost = I / η_tax = I / T²"""
        eta = t_value ** 2
        if eta == 0:
            return float('inf')
        return information_volume / eta

    @staticmethod
    def fidelity_ratio(output_bits: float, input_bits: float) -> float:
        """T值物理本质: T = I_output / I_input"""
        if input_bits == 0:
            return 0.0
        return output_bits / input_bits

    # ---- Layered Projection Methods ----

    def project_to_layer(self, meaning_signal: float, 
                         target_layer: MSSMeaningLayer) -> MeaningFieldProjection:
        """将意义场信号投影到指定显化层"""
        layer_clarity = target_layer.access_clarity
        effective_t = self.default_t * layer_clarity

        observed = self.project_observation(meaning_signal, effective_t)
        loss_pct = 100.0 * (1.0 - (observed / max(abs(meaning_signal), 1e-10)))
        heat_tax = self.heat_tax_cost(abs(meaning_signal), effective_t)

        projection = MeaningFieldProjection(
            raw_field_value=meaning_signal,
            shell_t_value=effective_t,
            observed_value=observed,
            projection_loss_pct=max(0.0, loss_pct),
            heat_tax_cost=heat_tax,
            layer=target_layer
        )
        self._projection_log.append(projection)
        return projection

    def project_full_stack(self, meaning_signal: float) -> List[MeaningFieldProjection]:
        """执行完整L0-L5六层投影"""
        projections = []
        for layer in MSSMeaningLayer:
            proj = self.project_to_layer(meaning_signal, layer)
            projections.append(proj)
        return projections

    # ---- Multi-Observer Relativistic Comparison ----

    def compare_observers(self, meaning_signal: float,
                          observers: List[Tuple[str, float]]) -> Dict[str, Any]:
        """
        A7相对性: 同一意义场信号，不同感知壳产生不同"显化现实"
        
        Args:
            meaning_signal: 原始意义场信号 M_LF
            observers: [(name, t_value), ...]
        
        Returns:
            多观察者感知对比结果
        """
        results = []
        for name, t_val in observers:
            obs = self.project_observation(meaning_signal, t_val)
            loss = 100.0 * (1.0 - (obs / max(abs(meaning_signal), 1e-10)))
            htax = self.heat_tax_cost(abs(meaning_signal), t_val)
            results.append({
                "observer": name,
                "t_value": t_val,
                "observed_reality": obs,
                "information_loss_pct": max(0.0, loss),
                "heat_tax": htax,
                "resolution_vs_T001": (t_val / 0.01)  # T=0.01 baseline
            })
        
        return {
            "raw_meaning_field": meaning_signal,
            "principle": "没有绝对客观现实，只有感知壳相对现实",
            "observations": results,
            "max_disagreement_ratio": self._calc_disagreement(results)
        }

    @staticmethod
    def _calc_disagreement(results: List[Dict]) -> float:
        """计算不同观察者之间最大分歧比例"""
        if len(results) < 2:
            return 0.0
        values = [r["observed_reality"] for r in results]
        max_v, min_v = max(values), min(values)
        if min_v == 0:
            return float('inf') if max_v != 0 else 0.0
        return max_v / min_v

    # ---- T-Value Management ----

    def register_observer(self, name: str, t_value: float, 
                          confidence: float = 1.0) -> TValueState:
        """注册观察者的T值状态"""
        state = TValueState(t_value=t_value, confidence=confidence)
        self._t_cache[name] = state
        return state

    def get_t_value(self, name: str) -> Optional[TValueState]:
        """获取观察者T值"""
        return self._t_cache.get(name)

    def calculate_t_growth(self, current_t: float, training_months: float,
                           base_rate: float = 0.05) -> float:
        """
        计算意识训练后的T值增长
        
        T值增长遵循对数衰减模型:
        3个月可提升20%-50%；随着T值越高，提升速度越慢
        """
        gain = base_rate * (1 - math.exp(-training_months / 3))
        return current_t * (1 + gain)

    # ---- Shell Compatibility Check ----

    def check_shell_compatibility(self, source_t: float, target_t: float,
                                  threshold: float = 0.5) -> Tuple[bool, str]:
        """
        检查感知壳切换兼容性 (A7安全机制)
        
        两个感知壳的T值差距过大时不能直接切换，需要过渡训练。
        """
        ratio = min(source_t, target_t) / max(source_t, target_t) if max(source_t, target_t) > 0 else 0
        if ratio >= threshold:
            return True, f"兼容: T值比率 {ratio:.2f} ≥ {threshold}"
        else:
            steps = math.ceil(abs(target_t - source_t) / 0.1)
            return False, f"不兼容: T值比率 {ratio:.2f} < {threshold}，建议过渡训练 (约{steps}步)"

    # ---- Layer Upgradability Check ----

    def check_layer_upgrade(self, current_t: float, target_layer: PerceptionLayer) -> Dict[str, Any]:
        """检查是否可以从当前T值升级到目标感知层"""
        required_t = target_layer.target_t
        can_upgrade = current_t >= required_t

        months_needed = 0
        if not can_upgrade:
            t = current_t
            while t < required_t:
                t = self.calculate_t_growth(t, 3)
                months_needed += 3
                if months_needed > 120:  # 10 year cap
                    break

        return {
            "current_t": current_t,
            "required_t": required_t,
            "target_layer": target_layer.chinese_name,
            "can_upgrade": can_upgrade,
            "estimated_months": months_needed if not can_upgrade else 0,
            "gap_ratio": required_t / max(current_t, 1e-10) if not can_upgrade else 1.0
        }

    # ---- Reporting ----

    def get_projection_summary(self) -> Dict[str, Any]:
        """获取投影统计摘要"""
        if not self._projection_log:
            return {"total_projections": 0}
        
        avg_loss = sum(p.projection_loss_pct for p in self._projection_log) / len(self._projection_log)
        avg_heat_tax = sum(p.heat_tax_cost for p in self._projection_log) / len(self._projection_log)
        
        return {
            "total_projections": len(self._projection_log),
            "average_loss_pct": round(avg_loss, 2),
            "average_heat_tax": avg_heat_tax,
            "current_t_value": self.default_t,
            "effective_resolution_bps": self.effective_resolution(
                self.current_layer.rp_max, self.default_t
            ),
            "heat_tax_efficiency": self.heat_tax_efficiency(self.default_t)
        }

    def export_state(self) -> Dict[str, Any]:
        """导出引擎完整状态（可序列化）"""
        return {
            "engine_version": "v15.1",
            "protocol": "MSS-AXIOM-007",
            "default_t_value": self.default_t,
            "current_layer": self.current_layer.chinese_name,
            "current_rp_max": self.current_layer.rp_max,
            "effective_resolution": self.effective_resolution(
                self.current_layer.rp_max, self.default_t
            ),
            "heat_tax_efficiency": self.heat_tax_efficiency(self.default_t),
            "registered_observers": {
                k: {"t_value": v.t_value, "confidence": v.confidence, "band": v.band}
                for k, v in self._t_cache.items()
            },
            "projection_count": len(self._projection_log),
            "a7_core_check": {
                "R_obs = T_s · M_LF": True,
                "R_p^eff = T × R_p^max": True,
                "η_tax = T²": True
            }
        }


# ============================================================
# A7 PHILOSOPHICAL ANATOMY ENGINE
# ============================================================

class PhilosophyAnatomyEngine:
    """
    L3哲学流派解剖引擎
    
    基于A7感知壳相对性公理，将各哲学流派定位为：
    "碳基特定感知壳的哲学表达"
    
    Each philosophy school correctly applies to a specific shell-niche
    but commits a transgression error when claiming universality.
    """

    SCHOOLS = {
        "唯物主义": {
            "shell_basis": "碳基视觉/触觉感知壳",
            "valid_niche": "L0物理层 / L1实体层",
            "transgression": "僭越错误: 将L0/L1的规律推广到L3/L4，否认意义层的实在性",
            "a7_correction": "物质是意义在L0的稳定投影模式，非终极实在",
            "compatibility_t_value": 0.01,
            "adaptation_rate": 1.0
        },
        "唯心主义": {
            "shell_basis": "碳基内省感知壳",
            "valid_niche": "L3意义层 / L4本体层",
            "transgression": "僭越错误: 将L3/L4的规律推广到L0/L1，否认物理层的独立性",
            "a7_correction": "意识体验是意义场的直接接入，受感知壳结构调制",
            "compatibility_t_value": 5.0,
            "adaptation_rate": 1.0
        },
        "实证主义": {
            "shell_basis": "碳基感官延伸（科学仪器）感知壳",
            "valid_niche": "L0-L2可观测现象验证层",
            "transgression": "僭越错误: 认为所有有意义的陈述都必须可观测验证",
            "a7_correction": "意义层(L3-L4)的观测需要不同的感知壳（意义感知/集体感知）",
            "compatibility_t_value": 1.0,
            "adaptation_rate": 1.0
        },
        "理性主义": {
            "shell_basis": "碳基逻辑思维感知壳",
            "valid_niche": "L2形式化逻辑层",
            "transgression": "僭越错误: 认为理性推理可以独立于感知壳结构",
            "a7_correction": "逻辑推理本身是感知壳的产物，受感知壳结构约束",
            "compatibility_t_value": 2.0,
            "adaptation_rate": 1.0
        },
        "二元论": {
            "shell_basis": "碳基感知壳分裂现象",
            "valid_niche": "L3人类主观认知结构（过渡状态）",
            "transgression": "僭越错误: 将感知壳的内部感受当作宇宙的本体结构",
            "a7_correction": "身心分裂是碳基感知壳的设计特征，非意义场本体",
            "compatibility_t_value": 0.5,
            "adaptation_rate": 0.5
        },
        "存在主义": {
            "shell_basis": "碳基有限性感知壳",
            "valid_niche": "L3个体意义层（生存论）",
            "transgression": "僭越错误: 将个体的意义危机投射到宇宙尺度",
            "a7_correction": "个体的意义危机是人类感知壳的局域现象，非意义场全局属性",
            "compatibility_t_value": 3.0,
            "adaptation_rate": 0.8
        },
        "实用主义": {
            "shell_basis": "碳基工具理性感知壳",
            "valid_niche": "L5工程实现层",
            "transgression": "僭越错误: 将效用等同于真理",
            "a7_correction": "工程上的可行性与本体论的真理性是两个维度",
            "compatibility_t_value": 1.0,
            "adaptation_rate": 1.0
        },
        "结构主义": {
            "shell_basis": "碳基模式识别感知壳",
            "valid_niche": "L4符号系统层",
            "transgression": "僭越错误: 将所有意义归结为符号间的关系",
            "a7_correction": "符号关系是意义场的一种编码，非意义的全部",
            "compatibility_t_value": 4.0,
            "adaptation_rate": 0.9
        }
    }

    @classmethod
    def analyze_school(cls, school_name: str, observer_t: float = 0.01) -> Dict[str, Any]:
        """分析观察者与某哲学流派的适配性"""
        info = cls.SCHOOLS.get(school_name)
        if not info:
            return {"error": f"未收录流派: {school_name}"}

        compatibility_t = info["compatibility_t_value"]
        # T匹配: 观察者T值低于流派设计T值时为距离度量
        #           观察者T值高于流派设计T值时仍可兼容(已超越)，但会有折损
        if observer_t >= compatibility_t:
            # 已超越流派T值：仍可兼容，越远折损越大（上限30%折损）
            t_match = 1.0 - 0.3 * min(abs(observer_t - compatibility_t) / max(compatibility_t, 1.0), 3.0)
        else:
            # 未达到流派T值：按距离计算匹配度
            t_gap = abs(observer_t - compatibility_t)
            t_match = 1.0 - min(t_gap / max(compatibility_t, 1.0), 1.0)

        return {
            "school": school_name,
            "shell_basis": info["shell_basis"],
            "valid_niche": info["valid_niche"],
            "transgression_error": info["transgression"],
            "a7_correction": info["a7_correction"],
            "compatibility_t": compatibility_t,
            "observer_t": observer_t,
            "t_match_pct": round(t_match * 100, 1),
            "assessment": (
                "完全适配" if t_match > 0.9 else
                "良好适配" if t_match > 0.7 else
                "部分适配" if t_match > 0.4 else
                "不适配"
            )
        }

    @classmethod
    def find_best_school(cls, observer_t: float) -> List[Dict[str, Any]]:
        """为特定T值的观察者找到最适配的哲学流派"""
        results = []
        for name in cls.SCHOOLS:
            analysis = cls.analyze_school(name, observer_t)
            if "error" not in analysis:
                results.append(analysis)
        results.sort(key=lambda x: x["t_match_pct"], reverse=True)
        return results

    @classmethod
    def export_anatomy_table(cls) -> List[Dict[str, Any]]:
        """导出完整的哲学流派解剖表"""
        return [
            {
                "school": name,
                "shell_basis": info["shell_basis"],
                "valid_niche": info["valid_niche"],
                "transgression": info["transgression"],
                "a7_correction": info["a7_correction"],
                "compatibility_t": info["compatibility_t"]
            }
            for name, info in cls.SCHOOLS.items()
        ]


# ============================================================
# SELF-TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MSS-A7 Perceptual Shell Relativity Engine v15.1")
    print("Protocol: MSS-AXIOM-007")
    print("=" * 60)

    engine = A7PerceptionShellEngine(default_t=0.02)

    # Test 1: Basic projection
    print("\n[Test 1] 意义场投影")
    proj = engine.project_to_layer(meaning_signal=100.0, 
                                   target_layer=MSSMeaningLayer.L3)
    print(proj.to_report())

    # Test 2: Multi-observer relativity
    print("\n[Test 2] 多观察者相对性")
    observers = [
        ("普通人 (T=0.01)", 0.01),
        ("科学家 (T=1.0)", 1.0),
        ("MSS觉醒者 (T=10.0)", 10.0),
        ("K4文明先驱 (T=50.0)", 50.0)
    ]
    comparison = engine.compare_observers(meaning_signal=100.0, observers=observers)
    print(f"原始意义场信号: {comparison['raw_meaning_field']}")
    print(f"原则: {comparison['principle']}")
    for obs in comparison["observations"]:
        print(f"  {obs['observer']}: 观察值={obs['observed_reality']:.2f}, "
              f"丢失={obs['information_loss_pct']:.1f}%, 热税={obs['heat_tax']:.2e}")

    # Test 3: T-value growth prediction
    print("\n[Test 3] T值增长预测")
    for months in [3, 6, 12, 24]:
        new_t = engine.calculate_t_growth(0.02, months)
        print(f"  训练{months}月后: T=0.02 → {new_t:.4f} (+{((new_t/0.02 - 1)*100):.0f}%)")

    # Test 4: Layer upgrade check
    print("\n[Test 4] 感知层升级检查")
    for layer in PerceptionLayer:
        result = engine.check_layer_upgrade(current_t=0.02, target_layer=layer)
        status = "✓可升级" if result["can_upgrade"] else f"需{result['estimated_months']}月"
        print(f"  {layer.chinese_name}(T需≥{layer.target_t}): {status}")

    # Test 5: Shell compatibility
    print("\n[Test 5] 感知壳兼容性检查")
    pairs = [(0.01, 1.0), (1.0, 10.0), (50.0, 0.01)]
    for src, dst in pairs:
        compat, msg = engine.check_shell_compatibility(src, dst)
        print(f"  T{src}→T{dst}: {'✓' if compat else '✗'} {msg}")

    # Test 6: Philosophy anatomy
    print("\n[Test 6] 哲学流派解剖")
    pe = PhilosophyAnatomyEngine()
    for school in ["唯物主义", "唯心主义", "实证主义"]:
        analysis = pe.analyze_school(school, observer_t=10.0)
        print(f"  {school}: T适配={analysis['t_match_pct']}% - {analysis['assessment']}")

    # Test 7: Full stack projection
    print("\n[Test 7] L0-L5全栈投影")
    projections = engine.project_full_stack(meaning_signal=100.0)
    for p in projections:
        print(f"  {p.layer.value} {p.layer.chinese_name}: "
              f"观察值={p.observed_value:.2f}, 丢失={p.projection_loss_pct:.1f}%")

    print("\n" + "=" * 60)
    summary = engine.export_state()
    print(f"引擎状态: v{summary['engine_version']} | T={summary['default_t_value']} | "
          f"R_p^eff={summary['effective_resolution']:.2e} bps | η_tax={summary['heat_tax_efficiency']:.4f}")
    print("=" * 60)