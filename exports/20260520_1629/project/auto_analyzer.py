#!/usr/bin/env python3
"""
MSS-AI 自动化分析器
自动分析项目状态、生成决策建议、执行优化任务
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class MSSAutoAnalyzer:
    """MSS-AI 自动化分析引擎"""
    
    def __init__(self, project_root: str = "C:\\MSS-AI-Project"):
        self.project_root = project_root
        self.kb_dir = os.path.join(project_root, "knowledge_base")
        self.logs_dir = os.path.join(project_root, "logs")
        self.report_dir = os.path.join(project_root, "reports")
        
        # 确保目录存在
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)
        
        # 状态缓存
        self._kb_cache = None
        self._last_scan = 0
        
    def analyze_knowledge_base(self) -> Dict:
        """分析知识库状态"""
        files = [f for f in os.listdir(self.kb_dir) if f.endswith('.jsonl')]
        
        total_entries = 0
        layer_counts = {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0}
        categories = {}
        recent_files = []
        
        for fname in sorted(files):
            path = os.path.join(self.kb_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    entries = [json.loads(line) for line in f if line.strip()]
                
                total_entries += len(entries)
                recent_files.append({
                    'name': fname,
                    'entries': len(entries),
                    'mtime': os.path.getmtime(path)
                })
                
                for e in entries:
                    layer = e.get('layer', 'unknown')
                    if layer in layer_counts:
                        layer_counts[layer] += 1
                    
                    cat = e.get('category', 'unknown')
                    categories[cat] = categories.get(cat, 0) + 1
                    
            except Exception as ex:
                print(f"Warning: Failed to parse {fname}: {ex}")
        
        # 按时间排序获取最近文件
        recent_files.sort(key=lambda x: x['mtime'], reverse=True)
        
        return {
            'total_entries': total_entries,
            'target': 500,
            'progress_pct': round(total_entries / 500 * 100, 1),
            'remaining': 500 - total_entries,
            'layer_counts': layer_counts,
            'categories': categories,
            'file_count': len(files),
            'recent_files': recent_files[:5]
        }
    
    def analyze_code_health(self) -> Dict:
        """分析代码健康度"""
        py_files = []
        total_lines = 0
        test_files = 0
        
        for root, dirs, files in os.walk(self.project_root):
            # 跳过 archive 和 __pycache__
            dirs[:] = [d for d in dirs if d not in ['archive', '__pycache__', '.git']]
            
            for f in files:
                if f.endswith('.py'):
                    path = os.path.join(root, f)
                    try:
                        with open(path, 'r', encoding='utf-8') as fp:
                            lines = len(fp.readlines())
                        total_lines += lines
                        py_files.append({'name': f, 'lines': lines})
                        
                        if f.startswith('test_'):
                            test_files += 1
                    except:
                        pass
        
        py_files.sort(key=lambda x: x['lines'], reverse=True)
        
        return {
            'total_python_files': len(py_files),
            'total_lines': total_lines,
            'test_files': test_files,
            'largest_files': py_files[:10],
            'avg_lines': round(total_lines / len(py_files), 1) if py_files else 0
        }
    
    def generate_decision_matrix(self, kb_status: Dict, code_status: Dict) -> Dict:
        """生成决策矩阵"""
        progress = kb_status['progress_pct']
        remaining = kb_status['remaining']
        
        # 决策逻辑
        decisions = []
        
        # Phase A 决策
        if progress < 100:
            priority = "P0" if progress < 90 else "P1"
            decisions.append({
                'phase': 'A',
                'task': f'知识库扩展 {kb_status["total_entries"]}/500',
                'priority': priority,
                'action': f'继续扩展 {remaining} 条目' if remaining > 0 else 'Phase A 完成',
                'eta': f'约 {remaining // 10} 个文件' if remaining > 0 else '已完成'
            })
        
        # Phase B 决策 (性能优化)
        if progress >= 80:
            decisions.append({
                'phase': 'B',
                'task': '性能优化 (Numba JIT/CUDA)',
                'priority': 'P1' if progress >= 90 else 'P2',
                'action': '准备Numba JIT集成' if progress >= 90 else '等待Phase A完成',
                'eta': 'Week 7-8'
            })
        
        # Phase C 决策 (Docker)
        if progress >= 90:
            decisions.append({
                'phase': 'C',
                'task': 'Docker容器化',
                'priority': 'P2',
                'action': '准备Dockerfile和docker-compose',
                'eta': 'Week 9-10'
            })
        
        # Phase D 决策 (v2.0发布)
        if progress >= 95:
            decisions.append({
                'phase': 'D',
                'task': 'v2.0发布准备',
                'priority': 'P2',
                'action': '准备发布文档和changelog',
                'eta': 'Week 11-12'
            })
        
        # 代码健康决策
        if code_status['test_files'] < 30:
            decisions.append({
                'phase': 'Code',
                'task': '测试覆盖',
                'priority': 'P1',
                'action': f'当前{code_status["test_files"]}个测试文件，目标30+',
                'eta': '持续进行'
            })
        
        return {
            'current_phase': 'A' if progress < 100 else 'B',
            'progress_pct': progress,
            'decisions': decisions,
            'recommendation': self._generate_recommendation(progress, kb_status, code_status)
        }
    
    def _generate_recommendation(self, progress: float, kb: Dict, code: Dict) -> str:
        """生成综合建议"""
        if progress < 80:
            return "优先完成Phase A知识库扩展，目标500条目。建议批量创建文件(10条目/文件)，保持L1:L2:L3≈1:3:3.5的层级比例。"
        elif progress < 90:
            return "Phase A进入冲刺阶段，建议创建5-8个文件完成剩余条目。同时可开始Phase B准备工作(Numba环境搭建)。"
        elif progress < 100:
            return "Phase A即将完成，建议收尾+质量审查。同时启动Phase B性能优化，并行推进。"
        else:
            return "Phase A完成！建议立即启动Phase B性能优化，同时准备Phase C Docker化。"
    
    def generate_report(self) -> str:
        """生成完整分析报告"""
        kb = self.analyze_knowledge_base()
        code = self.analyze_code_health()
        decision = self.generate_decision_matrix(kb, code)
        
        report = f"""
