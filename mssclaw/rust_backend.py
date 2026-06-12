# -*- coding: utf-8 -*-
"""
MSSclaw Rust Backend — Python-side integration layer.

Phase 1: JSON bridge with T1/T2/T3 timing split.
Phase 1.5 target: arena/buffer zero-copy when bridge_overhead_ratio > 0.4.

Architecture:
    Python list[dict] → json.dumps(T1) → Rust scan_ast_nodes(T2) → json.loads(T3) → Python list[dict]
"""
import json
import time
import sys
from typing import Optional
from types import ModuleType


class RustBackend:
    """Lazily-loaded Rust VDP scanner backend with automatic fallback."""

    def __init__(self):
        self._mod: Optional[ModuleType] = None
        self._load_error: Optional[str] = None
        try:
            import mssclaw_rs
            self._mod = mssclaw_rs
        except ImportError as e:
            self._load_error = str(e)
        except Exception as e:
            self._load_error = f"Unexpected: {e}"

    @property
    def available(self) -> bool:
        return self._mod is not None

    @property
    def version(self) -> str:
        if not self._mod:
            return "unavailable"
        info = json.loads(self._mod.health_check())
        return info.get("version", "unknown")

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def health(self) -> dict:
        if not self._mod:
            return {"available": False, "error": self._load_error}
        return json.loads(self._mod.health_check())

    def scan(self, nodes: list[dict]) -> list[dict]:
        """Scan AST nodes with VDP rules. Falls back to empty on unavailable."""
        if not self._mod:
            return []
        raw = self._mod.scan_ast_nodes(json.dumps(nodes))
        return json.loads(raw)

    def bench(self, nodes: list[dict], iterations: int = 100) -> dict:
        """
        Benchmark with T1/T2/T3 timing split.

        Returns:
            {
                "available": bool,
                "nodes_count": int,
                "iterations": int,
                "T1_dumps_us": float,       # Python → JSON string
                "T2_scan_us": float,         # Rust pure scan (avg per iter)
                "T3_loads_us": float,        # JSON string → Python
                "T_python_us": float,        # Pure Python fallback (avg)
                "total_per_call_us": float,  # T1 + T2 + T3
                "bridge_overhead_ratio": float,  # (T1+T3)/total
                "speedup_vs_python": float,  # T_python / total
            }
        """
        if not self._mod:
            return {"available": False, "error": self._load_error}

        # T1: Python → JSON
        t1_start = time.perf_counter()
        nodes_json = json.dumps(nodes)
        t1 = (time.perf_counter() - t1_start) * 1_000_000

        # T2: Rust scan (use internal bench for stable timing)
        bench_result = json.loads(
            self._mod.bench_scan_ast(nodes_json, iterations)
        )
        t2 = bench_result["avg_scan_ns"] / 1000  # ns → us

        # T3: JSON → Python
        raw = self._mod.scan_ast_nodes(nodes_json)
        t3_start = time.perf_counter()
        findings = json.loads(raw)
        t3 = (time.perf_counter() - t3_start) * 1_000_000

        # Pure Python fallback benchmark
        py_times = []
        for _ in range(min(iterations, 50)):
            ps = time.perf_counter()
            _findings = self._fallback_scan(nodes)
            py_times.append((time.perf_counter() - ps) * 1_000_000)
        t_python = sum(py_times) / len(py_times)

        total = t1 + t2 + t3
        bridge_ratio = (t1 + t3) / total if total > 0 else 0

        return {
            "available": True,
            "nodes_count": len(nodes),
            "findings_count": len(findings),
            "iterations": iterations,
            "T1_dumps_us": round(t1, 2),
            "T2_scan_us": round(t2, 2),
            "T3_loads_us": round(t3, 2),
            "T_python_us": round(t_python, 2),
            "total_per_call_us": round(total, 2),
            "bridge_overhead_ratio": round(bridge_ratio, 4),
            "speedup_vs_python": round(t_python / total, 2) if total > 0 else 0,
            "should_migrate_to_phase15": bridge_ratio > 0.4,
        }

    @staticmethod
    def _fallback_scan(nodes: list[dict]) -> list[dict]:
        """Pure Python rules for when Rust backend is unavailable."""
        findings = []
        for node in nodes:
            text = node.get("text", "")
            kind = node.get("kind", "")

            # V1: file I/O without precheck
            if kind in ("Call", "Command") and any(
                kw in text for kw in
                ("open(", "subprocess.run", "os.remove", "Get-Content",
                 "Set-Content", "Out-File", "Invoke-WebRequest",
                 "Remove-Item")
            ):
                if not any(g in text for g in (
                    "os.path.exists", "Test-Path", "try:", "ErrorAction"
                )):
                    findings.append({
                        "node_id": node["id"],
                        "rule_id": "V1-01",
                        "severity": "blocker",
                        "message": "File I/O without existence precheck",
                        "line": node.get("line"),
                    })

            # V5: network without timeout
            if kind == "Call" and any(
                kw in text for kw in
                ("requests.get", "requests.post", "Invoke-WebRequest",
                 "Invoke-RestMethod", "fetch(", "curl")
            ):
                if not any(g in text for g in (
                    "timeout=", "Timeout", "--connect-timeout"
                )):
                    findings.append({
                        "node_id": node["id"],
                        "rule_id": "V5-01",
                        "severity": "major",
                        "message": "Network call without timeout",
                        "line": node.get("line"),
                    })

            # MSS-SEC: hardcoded secrets
            text_lower = text.lower()
            if any(s in text_lower for s in ("password", "api_key", "secret", "token")):
                if not any(e in text_lower for e in ("os.environ", "getenv", "$env:", "none", "null", "placeholder", "''", '""')):
                    findings.append({
                        "node_id": node["id"],
                        "rule_id": "MSS-SEC-01",
                        "severity": "blocker",
                        "message": "Hardcoded secret detected",
                        "line": node.get("line"),
                    })

        return findings


