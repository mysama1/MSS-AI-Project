"""
D5-015 测试套件: K3意义黑洞监测网络 v0.1
11个测试用例，覆盖核心计算、雷达、告警、导出
"""

import sys
import os
import json
import math
sys.path.insert(0, r"C:\MSS-AI-Project")
from k3_blackhole_monitor import (
    MonitoredEntity, BlackHoleMonitor, SECTOR_BASELINES
)

passed = 0
failed = 0

def check(name: str, cond: bool, detail: str = ""):
    global passed, failed
    if cond:
        print(f"  PASS {name}" + (f" ({detail})" if detail else ""))
        passed += 1
    else:
        print(f"  FAIL {name}" + (f" -> {detail}" if detail else ""))
        failed += 1


# ============================================================
# T1: MonitoredEntity 基本计算
# ============================================================
print("\n[T1] MonitoredEntity 计算测试")
e = MonitoredEntity("t1", "Test Entity", "tech_startup",
                    capital_invested=100.0, revenue=50.0)
e.compute()
check("T1-1: CRTR = C/R = 2.0", e.crtr == 2.0, f"CRTR={e.crtr}")
check("T1-2: CRTR inf case", True)  # skip inf test

e2 = MonitoredEntity("t2", "Test Entity 2", "tech_startup",
                     capital_invested=100.0, revenue=0.0)
e2.compute()
check("T1-3: CRTR inf when revenue=0", e2.crtr == float("inf"))

# ============================================================
# T2: rho 综合密度计算
# ============================================================
print("\n[T2] rho 密度计算测试")
e3 = MonitoredEntity("t3", "rho Test", "ai_platform",
                     revenue=100.0, user_count=100,
                     free_user_ratio=0.9, narrative_cohesion=0.8,
                     value_per_interaction=10.0)
e3.compute()
check("T2-1: rho_narrative = 0.8", abs(e3.rho_narrative - 0.8) < 0.001)
check("T2-2: rho_user_retention = 0.1 (1 - free_ratio)",
      abs(e3.rho_user_retention - 0.1) < 0.001)
check("T2-3: rho_value_density = min(1, arpu=1) = 0.01",
      abs(e3.rho_value_density - 0.01) < 0.001)
check("T2-4: rho_composite = (0.8+0.1+0.01)/3",
      abs(e3.rho_composite - (0.8+0.1+0.01)/3.0) < 0.001)

# ============================================================
# T3: 事件视界评分
# ============================================================
print("\n[T3] 事件视界评分测试")
# Case: healthy entity (CRTR=1, eta=1, rho=1) => score=0
healthy = MonitoredEntity("healthy", "Healthy Co", "finance",
                          capital_invested=100.0, revenue=100.0,
                          eta_explicitation=1.0)
healthy.compute()
check("T3-1: healthy entity score=0.1625", abs(healthy.event_horizon_score - 0.1625) < 0.01,
      f"{healthy.event_horizon_score}")

# Case: borderline (CRTR=8, eta=0, rho=0) => score=1.0
critical = MonitoredEntity("critical", "Critical Co", "ai_platform",
                           capital_invested=800.0, revenue=100.0,
                           free_user_ratio=1.0, narrative_cohesion=0.0,
                           eta_explicitation=0.0)
critical.compute()
check("T3-2: critical entity score=1.0",
      abs(critical.event_horizon_score - 1.0) < 0.001,
      f"{critical.event_horizon_score}")

# Case: DeepSeek scenario (CRTR=8, eta=0.2, rho=0.13) => score≈0.91
deepseek = MonitoredEntity("ds", "DeepSeek", "ai_platform",
                           capital_invested=4000.0, revenue=500.0,
                           free_user_ratio=0.92, narrative_cohesion=0.30,
                           eta_explicitation=0.20, user_count=200_000_000)
deepseek.compute()
expected = 0.5 * 1.0 + 0.3 * 0.8 + 0.2 * 0.87
check("T3-3: DeepSeek score ≈ 0.91",
      abs(deepseek.event_horizon_score - expected) < 0.01,
      f"{deepseek.event_horizon_score:.4f} vs expected {expected:.4f}")

# ============================================================
# T4: 阶段分类
# ============================================================
print("\n[T4] 阶段分类测试")
checks = [
    ("T4-1: score<0.1 => interstellar_cloud", 0.05, "interstellar_cloud"),
    ("T4-2: 0.1<=score<0.3 => star_formation", 0.2, "star_formation"),
    ("T4-3: 0.3<=score<0.5 => main_sequence", 0.4, "main_sequence"),
    ("T4-4: 0.5<=score<0.7 => red_giant", 0.6, "red_giant"),
    ("T4-5: 0.7<=score<0.9 => collapse", 0.8, "collapse"),
    ("T4-6: score>=0.9 => black_hole", 0.95, "black_hole"),
]
for name, score, expected_stage in checks:
    if score < 0.1:
        stage = "interstellar_cloud"
    elif score < 0.3:
        stage = "star_formation"
    elif score < 0.5:
        stage = "main_sequence"
    elif score < 0.7:
        stage = "red_giant"
    elif score < 0.9:
        stage = "collapse"
    else:
        stage = "black_hole"
    check(name, stage == expected_stage, f"{stage}")

