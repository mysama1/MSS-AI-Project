"""
MSS Resilience Historical Tracker
组织韧性历史趋势追踪器

功能：
- 多期扫描数据存储与对比
- 趋势分析（改善/恶化/波动）
- 预测预警（基于历史趋势 extrapolation）
- 可视化时间序列
"""

import json
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from organizational_resilience import (
    OrganizationalResilienceScanner, OrganizationSnapshot
)

@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    metric_name: str
    values: List[float]
    trend_direction: str  # "improving", "declining", "stable", "volatile"
    slope: float  # 线性回归斜率
    volatility: float  # 波动率（标准差/均值）
    forecast_next: float  # 下期预测值
    alert_level: str  # "none", "watch", "warning", "critical"

@dataclass
class ResilienceHistory:
    """组织韧性历史记录"""
    org_id: str
    org_name: str
    snapshots: List[OrganizationSnapshot] = field(default_factory=list)

    def add_snapshot(self, snapshot: OrganizationSnapshot):
        """添加新快照"""
        self.snapshots.append(snapshot)
        # 按时间排序
        self.snapshots.sort(key=lambda s: s.timestamp)

    def get_metric_series(self, metric_name: str) -> List[Tuple[str, float]]:
        """
        获取指标时间序列

        metric_name: "O_d", "phi", "gamma", "innovation_rate", "resilience_score"
        """
        series = []
        for snap in self.snapshots:
            value = getattr(snap, f"global_{metric_name}", None)
            if value is None and metric_name == "resilience_score":
                value = snap.resilience_score
            if value is not None:
                series.append((snap.timestamp, value))
        return series

    def analyze_trend(self, metric_name: str, window: int = 6) -> TrendAnalysis:
        """
        分析指标趋势

        Args:
            metric_name: 指标名称
            window: 分析窗口期数（最近N期）
        """
        series = self.get_metric_series(metric_name)

        if len(series) < 2:
            return TrendAnalysis(
                metric_name=metric_name,
                values=[],
                trend_direction="insufficient_data",
                slope=0.0,
                volatility=0.0,
                forecast_next=0.0,
                alert_level="none"
            )

        # 使用最近window期
        recent = series[-window:]
        values = [v for _, v in recent]

        # 简单线性回归
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0.0

        # 波动率
        if y_mean != 0:
            volatility = math.sqrt(sum((v - y_mean) ** 2 for v in values) / n) / abs(y_mean)
        else:
            volatility = 0.0

        # 趋势方向
        if abs(slope) < 0.01 * abs(y_mean):
            trend_direction = "stable"
        elif slope > 0:
            # 对于O_d和gamma，上升是恶化；对于phi和resilience，上升是改善
            trend_direction = "improving" if metric_name in ["phi", "innovation_rate", "resilience_score"] else "declining"
        else:
            trend_direction = "declining" if metric_name in ["phi", "innovation_rate", "resilience_score"] else "improving"

        # 预测下一期
        forecast_next = values[-1] + slope

        # 预警级别
        alert_level = self._determine_alert(metric_name, values[-1], trend_direction, volatility)

        return TrendAnalysis(
            metric_name=metric_name,
            values=values,
            trend_direction=trend_direction,
            slope=slope,
            volatility=volatility,
            forecast_next=forecast_next,
            alert_level=alert_level
        )

    def _determine_alert(self, metric_name: str, current_value: float,
                         trend: str, volatility: float) -> str:
        """确定预警级别"""
        # 阈值定义
        thresholds = {
            "O_d": {"critical": 0.7, "warning": 0.5},
            "phi": {"critical": 40, "warning": 70},
            "resilience_score": {"critical": 0.2, "warning": 0.4},
            "gamma": {"critical": 1.0, "warning": 0.5},
            "innovation_rate": {"critical": 0.1, "warning": 0.3}
        }

        if metric_name not in thresholds:
            return "none"

        th = thresholds[metric_name]

        # 检查当前值
        if metric_name == "phi":
            # phi越低越危险
            if current_value < th["critical"]:
                return "critical"
            elif current_value < th["warning"]:
                return "warning"
        elif metric_name in ["O_d", "gamma"]:
            # O_d和gamma越高越危险
            if current_value > th["critical"]:
                return "critical"
            elif current_value > th["warning"]:
                return "warning"
        else:
            # resilience_score和innovation_rate越低越危险
            if current_value < th["critical"]:
                return "critical"
            elif current_value < th["warning"]:
                return "warning"

        # 检查趋势恶化速度
        if trend == "declining" and volatility > 0.3:
            return "watch"

        return "none"

    def generate_trend_report(self) -> Dict:
        """生成完整趋势报告"""
        metrics = ["O_d", "phi", "gamma", "innovation_rate", "resilience_score"]

        report = {
            "org_id": self.org_id,
            "org_name": self.org_name,
            "snapshot_count": len(self.snapshots),
            "time_span": {
                "first": self.snapshots[0].timestamp if self.snapshots else None,
                "latest": self.snapshots[-1].timestamp if self.snapshots else None
            },
            "trends": {},
            "overall_assessment": "",
            "recommendations": []
        }

        critical_alerts = []
        warning_alerts = []

        for metric in metrics:
            analysis = self.analyze_trend(metric)
            report["trends"][metric] = {
                "direction": analysis.trend_direction,
                "current_value": analysis.values[-1] if analysis.values else None,
                "forecast_next": round(analysis.forecast_next, 4),
                "volatility": round(analysis.volatility, 4),
                "alert_level": analysis.alert_level
            }

            if analysis.alert_level == "critical":
                critical_alerts.append(metric)
            elif analysis.alert_level == "warning":
                warning_alerts.append(metric)

        # 整体评估
        if critical_alerts:
            report["overall_assessment"] = f"危急：{', '.join(critical_alerts)} 指标处于临界状态"
        elif warning_alerts:
            report["overall_assessment"] = f"预警：{', '.join(warning_alerts)} 指标需要关注"
        else:
            report["overall_assessment"] = "组织韧性处于可控范围"

        # 生成建议
        if "resilience_score" in critical_alerts:
            report["recommendations"].append("【生死线】组织韧性指数跌破临界，立即启动升维程序")
        if "O_d" in critical_alerts:
            report["recommendations"].append("【紧急】规范场强过高，削减审批层级和会议时长")
        if "phi" in critical_alerts:
            report["recommendations"].append("【紧急】意义势能过低，开展意义对齐工作坊")

        if not report["recommendations"]:
            report["recommendations"].append("继续保持当前管理策略，定期监测")

        return report

