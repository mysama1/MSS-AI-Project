"""Memory Boundary Test 鈥?2000脳2000 grid simulation"""

import numpy as np
import os
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

class MemoryBoundaryTest:
    """鍐呭瓨杈圭晫娴嬭瘯鍣?""

    def __init__(self):
        if HAS_PSUTIL:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
        self.results = []

    def get_memory_usage(self):
        """鑾峰彇褰撳墠鍐呭瓨浣跨敤"""
        if not HAS_PSUTIL:
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0, 'available_mb': 0}

        return {
            'rss_mb': self.process.memory_info().rss / 1024 / 1024,
            'vms_mb': self.process.memory_info().vms / 1024 / 1024,
            'percent': psutil.virtual_memory().percent,
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
        }

    def test_grid_size(self, grid_size):
        """娴嬭瘯鎸囧畾缃戞牸澶у皬"""
        print(f"\n[TEST] Grid size: {grid_size}脳{grid_size}")

        # 璁板綍娴嬭瘯鍓嶅唴瀛?
        mem_before = self.get_memory_usage()
        print(f"  Memory before: {mem_before['rss_mb']:.1f} MB")

        try:
            # 鍒涘缓缃戞牸
            grid = np.zeros((grid_size, grid_size), dtype=np.float64)

            # 妯℃嫙璁＄畻锛堟笚娴佹ā鎷熺畝鍖栫増锛?
            grid[:] = np.random.random((grid_size, grid_size))
            grid = grid > 0.5927  # 娓楁祦闃堝€?

            # 鏍囪杩為€氬尯鍩?
            labeled = self._label_connected(grid)

            # 璁板綍娴嬭瘯鍚庡唴瀛?
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
            print(f"  Status: 鉁?PASS")

        except MemoryError:
            result = {
                'grid_size': grid_size,
                'status': 'FAIL',
                'error': 'MemoryError',
                'timestamp': datetime.now().isoformat(),
            }
            print(f"  Status: 鉂?FAIL - MemoryError")

        self.results.append(result)
        return result

    def _label_connected(self, grid):
        """鏍囪杩為€氬尯鍩燂紙绠€鍖栫増锛?""
        from scipy import ndimage
        labeled, num_features = ndimage.label(grid)
        return labeled

    def run_boundary_tests(self):
        """杩愯杈圭晫娴嬭瘯搴忓垪"""
        print("="*60)
        print("MEMORY BOUNDARY TEST SUITE")
        print("="*60)

        test_sizes = [100, 500, 1000, 1500, 2000, 2500]

        for size in test_sizes:
            result = self.test_grid_size(size)

            if result['status'] == 'FAIL':
                print(f"\n鈿狅笍 Memory limit reached at {size}脳{size}")
                break

            # 妫€鏌ユ槸鍚︽帴杩戝唴瀛橀檺鍒讹紙鏃爌sutil鏃惰烦杩囷級
            if HAS_PSUTIL and result.get('available_mb', 0) < 500:
                print(f"\n鈿狅笍 Approaching memory limit")
                break

        return self._generate_report()

    def _generate_report(self):
        """鐢熸垚娴嬭瘯鎶ュ憡"""
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
            print(f"Max successful grid: {max_grid}脳{max_grid}")

        # 淇濆瓨璇︾粏鎶ュ憡鍒版枃浠?
        report_file = "E:\\AI_Workspace\\MSS-AI\\project\\mem_boundary_report.json"
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
