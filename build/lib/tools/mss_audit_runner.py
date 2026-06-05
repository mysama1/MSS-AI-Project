#!/usr/bin/env python3
"""
MSS意义审计系统命令行工具
协议编号：MSS-AUDIT-CLI-001
"""
import argparse
import sys
import importlib.util as _u
spec = _u.spec_from_file_location('mss_meaning_audit_v02', __file__.rsplit('\\', 1)[0] + '\\mss_meaning_audit_v02.py')
_m = _u.module_from_spec(spec)
spec.loader.exec_module(_m)
from sys import modules
modules['mss_meaning_audit_v02'] = _m
MSSMeaningAuditor = _m.MSSMeaningAuditor
CrossFileMeaningChecker = _m.CrossFileMeaningChecker
DynamicThermalTaxProfiler = _m.DynamicThermalTaxProfiler
def main():
    parser = argparse.ArgumentParser(description="MSS意义审计系统")
    parser.add_argument("--file", "-f", help="审计单个文件")
    parser.add_argument("--project", "-p", help="审计整个项目")
    parser.add_argument("--test", "-t", action="store_true", help="运行测试审计")
    parser.add_argument("--output", "-o", help="输出JSON报告到指定文件")
    args = parser.parse_args()
    auditor = MSSMeaningAuditor()
    cross_checker = CrossFileMeaningChecker(auditor)
    if args.test:
        print("🔍 运行测试审计...")
        test_code = """
@meaning_contract(
    input_meaning="总热税支付Q、热税系数γ",
    output_meaning="有效逻辑功W",
    side_effects=["无"]
)
def calculate_logical_work(Q: float, gamma: float) -> float:
    if gamma <= 0:
        raise ValueError("热税系数γ必须大于0")
    return Q / gamma
"""
        report = auditor.audit_code(test_code, "test.py")
        print(f"✅ 测试审计通过，总评分：{round(report.total_score, 2)}/100")
        return
    if args.file:
        print(f"🔍 审计文件：{args.file}")
        report = auditor.audit_file(args.file)
    elif args.project:
        print(f"🔍 审计项目：{args.project}")
        report = cross_checker.audit_project(args.project)
    else:
        print("❌ 请指定要审计的文件或项目")
        sys.exit(1)
    # 打印报告摘要
    print("\n📊 审计结果摘要")
    print("="*50)
    print(f"总评分：{round(report.total_score, 2)}/100")
    print(f"逻辑刚性：{round(report.logical_rigidity, 2)}/100")
    print(f"热税指数：{round(report.thermal_tax_index, 2)}/100")
    print(f"意义保真度：{round(report.meaning_fidelity, 2)}/100")
    print(f"发现问题总数：{len(report.issues)}")
    p0_count = len([i for i in report.issues if i.level.value == "P0"])
    p1_count = len([i for i in report.issues if i.level.value == "P1"])
    print(f"P0级问题：{p0_count}")
    print(f"P1级问题：{p1_count}")
    # 输出JSON报告
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report.to_json())
        print(f"\n✅ JSON报告已保存至：{args.output}")
    # 检查是否通过
    if report.total_score < 70 or p0_count > 0:
        print("\n❌ 审计失败")
        sys.exit(1)
    else:
        print("\n✅ 审计通过")
        sys.exit(0)
if __name__ == "__main__":
    main()