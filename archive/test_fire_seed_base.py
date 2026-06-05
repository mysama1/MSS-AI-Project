"""D5-018 火种基地蓝图 测试套件"""
import sys, os
sys.path.insert(0, r'C:\MSS-AI-Project')

from fire_seed_base_blueprint import (
    BaseScale, SiteRequirements, EnergySystem, CommunicationSystem,
    MaterialReserve, GovernanceProtocol, SecurityProtocol,
    FireSeedProfile, FireSeedBase, CostModel,
    create_minimal_ember_base, create_flame_base
)


def test_site_scoring():
    """选址评分系统"""
    # 理想选址
    ideal = SiteRequirements(
        min_area_hectares=10, min_water_source_l_per_day=20000,
        solar_irradiance_kwh_m2_day=5.5, max_population_density_radius_50km=10,
        seismic_zone="低", flood_risk="低", soil_quality="可耕种",
        temperature_range_c=(0, 30), political_stability="稳定",
        legal_land_tenure="使用权>50年"
    )
    assert ideal.score() > 0.85, f"Ideal site score too low: {ideal.score()}"

    # 困难选址
    bad = SiteRequirements(
        min_area_hectares=2, min_water_source_l_per_day=1000,
        solar_irradiance_kwh_m2_day=2.5, max_population_density_radius_50km=200,
        seismic_zone="高", flood_risk="高", soil_quality="贫瘠",
        temperature_range_c=(-20, 45), political_stability="动荡",
        legal_land_tenure="短期租赁"
    )
    assert bad.score() < 0.4, f"Bad site score too high: {bad.score()}"
    print("  PASS test_site_scoring")


def test_energy_calculations():
    """能源系统计算"""
    e = EnergySystem(solar_pv_kw=20, solar_battery_kwh=40, wind_turbine_kw=3)

    # 日均发电量应约为: 20*4.5*0.8 + 3*24*0.25 = 72 + 18 = 90 kWh
    daily = e.daily_generation_kwh()
    assert 80 < daily < 100, f"Unexpected daily generation: {daily}"

    # 10人用50kWh/天，40kWh储能 = 0.8天
    autonomy = e.autonomy_days(50)
    assert 0.7 < autonomy < 0.9, f"Unexpected autonomy: {autonomy}"

    # 能源韧性 > 0 (多源)
    assert e.resilience_score() > 0.3, f"Low resilience: {e.resilience_score()}"
    print("  PASS test_energy_calculations")


def test_material_autonomy():
    """物资储备自持"""
    m = MaterialReserve(
        population=10, target_autonomy_days=365,
        food_stockpile_kg=5475, water_storage_liters=50000,
        water_purification_l_per_day=200,
        medical_supply_kits=5, seed_varieties=30,
        tool_kits=5, spare_parts_inventory_items=50
    )

    assert 350 < m.food_autonomy_days() < 370, f"Food autonomy: {m.food_autonomy_days()}"
    assert 350 < m.water_autonomy_days() < 400, f"Water autonomy: {m.water_autonomy_days()}"
    assert m.overall_autonomy_score() > 0.85, f"Overall autonomy: {m.overall_autonomy_score()}"
    print("  PASS test_material_autonomy")


def test_fire_seed_profile():
    """火种成员测评"""
    elite = FireSeedProfile(
        t_value=0.92, logic_maturity=0.88, paradigm_breakthrough=0.85,
        heat_tax_tolerance=0.90, primary_skill="符号引擎架构",
        secondary_skills=["农业", "急救"], group_compatibility=0.85,
        teaching_ability=0.90
    )
    assert elite.composite_score() > 0.85, f"Elite score: {elite.composite_score()}"
    assert elite.is_qualified(0.7)

    borderline = FireSeedProfile(
        t_value=0.55, logic_maturity=0.50, paradigm_breakthrough=0.30,
        heat_tax_tolerance=0.40, primary_skill="木工",
        group_compatibility=0.6, teaching_ability=0.5
    )
    assert borderline.composite_score() < 0.7
    assert not borderline.is_qualified(0.7)
    print("  PASS test_fire_seed_profile")


