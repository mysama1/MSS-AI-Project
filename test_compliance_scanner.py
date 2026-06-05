"""
Tests for Compliance Scanner
"""

import unittest
import os
import tempfile
from compliance_scanner import ComplianceScanner, ComplianceScore, ScanResult

class TestComplianceScanner(unittest.TestCase):

    def setUp(self):
        self.scanner = ComplianceScanner()

    def test_scan_valid_file(self):
        """测试扫描有效文件"""
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write("# Test file\n")
            f.write("def hello():\n")
            f.write("    print('Hello')\n")
            temp_path = f.name

        try:
            result = self.scanner.scan_file(temp_path)

            self.assertEqual(result.file_path, temp_path)
            self.assertGreater(result.line_count, 0)
            self.assertGreater(result.file_size, 0)
            self.assertIsNotNone(result.score)

        finally:
            os.remove(temp_path)

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        result = self.scanner.scan_file("nonexistent_file.py")

        self.assertEqual(result.score.grade, "ERROR")
        self.assertEqual(result.file_size, 0)

    def test_grade_calculation(self):
        """测试等级计算"""
        self.assertEqual(self.scanner._grade_from_score(0.9), "A")
        self.assertEqual(self.scanner._grade_from_score(0.75), "B")
        self.assertEqual(self.scanner._grade_from_score(0.6), "C")
        self.assertEqual(self.scanner._grade_from_score(0.3), "D")

    def test_grade_badge(self):
        """测试等级徽章"""
        self.assertIn("🟢", self.scanner._grade_badge("A"))
        self.assertIn("🔴", self.scanner._grade_badge("D"))

    def test_scorecard_empty(self):
        """测试空结果评分卡"""
        scorecard = self.scanner.generate_scorecard([])
        self.assertIn("error", scorecard)

    def test_scorecard_with_results(self):
        """测试有结果的评分卡"""
        # 创建模拟结果
        results = [
            ScanResult(
                file_path="test1.py",
                file_size=100,
                line_count=10,
                score=ComplianceScore(
                    cleanliness=0.8,
                    layer_adherence=0.7,
                    rsca_score=0.9,
                    overclaim=0.2,
                    overall=0.75,
                    grade="B"
                )
            ),
            ScanResult(
                file_path="test2.py",
                file_size=200,
                line_count=20,
                score=ComplianceScore(
                    cleanliness=0.6,
                    layer_adherence=0.5,
                    rsca_score=0.4,
                    overclaim=0.8,
                    overall=0.45,
                    grade="D"
                )
            )
        ]

        scorecard = self.scanner.generate_scorecard(results)

        self.assertEqual(scorecard['summary']['total_files'], 2)
        self.assertIn('dimension_scores', scorecard)
        self.assertIn('grade_distribution', scorecard)

    def test_markdown_report(self):
        """测试Markdown报告生成"""
        results = [
            ScanResult(
                file_path="test.py",
                file_size=100,
                line_count=10,
                score=ComplianceScore(
                    cleanliness=0.8,
                    layer_adherence=0.7,
                    rsca_score=0.9,
                    overclaim=0.2,
                    overall=0.75,
                    grade="B"
                )
            )
        ]

        report = self.scanner.generate_markdown_report(results)

        self.assertIn("MSS文本合规扫描报告", report)
        self.assertIn("test.py", report)
        self.assertIn("0.75", report)

    def test_markdown_report_export(self):
        """测试Markdown报告导出"""
        results = [
            ScanResult(
                file_path="test.py",
                file_size=100,
                line_count=10,
                score=ComplianceScore(overall=0.8, grade="A")
            )
        ]

        test_path = "test_compliance_report.md"
        result = self.scanner.generate_markdown_report(results, test_path)

        self.assertEqual(result, test_path)
        self.assertTrue(os.path.exists(test_path))

        # 清理
        os.remove(test_path)

    def test_directory_scan(self):
        """测试目录扫描"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            for i in range(3):
                with open(os.path.join(tmpdir, f"test{i}.py"), 'w') as f:
                    f.write(f"# Test file {i}\n")

            # 创建非Python文件
            with open(os.path.join(tmpdir, "readme.md"), 'w') as f:
                f.write("# README\n")

            results = self.scanner.scan_directory(tmpdir, pattern="*.py", recursive=False)

            self.assertEqual(len(results), 3)
            for r in results:
                self.assertTrue(r.file_path.endswith('.py'))

    def test_progress_callback(self):
        """测试进度回调"""
        progress_calls = []

        def callback(current, total):
            progress_calls.append((current, total))

        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                with open(os.path.join(tmpdir, f"test{i}.py"), 'w') as f:
                    f.write("# Test\n")

            self.scanner.scan_directory(tmpdir, pattern="*.py", progress_callback=callback)

            self.assertEqual(len(progress_calls), 3)
            self.assertEqual(progress_calls[-1], (3, 3))

class TestComplianceScore(unittest.TestCase):

    def test_default_values(self):
        """测试默认值"""
        score = ComplianceScore()
        self.assertEqual(score.cleanliness, 0.0)
        self.assertEqual(score.overall, 0.0)
        self.assertEqual(score.grade, "UNKNOWN")

    def test_custom_values(self):
        """测试自定义值"""
        score = ComplianceScore(
            cleanliness=0.8,
            layer_adherence=0.7,
            rsca_score=0.9,
            overclaim=0.2,
            overall=0.75,
            grade="B"
        )
        self.assertEqual(score.cleanliness, 0.8)
        self.assertEqual(score.grade, "B")

if __name__ == "__main__":
    unittest.main(verbosity=2)
