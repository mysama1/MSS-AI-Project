"""
MSS Organizational Resilience Visualizer
组织韧性扫描器可视化模块

生成: 雷达图、热力图、趋势对比图、报告导出(PDF/Markdown)
"""

import json
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import os

# 尝试导入matplotlib，如不可用则提供降级方案
try:
    import matplotlib
    matplotlib.use('Agg')  # 无GUI后端
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, visualizer will generate text-based reports only")

from organizational_resilience import (
    OrganizationalResilienceScanner, OrganizationSnapshot,
    DepartmentMetrics, DepartmentType, create_demo_organization
)

@dataclass
class VisualConfig:
    """可视化配置"""
    # 颜色方案 (MSS主题)
    colors = {
        'L1': '#2E86AB',      # 硬核蓝
        'L2': '#A23B72',      # 保护带紫
        'L3': '#F18F01',      # 试探法橙
        'critical': '#E63946', # 危险红
        'warning': '#F4A261',  # 警告黄
        'good': '#2A9D8F',     # 良好绿
        'neutral': '#264653',  # 中性灰蓝
    }

    # 字体配置
    font_family = 'SimHei'  # 中文黑体
    font_size = 12

    # 输出配置
    dpi = 150
    fig_size = (12, 8)

class ResilienceVisualizer:
    """组织韧性可视化器"""

    def __init__(self, config: Optional[VisualConfig] = None):
        self.config = config or VisualConfig()
        self.scanner = OrganizationalResilienceScanner()

        if MATPLOTLIB_AVAILABLE:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

    def generate_radar_chart(self, snapshot: OrganizationSnapshot,
                            output_path: Optional[str] = None) -> Optional[str]:
        """
        生成组织韧性雷达图

        维度: O_d(规范场强), phi(意义势能), gamma(热税),
              innovation(创新率), resilience(韧性指数)
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_text_radar(snapshot, output_path)

        # 准备数据
        categories = ['规范场强\n(O_d)', '意义势能\n(Φ)', '热税系数\n(γ)',
                     '创新率\n(R)', '韧性指数\n(M)']

        # 归一化到0-1范围
        values = [
            snapshot.global_O_d,  # 已经是0-1
            min(1.0, snapshot.global_phi / 200.0),  # phi max=200
            min(1.0, snapshot.global_gamma / 2.0),   # gamma typical max~2
            snapshot.global_innovation_rate,  # 已经是0-1
            snapshot.resilience_score  # 已经是0-1
        ]

        # 闭合雷达图
        values += values[:1]
        angles = [n / float(len(categories)) * 2 * math.pi for n in range(len(categories))]
        angles += angles[:1]

        # 创建图形
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

        # 绘制雷达图
        color = self._get_grade_color(snapshot.resilience_grade)
        ax.plot(angles, values, 'o-', linewidth=2, color=color, label='Current State')
        ax.fill(angles, values, alpha=0.25, color=color)

        # 添加参考线 (理想状态)
        ideal = [0.3, 0.8, 0.2, 0.7, 0.8]  # 理想值
        ideal += ideal[:1]
        ax.plot(angles, ideal, '--', linewidth=1, color='gray', alpha=0.5, label='Ideal')

        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=11)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], size=9)
        ax.grid(True)

        # 标题
        plt.title(f'组织韧性雷达图\n{snapshot.snapshot_id}\n'
                 f'韧性等级: {snapshot.resilience_grade} | M={snapshot.resilience_score}',
                 size=14, pad=20)

        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def generate_heatmap(self, snapshot: OrganizationSnapshot,
                        output_path: Optional[str] = None) -> Optional[str]:
        """
        生成部门指标热力图
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_text_heatmap(snapshot, output_path)

        # 准备数据
        dept_names = []
        metrics_matrix = []
        metric_labels = ['O_d', 'Φ', 'γ', 'R', 'M']

        for dept_id, metrics in snapshot.departments.items():
            dept_names.append(metrics.dept_name)
            row = [
                metrics.O_d,
                min(1.0, metrics.phi / 200.0),
                min(1.0, metrics.gamma / 2.0),
                metrics.innovation_rate,
                # 计算部门级韧性 (简化)
                (metrics.phi / 200.0) * (1 - metrics.O_d) * metrics.innovation_rate
            ]
            metrics_matrix.append(row)

        # 转置用于热力图
        metrics_matrix = list(zip(*metrics_matrix))

        fig, ax = plt.subplots(figsize=(max(10, len(dept_names) * 1.5), 6))

        im = ax.imshow(metrics_matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=1)

        # 设置标签
        ax.set_xticks(range(len(dept_names)))
        ax.set_xticklabels(dept_names, rotation=45, ha='right')
        ax.set_yticks(range(len(metric_labels)))
        ax.set_yticklabels(metric_labels)

        # 添加数值标注
        for i in range(len(metric_labels)):
            for j in range(len(dept_names)):
                text = ax.text(j, i, f'{metrics_matrix[i][j]:.2f}',
                             ha="center", va="center", color="black", fontsize=10)

        # 颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Normalized Score (0-1)', rotation=270, labelpad=20)

        plt.title(f'部门指标热力图 - {snapshot.snapshot_id}', size=14, pad=15)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def generate_trend_chart(self, history: List[OrganizationSnapshot],
                            output_path: Optional[str] = None) -> Optional[str]:
        """
        生成韧性趋势图 (需要历史数据)
        """
        if not MATPLOTLIB_AVAILABLE or len(history) < 2:
            return None

        timestamps = [s.timestamp[:10] for s in history]  # 只取日期
        scores = [s.resilience_score for s in history]
        grades = [s.resilience_grade for s in history]

        fig, ax = plt.subplots(figsize=(10, 6))

        # 绘制趋势线
        colors = [self._get_grade_color(g) for g in grades]
        ax.plot(timestamps, scores, 'o-', linewidth=2, markersize=8, color='#2E86AB')

        # 添加等级背景色
        for i, (ts, score, grade) in enumerate(zip(timestamps, scores, grades)):
            ax.scatter(ts, score, color=self._get_grade_color(grade), s=100, zorder=5)
            ax.annotate(grade, (ts, score), textcoords="offset points",
                       xytext=(0, 10), ha='center', fontsize=10, fontweight='bold')

        # 参考线
        ax.axhline(y=0.8, color='green', linestyle='--', alpha=0.5, label='High (A)')
        ax.axhline(y=0.5, color='orange', linestyle='--', alpha=0.5, label='Medium (B)')
        ax.axhline(y=0.3, color='red', linestyle='--', alpha=0.5, label='Low (C)')

        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Resilience Score (M)', fontsize=12)
        ax.set_title('组织韧性趋势追踪', fontsize=14)
        ax.set_ylim(0, 1)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.xticks(rotation=45)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def generate_markdown_report(self, snapshot: OrganizationSnapshot,
                                 output_path: Optional[str] = None) -> str:
        """
        生成Markdown格式报告
        """
        report = f"""# 组织韧性扫描报告

**扫描ID:** {snapshot.snapshot_id}
**扫描时间:** {snapshot.timestamp}
**MSS框架版本:** v15.1

---

## 一、全局指标概览

| 指标 | 数值 | 状态 | 说明 |
|:-----|:-----|:-----|:-----|
| 规范场强 O_d | {snapshot.global_O_d:.4f} | {'🟢' if snapshot.global_O_d < 0.4 else '🟡' if snapshot.global_O_d < 0.6 else '🔴'} | {'正常' if snapshot.global_O_d < 0.4 else '偏高' if snapshot.global_O_d < 0.6 else '危险'} |
| 意义势能 Φ | {snapshot.global_phi:.2f} | {'🟢' if snapshot.global_phi > 80 else '🟡' if snapshot.global_phi > 50 else '🔴'} | {'充足' if snapshot.global_phi > 80 else '偏低' if snapshot.global_phi > 50 else '严重不足'} |
| 热税系数 γ | {snapshot.global_gamma:.4f} | {'🟢' if snapshot.global_gamma < 0.5 else '🟡' if snapshot.global_gamma < 1.0 else '🔴'} | 组织熵增速率 |
| 创新率 R | {snapshot.global_innovation_rate:.4f} | {'🟢' if snapshot.global_innovation_rate > 0.3 else '🟡' if snapshot.global_innovation_rate > 0.1 else '🔴'} | {'活跃' if snapshot.global_innovation_rate > 0.3 else '不足'} |
| **韧性指数 M** | **{snapshot.resilience_score:.4f}** | **{'🟢 A' if snapshot.resilience_grade == 'A' else '🟡 B' if snapshot.resilience_grade == 'B' else '🟠 C' if snapshot.resilience_grade == 'C' else '🔴 D'}** | **{'自适应进化态' if snapshot.resilience_grade == 'A' else '稳态运行' if snapshot.resilience_grade == 'B' else '预警状态' if snapshot.resilience_grade == 'C' else '热寂临界'}** |

---

## 二、部门明细

"""

        for dept_id, metrics in snapshot.departments.items():
            dept_score = (metrics.phi / 200.0) * (1 - metrics.O_d) * metrics.innovation_rate
            report += f"""### {metrics.dept_name} ({metrics.dept_type.name})

| K3指标 | 数值 | K3指标 | 数值 |
|:-------|:-----|:-------|:-----|
| 人数 | {metrics.headcount} | 审批层级 | {metrics.approval_layers} |
| 周会议时长 | {metrics.meeting_hours_weekly}h | 项目交付周期 | {metrics.project_lead_time}天 |
| 员工满意度 | {metrics.employee_satisfaction}/10 | — | — |

**L1符号指标:**
- 规范场强 O_d = {metrics.O_d:.4f}
- 意义势能 Φ = {metrics.phi:.2f}
- 热税系数 γ = {metrics.gamma:.4f}
- 创新率 R = {metrics.innovation_rate:.4f}
- 部门韧性 M_dept ≈ {dept_score:.4f}

---

"""

        report += """## 三、诊断结果

"""

        if snapshot.diagnosis:
            for diag in snapshot.diagnosis:
                level_emoji = {'CRITICAL': '🔴', 'WARNING': '🟡', 'INFO': '🔵'}.get(diag['level'], '⚪')
                report += f"""### {level_emoji} [{diag['level']}] {diag['category']}

- **指标:** {diag['metric']}
- **描述:** {diag['description']}
- **MSS参考:** {diag['mss_reference']}

"""
        else:
            report += "✅ 未发现明显异常\n\n"

        report += """---

## 四、改进建议

"""

        for i, rec in enumerate(snapshot.recommendations, 1):
            report += f"{i}. {rec}\n"

        report += f"""

---

## 五、MSS理论框架

**扫描方法论:** K3可观测指标 → L1符号映射
**核心公理:** A1(意义本体) + A2(终极热税) + A3(随机性)
**参考定理:** T1(信息涌现) + T2(规范场涌现) + T3(矛盾升维)

---

*报告生成时间: {datetime.now().isoformat()}*
*MSS-AI Organizational Resilience Scanner v1.0*
"""

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            return output_path

        return report

    def generate_report(self, snapshot: OrganizationSnapshot,
                        output_dir: str = "resilience_reports") -> Dict[str, str]:
        """
        生成完整报告包 (Markdown + 图表)
        兼容旧API: generate_report() 是 generate_full_report_package() 的别名
        """
        return self.generate_full_report_package(snapshot, output_dir)

    def generate_full_report_package(self, snapshot: OrganizationSnapshot,
                                     output_dir: str = "resilience_reports") -> Dict[str, str]:
        """
        生成完整报告包 (Markdown + 图表)
        """
        os.makedirs(output_dir, exist_ok=True)
        base_name = snapshot.snapshot_id.replace("-", "_")

        files = {}

        # Markdown报告
        md_path = os.path.join(output_dir, f"{base_name}_report.md")
        files['markdown'] = self.generate_markdown_report(snapshot, md_path)

        # 雷达图
        if MATPLOTLIB_AVAILABLE:
            radar_path = os.path.join(output_dir, f"{base_name}_radar.png")
            files['radar'] = self.generate_radar_chart(snapshot, radar_path)

            # 热力图
            heatmap_path = os.path.join(output_dir, f"{base_name}_heatmap.png")
            files['heatmap'] = self.generate_heatmap(snapshot, heatmap_path)

        # JSON原始数据
        json_path = os.path.join(output_dir, f"{base_name}_data.json")
        self.scanner.export_report(snapshot, json_path)
        files['json'] = json_path

        return files

    def _get_grade_color(self, grade: str) -> str:
        """根据等级获取颜色"""
        return {
            'A': self.config.colors['good'],
            'B': '#2E86AB',
            'C': self.config.colors['warning'],
            'D': self.config.colors['critical']
        }.get(grade, self.config.colors['neutral'])

    def _generate_text_radar(self, snapshot: OrganizationSnapshot,
                            output_path: Optional[str] = None) -> str:
        """文本版雷达图 (matplotlib不可用时降级)"""
        lines = [
            "=" * 60,
            "组织韧性雷达图 (文本版)",
            "=" * 60,
            "",
            f"扫描ID: {snapshot.snapshot_id}",
            f"韧性等级: {snapshot.resilience_grade} | M={snapshot.resilience_score:.4f}",
            "",
            "维度评分 (0-1):",
            f"  规范场强  O_d: {'█' * int(snapshot.global_O_d * 20):<20} {snapshot.global_O_d:.4f}",
            f"  意义势能  Φ:   {'█' * int(min(1.0, snapshot.global_phi/200) * 20):<20} {snapshot.global_phi:.2f}",
            f"  热税系数  γ:   {'█' * int(min(1.0, snapshot.global_gamma/2) * 20):<20} {snapshot.global_gamma:.4f}",
            f"  创新率    R:   {'█' * int(snapshot.global_innovation_rate * 20):<20} {snapshot.global_innovation_rate:.4f}",
            f"  韧性指数  M:   {'█' * int(snapshot.resilience_score * 20):<20} {snapshot.resilience_score:.4f}",
            "",
            "理想参考: O_d<0.3, Φ>80, γ<0.5, R>0.7, M>0.8",
            "=" * 60
        ]

        text = "\n".join(lines)

        if output_path:
            with open(output_path.replace('.png', '.txt'), 'w', encoding='utf-8') as f:
                f.write(text)

        return text

    def _generate_text_heatmap(self, snapshot: OrganizationSnapshot,
                              output_path: Optional[str] = None) -> str:
        """文本版热力图"""
        lines = [
            "=" * 80,
            "部门指标热力图 (文本版)",
            "=" * 80,
            "",
            f"{'部门':<12} {'O_d':>8} {'Φ':>8} {'γ':>8} {'R':>8} {'M':>8}",
            "-" * 80
        ]

        for dept_id, metrics in snapshot.departments.items():
            dept_score = (metrics.phi / 200.0) * (1 - metrics.O_d) * metrics.innovation_rate
            lines.append(
                f"{metrics.dept_name:<12} {metrics.O_d:>8.4f} {metrics.phi:>8.2f} "
                f"{metrics.gamma:>8.4f} {metrics.innovation_rate:>8.4f} {dept_score:>8.4f}"
            )

        lines.extend(["=" * 80, "", "说明: O_d(规范场强) Φ(意义势能) γ(热税) R(创新率) M(韧性)"])

        text = "\n".join(lines)

        if output_path:
            with open(output_path.replace('.png', '.txt'), 'w', encoding='utf-8') as f:
                f.write(text)

        return text

def demo_visualization():
    """演示可视化功能"""
    print("=" * 70)
    print("MSS Organizational Resilience Visualizer Demo")
    print("=" * 70)
    print()

    # 创建扫描器和可视化器
    scanner = OrganizationalResilienceScanner()
    visualizer = ResilienceVisualizer()

    # 演示数据
    org_data = create_demo_organization()

    print(f"Scanning: {org_data['org_name']}")
    snapshot = scanner.scan_organization(org_data)
    print(f"Resilience Score: {snapshot.resilience_score} (Grade {snapshot.resilience_grade})")
    print()

    # 生成完整报告包
    print("Generating full report package...")
    files = visualizer.generate_full_report_package(snapshot)

    print("\nGenerated files:")
    for file_type, path in files.items():
        if path:
            print(f"  [{file_type}] {path}")

    # 打印Markdown报告预览
    print("\n" + "=" * 70)
    print("MARKDOWN REPORT PREVIEW")
    print("=" * 70)
    md_report = visualizer.generate_markdown_report(snapshot)
    print(md_report[:1500] + "\n... [truncated]")

    return files

if __name__ == "__main__":
    demo_visualization()
