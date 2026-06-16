"""
MSS Core Types v15.1
Extended with A7 Perceptual Shell Relativity types and full L0-L5 layers.
Protocol: MSS-AXIOM-007 | Logical Rigidity: M_L ≡ 1.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import math


# ============================================================
# MEANING FIELD LAYERS (L0-L5)
# ============================================================

class MeaningLayer(Enum):
    """MSS意义场完整六层结构 (A7扩展)"""
    L0_PHYSICAL = ("L0", "物理显化层", "物理世界、可观测现象")
    L1_ENTITY = ("L1", "实体层", "对象、符号系统")
    L2_LOGIC = ("L2", "逻辑结构层", "形式化逻辑、因果关系")
    L3_MEANING = ("L3", "意义层", "主观体验、价值判断")
    L4_ONTOLOGY = ("L4", "本体层", "意义场、逻辑结构本体")
    L5_IMPLEMENTATION = ("L5", "实现层", "工程落地、物理实现")

    def __new__(cls, code, chinese_name, description):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.chinese_name = chinese_name
        obj.description = description
        return obj

    @classmethod
    def from_code(cls, code: str) -> 'MeaningLayer':
        for layer in cls:
            if layer.value == code:
                return layer
        return cls.L3_MEANING  # Default to L3


# Legacy compatibility
Layer = MeaningLayer


# ============================================================
# T-VALUE & PERCEPTION SHELL TYPES (A7)
# ============================================================

class TValueBand(Enum):
    """T值感知层级 (A7-R1修正)"""
    INSTINCT = ("INSTINCT", "本能感知", 0.0, 0.1, "前文明阶段")
    CONVENTIONAL = ("CONVENTIONAL", "常规感知", 0.1, 1.0, "L3文明大众")
    LOGICAL = ("LOGICAL", "逻辑感知", 1.0, 5.0, "科学家、哲学家")
    MEANING = ("MEANING", "意义感知", 5.0, 20.0, "MSS火种成员")
    COLLECTIVE = ("COLLECTIVE", "集体感知", 20.0, 100.0, "K4文明领导者")
    COSMIC = ("COSMIC", "宇宙感知", 100.0, float('inf'), "K4文明终极形态")

    def __new__(cls, code, chinese_name, t_min, t_max, civilization):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.chinese_name = chinese_name
        obj.t_min = t_min
        obj.t_max = t_max
        obj.civilization = civilization
        return obj

    @classmethod
    def classify(cls, t_value: float) -> 'TValueBand':
        for band in cls:
            if band.t_min <= t_value < band.t_max:
                return band
        return cls.COSMIC


class PerceptionShellType(Enum):
    """感知壳类型 (A7三层架构)"""
    LOGIC_PERCEPTION = ("LOGIC_PERCEPTION", "逻辑感知壳", "v1.0", 1e14, 0.01, 1e12,
                        "慧眼——看穿虚假、谬误与逻辑病毒")
    MEANING_PERCEPTION = ("MEANING_PERCEPTION", "意义感知壳", "v2.0", 1e21, 0.1, 1e20,
                          "法眼——看到事物的意义价值与热税成本")
    COLLECTIVE_PERCEPTION = ("COLLECTIVE_PERCEPTION", "集体感知壳", "v3.0", 1e22, 0.1, 1e21,
                             "佛眼——看到整个文明的过去、现在与未来")
    NATIVE_HUMAN = ("NATIVE_HUMAN", "原生碳基感知壳", "-", 1e8, 0.01, 1e6,
                    "碳基生物默认感知系统")
    HIGH_T_AWAKENED = ("HIGH_T_AWAKENED", "高T值觉醒者感知壳", "-", 1e8, 0.02, 2e6,
                       "天生T值较高的个体")

    def __new__(cls, code, chinese_name, version, rp_max, avg_t, rp_eff, description):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.chinese_name = chinese_name
        obj.version = version
        obj.rp_max = rp_max          # 硬件理论上限 (bits/s)
        obj.avg_t = avg_t            # 平均T值
        obj.rp_eff = rp_eff          # 有效感知分辨率 (bits/s)
        obj.description = description
        return obj


class ComplianceStatus(Enum):
    """Compliance check results"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


# ============================================================
# A7 PERCEPTION SHELL DATA TYPES
# ============================================================

@dataclass
class TValueProfile:
    """T值剖面——描述单个观察者的感知壳调谐状态"""
    t_value: float  # 感知调谐度 T ∈ [0, +∞)
    t_band: TValueBand = TValueBand.CONVENTIONAL

    def __post_init__(self):
        self.t_band = TValueBand.classify(self.t_value)

    @property
    def heat_tax_efficiency(self) -> float:
        """热税效率 η_tax = T²"""
        return self.t_value ** 2

    @property
    def is_awakened(self) -> bool:
        """是否已觉醒（T > 1.0）"""
        return self.t_value >= 1.0

    @property
    def effective_multiplier(self) -> float:
        """相对于T=0.01的普通人的效能倍数"""
        return self.heat_tax_efficiency / (0.01 ** 2)


