"""
TSP Server Stub — 为 multi-process 集成测试提供协议兼容的 mock 后端.

Phase 1: 纯 Python 实现，仅用作测试 + 协议验证。
Phase 2: 由 mssclaw-rs 替换。
"""
from __future__ import annotations

import json
import struct
import sys
from enum import IntEnum


MAGIC = 0x4D535354  # "MSST"
VERSION = 1
HEADER_SIZE = 16
HEADER_FMT = ">IBBHII"
MAX_PAYLOAD = 16 * 1024 * 1024


class OpCode(IntEnum):
    PING = 0x0001
    PONG = 0x0002
    SCAN_AST = 0x0010
    SCAN_RESULT = 0x0011
    HEALTH = 0x0020
    HEALTH_REPLY = 0x0021
    BENCH = 0x0030
    BENCH_RESULT = 0x0031
    ERROR = 0xFFFF


def read_frame(stream) -> tuple:
    """Read length-prefixed frame from stream."""
    len_bytes = stream.read(4)
    if len(len_bytes) < 4:
        raise EOFError("Connection closed")
    size = struct.unpack(">I", len_bytes)[0]
    if size > MAX_PAYLOAD + HEADER_SIZE:
        raise ValueError(f"Frame too large: {size}")
    data = stream.read(size)
    if len(data) < size:
        raise EOFError("Truncated frame")
    magic, ver, flags, opcode, seq_id, payload_len = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    if magic != MAGIC:
        raise ValueError(f"Bad magic: 0x{magic:08X}")
    if ver != VERSION:
        raise ValueError(f"Unsupported version: {ver}")
    if payload_len > MAX_PAYLOAD:
        raise ValueError(f"Payload too large: {payload_len}")
    payload = data[HEADER_SIZE:HEADER_SIZE + payload_len]
    return opcode, flags, seq_id, payload


def write_response(stream, opcode: int, seq_id: int, payload: bytes = b"", flags: int = 0):
    """Write length-prefixed response frame."""
    header = struct.pack(HEADER_FMT, MAGIC, VERSION, flags, opcode, seq_id, len(payload))
    frame = header + payload
    stream.write(struct.pack(">I", len(frame)))
    stream.write(frame)
    stream.flush()


def run_server():
    """Main TSP server loop — reads from stdin, writes to stdout."""
    while True:
        try:
            opcode, flags, seq_id, payload = read_frame(sys.stdin.buffer)
        except EOFError:
            break
        except ValueError as e:
            write_response(sys.stdout.buffer, OpCode.ERROR, 0, str(e).encode("utf-8"))
            continue

        if opcode == OpCode.PING:
            write_response(sys.stdout.buffer, OpCode.PONG, seq_id, b"pong")

        elif opcode == OpCode.SCAN_AST:
            try:
                nodes = json.loads(payload.decode("utf-8"))
                findings = []
                for node in nodes.get("nodes", []):
                    if node.get("type") == "eval":
                        findings.append({
                            "rule": "R-001",
                            "severity": "CRITICAL",
                            "message": f"eval() at line {node.get('line', '?')}",
                        })
                result = json.dumps({"findings": findings, "count": len(findings)})
                write_response(sys.stdout.buffer, OpCode.SCAN_RESULT, seq_id, result.encode("utf-8"))
            except Exception as e:
                write_response(sys.stdout.buffer, OpCode.ERROR, seq_id, str(e).encode("utf-8"))

        elif opcode == OpCode.HEALTH:
            status = json.dumps({"status": "ok", "version": "1.0-stub", "pid": 0})
            write_response(sys.stdout.buffer, OpCode.HEALTH_REPLY, seq_id, status.encode("utf-8"))

        elif opcode == OpCode.BENCH:
            try:
                iterations = struct.unpack(">I", payload[:4])[0]
                result = json.dumps({
                    "iterations": iterations,
                    "mean_us": 150.0,
                    "min_us": 120.0,
                    "max_us": 300.0,
                })
                write_response(sys.stdout.buffer, OpCode.BENCH_RESULT, seq_id, result.encode("utf-8"))
            except Exception as e:
                write_response(sys.stdout.buffer, OpCode.ERROR, seq_id, str(e).encode("utf-8"))

        else:
            write_response(sys.stdout.buffer, OpCode.ERROR, seq_id, f"Unknown opcode: {opcode}".encode("utf-8"))


if __name__ == "__main__":
    run_server()
