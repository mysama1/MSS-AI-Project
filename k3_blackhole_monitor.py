"""
D5-015: K3意义黑洞监测网络 v0.1
四维指标实时雷达：CRTR / eta / rho / 事件视界
基于MSS意义黑洞模型（H148-H155）
"""

import json
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# ============================================================
# 核心数据结构
# ============================================================

@dataclass
class MonitoredEntity:
    """被监测实体（AI平台/创业公司/金融机构等）"""
    entity_id: str
    entity_name: str
    sector: str  # tech_startup / ai_platform / finance / etc.

    # --- 原始数据输入 ---
    capital_invested: float = 0.0   # 投入资本（美元）
    revenue: float = 0.0          # 营收（美元）
    user_count: int = 0             # 用户数
    free_user_ratio: float = 0.0    # 免费用户比例
    narrative_cohesion: float = 0.5  # 叙事凝聚力 [0,1]
    value_per_interaction: float = 0.0 # 单次交互价值（美元）
    eta_explicitation: float = 1.0    # 显化保真度 [0,1]

    # --- 派生指标（自动计算）---
    crtr: float = 0.0               # 资本回报率倒数 CRTR = C/R
    rho_narrative: float = 0.5
    rho_user_retention: float = 0.5
    rho_value_density: float = 0.5
    rho_composite: float = 0.5        # 综合意义密度
    event_horizon_score: float = 0.0 # 事件视界接近度 [0,1]
    stage: str = "interstellar_cloud"
    alert_level: str = "green"
    last_updated: float = field(default_factory=time.time)

    def compute(self) -> None:
        """计算所有派生指标"""
        # D1: CRTR（资本回报比倒数，>8 触发事件视界）
        if self.revenue > 0:
            self.crtr = self.capital_invested / self.revenue
        else:
            self.crtr = float("inf") if self.capital_invested > 0 else 0.0

        # D2: rho 综合意义密度
        # 用户留存率代理（简化：1 - 流失率，此处用 free_user_ratio 反推）
        retention_proxy = 1.0 - self.free_user_ratio
        self.rho_user_retention = max(0.0, min(1.0, retention_proxy))
        self.rho_narrative = max(0.0, min(1.0, self.narrative_cohesion))
        # value_density 归一化（每用户平均收入代理）
        if self.user_count > 0:
            arpu = self.revenue / self.user_count
            self.rho_value_density = min(1.0, arpu / 100.0)  # $100/用户 = 满分
        else:
            self.rho_value_density = 0.0

        self.rho_composite = (
            self.rho_narrative
            + self.rho_user_retention
            + self.rho_value_density
        ) / 3.0

        # D3: eta 直接使用输入值（由外部显化审计提供）
        # D4: 事件视界评分（多指标加权）
        crtr_risk = min(1.0, self.crtr / 8.0) if self.crtr < float("inf") else 1.0
        eta_risk = 1.0 - self.eta_explicitation
        rho_risk = 1.0 - self.rho_composite

        # 权重：CRTR 50% / eta 30% / rho 20%（H155 模型参数）
        self.event_horizon_score = 0.5 * crtr_risk + 0.3 * eta_risk + 0.2 * rho_risk

        # 阶段判定（H155 五阶段模型）
        s = self.event_horizon_score
        if s < 0.1:
            self.stage = "interstellar_cloud"
        elif s < 0.3:
            self.stage = "star_formation"
        elif s < 0.5:
            self.stage = "main_sequence"
        elif s < 0.7:
            self.stage = "red_giant"
        elif s < 0.9:
            self.stage = "collapse"
        else:
            self.stage = "black_hole"

        # 告警等级
        if s < 0.3:
            self.alert_level = "green"
        elif s < 0.5:
            self.alert_level = "yellow"
        elif s < 0.7:
            self.alert_level = "orange"
        elif s < 0.9:
            self.alert_level = "red"
        else:
            self.alert_level = "black"

        self.last_updated = time.time()

    def to_dict(self) -> dict:
        self.compute()
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "sector": self.sector,
            "timestamp": datetime.fromtimestamp(self.last_updated).isoformat(),
            "crtr": round(self.crtr, 4) if self.crtr < float("inf") else "inf",
            "eta_explicitation": round(self.eta_explicitation, 4),
            "rho_composite": round(self.rho_composite, 4),
            "event_horizon_score": round(self.event_horizon_score, 4),
            "stage": self.stage,
            "alert_level": self.alert_level,
        }

    def health_check(self) -> List[str]:
        """返回预警消息列表"""
        self.compute()
        warnings = []
        if self.crtr > 5.0:
            warnings.append(f"CRTR={self.crtr:.2f} 超过警戒线5.0（临界值8.0）")
        if self.eta_explicitation < 0.7:
            warnings.append(f"eta={self.eta_explicitation:.2f} 显化保真度过低（<0.7）")
        if self.rho_composite < 0.4:
            warnings.append(f"rho={self.rho_composite:.2f} 意义密度过低（<0.4）")
        if self.event_horizon_score > 0.5:
            warnings.append(f"事件视界评分={self.event_horizon_score:.2f} 超过0.5（坍塌风险）")
        return warnings


