"""
MSS Text Compliance Scanner
文本合规扫描器产品化

批量文档扫描、评分卡生成、修复建议、报告导出
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import fnmatch

from mss_analyzer import MSSAnalyzer
from arbiter_agent import ArbiterAgent


@dataclass
class ComplianceScore:
    """合规评分"""
    cleanliness: float = 0.0      # 清洁度 (0-1)
    layer_adherence: float = 0.0  # 层级遵循 (0-1)
    rsca_score: float = 0.0       # RSCA评分 (0-1)
    overclaim: float = 0.0        # 过度宣称 (0-1, 越低越好)
    
    # 综合评分
    overall: float = 0.0
    grade: str = "UNKNOWN"
    
    # 详细结果
    issues: List[Dict] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """扫描结果"""
    file_path: str
    file_size: int
    line_count: int
    
    # 评分
    score: ComplianceScore
    
    # 元数据
    scan_time: str = field(default_factory=lambda: datetime.now().isoformat())
    processing_time_ms: float = 0.0


class ComplianceScanner:
    """
    文本合规扫描器
    
    基于MSS仲裁引擎，实现批量文档的自动化合规检查
    """
    
    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.py', '.json', '.yaml', '.yml'}
    
    # 评分权重
    WEIGHTS = {
        'cleanliness': 0.25,
        'layer_adherence': 0.30,
        'rsca': 0.30,
        'overclaim': 0.15
    }
    
    def __init__(self, 
                 analyzer: Optional[MSSAnalyzer] = None,
                 arbiter: Optional[ArbiterAgent] = None):
        self.analyzer = analyzer or MSSAnalyzer()
        self.arbiter = arbiter or ArbiterAgent()
        
        # 统计信息
        self.stats = {
            'files_scanned': 0,
            'files_passed': 0,
            'files_failed': 0,
            'total_issues': 0,
            'start_time': None,
            'end_time': None
        }
    
    def scan_file(self, file_path: str) -> ScanResult:
        """
        扫描单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ScanResult: 扫描结果
        """
        start_time = datetime.now()
        
        # 读取文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return ScanResult(
                file_path=file_path,
                file_size=0,
                line_count=0,
                score=ComplianceScore(
                    overall=0.0,
                    grade="ERROR",
                    issues=[{"error": str(e)}]
                )
            )
        
        # 分析内容
        lines = content.split('\n')
        line_count = len(lines)
        
        # 使用MSS分析器
        try:
            analysis = self.analyzer.analyze(content)
            
            # 计算评分
            score = self._calculate_score(analysis, content)
            
        except Exception as e:
            score = ComplianceScore(
                overall=0.5,
                grade="UNKNOWN",
                issues=[{"analyzer_error": str(e)}]
            )
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ScanResult(
            file_path=file_path,
            file_size=len(content.encode('utf-8')),
            line_count=line_count,
            score=score,
            processing_time_ms=processing_time
        )
    
    def scan_directory(self, 
                      directory: str,
                      pattern: str = "*",
                      recursive: bool = True,
                      progress_callback: Optional[callable] = None) -> List[ScanResult]:
        """
        扫描目录
        
        Args:
            directory: 目标目录
            pattern: 文件匹配模式 (如 "*.md", "*.py")
            recursive: 是否递归子目录
            progress_callback: 进度回调函数(current, total)
            
        Returns:
            List[ScanResult]: 扫描结果列表
        """
        self.stats['start_time'] = datetime.now().isoformat()
        self.stats['files_scanned'] = 0
        self.stats['files_passed'] = 0
        self.stats['files_failed'] = 0
        self.stats['total_issues'] = 0
        
        results = []
        
        # 收集文件
        if recursive:
            files = list(Path(directory).rglob(pattern))
        else:
            files = list(Path(directory).glob(pattern))
        
        # 过滤支持的文件类型
        files = [f for f in files if f.suffix in self.SUPPORTED_EXTENSIONS]
        
        total = len(files)
        
        for i, file_path in enumerate(files):
            result = self.scan_file(str(file_path))
            results.append(result)
            
            # 更新统计
            self.stats['files_scanned'] += 1
            if result.score.grade in ['A', 'B']:
                self.stats['files_passed'] += 1
            else:
                self.stats['files_failed'] += 1
            self.stats['total_issues'] += len(result.score.issues)
            
            # 进度回调
            if progress_callback:
                progress_callback(i + 1, total)
        
        self.stats['end_time'] = datetime.now().isoformat()
        
        return results
    
    def generate_scorecard(self, results: List[ScanResult]) -> Dict:
        """
        生成评分卡
        
        Args:
            results: 扫描结果列表
            
        Returns:
            Dict: 评分卡数据
        """
        if not results:
            return {"error": "No results to generate scorecard"}
        
        # 计算平均分
        avg_cleanliness = sum(r.score.cleanliness for r in results) / len(results)
        avg_layer = sum(r.score.layer_adherence for r in results) / len(results)
        avg_rsca = sum(r.score.rsca_score for r in results) / len(results)
        avg_overclaim = sum(r.score.overclaim for r in results) / len(results)
        avg_overall = sum(r.score.overall for r in results) / len(results)
        
        # 等级分布
        grade_distribution = {}
        for r in results:
            grade = r.score.grade
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        # 问题统计
        all_issues = []
        for r in results:
            all_issues.extend(r.score.issues)
        
        issue_categories = {}
        for issue in all_issues:
            cat = issue.get('category', 'UNKNOWN')
            issue_categories[cat] = issue_categories.get(cat, 0) + 1
        
        return {
            "summary": {
                "total_files": len(results),
                "avg_overall_score": round(avg_overall, 4),
                "avg_grade": self._grade_from_score(avg_overall),
                "pass_rate": round(self.stats['files_passed'] / max(1, self.stats['files_scanned']), 4),
                "total_issues": len(all_issues)
            },
            "dimension_scores": {
                "cleanliness": round(avg_cleanliness, 4),
                "layer_adherence": round(avg_layer, 4),
                "rsca": round(avg_rsca, 4),
                "overclaim": round(avg_overclaim, 4)
            },
            "grade_distribution": grade_distribution,
            "issue_categories": issue_categories,
            "top_issues": self._get_top_issues(all_issues, 10),
            "file_breakdown": [
                {
                    "file": os.path.basename(r.file_path),
                    "score": r.score.overall,
                    "grade": r.score.grade,
                    "issues": len(r.score.issues)
                }
                for r in sorted(results, key=lambda x: x.score.overall)
            ]
        }
    
    def generate_markdown_report(self, results: List[ScanResult],
                                 output_path: Optional[str] = None) -> str:
        """
        生成Markdown格式合规报告
        """
        scorecard = self.generate_scorecard(results)
        
        report = f"""# MSS文本合规扫描报告

