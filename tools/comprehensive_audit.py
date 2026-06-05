"""
MSS-AI 项目全面审计
=====================
实事求是：任务栏进度 vs 实际交付物

规则：
- 文件存在且 > 1KB = 有实质内容
- 文件存在但 < 1KB = 占位符/空文件
- 测试通过 = 可验证
- 测试失败/无测试 = 不可验证
"""

import os, json, glob

ROOT = r"C:\MSS-AI-Project"

# ============================================================
# 任务栏 vs 实际文件系统
# ============================================================

TASK_FILE_MAP = {
    "D1-001": [  # 符号引擎v4.0
        "symbolic_engine.py", "symbolic_engine_v2.py", "symbolic_engine_v3.py",
        "symbolic_engine_v4/core.py", "symbolic_engine_v4/api.py",
    ],
    "D1-002": [  # API接口
        "mss_agent_sdk/client.py", "mss_agent_sdk/__init__.py",
    ],
    "D1-003": [  # CSR图优化
        "symbolic_engine_v4/core.py", "symbolic_engine_v4/test_core.py",
    ],
    "D1-004": [  # 监控体系
        "mss_stability.py", "system_status.py", "test_stability.py", "test_system_status.py",
    ],
    "D2-001": [  # 韧性扫描器SaaS
        "resilience_visualizer.py", "resilience_scanner_web.py",
    ],
    "D2-002": [  # 合规扫描器API
        "compliance_scanner.py", "compliance_scanner_enhanced.py",
    ],
    "D3-001": [  # GRAV-EXP-001
        "GRAV-EXP-001_proposal.md", "empirical_validation.py",
    ],
    "D3-003": [  # 暗物质/暗能量验证
        "empirical_validation.py",
    ],
    "D5-001": [  # MSS-Agent SDK v0.1
        "mss_agent_sdk/__init__.py", "mss_agent_sdk/client.py",
        "mss_agent_sdk/test_sdk.py", "dist/",
    ],
    "D5-004": [  # K4协议族
        "k4_protocols/k4_rsca_genes.py", "k4_protocols/k4_guardian_protocol.py",
        "k4_protocols/k4_bidirectional_coupler.py", "k4_protocols/k4_logical_work.py",
        "k4_protocols/test_k4_protocols.py",
    ],
    "D5-005": [  # 逻辑疫苗引擎
        "k4_immune/logical_vaccine_engine.py", "k4_immune/test_logical_vaccine.py",
    ],
    "D5-006": [  # 双壳设计
        # 尚未创建
    ],
    "D5-002": [  # 显化思考UI
        # 尚未创建
    ],
    "D5-003": [  # 认知快照协议
        # 尚未创建
    ],
}

def check_file(fp):
    """返回 (exists, size_kb, has_content)"""
    if os.path.isfile(fp):
        sz = os.path.getsize(fp)
        return True, sz/1024, sz > 1024
    elif os.path.isdir(fp):
        files = glob.glob(os.path.join(fp, "**/*.py"), recursive=True)
        total = sum(os.path.getsize(f) for f in files)
        return True, total/1024, total > 1024
    return False, 0, False

print("="*60)
print("任务栏进度 vs 实际交付物审计")
print("="*60)
print()

results = []
for tid, files in TASK_FILE_MAP.items():
    found = []
    missing = []
    total_kb = 0
    for f in files:
        fp = os.path.join(ROOT, f)
        exists, kb, has = check_file(fp)
        total_kb += kb if exists else 0
        if exists:
            found.append(f"{f}({kb:.1f}KB)")
        else:
            missing.append(f)
    
    status = "✅" if (found and not missing) else ("⚠️" if found else "❌")
    results.append({
        "id": tid,
        "status": status,
        "found": len(found),
        "missing": len(missing),
        "total_kb": total_kb,
    })
    print(f"{status} {tid}: {len(found)}/{len(files)} files, {total_kb:.1f}KB")
    for ff in found:
        print(f"    ✅ {ff}")
    for mf in missing:
        print(f"    ❌ {mf}")

print()
print("="*60)
print("诚实基线校准")
print("="*60)

# 测试套件实际运行结果
print()
print("实际可运行测试（pytest/unittest）:")
test_dirs = [
    os.path.join(ROOT, "k4_protocols"),
    os.path.join(ROOT, "k4_immune"),
    os.path.join(ROOT, "mss_agent_sdk"),
    os.path.join(ROOT, "symbolic_engine_v4"),
]
for td in test_dirs:
    if os.path.isdir(td):
        test_files = glob.glob(os.path.join(td, "test_*.py"))
        for tf in test_files:
            # Quick syntax check
            try:
                with open(tf, 'r', encoding='utf-8') as f:
                    compile(f.read(), tf, 'exec')
                print(f"  ✅ {os.path.basename(td)}/{os.path.basename(tf)} (syntax OK)")
            except Exception as e:
                print(f"  ❌ {os.path.basename(td)}/{os.path.basename(tf)}: {e}")

print()
print("="*60)
print("phantom任务检测")
print("="*60)
print()
print("以下任务在任务栏中有进度，但无实质交付物：")
phantom = [r for r in results if r["total_kb"] < 10 and r["missing"] > 0]
for p in phantom:
    print(f"  ⚠️ {p['id']}: {p['found']} files found, {p['total_kb']:.1f}KB total")
if not phantom:
    print("  (无phantom任务)")

print()
print("="*60)
print("校准后的任务栏建议")
print("="*60)
print()
print("建议修正（基于实际交付物）：")
for r in results:
    # Suggest calibrated progress
    if r["total_kb"] > 50 and r["missing"] == 0:
        suggested = "80-100%"
    elif r["total_kb"] > 10:
        suggested = "40-70%"
    elif r["found"] > 0:
        suggested = "10-30%"
    else:
        suggested = "0%"
    print(f"  {r['id']}: {suggested} ({r['total_kb']:.1f}KB, {r['found']}/{r['found']+r['missing']} files)")