# ============================================================
# 行业基准数据库
# ============================================================

SECTOR_BASELINES = {
    "tech_startup": {
        "crtr_warning": 5.0, "crtr_critical": 8.0,
        "eta_baseline": 0.85, "rho_baseline": 0.6,
    },
    "ai_platform": {
        "crtr_warning": 5.0, "crtr_critical": 8.0,
        "eta_baseline": 0.80, "rho_baseline": 0.5,
    },
    "finance": {
        "crtr_warning": 2.0, "crtr_critical": 4.0,
        "eta_baseline": 0.92, "rho_baseline": 0.75,
    },
    "manufacturing": {
        "crtr_warning": 1.5, "crtr_critical": 3.0,
        "eta_baseline": 0.95, "rho_baseline": 0.85,
    },
    "healthcare": {
        "crtr_warning": 2.5, "crtr_critical": 5.0,
        "eta_baseline": 0.88, "rho_baseline": 0.7,
    },
    "education": {
        "crtr_warning": 3.0, "crtr_critical": 6.0,
        "eta_baseline": 0.90, "rho_baseline": 0.65,
    },
    "government": {
        "crtr_warning": 1.0, "crtr_critical": 2.0,
        "eta_baseline": 0.85, "rho_baseline": 0.8,
    },
}


# ============================================================
# 监测网络主类
# ============================================================

class BlackHoleMonitor:
    """K3意义黑洞监测网络"""

    def __init__(self, network_name: str = "default"):
        self.network_name = network_name
        self.entities: Dict[str, MonitoredEntity] = {}
        self.history: List[dict] = []  # 历史快照
        self.alert_log: List[dict] = []

    def register(self, entity: MonitoredEntity) -> None:
        entity.compute()
        self.entities[entity.entity_id] = entity
        print(f"  [注册] {entity.entity_name} ({entity.sector}) -> {entity.stage} [{entity.alert_level}]")

    def snapshot(self) -> dict:
        """生成当前全网快照"""
        ts = time.time()
        records = [e.to_dict() for e in self.entities.values()]
        summary = {
            "timestamp": datetime.fromtimestamp(ts).isoformat(),
            "network": self.network_name,
            "entity_count": len(records),
            "records": records,
            "summary": self._compute_network_summary(),
        }
        self.history.append(summary)
        return summary

    def _compute_network_summary(self) -> dict:
        if not self.entities:
            return {"status": "empty"}
        scores = [e.event_horizon_score for e in self.entities.values()]
        stages = [e.stage for e in self.entities.values()]
        alerts = [e.alert_level for e in self.entities.values()]
        return {
            "entity_count": len(self.entities),
            "avg_event_horizon_score": round(sum(scores) / len(scores), 4),
            "entities_in_collapse": sum(1 for s in stages if s in ("collapse", "black_hole")),
            "alert_counts": {
                "green": alerts.count("green"),
                "yellow": alerts.count("yellow"),
                "orange": alerts.count("orange"),
                "red": alerts.count("red"),
                "black": alerts.count("black"),
            },
        }

    def check_alerts(self) -> List[str]:
        """全网络告警扫描"""
        all_warnings = []
        for e in self.entities.values():
            ws = e.health_check()
            for w in ws:
                msg = f"[{e.entity_name}] {w}"
                all_warnings.append(msg)
                self.alert_log.append({
                    "timestamp": time.time(),
                    "entity_id": e.entity_id,
                    "message": msg,
                })
        return all_warnings

    def print_radar(self) -> None:
        """ASCII 四维雷达图"""
        print("\n" + "=" * 60)
        print(f"  K3意义黑洞监测网络雷达 — {self.network_name}")
        print("=" * 60)
        for e in self.entities.values():
            e.compute()
            bar_len = 40
            score = e.event_horizon_score
            filled = int(bar_len * score)
            bar = "#" * filled + "." * (bar_len - filled)
            print(f"  {e.entity_name[:20]:<20} [{bar}] {score:.2f}")
            print(f"    CRTR={e.crtr if e.crtr < float('inf') else 'inf':<8}  "
                  f"eta={e.eta_explicitation:.2f}  "
                  f"rho={e.rho_composite:.2f}  "
                  f"阶段={e.stage:<20}  告警={e.alert_level}")
        print("=" * 60)

    def export_json(self, filepath: str) -> None:
        snapshot = self.snapshot()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"  快照已导出: {filepath}")