**扫描时间:** {datetime.now().isoformat()}  
**MSS框架版本:** v12.2  
**扫描文件数:** {scorecard['summary']['total_files']}

---

## 一、执行摘要

| 指标 | 数值 | 状态 |
|:-----|:-----|:-----|
| 综合评分 | {scorecard['summary']['avg_overall_score']:.4f} | {self._grade_badge(scorecard['summary']['avg_grade'])} |
| 通过率 | {scorecard['summary']['pass_rate']*100:.1f}% | {'🟢' if scorecard['summary']['pass_rate'] > 0.8 else '🟡' if scorecard['summary']['pass_rate'] > 0.5 else '🔴'} |
| 总问题数 | {scorecard['summary']['total_issues']} | {'🟢' if scorecard['summary']['total_issues'] == 0 else '🟡' if scorecard['summary']['total_issues'] < 10 else '🔴'} |

### 维度评分

| 维度 | 得分 | 权重 | 加权贡献 |
|:-----|:-----|:-----|:---------|
| 清洁度 | {scorecard['dimension_scores']['cleanliness']:.4f} | 25% | {scorecard['dimension_scores']['cleanliness'] * 0.25:.4f} |
| 层级遵循 | {scorecard['dimension_scores']['layer_adherence']:.4f} | 30% | {scorecard['dimension_scores']['layer_adherence'] * 0.30:.4f} |
| RSCA | {scorecard['dimension_scores']['rsca']:.4f} | 30% | {scorecard['dimension_scores']['rsca'] * 0.30:.4f} |
| 过度宣称 | {scorecard['dimension_scores']['overclaim']:.4f} | 15% | {scorecard['dimension_scores']['overclaim'] * 0.15:.4f} |

---

## 二、等级分布

