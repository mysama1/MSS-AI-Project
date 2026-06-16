#!/usr/bin/env python3
"""
DEV-102: Runtime Lock Contention Profiler
Monkey-patch threading primitives → profile → report VDP-compatible violations.
"""
import threading
import time
import json
import sys
import os
from collections import defaultdict
from typing import Dict, List, Optional


class LockStats:
    """Per-lock contention statistics."""
    __slots__ = ('name', 'acquires', 'contended', 'wait_time', 'hold_time',
                 'deadlock_risk', 'max_wait', 'max_hold')
    
    def __init__(self, name: str):
        self.name = name
        self.acquires = 0
        self.contended = 0       # Acquires that had to wait
        self.wait_time = 0.0      # Total time spent waiting (seconds)
        self.hold_time = 0.0      # Total time holding the lock
        self.deadlock_risk = 0    # Nested acquires on same thread (potential deadlock)
        self.max_wait = 0.0
        self.max_hold = 0.0
    
    def to_dict(self):
        return {
            'name': self.name,
            'acquires': self.acquires,
            'contended': self.contended,
            'contention_rate': round(self.contended / max(self.acquires, 1), 3),
            'total_wait_seconds': round(self.wait_time, 4),
            'total_hold_seconds': round(self.hold_time, 4),
            'avg_wait_ms': round(self.wait_time / max(self.contended, 1) * 1000, 2),
            'max_wait_ms': round(self.max_wait * 1000, 2),
            'avg_hold_ms': round(self.hold_time / max(self.acquires, 1) * 1000, 2),
            'max_hold_ms': round(self.max_hold * 1000, 2),
            'deadlock_risk': self.deadlock_risk,
        }


class ProfiledLock:
    """Drop-in replacement for threading.Lock with profiling."""
    
    def __init__(self, name: str = None):
        self._lock = _original_lock()
        self._name = name or f"Lock@{id(self):x}"
        self._stats = LockStats(self._name)
        Profiler.register(self)
    
    def acquire(self, blocking=True, timeout=-1):
        t0 = time.perf_counter()
        result = self._lock.acquire(blocking, timeout)
        t1 = time.perf_counter()
        
        self._stats.acquires += 1
        wait = t1 - t0
        
        if wait > 0.001:  # More than 1ms wait = contended
            self._stats.contended += 1
            self._stats.wait_time += wait
            self._stats.max_wait = max(self._stats.max_wait, wait)
        
        if result:
            self._acquire_time = t1
            # Deadlock risk: check if current thread holds multiple locks
            tid = threading.get_ident()
            held = Profiler._thread_locks.get(tid, set())
            if held:
                self._stats.deadlock_risk += 1
            held.add(self._name)
            Profiler._thread_locks[tid] = held
        
        return result
    
    def release(self):
        hold_time = time.perf_counter() - getattr(self, '_acquire_time', time.perf_counter())
        self._stats.hold_time += hold_time
        self._stats.max_hold = max(self._stats.max_hold, hold_time)
        
        tid = threading.get_ident()
        held = Profiler._thread_locks.get(tid, set())
        held.discard(self._name)
        
        return self._lock.release()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *args):
        self.release()
    
    def locked(self):
        return self._lock.locked()


class Profiler:
    """Global lock profiler registry."""
    _locks: Dict[str, ProfiledLock] = {}
    _thread_locks: Dict[int, set] = defaultdict(set)  # thread_id → {lock_names}
    _enabled = False
    
    @classmethod
    def register(cls, lock: ProfiledLock):
        if cls._enabled:
            cls._locks[lock._name] = lock
    
    @classmethod
    def start(cls):
        """Enable profiling globally."""
        cls._enabled = True
        cls._locks.clear()
        cls._thread_locks.clear()
    
    @classmethod
    def stop(cls) -> dict:
        """Stop profiling and return report."""
        cls._enabled = False
        return cls.report()
    
    @classmethod
    def report(cls) -> dict:
        """Generate VDP-compatible lock contention report."""
        locks_data = [l._stats.to_dict() for l in cls._locks.values()]
        locks_data.sort(key=lambda x: x['contended'], reverse=True)
        
        violations = []
        for ld in locks_data:
            if ld['contention_rate'] > 0.5:
                violations.append({
                    'rule_id': 'L1_HIGH_CONTENTION',
                    'severity': 'reject',
                    'loc': f'Lock:{ld["name"]}',
                    'kind': 'high_contention',
                    'detail': f"Contention {ld['contention_rate']*100:.0f}% — {ld['contended']}/{ld['acquires']} acquires blocked (avg wait {ld['avg_wait_ms']}ms)",
                })
            elif ld['contention_rate'] > 0.1:
                violations.append({
                    'rule_id': 'L2_MODERATE_CONTENTION',
                    'severity': 'warn',
                    'loc': f'Lock:{ld["name"]}',
                    'kind': 'moderate_contention',
                    'detail': f"Contention {ld['contention_rate']*100:.0f}% — {ld['contended']}/{ld['acquires']} acquires waited",
                })
            if ld['deadlock_risk'] > 0:
                violations.append({
                    'rule_id': 'L3_DEADLOCK_RISK',
                    'severity': 'warn',
                    'loc': f'Lock:{ld["name"]}',
                    'kind': 'deadlock_risk',
                    'detail': f"Nested lock acquires detected ({ld['deadlock_risk']} times) — potential deadlock pattern",
                })
            if ld['max_hold_ms'] > 100:
                violations.append({
                    'rule_id': 'L4_LONG_HOLD',
                    'severity': 'warn',
                    'loc': f'Lock:{ld["name"]}',
                    'kind': 'long_hold',
                    'detail': f"Max hold time {ld['max_hold_ms']:.0f}ms — lock held too long, blocks other threads",
                })
        
        total_contended = sum(ld['contended'] for ld in locks_data)
        total_acquires = sum(ld['acquires'] for ld in locks_data)
        
        return {
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
            'violations': violations,
            'summary': {
                'locks_profiled': len(locks_data),
                'total_acquires': total_acquires,
                'total_contended': total_contended,
                'overall_contention_rate': round(total_contended / max(total_acquires, 1), 3),
                'avg_wait_ms': round(
                    sum(ld['total_wait_seconds'] for ld in locks_data) / max(total_contended, 1) * 1000, 2
                ),
            },
            'locks': locks_data,
        }


