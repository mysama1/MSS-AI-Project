"""Memory Boundary Test — 2000×2000 grid simulation"""

import numpy as np
import os
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

class MemoryBoundaryTest:
    """内存边界测试器"""
    
    def __init__(self):
        if HAS_PSUTIL:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
        self.results = []
    
    def get_memory_usage(self):
        """获取当前内存使用"""
        if not HAS_PSUTIL:
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0, 'available_mb': 0}
        
        return {
            'rss_mb': self.process.memory_info().rss / 1024 / 1024,
            'vms_mb': self.process.memory_info().vms / 1024 / 1024,
            'percent': psutil.virtual_memory().percent,
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
        }
    
    def test_grid_size(self, grid_size):
        """测试指定网格大小"""
        print(f"\n[TEST] Grid size: {grid_size}×{grid_size}")
        
        # 记录测试前内存
        mem_before = self.get_memory_usage()
        print(f"  Memory before: {mem_before['rss_mb']:.1f} MB")
        
        try:
            # 创建网格
            grid = np.zeros((grid_size, grid_size), dtype=np.float64)
            
            # 模拟计算（渗流模拟简化版）
            grid[:] = np.random.random((grid_size, grid_size))
            grid = grid > 0.5927  # 渗流阈值
            
            # 标记连通区域
            labeled = self._label_connected(grid)
            
            # 记录测试后内存
            mem_after = self.get_memory_usage()
            mem_used = mem_after['rss_mb'] - mem_before['rss_mb']
            
            result = {
                'grid_size': grid_size,
                'memory_used_mb': mem_used,
                'memory_after_mb': mem_after['rss_mb'],
                'available_mb': mem_after['available_mb'],
                'status': 'PASS',
                'timestamp': datetime.now().isoformat(),
            }
            
            print(f"  Memory used: {mem_used:.1f} MB")
            print(f"  Memory after: {mem_after['rss_mb']:.1f} MB")
            print(f"  Available: {mem_after['available_mb']:.1f} MB")
            print(f"  Status: ✅ PASS")
            
        except MemoryError:
            result = {
                'grid_size': grid_size,
                'status': 'FAIL',
                'error': 'MemoryError',
                'timestamp': datetime.now().isoformat(),
            }
            print(f"  Status: ❌ FAIL - MemoryError")
        
        self.results.append(result)
        return result
    
    def _label_connected(self, grid):
        """标记连通区域（简化版）"""
        from scipy import ndimage
        labeled, num_features = ndimage.label(grid)
        return labeled
    
    def run_boundary_tests(self):
        """运行边界测试序列"""
        print("="*60)
        print("MEMORY BOUNDARY TEST SUITE")
        print("="*60)
        
        test_sizes = [100, 500, 1000, 1500, 2000, 2500]
        
        for size in test_sizes:
            result = self.test_grid_size(size)
            
            if result['status'] == 'FAIL':
                print(f"\n⚠️ Memory limit reached at {size}×{size}")
                break
            
            # 检查是否接近内存限制（无psutil时跳过）
            if HAS_PSUTIL and result.get('available_mb', 0) < 500:
                print(f"\n⚠️ Approaching memory limit")
                break
        
        return self._generate_report()
    
    def _generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        
        print(f"Total tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if self.results:
            max_grid = max(r['grid_size'] for r in self.results if r['status'] == 'PASS')
            print(f"Max successful grid: {max_grid}×{max_grid}")
        
        # 保存详细报告到文件
        report_file = "C:\\MSS-AI-Project\\mem_boundary_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {'total': len(self.results), 'passed': passed, 'failed': failed},
                'results': self.results,
            }, f, indent=2)
        
        print(f"\nDetailed report: {report_file}")
        
        return {'passed': passed, 'failed': failed, 'total': len(self.results)}


if __name__ == "__main__":
    import json
    
    tester = MemoryBoundaryTest()
    result = tester.run_boundary_tests()
    
    print(f"\n[FINAL] {result['passed']}/{result['total']} tests passed")
