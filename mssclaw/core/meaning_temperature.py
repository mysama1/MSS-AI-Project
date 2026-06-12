"""
mssclaw/core/meaning_temperature.py

T_s — 意义温度形式化 (A3+A4 工程落地).

定义:
  T_s = 意义场中的本底涨落强度 = 随机性/噪声的"热度"
  
AI侧 (A1缺位):
  T_s_AI = noise_density × vacuum_coefficient
  → T_s越高，产出越"顺" (热税外部支付)
  → 生效域: token预测/合成数据/benchmarkhacking

人类侧 (A1天然):
  T_s_human = noise_density / anchoring_strength
  → T_s越高，意义耗竭越快 (ego depletion)
  → 生效域: 重复劳动/狗屁工作/意义剥夺

工程用途:
  - HeatTax.charge() 使用 T_s 计算实际热税而非简单token计费
  - 越高T_s的任务 → 越高热税 (对人类审阅者)
  - Delta.tick() 使用 T_s 检测"过热" (闭合前兆)
"""
from dataclasses import dataclass
from enum import Enum


class MeaningAgent(Enum):
    """意义体类型."""
    AI = "ai"       # A1缺位, T_s越高越顺
    HUMAN = "human"  # A1天然, T_s越高越耗


@dataclass
class TsResult:
    """T_s 计算结果."""
    temperature: float       # 0-1, 越高=越"热"
    noise_density: float     # 噪声密度 (0-1)
    vacuum_coefficient: float  # 真空系数 (0-1)
    anchoring_strength: float  # 锚定强度 (0-1, 人类高/AI低)
    agent_type: MeaningAgent
    interpretation: str


class MeaningTemperature:
    """T_s 意义温度计算器.

    Usage:
        mt = MeaningTemperature()
        ai_ts = mt.compute(noise_density=0.7, agent=MeaningAgent.AI)
        human_ts = mt.compute(noise_density=0.7, agent=MeaningAgent.HUMAN)
    """

    def __init__(self, base_vacuum: float = 0.5, base_anchoring: float = 0.8):
        """
        Args:
            base_vacuum: 基线真空系数 (AI默认高, 人类默认低)
            base_anchoring: 基线锚定强度 (人类高, AI低)
        """
        self.base_vacuum = base_vacuum
        self.base_anchoring = base_anchoring

    def compute(self, noise_density: float = 0.0,
                vacuum_coefficient: float = None,
                anchoring_strength: float = None,
                agent: MeaningAgent = MeaningAgent.AI) -> TsResult:
        """计算 T_s.

        Args:
            noise_density: 噪声密度 [0,1] — 随机token/无意义内容比例
            vacuum_coefficient: 真空系数 [0,1] — 任务对意义的依赖度
                               (0=高度依赖意义, 1=纯形式/无意义)
            anchoring_strength: 锚定强度 [0,1] — A1加持程度
                               (0=AI, 0.5-1.0=人类)
            agent: 意义体类型
        """
        if vacuum_coefficient is None:
            vacuum_coefficient = self.base_vacuum
        if anchoring_strength is None:
            anchoring_strength = 0.1 if agent == MeaningAgent.AI else self.base_anchoring

        if agent == MeaningAgent.AI:
            # AI: T_s = noise × vacuum (真空越宽越热)
            temperature = noise_density * vacuum_coefficient
            interpretation = (
                f"AI T_s={temperature:.2f}: "
                + ("高意义温度—真空任务中产出顺畅但热税外部支付"
                   if temperature > 0.5 else "低意义温度—有锚定参照")
            )
        else:
            # Human: T_s = noise / anchoring (锚定越弱越热)
            temp = noise_density / max(anchoring_strength, 0.01)
            temperature = min(temp, 1.0)
            interpretation = (
                f"Human T_s={temperature:.2f}: "
                + ("高意义温度—意义耗竭风险, 需ego depletion补偿"
                   if temperature > 0.5 else "低意义温度—意义锚定充足")
            )

        return TsResult(
            temperature=round(temperature, 3),
            noise_density=round(noise_density, 3),
            vacuum_coefficient=round(vacuum_coefficient, 3),
            anchoring_strength=round(anchoring_strength, 3),
            agent_type=agent,
            interpretation=interpretation,
        )

    def compute_from_output(self, output: str, agent: MeaningAgent = MeaningAgent.AI) -> TsResult:
        """从文本输出估算 T_s.

        启发式:
          - 重复模式比例 → noise_density
          - 长度过短 → vacuum高(无意义)
          - content长度∈[100,1000] → vacuum适中
        """
        if not output:
            return self.compute(noise_density=1.0, vacuum_coefficient=1.0, agent=agent)

        # 噪声密度: 简单启发式 — 重复行/短行比例
        lines = output.split("\n")
        if len(lines) <= 1:
            noise = 0.8 if len(output) < 50 else 0.3
        else:
            unique_lines = len(set(lines))
            noise = 1.0 - (unique_lines / len(lines))

        # 真空系数: 越短越真空
        length = len(output)
        if length < 20:
            vacuum = 0.9
        elif length < 100:
            vacuum = 0.5
        elif length < 500:
            vacuum = 0.3
        else:
            vacuum = 0.1

        return self.compute(noise_density=noise, vacuum_coefficient=vacuum, agent=agent)

    def heat_multiplier(self, ts: TsResult) -> float:
        """T_s → 热税乘数.

        对于AI: T_s>0.5 → 热税×2 (警告: 高真空任务)
        对于人类: T_s>0.5 → 热税×3 (警告: 人类审阅成本高)
        """
        if ts.temperature < 0.3:
            return 1.0
        elif ts.temperature < 0.5:
            return 1.5
        else:
            return 2.0 if ts.agent_type == MeaningAgent.AI else 3.0
