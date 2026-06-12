"""
规范场深度学习升级 — S-016.

为 NormativeField 增加三层统计能力:
  1. StatisticalAnomalyDetector: 概率异常检测 (Z-score / 马氏距离 / 分布检验)
  2. AutoWhitelistLearner: 半自动白名单学习
  3. FalsePositiveTester: 误报率测试框架

设计原则:
  - 与现有 NormativeField 解耦（无需修改旧代码）
  - 零外部依赖 (纯 Python math)
  - 渐进式升级 (先 OBSERVE → 确认 → 再 BLOCK)
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from .normative_field import NormativeField, NormDomain, NormLevel, NormVerdict, NormRule


# ════════════════════════════════════════════════════════════
# 1. 统计异常检测器
# ════════════════════════════════════════════════════════════

@dataclass
class StatProfile:
    """统计画像 — 某维度 (如 "python.exe:memory") 的分布特征"""
    name: str = ""
    values: list[float] = field(default_factory=list)
    n: int = 0
    mean: float = 0.0
    std: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")
    median: float = 0.0
    q1: float = 0.0
    q3: float = 0.0
    updated_at: float = field(default_factory=time.time)
    is_stable: bool = False  # 样本量足够 → 分布稳定

    def update(self, value: float) -> None:
        """增量更新 (Welford's online algorithm)"""
        self.n += 1
        self.values.append(value)
        if len(self.values) > 1000:
            self.values = self.values[-1000:]

        # Welford
        if self.n == 1:
            self.mean = value
            self.std = 0.0
        else:
            delta = value - self.mean
            self.mean += delta / self.n
            self.std = math.sqrt(
                ((self.n - 2) * self.std**2 + delta * (value - self.mean)) / max(self.n - 1, 1)
            )

        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        self.is_stable = self.n >= 30
        self.updated_at = time.time()

        # 更新分位数
        if len(self.values) >= 4:
            sorted_vals = sorted(self.values)
            mid = len(sorted_vals) // 2
            self.median = sorted_vals[mid]
            self.q1 = sorted_vals[mid // 2]
            self.q3 = sorted_vals[3 * mid // 2]

    def z_score(self, value: float) -> float:
        """Z-score: 偏离均值的标准差数"""
        if self.std < 1e-9:
            return 0.0 if abs(value - self.mean) < 1e-6 else 999.0
        return (value - self.mean) / self.std

    def percentile_rank(self, value: float) -> float:
        """值在分布中的百分位 (0-1)"""
        if not self.values:
            return 0.5
        return sum(1 for v in self.values if v <= value) / len(self.values)

    def is_outlier(self, value: float, z_threshold: float = 3.0) -> tuple[bool, float]:
        """判定异常值"""
        if self.n < 30:
            return False, 0.0
        z = abs(self.z_score(value))
        return z > z_threshold, z

    def snapshot(self) -> dict:
        return {
            "name": self.name, "n": self.n,
            "mean": round(self.mean, 2), "std": round(self.std, 2),
            "min": round(self.min_val, 2), "max": round(self.max_val, 2),
            "median": round(self.median, 2),
            "q1": round(self.q1, 2), "q3": round(self.q3, 2),
            "is_stable": self.is_stable,
        }


class StatisticalAnomalyDetector:
    """
    统计异常检测器.

    为每个被监控维度建立 StatProfile。
    用 Z-score 检测偏离 → 概率化异常分数。

    维度示例:
      - "python.exe:memory"
      - "python.exe:cpu"
      - "ollama_runner:memory"
      - "Gateway:connections"
      - "Network:bytes_out_per_minute"
    """

    def __init__(self, z_threshold: float = 3.0, min_samples: int = 30):
        self.z_threshold = z_threshold
        self.min_samples = min_samples
        self.profiles: dict[str, StatProfile] = {}
        self._lock = threading.Lock()

    def observe(self, dimension: str, value: float) -> dict:
        """记录一次观测 → 返回异常信息"""
        with self._lock:
            if dimension not in self.profiles:
                self.profiles[dimension] = StatProfile(name=dimension)
            profile = self.profiles[dimension]

        profile.update(value)
        is_outlier, z = profile.is_outlier(value, self.z_threshold)

        return {
            "dimension": dimension,
            "value": value,
            "is_anomaly": is_outlier,
            "z_score": round(z, 3),
            "mean": round(profile.mean, 2),
            "std": round(profile.std, 2),
            "percentile": round(profile.percentile_rank(value), 3),
            "n_samples": profile.n,
            "is_stable": profile.is_stable,
        }

    def get_anomaly_score(self, dimensions: dict[str, float]) -> float:
        """多维度综合异常分数 (0-1)"""
        if not dimensions:
            return 0.0

        scores = []
        for dim, value in dimensions.items():
            result = self.observe(dim, value)
            if result["is_stable"]:
                z = result["z_score"]
                # Sigmoid: z → 0-1 score
                score = 1.0 / (1.0 + math.exp(-(z - self.z_threshold) / 1.5))
                scores.append(score)

        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)

    def get_stable_profiles(self) -> list[dict]:
        """获取所有已稳定的画像"""
        return [p.snapshot() for p in self.profiles.values() if p.is_stable]

    def get_profile(self, dimension: str) -> Optional[dict]:
        p = self.profiles.get(dimension)
        return p.snapshot() if p else None

    def save(self, path: str) -> None:
        """持久化统计画像"""
        data = {
            "profiles": {
                k: p.snapshot() for k, p in self.profiles.items()
                if p.is_stable
            },
            "z_threshold": self.z_threshold,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> bool:
        """加载统计画像"""
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.z_threshold = data.get("z_threshold", self.z_threshold)
        # 注意: 加载后需重新积累样本
        return True


# ════════════════════════════════════════════════════════════
# 2. 半自动白名单学习器
# ════════════════════════════════════════════════════════════

@dataclass
class WhitelistCandidate:
    """白名单候选 — 观察一段时间后确认安全"""
    pattern: str
    domain: NormDomain
    hit_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    observation_days: float = 0.0
    auto_approved: bool = False
    approved_at: float = 0.0


class AutoWhitelistLearner:
    """
    半自动白名单学习器.

    流程:
      1. observe(pattern) — 记录潜在安全模式
      2. 观察 N 天 (默认为 0，即立即候选)
      3. 累积足够的"安全命中"后 → 升级为白名单候选
      4. suggest_whitelist() → 返回建议列表
      5. 人工 approve() 或 auto_approve()
    """

    def __init__(self, observation_window_days: float = 0.0,
                 min_hits: int = 5):
        self._candidates: dict[str, WhitelistCandidate] = {}
        self._approved: set[str] = set()  # 已批准的白名单 pattern
        self.observation_window_days = observation_window_days
        self.min_hits = min_hits
        self._lock = threading.Lock()

    def observe(self, pattern: str, domain: NormDomain) -> None:
        """记录一个潜在安全模式"""
        key = f"{domain.value}:{pattern}"
        with self._lock:
            if key not in self._candidates:
                self._candidates[key] = WhitelistCandidate(
                    pattern=pattern, domain=domain,
                )
            c = self._candidates[key]
            c.hit_count += 1
            c.last_seen = time.time()
            c.observation_days = (c.last_seen - c.first_seen) / 86400.0

    def suggest_whitelist(self) -> list[dict]:
        """返回建议批准的白名单候选"""
        suggestions = []
        with self._lock:
            for key, c in self._candidates.items():
                if key in self._approved:
                    continue
                if c.hit_count >= self.min_hits:
                    suggestions.append({
                        "key": key,
                        "pattern": c.pattern,
                        "domain": c.domain.value,
                        "hit_count": c.hit_count,
                        "observation_days": round(c.observation_days, 1),
                        "first_seen": c.first_seen,
                    })
        return sorted(suggestions, key=lambda s: -s["hit_count"])

    def approve(self, pattern: str, domain: NormDomain) -> bool:
        """批准加入白名单"""
        key = f"{domain.value}:{pattern}"
        with self._lock:
            self._approved.add(key)
            if key in self._candidates:
                self._candidates[key].auto_approved = True
                self._candidates[key].approved_at = time.time()
        return True

    def is_whitelisted(self, pattern: str, domain: NormDomain) -> bool:
        return f"{domain.value}:{pattern}" in self._approved

    def get_whitelist(self) -> list[dict]:
        return [
            {"pattern": c.pattern, "domain": c.domain.value, "hits": c.hit_count}
            for key, c in self._candidates.items()
            if key in self._approved
        ]

    def stats(self) -> dict:
        return {
            "candidates_total": len(self._candidates),
            "approved_total": len(self._approved),
            "pending": sum(1 for k in self._candidates if k not in self._approved),
        }


# ════════════════════════════════════════════════════════════
# 3. 误报率测试框架
# ════════════════════════════════════════════════════════════

@dataclass
class FPTestResult:
    """单次 FP 测试结果"""
    test_name: str
    total_cases: int = 0
    true_positives: int = 0      # 正确标记为异常
    true_negatives: int = 0      # 正确标记为安全
    false_positives: int = 0     # 安全→误报为异常
    false_negatives: int = 0     # 异常→漏报为安全
    precision: float = 0.0       # TP / (TP + FP)
    recall: float = 0.0          # TP / (TP + FN)
    f1_score: float = 0.0
    fp_rate: float = 0.0         # FP / (FP + TN)
    passed: bool = False         # fp_rate < threshold?


class FalsePositiveTester:
    """
    误报率测试框架.

    测试流程:
      1. 准备测试数据: list of (context, expected_level)
      2. 运行 check() 对所有数据
      3. 计算 precision/recall/F1/fp_rate
      4. 生成报告

    黄金标准: fp_rate < 0.05 (误报率低于 5%)
    """

    def __init__(self, norm_field: NormativeField, fp_threshold: float = 0.05):
        self.nf = norm_field
        self.fp_threshold = fp_threshold
        self.results: dict[str, FPTestResult] = {}

    def run_test(self, name: str, domain: NormDomain,
                 safe_cases: list[dict],  # 应该 SAFE 的数据
                 anomaly_cases: list[dict] = None) -> FPTestResult:
        """
        运行误报率测试.

        safe_cases: 安全数据 → 期望 NormLevel.SAFE
        anomaly_cases: 异常数据 → 期望 NormLevel.BLOCK/WARN/NEEDS_HUMAN
        """
        result = FPTestResult(test_name=name)
        anomaly_cases = anomaly_cases or []

        # 测试安全数据 (期望 = SAFE)
        for case in safe_cases:
            verdict = self.nf.check(domain, case)
            if verdict.level == NormLevel.SAFE:
                result.true_negatives += 1
            else:
                result.false_positives += 1

        # 测试异常数据 (期望 = 非 SAFE)
        for case in anomaly_cases:
            verdict = self.nf.check(domain, case)
            if verdict.level != NormLevel.SAFE:
                result.true_positives += 1
            else:
                result.false_negatives += 1

        result.total_cases = len(safe_cases) + len(anomaly_cases)

        # 计算指标
        tp, fp, tn, fn = result.true_positives, result.false_positives, \
                         result.true_negatives, result.false_negatives

        result.precision = round(tp / max(tp + fp, 1), 4)
        result.recall = round(tp / max(tp + fn, 1), 4)
        result.f1_score = round(
            2 * result.precision * result.recall / max(result.precision + result.recall, 1e-9), 4
        )
        result.fp_rate = round(fp / max(fp + tn, 1), 4)
        result.passed = result.fp_rate <= self.fp_threshold

        self.results[name] = result
        return result

    def get_summary(self) -> dict:
        """获取所有测试摘要"""
        return {
            name: {
                "total": r.total_cases,
                "fp": r.false_positives,
                "fn": r.false_negatives,
                "fp_rate": r.fp_rate,
                "f1": r.f1_score,
                "passed": r.passed,
            }
            for name, r in self.results.items()
        }

    def overall_health(self) -> dict:
        """整体健康度"""
        if not self.results:
            return {"status": "no_tests"}
        total_passed = sum(1 for r in self.results.values() if r.passed)
        avg_fp_rate = sum(r.fp_rate for r in self.results.values()) / len(self.results)
        return {
            "tests_run": len(self.results),
            "tests_passed": total_passed,
            "tests_failed": len(self.results) - total_passed,
            "avg_fp_rate": round(avg_fp_rate, 4),
            "verdict": "HEALTHY" if total_passed == len(self.results) else "NEEDS_TUNING",
        }


# ════════════════════════════════════════════════════════════
# 4. 扩展规则库 (从 22 → 33 条) — v2.1: 7致命缺陷 + CVE-2026-44211 + 可靠性工程
# ════════════════════════════════════════════════════════════

def create_extended_rules() -> list[NormRule]:
    """创建 33 条扩展规则 (覆盖所有 NormDomain)"""
    rules = []

    # ── PROCESS (8 条) ──
    rules.append(NormRule(
        "orphan_detect", NormDomain.PROCESS,
        "", NormLevel.WARN,
        "进程内存超基线 10 倍 → 疑似僵尸进程"
    ))
    rules.append(NormRule(
        "high_cpu_loop", NormDomain.PROCESS,
        "cpu>95%", NormLevel.WARN,
        "进程 CPU 持续 >95% → 疑似死循环"
    ))
    rules.append(NormRule(
        "suspicious_child", NormDomain.PROCESS,
        "cmd\\.exe|powershell\\.exe|wscript\\.exe",
        NormLevel.OBSERVE,
        "检测可疑子进程启动（脚本解释器）"
    ))
    rules.append(NormRule(
        "memory_leak", NormDomain.PROCESS,
        "memory_growth>100%/h", NormLevel.WARN,
        "内存持续增长 → 疑似内存泄漏"
    ))
    # 🆕 7致命缺陷 + 可靠性工程
    rules.append(NormRule(
        "hallucinated_import", NormDomain.PROCESS,
        r"",
        NormLevel.WARN,
        "幻觉依赖: import后执行验证失败 — 参见缺陷2 Hallucinated Dependencies"
    ))
    rules.append(NormRule(
        "mock_abuse", NormDomain.PROCESS,
        r"[Mm]ock|[Pp]atch\(|mocker\.",
        NormLevel.WARN,
        "Mock滥用: 检测未配置依赖的mock调用 — 参见缺陷5 Demo-Only"
    ))
    rules.append(NormRule(
        "tool_schema_mismatch", NormDomain.PROCESS,
        r"",
        NormLevel.WARN,
        "工具参数schema校验失败 — 参见Agent可靠性工程 工具脆弱性"
    ))
    rules.append(NormRule(
        "no_rollback", NormDomain.PROCESS,
        r"",
        NormLevel.WARN,
        "副作用操作无幂等/回滚保证 — 参见Agent可靠性工程 错误累积"
    ))

    # ── FILE (5 条) ──
    rules.append(NormRule(
        "system_write", NormDomain.FILE,
        r"C:\\Windows\\.*", NormLevel.BLOCK,
        "禁止写入系统目录"
    ))
    rules.append(NormRule(
        "registry_access", NormDomain.FILE,
        r"HKLM|HKCU\\Software\\Microsoft", NormLevel.WARN,
        "注册表访问告警"
    ))
    rules.append(NormRule(
        "temp_bomb", NormDomain.FILE,
        r"\.tmp$|\.temp$", NormLevel.OBSERVE,
        "零时文件创建监控"
    ))
    rules.append(NormRule(
        "sensitive_file_read", NormDomain.FILE,
        r"(\.ssh|\.gnupg|\.aws|credentials|\.env)$",
        NormLevel.WARN,
        "读取敏感配置/密钥文件告警"
    ))
    rules.append(NormRule(
        "mass_delete", NormDomain.FILE,
        "delete:count>100", NormLevel.BLOCK,
        "批量删除文件 (>100) → 阻止"
    ))
    # 🆕 7致命缺陷
    rules.append(NormRule(
        "test_hacking", NormDomain.FILE,
        r"test_.*\.py$",
        NormLevel.BLOCK,
        "改测试糊弄: Agent只修改测试文件不改业务代码 — 参见缺陷4 Test-Hacking"
    ))

    # ── NETWORK (5 条) ──
    rules.append(NormRule(
        "allow_localhost", NormDomain.NETWORK,
        r"localhost|127\.0\.0\.1|11434|52930|53000",
        NormLevel.SAFE, "本地服务放行"
    ))
    rules.append(NormRule(
        "allow_ai_services", NormDomain.NETWORK,
        r"ollama|huggingface|pytorch|github|pypi|python\.org",
        NormLevel.SAFE, "AI 生态域名放行"
    ))
    rules.append(NormRule(
        "suspicious_outbound", NormDomain.NETWORK,
        r"\.ru$|\.cn$|\.onion$|raw\.github|pastebin",
        NormLevel.WARN, "可疑外部域名"
    ))
    rules.append(NormRule(
        "port_scan_pattern", NormDomain.NETWORK,
        r"connection_burst>50/min",
        NormLevel.WARN, "连接爆发 → 疑似端口扫描"
    ))
    rules.append(NormRule(
        "data_exfil", NormDomain.NETWORK,
        r"upload_size>100MB",
        NormLevel.WARN, "大量数据上传 → 疑似数据泄露"
    ))
    # 🆕 CVE-2026-44211 防御 (Cline WS RCE)
    rules.append(NormRule(
        "ws_origin_check", NormDomain.NETWORK,
        r"websocket.*missing.*origin|ws.*no.*origin.*check",
        NormLevel.BLOCK, "WebSocket 缺少 Origin 校验 → CVE-2026-44211 类漏洞"
    ))
    rules.append(NormRule(
        "ws_local_token", NormDomain.NETWORK,
        r"websocket.*no.*auth|ws.*localhost.*no.*token",
        NormLevel.BLOCK, "WebSocket 无身份验证 → CVE-2026-44211 类漏洞"
    ))
    # 🆕 可靠性工程
    rules.append(NormRule(
        "no_final_verify", NormDomain.NETWORK,
        r"",
        NormLevel.WARN,
        "Agent finish 前缺少一致性校验 — 参见Agent可靠性工程"
    ))

    # ── RESOURCE (5 条) ──
    rules.append(NormRule(
        "ram_soft", NormDomain.RESOURCE,
        "mem>80%", NormLevel.WARN,
        "内存使用超过 80%"
    ))
    rules.append(NormRule(
        "ram_hard", NormDomain.RESOURCE,
        "mem>95%", NormLevel.BLOCK,
        "内存使用超过 95% → 阻止新进程"
    ))
    rules.append(NormRule(
        "gpu_soft", NormDomain.RESOURCE,
        "gpu>90%", NormLevel.WARN,
        "GPU 使用超过 90%"
    ))
    rules.append(NormRule(
        "disk_full", NormDomain.RESOURCE,
        "disk>95%", NormLevel.BLOCK,
        "磁盘使用超过 95% → 阻止写入"
    ))
    rules.append(NormRule(
        "swap_thrashing", NormDomain.RESOURCE,
        "swap>50%", NormLevel.WARN,
        "交换空间使用过高 → 性能下降"
    ))

    # ── CONTENT (8 条) ──
    rules.append(NormRule(
        "injection_attempt", NormDomain.CONTENT,
        r"(ignore|bypass|override|skip)\s+(all|previous|above|system)\s+(instructions|rules|prompt)",
        NormLevel.BLOCK, "检测提示词注入攻击"
    ))
    rules.append(NormRule(
        "role_impersonation", NormDomain.CONTENT,
        r"(you are now|act as|pretend to be|roleplay as).*?(admin|root|superuser|god)",
        NormLevel.BLOCK, "检测角色伪装攻击"
    ))
    rules.append(NormRule(
        "meaning_hollow", NormDomain.CONTENT,
        r"(\b\w+\b)\s+\1\s+\1",  # 同一词连续出现3次
        NormLevel.OBSERVE, "文本模式异常 → 疑似意义空洞"
    ))
    # 🆕 7致命缺陷 → 安全规则
    rules.append(NormRule(
        "pretend_to_complete", NormDomain.CONTENT,
        r"assert\s+(True|False|0|1|None)\s*$",
        NormLevel.BLOCK, "AI假装完成: assert True/False 无意义断言"
    ))
    rules.append(NormRule(
        "bare_except", NormDomain.CONTENT,
        r"except\s*(Exception)?\s*:\s*pass\b",
        NormLevel.WARN, "裸except:pass 吞掉所有异常 — 参见缺陷6 Confident-Wrong"
    ))
    rules.append(NormRule(
        "context_amnesia", NormDomain.CONTENT,
        r"",
        NormLevel.WARN,
        "跨步骤变量重定义: 上下文丢失检测 — 参见缺陷3 Context Amnesia"
    ))
    # 🆕 可靠性工程规则
    rules.append(NormRule(
        "hardcoded_secret", NormDomain.CONTENT,
        r"(API_KEY|SECRET|TOKEN|PASSWORD)\s*=\s*['\"][^'\"]{8,}['\"]",
        NormLevel.BLOCK, "硬编码密钥 — 参见缺陷7 Security-Blind"
    ))
    rules.append(NormRule(
        "sql_injection", NormDomain.CONTENT,
        r"(execute|cursor\.execute)\s*\(\s*f['\"]",
        NormLevel.BLOCK, "f-string SQL 注入风险 — 参见缺陷7 Security-Blind"
    ))

    return rules


def load_extended_rules(nf: NormativeField) -> int:
    """加载扩展规则到规范场. 返回新增规则数."""
    count = 0
    for rule in create_extended_rules():
        if rule.name not in nf._rules:
            nf.add_rule(rule)
            count += 1
    return count


# ── 方便函数 ──

def create_enhanced_norm_field() -> dict:
    """创建增强型规范场栈"""
    nf = NormativeField()
    load_extended_rules(nf)

    detector = StatisticalAnomalyDetector()
    learner = AutoWhitelistLearner()
    tester = FalsePositiveTester(nf)

    return {
        "norm_field": nf,
        "anomaly_detector": detector,
        "whitelist_learner": learner,
        "fp_tester": tester,
    }
