#!/usr/bin/env python3
"""
DEV-202: Memory Leak Detector
Wraps tracemalloc + objgraph for runtime leak detection.
Produces VDP-compatible violation reports.
"""
import sys, os, json, time, gc
import tracemalloc

class MemoryProfiler:
    """Lightweight runtime memory leak detector."""
    
    def __init__(self, top_n: int = 10, threshold_kb: int = 100):
        self.top_n = top_n
        self.threshold_kb = threshold_kb
        self._snapshots = {}
        self._started = False
    
    def start(self):
        tracemalloc.start()
        self._snapshots['start'] = tracemalloc.take_snapshot()
        self._started = True
    
    def checkpoint(self, label: str):
        if not self._started:
            self.start()
        self._snapshots[label] = tracemalloc.take_snapshot()
    
    def stop(self) -> dict:
        if not self._started:
            return {'error': 'Profiler not started'}
        tracemalloc.stop()
        return self.report()
    
    def report(self) -> dict:
        """Generate VDP-compatible memory leak report."""
        snapshots = list(self._snapshots.items())
        violations = []
        
        for i in range(len(snapshots) - 1):
            name_a, snap_a = snapshots[i]
            name_b, snap_b = snapshots[i + 1]
            
            stats = snap_b.compare_to(snap_a, 'lineno')
            top_leaks = [s for s in stats if s.size_diff > 0][:self.top_n]
            
            for s in top_leaks:
                if s.size_diff > self.threshold_kb * 1024:
                    violations.append({
                        'rule_id': 'M1_GROWTH',
                        'severity': 'reject' if s.size_diff > 1024 * 1024 else 'warn',
                        'loc': f'{s.traceback}',
                        'kind': 'memory_growth',
                        'detail': f'{name_a}→{name_b}: +{s.size_diff/1024:.0f}KB ({s.count_diff} new objects)',
                    })
        
        # Check for objects persisting across all snapshots
        if len(snapshots) >= 2:
            first = snapshots[0][1]
            last = snapshots[-1][1]
            diff = last.compare_to(first, 'lineno')
            leaked = [s for s in diff if s.count_diff == s.count and s.count > 5]
            
            for s in leaked[:self.top_n]:
                if s.size > self.threshold_kb * 1024:
                    violations.append({
                        'rule_id': 'M2_PERSIST',
                        'severity': 'warn',
                        'loc': f'{s.traceback}',
                        'kind': 'persistent_objects',
                        'detail': f'{s.count} objects ({s.size/1024:.0f}KB) persisted from start to end — potential leak',
                    })
        
        # GC stats
        gc.collect()
        gc_stats = {
            'generations': gc.get_count(),
            'collectable': len(gc.get_objects()),
            'thresholds': gc.get_threshold(),
        }
        
        total_growth_kb = 0
        for i in range(len(snapshots) - 1):
            diff = snapshots[i+1][1].compare_to(snapshots[i][1], 'lineno')
            total_growth_kb += sum(s.size_diff for s in diff) / 1024
        
        return {
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
            'violations': violations,
            'summary': {
                'snapshots': len(snapshots),
                'threshold_kb': self.threshold_kb,
                'total_growth_kb': round(total_growth_kb, 1),
                'top_n': min(self.top_n, len(violations)),
                'gc_collectable': gc_stats['collectable'],
            },
            'snapshot_labels': [s[0] for s in snapshots],
        }


def profile_block(code_block: str, checkpoints: list = None) -> dict:
    """Profile a code block with automatic checkpoints."""
    mp = MemoryProfiler()
    mp.start()
    
    local_vars = {}
    exec(code_block, {'__builtins__': __builtins__, 'time': time, 'gc': gc}, local_vars)
    
    if checkpoints:
        for label in checkpoints:
            mp.checkpoint(label)
    else:
        mp.checkpoint('end')
    
    gc.collect()
    return mp.stop()


def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS-VDP Memory Leak Detector')
    ap.add_argument('--demo', action='store_true', help='Run demo leak')
    ap.add_argument('--json', action='store_true', help='JSON output')
    ap.add_argument('--threshold', type=int, default=100, help='Threshold in KB')
    args = ap.parse_args()
    
    if args.demo or True:
        # Demonstrate memory leak detection
        mp = MemoryProfiler(threshold_kb=10)
        mp.start()
        
        # Create some allocations
        data = []
        for i in range(1000):
            data.append('x' * 1000)  # ~1KB each
        mp.checkpoint('after_load')
        
        # Simulate leak: hold onto data
        _leaked = data  # noqa
        
        time.sleep(0.5)
        mp.checkpoint('after_hold')
        
        # Clean up and check
        data.clear()
        gc.collect()
        mp.checkpoint('after_cleanup')
        
        report = mp.stop()
        
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"\nMemory Leak Report ({report['summary']['snapshots']} snapshots)")
            print(f"Growth: {report['summary']['total_growth_kb']}KB")
            print(f"Collectable: {report['summary']['gc_collectable']} objects")
            if report['violations']:
                print(f"\nViolations: {len(report['violations'])}")
                for v in report['violations']:
                    print(f"  [{v['severity']}] {v['rule_id']}: {v['detail'][:100]}")
            else:
                print("  No leak violations detected")


if __name__ == '__main__':
    main()