# ── Monkey-patch for seamless integration ──

_original_lock = threading.Lock
_original_rlock = threading.RLock
_lock_names = {}

def _patched_lock(name=None):
    """Factory: threading.Lock() replacement that auto-profiles."""
    lock = ProfiledLock(name)
    return lock

def inject():
    """Replace threading.Lock globally with ProfiledLock.
    Call once at application startup.
    """
    Profiler.start()
    # Restore original first so ProfiledLock.__init__ uses real Lock
    threading.Lock = _original_lock
    threading.RLock = _original_rlock
    # Now monkey-patch for external callers
    threading.Lock = _patched_lock
    threading.RLock = lambda name=None: ProfiledLock(name or "RLock")


def restore():
    """Restore original threading.Lock."""
    threading.Lock = _original_lock
    threading.RLock = _original_rlock


# ── Standalone runner ──

def run_and_profile(target_module: str, timeout: float = 30.0) -> dict:
    """Import and run target_module under lock profiling, return report."""
    import importlib
    import runpy
    
    inject()
    try:
        # Run the target as __main__ with a timeout
        import signal
        old_alarm = None
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Profiling timeout after {timeout}s")
        
        if hasattr(signal, 'SIGALRM'):
            old_alarm = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
        
        try:
            if target_module.endswith('.py'):
                runpy.run_path(target_module, run_name='__profiled__')
            else:
                importlib.import_module(target_module)
        finally:
            if old_alarm and hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_alarm)
    except TimeoutError:
        pass
    except Exception as e:
        print(f"Target exited: {e}", file=sys.stderr)
    finally:
        restore()
    
    return Profiler.report()


def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS-VDP Lock Contention Profiler')
    ap.add_argument('target', nargs='?', help='Python script to profile')
    ap.add_argument('--json', action='store_true', help='JSON output')
    ap.add_argument('--timeout', type=float, default=30.0, help='Profiling timeout (seconds)')
    ap.add_argument('--demo', action='store_true', help='Run built-in demo')
    args = ap.parse_args()
    
    if args.demo or not args.target:
        print("Running built-in lock contention demo...")
        inject()
        
        def contended_worker(lock, name):
            for _ in range(50):
                with lock:
                    time.sleep(0.005)  # Hold lock for 5ms
        
        lock1 = ProfiledLock("shared_db")
        lock2 = ProfiledLock("cache")
        lock3 = ProfiledLock("config")
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=contended_worker, args=(lock1, f"w{i}"))
            threads.append(t)
        for i in range(3):
            t = threading.Thread(target=contended_worker, args=(lock2, f"c{i}"))
            threads.append(t)
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        restore()
        report = Profiler.report()
        
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            locks = report['locks']
            print(f"\nLock Contention Report ({len(locks)} locks, {report['summary']['total_acquires']} acquires)")
            print(f"Overall contention: {report['summary']['overall_contention_rate']*100:.1f}%")
            print(f"{'='*70}")
            for ld in locks:
                flag = '!!' if ld['contention_rate'] > 0.5 else '! ' if ld['contention_rate'] > 0.1 else '  '
                print(f"{flag} {ld['name']:<20s} {ld['contention_rate']*100:5.1f}% "
                      f"wait={ld['avg_wait_ms']:6.2f}ms hold={ld['avg_hold_ms']:6.2f}ms "
                      f"deadlock_risk={ld['deadlock_risk']}")
            if report['violations']:
                print(f"\nViolations: {len(report['violations'])}")
                for v in report['violations'][:10]:
                    print(f"  [{v['severity']}] {v['rule_id']}: {v['detail'][:80]}")
        return
    
    # Profile target script
    print(f"Profiling: {args.target} (timeout={args.timeout}s)")
    report = run_and_profile(args.target, timeout=args.timeout)
    
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Locks profiled: {report['summary']['locks_profiled']}")
        print(f"Violations: {len(report['violations'])}")
        for v in report['violations']:
            print(f"  [{v['severity']}] {v['rule_id']}: {v['detail'][:80]}")


if __name__ == '__main__':
    main()
