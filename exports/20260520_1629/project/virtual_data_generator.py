"""
MSS Virtual Data Generator
虚拟组织数据生成器

基于行业基准生成仿真组织数据，支持：
- 多行业模板（科技初创/科技巨头/制造业/金融/医疗/教育/政府/咨询）
- 参数化部门配置
- 历史趋势数据生成
- 异常/压力场景模拟
"""

import json
import random
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class IndustryTemplate(Enum):
    """行业模板"""
    TECH_STARTUP = "tech_startup"
    TECH_ENTERPRISE = "tech_enterprise"
    MANUFACTURING = "manufacturing"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    GOVERNMENT = "government"
    CONSULTING = "consulting"


@dataclass
class IndustryProfile:
    """行业特征档案"""
    name: str
    avg_headcount: int
    avg_approval_layers: float
    avg_meeting_hours: float
    avg_satisfaction: float
    dept_distribution: Dict[str, float]  # 部门类型占比
    stress_factors: Dict[str, float]  # 压力因子


# 行业基准数据（基于行业研究和公开数据）
INDUSTRY_PROFILES = {
    IndustryTemplate.TECH_STARTUP: IndustryProfile(
        name="科技初创",
        avg_headcount=50,
        avg_approval_layers=2.0,
        avg_meeting_hours=8.0,
        avg_satisfaction=7.8,
        dept_distribution={"RND": 0.40, "PRODUCT": 0.20, "OPERATIONS": 0.15, "SALES": 0.15, "ADMIN": 0.10},
        stress_factors={"funding_pressure": 0.8, "growth_rate": 0.9, "burnout_risk": 0.7}
    ),
    IndustryTemplate.TECH_ENTERPRISE: IndustryProfile(
        name="科技巨头",
        avg_headcount=5000,
        avg_approval_layers=4.5,
        avg_meeting_hours=15.0,
        avg_satisfaction=6.5,
        dept_distribution={"RND": 0.30, "PRODUCT": 0.15, "OPERATIONS": 0.25, "SALES": 0.15, "STRATEGY": 0.05, "ADMIN": 0.10},
        stress_factors={"bureaucracy": 0.9, "politics": 0.8, "innovation_stagnation": 0.6}
    ),
    IndustryTemplate.MANUFACTURING: IndustryProfile(
        name="制造业",
        avg_headcount=2000,
        avg_approval_layers=5.0,
        avg_meeting_hours=12.0,
        avg_satisfaction=6.0,
        dept_distribution={"RND": 0.15, "OPERATIONS": 0.40, "SALES": 0.20, "ADMIN": 0.25},
        stress_factors={"cost_pressure": 0.9, "safety_regulations": 0.7, "union_dynamics": 0.6}
    ),
    IndustryTemplate.FINANCE: IndustryProfile(
        name="金融业",
        avg_headcount=1000,
        avg_approval_layers=6.0,
        avg_meeting_hours=18.0,
        avg_satisfaction=5.5,
        dept_distribution={"RND": 0.10, "OPERATIONS": 0.30, "SALES": 0.30, "STRATEGY": 0.10, "ADMIN": 0.20},
        stress_factors={"compliance": 0.95, "risk_aversion": 0.9, "bonus_dependency": 0.8}
    ),
    IndustryTemplate.HEALTHCARE: IndustryProfile(
        name="医疗健康",
        avg_headcount=800,
        avg_approval_layers=4.0,
        avg_meeting_hours=10.0,
        avg_satisfaction=6.8,
        dept_distribution={"RND": 0.20, "OPERATIONS": 0.35, "SALES": 0.15, "ADMIN": 0.30},
        stress_factors={"regulatory": 0.9, "liability": 0.8, "staffing_shortage": 0.7}
    ),
    IndustryTemplate.EDUCATION: IndustryProfile(
        name="教育",
        avg_headcount=300,
        avg_approval_layers=3.5,
        avg_meeting_hours=8.0,
        avg_satisfaction=7.0,
        dept_distribution={"RND": 0.10, "PRODUCT": 0.15, "OPERATIONS": 0.30, "SALES": 0.20, "ADMIN": 0.25},
        stress_factors={"funding_uncertainty": 0.7, "tenure_pressure": 0.6, "bureaucracy": 0.5}
    ),
    IndustryTemplate.GOVERNMENT: IndustryProfile(
        name="政府机构",
        avg_headcount=500,
        avg_approval_layers=7.0,
        avg_meeting_hours=20.0,
        avg_satisfaction=5.0,
        dept_distribution={"RND": 0.05, "OPERATIONS": 0.25, "SALES": 0.10, "STRATEGY": 0.15, "ADMIN": 0.45},
        stress_factors={"political_cycles": 0.9, "bureaucracy": 0.95, "accountability": 0.8}
    ),
    IndustryTemplate.CONSULTING: IndustryProfile(
        name="咨询业",
        avg_headcount=200,
        avg_approval_layers=3.0,
        avg_meeting_hours=14.0,
        avg_satisfaction=6.2,
        dept_distribution={"RND": 0.10, "PRODUCT": 0.10, "OPERATIONS": 0.20, "SALES": 0.40, "STRATEGY": 0.10, "ADMIN": 0.10},
        stress_factors={"client_pressure": 0.9, "travel_burnout": 0.8, "up_or_out": 0.7}
    ),
}


