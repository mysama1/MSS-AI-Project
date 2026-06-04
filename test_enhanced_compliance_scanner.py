"""
Test suite for Enhanced Compliance Scanner
增强型合规扫描器测试
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
from enhanced_compliance_scanner import (
    EnhancedComplianceScanner, BatchScanConfig,
    quick_scan_directory
)

class TestEnhancedComplianceScanner(unittest.TestCase):
    """测试增强型合规扫描器"""

    def setUp(self):
        self.scanner = EnhancedComplianceScanner()

        # 创建临时测试目录
        self.test_dir = tempfile.mkdtemp(prefix="test_compliance_")

        # 创建测试文件
        (Path(self.test_dir) / "test_doc.md").write_text(
            "# 测试文档\n\n这是一个合规的文档。\n",
            encoding="utf-8"
        )
        (Path(self.test_dir) / "test_code.py").write_text(
            "# 测试代码\nprint('hello')\n",
            encoding="utf-8"
        )

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_scan_directory_basic(self):
        """测试基本目录扫描"""
        report = self.scanner.scan_directory(self.test_dir)

        self.assertIn("summary", report)
        self.assertGreater(report["summary"]["files_scanned"], 0)
        self.assertIn("files", report)

    def test_scan_directory_with_industry(self):
        """测试带行业基准的扫描"""
        report = self.scanner.scan_directory(self.test_dir, industry="tech_startup")

        self.assertIn("benchmark_comparison", report)
        comp = report["benchmark_comparison"]
        self.assertIn("current_average", comp)
        self.assertIn("benchmark_average", comp)

    def test_scan_with_remediation(self):
        """测试扫描+修复"""
        test_file = Path(self.test_dir) / "overclaim_doc.md"
        test_file.write_text(
            "# 文档\n\n这是终极解决方案，完美无缺。\n",
            encoding="utf-8"
        )

        result = self.scanner.scan_with_remediation(str(test_file))

        self.assertIn("scan", result)
        self.assertIn("remediation", result)
        self.assertIn("can_auto_fix", result["remediation"])

    def test_incremental_scan(self):
        """测试增量扫描"""
        config = BatchScanConfig(incremental=True, history_file=os.path.join(self.test_dir, ".history.json"))
        scanner = EnhancedComplianceScanner(config)

        # 首次扫描
        report1 = scanner.scan_directory(self.test_dir)
        files_first = report1["summary"]["files_scanned"]

        # 再次扫描（应该跳过未变更文件）
        report2 = scanner.scan_directory(self.test_dir)
        files_second = report2["summary"]["files_scanned"]

        # 增量模式下第二次应该扫描0个或更少文件
        self.assertLessEqual(files_second, files_first)

    def test_quick_scan(self):
        """测试快速扫描函数"""
        report = quick_scan_directory(self.test_dir)

        self.assertIn("summary", report)
        self.assertIn("files", report)

class TestBatchScanConfig(unittest.TestCase):
    """测试批量扫描配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = BatchScanConfig()

        self.assertTrue(config.recursive)
        self.assertFalse(config.incremental)
        self.assertGreater(config.max_file_size, 0)

    def test_custom_config(self):
        """测试自定义配置"""
        config = BatchScanConfig(
            include_patterns=["*.py"],
            recursive=False,
            incremental=True
        )

        self.assertEqual(config.include_patterns, ["*.py"])
        self.assertFalse(config.recursive)
        self.assertTrue(config.incremental)

if __name__ == "__main__":
    unittest.main()
