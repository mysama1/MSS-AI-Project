"""
MSS Symbolic Engine v3.0 演示脚本
展示传递推理、环检测、MSS v12.2公理体系和热税监测
"""

from symbolic_engine_v3 import create_mss_v12_engine, HeatTaxMonitor

# 创建引擎
e = create_mss_v12_engine()
print("=" * 60)
print("MSS Symbolic Engine v3.0 演示")
print("=" * 60)
print(f"\n引擎初始化完成: {len(e.graph.nodes)} 节点, {len(e.graph.edges)} 边")
print(f"L1公理: {list(e.axiom_system.axioms.keys())}")
print(f"L2定理: {list(e.axiom_system.theorems.keys())}")

# 演示1: 传递推理
print("\n" + "=" * 60)
print("演示1: 传递推理")
print("=" * 60)

for premise, conclusion in [("A1", "T1"), ("A1", "T2"), ("A1", "T3"), ("A2", "T3")]:
    result = e.reason(premise, conclusion)
    print(f"\n{premise} → {conclusion}:")
    print(f"  结果: {result.result.name}")
    print(f"  确定性: {result.certainty:.0%}")
    print(f"  解释: {result.explanation}")
    if result.steps:
        print(f"  推理步骤: {len(result.steps)} 步")

# 演示2: 热税监测
print("\n" + "=" * 60)
print("演示2: 系统健康监测 (K3降维热寂机制)")
print("=" * 60)

scenarios = [
    ("健康系统", 0.3, 90.0),
    ("预警系统", 0.7, 60.0),
    ("热寂临界", 0.85, 15.0),
]

for name, O_d, phi in scenarios:
    health = e.monitor_system_health(O_d=O_d, phi=phi)
    print(f"\n--- {name} (O_d={O_d}, Φ={phi}) ---")
    print(f"状态: {health['status']}")
    trend = health['report']['trend']
    risk = trend.get('risk_level', 'N/A')
    print(f"风险等级: {risk}")
    
    if health['report']['alerts']:
        print("告警:")
        for alert in health['report']['alerts']:
            print(f"  [{alert['level']}] {alert['message']}")
            print(f"    建议: {alert['action']}")
    else:
        print("告警: 无")
    
    print("建议:")
    for rec in health['report']['recommendations']:
        print(f"  - {rec}")

# 演示3: 导出公理体系
print("\n" + "=" * 60)
print("演示3: 导出MSS v12.2公理体系")
print("=" * 60)

output_file = "mss_v12_axioms.json"
e.export_axiom_system(output_file)
print(f"\n公理体系已导出到: {output_file}")

import json
with open(output_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"导出内容:")
print(f"  - 基础公理: {len(data['axioms'])} 条")
print(f"  - 导出定理: {len(data['theorems'])} 条")
print(f"  - 核心机制: {len(data['mechanisms'])} 条")

print("\n" + "=" * 60)
print("演示完成")
print("=" * 60)