class ResilienceTrackerManager:
    """韧性追踪管理器"""

    def __init__(self, storage_dir: str = "resilience_history"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.histories: Dict[str, ResilienceHistory] = {}

    def get_or_create_history(self, org_id: str, org_name: str) -> ResilienceHistory:
        """获取或创建历史记录"""
        if org_id not in self.histories:
            self.histories[org_id] = ResilienceHistory(org_id=org_id, org_name=org_name)
            # 尝试加载已有数据
            self._load_history(org_id)
        return self.histories[org_id]

    def record_scan(self, org_id: str, org_name: str, snapshot: OrganizationSnapshot):
        """记录一次扫描"""
        history = self.get_or_create_history(org_id, org_name)
        history.add_snapshot(snapshot)
        self._save_history(org_id)

    def _save_history(self, org_id: str):
        """保存历史到文件"""
        history = self.histories[org_id]
        filepath = self.storage_dir / f"{org_id}.json"

        data = {
            "org_id": history.org_id,
            "org_name": history.org_name,
            "snapshots": []
        }

        for snap in history.snapshots:
            data["snapshots"].append({
                "snapshot_id": snap.snapshot_id,
                "timestamp": snap.timestamp,
                "global_O_d": snap.global_O_d,
                "global_phi": snap.global_phi,
                "global_gamma": snap.global_gamma,
                "global_innovation_rate": snap.global_innovation_rate,
                "resilience_score": snap.resilience_score,
                "resilience_grade": snap.resilience_grade
            })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_history(self, org_id: str):
        """从文件加载历史"""
        filepath = self.storage_dir / f"{org_id}.json"

        if not filepath.exists():
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            history = self.histories[org_id]

            for snap_data in data.get("snapshots", []):
                snap = OrganizationSnapshot(
                    snapshot_id=snap_data["snapshot_id"],
                    timestamp=snap_data["timestamp"]
                )
                snap.global_O_d = snap_data["global_O_d"]
                snap.global_phi = snap_data["global_phi"]
                snap.global_gamma = snap_data["global_gamma"]
                snap.global_innovation_rate = snap_data["global_innovation_rate"]
                snap.resilience_score = snap_data["resilience_score"]
                snap.resilience_grade = snap_data["resilience_grade"]

                history.snapshots.append(snap)

        except Exception as e:
            print(f"Warning: Failed to load history for {org_id}: {e}")

    def list_organizations(self) -> List[Tuple[str, str, int]]:
        """列出所有追踪的组织"""
        result = []
        for org_id, history in self.histories.items():
            result.append((org_id, history.org_name, len(history.snapshots)))
        return result

# 便捷函数
def track_organization_scans(
    org_data_list: List[Dict],
    org_id: str = "ORG001",
    org_name: str = "示例组织"
) -> ResilienceHistory:
    """
    追踪一系列组织扫描

    Args:
        org_data_list: 多期组织数据列表
        org_id: 组织ID
        org_name: 组织名称

    Returns:
        ResilienceHistory对象
    """
    scanner = OrganizationalResilienceScanner()
    manager = ResilienceTrackerManager()

    for org_data in org_data_list:
        snapshot = scanner.scan_organization(org_data)
        manager.record_scan(org_id, org_name, snapshot)

    return manager.get_or_create_history(org_id, org_name)

if __name__ == "__main__":
    # 演示
    print("=" * 70)
    print("MSS Resilience Historical Tracker Demo")
    print("=" * 70)

    from virtual_data_generator import VirtualDataGenerator, IndustryTemplate

    gen = VirtualDataGenerator(seed=42)
    scanner = OrganizationalResilienceScanner()
    manager = ResilienceTrackerManager()

    # 生成12个月的衰退趋势数据
    print("\n1. 生成12个月历史数据...")
    series = gen.generate_historical_series(
        IndustryTemplate.TECH_STARTUP,
        org_name="红移科技",
        months=12,
        trend="declining",
        start_stress=0.1,
        end_stress=0.7
    )

    # 逐月扫描并记录
    for org_data in series:
        snapshot = scanner.scan_organization(org_data)
        manager.record_scan("RED001", "红移科技", snapshot)

    print(f"   已记录 {len(series)} 期扫描数据")

    # 获取历史并分析
    history = manager.get_or_create_history("RED001", "红移科技")

    print("\n2. 趋势分析:")
    for metric in ["O_d", "phi", "resilience_score"]:
        analysis = history.analyze_trend(metric)
        print(f"   {metric}: {analysis.trend_direction}")
        print(f"      当前: {analysis.values[-1]:.4f}, 预测下期: {analysis.forecast_next:.4f}")
        print(f"      波动率: {analysis.volatility:.4f}, 预警: {analysis.alert_level}")

    # 生成完整报告
    print("\n3. 完整趋势报告:")
    report = history.generate_trend_report()
    print(f"   整体评估: {report['overall_assessment']}")
    print(f"   建议:")
    for rec in report["recommendations"]:
        print(f"      - {rec}")

    print("\n4. 追踪的组织列表:")
    for org_id, org_name, count in manager.list_organizations():
        print(f"   {org_id} ({org_name}): {count} 期数据")
