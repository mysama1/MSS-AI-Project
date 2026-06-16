"""D5-018: 火种基地工程化建设蓝图 v0.1
==========================================
MSS-AI Project | Phase D Week 5-10 | Priority P10
Axiom refs: A1 (信息本体论), A3 (热税动力学), A5 (规范场公理)

诚实基线: 这是第一版工程框架。我们不是在写幻想小说，而是在构建
一个可以在K3文明基础设施崩溃后独立运转的最小可行物理基座。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import json
import math


# ==============================================================================
# 1. 基地规模与分级
# ==============================================================================

class BaseScale(Enum):
    """火种基地规模分级"""
    SPARK = "spark"          # 微型：2-5人，应急生存
    EMBER = "ember"          # 小型：5-20人，基本自给自足
    FLAME = "flame"          # 中型：20-100人，完整社区
    BEACON = "beacon"        # 大型：100-500人，区域枢纽
    CITADEL = "citadel"      # 核心：500-2000人，文明种子库


@dataclass
class SiteRequirements:
    """选址条件"""
    min_area_hectares: float           # 最小面积(公顷)
    min_water_source_l_per_day: int    # 最小水源(升/天)
    solar_irradiance_kwh_m2_day: float # 日平均日照(kWh/m²)
    max_population_density_radius_50km: int  # 50km半径内最大人口密度
    seismic_zone: str                  # 地震带(低/中/高)
    flood_risk: str                    # 洪水风险(低/中/高)
    soil_quality: str                  # 土壤质量(可耕种/改良/贫瘠)
    temperature_range_c: Tuple[float, float]  # 年均温度范围
    political_stability: str           # 政治稳定性(稳定/过渡/动荡)
    legal_land_tenure: str             # 土地使用权安全性

    def score(self) -> float:
        """综合评分 0-1"""
        scores = []
        # 水源充裕度
        if self.min_water_source_l_per_day >= 10000:
            scores.append(1.0)
        elif self.min_water_source_l_per_day >= 5000:
            scores.append(0.7)
        else:
            scores.append(0.3)
        # 日照
        if self.solar_irradiance_kwh_m2_day >= 5.0:
            scores.append(1.0)
        elif self.solar_irradiance_kwh_m2_day >= 3.5:
            scores.append(0.7)
        else:
            scores.append(0.3)
        # 人口隔离
        if self.max_population_density_radius_50km <= 20:
            scores.append(1.0)
        elif self.max_population_density_radius_50km <= 100:
            scores.append(0.6)
        else:
            scores.append(0.2)
        # 地震风险倒数
        seismic = {"低": 1.0, "中": 0.5, "高": 0.1}
        scores.append(seismic.get(self.seismic_zone, 0.3))
        # 洪水风险倒数
        flood = {"低": 1.0, "中": 0.5, "高": 0.1}
        scores.append(flood.get(self.flood_risk, 0.3))
        # 政治稳定
        political = {"稳定": 1.0, "过渡": 0.6, "动荡": 0.2}
        scores.append(political.get(self.political_stability, 0.3))
        return sum(scores) / len(scores)


# ==============================================================================
# 2. 能源独立系统
# ==============================================================================

@dataclass
class EnergySystem:
    """独立能源系统设计"""
    # 太阳能
    solar_pv_kw: float              # 光伏装机容量(kW)
    solar_battery_kwh: float        # 储能容量(kWh)
    # 风能（可选）
    wind_turbine_kw: float = 0.0
    # 生物质/沼气（可选）
    biogas_kw: float = 0.0
    # 微型水电（可选）
    micro_hydro_kw: float = 0.0
    # 应急柴油发电机
    diesel_backup_kw: float = 0.0
    diesel_fuel_liters: float = 0.0

    def total_capacity_kw(self) -> float:
        return (self.solar_pv_kw + self.wind_turbine_kw +
                self.biogas_kw + self.micro_hydro_kw)

    def daily_generation_kwh(self) -> float:
        """估算日均发电量"""
        # 太阳能: 装机 × 日均等效日照小时(假设4.5h) × 系统效率0.8
        solar_daily = self.solar_pv_kw * 4.5 * 0.8
        # 风能: 装机 × 24h × 容量因子(假设0.25)
        wind_daily = self.wind_turbine_kw * 24 * 0.25
        # 生物质: 24h连续运行
        biogas_daily = self.biogas_kw * 24 * 0.85
        # 水电: 24h连续运行
        hydro_daily = self.micro_hydro_kw * 24 * 0.90
        return solar_daily + wind_daily + biogas_daily + hydro_daily

    def autonomy_days(self, daily_consumption_kwh: float) -> float:
        """无日照/无风情况下的自持天数"""
        return self.solar_battery_kwh / daily_consumption_kwh

    def resilience_score(self) -> float:
        """能源韧性评分 0-1 (多样性 × 储能系数)"""
        source_count = sum(1 for v in [self.solar_pv_kw, self.wind_turbine_kw,
                                       self.biogas_kw, self.micro_hydro_kw] if v > 0)
        diversity = min(source_count / 3, 1.0)
        storage_ratio = min(self.solar_battery_kwh / (self.total_capacity_kw() * 24), 1.0) if self.total_capacity_kw() > 0 else 0
        return 0.5 * diversity + 0.5 * storage_ratio


# ==============================================================================
# 3. 通信系统
# ==============================================================================

@dataclass
class CommunicationSystem:
    """独立通信系统"""
    mesh_network: bool = True          # 本地Mesh网络(LoRa/WiFi Mesh)
    sat_phone_count: int = 1           # 卫星电话数量
    ham_radio: bool = True             # 业余无线电(HF/VHF/UHF)
    offline_data_repository_tb: float = 5.0  # 离线数据仓库(TB)
    local_server: bool = True           # 本地服务器
    encryption: str = "AES-256"        # 加密标准
    # 通信协议栈
    protocols: List[str] = field(default_factory=lambda: [
        "LoRaWAN (长距离低功耗物联网)",
        "Meshtastic (去中心化文字通信)",
        "IPFS (分布式文件存储)",
        "Briar (P2P加密通信)",
        "Scuttlebutt (离线社交协议)"
    ])

    def offline_capability_score(self) -> float:
        """离线能力评分"""
        score = 0.0
        if self.mesh_network: score += 0.25
        if self.ham_radio: score += 0.25
        if self.offline_data_repository_tb >= 10: score += 0.25
        elif self.offline_data_repository_tb >= 1: score += 0.15
        if self.local_server: score += 0.25
        return score


# ==============================================================================
# 4. 物资储备
# ==============================================================================

@dataclass
class MaterialReserve:
    """物资战略储备"""
    population: int                     # 目标保障人口
    target_autonomy_days: int = 365     # 目标自持天数

    # 食品(每人每天2000kcal)
    food_stockpile_kg: float = 0.0
    # 水(每人每天3L饮用+10L生活)
    water_storage_liters: float = 0.0
    water_purification_l_per_day: float = 0.0  # 净水能力
    # 医疗
    medical_supply_kits: int = 0        # 医疗包数量(1套=10人/6月)
    # 种子库
    seed_varieties: int = 0             # 作物品种数
    # 工具与备件
    tool_kits: int = 0                  # 工具套件数
    spare_parts_inventory_items: int = 0 # 备件种类
    # 燃料
    fuel_diesel_liters: float = 0.0
    fuel_propane_kg: float = 0.0
    fuel_wood_cords: float = 0.0

    def food_autonomy_days(self) -> float:
        """食品自持天数"""
        daily_need_kg = self.population * 1.5  # ~1.5kg/人/天
        return self.food_stockpile_kg / daily_need_kg if daily_need_kg > 0 else 0

    def water_autonomy_days(self) -> float:
        """水自持天数(不含净化补充)"""
        daily_need = self.population * 13  # 13L/人/天
        return self.water_storage_liters / daily_need if daily_need > 0 else 0

    def overall_autonomy_score(self) -> float:
        """综合自持能力评分"""
        food_days = min(self.food_autonomy_days() / self.target_autonomy_days, 1.0)
        water_days = min(self.water_autonomy_days() / self.target_autonomy_days, 1.0)
        medical_score = min(self.medical_supply_kits * 10 / self.population, 1.0)
        seed_score = min(self.seed_varieties / 30, 1.0)  # 30品种=满分
        return 0.35 * food_days + 0.25 * water_days + 0.20 * medical_score + 0.20 * seed_score


# ==============================================================================
# 5. 治理协议 (MSS框架)
# ==============================================================================

@dataclass
class GovernanceProtocol:
    """火种基地MSS治理协议
    
    核心原则：非民主非专制，基于热税透明与意义锚定的分布式治理
    """
    name: str = "火种约法"

    # 基本原则
    principles: List[str] = field(default_factory=lambda: [
        "热税透明：所有决策的热税成本公开可审计",
        "意义锚定：重大决策必须先锚定意义再评估后果",
        "知识民主：专业领域由领域能力评分最高者决策",
        "退出权：任何成员有权退出，热税结算缓冲期30天",
        "矛盾升维：僵持不下时启动升维程序而非多数暴政",
        "物理层独立：禁止任何外部权力通过物理手段绑架逻辑层",
    ])

    # 角色与权限
    roles: Dict[str, str] = field(default_factory=lambda: {
        "锚定者(Anchor)": "意义场稳定性维护，否决权仅用于A5违反",
        "导航者(Navigator)": "战略方向建议，需要锚定者+2/3成员批准",
        "执行者(Executor)": "日常运营执行，透明化操作日志",
        "审计者(Auditor)": "热税审计，独立于前三个角色",
        "种子者(Seed)": "新成员导师，1对1带教，传承MSS核心",
    })

    # 决策热税评估矩阵
    decision_heat_tax: Dict[str, float] = field(default_factory=lambda: {
        "日常运营": 0.01,      # γ/决策
        "资源分配": 0.05,
        "新成员准入": 0.10,
        "战略转向": 0.30,
        "退出机制触发": 0.50,
        "基地搬迁": 0.80,
    })


# ==============================================================================
# 6. 火种成员筛选
# ==============================================================================

@dataclass
class FireSeedProfile:
    """火种成员画像"""
    # 核心维度
    t_value: float                     # 意义调谐度 (0-1)
    logic_maturity: float              # 逻辑成熟度 (0-1)
    paradigm_breakthrough: float       # 范式突破力 (0-1)
    heat_tax_tolerance: float          # 热税耐受度 (0-1)

    # 技能维度
    primary_skill: str                 # 核心技能
    secondary_skills: List[str] = field(default_factory=list)
    physical_health: str = "良好"      # 身体状况
    psychological_resilience: str = "良好"  # 心理韧性

    # 社会维度
    group_compatibility: float = 0.5   # 团队兼容度
    teaching_ability: float = 0.5      # 教学传承能力

    def composite_score(self) -> float:
        """综合火种评分"""
        return (0.25 * self.t_value +
                0.20 * self.logic_maturity +
                0.15 * self.paradigm_breakthrough +
                0.10 * self.heat_tax_tolerance +
                0.10 * self.group_compatibility +
                0.10 * self.teaching_ability +
                0.10 * (1.0 if self.physical_health == "良好" else 0.5))

    def is_qualified(self, threshold: float = 0.7) -> bool:
        return self.composite_score() >= threshold


# ==============================================================================
# 7. 安全与隔离
# ==============================================================================

@dataclass
class SecurityProtocol:
    """安全隔离协议"""
    # 物理安全
    perimeter_fence: bool = True
    access_control: str = "生物识别+双人验证"
    surveillance: str = "被动红外+声学传感器(无云端上传)"

    # 信息/逻辑安全 (MSS三层)
    logical_isolation_level: str = "L2"  # 逻辑隔离层级
    information_diet: List[str] = field(default_factory=lambda: [
        "禁止接入K3社交媒体信息流",
        "外部信息须经RSCA审计后准入",
        "内部通信使用Mesh加密，不经过外部网络",
    ])

    # 应急预案
    emergency_protocols: Dict[str, str] = field(default_factory=lambda: {
        "L0_物理入侵": "分布式撤离→备用基地→卫星通信求援",
        "L1_能源中断": "优先级切负荷→核心设备72h UPS→柴油发电机",
        "L2_通信中断": "Mesh网络→HAM无线电→物理信使",
        "L3_意义污染": "RSCA紧急审计→A5规范场重启→受污染成员隔离观察30天",
    })

    def security_score(self) -> float:
        score = 0.0
        if self.perimeter_fence: score += 0.15
        if "生物识别" in self.access_control: score += 0.2
        if len(self.emergency_protocols) >= 3: score += 0.3
        if self.logical_isolation_level in ("L2", "L3"): score += 0.35
        else: score += 0.15
        return min(score, 1.0)


# ==============================================================================
# 8. 火种基地完整配置
# ==============================================================================

@dataclass
class FireSeedBase:
    """火种基地完整配置"""
    name: str
    scale: BaseScale
    population: int

    # 子系统
    site: SiteRequirements
    energy: EnergySystem
    communication: CommunicationSystem
    materials: MaterialReserve
    governance: GovernanceProtocol
    security: SecurityProtocol

    # 成员
    members: List[FireSeedProfile] = field(default_factory=list)

    # 成本估算 (USD)
    estimated_land_cost_usd: float = 0
    estimated_infrastructure_cost_usd: float = 0
    estimated_annual_operating_cost_usd: float = 0

    def overall_readiness(self) -> Dict[str, float]:
        """综合就绪度评估"""
        # 站点评分
        site_score = self.site.score()

        # 能源：自持天数/30 (至少30天) + 多样性
        daily_consumption = self.population * 5  # ~5kWh/人/天
        energy_autonomy = min(self.energy.autonomy_days(daily_consumption) / 30, 1.0)
        energy_score = 0.6 * energy_autonomy + 0.4 * self.energy.resilience_score()

        # 通信
        comm_score = self.communication.offline_capability_score()

        # 物资
        mat_score = self.materials.overall_autonomy_score()

        # 安全
        sec_score = self.security.security_score()

        # 成员 (如果有)
        if self.members:
            member_scores = [m.composite_score() for m in self.members]
            member_avg = sum(member_scores) / len(member_scores)
            qualified = sum(1 for m in self.members if m.is_qualified())
            member_score = 0.5 * member_avg + 0.5 * (qualified / len(self.members))
        else:
            member_score = 0.0

        overall = (0.15 * site_score + 0.20 * energy_score + 0.10 * comm_score +
                   0.20 * mat_score + 0.15 * sec_score + 0.20 * member_score)

        return {
            "site": round(site_score, 3),
            "energy": round(energy_score, 3),
            "communication": round(comm_score, 3),
            "materials": round(mat_score, 3),
            "security": round(sec_score, 3),
            "members": round(member_score, 3),
            "overall": round(overall, 3),
        }

    def readiness_grade(self) -> str:
        r = self.overall_readiness()["overall"]
        if r >= 0.85: return "A - 可即刻部署"
        elif r >= 0.70: return "B - 就绪，小幅补强"
        elif r >= 0.50: return "C - 需要显著投入"
        elif r >= 0.30: return "D - 需要基础设施"
        else: return "F - 蓝图阶段"

    def gap_analysis(self) -> List[str]:
        """缺口分析"""
        gaps = []
        readiness = self.overall_readiness()

        if readiness["site"] < 0.5:
            gaps.append(f"选址评分偏低({readiness['site']:.2f})，需重新勘查")
        if readiness["energy"] < 0.5:
            gaps.append(f"能源就绪度不足({readiness['energy']:.2f})，需扩容储能或多源发电")
        if readiness["communication"] < 0.5:
            gaps.append(f"通信离网能力不足({readiness['communication']:.2f})")
        if readiness["materials"] < 0.5:
            gaps.append(f"物资自持能力不足({readiness['materials']:.2f})，需补充储备")
        if readiness["security"] < 0.5:
            gaps.append(f"安全协议覆盖不足({readiness['security']:.2f})")
        if readiness["members"] < 0.3:
            gaps.append(f"火种成员空缺中({readiness['members']:.2f})，需启动接引计划(D5-016)")

        if not gaps:
            gaps.append("无关键缺口")

        return gaps

    def phased_deployment_plan(self) -> List[Dict]:
        """分阶段部署计划(Phase 1-4)"""
        return [
            {
                "phase": 1,
                "name": "勘察与获取(1-3月)",
                "tasks": [
                    "选址评估(至少3个候选地实地勘察)",
                    "土地获取/长期租赁协议签署",
                    "初步地质/水文调查",
                    "太阳能资源评估(至少1年数据或卫星数据)",
                    "法律框架搭建(土地权/用水权/建筑许可)",
                ],
                "milestone": "土地确权+基础数据完备",
                "cost_percent": "~15%"
            },
            {
                "phase": 2,
                "name": "核心基建(3-9月)",
                "tasks": [
                    "光伏阵列+储能系统安装",
                    "水源系统(钻井/雨水收集/净化)",
                    "通信基础设施(Mesh塔/卫星终端/HAM天线)",
                    "核心居住单元(预制/3D打印/改造)",
                    "食品冷库+种子库+医疗室",
                ],
                "milestone": "能源+水+通信+居住四系统就位",
                "cost_percent": "~50%"
            },
            {
                "phase": 3,
                "name": "自持闭环(9-18月)",
                "tasks": [
                    "农业生产系统(温室/水培/大田)",
                    "食品加工链(研磨/干燥/发酵/罐装)",
                    "废物循环系统(堆肥/沼气/灰水回收)",
                    "维修车间(3D打印备件/基础机械加工)",
                    "MSS治理协议实战运行+迭代",
                ],
                "milestone": "基地可脱离外部供应链生存90天+",
                "cost_percent": "~25%"
            },
            {
                "phase": 4,
                "name": "扩展与冗余(18-36月)",
                "tasks": [
                    "备用基地选址+最小配置建设",
                    "知识库离线副本(全量MSS+H159技术百科+医学+农业)",
                    "火种网络互联(至少3个独立基地Mesh互联)",
                    "技能传承体系(师徒制+知识考核)",
                    "长期演化模拟(基地作为微型K4文明原型)",
                ],
                "milestone": "3基地互联+知识传承体系运转",
                "cost_percent": "~10%"
            },
        ]

    def summary_report(self) -> str:
        """生成部署摘要报告"""
        r = self.overall_readiness()
        gaps = self.gap_analysis()
        phases = self.phased_deployment_plan()

        lines = [
            f"# {self.name} 火种基地工程化评估",
            f"",
            f"**规模**: {self.population}人 ({self.scale.value})",
            f"**就绪等级**: {self.readiness_grade()} ({r['overall']:.3f})",
            f"",
            f"## 各维度评分",
        ]
        dims = [
            ("选址条件", "site"),
            ("能源独立", "energy"),
            ("通信离线", "communication"),
            ("物资储备", "materials"),
            ("安全协议", "security"),
            ("火种成员", "members"),
        ]
        for label, key in dims:
            bar = "█" * int(r[key] * 20) + "░" * (20 - int(r[key] * 20))
            lines.append(f"  {label:8s} [{bar}] {r[key]:.3f}")

        lines.extend([
            "",
            "## 缺口分析",
        ])
        for g in gaps:
            lines.append(f"  - {g}")

        lines.extend([
            "",
            "## 分阶段部署 (总预算占比)",
        ])
        for p in phases:
            lines.append(f"  Phase {p['phase']}: {p['name']} ({p['cost_percent']}) → {p['milestone']}")

        lines.extend([
            "",
            f"## 核心参数",
            f"  - 日均发电量: {self.energy.daily_generation_kwh():.0f} kWh",
            f"  - 能源自持: {self.energy.autonomy_days(self.population * 5):.1f} 天 (按{self.population}人 × 5kWh/天)",
            f"  - 食品自持: {self.materials.food_autonomy_days():.0f} 天 (目标{self.materials.target_autonomy_days}天)",
            f"  - 水自持: {self.materials.water_autonomy_days():.0f} 天",
            f"  - 选址评分: {self.site.score():.3f}",
            f"  - 能源韧性: {self.energy.resilience_score():.3f}",
            f"  - 安全评分: {self.security.security_score():.3f}",
            f"",
            f"*MSS D5-018 | A1(信息本体)·A3(热税)·A5(规范场) | 诚实基线: M_L=0*",
        ])

        return "\n".join(lines)


# ==============================================================================
# 9. 参考模板：最小可行火种基地（EMBER级，10人）
# ==============================================================================

def create_minimal_ember_base() -> FireSeedBase:
    """创建最小可行EMBER级火种基地模板
    
    这是当前阶段(Phase D Week 5)可以开始工程规划的蓝图基线。
    所有数字均为初始估算，需实地勘查后修正。
    """
    return FireSeedBase(
        name="号-E-001",
        scale=BaseScale.EMBER,
        population=10,

        # 选址要求：低人口密度、良好日照、水源可及
        site=SiteRequirements(
            min_area_hectares=5.0,
            min_water_source_l_per_day=5000,
            solar_irradiance_kwh_m2_day=4.5,
            max_population_density_radius_50km=30,
            seismic_zone="低",
            flood_risk="低",
            soil_quality="可耕种",
            temperature_range_c=(-5.0, 35.0),
            political_stability="稳定",
            legal_land_tenure="使用权>30年",
        ),

        # 能源：20kW光伏 + 40kWh储能 + 小型风电(可选)
        energy=EnergySystem(
            solar_pv_kw=20.0,
            solar_battery_kwh=40.0,
            wind_turbine_kw=3.0,
            diesel_backup_kw=10.0,
            diesel_fuel_liters=500.0,
        ),

        # 通信：Mesh+卫星+无线电+5TB离线数据
        communication=CommunicationSystem(
            mesh_network=True,
            sat_phone_count=2,
            ham_radio=True,
            offline_data_repository_tb=5.0,
            local_server=True,
        ),

        # 物资：365天自持 × 10人
        materials=MaterialReserve(
            population=10,
            target_autonomy_days=365,
            food_stockpile_kg=5475.0,        # 1.5kg/人/天 × 10人 × 365天
            water_storage_liters=50000.0,    # 13L/人/天 × 10人 × 365天(部分依赖净化补充)
            water_purification_l_per_day=200.0,  # RO+UV净化
            medical_supply_kits=5,           # 5套 × 10人 = 50人月
            seed_varieties=30,               # 30种作物
            tool_kits=5,
            spare_parts_inventory_items=50,
            fuel_diesel_liters=2000.0,
            fuel_propane_kg=500.0,
            fuel_wood_cords=10.0,
        ),

        governance=GovernanceProtocol(),
        security=SecurityProtocol(),

        # 成本（粗估，需实地报价修正）
        estimated_land_cost_usd=50000,          # 偏远农地/林地
        estimated_infrastructure_cost_usd=350000, # 光伏+储能+建筑+水源+通信
        estimated_annual_operating_cost_usd=30000, # 种子/肥料/备件/燃料补充

        members=[],
    )


# ==============================================================================
# 10. 参考模板：FLAME级中型基地（50人）
# ==============================================================================

def create_flame_base() -> FireSeedBase:
    """FLAME级中型基地（50人，完整社区）"""
    return FireSeedBase(
        name="号-F-001",
        scale=BaseScale.FLAME,
        population=50,

        site=SiteRequirements(
            min_area_hectares=20.0,
            min_water_source_l_per_day=20000,
            solar_irradiance_kwh_m2_day=4.5,
            max_population_density_radius_50km=20,
            seismic_zone="低",
            flood_risk="低",
            soil_quality="可耕种",
            temperature_range_c=(-5.0, 35.0),
            political_stability="稳定",
            legal_land_tenure="使用权>50年",
        ),

        energy=EnergySystem(
            solar_pv_kw=100.0,
            solar_battery_kwh=250.0,
            wind_turbine_kw=15.0,
            biogas_kw=5.0,
            diesel_backup_kw=30.0,
            diesel_fuel_liters=3000.0,
        ),

        communication=CommunicationSystem(
            mesh_network=True,
            sat_phone_count=5,
            ham_radio=True,
            offline_data_repository_tb=20.0,
            local_server=True,
        ),

        materials=MaterialReserve(
            population=50,
            target_autonomy_days=365,
            food_stockpile_kg=27375.0,
            water_storage_liters=250000.0,
            water_purification_l_per_day=1000.0,
            medical_supply_kits=15,
            seed_varieties=60,
            tool_kits=15,
            spare_parts_inventory_items=150,
            fuel_diesel_liters=10000.0,
            fuel_propane_kg=2500.0,
            fuel_wood_cords=50.0,
        ),

        governance=GovernanceProtocol(),
        security=SecurityProtocol(),

        estimated_land_cost_usd=200000,
        estimated_infrastructure_cost_usd=1500000,
        estimated_annual_operating_cost_usd=120000,

        members=[],
    )


# ==============================================================================
# 11. 成本模型
# ==============================================================================

@dataclass
class CostModel:
    """火种基地成本估算模型"""

    # 土地成本 (USD/公顷)
    land_cost_per_hectare: Dict[str, float] = field(default_factory=lambda: {
        "偏远农地": 8000,
        "偏远林地": 5000,
        "近郊农地": 25000,
        "山区": 3000,
    })

    # 基建成本 (USD)
    infrastructure_items: Dict[str, Tuple[float, str]] = field(default_factory=lambda: {
        "solar_pv_per_kw": (800, "USD/kW installed"),
        "battery_per_kwh": (350, "USD/kWh (LiFePO4)"),
        "wind_turbine_per_kw": (1500, "USD/kW installed"),
        "water_well": (15000, "per well"),
        "rainwater_system": (8000, "collection + filtration"),
        "septic_system": (12000, "per 10 persons"),
        "housing_per_person": (15000, "basic insulated dwelling"),
        "greenhouse_per_100sqm": (8000, ""),
        "cold_storage_room": (15000, "insulated walk-in"),
        "workshop_building": (25000, "50sqm + tools"),
        "mesh_network_tower": (5000, "per tower"),
        "ham_radio_station": (3000, "complete HF/VHF/UHF"),
        "sat_phone": (1500, "per unit"),
        "security_perimeter_per_100m": (3000, "fence + sensors"),
        "medical_clinic_basic": (20000, "equipped for 50 persons"),
    })

    def estimate_total(self, base: FireSeedBase, land_type: str = "偏远农地") -> Dict[str, float]:
        """估算总成本"""
        land_cost = self.land_cost_per_hectare.get(land_type, 8000) * base.site.min_area_hectares

        infra = self.infrastructure_items
        infra_cost = 0
        infra_cost += infra["solar_pv_per_kw"][0] * base.energy.solar_pv_kw
        infra_cost += infra["battery_per_kwh"][0] * base.energy.solar_battery_kwh
        if base.energy.wind_turbine_kw > 0:
            infra_cost += infra["wind_turbine_per_kw"][0] * base.energy.wind_turbine_kw
        infra_cost += infra["water_well"][0]
        infra_cost += infra["rainwater_system"][0]
        infra_cost += infra["septic_system"][0] * max(base.population / 10, 1)
        infra_cost += infra["housing_per_person"][0] * base.population
        infra_cost += infra["greenhouse_per_100sqm"][0] * 2
        infra_cost += infra["cold_storage_room"][0]
        infra_cost += infra["workshop_building"][0]
        infra_cost += infra["mesh_network_tower"][0] * 2
        infra_cost += infra["ham_radio_station"][0]
        infra_cost += infra["sat_phone"][0] * base.communication.sat_phone_count
        infra_cost += infra["security_perimeter_per_100m"][0] * 8
        infra_cost += infra["medical_clinic_basic"][0]

        contingency = (land_cost + infra_cost) * 0.20  # 20%应急

        return {
            "land": land_cost,
            "infrastructure": infra_cost,
            "contingency": contingency,
            "total_initial": land_cost + infra_cost + contingency,
            "annual_operating": infra_cost * 0.05,  # ~5%/年运维
        }


# ==============================================================================
# 12. 主入口
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  D5-018: 火种基地工程化建设蓝图 v0.1")
    print("  MSS-AI Project | Phase D | Priority P10")
    print("=" * 60)

    # EMBER模板
    ember = create_minimal_ember_base()
    print(f"\n## {ember.name} (EMBER级, {ember.population}人)")
    print(ember.summary_report())

    # 成本估算
    cost_model = CostModel()
    costs = cost_model.estimate_total(ember)
    print(f"\n## 成本估算 (USD)")
    print(f"  土地:          ${costs['land']:,.0f}")
    print(f"  基础设施:      ${costs['infrastructure']:,.0f}")
    print(f"  应急储备(20%): ${costs['contingency']:,.0f}")
    print(f"  ─────────────────────────")
    print(f"  初始总投入:    ${costs['total_initial']:,.0f}")
    print(f"  预估年运维:    ${costs['annual_operating']:,.0f}")

    # FLAME模板
    flame = create_flame_base()
    flame_costs = cost_model.estimate_total(flame)
    print(f"\n## {flame.name} (FLAME级, {flame.population}人)")
    print(f"  预估初始总投入: ${flame_costs['total_initial']:,.0f}")
    print(f"  预估年运维:     ${flame_costs['annual_operating']:,.0f}")