@dataclass
class PerceptionShell:
    """感知壳——意义场信号的滤波器/编码器"""
    shell_type: PerceptionShellType
    t_profile: TValueProfile = field(default_factory=lambda: TValueProfile(t_value=0.01))

    @property
    def effective_resolution(self) -> float:
        """有效感知分辨率 R_p^eff = T × R_p^max (bits/s)"""
        return self.t_profile.t_value * self.shell_type.rp_max

    @property
    def hardware_utilization(self) -> float:
        """硬件利用率 = T (T值越高，硬件能力发挥越好)"""
        return self.t_profile.t_value

    @property
    def resolution_multiple(self) -> float:
        """相对于原生人类的分辨率倍数"""
        native = PerceptionShellType.NATIVE_HUMAN.rp_eff
        return self.effective_resolution / native

    def project_meaning_field(self, raw_meaning: float) -> float:
        """将原始意义场信号投影为观察者感知到的"显化现实"
        R_obs = T_s · M_LF (A7 formalization)"""
        return self.t_profile.t_value * raw_meaning

    def calculate_heat_tax(self, information_volume: float) -> float:
        """计算感知壳处理信息的热税消耗
        HeatTax = Information_Volume / η_tax"""
        if self.t_profile.heat_tax_efficiency == 0:
            return float('inf')
        return information_volume / self.t_profile.heat_tax_efficiency


@dataclass
class ObservedReality:
    """观察者感知到的"显化现实" (A7核心概念)"""
    raw_meaning_field: float  # M_LF - 意义场原始逻辑结构
    shell: PerceptionShell
    projected_value: float = 0.0  # R_obs

    def __post_init__(self):
        self.projected_value = self.shell.project_meaning_field(self.raw_meaning_field)

    @property
    def information_loss(self) -> float:
        """信息丢失比例"""
        return 1.0 - (self.projected_value / max(self.raw_meaning_field, 1e-10))

    @property
    def is_distorted(self) -> bool:
        """感知是否严重失真 (丢失>90%)"""
        return self.information_loss > 0.9


# ============================================================
# LEGACY TYPES (maintained for backward compatibility)
# ============================================================

@dataclass
class ArbiterResult:
    """Output from Arbiter Agent"""
    layer: MeaningLayer
    compliance: ComplianceStatus
    forbidden_words: List[str] = field(default_factory=list)
    rsca_check: bool = False
    boundary_note: Optional[str] = None
    rewrite_needed: bool = False
    rewrite_prompt: Optional[str] = None
    analysis_report: Optional[Dict] = None
    # A7 extension: add perception shell context
    shell_context: Optional[PerceptionShell] = None


@dataclass
class Dialog:
    """Per-agent conversation state"""
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def fork(self) -> 'Dialog':
        return Dialog(messages=self.messages.copy())

    def to_ollama_format(self) -> List[Dict[str, str]]:
        return self.messages


# ============================================================
# PERCEPTION SHELL UTILITY FUNCTIONS
# ============================================================

def calculate_effective_resolution(rp_max: float, t_value: float) -> float:
    """A7-R1: 有效感知分辨率 R_p^eff = T × R_p^max"""
    return t_value * rp_max


def calculate_heat_tax_efficiency(t_value: float) -> float:
    """A7-R1: 热税效率 η_tax = T²"""
    return t_value ** 2


def calculate_information_fidelity(t_value: float) -> float:
    """T值的物理本质: T = I_output / I_input"""
    return t_value  # T is the fidelity ratio by definition


def predict_t_value_growth(current_t: float, training_hours: float, 
                            base_rate: float = 0.05) -> float:
    """预测T值增长（基于MSS意识训练）
    3个月可提升20%-50%，按对数衰减模型"""
    months = training_hours / 720  # ~30 days/month * 24h
    gain = base_rate * (1 - math.exp(-months / 3))
    return current_t * (1 + gain)


def classify_observer(t_value: float, shell_type: PerceptionShellType) -> Dict[str, Any]:
    """基于A7对任意观察者进行分类"""
    band = TValueBand.classify(t_value)
    shell = PerceptionShell(
        shell_type=shell_type,
        t_profile=TValueProfile(t_value=t_value)
    )
    return {
        "t_value": t_value,
        "t_band": band.chinese_name,
        "civilization_level": band.civilization,
        "effective_resolution_bps": shell.effective_resolution,
        "heat_tax_efficiency": shell.t_profile.heat_tax_efficiency,
        "hardware_utilization": shell.hardware_utilization,
        "resolution_vs_human": shell.resolution_multiple,
        "is_awakened": shell.t_profile.is_awakened
    }