class VirtualDataGenerator:
    """虚拟数据生成器"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.generated_orgs: List[Dict] = []
    
    def generate_organization(
        self,
        industry: IndustryTemplate,
        org_name: Optional[str] = None,
        headcount: Optional[int] = None,
        stress_level: float = 0.0,  # 0=正常, 1=极端压力
        anomaly_type: Optional[str] = None  # "bureaucratic_explosion", "innovation_death", "mass_exodus"
    ) -> Dict:
        """
        生成单个组织数据
        
        Args:
            industry: 行业模板
            org_name: 组织名称（默认自动生成）
            headcount: 总人数（默认使用行业均值±30%）
            stress_level: 压力水平 0-1
            anomaly_type: 异常场景类型
        """
        profile = INDUSTRY_PROFILES[industry]
        
        # 确定总人数
        if headcount is None:
            headcount = int(profile.avg_headcount * random.uniform(0.7, 1.3))
        
        # 生成组织名称
        if org_name is None:
            org_name = self._generate_org_name(industry)
        
        # 计算基础参数（含随机波动和压力影响）
        base_approval = profile.avg_approval_layers * random.uniform(0.8, 1.2)
        base_meeting = profile.avg_meeting_hours * random.uniform(0.8, 1.2)
        base_satisfaction = profile.avg_satisfaction * random.uniform(0.9, 1.1)
        
        # 应用压力因子
        approval_layers = base_approval * (1 + stress_level * 0.5)
        meeting_hours = base_meeting * (1 + stress_level * 0.3)
        satisfaction = base_satisfaction * (1 - stress_level * 0.4)
        
        # 应用异常场景
        if anomaly_type == "bureaucratic_explosion":
            approval_layers *= 2.0
            meeting_hours *= 1.5
            satisfaction *= 0.7
        elif anomaly_type == "innovation_death":
            satisfaction *= 0.6
            meeting_hours *= 0.8
        elif anomaly_type == "mass_exodus":
            satisfaction *= 0.5
            headcount = int(headcount * 0.6)
        
        # 生成部门
        departments = self._generate_departments(
            headcount, profile, approval_layers, meeting_hours, satisfaction
        )
        
        org_data = {
            "org_name": org_name,
            "industry": industry.value,
            "headcount": headcount,
            "stress_level": stress_level,
            "anomaly_type": anomaly_type,
            "generated_at": datetime.now().isoformat(),
            "departments": departments
        }
        
        self.generated_orgs.append(org_data)
        return org_data
    
    def generate_historical_series(
        self,
        industry: IndustryTemplate,
        org_name: str,
        months: int = 12,
        trend: str = "declining",  # "improving", "stable", "declining", "volatile"
        start_stress: float = 0.0,
        end_stress: float = 0.5
    ) -> List[Dict]:
        """
        生成历史趋势数据系列
        
        Args:
            industry: 行业模板
            org_name: 组织名称
            months: 历史月数
            trend: 趋势类型
            start_stress: 起始压力水平
            end_stress: 结束压力水平
        """
        series = []
        
        for i in range(months):
            # 计算当前压力水平
            if trend == "improving":
                stress = start_stress - (start_stress - end_stress) * (i / months)
            elif trend == "declining":
                stress = start_stress + (end_stress - start_stress) * (i / months)
            elif trend == "volatile":
                stress = start_stress + (end_stress - start_stress) * (i / months) + random.uniform(-0.2, 0.2)
            else:  # stable
                stress = start_stress + random.uniform(-0.1, 0.1)
            
            stress = max(0.0, min(1.0, stress))
            
            # 生成该月数据
            org_data = self.generate_organization(
                industry=industry,
                org_name=f"{org_name} (Month {i+1})",
                stress_level=stress
            )
            
            # 添加时间戳
            timestamp = datetime.now() - timedelta(days=(months - i) * 30)
            org_data["snapshot_date"] = timestamp.isoformat()
            
            series.append(org_data)
        
        return series
    
    def generate_benchmark_dataset(
        self,
        industries: Optional[List[IndustryTemplate]] = None,
        samples_per_industry: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        生成跨行业基准数据集
        
        Returns:
            {industry_name: [org_data, ...]}
        """
        if industries is None:
            industries = list(IndustryTemplate)
        
        dataset = {}
        for industry in industries:
            orgs = []
            for i in range(samples_per_industry):
                # 正常样本
                orgs.append(self.generate_organization(industry, stress_level=random.uniform(0, 0.3)))
                # 压力样本
                orgs.append(self.generate_organization(industry, stress_level=random.uniform(0.4, 0.7)))
                # 危机样本
                orgs.append(self.generate_organization(industry, stress_level=random.uniform(0.7, 1.0)))
            
            dataset[industry.value] = orgs
        
        return dataset
    
    def _generate_org_name(self, industry: IndustryTemplate) -> str:
        """生成组织名称"""
        prefixes = {
            IndustryTemplate.TECH_STARTUP: ["星云", "量子", "红移", "拓扑", "熵减"],
            IndustryTemplate.TECH_ENTERPRISE: ["全球", "联合", "智慧", "数字", "未来"],
            IndustryTemplate.MANUFACTURING: ["精工", "重工", "智造", "工业", "材料"],
            IndustryTemplate.FINANCE: ["恒信", "汇通", "金控", "资本", "财富"],
            IndustryTemplate.HEALTHCARE: ["康宁", "生命", "仁爱", "健康", "医疗"],
            IndustryTemplate.EDUCATION: ["知行", "启明", "博雅", "学海", "育才"],
            IndustryTemplate.GOVERNMENT: ["市", "省", "国家", "区域", "联合"],
            IndustryTemplate.CONSULTING: ["思略", "智汇", "远见", "策略", "洞察"],
        }
        
        suffixes = {
            IndustryTemplate.TECH_STARTUP: "科技",
            IndustryTemplate.TECH_ENTERPRISE: "集团",
            IndustryTemplate.MANUFACTURING: "制造",
            IndustryTemplate.FINANCE: "金融",
            IndustryTemplate.HEALTHCARE: "医疗",
            IndustryTemplate.EDUCATION: "教育",
            IndustryTemplate.GOVERNMENT: "管理局",
            IndustryTemplate.CONSULTING: "咨询",
        }
        
        prefix = random.choice(prefixes.get(industry, ["通用"]))
        suffix = suffixes.get(industry, "公司")
        
        return f"{prefix}{suffix}"
    
    def _generate_departments(
        self,
        total_headcount: int,
        profile: IndustryProfile,
        global_approval: float,
        global_meeting: float,
        global_satisfaction: float
    ) -> List[Dict]:
        """生成部门数据"""
        departments = []
        dept_id = 0
        
        for dept_type, ratio in profile.dept_distribution.items():
            dept_headcount = max(3, int(total_headcount * ratio * random.uniform(0.8, 1.2)))
            
            # 部门级参数（在全局基础上波动）
            dept_approval = max(1, int(global_approval * random.uniform(0.7, 1.3)))
            dept_meeting = global_meeting * random.uniform(0.5, 1.5)
            dept_satisfaction = global_satisfaction * random.uniform(0.8, 1.2)
            
            # 项目交付周期（与部门类型相关）
            lead_time_base = {
                "RND": 45, "PRODUCT": 30, "OPERATIONS": 14,
                "SALES": 21, "STRATEGY": 60, "ADMIN": 7
            }.get(dept_type, 30)
            
            dept_lead_time = lead_time_base * random.uniform(0.8, 1.5)
            
            departments.append({
                "dept_id": f"D{dept_id:03d}",
                "dept_name": self._get_dept_name(dept_type),
                "dept_type": dept_type,
                "headcount": dept_headcount,
                "approval_layers": dept_approval,
                "meeting_hours_weekly": round(dept_meeting, 1),
                "project_lead_time": round(dept_lead_time, 1),
                "employee_satisfaction": round(min(10, max(1, dept_satisfaction)), 1)
            })
            
            dept_id += 1
        
        return departments
    
    def _get_dept_name(self, dept_type: str) -> str:
        """获取部门中文名称"""
        names = {
            "RND": "研发中心",
            "PRODUCT": "产品部",
            "OPERATIONS": "运营中心",
            "SALES": "销售部",
            "STRATEGY": "战略部",
            "ADMIN": "行政支撑"
        }
        return names.get(dept_type, dept_type)
    
    def export_dataset(self, dataset: Dict, filepath: str):
        """导出数据集为JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        return filepath


# 便捷函数
def generate_tech_startup(stress: float = 0.0) -> Dict:
    """生成科技初创公司数据"""
    gen = VirtualDataGenerator()
    return gen.generate_organization(IndustryTemplate.TECH_STARTUP, stress_level=stress)


def generate_declining_series(industry: IndustryTemplate = IndustryTemplate.TECH_ENTERPRISE) -> List[Dict]:
    """生成衰退趋势系列数据"""
    gen = VirtualDataGenerator(seed=42)
    return gen.generate_historical_series(
        industry=industry,
        org_name="示例科技集团",
        months=12,
        trend="declining",
        start_stress=0.1,
        end_stress=0.8
    )


if __name__ == "__main__":
    # 演示
    print("=" * 70)
    print("MSS Virtual Data Generator Demo")
    print("=" * 70)
    
    gen = VirtualDataGenerator(seed=42)
    
    # 1. 生成正常科技初创
    print("\n1. 正常科技初创:")
    org1 = gen.generate_organization(IndustryTemplate.TECH_STARTUP, stress_level=0.2)
    print(f"   {org1['org_name']}: {org1['headcount']}人, 压力={org1['stress_level']}")
    
    # 2. 生成高压力金融公司
    print("\n2. 高压力金融公司:")
    org2 = gen.generate_organization(IndustryTemplate.FINANCE, stress_level=0.8)
    print(f"   {org2['org_name']}: {org2['headcount']}人, 压力={org2['stress_level']}")
    
    # 3. 生成异常场景
    print("\n3. 官僚爆炸场景（政府机构）:")
    org3 = gen.generate_organization(
        IndustryTemplate.GOVERNMENT,
        stress_level=0.5,
        anomaly_type="bureaucratic_explosion"
    )
    print(f"   {org3['org_name']}: {org3['headcount']}人, 异常={org3['anomaly_type']}")
    
    # 4. 生成历史趋势
    print("\n4. 12月衰退趋势:")
    series = gen.generate_historical_series(
        IndustryTemplate.TECH_STARTUP,
        org_name="红移科技",
        months=12,
        trend="declining",
        start_stress=0.1,
        end_stress=0.7
    )
    for org in series[::3]:  # 每3月显示
        print(f"   {org['snapshot_date'][:7]}: 压力={org['stress_level']:.2f}")
    
    # 5. 导出基准数据集
    print("\n5. 导出跨行业基准数据集...")
    dataset = gen.generate_benchmark_dataset(samples_per_industry=2)
    total_orgs = sum(len(orgs) for orgs in dataset.values())
    print(f"   生成 {total_orgs} 个组织样本，覆盖 {len(dataset)} 个行业")
    
    gen.export_dataset(dataset, "virtual_benchmark_dataset.json")
    print("   已保存至: virtual_benchmark_dataset.json")