def test_governance_protocol():
    """治理协议完整性"""
    gp = GovernanceProtocol()
    assert len(gp.principles) == 6
    assert len(gp.roles) == 5
    assert "锚定者(Anchor)" in gp.roles
    assert "审计者(Auditor)" in gp.roles
    assert "退出权" in gp.principles[3]
    assert gp.decision_heat_tax["基地搬迁"] > 0.7  # 最高热税决策
    print("  PASS test_governance_protocol")


def test_security_score():
    """安全协议评分"""
    sec = SecurityProtocol()
    assert sec.security_score() > 0.8, f"Security score: {sec.security_score()}"
    assert len(sec.emergency_protocols) == 4
    assert "L2_通信中断" in sec.emergency_protocols
    print("  PASS test_security_score")


def test_ember_base_creation():
    """EMBER基地模板创建"""
    ember = create_minimal_ember_base()
    assert ember.scale == BaseScale.EMBER
    assert ember.population == 10
    assert ember.name == "号-E-001"

    # 就绪度评估
    readiness = ember.overall_readiness()
    assert "site" in readiness
    assert "energy" in readiness
    assert readiness["overall"] > 0.3, f"Too low: {readiness['overall']}"
    assert readiness["overall"] < 0.85, f"Too high (unrealistic): {readiness['overall']}"

    # 缺口分析
    gaps = ember.gap_analysis()
    # 应该有能源和成员缺口
    gap_texts = " ".join(gaps)
    assert "能源" in gap_texts or "成员" in gap_texts, f"No expected gaps: {gaps}"

    # 部署计划
    plan = ember.phased_deployment_plan()
    assert len(plan) == 4
    assert plan[0]["name"].startswith("勘察")
    assert plan[-1]["name"].startswith("扩展")

    # 报告生成
    report = ember.summary_report()
    assert "号-E-001" in report
    assert "火种成员" in report

    print("  PASS test_ember_base_creation")


def test_flame_base_creation():
    """FLAME基地模板"""
    flame = create_flame_base()
    assert flame.scale == BaseScale.FLAME
    assert flame.population == 50

    readiness = flame.overall_readiness()
    assert readiness["materials"] > 0.9  # 物资最充裕

    print("  PASS test_flame_base_creation")


def test_cost_model():
    """成本估算"""
    cm = CostModel()
    ember = create_minimal_ember_base()
    costs = cm.estimate_total(ember, "偏远农地")

    assert "land" in costs
    assert "total_initial" in costs
    assert 300_000 < costs["total_initial"] < 600_000, f"Cost out of range: {costs['total_initial']}"
    assert costs["infrastructure"] > costs["land"]

    # FLAME 应该是 EMBER 的 3-4 倍
    flame = create_flame_base()
    flame_costs = cm.estimate_total(flame, "偏远农地")
    ratio = flame_costs["total_initial"] / costs["total_initial"]
    assert 2.5 < ratio < 5.0, f"FLAME/EMBER ratio: {ratio:.1f}"

    print("  PASS test_cost_model")


def test_communication_offline():
    """通信离线能力"""
    comm = CommunicationSystem()
    score = comm.offline_capability_score()
    assert score > 0.7, f"Offline score too low: {score}"

    # 无Mesh无HAM = 低离线能力
    bad_comm = CommunicationSystem(
        mesh_network=False, ham_radio=False,
        offline_data_repository_tb=0.1, local_server=False
    )
    assert bad_comm.offline_capability_score() < 0.2
    print("  PASS test_communication_offline")


def test_readiness_grade():
    """就绪等级评定"""
    ember = create_minimal_ember_base()
    grade = ember.readiness_grade()
    assert grade.startswith("C"), f"Expected C grade, got: {grade}"
    print("  PASS test_readiness_grade")


if __name__ == "__main__":
    print("D5-018 火种基地蓝图 测试套件\n")
    tests = [
        test_site_scoring, test_energy_calculations, test_material_autonomy,
        test_fire_seed_profile, test_governance_protocol, test_security_score,
        test_ember_base_creation, test_flame_base_creation, test_cost_model,
        test_communication_offline, test_readiness_grade,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"  {passed}/{len(tests)} ALL PASS")
    print(f"{'='*50}")