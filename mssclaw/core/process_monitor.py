"""
MSS Process Monitor — 进程健康 + 僵尸检测

检测:
  - 孤儿进程 (父进程已死)
  - 高CPU异常 (>80% 持续)
  - 内存泄漏 (>1GB)
  - 预期服务状态 (skill_api, ollama, gateway)

用法:
    from mssclaw.core.process_monitor import ProcessMonitor
    pm = ProcessMonitor()
    report = pm.check()
    pm.kill_orphans()  # 清理僵尸
"""
from __future__ import annotations
import os, time, subprocess, sys
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class ProcessInfo:
    pid: int
    name: str
    parent_pid: int
    cpu_percent: float
    memory_mb: float
    is_orphan: bool
    cmdline: str
    status: str = "ok"  # ok | orphan | high_cpu | high_mem


class ProcessMonitor:
    """进程健康监控."""

    # 预期运行的服务 (不会被标记为异常)
    KNOWN_SERVICES = {
        "skill_api.py": "skill_api",
        "ollama": "ollama",
        "node": "openclaw_gateway",
    }

    CPU_THRESHOLD = 80.0     # % CPU
    MEM_THRESHOLD = 1024.0   # MB

    def check(self) -> dict:
        """全量进程检查."""
        processes = self._list_processes()
        orphans = [p for p in processes if p.is_orphan]
        high_cpu = [p for p in processes if p.cpu_percent > self.CPU_THRESHOLD]
        high_mem = [p for p in processes if p.memory_mb > self.MEM_THRESHOLD]

        return {
            "total": len(processes),
            "orphans": len(orphans),
            "orphan_list": [{"pid": p.pid, "name": p.name, "cmd": p.cmdline[:80]}
                           for p in orphans],
            "high_cpu": len(high_cpu),
            "high_cpu_list": [{"pid": p.pid, "name": p.name, "cpu": p.cpu_percent}
                             for p in high_cpu],
            "high_mem": len(high_mem),
            "high_mem_list": [{"pid": p.pid, "name": p.name, "mem_mb": round(p.memory_mb, 1)}
                             for p in high_mem],
            "healthy": len(processes) - len(orphans) - len(high_cpu) - len(high_mem),
            "status": "HEALTHY" if not orphans and not high_cpu and not high_mem else "WARNING",
            "services": self._check_services(processes),
        }

    def kill_orphans(self) -> int:
        """清理孤儿进程. 返回清理数."""
        processes = self._list_processes()
        killed = 0
        for p in processes:
            if p.is_orphan and not self._is_known_service(p.name, p.cmdline):
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/PID", str(p.pid)],
                                      capture_output=True)
                    else:
                        os.kill(p.pid, 9)
                    killed += 1
                except Exception:
                    pass
        return killed

    def _list_processes(self) -> List[ProcessInfo]:
        """获取 Python/Node/Ollama 相关进程."""
        processes = []
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'ppid', 'cpu_percent',
                                              'memory_info', 'cmdline']):
                try:
                    info = proc.info
                    name = (info['name'] or '').lower()
                    cmdline = ' '.join(info['cmdline'] or []) if info['cmdline'] else ''

                    # Filter: only interesting processes
                    interesting = any(k in name or k in cmdline
                                     for k in ['python', 'node', 'ollama', 'openclaw'])
                    if not interesting:
                        continue

                    # Check if orphan (parent doesn't exist)
                    is_orphan = False
                    try:
                        parent = psutil.Process(info['ppid'])
                        if not parent.is_running():
                            is_orphan = True
                    except (psutil.NoSuchProcess, Exception):
                        is_orphan = True

                    mem_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0

                    # Check if known service
                    is_known = self._is_known_service(name, cmdline)

                    status = "ok"
                    if is_orphan and not is_known:
                        status = "orphan"
                    elif info['cpu_percent'] > self.CPU_THRESHOLD and not is_known:
                        status = "high_cpu"
                    elif mem_mb > self.MEM_THRESHOLD:
                        status = "high_mem"

                    processes.append(ProcessInfo(
                        pid=info['pid'], name=name, parent_pid=info['ppid'],
                        cpu_percent=round(info['cpu_percent'] or 0, 1),
                        memory_mb=round(mem_mb, 1),
                        is_orphan=is_orphan, cmdline=cmdline[:200], status=status,
                    ))
                except (psutil.NoSuchProcess, Exception):
                    continue
        except ImportError:
            # Fallback: subprocess + tasklist
            processes = self._list_processes_fallback()

        return processes

    def _list_processes_fallback(self) -> List[ProcessInfo]:
        """psutil 不可用时的回退方案."""
        processes = []
        try:
            if sys.platform == "win32":
                output = subprocess.check_output(
                    ["tasklist", "/FO", "CSV", "/NH", "/FI", "IMAGENAME eq python.exe"],
                    text=True, errors="replace"
                )
                for line in output.strip().split("\n"):
                    parts = line.replace('"', '').split(",")
                    if len(parts) >= 5:
                        pid = int(parts[1].strip())
                        mem_kb = int(parts[4].strip().replace(" K", "").replace(",", ""))
                        processes.append(ProcessInfo(
                            pid=pid, name="python", parent_pid=0,
                            cpu_percent=0, memory_mb=round(mem_kb / 1024, 1),
                            is_orphan=False, cmdline="", status="ok",
                        ))
        except Exception:
            pass
        return processes

    def _is_known_service(self, name: str, cmdline: str) -> bool:
        """检查是否是已知的正常服务."""
        for pattern, _ in self.KNOWN_SERVICES.items():
            if pattern in name or pattern in cmdline:
                return True
        return False

    def _check_services(self, processes: List[ProcessInfo]) -> dict:
        """检查关键服务是否在运行."""
        services = {
            "ollama": False,
            "skill_api": False,
            "gateway": False,
        }
        for p in processes:
            if "ollama" in p.name:
                services["ollama"] = True
            if "skill_api" in p.cmdline:
                services["skill_api"] = True
            if "node" in p.name:
                services["gateway"] = True
        return services


def cmd_process_check():
    """CLI: 进程健康检查."""
    pm = ProcessMonitor()
    report = pm.check()

    print("═══ MSS Process Monitor ═══")
    print(f"  进程: {report['total']} | 孤儿: {report['orphans']} | "
          f"高CPU: {report['high_cpu']} | 高内存: {report['high_mem']}")
    print(f"  状态: {report['status']}")

    if report["orphan_list"]:
        print(f"\n  ⚠️ 孤儿进程 ({len(report['orphan_list'])}):")
        for o in report["orphan_list"]:
            print(f"    PID {o['pid']}: {o['cmd'][:60]}")

    if report["high_cpu_list"]:
        print(f"\n  🔥 高CPU (>80%):")
        for c in report["high_cpu_list"]:
            print(f"    PID {c['pid']}: {c['name']} {c['cpu']}%")

    print(f"\n  服务: Ollama={'✅' if report['services']['ollama'] else '❌'} "
          f"| skill_api={'✅' if report['services']['skill_api'] else '❌'} "
          f"| Gateway={'✅' if report['services']['gateway'] else '❌'}")

    if report["orphans"] > 0:
        import getpass
        print(f"\n  发现 {report['orphans']} 个孤儿进程. 执行 mssclaw health --fix 清理")


if __name__ == "__main__":
    cmd_process_check()
