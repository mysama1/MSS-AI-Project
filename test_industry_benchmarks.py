"""
Tests for industry_benchmarks.py
"""

import unittest
from industry_benchmarks import (
    IndustryBenchmark, INDUSTRY_BENCHMARKS,
    get_benchmark, list_industries, compare_to_benchmark
)

class TestIndustryBenchmarks(unittest.TestCase):

    def test_all_benchmarks_have_required_fields(self):
        """所有行业基准都有必需字段"""
        for code, benchmark in INDUSTRY_BENCHMARKS.items():
            self.assertIsNotNone(benchmark.industry_name)
            self.assertIsNotNone(benchmark.industry_code)
            self.assertEqual(code, benchmark.industry_code.lower())
            self.assertIn("O_d_target", benchmark.resilience_benchmark)
            self.assertIn("phi_target", benchmark.resilience_benchmark)
            self.assertIn("gamma_target", benchmark.resilience_benchmark)
            self.assertIn("R_target", benchmark.resilience_benchmark)
            self.assertIn("M_target", benchmark.resilience_benchmark)

    def test_get_benchmark(self):
        """获取指定行业基准"""
        benchmark = get_benchmark("tech_startup")
        self.assertIsNotNone(benchmark)
        self.assertEqual(benchmark.industry_name, "科技初创公司")

        # 不存在的行业
        self.assertIsNone(get_benchmark("nonexistent"))

    def test_list_industries(self):
        """列出所有行业"""
        industries = list_industries()
        self.assertEqual(len(industries), 8)
        self.assertIn("tech_startup", industries)
        self.assertIn("government", industries)

    def test_compare_to_benchmark_better(self):
        """对比：优于基准"""
        org = {
            "O_d": 0.20,  # 低于目标0.25（更好）
            "phi": 130.0,  # 高于目标120（更好）
            "gamma": 0.15,  # 低于目标0.20（更好）
            "R": 0.80,  # 高于目标0.70（更好）
            "M": 0.85,  # 高于目标0.75（更好）
        }
        result = compare_to_benchmark(org, "tech_startup")
        self.assertEqual(result["industry"], "科技初创公司")
        self.assertIn("优于行业基准", result["overall_assessment"])
        self.assertEqual(len(result["recommendations"]), 0)  # 没有落后项

    def test_compare_to_benchmark_worse(self):
        """对比：低于基准"""
        org = {
            "O_d": 0.60,
            "phi": 50.0,
            "gamma": 0.50,
            "R": 0.10,
            "M": 0.10,
        }
        result = compare_to_benchmark(org, "tech_startup")
        self.assertIn("低于行业基准", result["overall_assessment"])
        self.assertGreater(len(result["recommendations"]), 0)

    def test_compare_to_benchmark_equal(self):
        """对比：持平基准"""
        benchmark = get_benchmark("tech_startup")
        org = {
            "O_d": benchmark.resilience_benchmark["O_d_target"],
            "phi": benchmark.resilience_benchmark["phi_target"],
            "gamma": benchmark.resilience_benchmark["gamma_target"],
            "R": benchmark.resilience_benchmark["R_target"],
            "M": benchmark.resilience_benchmark["M_target"],
        }
        result = compare_to_benchmark(org, "tech_startup")
        self.assertIn("持平", result["overall_assessment"])

    def test_compare_unknown_industry(self):
        """对比：未知行业"""
        result = compare_to_benchmark({"O_d": 0.5}, "unknown")
        self.assertIn("error", result)

    def test_industry_characteristics(self):
        """行业特征标签"""
        benchmark = get_benchmark("tech_startup")
        self.assertIn("扁平化", benchmark.characteristics)
        self.assertIn("创新导向", benchmark.characteristics)

        benchmark = get_benchmark("government")
        self.assertIn("稳定优先", benchmark.characteristics)
        self.assertIn("变革缓慢", benchmark.characteristics)

    def test_risk_factors(self):
        """风险因素"""
        benchmark = get_benchmark("finance")
        self.assertIn("监管变化", benchmark.risk_factors)
        self.assertIn("系统性风险", benchmark.risk_factors)

if __name__ == "__main__":
    unittest.main(verbosity=2)
