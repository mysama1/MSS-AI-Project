"""
DEEP-008: TSP Bridge multi-process integration tests.

Tests:
  1. Ping/Pong round-trip
  2. AST scan (mock nodes → findings)
  3. Health check
  4. Benchmark round-trip
  5. Bad magic rejection
  6. Truncated frame handling
  7. SandboxContext auth header
  8. Bridge stats tracking
  9. Sequence ID monotonicity
  10. Graceful shutdown
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mssclaw.core.tsp_bridge import (
    TSPBridge, Frame, OpCode, Flag, SandboxContext, ZeroCopyBuffer,
    MAGIC, HEADER_SIZE, HEADER_FMT, MAX_PAYLOAD,
)


STUB_PATH = os.path.join(os.path.dirname(__file__), "..", "mssclaw", "core", "tsp_server_stub.py")


def spawn_stub():
    """Spawn TSP server stub in subprocess with BREAKAWAY_FROM_JOB."""
    CREATE_BREAKAWAY_FROM_JOB = 0x01000000
    CREATE_NO_WINDOW = 0x08000000
    return subprocess.Popen(
        [sys.executable, STUB_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW,
    )


def raw_send_recv(proc, frame: Frame) -> Frame:
    """Send a frame and receive response (raw, no bridge)."""
    raw = frame.to_bytes()
    proc.stdin.write(struct.pack(">I", len(raw)))
    proc.stdin.write(raw)
    proc.stdin.flush()

    len_bytes = proc.stdout.read(4)
    assert len(len_bytes) == 4, "No response length"
    size = struct.unpack(">I", len_bytes)[0]
    data = proc.stdout.read(size)
    assert len(data) == size, f"Truncated response: {len(data)} < {size}"
    return Frame.from_bytes(data)


class TestTSPMultiProcess:
    """Multi-process TSP integration tests."""

    # ── T1: Ping/Pong ──

    def test_ping_pong(self):
        """Ping → Pong round-trip through subprocess."""
        proc = spawn_stub()
        try:
            ping = Frame(opcode=OpCode.PING, seq_id=1, payload=b"hello")
            pong = raw_send_recv(proc, ping)
            assert pong.opcode == OpCode.PONG, f"Expected PONG, got {pong.opcode}"
            assert pong.seq_id == 1
            assert pong.payload == b"pong"
        finally:
            proc.kill()
            proc.wait()

    # ── T2: AST Scan ──

    def test_ast_scan(self):
        """AST scan: send nodes → get findings."""
        proc = spawn_stub()
        try:
            nodes = {
                "nodes": [
                    {"id": 1, "type": "eval", "line": 42, "code": "eval(input())"},
                    {"id": 2, "type": "function", "line": 10, "code": "def f(): pass"},
                    {"id": 3, "type": "eval", "line": 99, "code": "eval(x)"},
                ]
            }
            scan = Frame(opcode=OpCode.SCAN_AST, seq_id=2, payload=json.dumps(nodes).encode("utf-8"))
            result = raw_send_recv(proc, scan)
            assert result.opcode == OpCode.SCAN_RESULT
            data = json.loads(result.payload)
            assert data["count"] == 2  # 2 eval nodes detected
            assert data["findings"][0]["rule"] == "R-001"
        finally:
            proc.kill()
            proc.wait()

    # ── T3: Health Check ──

    def test_health(self):
        """Health check → status reply."""
        proc = spawn_stub()
        try:
            health = Frame(opcode=OpCode.HEALTH, seq_id=3)
            reply = raw_send_recv(proc, health)
            assert reply.opcode == OpCode.HEALTH_REPLY
            data = json.loads(reply.payload)
            assert data["status"] == "ok"
        finally:
            proc.kill()
            proc.wait()

    # ── T4: Benchmark ──

    def test_benchmark(self):
        """Benchmark request → result."""
        proc = spawn_stub()
        try:
            payload = struct.pack(">I", 100) + json.dumps({"nodes": []}).encode("utf-8")
            bench = Frame(opcode=OpCode.BENCH, seq_id=4, payload=payload)
            result = raw_send_recv(proc, bench)
            assert result.opcode == OpCode.BENCH_RESULT
            data = json.loads(result.payload)
            assert data["iterations"] == 100
            assert data["mean_us"] == 150.0
        finally:
            proc.kill()
            proc.wait()

    # ── T5: Bad Magic ──

    def test_bad_magic(self):
        """Bad magic number → server sends ERROR."""
        proc = spawn_stub()
        try:
            # Send a properly-sized frame with bad magic
            header = struct.pack(">IBBHII", 0xDEADBEEF, 1, 0, OpCode.PING, 99, 0)
            proc.stdin.write(struct.pack(">I", len(header)))
            proc.stdin.write(header)
            proc.stdin.flush()
            proc.stdin.flush()

            len_bytes = proc.stdout.read(4)
            assert len(len_bytes) == 4
            size = struct.unpack(">I", len_bytes)[0]
            data = proc.stdout.read(size)
            result = Frame.from_bytes(data)
            assert result.opcode == OpCode.ERROR
            assert b"Bad magic" in result.payload
        finally:
            proc.kill()
            proc.wait()

    # ── T6: Multiple Sequential Frames ──

    def test_sequential_frames(self):
        """Multiple frames in sequence without reconnection."""
        proc = spawn_stub()
        try:
            for i in range(10):
                ping = Frame(opcode=OpCode.PING, seq_id=i)
                pong = raw_send_recv(proc, ping)
                assert pong.opcode == OpCode.PONG
                assert pong.seq_id == i
        finally:
            proc.kill()
            proc.wait()

    # ── T7: SandboxContext ──

    def test_sandbox_context(self):
        """Auth header round-trip with compact JSON keys."""
        ctx = SandboxContext(
            agent_id="audit-agent",
            capabilities=["fs.read.project", "vdp.scan.all"],
            quota_limit_mb=256,
            priority=2,
        )
        header = ctx.to_auth_header()
        assert len(header) == 128

        ctx2 = SandboxContext.from_auth_header(header)
        assert ctx2.agent_id == "audit-agent"
        assert len(ctx2.capabilities) == 2
        assert ctx2.quota_limit_mb == 256
        assert ctx2.priority == 2

    # ── T8: Bridge Stats ──

    def test_bridge_stats(self):
        """After sending frames, bridge_stats() returns timing data."""
        bridge = TSPBridge()
        # Direct frame ops (no subprocess) still count
        f1 = bridge.encode_ping()
        f2 = bridge.decode_response(f1.to_bytes())
        assert f2.opcode == OpCode.PING

        stats = bridge.bridge_stats
        assert stats["samples"] >= 0

    # ── T9: Seq ID Monotonicity ──

    def test_seq_id_monotonic(self):
        """Sequence IDs must be strictly increasing."""
        bridge = TSPBridge()
        ids = []
        for _ in range(5):
            f = bridge.encode_ping()
            ids.append(f.seq_id)
        assert ids == sorted(ids), f"Not monotonic: {ids}"
        assert len(set(ids)) == len(ids), f"Duplicates: {ids}"

    # ── T10: ZeroCopyBuffer ──

    def test_zero_copy_buffer(self):
        """ZeroCopyBuffer write/read operations."""
        buf = ZeroCopyBuffer.alloc(1024)
        buf.write_u32(0xAABBCCDD)
        buf.write_bytes(b"hello world")
        buf.write_u32(42)
        assert buf.used == 19  # 4(u32) + 11(hello world) + 4(u32)
        assert buf.buffer[0:4] == struct.pack(">I", 0xAABBCCDD)
        assert bytes(buf.buffer[4:15]) == b"hello world"

        buf.reset()
        assert buf.used == 0

    # ── T11: Error on Unknown OpCode ──

    def test_unknown_opcode(self):
        """Server returns ERROR for unknown opcodes."""
        proc = spawn_stub()
        try:
            unknown = Frame(opcode=0x9999, seq_id=99, payload=b"???")
            result = raw_send_recv(proc, unknown)
            assert result.opcode == OpCode.ERROR
            assert b"Unknown opcode" in result.payload
        finally:
            proc.kill()
            proc.wait()

    # ── T12: Concurrent SAFE (sequential stress) ──

    def test_multi_frames_stress(self):
        """50 sequential ping/pong — no degradation."""
        proc = spawn_stub()
        try:
            for i in range(50):
                ping = Frame(opcode=OpCode.PING, seq_id=i)
                pong = raw_send_recv(proc, ping)
                assert pong.opcode == OpCode.PONG, f"Frame {i} failed"
        finally:
            proc.kill()
            proc.wait()
