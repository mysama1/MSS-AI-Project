#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSS-AI Monitoring Dashboard v1.0
实时监控运行状态、性能指标、系统健康度
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class SystemMetrics:
    """系统运行指标"""
    timestamp: str
    total_requests: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    active_models: List[str] = field(default_factory=list)
    gpu_memory_used_mb: int = 0
    gpu_memory_total_mb: int = 0
    cache_hit_rate: float = 0.0
    queue_depth: int = 0


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: str  # 'gt', 'lt', 'eq'
    threshold: float
    metric: str
    severity: str  # 'warning', 'critical'
    message_template: str


class MonitoringDashboard:
    """监控面板"""
    
    def __init__(self, tactic_instance=None, max_history: int = 1000):
        """
        初始化监控面板
        
        Args:
            tactic_instance: MSSTactic实例（可选，用于获取运行时数据）
            max_history: 保留的最大历史记录数
        """
        self.tactic = tactic_instance
        self.metrics_history: deque = deque(maxlen=int(max_history))
        self.alerts: List[Dict] = []
        self.alert_rules: List[AlertRule] = self._default_rules()
        self.start_time = time.time()
        
        # 统计计数器
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _default_rules(self) -> List[AlertRule]:
        """默认告警规则"""
        return [
            AlertRule(
                name='low_success_rate',
                condition='lt',
                threshold=0.8,
                metric='success_rate',
                severity='critical',
                message_template='Success rate dropped to {value:.1%}, below threshold {threshold:.1%}'
            ),
            AlertRule(
                name='high_response_time',
                condition='gt',
                threshold=10.0,
                metric='avg_response_time',
                severity='warning',
                message_template='Average response time {value:.2f}s exceeds {threshold:.2f}s'
            ),
            AlertRule(
                name='gpu_memory_critical',
                condition='gt',
                threshold=0.95,
                metric='gpu_memory_ratio',
                severity='critical',
                message_template='GPU memory usage {value:.1%} approaching limit'
            ),
            AlertRule(
                name='queue_backlog',
                condition='gt',
                threshold=50,
                metric='queue_depth',
                severity='warning',
                message_template='Queue depth {value} exceeds {threshold}'
            ),
        ]
    
    def record_request(self, success: bool, response_time: float, cached: bool = False):
        """记录请求指标"""
        self.request_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        self.total_response_time += response_time
        
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def get_current_metrics(self, tactic_instance=None) -> SystemMetrics:
        """获取当前指标"""
        success_rate = self.success_count / max(self.request_count, 1)
        avg_time = self.total_response_time / max(self.request_count, 1)
        
        cache_total = self.cache_hits + self.cache_misses
        cache_rate = self.cache_hits / max(cache_total, 1)
        
        # GPU 状态
        gpu_used = 0
        gpu_total = 0
        active_models = []
        
        if tactic_instance and hasattr(tactic_instance, 'model_manager'):
            try:
                gpu_info = tactic_instance.model_manager.check_gpu_memory()
                if gpu_info:
                    gpu_used = gpu_info.get('used_mb', 0)
                    gpu_total = gpu_info.get('total_mb', 1)
            except:
                pass
            
            # 获取活跃模型
            try:
                models = tactic_instance.model_manager.list_models()
                active_models = [m.get('name', 'unknown') for m in models]
            except:
                pass
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            total_requests=self.request_count,
            success_rate=round(success_rate, 3),
            avg_response_time=round(avg_time, 3),
            active_models=active_models,
            gpu_memory_used_mb=gpu_used,
            gpu_memory_total_mb=gpu_total,
            cache_hit_rate=round(cache_rate, 3),
            queue_depth=0  # 当前版本未实现队列
        )
    
    def update(self, tactic_instance=None):
        """更新并保存当前指标"""
        metrics = self.get_current_metrics(tactic_instance)
        self.metrics_history.append(metrics)
        
        # 检查告警
        self._check_alerts(metrics)
        
        return metrics
    
    def _check_alerts(self, metrics: SystemMetrics):
        """检查告警条件"""
        for rule in self.alert_rules:
            value = self._get_metric_value(metrics, rule.metric)
            if value is None:
                continue
            
            triggered = False
            if rule.condition == 'gt' and value > rule.threshold:
                triggered = True
            elif rule.condition == 'lt' and value < rule.threshold:
                triggered = True
            elif rule.condition == 'eq' and value == rule.threshold:
                triggered = True
            
            if triggered:
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'rule': rule.name,
                    'severity': rule.severity,
                    'message': rule.message_template.format(
                        value=value,
                        threshold=rule.threshold
                    ),
                    'metric_value': value,
                    'threshold': rule.threshold
                }
                self.alerts.append(alert)
    
    def _get_metric_value(self, metrics: SystemMetrics, metric_name: str) -> Optional[float]:
        """获取指标值"""
        if metric_name == 'success_rate':
            return metrics.success_rate
        elif metric_name == 'avg_response_time':
            return metrics.avg_response_time
        elif metric_name == 'gpu_memory_ratio':
            return metrics.gpu_memory_used_mb / max(metrics.gpu_memory_total_mb, 1)
        elif metric_name == 'queue_depth':
            return metrics.queue_depth
        return None
    
    def get_health_score(self) -> Dict:
        """计算系统健康度评分"""
        if not self.metrics_history:
            return {'score': 0, 'status': 'unknown', 'components': {}}
        
        latest = self.metrics_history[-1]
        
        # 各组件评分 (0-1)
        components = {}
        
        # 成功率评分
        components['success_rate'] = latest.success_rate
        
        # 响应时间评分 (越快越好，超过30秒为0)
        response_score = max(0, 1 - latest.avg_response_time / 30)
        components['response_time'] = round(response_score, 3)
        
        # GPU 评分
        gpu_ratio = latest.gpu_memory_used_mb / max(latest.gpu_memory_total_mb, 1)
        gpu_score = 1 - gpu_ratio
        components['gpu_health'] = round(gpu_score, 3)
        
        # 缓存评分
        components['cache_efficiency'] = latest.cache_hit_rate
        
        # 综合评分 (加权平均)
        weights = {
            'success_rate': 0.4,
            'response_time': 0.2,
            'gpu_health': 0.2,
            'cache_efficiency': 0.2
        }
        
        total_score = sum(components[k] * weights[k] for k in weights)
        total_score = round(total_score, 3)
        
        # 状态判定
        if total_score >= 0.9:
            status = 'excellent'
        elif total_score >= 0.7:
            status = 'good'
        elif total_score >= 0.5:
            status = 'fair'
        else:
            status = 'critical'
        
        return {
            'score': total_score,
            'status': status,
            'components': components,
            'uptime_seconds': int(time.time() - self.start_time)
        }
    
    def render_text_dashboard(self, tactic_instance=None) -> str:
        """渲染文本模式监控面板"""
        metrics = self.update(tactic_instance)
        health = self.get_health_score()
        
        lines = [
            '=' * 60,
            '           MSS-AI Monitoring Dashboard',
            '=' * 60,
            f'Time: {metrics.timestamp}',
            f'Uptime: {health["uptime_seconds"]}s',
            '',
            '--- System Health ---',
            f'Overall Score: {health["score"]} ({health["status"].upper()})',
            f'  Success Rate:  {health["components"].get("success_rate", 0):.1%}',
            f'  Response Time: {health["components"].get("response_time", 0):.2f}',
            f'  GPU Health:    {health["components"].get("gpu_health", 0):.1%}',
            f'  Cache Hit:     {health["components"].get("cache_efficiency", 0):.1%}',
            '',
            '--- Current Metrics ---',
            f'Total Requests: {metrics.total_requests}',
            f'Success Rate:   {metrics.success_rate:.1%}',
            f'Avg Response:   {metrics.avg_response_time:.3f}s',
            f'GPU Memory:     {metrics.gpu_memory_used_mb}/{metrics.gpu_memory_total_mb} MB',
            f'Active Models:  {", ".join(metrics.active_models) or "None"}',
            '',
        ]
        
        # 最近告警
        recent_alerts = [a for a in self.alerts 
                        if time.time() - datetime.fromisoformat(a['timestamp']).timestamp() < 3600]
        
        if recent_alerts:
            lines.append('--- Recent Alerts (last hour) ---')
            for alert in recent_alerts[-5:]:  # 最近5条
                lines.append(f'[{alert["severity"].upper()}] {alert["message"]}')
            lines.append('')
        
        lines.append('=' * 60)
        
        return '\n'.join(lines)
    
    def render_compact_status(self) -> str:
        """渲染紧凑状态行"""
        if not self.metrics_history:
            return 'MSS-AI [Initializing...]'
        
        latest = self.metrics_history[-1]
        health = self.get_health_score()
        
        status_icon = {
            'excellent': '✓',
            'good': '○',
            'fair': '△',
            'critical': '✗'
        }.get(health['status'], '?')
        
        return (
            f'MSS-AI [{status_icon}] '
            f'Reqs:{latest.total_requests} '
            f'SR:{latest.success_rate:.0%} '
            f'RT:{latest.avg_response_time:.2f}s '
            f'GPU:{latest.gpu_memory_used_mb}MB'
        )
    
    def export_metrics(self, filepath: str, hours: int = 24):
        """导出指标历史到文件"""
        cutoff = time.time() - (hours * 3600)
        recent = [m for m in self.metrics_history 
                 if time.time() - datetime.fromisoformat(m.timestamp).timestamp() < cutoff]
        
        data = {
            'export_time': datetime.now().isoformat(),
            'period_hours': hours,
            'metrics_count': len(recent),
            'metrics': [
                {
                    'timestamp': m.timestamp,
                    'total_requests': m.total_requests,
                    'success_rate': m.success_rate,
                    'avg_response_time': m.avg_response_time,
                    'gpu_memory_used_mb': m.gpu_memory_used_mb,
                    'cache_hit_rate': m.cache_hit_rate
                }
                for m in recent
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_performance_report(self) -> Dict:
        """生成性能报告"""
        if not self.metrics_history:
            return {'error': 'No metrics data available'}
        
        # 计算趋势
        if len(self.metrics_history) >= 2:
            first = self.metrics_history[0]
            last = self.metrics_history[-1]
            
            time_span = (datetime.fromisoformat(last.timestamp) - 
                        datetime.fromisoformat(first.timestamp)).total_seconds()
            
            throughput = (last.total_requests - first.total_requests) / max(time_span, 1)
        else:
            throughput = 0
        
        # 统计分布
        response_times = [m.avg_response_time for m in self.metrics_history if m.avg_response_time > 0]
        
        return {
            'period': {
                'start': self.metrics_history[0].timestamp,
                'end': self.metrics_history[-1].timestamp,
                'records': len(self.metrics_history)
            },
            'throughput_rps': round(throughput, 3),
            'response_time': {
                'avg': round(sum(response_times) / len(response_times), 3) if response_times else 0,
                'min': round(min(response_times), 3) if response_times else 0,
                'max': round(max(response_times), 3) if response_times else 0,
            },
            'reliability': {
                'total_requests': self.request_count,
                'success_rate': round(self.success_count / max(self.request_count, 1), 3),
                'error_count': self.error_count
            },
            'health_history': [
                {'timestamp': m.timestamp, 'score': self._calculate_health_at(m)}
                for m in self.metrics_history
            ]
        }
    
    def _calculate_health_at(self, metrics: SystemMetrics) -> float:
        """计算特定时间点的健康度"""
        response_score = max(0, 1 - metrics.avg_response_time / 30)
        gpu_ratio = metrics.gpu_memory_used_mb / max(metrics.gpu_memory_total_mb, 1)
        gpu_score = 1 - gpu_ratio
        
        return round(
            metrics.success_rate * 0.4 +
            response_score * 0.2 +
            gpu_score * 0.2 +
            metrics.cache_hit_rate * 0.2,
            3
        )


# 便捷函数
def create_dashboard(max_history: int = 1000) -> MonitoringDashboard:
    """创建监控面板实例"""
    return MonitoringDashboard(max_history)


if __name__ == '__main__':
    # 简单演示
    dash = MonitoringDashboard()
    
    # 模拟一些请求
    for i in range(10):
        dash.record_request(success=True, response_time=0.5 + i * 0.1)
    
    dash.record_request(success=False, response_time=2.0)
    
    print(dash.render_text_dashboard())
    print()
    print(dash.render_compact_status())