"""
        
        for grade, count in sorted(scorecard['grade_distribution'].items()):
            bar = "█" * count
            report += f"- {self._grade_badge(grade)} {grade}: {count} 文件 {bar}\n"
        
        report += "\n---\n\n## 三、问题分类统计\n\n"
        
        if scorecard['issue_categories']:
            for category, count in sorted(scorecard['issue_categories'].items(), 
                                         key=lambda x: x[1], reverse=True):
                report += f"- **{category}**: {count} 次\n"
        else:
            report += "✅ 未发现明显问题\n"
        
        report += "\n---\n\n## 四、文件明细 (按评分排序)\n\n"
        report += "| 文件 | 评分 | 等级 | 问题数 | 状态 |\n"
        report += "|:-----|:-----|:-----|:-------|:-----|\n"
        
        for file_info in scorecard['file_breakdown']:
            status = '🟢' if file_info['grade'] in ['A', 'B'] else '🟡' if file_info['grade'] == 'C' else '🔴'
            report += f"| {file_info['file']} | {file_info['score']:.4f} | {file_info['grade']} | {file_info['issues']} | {status} |\n"
        
        report += f"""

---

## 五、Top 问题

"""
        
        for i, issue in enumerate(scorecard['top_issues'], 1):
            report += f"{i}. **{issue.get('category', 'UNKNOWN')}**: {issue.get('description', 'No description')}\n"
        
        report += f"""

---

*报告生成时间: {datetime.now().isoformat()}*  
*MSS-AI Text Compliance Scanner v1.0*
"""
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            return output_path
        
        return report
    
    def _calculate_score(self, analysis: Dict, content: str) -> ComplianceScore:
        """计算合规评分"""
        # 从分析结果提取指标
        cleanliness = analysis.get('cleanliness', 0.5)
        layer_adherence = analysis.get('layer_adherence', 0.5)
        rsca_score = analysis.get('rsca_score', 0.5)
        overclaim = analysis.get('overclaim', 0.5)
        
        # 计算综合评分
        overall = (
            cleanliness * self.WEIGHTS['cleanliness'] +
            layer_adherence * self.WEIGHTS['layer_adherence'] +
            rsca_score * self.WEIGHTS['rsca'] +
            (1 - overclaim) * self.WEIGHTS['overclaim']  # overclaim越低越好
        )
        
        # 提取问题
        issues = analysis.get('issues', [])
        suggestions = analysis.get('suggestions', [])
        
        return ComplianceScore(
            cleanliness=cleanliness,
            layer_adherence=layer_adherence,
            rsca_score=rsca_score,
            overclaim=overclaim,
            overall=round(overall, 4),
            grade=self._grade_from_score(overall),
            issues=issues,
            suggestions=suggestions
        )
    
    def _grade_from_score(self, score: float) -> str:
        """根据评分确定等级"""
        if score >= 0.85:
            return "A"
        elif score >= 0.70:
            return "B"
        elif score >= 0.50:
            return "C"
        else:
            return "D"
    
    def _grade_badge(self, grade: str) -> str:
        """等级徽章"""
        return {
            'A': '🟢 A',
            'B': '🔵 B',
            'C': '🟡 C',
            'D': '🔴 D',
            'ERROR': '⚪ ERR',
            'UNKNOWN': '⚪ ?'
        }.get(grade, '⚪ ?')
    
    def _get_top_issues(self, issues: List[Dict], n: int = 10) -> List[Dict]:
        """获取Top N问题"""
        # 按严重程度排序
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        sorted_issues = sorted(issues, 
                             key=lambda x: severity_order.get(x.get('severity', 'LOW'), 4))
        return sorted_issues[:n]


def demo_compliance_scan():
    """演示合规扫描"""
    print("=" * 70)
    print("MSS Text Compliance Scanner Demo")
    print("=" * 70)
    print()
    
    scanner = ComplianceScanner()
    
    # 扫描当前目录的Python文件
    print("Scanning Python files in current directory...")
    results = scanner.scan_directory(
        ".",
        pattern="*.py",
        recursive=False,
        progress_callback=lambda current, total: print(f"  Progress: {current}/{total}", end='\r')
    )
    
    print(f"\n\nScanned {len(results)} files")
    print(f"Passed: {scanner.stats['files_passed']}")
    print(f"Failed: {scanner.stats['files_failed']}")
    print(f"Total issues: {scanner.stats['total_issues']}")
    print()
    
    # 生成评分卡
    scorecard = scanner.generate_scorecard(results)
    print("Scorecard Summary:")
    print(f"  Average score: {scorecard['summary']['avg_overall_score']:.4f}")
    print(f"  Pass rate: {scorecard['summary']['pass_rate']*100:.1f}%")
    print()
    
    # 生成报告
    report_path = "compliance_report.md"
    scanner.generate_markdown_report(results, report_path)
    print(f"Report saved to: {report_path}")
    
    return results


if __name__ == "__main__":
    demo_compliance_scan()
