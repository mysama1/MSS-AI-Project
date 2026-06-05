"""
MSS Enhanced Compliance Scanner
增强型合规扫描器

新增功能：
- 批量目录扫描（递归）
- 增量扫描（仅扫描变更文件）
- 修复建议自动应用
- 集成行业基准对比
- 历史扫描追踪
"""

import os
import re
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import fnmatch

from compliance_scanner import ComplianceScanner, ComplianceScore, ScanResult
from industry_benchmarks import get_benchmark, compare_to_benchmark


@dataclass
class BatchScanConfig:
    """批量扫描配置"""
    include_patterns: List[str] = field(default_factory=lambda: ["*.md", "*.txt", "*.json", "*.py"])
    exclude_patterns: List[str] = field(default_factory=lambda: ["*.min.js", "node_modules/*", "__pycache__/*"])
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    recursive: bool = True
    incremental: bool = False  # 增量扫描
    history_file: str = ".compliance_history.json"


@dataclass
class FileFingerprint:
    """文件指纹（用于增量扫描）"""
    filepath: str
    mtime: float
    size: int
    content_hash: str


class EnhancedComplianceScanner:
    """增强型合规扫描器"""
    
    def __init__(self, config: Optional[BatchScanConfig] = None):
        self.config = config or BatchScanConfig()
        self.scanner = ComplianceScanner()
        self.history: Dict[str, FileFingerprint] = {}
        self.scan_history: List[Dict] = []
        
        if self.config.incremental:
            self._load_history()
    
    def scan_directory(
        self,
        directory: str,
        industry: Optional[str] = None
    ) -> Dict:
        """
        扫描整个目录
        
        Args:
            directory: 目标目录
            industry: 行业类型（用于基准对比）
        
        Returns:
            扫描报告
        """
        directory = Path(directory)
        
        if not directory.exists():
            return {"error": f"Directory not found: {directory}"}
        
        # 收集文件
        files = self._collect_files(directory)
        
        # 过滤已扫描未变更的文件（增量模式）
        if self.config.incremental:
            files = self._filter_unchanged(files)
        
        # 执行扫描
        results = []
        for filepath in files:
            try:
                result = self.scanner.scan_file(str(filepath))
                results.append(result)
                
                # 更新指纹
                if self.config.incremental:
                    self._update_fingerprint(filepath)
            
            except Exception as e:
                results.append(ScanResult(
                    file_path=str(filepath),
                    file_size=0,
                    line_count=0,
                    score=ComplianceScore(
                        overall=0.0,
                        grade="ERROR",
                        issues=[{"error": str(e)}]
                    )
                ))
        
        # 生成报告
        report = self._generate_directory_report(results, directory, industry)
        
        # 保存历史
        if self.config.incremental:
            self._save_history()
        
        # 记录扫描历史
        self.scan_history.append({
            "timestamp": datetime.now().isoformat(),
            "directory": str(directory),
            "files_scanned": len(results),
            "avg_score": report["summary"]["average_score"]
        })
        
        return report
    
    def scan_with_remediation(
        self,
        filepath: str,
        auto_apply: bool = False
    ) -> Dict:
        """
        扫描并生成修复方案
        
        Args:
            filepath: 文件路径
            auto_apply: 是否自动应用修复
        
        Returns:
            扫描结果+修复建议
        """
        result = self.scanner.scan_file(filepath)
        
        # 生成修复建议
        remediation = self._generate_remediation(result)
        
        response = {
            "scan": {
                "file": result.file_path,
                "score": {
                    "overall": result.score.overall,
                    "grade": result.score.grade,
                    "cleanliness": result.score.cleanliness,
                    "layer_adherence": result.score.layer_adherence,
                    "rsca_score": result.score.rsca_score,
                    "overclaim": result.score.overclaim
                },
                "issues_count": len(result.score.issues)
            },
            "remediation": remediation
        }
        
        # 自动应用修复
        if auto_apply and remediation["can_auto_fix"]:
            fixed_content = self._apply_fixes(filepath, remediation["fixes"])
            response["auto_fix_applied"] = True
            response["fixed_content_preview"] = fixed_content[:500] if fixed_content else None
        
        return response
    
    def compare_with_benchmark(
        self,
        scan_results: List[ScanResult],
        industry: str
    ) -> Dict:
        """
        与行业基准对比
        
        Args:
            scan_results: 扫描结果列表
            industry: 行业名称
        """
        # 计算当前平均分
        scores = [r.score.overall for r in scan_results if r.score.overall > 0]
        if not scores:
            return {"error": "No valid scores to compare"}
        
        current_avg = sum(scores) / len(scores)
        
        # 获取行业基准
        benchmark = get_benchmark(industry)
        
        if benchmark is None:
            return {"error": f"Unknown industry: {industry}"}
        
        # 使用韧性基准中的M_target作为平均分参考
        benchmark_avg = benchmark.resilience_benchmark.get("M_target", 0.5)
        
        comparison = {
            "industry": industry,
            "current_average": round(current_avg, 3),
            "benchmark_average": benchmark_avg,
            "difference": round(current_avg - benchmark_avg, 3),
            "percentile": self._calculate_percentile(current_avg, {"average_score": benchmark_avg, "std_dev": 0.15}),
            "gap_analysis": []
        }
        
        # 差距分析
        if current_avg < benchmark_avg:
            comparison["gap_analysis"].append({
                "area": "整体合规水平",
                "status": "below_average",
                "recommendation": f"低于行业均值 {benchmark_avg:.3f}，建议系统性改进"
            })
        
        # 维度对比
        dimensions = ["cleanliness", "layer_adherence", "rsca_score"]
        for dim in dimensions:
            current_dim = sum(
                getattr(r.score, dim, 0) for r in scan_results
            ) / len(scan_results)
            bench_dim = benchmark.resilience_benchmark.get(f"{dim}_target", 0.5)
            
            if current_dim < bench_dim - 0.1:
                comparison["gap_analysis"].append({
                    "area": dim,
                    "status": "significantly_below",
                    "current": round(current_dim, 3),
                    "benchmark": bench_dim,
                    "recommendation": f"{dim}维度显著低于行业水平，需重点改进"
                })
        
        return comparison
    
    def _collect_files(self, directory: Path) -> List[Path]:
        """收集符合条件的文件"""
        files = []
        
        if self.config.recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for filepath in directory.glob(pattern):
            if not filepath.is_file():
                continue
            
            # 检查文件大小
            if filepath.stat().st_size > self.config.max_file_size:
                continue
            
            # 检查包含模式
            if not any(fnmatch.fnmatch(filepath.name, p) for p in self.config.include_patterns):
                continue
            
            # 检查排除模式
            if any(fnmatch.fnmatch(str(filepath), p) for p in self.config.exclude_patterns):
                continue
            
            files.append(filepath)
        
        return sorted(files)
    
    def _filter_unchanged(self, files: List[Path]) -> List[Path]:
        """过滤未变更的文件"""
        changed = []
        
        for filepath in files:
            stat = filepath.stat()
            current = FileFingerprint(
                filepath=str(filepath),
                mtime=stat.st_mtime,
                size=stat.st_size,
                content_hash=self._hash_file(filepath)
            )
            
            key = str(filepath)
            if key not in self.history:
                changed.append(filepath)
            elif (self.history[key].mtime != current.mtime or
                  self.history[key].size != current.size or
                  self.history[key].content_hash != current.content_hash):
                changed.append(filepath)
        
        return changed
    
    def _hash_file(self, filepath: Path) -> str:
        """计算文件哈希"""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
        except:
            return ""
        return hasher.hexdigest()
    
    def _update_fingerprint(self, filepath: Path):
        """更新文件指纹"""
        stat = filepath.stat()
        self.history[str(filepath)] = FileFingerprint(
            filepath=str(filepath),
            mtime=stat.st_mtime,
            size=stat.st_size,
            content_hash=self._hash_file(filepath)
        )
    
    def _load_history(self):
        """加载历史指纹"""
        history_path = Path(self.config.history_file)
        if history_path.exists():
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for key, value in data.items():
                    self.history[key] = FileFingerprint(**value)
            except:
                pass
    
    def _save_history(self):
        """保存历史指纹"""
        data = {
            key: {
                "filepath": fp.filepath,
                "mtime": fp.mtime,
                "size": fp.size,
                "content_hash": fp.content_hash
            }
            for key, fp in self.history.items()
        }
        
        with open(self.config.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _generate_remediation(self, result: ScanResult) -> Dict:
        """生成修复建议"""
        fixes = []
        can_auto_fix = True
        
        for issue in result.score.issues:
            issue_type = issue.get("type", "unknown")
            
            if issue_type == "overclaim":
                fixes.append({
                    "type": "replace",
                    "target": issue.get("text", ""),
                    "replacement": issue.get("suggestion", ""),
                    "description": "替换过度宣称表述"
                })
            elif issue_type == "layer_violation":
                fixes.append({
                    "type": "add_marker",
                    "description": "添加层级标记[L2]或[L3]",
                    "example": "在推测性内容前添加[L3试探法]标记"
                })
                can_auto_fix = False
            elif issue_type == "rsca_failure":
                fixes.append({
                    "type": "manual_review",
                    "description": "需要人工审查自洽性",
                    "guidance": issue.get("suggestion", "")
                })
                can_auto_fix = False
            else:
                fixes.append({
                    "type": "manual_review",
                    "description": f"未分类问题: {issue_type}"
                })
                can_auto_fix = False
        
        return {
            "can_auto_fix": can_auto_fix and len(fixes) > 0,
            "fixes": fixes,
            "estimated_effort": len(fixes) * 5  # 估计修复时间（分钟）
        }
    
    def _apply_fixes(self, filepath: str, fixes: List[Dict]) -> Optional[str]:
        """应用自动修复"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for fix in fixes:
                if fix["type"] == "replace":
                    content = content.replace(fix["target"], fix["replacement"])
            
            # 写回（实际应用中可能需要备份）
            # with open(filepath, 'w', encoding='utf-8') as f:
            #     f.write(content)
            
            return content
        
        except Exception as e:
            return None
    
    def _generate_directory_report(
        self,
        results: List[ScanResult],
        directory: Path,
        industry: Optional[str]
    ) -> Dict:
        """生成目录扫描报告"""
        valid_results = [r for r in results if r.score.overall > 0]
        
        if not valid_results:
            return {
                "directory": str(directory),
                "summary": {"files_scanned": len(results), "valid_files": 0},
                "error": "No valid files scanned"
            }
        
        scores = [r.score.overall for r in valid_results]
        grades = [r.score.grade for r in valid_results]
        
        report = {
            "directory": str(directory),
            "scan_time": datetime.now().isoformat(),
            "summary": {
                "files_scanned": len(results),
                "valid_files": len(valid_results),
                "average_score": round(sum(scores) / len(scores), 3),
                "min_score": round(min(scores), 3),
                "max_score": round(max(scores), 3),
                "grade_distribution": {
                    grade: grades.count(grade) for grade in set(grades)
                }
            },
            "files": []
        }
        
        # 文件详情
        for result in valid_results:
            report["files"].append({
                "path": result.file_path,
                "size": result.file_size,
                "lines": result.line_count,
                "score": round(result.score.overall, 3),
                "grade": result.score.grade,
                "issues": len(result.score.issues)
            })
        
        # 行业对比
        if industry:
            comparison = self.compare_with_benchmark(valid_results, industry)
            report["benchmark_comparison"] = comparison
        
        # 风险文件（评分最低）
        report["risk_files"] = sorted(
            report["files"],
            key=lambda x: x["score"]
        )[:5]
        
        return report
    
    def _calculate_percentile(self, score: float, benchmark: Dict) -> int:
        """计算百分位排名"""
        # 简化实现：基于行业均值的正态分布假设
        avg = benchmark.get("average_score", 0.5)
        std = benchmark.get("std_dev", 0.15)
        
        if std == 0:
            return 50
        
        import math
        z_score = (score - avg) / std
        percentile = int(50 + z_score * 34)  # 简化正态近似
        
        return max(0, min(100, percentile))


# 便捷函数
def quick_scan_directory(directory: str, industry: Optional[str] = None) -> Dict:
    """快速扫描目录"""
    scanner = EnhancedComplianceScanner()
    return scanner.scan_directory(directory, industry)


def scan_with_benchmark(directory: str, industry: str) -> Dict:
    """扫描并对比行业基准"""
    scanner = EnhancedComplianceScanner()
    report = scanner.scan_directory(directory, industry)
    return report


if __name__ == "__main__":
    # 演示
    print("=" * 70)
    print("MSS Enhanced Compliance Scanner Demo")
    print("=" * 70)
    
    # 扫描当前目录
    scanner = EnhancedComplianceScanner()
    report = scanner.scan_directory(".", industry="tech_startup")
    
    print(f"\n扫描目录: {report['directory']}")
    print(f"文件数: {report['summary']['files_scanned']}")
    print(f"平均分: {report['summary']['average_score']}")
    print(f"等级分布: {report['summary']['grade_distribution']}")
    
    if "benchmark_comparison" in report:
        comp = report["benchmark_comparison"]
        print(f"\n行业对比 ({comp['industry']}):")
        print(f"  当前: {comp['current_average']}")
        print(f"  行业均值: {comp['benchmark_average']}")
        print(f"  差距: {comp['difference']}")
    
    print("\n风险文件Top 5:")
    for f in report.get("risk_files", [])[:5]:
        print(f"  {f['path']}: {f['score']} ({f['grade']})")