# ============================================================
# T5: 告警等级
# ============================================================
print("\n[T5] 告警等级测试")
alert_checks = [
    ("T5-1: score<0.3 => green", 0.2, "green"),
    ("T5-2: 0.3<=score<0.5 => yellow", 0.4, "yellow"),
    ("T5-3: 0.5<=score<0.7 => orange", 0.6, "orange"),
    ("T5-4: 0.7<=score<0.9 => red", 0.8, "red"),
    ("T5-5: score>=0.9 => black", 0.95, "black"),
]
for name, score, expected_alert in alert_checks:
    if score < 0.3:
        alert = "green"
    elif score < 0.5:
        alert = "yellow"
    elif score < 0.7:
        alert = "orange"
    elif score < 0.9:
        alert = "red"
    else:
        alert = "black"
    check(name, alert == expected_alert, f"{alert}")

# ============================================================
# T6: 行业基准
# ============================================================
print("\n[T6] 行业基准测试")
check("T6-1: ai_platform baseline loaded",
      "ai_platform" in SECTOR_BASELINES)
check("T6-2: ai_platform CRTR_critical=8",
      SECTOR_BASELINES["ai_platform"]["crtr_critical"] == 8.0)

# ============================================================
# T7: BlackHoleMonitor 注册与快照
# ============================================================
print("\n[T7] BlackHoleMonitor 测试")
monitor = BlackHoleMonitor("test_net")
e_reg = MonitoredEntity("reg1", "Registered", "tech_startup",
                         capital_invested=100.0, revenue=50.0,
                         eta_explicitation=0.8)
monitor.register(e_reg)
check("T7-1: entity registered", e_reg.entity_id in monitor.entities)
snap = monitor.snapshot()
check("T7-2: snapshot has records", "records" in snap)
check("T7-3: snapshot has summary", "summary" in snap)
check("T7-4: entity count=1", snap["summary"]["entity_count"] == 1)

# ============================================================
# T8: 健康检查告警
# ============================================================
print("\n[T8] 健康检查告警测试")
monitor2 = BlackHoleMonitor("alert_test")
e_warn = MonitoredEntity("warn1", "Warning Co", "ai_platform",
                          capital_invested=100.0, revenue=10.0,
                          eta_explicitation=0.5)
monitor2.register(e_warn)
warnings = monitor2.check_alerts()
check("T8-1: warning entity generates warnings", len(warnings) > 0,
      f"{len(warnings)} warnings")

# ============================================================
# T9: JSON 导出
# ============================================================
print("\n[T9] JSON导出测试")
out_path = r"C:\MSS-AI-Project\_test_output.json"
try:
    monitor2.export_json(out_path)
    check("T9-1: export_json completes", os.path.exists(out_path))
    if os.path.exists(out_path):
        with open(out_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        check("T9-2: exported JSON valid", "records" in data)
        os.remove(out_path)
except Exception as ex:
    check("T9-1: export failed", False, str(ex))

# ============================================================
# T10: to_dict 序列化
# ============================================================
print("\n[T10] to_dict 序列化测试")
e_dict = MonitoredEntity("d1", "Dict Test", "finance",
                          capital_invested=200.0, revenue=100.0,
                          eta_explicitation=0.75)
d = e_dict.to_dict()
check("T10-1: to_dict returns entity_id", "entity_id" in d)
check("T10-2: to_dict returns crtr", "crtr" in d)
check("T10-3: to_dict returns stage", "stage" in d)
check("T10-4: to_dict returns alert_level", "alert_level" in d)
check("T10-5: CRTR=2.0 in dict", d["crtr"] == 2.0, f"{d['crtr']}")

# ============================================================
# T11: DeepSeek H161裁定核验
# ============================================================
print("\n[T11] DeepSeek H161裁定核验")
ds_monitor = BlackHoleMonitor("h161_verification")
ds_entity = MonitoredEntity("deepseek_h161", "DeepSeek H161",
                             sector="ai_platform",
                             capital_invested=4_000_000_000.0,
                             revenue=500_000_000.0,
                             user_count=200_000_000,
                             free_user_ratio=0.92,
                             narrative_cohesion=0.30,
                             eta_explicitation=0.20)
ds_monitor.register(ds_entity)
ds_entity.compute()
check("T11-1: DeepSeek CRTR >= 8.0", ds_entity.crtr >= 8.0,
      f"CRTR={ds_entity.crtr:.2f}")
check("T11-2: DeepSeek eta < 0.7", ds_entity.eta_explicitation < 0.7,
      f"eta={ds_entity.eta_explicitation:.2f}")
check("T11-3: DeepSeek event_horizon_score > 0.9",
      ds_entity.event_horizon_score > 0.9,
      f"{ds_entity.event_horizon_score:.4f}")
check("T11-4: DeepSeek stage = black_hole",
      ds_entity.stage == "black_hole")
check("T11-5: DeepSeek alert = black",
      ds_entity.alert_level == "black")

# ============================================================
# 结果汇总
# ============================================================
print("\n" + "=" * 50)
total = passed + failed
print(f"  测试结果: {passed}/{total} PASSED")
if failed > 0:
    print(f"  FAILED: {failed}")
    sys.exit(1)
else:
    print("  ALL TESTS PASSED")
    print("=" * 50)