# MSS-AI 自动化分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. 知识库状态

| 指标 | 数值 |
|:---|:---|
| 总条目 | {kb['total_entries']}/500 |
| 完成度 | {kb['progress_pct']}% |
| 剩余 | {kb['remaining']} 条目 |
| 文件数 | {kb['file_count']} |

### 层级分布
| L1 硬核 | L2 保护带 | L3 试探法 | L4 污染池 |
|:---|:---|:---|:---|
| {kb['layer_counts']['L1']} | {kb['layer_counts']['L2']} | {kb['layer_counts']['L3']} | {kb['layer_counts']['L4']} |

### 最近更新
"""
        for f in kb['recent_files'][:3]:
            mtime = datetime.fromtimestamp(f['mtime']).strftime('%m-%d %H:%M')
            report += f"- {f['name']}: {f['entries']} entries ({mtime})\n"
        
        report += f"""
## 2. 代码健康度

| 指标 | 数值 |
|:---|:---|
| Python文件 | {code['total_python_files']} |
| 总代码行 | {code['total_lines']} |
| 测试文件 | {code['test_files']} |
| 平均文件大小 | {code['avg_lines']} 行 |

### 最大文件
"""
        for f in code['largest_files'][:5]:
            report += f"- {f['name']}: {f['lines']} 行\n"
        
        report += f"""
## 3. 决策矩阵

| 阶段 | 任务 | 优先级 | 行动 | 预计时间 |
|:---|:---|:---|:---|:---|
"""
        for d in decision['decisions']:
            report += f"| {d['phase']} | {d['task']} | {d['priority']} | {d['action']} | {d['eta']} |\n"
        
        report += f"""
## 4. 综合建议

{decision['recommendation']}

### 下一步行动
1. {'继续扩展知识库' if kb['progress_pct'] < 100 else '启动Phase B性能优化'}
2. {'保持测试通过率100%' if code['test_files'] >= 26 else '增加测试覆盖'}
3. 定期运行本分析器监控进度

---
*本报告由 MSSAutoAnalyzer 自动生成*
"""
        
        return report
    
    def save_report(self, report: str) -> str:
        """保存报告到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"auto_report_{timestamp}.md"
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filepath
    
    def run_health_check(self) -> Dict:
        """运行健康检查"""
        kb = self.analyze_knowledge_base()
        code = self.analyze_code_health()
        
        issues = []
        warnings = []
        
        # 检查层级平衡
        l1_ratio = kb['layer_counts']['L1'] / max(kb['total_entries'], 1)
        if l1_ratio < 0.1:
            warnings.append(f"L1比例偏低({l1_ratio:.1%})，建议增加硬核公理")
        
        # 检查测试覆盖
        if code['test_files'] < 26:
            issues.append(f"测试文件不足({code['test_files']} < 26)")
        
        # 检查大文件
        for f in code['largest_files'][:3]:
            if f['lines'] > 1000:
                warnings.append(f"文件过大: {f['name']} ({f['lines']} 行)")
        
        return {
            'status': 'HEALTHY' if not issues else 'WARNING',
            'issues': issues,
            'warnings': warnings,
            'kb': kb,
            'code': code
        }


def main():
    """主函数"""
    analyzer = MSSAutoAnalyzer()
    
    print("=" * 60)
    print("MSS-AI 自动化分析器 v1.0")
    print("=" * 60)
    
    # 运行健康检查
    print("\n[1/3] 运行健康检查...")
    health = analyzer.run_health_check()
    print(f"状态: {health['status']}")
    if health['issues']:
        print(f"问题: {len(health['issues'])} 个")
        for i in health['issues']:
            print(f"  - {i}")
    if health['warnings']:
        print(f"警告: {len(health['warnings'])} 个")
        for w in health['warnings']:
            print(f"  - {w}")
    
    # 生成报告
    print("\n[2/3] 生成分析报告...")
    report = analyzer.generate_report()
    
    # 保存报告
    print("\n[3/3] 保存报告...")
    filepath = analyzer.save_report(report)
    print(f"报告已保存: {filepath}")
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("分析摘要")
    print("=" * 60)
    kb = health['kb']
    print(f"知识库: {kb['total_entries']}/500 ({kb['progress_pct']}%)")
    print(f"层级: L1={kb['layer_counts']['L1']} L2={kb['layer_counts']['L2']} L3={kb['layer_counts']['L3']}")
    print(f"代码: {health['code']['total_python_files']} 文件, {health['code']['total_lines']} 行")
    print(f"测试: {health['code']['test_files']} 文件")
    
    if kb['progress_pct'] < 100:
        remaining = kb['remaining']
        files_needed = remaining // 10 + (1 if remaining % 10 else 0)
        print(f"\n建议: 继续创建 {files_needed} 个文件(10条目/文件)完成Phase A")
    else:
        print("\nPhase A 完成！建议启动Phase B性能优化")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
