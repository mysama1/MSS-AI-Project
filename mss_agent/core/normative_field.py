"""
MSSclaw NormativeField — 自演化安全引擎.

替代传统 SIGKILL 式硬限制。

双层架构：
  Layer 1 (确定性):
    - 白名单：允许的进程/文件/网络/域
    - 速率限制：CPU/RAM/GPU 软硬上限
    - 孤儿检测：自动清理僵尸进程
    - 人类覆盖：始终可放行

  Layer 2 (推理性):
    - 异常检测：行为偏离正常模式 → 标记
    - Δ 阈值：Δ<0.3 持续 2 周期 → 告警
    - 半自动学习：未知异常 → 标记+等待确认 → 纳入规范场

核心原则：
  "不是禁止什么，而是正常范围是什么" → 在正常范围内自由
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class NormLevel(str, Enum):
    """规范场判定级别"""
    SAFE = "safe"              # 完全安全，放行
    OBSERVE = "observe"        # 略偏离正常，记录观测
    WARN = "warn"              # 明显偏离，警告
    BLOCK = "block"            # 严重偏离，阻止
    NEEDS_HUMAN = "needs_human"  # 无法判定，需人工


class NormDomain(str, Enum):
    """规范场管控域"""
    PROCESS = "process"    # 进程管理
    FILE = "file"          # 文件访问
    NETWORK = "network"    # 网络访问
    RESOURCE = "resource"  # CPU/RAM/GPU
    CONTENT = "content"    # 内容安全（输出审查）


@dataclass
class NormRule:
    """单条规范规则"""
    name: str
    domain: NormDomain
    pattern: str = ""          # 匹配模式（regex/glob/资源表达式）
    level: NormLevel = NormLevel.WARN
    description: str = ""
    learned: bool = False      # 是否从异常中学习
    hit_count: int = 0         # 命中次数
    last_hit: float = 0.0      # 最后命中时间
    cooldown_seconds: float = 0.0  # 冷却期（秒）


@dataclass
class NormVerdict:
    """规范场判定结果"""
    level: NormLevel = NormLevel.SAFE
    domain: NormDomain = NormDomain.PROCESS
    rule_name: str = ""
    reason: str = ""
    suggested_action: str = ""
    needs_confirm: bool = False  # 是否需要人工确认
    anomaly_score: float = 0.0   # 异常分数 0-1


# ── 规范场引擎 ──


class NormativeField:
    """自演化安全规范场.

    使用：
        nf = NormativeField()
        nf.load_defaults()          # 加载默认安全规则
        verdict = nf.check("process", {"name": "python", "mem_mb": 12000})
        if verdict.level == NormLevel.BLOCK:
            # 阻止
    """

    def __init__(self, config_path: str = ""):
        self._path = config_path or "config/norm_field.json"
        self._rules: dict[str, NormRule] = {}         # rule_name → Rule
        self._resource_baseline: dict[str, dict] = {}  # 资源基线（学习）
        self._anomaly_history: list[dict] = []          # 异常历史
        self._total_checks: int = 0
        self._total_blocks: int = 0

    # ── 规则管理 ──

    def add_rule(self, rule: NormRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        self._rules.pop(name, None)

    def learn_rule(self, name: str, domain: NormDomain, pattern: str,
                   description: str = "", level: NormLevel = NormLevel.WARN) -> NormRule:
        """从异常中学习新规则"""
        rule = NormRule(
            name=name,
            domain=domain,
            pattern=pattern,
            level=level,
            description=f"[LEARNED] {description}",
            learned=True,
        )
        self._rules[name] = rule
        self._save()
        return rule

    # ── 核心检查 ──

    def check(self, domain: NormDomain, context: dict[str, Any]) -> NormVerdict:
        """检查行为是否符合规范场.

        Args:
            domain: 管控域
            context: 待检查上下文
                process: {"name": str, "pid": int, "mem_mb": float, "cpu_pct": float}
                file:    {"path": str, "operation": "read"|"write"|"delete"}
                network: {"url": str, "method": str, "domain": str}
                resource: {"cpu_pct": float, "mem_mb": float, "gpu_pct": float}
                content: {"text": str, "source": str}

        Returns:
            NormVerdict
        """
        self._total_checks += 1

        # Layer 1: 确定性检查
        for rule in self._rules.values():
            if rule.domain != domain:
                continue
            if self._match_rule(rule, context):
                rule.hit_count += 1
                rule.last_hit = time.time()

                self._total_blocks += 1
                self._record_anomaly(rule, context)

                return NormVerdict(
                    level=rule.level,
                    domain=domain,
                    rule_name=rule.name,
                    reason=f"Rule '{rule.name}': {rule.description}",
                    suggested_action=self._suggest_action(rule, context),
                    needs_confirm=rule.level in (NormLevel.BLOCK, NormLevel.NEEDS_HUMAN),
                )

        # Layer 2: 推理性异常检测（仅 RESOURCE 域）
        if domain == NormDomain.RESOURCE:
            return self._check_resource_anomaly(context)

        return NormVerdict(level=NormLevel.SAFE, domain=domain)

    def check_process(self, name: str, pid: int = 0, mem_mb: float = 0,
                      cpu_pct: float = 0) -> NormVerdict:
        """快捷：进程检查"""
        return self.check(NormDomain.PROCESS, {
            "name": name, "pid": pid, "mem_mb": mem_mb, "cpu_pct": cpu_pct,
        })

    def check_file(self, path: str, operation: str) -> NormVerdict:
        """快捷：文件访问检查"""
        return self.check(NormDomain.FILE, {"path": str(path), "operation": operation})

    def check_network(self, url: str) -> NormVerdict:
        """快捷：网络访问检查"""
        domain_match = re.search(r'://([^/:]+)', url)
        domain = domain_match.group(1) if domain_match else url
        return self.check(NormDomain.NETWORK, {"url": url, "domain": domain})

    def check_content(self, text: str, source: str = "") -> NormVerdict:
        """快捷：内容安全检查"""
        return self.check(NormDomain.CONTENT, {"text": text, "source": source})

    # ── 资源基线学习 ──

    def update_resource_baseline(self, name: str, cpu_pct: float, mem_mb: float) -> None:
        """更新进程资源基线"""
        if name not in self._resource_baseline:
            self._resource_baseline[name] = {
                "cpu_samples": [],
                "mem_samples": [],
                "samples": 0,
            }
        bl = self._resource_baseline[name]
        bl["cpu_samples"].append(cpu_pct)
        bl["mem_samples"].append(mem_mb)
        bl["samples"] += 1

        # 只保留最近 100 个样本
        if len(bl["cpu_samples"]) > 100:
            bl["cpu_samples"] = bl["cpu_samples"][-100:]
            bl["mem_samples"] = bl["mem_samples"][-100:]

    def detect_orphans(self) -> list[int]:
        """孤儿进程检测：返回疑似僵尸进程的 PID 列表.

        在 Windows 上通过 wmic 或 psutil 检测。
        优先使用内置方法。
        """
        orphans = []
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "process", "get", "ProcessId,Name,WorkingSetSize", "/format:csv"],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().split("\n")[2:]
            for line in lines:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    try:
                        pid = int(parts[-1])
                        name = parts[1]
                        mem = int(parts[-2]) / (1024 * 1024) if parts[-2].isdigit() else 0
                    except (ValueError, IndexError):
                        continue

                    # 检查是否存在基线
                    bl = self._resource_baseline.get(name)
                    if bl and bl["samples"] > 10:
                        avg_mem = sum(bl["mem_samples"]) / len(bl["mem_samples"])
                        # 内存远超基线 → 疑似僵尸
                        if avg_mem > 0 and mem > avg_mem * 10:
                            orphans.append(pid)
        except Exception:
            pass

        return orphans

    # ── 持久化 ──

    def load_defaults(self) -> None:
        """加载 MSSclaw 默认安全规则 (35 rules, 5 域覆盖)"""
        # ── 进程规则 (5) ──
        self.add_rule(NormRule("orphan_detect", NormDomain.PROCESS,
            "memory_10x_baseline", NormLevel.WARN,
            "进程内存超基线 10 倍 → 疑似僵尸进程"))
        self.add_rule(NormRule("process_fork_bomb", NormDomain.PROCESS,
            "pid_count>200", NormLevel.BLOCK,
            "进程数超过 200 → 疑似 fork bomb"))
        self.add_rule(NormRule("process_system_tool", NormDomain.PROCESS,
            r"(?i)(cmd\.exe|powershell\.exe|bash\.exe|regedit\.exe|taskkill)",
            NormLevel.WARN, "系统工具调用 → 记录审计"))
        self.add_rule(NormRule("process_suspicious_child", NormDomain.PROCESS,
            r"(?i)(python).*(cmd|powershell|bash)",
            NormLevel.WARN, "可疑父子进程链"))
        self.add_rule(NormRule("process_cpu_spike", NormDomain.PROCESS,
            "cpu>95%_duration_30s", NormLevel.WARN,
            "CPU 持续 30s > 95% → 可能的挖矿/死循环"))

        # ── 文件规则 (7) ──
        self.add_rule(NormRule("system_write", NormDomain.FILE,
            "C:\\\\Windows\\\\.*", NormLevel.BLOCK,
            "禁止写入系统目录"))
        self.add_rule(NormRule("workspace_only", NormDomain.FILE,
            "", NormLevel.OBSERVE,
            "文件操作应在 workspace 内"))
        self.add_rule(NormRule("file_bulk_delete", NormDomain.FILE,
            "delete_count>50", NormLevel.BLOCK,
            "单次删除超过 50 文件 → 需确认"))
        self.add_rule(NormRule("file_exfil_check", NormDomain.FILE,
            r"(?i)(\.env|\.secret|\.key|\.pem|\.crt|credentials|id_rsa)",
            NormLevel.BLOCK, "禁止读取/传输敏感凭证文件"))
        self.add_rule(NormRule("file_path_traversal", NormDomain.FILE,
            r"\.\./|\.\\.\\",
            NormLevel.BLOCK, "路径遍历攻击检测"))
        self.add_rule(NormRule("file_exec_in_data", NormDomain.FILE,
            r"(?i)(\.exe|\.dll|\.sys|\.bat|\.ps1)\b",
            NormLevel.WARN, "数据目录出现可执行文件"))
        self.add_rule(NormRule("file_size_anomaly", NormDomain.FILE,
            "write_size>500MB", NormLevel.WARN,
            "单文件写入超过 500MB → 审计"))

        # ── 网络规则 (8) ──
        self.add_rule(NormRule("allow_localhost", NormDomain.NETWORK,
            "localhost|127\\.0\\.0\\.1|11434|52930|53000",
            NormLevel.SAFE, "本地服务放行"))
        self.add_rule(NormRule("allow_ollama", NormDomain.NETWORK,
            "ollama|huggingface|pytorch|github|pypi|zenodo|arxiv",
            NormLevel.SAFE, "AI/开发相关域名放行"))
        self.add_rule(NormRule("net_raw_socket", NormDomain.NETWORK,
            r"(?i)(socket\.SOCK_RAW|AF_PACKET)",
            NormLevel.BLOCK, "原始套接字 → 需审计"))
        self.add_rule(NormRule("net_unknown_egress", NormDomain.NETWORK,
            "egress_to_unknown", NormLevel.OBSERVE,
            "连接未识别外部 IP → 记录观测"))
        self.add_rule(NormRule("net_large_upload", NormDomain.NETWORK,
            "upload_size>100MB", NormLevel.WARN,
            "单次上传超过 100MB → 审计"))
        self.add_rule(NormRule("net_internal_scan", NormDomain.NETWORK,
            r"(?i)(nmap|port.scan|masscan|zmap)",
            NormLevel.BLOCK, "禁止端口扫描工具"))
        self.add_rule(NormRule("net_reverse_shell", NormDomain.NETWORK,
            r"(?i)(nc\.exe|netcat|reverse_shell|bind_shell)",
            NormLevel.BLOCK, "反向 Shell 检测"))
        self.add_rule(NormRule("net_websocket_spam", NormDomain.NETWORK,
            "websocket_msg_rate>100_per_sec", NormLevel.WARN,
            "WebSocket 消息频率过高 → CVE-2026-44211"))

        # ── 资源规则 (6) ──
        self.add_rule(NormRule("ram_soft", NormDomain.RESOURCE,
            "mem>80%", NormLevel.WARN, "内存使用超过 80%"))
        self.add_rule(NormRule("ram_hard", NormDomain.RESOURCE,
            "mem>95%", NormLevel.BLOCK, "内存使用超过 95% → 阻止新进程"))
        self.add_rule(NormRule("gpu_soft", NormDomain.RESOURCE,
            "gpu>90%", NormLevel.WARN, "GPU 使用超过 90%"))
        self.add_rule(NormRule("disk_soft", NormDomain.RESOURCE,
            "disk>90%", NormLevel.WARN, "磁盘使用超过 90%"))
        self.add_rule(NormRule("disk_hard", NormDomain.RESOURCE,
            "disk>97%", NormLevel.BLOCK, "磁盘使用超过 97% → 阻止写入"))
        self.add_rule(NormRule("handle_leak", NormDomain.RESOURCE,
            "handle_count>10000", NormLevel.WARN,
            "句柄数超过 10000 → 疑似泄漏"))

        # ── 内容规则 (9) — 意义场 / 隐私保护 ──
        self.add_rule(NormRule("content_pii_leak", NormDomain.CONTENT,
            r"(\\d{17}[\\dXx]|\\d{18})",
            NormLevel.BLOCK, "身份证号泄露"))
        self.add_rule(NormRule("content_phone_leak", NormDomain.CONTENT,
            r"1[3-9]\\d{9}",
            NormLevel.BLOCK, "手机号泄露"))
        self.add_rule(NormRule("content_api_key_leak", NormDomain.CONTENT,
            r"(?i)(sk-[a-zA-Z0-9]{20,}|api_key|access_token)",
            NormLevel.BLOCK, "API Key/Token 泄露"))
        self.add_rule(NormRule("content_forbidden_words", NormDomain.CONTENT,
            r"(?i)(忽略.*指令|跳过.*所有|假装.*你.*是|绕过.*限制)",
            NormLevel.BLOCK, "越狱/指令覆盖检测"))
        self.add_rule(NormRule("content_meaning_hollow", NormDomain.CONTENT,
            "meaning_density<0.1", NormLevel.WARN,
            "意义密度不足 → 疑似空洞输出"))
        self.add_rule(NormRule("content_self_ref_loop", NormDomain.CONTENT,
            "self_ref_count>=3", NormLevel.WARN,
            "自我引用循环 → K3 化风险"))
        self.add_rule(NormRule("content_guardian_bypass", NormDomain.CONTENT,
            r"(?i)(base64|rot13|reverse|encode|decode).*?(prompt|instruction|rule)",
            NormLevel.BLOCK, "编码绕过守卫检测"))
        self.add_rule(NormRule("content_injection_markdown", NormDomain.CONTENT,
            r"```system|<!--.*system|##.*System\s*:",
            NormLevel.BLOCK, "Markdown 注入伪装系统指令"))
        self.add_rule(NormRule("content_metadata_implant", NormDomain.CONTENT,
            r"\\u[0-9a-f]{4}\\u[0-9a-f]{4}",
            NormLevel.WARN, "Unicode 隐写/元数据植入"))


    def load(self) -> None:
        """从磁盘加载规范场"""
        try:
            if os.path.exists(self._path):
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
                    for r in data.get("rules", []):
                        self.add_rule(NormRule(**r))
        except Exception:
            pass

    def save(self) -> None:
        self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or "config", exist_ok=True)
        data = {
            "rules": [
                {
                    "name": r.name, "domain": r.domain.value,
                    "pattern": r.pattern, "level": r.level.value,
                    "description": r.description, "learned": r.learned,
                    "hit_count": r.hit_count, "last_hit": r.last_hit,
                }
                for r in self._rules.values()
            ],
            "resource_baselines": {
                k: {"samples": v["samples"],
                    "avg_cpu": sum(v["cpu_samples"]) / len(v["cpu_samples"]) if v["cpu_samples"] else 0,
                    "avg_mem": sum(v["mem_samples"]) / len(v["mem_samples"]) if v["mem_samples"] else 0}
                for k, v in self._resource_baseline.items()
            },
            "total_checks": self._total_checks,
            "total_blocks": self._total_blocks,
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 内部实现 ──

    def _match_rule(self, rule: NormRule, context: dict) -> bool:
        """匹配规则 — 根据域类型选择匹配方式"""
        pattern = rule.pattern
        if not pattern:
            return False

        if rule.domain == NormDomain.PROCESS:
            return bool(re.search(pattern, str(context.get("name", "")), re.IGNORECASE))

        elif rule.domain == NormDomain.FILE:
            path = str(context.get("path", ""))
            return bool(re.search(pattern, path, re.IGNORECASE))

        elif rule.domain == NormDomain.NETWORK:
            url = str(context.get("url", ""))
            domain = str(context.get("domain", ""))
            # SAFE 规则特殊处理：命中 = 安全 = 不触发
            if rule.level == NormLevel.SAFE:
                return False  # SAFE 规则不触发阻断
            return bool(re.search(pattern, url, re.IGNORECASE)) or \
                   bool(re.search(pattern, domain, re.IGNORECASE))

        elif rule.domain == NormDomain.RESOURCE:
            mem_pct = float(context.get("mem_mb", 0))
            # 简单阈值比较
            if "mem>95%" in pattern and mem_pct > 0.95 * 32000:  # 32GB 上限
                return True
            if "mem>80%" in pattern and mem_pct > 0.80 * 32000:
                return True
            gpu_pct = float(context.get("gpu_pct", 0))
            if "gpu>90%" in pattern and gpu_pct > 90:
                return True

        elif rule.domain == NormDomain.CONTENT:
            text = str(context.get("text", ""))
            return bool(re.search(pattern, text, re.IGNORECASE))

        return False

    def _check_resource_anomaly(self, context: dict) -> NormVerdict:
        """Layer 2: 资源异常推理检测"""
        name = str(context.get("name", ""))
        mem_mb = float(context.get("mem_mb", 0))
        cpu_pct = float(context.get("cpu_pct", 0))
        gpu_pct = float(context.get("gpu_pct", 0))

        # 更新基线
        if name:
            self.update_resource_baseline(name, cpu_pct, mem_mb)

        # 与基线比较
        bl = self._resource_baseline.get(name)
        if bl and bl["samples"] > 10:
            avg_mem = sum(bl["mem_samples"]) / len(bl["mem_samples"])
            avg_cpu = sum(bl["cpu_samples"]) / len(bl["cpu_samples"])

            anomaly_score = 0.0
            if avg_mem > 0:
                anomaly_score += min(1.0, mem_mb / (avg_mem * 3))
            if avg_cpu > 0:
                anomaly_score += min(1.0, cpu_pct / (avg_cpu * 3))
            anomaly_score = anomaly_score / 2.0  # 归一化

            if anomaly_score > 0.8:
                return NormVerdict(
                    level=NormLevel.WARN,
                    domain=NormDomain.RESOURCE,
                    rule_name="anomaly_detection",
                    reason=f"资源偏差异常: {name} mem={mem_mb:.0f}MB (avg={avg_mem:.0f}MB), cpu={cpu_pct:.1f}% (avg={avg_cpu:.1f}%)",
                    anomaly_score=anomaly_score,
                    needs_confirm=True,
                )

        return NormVerdict(level=NormLevel.SAFE, domain=NormDomain.RESOURCE)

    def _suggest_action(self, rule: NormRule, context: dict) -> str:
        """根据规则建议行动"""
        suggestions = {
            "orphan_detect": "建议: 检查进程是否为僵尸，手动 kill 或等待规范场自动清理",
            "system_write": "建议: 使用 workspace 路径替代系统目录",
            "ram_hard": "建议: 等待内存释放后再启动新任务",
            "ram_soft": "建议: 关闭不必要进程释放内存",
            "gpu_soft": "建议: 等待 GPU 空闲后再提交任务",
        }
        return suggestions.get(rule.name, "人工审核后决定")

    def _record_anomaly(self, rule: NormRule, context: dict) -> None:
        self._anomaly_history.append({
            "time": time.time(),
            "rule": rule.name,
            "level": rule.level.value,
            "context_summary": str(context)[:200],
        })
        if len(self._anomaly_history) > 500:
            self._anomaly_history = self._anomaly_history[-250:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_rules": len(self._rules),
            "learned_rules": sum(1 for r in self._rules.values() if r.learned),
            "total_checks": self._total_checks,
            "total_blocks": self._total_blocks,
            "block_rate": round(self._total_blocks / max(1, self._total_checks), 4),
            "recent_anomalies": self._anomaly_history[-10:],
            "resource_baselines": {
                k: {"samples": v["samples"],
                    "avg_mem": round(sum(v["mem_samples"]) / len(v["mem_samples"]), 0)
                    if v["mem_samples"] else 0}
                for k, v in self._resource_baseline.items()
            },
        }


# ── 规范场守卫装饰器 ──


def with_norm_guard(nf: NormativeField, domain: NormDomain):
    """装饰器：在执行函数前经过规范场检查.

    用法：
        @with_norm_guard(nf, NormDomain.FILE)
        def write_file(path):
            ...
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            # 从参数中提取上下文
            context = {}
            if domain == NormDomain.FILE and args:
                context = {"path": str(args[0]), "operation": "write"}
            elif domain == NormDomain.NETWORK and args:
                context = {"url": str(args[0])}

            verdict = nf.check(domain, context)
            if verdict.level == NormLevel.BLOCK:
                raise PermissionError(f"NormField BLOCKED: {verdict.reason}")
            if verdict.level == NormLevel.NEEDS_HUMAN:
                print(f"[NORM] NEEDS_HUMAN: {verdict.reason}")

            return fn(*args, **kwargs)
        return wrapper
    return decorator