# ── Helper: generate test AST nodes ──

def make_test_nodes(count: int = 100) -> list[dict]:
    """Generate a mix of clean and dirty AST nodes for benchmarking."""
    import random
    nodes = []
    patterns = [
        # (kind, text, expect_finding)
        ("Call", 'open("file.txt", encoding="utf-8")', True),  # V1+V3
        ("Call", 'requests.get("http://api.example.com")', True),  # V5
        ("Call", 'requests.get(url, timeout=30)', False),  # clean
        ("Assignment", 'password = "admin123"', True),  # MSS-SEC
        ("Assignment", 'db_host = os.environ.get("DB_HOST")', False),  # clean
        ("Call", 'eval(user_input)', True),  # MSS-SEC
        ("Call", 'os.system("rm -rf /")', True),  # V4 + MSS-SEC
        ("Call", 'if os.path.exists(p): open(p, encoding="utf-8")', False),  # clean
        ("ExpressionStatement", "看起来是被沙箱拦截了", True),  # V2
        ("ExpressionStatement", "Exit code 5: permission denied", False),  # clean (has errno)
        ("Comment", "观察到返回值为0，推断是网络问题", True),  # V6
        ("Call", 'rewrite(text)', True),  # MSS-WASTE
        ("Call", "subprocess.run(['ls'], check=True)", True),  # V1
        ("Call", 'shutil.rmtree("/tmp/build")', True),  # V4
        ("Call", 'curl -s https://example.com', True),  # V5
    ]
    for i in range(count):
        kind, text, dirty = random.choice(patterns)
        nodes.append({
            "id": i, "kind": kind, "start": 0,
            "end": len(text), "line": i + 1, "text": text,
        })
    return nodes


# ── CLI entry ──

if __name__ == "__main__":
    backend = RustBackend()
    print(f"=== RustBackend Status ===")
    print(f"Available: {backend.available}")
    print(f"Version:   {backend.version}")
    if backend.load_error:
        print(f"Error:     {backend.load_error}")
    print()

    if backend.available:
        test_nodes = make_test_nodes(200)
        result = backend.bench(test_nodes, iterations=500)
        print("=== Benchmark Results ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
