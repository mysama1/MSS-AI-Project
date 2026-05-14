#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSS-AI Batch Processor v1.0
支持文件/目录批量分析、结果聚合、报告生成
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class BatchResult:
    """单个文件的分析结果"""
    file_path: str
    status: str  # 'success', 'error', 'skipped'
    score: Optional[float] = None
    layer: Optional[str] = None
    issues: Optional[List[Dict]] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class BatchSummary:
    """批量处理汇总报告"""
    total_files: int
    success_count: int
    error_count: int
    skipped_count: int
    avg_score: float
    score_distribution: Dict[str, int]
    layer_distribution: Dict[str, int]
    total_processing_time: float
    timestamp: str


class BatchProcessor:
    """批量内容分析处理器"""
    
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.py', '.json', '.yaml', '.yml', '.csv'}
    
    def __init__(self, tactic_instance):
        """
        初始化批量处理器
        
        Args:
            tactic_instance: MSSTactic 实例
        """
        self.tactic = tactic_instance
        self.results: List[BatchResult] = []
        self.progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """设置进度回调函数 (current, total, message)"""
        self.progress_callback = callback
    
    def _read_file(self, file_path: str) -> Optional[str]:
        """读取文件内容，支持多种编码"""
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                return None
        
        return None
    
    def _is_supported_file(self, file_path: str) -> bool:
        """检查文件类型是否支持"""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    def _notify_progress(self, current: int, total: int, message: str):
        """通知进度更新"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def process_file(self, file_path: str, claimed_layer: Optional[str] = None) -> BatchResult:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            claimed_layer: 声称的理论层级
            
        Returns:
            BatchResult 分析结果
        """
        start_time = time.time()
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return BatchResult(
                file_path=file_path,
                status='error',
                error_message='File not found',
                processing_time=time.time() - start_time
            )
        
        # 检查文件类型
        if not self._is_supported_file(file_path):
            return BatchResult(
                file_path=file_path,
                status='skipped',
                error_message=f'Unsupported file type: {Path(file_path).suffix}',
                processing_time=time.time() - start_time
            )
        
        # 读取内容
        content = self._read_file(file_path)
        if content is None:
            return BatchResult(
                file_path=file_path,
                status='error',
                error_message='Failed to read file (encoding issues)',
                processing_time=time.time() - start_time
            )
        
        # 内容为空检查
        if not content.strip():
            return BatchResult(
                file_path=file_path,
                status='skipped',
                error_message='Empty file',
                processing_time=time.time() - start_time
            )
        
        # 执行分析
        try:
            result = self.tactic.analyze(content, claimed_layer=claimed_layer)
            
            return BatchResult(
                file_path=file_path,
                status='success',
                score=result.get('overall_score'),
                layer=result.get('detected_layer'),
                issues=result.get('issues', []),
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return BatchResult(
                file_path=file_path,
                status='error',
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def process_directory(
        self, 
        directory: str, 
        recursive: bool = True,
        claimed_layer: Optional[str] = None,
        file_pattern: Optional[str] = None
    ) -> List[BatchResult]:
        """
        批量处理目录
        
        Args:
            directory: 目标目录
            recursive: 是否递归子目录
            claimed_layer: 声称的理论层级
            file_pattern: 文件匹配模式 (如 '*.md')
            
        Returns:
            List[BatchResult] 所有文件的分析结果
        """
        self.results = []
        
        # 收集文件列表
        files = []
        dir_path = Path(directory)
        
        if recursive:
            pattern = file_pattern or '*'
            files = list(dir_path.rglob(pattern))
        else:
            pattern = file_pattern or '*'
            files = list(dir_path.glob(pattern))
        
        # 过滤只保留文件（排除目录）和支持的类型
        files = [f for f in files if f.is_file() and self._is_supported_file(str(f))]
        
        total = len(files)
        self._notify_progress(0, total, f'Found {total} files to process')
        
        # 逐个处理
        for i, file_path in enumerate(files, 1):
            str_path = str(file_path)
            self._notify_progress(i, total, f'Processing: {file_path.name}')
            
            result = self.process_file(str_path, claimed_layer)
            self.results.append(result)
        
        self._notify_progress(total, total, 'Batch processing complete')
        return self.results
    
    def process_file_list(
        self, 
        file_paths: List[str],
        claimed_layer: Optional[str] = None
    ) -> List[BatchResult]:
        """
        批量处理文件列表
        
        Args:
            file_paths: 文件路径列表
            claimed_layer: 声称的理论层级
            
        Returns:
            List[BatchResult] 分析结果
        """
        self.results = []
        total = len(file_paths)
        
        self._notify_progress(0, total, f'Processing {total} files')
        
        for i, file_path in enumerate(file_paths, 1):
            self._notify_progress(i, total, f'Processing: {os.path.basename(file_path)}')
            
            result = self.process_file(file_path, claimed_layer)
            self.results.append(result)
        
        self._notify_progress(total, total, 'Batch processing complete')
        return self.results
    
    def generate_summary(self) -> BatchSummary:
        """生成处理汇总报告"""
        if not self.results:
            return BatchSummary(
                total_files=0, success_count=0, error_count=0, 
                skipped_count=0, avg_score=0.0,
                score_distribution={}, layer_distribution={},
                total_processing_time=0.0, timestamp=datetime.now().isoformat()
            )
        
        total = len(self.results)
        success = sum(1 for r in self.results if r.status == 'success')
        errors = sum(1 for r in self.results if r.status == 'error')
        skipped = sum(1 for r in self.results if r.status == 'skipped')
        
        # 分数分布
        scores = [r.score for r in self.results if r.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        score_dist = {
            'excellent (0.9-1.0)': sum(1 for s in scores if 0.9 <= s <= 1.0),
            'good (0.7-0.9)': sum(1 for s in scores if 0.7 <= s < 0.9),
            'acceptable (0.5-0.7)': sum(1 for s in scores if 0.5 <= s < 0.7),
            'poor (0.3-0.5)': sum(1 for s in scores if 0.3 <= s < 0.5),
            'critical (<0.3)': sum(1 for s in scores if s < 0.3),
        }
        
        # 层级分布
        layers = {}
        for r in self.results:
            if r.layer:
                layers[r.layer] = layers.get(r.layer, 0) + 1
        
        total_time = sum(r.processing_time for r in self.results)
        
        return BatchSummary(
            total_files=total,
            success_count=success,
            error_count=errors,
            skipped_count=skipped,
            avg_score=round(avg_score, 3),
            score_distribution=score_dist,
            layer_distribution=layers,
            total_processing_time=round(total_time, 2),
            timestamp=datetime.now().isoformat()
        )
    
    def export_results(self, output_path: str, format: str = 'json'):
        """
        导出结果到文件
        
        Args:
            output_path: 输出文件路径
            format: 输出格式 ('json', 'csv', 'markdown')
        """
        if format == 'json':
            data = {
                'summary': asdict(self.generate_summary()),
                'results': [asdict(r) for r in self.results]
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        elif format == 'markdown':
            summary = self.generate_summary()
            lines = [
                '# MSS-AI Batch Analysis Report',
                f'\nGenerated: {summary.timestamp}',
                f'\n## Summary',
                f'- Total files: {summary.total_files}',
                f'- Success: {summary.success_count}',
                f'- Errors: {summary.error_count}',
                f'- Skipped: {summary.skipped_count}',
                f'- Average score: {summary.avg_score}',
                f'- Total time: {summary.total_processing_time}s',
                '\n## Score Distribution',
            ]
            for range_name, count in summary.score_distribution.items():
                lines.append(f'- {range_name}: {count}')
            
            lines.append('\n## Layer Distribution')
            for layer, count in summary.layer_distribution.items():
                lines.append(f'- {layer}: {count}')
            
            lines.append('\n## Detailed Results')
            lines.append('| File | Status | Score | Layer | Time |')
            lines.append('|------|--------|-------|-------|------|')
            
            for r in self.results:
                score_str = f'{r.score:.3f}' if r.score else 'N/A'
                layer_str = r.layer or 'N/A'
                lines.append(f'| {os.path.basename(r.file_path)} | {r.status} | {score_str} | {layer_str} | {r.processing_time:.2f}s |')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
    
    def get_high_risk_files(self, threshold: float = 0.5) -> List[BatchResult]:
        """获取高风险文件（分数低于阈值）"""
        return [r for r in self.results 
                if r.status == 'success' and r.score is not None and r.score < threshold]
    
    def get_layer_mismatches(self) -> List[BatchResult]:
        """获取层级不匹配的结果（需要 claimed_layer 参数）"""
        # 注：此功能需要扩展 BatchResult 记录 claimed_layer
        # 当前版本预留接口
        return []


# 便捷函数
def quick_batch_analyze(
    directory: str,
    output_file: Optional[str] = None,
    recursive: bool = True,
    claimed_layer: Optional[str] = None
) -> BatchSummary:
    """
    快速批量分析目录
    
    Args:
        directory: 目标目录
        output_file: 可选的输出文件路径
        recursive: 是否递归
        claimed_layer: 声称的理论层级
        
    Returns:
        BatchSummary 汇总报告
    """
    from mss_tactic_integrated import MSSTactic
    
    tactic = MSSTactic()
    processor = BatchProcessor(tactic)
    
    # 设置简单进度打印
    def print_progress(current, total, message):
        print(f'[{current}/{total}] {message}')
    
    processor.set_progress_callback(print_progress)
    processor.process_directory(directory, recursive, claimed_layer)
    
    summary = processor.generate_summary()
    
    if output_file:
        processor.export_results(output_file, format='markdown')
        print(f'Report saved to: {output_file}')
    
    return summary


if __name__ == '__main__':
    # 简单测试
    print('Batch Processor v1.0 loaded')
    print('Supported formats:', BatchProcessor.SUPPORTED_EXTENSIONS)
