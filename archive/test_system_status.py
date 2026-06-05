"""
Tests for system_status.py
"""

import unittest
import os
import tempfile
from pathlib import Path
from system_status import SystemStatusMonitor, FileStatus

class TestSystemStatusMonitor(unittest.TestCase):

    def setUp(self):
        self.monitor = SystemStatusMonitor()

    def test_check_existing_file(self):
        """检查存在的文件"""
        status = self.monitor.check_file("knowledge_base/omega_evolution_v12.4.jsonl")
        self.assertEqual(status.path, "knowledge_base/omega_evolution_v12.4.jsonl")
        self.assertGreater(status.size, 0)
        self.assertEqual(status.encoding, "utf-8")
        self.assertTrue(status.json_valid)
        self.assertEqual(len(status.issues), 0)

    def test_check_missing_file(self):
        """检查不存在的文件"""
        status = self.monitor.check_file("nonexistent_file.py")
        self.assertEqual(status.size, 0)
        self.assertEqual(status.encoding, "missing")
        self.assertIn("File not found", status.issues)

    def test_check_specific_issue_encoding(self):
        """特定问题检查：编码"""
        result = self.monitor.check_specific_issue(
            "knowledge_base/omega_evolution_v12.4.jsonl", "encoding"
        )
        self.assertTrue(result)

    def test_check_specific_issue_json_valid(self):
        """特定问题检查：JSON有效性"""
        result = self.monitor.check_specific_issue(
            "knowledge_base/omega_evolution_v12.4.jsonl", "json_valid"
        )
        self.assertTrue(result)

    def test_run_system_check(self):
        """运行完整系统检查"""
        snapshot = self.monitor.run_system_check()
        self.assertIn(snapshot.overall_health, ["HEALTHY", "WARNING", "CRITICAL"])
        self.assertEqual(snapshot.total_files, len(self.monitor.CRITICAL_FILES))
        self.assertEqual(snapshot.valid_files + snapshot.invalid_files, snapshot.total_files)

    def test_generate_report(self):
        """生成报告"""
        snapshot = self.monitor.run_system_check()
        report = self.monitor.generate_report(snapshot)
        self.assertIn("MSS System Status Report", report)
        self.assertIn(snapshot.overall_health, report)

    def test_log_file_created(self):
        """日志文件是否创建"""
        # 确保运行过检查
        self.monitor.run_system_check()
        self.assertTrue(self.monitor.status_log.exists())

if __name__ == "__main__":
    unittest.main(verbosity=2)