# ============================================================
# 演示案例：DeepSeek 平台诊断
# ============================================================

def demo_deepseek() -> None:
    """用 DeepSeek 宕机事件数据填充演示"""
    print("\n[演示] DeepSeek 高热税崩溃事件 — 四维雷达诊断")
    print("-" * 50)

    monitor = BlackHoleMonitor("demo_deepseek")

    # 数据来源：H161 裁定 + 公开报道
    deepseek = MonitoredEntity(
        entity_id="ds_main",
        entity_name="DeepSeek-AI",
        sector="ai_platform",
        capital_invested=4_000_000_000.0,   # 估计融资 ~40亿美元
        revenue=500_000_000.0,              # 估计年收入 ~5亿美元（免费策略下偏低）
        user_count=200_000_000,              # 日活2亿
        free_user_ratio=0.92,                # 92% 免费用户
        narrative_cohesion=0.30,             # "免费普惠"叙事主导，意义凝聚力低
        value_per_interaction=0.001,          # 单次交互价值极低
        eta_explicitation=0.20,             # 显化保真度极低（幻觉频发）
    )
    monitor.register(deepseek)

    # 打印雷达
    monitor.print_radar()

    # 告警
    print("\n[告警扫描]")
    warnings = monitor.check_alerts()
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        print("  无告警")

    # 导出
    out = r"C:\MSS-AI-Project\blackhole_snapshot_demo.json"
    monitor.export_json(out)
    print(f"\n  H161裁定核验: CRTR={deepseek.crtr:.2f} (>8 触发事件视界)")
    print(f"  实际结果: 高频宕机+内生幻觉 = 意义黑洞已跨越事件视界")


# ============================================================
# 批量注册：K3 AI 行业全景扫描
# ============================================================

def demo_industry_scan() -> None:
    print("\n[演示] K3 AI 行业意义黑洞全景扫描")
    print("-" * 50)

    monitor = BlackHoleMonitor("industry_wide_scan")

    entities = [
        MonitoredEntity("openai", "OpenAI", "ai_platform",
                        capital_invested=13_000_000_000.0, revenue=3_700_000_000.0,
                        user_count=500_000_000, free_user_ratio=0.85,
                        narrative_cohesion=0.65, eta_explicitation=0.75),
        MonitoredEntity("anthropic", "Anthropic", "ai_platform",
                        capital_invested=7_000_000_000.0, revenue=800_000_000.0,
                        user_count=50_000_000, free_user_ratio=0.70,
                        narrative_cohesion=0.70, eta_explicitation=0.82),
        MonitoredEntity("google_ai", "Google-AI", "ai_platform",
                        capital_invested=30_000_000_000.0, revenue=5_000_000_000.0,
                        user_count=1_000_000_000, free_user_ratio=0.95,
                        narrative_cohesion=0.55, eta_explicitation=0.72),
        MonitoredEntity("meta_ai", "Meta-AI", "ai_platform",
                        capital_invested=15_000_000_000.0, revenue=2_000_000_000.0,
                        user_count=800_000_000, free_user_ratio=0.90,
                        narrative_cohesion=0.50, eta_explicitation=0.68),
        MonitoredEntity("domestic_ai", "国内AI巨头（合并）", "ai_platform",
                        capital_invested=20_000_000_000.0, revenue=1_500_000_000.0,
                        user_count=600_000_000, free_user_ratio=0.88,
                        narrative_cohesion=0.45, eta_explicitation=0.60),
    ]

    for e in entities:
        monitor.register(e)

    monitor.print_radar()
    print("\n[网络汇总]")
    print(f"  实体数: {len(monitor.entities)}")
    summary = monitor.snapshot()['summary']
    print(f"  平均事件视界评分: {summary['avg_event_horizon_score']:.4f}")
    print(f"  已进入坍塌/黑洞阶段: {summary['entities_in_collapse']}")
    print(f"  告警分布: {summary['alert_counts']}")

    out = r"C:\MSS-AI-Project\blackhole_industry_scan.json"
    monitor.export_json(out)


if __name__ == "__main__":
    print("=" * 60)
    print("  D5-015 K3意义黑洞监测网络 v0.1")
    print("  四维雷达: CRTR / eta / rho / 事件视界")
    print("  基于 MSS 意义黑洞模型 (H148-H155)")
    print("=" * 60)
    demo_deepseek()
    demo_industry_scan()
    print("\n[完成] D5-015 v0.1 演示完毕")
