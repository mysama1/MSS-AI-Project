"""
MSS Organizational Resilience Scanner - Symbolic Backend
组织韧性扫描器符号推理后端

基于MSS v12.2公理体系，实现组织健康度的符号化评估：
- 规范场强 O_d 计算
- 意义势能 Φ 评估  
- 热税系数 γ 监测
- 创新率 R 跟踪
- 韧性指数 M 综合评分
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum, auto
import json
import math
from datetime import datetime
from collections import defaultdict

from symbolic_engine_v3 import (
    SymbolicEngineV3, HeatTaxMonitor, HeatTaxState,
    MSSv12AxiomSystem, AxiomType
)
from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType, InferenceResult
)


class DepartmentType(Enum):
    """部门类型"""
    RND = auto()           # 研发
    PRODUCT = auto()       # 产品
    OPERATIONS = auto()    # 运营
    ADMIN = auto()         # 行政支撑
    SALES = auto()         # 销售
    STRATEGY = auto()      # 战略


@dataclass
class DepartmentMetrics:
    """部门级指标"""
    dept_id: str
    dept_name: str
    dept_type: DepartmentType
    
    # 核心MSS指标
    O_d: float = 0.0           # 规范场强 (0-1)
    phi: float = 100.0         # 意义势能 (0-200)
    gamma: float = 0.0         # 热税系数
    innovation_rate: float = 1.0  # 创新率
    
    # K3可观测指标
    headcount: int = 0         # 人数
    approval_layers: int = 0   # 审批层级
    meeting_hours_weekly: float = 0.0  # 周会议时长
    project_lead_time: float = 0.0     # 项目交付周期(天)
    employee_satisfaction: float = 0.0  # 员工满意度 (0-10)
    
    # 计算时间戳
    computed_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OrganizationSnapshot:
    """组织全景快照"""
    snapshot_id: str
    timestamp: str
    
    # 全局指标
    global_O_d: float = 0.0
    global_phi: float = 100.0
    global_gamma: float = 0.0
    global_innovation_rate: float = 1.0
    
    # 部门指标
    departments: Dict[str, DepartmentMetrics] = field(default_factory=dict)
    
    # 韧性指数 (综合评分)
    resilience_score: float = 0.0
    resilience_grade: str = "UNKNOWN"
    
    # 诊断结果
    diagnosis: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class OrganizationalResilienceScanner:
    """
    组织韧性扫描器
    
    基于MSS v12.2公理体系，将K3可观测指标映射到L1/L2符号指标，
    实现组织健康度的形式化评估。
    """
    
    # K3 → L1 映射参数 (经验校准)
    CALIBRATION = {
        "O_d_base": 0.15,           # 基础规范场强
        "O_d_per_approval_layer": 0.08,  # 每层审批增加的O_d
        "O_d_per_meeting_hour": 0.02,    # 每小时会议增加的O_d
        "phi_per_satisfaction": 10.0,    # 每点满意度对应的phi
        "phi_per_employee": 0.5,         # 每人对应的phi基数
        "gamma_base": 0.1,               # 基础热税
        "innovation_threshold": 0.3,     # 创新率警戒线
        "resilience_threshold_high": 0.8,
        "resilience_threshold_medium": 0.5,
        "resilience_threshold_low": 0.3,
    }
    
    def __init__(self, symbolic_engine: Optional[SymbolicEngineV3] = None):
        self.engine = symbolic_engine or SymbolicEngineV3()
        self.monitor = HeatTaxMonitor()
        self.history: List[OrganizationSnapshot] = []
        
        # 部门类型权重 (基于MSS意义密度理论)
        self.dept_weights = {
            DepartmentType.RND: 1.5,        # 研发: 高意义密度
            DepartmentType.PRODUCT: 1.3,    # 产品: 较高意义密度
            DepartmentType.STRATEGY: 1.2,   # 战略: 较高意义密度
            DepartmentType.SALES: 1.0,      # 销售: 中等意义密度
            DepartmentType.OPERATIONS: 0.9, # 运营: 中等意义密度
            DepartmentType.ADMIN: 0.6,      # 行政: 低意义密度 (但必要)
        }
    
    def compute_department_metrics(self, dept_data: Dict) -> DepartmentMetrics:
        """
        计算部门级MSS指标
        
        K3输入示例:
        {
            "dept_id": "D001",
            "dept_name": "研发中心",
            "dept_type": "RND",
            "headcount": 50,
            "approval_layers": 3,
            "meeting_hours_weekly": 15.0,
            "project_lead_time": 45.0,
            "employee_satisfaction": 7.5
        }
        """
        dept_type = DepartmentType[dept_data.get("dept_type", "ADMIN")]
        
        # 计算规范场强 O_d
        O_d = self.CALIBRATION["O_d_base"]
        O_d += dept_data.get("approval_layers", 0) * self.CALIBRATION["O_d_per_approval_layer"]
        O_d += dept_data.get("meeting_hours_weekly", 0) * self.CALIBRATION["O_d_per_meeting_hour"]
        
        # 项目交付周期影响 (越长O_d越高)
        lead_time = dept_data.get("project_lead_time", 30.0)
        if lead_time > 30:
            O_d += min(0.2, (lead_time - 30) / 300)
        
        O_d = min(1.0, max(0.0, O_d))
        
        # 计算意义势能 phi
        phi = self.CALIBRATION["phi_per_satisfaction"] * dept_data.get("employee_satisfaction", 5.0)
        phi += self.CALIBRATION["phi_per_employee"] * dept_data.get("headcount", 10)
        
        # 高意义密度部门加成
        phi *= self.dept_weights.get(dept_type, 1.0)
        
        phi = min(200.0, max(0.0, phi))
        
        # 计算热税系数 gamma
        gamma = self.CALIBRATION["gamma_base"] * math.exp(2.0 * O_d)
        
        # 计算创新率
        if phi > 0:
            innovation_rate = (phi / 100.0) * (1.0 - O_d)
        else:
            innovation_rate = 0.0
        
        return DepartmentMetrics(
            dept_id=dept_data.get("dept_id", "UNKNOWN"),
            dept_name=dept_data.get("dept_name", "Unknown Department"),
            dept_type=dept_type,
            O_d=round(O_d, 4),
            phi=round(phi, 4),
            gamma=round(gamma, 4),
            innovation_rate=round(innovation_rate, 4),
            headcount=dept_data.get("headcount", 0),
            approval_layers=dept_data.get("approval_layers", 0),
            meeting_hours_weekly=dept_data.get("meeting_hours_weekly", 0.0),
            project_lead_time=dept_data.get("project_lead_time", 0.0),
            employee_satisfaction=dept_data.get("employee_satisfaction", 0.0)
        )
    
    def scan_organization(self, org_data: Dict) -> OrganizationSnapshot:
        """
        扫描整个组织
        
        输入示例:
        {
            "org_name": "红移试点",
            "departments": [
                {"dept_id": "D001", "dept_name": "研发中心", "dept_type": "RND", ...},
                {"dept_id": "D002", "dept_name": "产品部", "dept_type": "PRODUCT", ...},
                ...
            ]
        }
        """
        snapshot = OrganizationSnapshot(
            snapshot_id=f"SCAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            timestamp=datetime.now().isoformat()
        )
        
        # 计算各部门指标
        total_weighted_O_d = 0.0
        total_weighted_phi = 0.0
        total_weight = 0.0
        
        for dept_data in org_data.get("departments", []):
            metrics = self.compute_department_metrics(dept_data)
            snapshot.departments[metrics.dept_id] = metrics
            
            weight = self.dept_weights.get(metrics.dept_type, 1.0)
            total_weighted_O_d += metrics.O_d * weight
            total_weighted_phi += metrics.phi * weight
            total_weight += weight
        
        # 计算全局指标
        if total_weight > 0:
            snapshot.global_O_d = round(total_weighted_O_d / total_weight, 4)
            snapshot.global_phi = round(total_weighted_phi / total_weight, 4)
        
        snapshot.global_gamma = round(
            self.CALIBRATION["gamma_base"] * math.exp(2.0 * snapshot.global_O_d), 4
        )
        
        if snapshot.global_phi > 0:
            snapshot.global_innovation_rate = round(
                (snapshot.global_phi / 100.0) * (1.0 - snapshot.global_O_d), 4
            )
        
        # 计算韧性指数
        snapshot.resilience_score = self._compute_resilience_score(snapshot)
        snapshot.resilience_grade = self._grade_resilience(snapshot.resilience_score)
        
        # 生成诊断
        snapshot.diagnosis = self._generate_diagnosis(snapshot)
        snapshot.recommendations = self._generate_recommendations(snapshot)
        
        # 保存历史
        self.history.append(snapshot)
        
        return snapshot
    
    def _compute_resilience_score(self, snapshot: OrganizationSnapshot) -> float:
        """
        计算组织韧性指数 M ∈ [0, 1]
        
        基于MSS v12.2:
        M = (Φ/200) × (1-O_d) × (R/R_max) × (1-γ/γ_max)
        """
        phi_factor = snapshot.global_phi / 200.0
        od_factor = 1.0 - snapshot.global_O_d
        
        # 创新率因子
        if snapshot.global_innovation_rate > self.CALIBRATION["innovation_threshold"]:
            innovation_factor = 1.0
        else:
            innovation_factor = snapshot.global_innovation_rate / self.CALIBRATION["innovation_threshold"]
        
        # 热税因子 (gamma越大越差)
        gamma_max = self.CALIBRATION["gamma_base"] * math.exp(2.0)  # O_d=1时的gamma
        gamma_factor = max(0.0, 1.0 - snapshot.global_gamma / gamma_max)
        
        M = phi_factor * od_factor * innovation_factor * gamma_factor
        return round(min(1.0, max(0.0, M)), 4)
    
    def _grade_resilience(self, score: float) -> str:
        """韧性等级评定"""
        if score >= self.CALIBRATION["resilience_threshold_high"]:
            return "A"  # 高韧性 - 自适应进化态
        elif score >= self.CALIBRATION["resilience_threshold_medium"]:
            return "B"  # 中韧性 - 稳态运行
        elif score >= self.CALIBRATION["resilience_threshold_low"]:
            return "C"  # 低韧性 - 预警状态
        else:
            return "D"  # 危险 - 热寂临界
    
    def _generate_diagnosis(self, snapshot: OrganizationSnapshot) -> List[Dict]:
        """生成诊断报告"""
        diagnosis = []
        
        # 全局诊断
        if snapshot.global_O_d > 0.6:
            diagnosis.append({
                "level": "CRITICAL",
                "category": "规范场强过高",
                "metric": f"O_d = {snapshot.global_O_d}",
                "description": "组织规范场强超过不可逆临界点，创新空间被严重压缩",
                "mss_reference": "A3终极热税公理 + MECH-EVOL-002"
            })
        elif snapshot.global_O_d > 0.4:
            diagnosis.append({
                "level": "WARNING",
                "category": "规范场强偏高",
                "metric": f"O_d = {snapshot.global_O_d}",
                "description": "规范场强偏高，建议减少审批层级和会议时长",
                "mss_reference": "A3终极热税公理"
            })
        
        if snapshot.global_phi < 50.0:
            diagnosis.append({
                "level": "CRITICAL",
                "category": "意义势能过低",
                "metric": f"Φ = {snapshot.global_phi}",
                "description": "组织意义势能严重不足，员工满意度和创新动力低下",
                "mss_reference": "A1意义本体公理"
            })
        elif snapshot.global_phi < 80.0:
            diagnosis.append({
                "level": "WARNING",
                "category": "意义势能偏低",
                "metric": f"Φ = {snapshot.global_phi}",
                "description": "意义势能偏低，建议提升员工满意度和组织活力",
                "mss_reference": "A1意义本体公理"
            })
        
        if snapshot.global_innovation_rate < self.CALIBRATION["innovation_threshold"]:
            diagnosis.append({
                "level": "WARNING",
                "category": "创新率不足",
                "metric": f"R = {snapshot.global_innovation_rate}",
                "description": "创新率低于警戒线，组织可能陷入K3热寂同化",
                "mss_reference": "T2规范场涌现定理"
            })
        
        # 部门级诊断
        for dept_id, metrics in snapshot.departments.items():
            if metrics.O_d > snapshot.global_O_d + 0.2:
                diagnosis.append({
                    "level": "WARNING",
                    "category": "部门规范场异常",
                    "metric": f"{metrics.dept_name}: O_d = {metrics.O_d}",
                    "description": f"{metrics.dept_name}规范场强显著高于全局平均，成为组织瓶颈",
                    "mss_reference": "T3矛盾升维定理"
                })
        
        return diagnosis
    
    def _generate_recommendations(self, snapshot: OrganizationSnapshot) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if snapshot.global_O_d > 0.5:
            recommendations.append("【紧急】减少审批层级：将核心审批压缩至2层以内，建立快速决策通道")
            recommendations.append("【紧急】削减会议时长：周会议时间控制在10小时以内，推行异步协作")
        
        if snapshot.global_phi < 80.0:
            recommendations.append("【重要】提升员工满意度：开展意义对齐工作坊，建立内部创新基金")
            recommendations.append("【重要】优化人才结构：引入高意义密度岗位，减少行政支撑占比")
        
        if snapshot.global_innovation_rate < 0.3:
            recommendations.append("【重要】激活创新机制：建立矛盾上报通道，鼓励跨部门升维思考")
            recommendations.append("【重要】引入外部意义：与外部专家/客户建立共创机制，打破封闭系统")
        
        # 基于韧性等级的建议
        if snapshot.resilience_grade == "D":
            recommendations.append("【生死线】组织已进入热寂临界，必须立即启动升维程序：重组架构、更换领导层、引入外部冲击")
        elif snapshot.resilience_grade == "C":
            recommendations.append("【预警】组织处于低韧性状态，建议3个月内完成规范场优化和意义注入")
        
        if not recommendations:
            recommendations.append("【健康】组织韧性良好，继续保持开放性和创新活力，定期进行扫描监测")
        
        return recommendations
    
    def compare_snapshots(self, snapshot1_id: str, snapshot2_id: str) -> Dict:
        """对比两个快照，分析趋势"""
        s1 = next((s for s in self.history if s.snapshot_id == snapshot1_id), None)
        s2 = next((s for s in self.history if s.snapshot_id == snapshot2_id), None)
        
        if not s1 or not s2:
            return {"error": "Snapshot not found"}
        
        return {
            "time_delta": s2.timestamp,
            "O_d_change": round(s2.global_O_d - s1.global_O_d, 4),
            "phi_change": round(s2.global_phi - s1.global_phi, 4),
            "resilience_change": round(s2.resilience_score - s1.resilience_score, 4),
            "grade_change": f"{s1.resilience_grade} -> {s2.resilience_grade}",
            "trend": "improving" if s2.resilience_score > s1.resilience_score else "declining",
            "diagnosis_count_delta": len(s2.diagnosis) - len(s1.diagnosis)
        }
    
    def export_report(self, snapshot: OrganizationSnapshot, filepath: str):
        """导出扫描报告为JSON"""
        report = {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp,
            "global_metrics": {
                "O_d": snapshot.global_O_d,
                "phi": snapshot.global_phi,
                "gamma": snapshot.global_gamma,
                "innovation_rate": snapshot.global_innovation_rate,
                "resilience_score": snapshot.resilience_score,
                "resilience_grade": snapshot.resilience_grade
            },
            "departments": {
                dept_id: {
                    "name": metrics.dept_name,
                    "type": metrics.dept_type.name,
                    "O_d": metrics.O_d,
                    "phi": metrics.phi,
                    "gamma": metrics.gamma,
                    "innovation_rate": metrics.innovation_rate,
                    "headcount": metrics.headcount,
                    "approval_layers": metrics.approval_layers,
                    "meeting_hours_weekly": metrics.meeting_hours_weekly,
                    "project_lead_time": metrics.project_lead_time,
                    "employee_satisfaction": metrics.employee_satisfaction
                }
                for dept_id, metrics in snapshot.departments.items()
            },
            "diagnosis": snapshot.diagnosis,
            "recommendations": snapshot.recommendations,
            "mss_framework": {
                "version": "v12.2",
                "axiom_reference": "A1-A3 + T1-T3 + MECH-EVOL-002",
                "scan_methodology": "K3_observable -> L1_symbolic_mapping"
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return filepath


def create_demo_organization() -> Dict:
    """创建演示组织数据"""
    return {
        "org_name": "红移试点科技公司",
        "departments": [
            {
                "dept_id": "D001",
                "dept_name": "研发中心",
                "dept_type": "RND",
                "headcount": 45,
                "approval_layers": 2,
                "meeting_hours_weekly": 8.0,
                "project_lead_time": 35.0,
                "employee_satisfaction": 8.2
            },
            {
                "dept_id": "D002",
                "dept_name": "产品部",
                "dept_type": "PRODUCT",
                "headcount": 20,
                "approval_layers": 3,
                "meeting_hours_weekly": 12.0,
                "project_lead_time": 28.0,
                "employee_satisfaction": 7.5
            },
            {
                "dept_id": "D003",
                "dept_name": "运营中心",
                "dept_type": "OPERATIONS",
                "headcount": 30,
                "approval_layers": 4,
                "meeting_hours_weekly": 18.0,
                "project_lead_time": 14.0,
                "employee_satisfaction": 6.8
            },
            {
                "dept_id": "D004",
                "dept_name": "行政支撑",
                "dept_type": "ADMIN",
                "headcount": 15,
                "approval_layers": 5,
                "meeting_hours_weekly": 6.0,
                "project_lead_time": 7.0,
                "employee_satisfaction": 6.5
            },
            {
                "dept_id": "D005",
                "dept_name": "战略部",
                "dept_type": "STRATEGY",
                "headcount": 8,
                "approval_layers": 2,
                "meeting_hours_weekly": 5.0,
                "project_lead_time": 60.0,
                "employee_satisfaction": 8.5
            }
        ]
    }


if __name__ == "__main__":
    # 演示运行
    print("=" * 70)
    print("MSS Organizational Resilience Scanner v1.0")
    print("=" * 70)
    print()
    
    scanner = OrganizationalResilienceScanner()
    org_data = create_demo_organization()
    
    print(f"Scanning organization: {org_data['org_name']}")
    print(f"Departments: {len(org_data['departments'])}")
    print()
    
    snapshot = scanner.scan_organization(org_data)
    
    print("-" * 70)
    print("GLOBAL METRICS")
    print("-" * 70)
    print(f"  规范场强 O_d:        {snapshot.global_O_d}")
    print(f"  意义势能 Φ:          {snapshot.global_phi}")
    print(f"  热税系数 γ:          {snapshot.global_gamma}")
    print(f"  创新率 R:            {snapshot.global_innovation_rate}")
    print(f"  韧性指数 M:          {snapshot.resilience_score}")
    print(f"  韧性等级:            {snapshot.resilience_grade}")
    print()
    
    print("-" * 70)
    print("DEPARTMENT BREAKDOWN")
    print("-" * 70)
    for dept_id, metrics in snapshot.departments.items():
        print(f"  {metrics.dept_name} ({metrics.dept_type.name})")
        print(f"    O_d={metrics.O_d}, Φ={metrics.phi}, R={metrics.innovation_rate}")
    print()
    
    print("-" * 70)
    print("DIAGNOSIS")
    print("-" * 70)
    for diag in snapshot.diagnosis:
        print(f"  [{diag['level']}] {diag['category']}")
        print(f"    {diag['description']}")
    print()
    
    print("-" * 70)
    print("RECOMMENDATIONS")
    print("-" * 70)
    for i, rec in enumerate(snapshot.recommendations, 1):
        print(f"  {i}. {rec}")
    print()
    
    # 导出报告
    report_path = "organizational_resilience_report.json"
    scanner.export_report(snapshot, report_path)
    print(f"Report exported to: {report_path}")
