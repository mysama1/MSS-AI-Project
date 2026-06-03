"""
MSS System Status Monitor
系统状态监控与自动验证

提供文件完整性检查、编码验证、测试状态监控等功能。
"""

import json
import hashlib
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class FileStatus:
    """文件状态记录"""
    path: str
    size: int
    modified_time: float
    md5_hash: str
    encoding: str
    json_valid: bool
    line_count: int
    issues: List[str]


@dataclass
class SystemSnapshot:
    """系统状态快照"""
    timestamp: str
    total_files: int
    valid_files: int
    invalid_files: int
    files: Dict[str, FileStatus]
    test_summary: Dict[str, any]
    overall_health: str  # HEALTHY, WARNING, CRITICAL


class SystemStatusMonitor:
    """系统状态监控器"""
    
    # 关键文件清单 — 需要监控的文件
    CRITICAL_FILES = [
        "knowledge_base/omega_evolution_v12.4.jsonl",
        "knowledge_base/k4_civilization_steady_state_v1.0.jsonl",
        "knowledge_base/mtl_framework_v1.0.jsonl",
        "symbolic_engine.py",
        "symbolic_engine_v2.py",
        "symbolic_engine_v3.py",
        "symbolic_rules_omega.py",
        "post_process_engine.py",
        "post_process_engine_v3.py",
        "hybrid_reasoning.py",
        "mss_stability.py",
        "simulation_numba.py",
        "resilience_visualizer.py",
        "compliance_scanner.py",
        "industry_benchmarks.py",
        "kb_loader.py",
        "mss_config.py",
        "mss_exceptions.py",
        "mss_checkpoint.py",
    ]
    
    def __init__(self, project_dir: str = "C:\\MSS-AI-Project"):
        self.project_dir = Path(project_dir)
        self.status_log = self.project_dir / "system_status_log.jsonl"
    
    def _calculate_md5(self, filepath: Path) -> str:
        """计算文件MD5哈希"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _detect_encoding(self, filepath: Path) -> Tuple[str, List[str]]:
        """检测文件编码"""
        issues = []
        
        # 检查BOM
        with open(filepath, "rb") as f:
            raw = f.read(4)
        
        if raw.startswith(b'\xef\xbb\xbf'):
            encoding = "utf-8-sig"
            issues.append("Has UTF-8 BOM")
        elif raw.startswith(b'\xff\xfe'):
            encoding = "utf-16"
            issues.append("Has UTF-16 BOM")
        else:
            encoding = "utf-8"
        
        # 尝试解码
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 检查是否有替换字符
            if '\ufffd' in content:
                issues.append("Contains replacement characters (encoding issues)")
                encoding = "utf-8-with-errors"
            
        except UnicodeDecodeError:
            encoding = "non-utf8"
            issues.append("Not valid UTF-8")
        
        return encoding, issues
    
    def _validate_jsonl(self, filepath: Path) -> Tuple[bool, int, List[str]]:
        """验证JSONL文件"""
        issues = []
        valid_count = 0
        total_count = 0
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    total_count += 1
                    try:
                        json.loads(line)
                        valid_count += 1
                    except json.JSONDecodeError as e:
                        issues.append(f"Line {i}: JSON parse error - {e}")
        except Exception as e:
            issues.append(f"File read error: {e}")
        
        is_valid = valid_count == total_count and total_count > 0
        return is_valid, total_count, issues
    
    def check_file(self, relative_path: str) -> FileStatus:
        """检查单个文件状态"""
        filepath = self.project_dir / relative_path
        issues = []
        
        if not filepath.exists():
            return FileStatus(
                path=relative_path,
                size=0,
                modified_time=0,
                md5_hash="",
                encoding="missing",
                json_valid=False,
                line_count=0,
                issues=["File not found"]
            )
        
        # 基本属性
        stat = filepath.stat()
        size = stat.st_size
        modified_time = stat.st_mtime
        
        # 计算MD5
        md5_hash = self._calculate_md5(filepath)
        
        # 检测编码
        encoding, encoding_issues = self._detect_encoding(filepath)
        issues.extend(encoding_issues)
        
        # 验证JSONL
        json_valid = False
        line_count = 0
        if relative_path.endswith('.jsonl'):
            json_valid, line_count, json_issues = self._validate_jsonl(filepath)
            issues.extend(json_issues)
        else:
            # 非JSONL文件，计算行数
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                line_count = sum(1 for _ in f)
        
        return FileStatus(
            path=relative_path,
            size=size,
            modified_time=modified_time,
            md5_hash=md5_hash,
            encoding=encoding,
            json_valid=json_valid,
            line_count=line_count,
            issues=issues
        )
    
    def run_system_check(self) -> SystemSnapshot:
        """运行完整系统检查"""
        files = {}
        valid_count = 0
        invalid_count = 0
        
        for relative_path in self.CRITICAL_FILES:
            status = self.check_file(relative_path)
            files[relative_path] = status
            
            if not status.issues:
                valid_count += 1
            else:
                invalid_count += 1
        
        # 确定整体健康状态
        if invalid_count == 0:
            health = "HEALTHY"
        elif invalid_count / len(self.CRITICAL_FILES) < 0.2:
            health = "WARNING"
        else:
            health = "CRITICAL"
        
        snapshot = SystemSnapshot(
            timestamp=datetime.now().isoformat(),
            total_files=len(self.CRITICAL_FILES),
            valid_files=valid_count,
            invalid_files=invalid_count,
            files=files,
            test_summary={},  # 可由外部填充
            overall_health=health
        )
        
        # 保存到日志
        self._save_snapshot(snapshot)
        
        return snapshot
    
    def _save_snapshot(self, snapshot: SystemSnapshot):
        """保存快照到日志文件"""
        with open(self.status_log, "a", encoding="utf-8") as f:
            record = {
                "timestamp": snapshot.timestamp,
                "health": snapshot.overall_health,
                "total": snapshot.total_files,
                "valid": snapshot.valid_files,
                "invalid": snapshot.invalid_files,
                "issues_found": [
                    {
                        "file": path,
                        "issues": status.issues
                    }
                    for path, status in snapshot.files.items()
                    if status.issues
                ]
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def generate_report(self, snapshot: SystemSnapshot) -> str:
        """生成状态报告"""
        lines = [
            "=" * 70,
            "MSS System Status Report",
            "=" * 70,
            f"Timestamp: {snapshot.timestamp}",
            f"Overall Health: {snapshot.overall_health}",
            f"Files Checked: {snapshot.total_files}",
            f"Valid: {snapshot.valid_files} | Invalid: {snapshot.invalid_files}",
            "",
            "File Details:",
            "-" * 70
        ]
        
        for path, status in snapshot.files.items():
            status_icon = "OK" if not status.issues else "FAIL"
            lines.append(f"[{status_icon}] {path}")
            lines.append(f"   Size: {status.size} bytes | Lines: {status.line_count} | Encoding: {status.encoding}")
            if status.md5_hash:
                lines.append(f"   MD5: {status.md5_hash[:16]}...")
            if status.issues:
                for issue in status.issues:
                    lines.append(f"   ! {issue}")
            lines.append("")
        
        lines.extend([
            "-" * 70,
            f"Report generated at {datetime.now().isoformat()}",
            "=" * 70
        ])
        
        return "\n".join(lines)
    
    def check_specific_issue(self, relative_path: str, issue_type: str) -> bool:
        """
        检查特定文件是否存在特定问题
        
        用于自动化验证，如：
        - omega_evolution 编码问题
        - 知识库JSON完整性
        """
        status = self.check_file(relative_path)
        
        if issue_type == "encoding":
            return status.encoding in ["utf-8", "utf-8-sig"] and "encoding issues" not in str(status.issues)
        elif issue_type == "json_valid":
            return status.json_valid
        elif issue_type == "exists":
            return status.size > 0
        else:
            return len(status.issues) == 0


def demo_status_monitor():
    """演示系统状态监控"""
    monitor = SystemStatusMonitor()
    
    print("Running system status check...")
    snapshot = monitor.run_system_check()
    
    report = monitor.generate_report(snapshot)
    print(report)
    
    # 保存报告
    report_path = f"C:\\MSS-AI-Project\\status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    
    # 特定检查示例
    print("\n" + "=" * 70)
    print("Specific Issue Checks")
    print("=" * 70)
    
    omega_encoding_ok = monitor.check_specific_issue(
        "knowledge_base/omega_evolution_v12.4.jsonl", "encoding"
    )
    print(f"omega_evolution encoding OK: {omega_encoding_ok}")
    
    omega_json_ok = monitor.check_specific_issue(
        "knowledge_base/omega_evolution_v12.4.jsonl", "json_valid"
    )
    print(f"omega_evolution JSON valid: {omega_json_ok}")


if __name__ == "__main__":
    demo_status_monitor()
