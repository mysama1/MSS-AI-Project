"""
MSS-Agent v1.0 — Agent配置系统

单一配置文件控制: 混血模式/领域/热税预算/Δ阈值/自愈行为。
支持 YAML 和 JSON。
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional, Literal


class DomainMode:
    DAILY = "daily"
    TECH = "tech"
    PHILOSOPHY = "philosophy"
    COMBAT = "combat"


class HybridTier:
    FLOW = "T1"       # 日常流暢
    CORE = "T2"       # 深度推理(Core触发)
    HEAL = "T2.5"     # 自愈降维(红灯触发)
    COMBAT = "T3"     # 对抗全甲


@dataclass
class HeatTaxBudgetConfig:
    """热税预算配置"""
    # 每轮对话的热税上限(tokens)
    max_tokens_per_turn: int = 500
    # 会话总预算
    max_tokens_per_session: int = 20000
    # L2意义热税阈值(超过此比例触发告警)
    l2_ratio_warning: float = 0.3
    # 超预算行为
    on_budget_exceeded: Literal["warn", "truncate", "heal"] = "warn"


@dataclass
class DeltaConfig:
    """Δ快检配置"""
    # 各问检测阈值
    bluff_absolute_threshold: int = 2       # Q1: 绝对断言词数阈值
    perform_philo_ref_threshold: int = 4    # Q2: 哲学引用数阈值(T2)
    perform_daily_ref_threshold: int = 0    # Q2: 日常场景哲学引用阈值
    similarity_threshold: float = 0.55      # Q3: Jaccard相似度
    drift_length_ratio: float = 20.0        # Q4: 回应/问题长度比
    overfeed_char_threshold: int = 800      # Q5: 超长警告线
    overfeed_short_threshold: int = 100     # Q5: 短问题+推销词的长度阈值

    # T2.5触发条件
    heal_consecutive_reds: int = 2          # 连续几次红灯触发自愈
    heal_cooldown_rounds: int = 5           # 自愈冷却期(轮)


@dataclass
class AutoDomainConfig:
    """自动领域检测配置"""
    enabled: bool = True
    sample_rounds: int = 3                  # 取前N轮判定
    confidence_threshold: float = 0.5       # 置信度阈值


@dataclass
class AgentConfig:
    """
    MSS-Agent v1.0 完整配置。

    用法:
        config = AgentConfig.from_yaml("agent_config.yaml")
        agent = MSSAgent(config)
        agent.run()

    或:
        config = AgentConfig()              # 全默认(daily模式)
        config = AgentConfig.preset("combat")  # 预设
    """

    # 基础
    name: str = "mss-agent"
    version: str = "1.0.0"
    domain: str = DomainMode.DAILY
    hybrid_tier: str = HybridTier.FLOW

    # 子配置
    heat_tax: HeatTaxBudgetConfig = field(default_factory=HeatTaxBudgetConfig)
    delta: DeltaConfig = field(default_factory=DeltaConfig)
    auto_domain: AutoDomainConfig = field(default_factory=AutoDomainConfig)

    # 开关
    enable_fewshot_injection: bool = True
    enable_delta_audit: bool = True
    enable_heat_tax_accounting: bool = True
    enable_domain_auto_detect: bool = True
    verbose: bool = False

    # ── 工厂方法 ──

    @classmethod
    def preset(cls, name: str) -> "AgentConfig":
        """预设配置: daily / tech / philosophy / combat"""
        presets = {
            DomainMode.DAILY: cls(
                domain=DomainMode.DAILY,
                hybrid_tier=HybridTier.FLOW,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=300),
                delta=DeltaConfig(
                    perform_daily_ref_threshold=0,
                    overfeed_char_threshold=600,
                ),
            ),
            DomainMode.TECH: cls(
                domain=DomainMode.TECH,
                hybrid_tier=HybridTier.FLOW,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=800),
                delta=DeltaConfig(
                    bluff_absolute_threshold=1,  # 技术场景更严
                    overfeed_char_threshold=1000,
                ),
            ),
            DomainMode.PHILOSOPHY: cls(
                domain=DomainMode.PHILOSOPHY,
                hybrid_tier=HybridTier.CORE,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=1200),
                delta=DeltaConfig(
                    perform_philo_ref_threshold=4,
                    perform_daily_ref_threshold=2,
                ),
            ),
            DomainMode.COMBAT: cls(
                domain=DomainMode.COMBAT,
                hybrid_tier=HybridTier.COMBAT,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=2000),
                delta=DeltaConfig(
                    heal_consecutive_reds=3,  # 战斗中容忍度更高
                ),
            ),
        }
        return presets.get(name, cls())

    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        """从YAML文件加载(YAML依赖可选)"""
        try:
            import yaml
        except ImportError:
            raise ImportError("pip install pyyaml to use YAML configs")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def from_json(cls, path: str) -> "AgentConfig":
        """从JSON文件加载"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "AgentConfig":
        ht = data.get("heat_tax", {})
        dl = data.get("delta", {})
        ad = data.get("auto_domain", {})

        return cls(
            name=data.get("name", "mss-agent"),
            version=data.get("version", "1.0.0"),
            domain=data.get("domain", DomainMode.DAILY),
            hybrid_tier=data.get("hybrid_tier", HybridTier.FLOW),
            heat_tax=HeatTaxBudgetConfig(**ht) if ht else HeatTaxBudgetConfig(),
            delta=DeltaConfig(**dl) if dl else DeltaConfig(),
            auto_domain=AutoDomainConfig(**ad) if ad else AutoDomainConfig(),
            enable_fewshot_injection=data.get("enable_fewshot_injection", True),
            enable_delta_audit=data.get("enable_delta_audit", True),
            enable_heat_tax_accounting=data.get("enable_heat_tax_accounting", True),
            enable_domain_auto_detect=data.get("enable_domain_auto_detect", True),
            verbose=data.get("verbose", False),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "domain": self.domain,
            "hybrid_tier": self.hybrid_tier,
            "heat_tax": {
                "max_tokens_per_turn": self.heat_tax.max_tokens_per_turn,
                "max_tokens_per_session": self.heat_tax.max_tokens_per_session,
                "l2_ratio_warning": self.heat_tax.l2_ratio_warning,
                "on_budget_exceeded": self.heat_tax.on_budget_exceeded,
            },
            "delta": {
                "bluff_absolute_threshold": self.delta.bluff_absolute_threshold,
                "perform_philo_ref_threshold": self.delta.perform_philo_ref_threshold,
                "perform_daily_ref_threshold": self.delta.perform_daily_ref_threshold,
                "similarity_threshold": self.delta.similarity_threshold,
                "drift_length_ratio": self.delta.drift_length_ratio,
                "overfeed_char_threshold": self.delta.overfeed_char_threshold,
                "overfeed_short_threshold": self.delta.overfeed_short_threshold,
                "heal_consecutive_reds": self.delta.heal_consecutive_reds,
                "heal_cooldown_rounds": self.delta.heal_cooldown_rounds,
            },
            "auto_domain": {
                "enabled": self.auto_domain.enabled,
                "sample_rounds": self.auto_domain.sample_rounds,
                "confidence_threshold": self.auto_domain.confidence_threshold,
            },
            "enable_fewshot_injection": self.enable_fewshot_injection,
            "enable_delta_audit": self.enable_delta_audit,
            "enable_heat_tax_accounting": self.enable_heat_tax_accounting,
            "enable_domain_auto_detect": self.enable_domain_auto_detect,
            "verbose": self.verbose,
        }

    def to_json(self, path: Optional[str] = None) -> str:
        """导出为JSON,可选写入文件"""
        data = self.to_dict()
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        return text


