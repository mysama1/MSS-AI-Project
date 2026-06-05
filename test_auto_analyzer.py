#!/usr/bin/env python3
"""
自动化分析器测试
"""

import unittest
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_analyzer import MSSAutoAnalyzer

class TestMSSAutoAnalyzer(unittest.TestCase):
    """测试自动化分析器"""

    def setUp(self):
        """设置测试环境"""
        self.analyzer = MSSAutoAnalyzer()

    def test_analyze_knowledge_base(self):
        """测试知识库分析"""
        result = self.analyzer.analyze_knowledge_base()

        # 验证基本结构
        self.assertIn('total_entries', result)
        self.assertIn('target', result)
        self.assertIn('progress_pct', result)
        self.assertIn('layer_counts', result)
        self.assertIn('recent_files', result)

        # 验证数值合理性
        self.assertGreaterEqual(result['total_entries'], 0)
        self.assertEqual(result['target'], 500)
        self.assertGreaterEqual(result['progress_pct'], 0)
        self.assertLessEqual(result['progress_pct'], 100)

        # 验证层级分布
        layers = result['layer_counts']
        self.assertIn('L1', layers)
        self.assertIn('L2', layers)
        self.assertIn('L3', layers)
        self.assertIn('L4', layers)

        # 验证总数匹配
        total_layers = sum(layers.values())
        self.assertEqual(total_layers, result['total_entries'])

        print(f"✓ 知识库分析通过: {result['total_entries']}/500 ({result['progress_pct']}%)")

    def test_analyze_code_health(self):
        """测试代码健康度分析"""
        result = self.analyzer.analyze_code_health()

        # 验证基本结构
        self.assertIn('total_python_files', result)
        self.assertIn('total_lines', result)
        self.assertIn('test_files', result)
        self.assertIn('largest_files', result)

        # 验证数值合理性
        self.assertGreaterEqual(result['total_python_files'], 0)
        self.assertGreaterEqual(result['total_lines'], 0)
        self.assertGreaterEqual(result['test_files'], 0)

        # 验证文件列表
        self.assertIsInstance(result['largest_files'], list)
        if result['largest_files']:
            self.assertIn('name', result['largest_files'][0])
            self.assertIn('lines', result['largest_files'][0])

        print(f"✓ 代码健康度分析通过: {result['total_python_files']} 文件, {result['total_lines']} 行")

    def test_generate_decision_matrix(self):
        """测试决策矩阵生成"""
        kb = self.analyzer.analyze_knowledge_base()
        code = self.analyzer.analyze_code_health()
        result = self.analyzer.generate_decision_matrix(kb, code)

        # 验证基本结构
        self.assertIn('current_phase', result)
        self.assertIn('progress_pct', result)
        self.assertIn('decisions', result)
        self.assertIn('recommendation', result)

        # 验证决策列表
        self.assertIsInstance(result['decisions'], list)
        if result['decisions']:
            decision = result['decisions'][0]
            self.assertIn('phase', decision)
            self.assertIn('task', decision)
            self.assertIn('priority', decision)
            self.assertIn('action', decision)

        # 验证建议非空
        self.assertIsInstance(result['recommendation'], str)
        self.assertGreater(len(result['recommendation']), 0)

        print(f"✓ 决策矩阵生成通过: {len(result['decisions'])} 个决策")

    def test_generate_report(self):
        """测试报告生成"""
        report = self.analyzer.generate_report()

        # 验证报告非空
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 100)

        # 验证关键内容存在
        self.assertIn('MSS-AI 自动化分析报告', report)
        self.assertIn('知识库状态', report)
        self.assertIn('代码健康度', report)
        self.assertIn('决策矩阵', report)
        self.assertIn('综合建议', report)

        print(f"✓ 报告生成通过: {len(report)} 字符")

    def test_save_report(self):
        """测试报告保存"""
        report = self.analyzer.generate_report()
        filepath = self.analyzer.save_report(report)

        # 验证文件存在
        self.assertTrue(os.path.exists(filepath))

        # 验证文件内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, report)

        # 清理测试文件
        os.remove(filepath)

        print(f"✓ 报告保存通过: {filepath}")

    def test_run_health_check(self):
        """测试健康检查"""
        result = self.analyzer.run_health_check()

        # 验证基本结构
        self.assertIn('status', result)
        self.assertIn('issues', result)
        self.assertIn('warnings', result)
        self.assertIn('kb', result)
        self.assertIn('code', result)

        # 验证状态值
        self.assertIn(result['status'], ['HEALTHY', 'WARNING', 'CRITICAL'])

        # 验证列表类型
        self.assertIsInstance(result['issues'], list)
        self.assertIsInstance(result['warnings'], list)

        print(f"✓ 健康检查通过: 状态={result['status']}, 问题={len(result['issues'])}, 警告={len(result['warnings'])}")

    def test_layer_balance(self):
        """测试层级平衡性"""
        kb = self.analyzer.analyze_knowledge_base()
        layers = kb['layer_counts']
        total = kb['total_entries']

        if total > 0:
            l1_ratio = layers['L1'] / total
            l2_ratio = layers['L2'] / total
            l3_ratio = layers['L3'] / total

            # L1 应该占总数的 10-20%
            self.assertGreaterEqual(l1_ratio, 0.05, f"L1比例过低: {l1_ratio:.1%}")
            self.assertLessEqual(l1_ratio, 0.25, f"L1比例过高: {l1_ratio:.1%}")

            # L2 应该最多
            self.assertGreaterEqual(l2_ratio, l1_ratio, "L2应该多于L1")

            print(f"✓ 层级平衡通过: L1={l1_ratio:.1%}, L2={l2_ratio:.1%}, L3={l3_ratio:.1%}")

    def test_recent_files_sorted(self):
        """测试最近文件排序"""
        kb = self.analyzer.analyze_knowledge_base()
        recent = kb['recent_files']

        if len(recent) > 1:
            # 验证按时间倒序
            for i in range(len(recent) - 1):
                self.assertGreaterEqual(
                    recent[i]['mtime'],
                    recent[i+1]['mtime'],
                    "最近文件应该按时间倒序"
                )

        print(f"✓ 文件排序通过: {len(recent)} 个最近文件")

class TestAutoAnalyzerIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        analyzer = MSSAutoAnalyzer()

        # 1. 健康检查
        health = analyzer.run_health_check()
        self.assertIn(health['status'], ['HEALTHY', 'WARNING'])

        # 2. 生成报告
        report = analyzer.generate_report()
        self.assertGreater(len(report), 100)

        # 3. 保存报告
        filepath = analyzer.save_report(report)
        self.assertTrue(os.path.exists(filepath))

        # 4. 验证报告内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('MSS-AI', content)

        # 清理
        os.remove(filepath)

        print("✓ 完整工作流测试通过")

if __name__ == '__main__':
    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试
    suite.addTests(loader.loadTestsFromTestCase(TestMSSAutoAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoAnalyzerIntegration))

    # 运行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"总测试数: {result.testsRun}")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    # 返回退出码
    sys.exit(0 if result.wasSuccessful() else 1)
