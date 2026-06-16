"""
MSS Industry Benchmark Library
行业基准对比库

提供各行业组织韧性基准数据，用于对比分析。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class IndustryBenchmark:
    """行业基准数据"""
    industry_name: str  # 行业名称
    industry_code: str  # 行业代码

    # 典型指标范围 (min, max, median)
    typical_headcount: tuple  # 典型人数
    typical_approval_layers: tuple  # 典型审批层级
    typical_meeting_hours: tuple  # 典型周会议时长
    typical_project_lead_time: tuple  # 典型项目交付周期
    typical_satisfaction: tuple  # 典型员工满意度

    # 韧性基准 (基于MSS框架)
    resilience_benchmark: Dict[str, float]  # 韧性基准值

    # 行业特征
    characteristics: List[str]  # 行业特征标签
    risk_factors: List[str]  # 典型风险因素

# 预定义行业基准数据库
INDUSTRY_BENCHMARKS: Dict[str, IndustryBenchmark] = {
    "tech_startup": IndustryBenchmark(
        industry_name="科技初创公司",
        industry_code="TECH_STARTUP",
        typical_headcount=(10, 100, 30),
        typical_approval_layers=(1, 2, 1),
        typical_meeting_hours=(2, 8, 4),
        typical_project_lead_time=(7, 30, 14),
        typical_satisfaction=(7.0, 9.0, 8.0),
        resilience_benchmark={
            "O_d_target": 0.25,  # 低规范场强（扁平化）
            "phi_target": 120.0,  # 高意义势能（创新导向）
            "gamma_target": 0.20,  # 低热税（敏捷）
            "R_target": 0.70,  # 高创新率
            "M_target": 0.75,  # 目标韧性A级
        },
        characteristics=["扁平化", "创新导向", "快速迭代", "高风险高回报"],
        risk_factors=["资金断裂", "市场验证失败", "核心人员流失", "技术债务"]
    ),

    "tech_enterprise": IndustryBenchmark(
        industry_name="科技大型企业",
        industry_code="TECH_ENTERPRISE",
        typical_headcount=(1000, 100000, 10000),
        typical_approval_layers=(3, 7, 5),
        typical_meeting_hours=(10, 25, 15),
        typical_project_lead_time=(30, 180, 90),
        typical_satisfaction=(6.0, 8.0, 7.0),
        resilience_benchmark={
            "O_d_target": 0.55,  # 中等规范场强
            "phi_target": 90.0,  # 中等意义势能
            "gamma_target": 0.40,  # 中等热税
            "R_target": 0.35,  # 中等创新率
            "M_target": 0.45,  # 目标韧性B级
        },
        characteristics=["规模化", "流程化", "稳定现金流", "创新惰性"],
        risk_factors=["官僚化", "部门墙", "技术债务累积", "市场反应迟缓"]
    ),

    "manufacturing": IndustryBenchmark(
        industry_name="传统制造业",
        industry_code="MANUFACTURING",
        typical_headcount=(100, 10000, 1000),
        typical_approval_layers=(3, 6, 4),
        typical_meeting_hours=(5, 15, 8),
        typical_project_lead_time=(30, 365, 90),
        typical_satisfaction=(5.5, 7.5, 6.5),
        resilience_benchmark={
            "O_d_target": 0.65,  # 较高规范场强（流程严格）
            "phi_target": 60.0,  # 较低意义势能
            "gamma_target": 0.50,  # 较高热税（层级多）
            "R_target": 0.15,  # 低创新率
            "M_target": 0.25,  # 目标韧性C级
        },
        characteristics=["流程驱动", "质量导向", "资本密集", "周期性强"],
        risk_factors=["产能过剩", "成本上升", "自动化替代", "环保压力"]
    ),

    "finance": IndustryBenchmark(
        industry_name="金融服务",
        industry_code="FINANCE",
        typical_headcount=(50, 50000, 5000),
        typical_approval_layers=(4, 8, 6),
        typical_meeting_hours=(8, 20, 12),
        typical_project_lead_time=(14, 90, 45),
        typical_satisfaction=(6.0, 8.0, 7.0),
        resilience_benchmark={
            "O_d_target": 0.75,  # 高规范场强（合规严格）
            "phi_target": 70.0,  # 较低意义势能（风险厌恶）
            "gamma_target": 0.55,  # 较高热税（监管成本）
            "R_target": 0.20,  # 低创新率（监管限制）
            "M_target": 0.30,  # 目标韧性C级
        },
        characteristics=["合规驱动", "风险厌恶", "资本密集", "监管严格"],
        risk_factors=["监管变化", "技术颠覆", "信用风险", "系统性风险"]
    ),

    "healthcare": IndustryBenchmark(
        industry_name="医疗健康",
        industry_code="HEALTHCARE",
        typical_headcount=(20, 50000, 500),
        typical_approval_layers=(3, 6, 4),
        typical_meeting_hours=(5, 15, 8),
        typical_project_lead_time=(30, 365, 90),
        typical_satisfaction=(6.0, 8.5, 7.2),
        resilience_benchmark={
            "O_d_target": 0.60,  # 中等偏高规范场强
            "phi_target": 85.0,  # 中等意义势能（使命感）
            "gamma_target": 0.45,  # 中等热税
            "R_target": 0.25,  # 低中等创新率
            "M_target": 0.40,  # 目标韧性B-级
        },
        characteristics=["使命驱动", "人命关天", "监管严格", "技术敏感"],
        risk_factors=["医疗事故", "政策变化", "人才短缺", "技术迭代"]
    ),

    "education": IndustryBenchmark(
        industry_name="教育培训",
        industry_code="EDUCATION",
        typical_headcount=(10, 10000, 200),
        typical_approval_layers=(2, 5, 3),
        typical_meeting_hours=(3, 12, 6),
        typical_project_lead_time=(7, 90, 30),
        typical_satisfaction=(6.5, 8.5, 7.5),
        resilience_benchmark={
            "O_d_target": 0.40,  # 中等规范场强
            "phi_target": 100.0,  # 较高意义势能（使命感）
            "gamma_target": 0.30,  # 中等偏低热税
            "R_target": 0.40,  # 中等创新率
            "M_target": 0.55,  # 目标韧性B级
        },
        characteristics=["使命驱动", "知识密集", "周期长", "效果难量化"],
        risk_factors=["政策监管", "技术颠覆", "师资流失", "效果验证"]
    ),

    "government": IndustryBenchmark(
        industry_name="政府机构",
        industry_code="GOVERNMENT",
        typical_headcount=(50, 1000000, 5000),
        typical_approval_layers=(5, 10, 7),
        typical_meeting_hours=(10, 30, 18),
        typical_project_lead_time=(90, 730, 180),
        typical_satisfaction=(5.0, 7.0, 6.0),
        resilience_benchmark={
            "O_d_target": 0.85,  # 极高规范场强（官僚体系）
            "phi_target": 50.0,  # 低意义势能
            "gamma_target": 0.70,  # 高热税
            "R_target": 0.05,  # 极低创新率
            "M_target": 0.10,  # 目标韧性D级
        },
        characteristics=["稳定优先", "程序正义", "公共性", "变革缓慢"],
        risk_factors=["官僚僵化", "效率低下", "公信力危机", "技术落后"]
    ),

    "consulting": IndustryBenchmark(
        industry_name="咨询顾问",
        industry_code="CONSULTING",
        typical_headcount=(5, 1000, 100),
        typical_approval_layers=(1, 3, 2),
        typical_meeting_hours=(8, 25, 15),
        typical_project_lead_time=(7, 60, 30),
        typical_satisfaction=(7.0, 8.5, 7.8),
        resilience_benchmark={
            "O_d_target": 0.30,  # 低规范场强（项目制）
            "phi_target": 110.0,  # 高意义势能（知识密集）
            "gamma_target": 0.25,  # 低热税（灵活）
            "R_target": 0.55,  # 较高创新率
            "M_target": 0.65,  # 目标韧性B+级
        },
        characteristics=["知识密集", "项目驱动", "高流动性", "客户依赖"],
        risk_factors=["人才竞争", "客户集中", "知识变现", "品牌声誉"]
    ),
}

def get_benchmark(industry_code: str) -> Optional[IndustryBenchmark]:
    """获取指定行业的基准数据"""
    return INDUSTRY_BENCHMARKS.get(industry_code)

def list_industries() -> List[str]:
    """列出所有可用行业代码"""
    return list(INDUSTRY_BENCHMARKS.keys())

def compare_to_benchmark(org_metrics: Dict[str, float],
                         industry_code: str) -> Dict[str, any]:
    """
    将组织指标与行业基准对比

    Args:
        org_metrics: 组织指标字典，包含 O_d, phi, gamma, R, M
        industry_code: 行业代码

    Returns:
        对比结果字典
    """
    benchmark = get_benchmark(industry_code)
    if not benchmark:
        return {"error": f"Unknown industry code: {industry_code}"}

    results = {
        "industry": benchmark.industry_name,
        "industry_code": industry_code,
        "comparisons": {},
        "overall_assessment": "",
        "recommendations": []
    }

    # 对比各维度
    metrics_map = {
        "O_d": ("规范场强", "lower_is_better"),
        "phi": ("意义势能", "higher_is_better"),
        "gamma": ("热税系数", "lower_is_better"),
        "R": ("创新率", "higher_is_better"),
        "M": ("韧性指数", "higher_is_better"),
    }

    for metric, (name, direction) in metrics_map.items():
        if metric not in org_metrics:
            continue

        actual = org_metrics[metric]
        target_key = f"{metric}_target"
        target = benchmark.resilience_benchmark.get(target_key, 0)

        if target == 0:
            continue

        diff = actual - target
        diff_pct = (diff / target * 100) if target != 0 else 0

        if direction == "lower_is_better":
            status = "better" if diff < 0 else "worse" if diff > 0 else "equal"
        else:
            status = "better" if diff > 0 else "worse" if diff < 0 else "equal"

        results["comparisons"][metric] = {
            "name": name,
            "actual": actual,
            "benchmark": target,
            "diff": diff,
            "diff_pct": diff_pct,
            "status": status
        }

    # 整体评估
    better_count = sum(1 for c in results["comparisons"].values() if c["status"] == "better")
    worse_count = sum(1 for c in results["comparisons"].values() if c["status"] == "worse")
    total = len(results["comparisons"])

    if better_count / total >= 0.6:
        results["overall_assessment"] = f"优于行业基准 ({better_count}/{total} 维度领先)"
    elif worse_count / total >= 0.6:
        results["overall_assessment"] = f"低于行业基准 ({worse_count}/{total} 维度落后)"
    else:
        results["overall_assessment"] = f"与行业基准持平 ({better_count}/{total} 维度领先)"

    # 生成建议
    for metric, comp in results["comparisons"].items():
        if comp["status"] == "worse":
            if metric == "O_d":
                results["recommendations"].append("规范场强偏高：考虑扁平化组织架构，减少审批层级")
            elif metric == "phi":
                results["recommendations"].append("意义势能偏低：加强使命愿景传达，提升员工认同感")
            elif metric == "gamma":
                results["recommendations"].append("热税系数偏高：优化流程减少内耗，推行异步协作")
            elif metric == "R":
                results["recommendations"].append("创新率偏低：建立创新激励机制，允许试错空间")
            elif metric == "M":
                results["recommendations"].append("韧性指数偏低：综合提升各维度，启动组织升维程序")

    return results

def demo_benchmark_comparison():
    """演示行业基准对比"""
    print("=" * 70)
    print("MSS Industry Benchmark Library Demo")
    print("=" * 70)
    print()

    # 列出所有行业
    print("Available industries:")
    for code, benchmark in INDUSTRY_BENCHMARKS.items():
        print(f"  {code}: {benchmark.industry_name}")
    print()

    # 演示对比
    demo_org = {
        "O_d": 0.60,
        "phi": 109.0,
        "gamma": 0.33,
        "R": 0.43,
        "M": 0.12
    }

    print("Demo organization metrics:")
    for k, v in demo_org.items():
        print(f"  {k}: {v}")
    print()

    # 对比科技初创
    result = compare_to_benchmark(demo_org, "tech_startup")
    print(f"vs {result['industry']}:")
    print(f"  Assessment: {result['overall_assessment']}")
    print("  Details:")
    for metric, comp in result['comparisons'].items():
        status_emoji = "✅" if comp['status'] == 'better' else "❌" if comp['status'] == 'worse' else "➖"
        print(f"    {status_emoji} {comp['name']}: {comp['actual']:.2f} vs {comp['benchmark']:.2f} ({comp['diff_pct']:+.1f}%)")
    if result['recommendations']:
        print("  Recommendations:")
        for rec in result['recommendations']:
            print(f"    • {rec}")
    print()

    # 对比政府机构
    result = compare_to_benchmark(demo_org, "government")
    print(f"vs {result['industry']}:")
    print(f"  Assessment: {result['overall_assessment']}")
    print()

if __name__ == "__main__":
    demo_benchmark_comparison()