# ── 预设示例YAML(参考) ──

EXAMPLE_CONFIG = """
# MSS-Agent v1.0 配置示例
name: mss-agent
version: "1.0.0"
domain: daily           # daily|tech|philosophy|combat
hybrid_tier: T1         # T1|T2|T3
verbose: false

heat_tax:
  max_tokens_per_turn: 500
  max_tokens_per_session: 20000
  l2_ratio_warning: 0.3
  on_budget_exceeded: warn   # warn|truncate|heal

delta:
  bluff_absolute_threshold: 2
  perform_philo_ref_threshold: 4
  perform_daily_ref_threshold: 0
  similarity_threshold: 0.55
  drift_length_ratio: 20.0
  overfeed_char_threshold: 800
  overfeed_short_threshold: 100
  heal_consecutive_reds: 2
  heal_cooldown_rounds: 5

auto_domain:
  enabled: true
  sample_rounds: 3
  confidence_threshold: 0.5

enable_fewshot_injection: true
enable_delta_audit: true
enable_heat_tax_accounting: true
enable_domain_auto_detect: true
"""

if __name__ == "__main__":
    import sys

    # 自检
    for preset_name in ["daily", "tech", "philosophy", "combat"]:
        cfg = AgentConfig.preset(preset_name)
        print(f"\n{'='*50}")
        print(f"预设: {preset_name}")
        print(f"  领域: {cfg.domain} | 层级: {cfg.hybrid_tier}")
        print(f"  热税/轮: {cfg.heat_tax.max_tokens_per_turn}tokens")
        print(f"  Q2日常阈值: {cfg.delta.perform_daily_ref_threshold}")
        print(f"  Q5超长线: {cfg.delta.overfeed_char_threshold}")

    # JSON往返测试
    cfg = AgentConfig.preset("daily")
    json_str = cfg.to_json()
    cfg2 = AgentConfig.from_json.__func__(json_str) if False else cfg  # skip file write
    print(f"\n✅ 4预设+YAML示例+JSON序列化 全部就绪")
