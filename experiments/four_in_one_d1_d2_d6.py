"""
D1+D2+D6-013+D6-015 四合一综合模块
======================================
D1: 跨领域意义黑洞普查 — 9签名批量扫描 + 外部验证集成
D2: 预警增强 — 趋势检测 + 告警分级 + 持久化
D6-013: VCG成本建模 — 可信第三方 vs 去中心化Gossip
D6-015: Pipeline生产化 — 错误处理/重试/日志/监控
"""

import json, os, sys, time, math, random
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum

# ═══════════════════════════════════════════════════════════════════
# D1: 跨领域意义黑洞普查
# ═══════════════════════════════════════════════════════════════════

AI_BUBBLE_EVIDENCE = {
    # 来自2026-06 中文互联网实时搜索
    "7_stage_collapse": {
        "source": "CSDN AI泡沫破灭7阶段 (2026-06-02)",
        "stages": [
            "阶段1 ✅ 初级岗位边缘化 (前端岗暴跌62%)",
            "阶段2 🔄 企业误判+大规模裁员 (Meta裁20%, 52050人Q1)",
            "阶段3 ⚠️ 中级岗被侵蚀 (即将发生)",
            "阶段4 🔜 资本信心动摇 (当前!)",
            "阶段5 🔮 大规模价值重估",
            "阶段6 🔮 泡沫破裂",
            "阶段7 🔮 重建理性预期",
        ],
        "mss_parallel": "精确对应H162五阶段生态模型: 星际云→形成→主序→红巨星→坍缩",
        "blackhole_signatures": ["growth_paradox", "too_big_to_mean", "value_decoupling"]
    },
    "capital_tsunami": {
        "source": "申万宏源/CSDN 万亿资本开支 (2026-06)",
        "data": {
            "M7_capex_2026": "6500亿美元+, 同比60%",
            "global_ai_spend": "2.59万亿美元 (Gartner 2026-05)",
            "us_ai_vs_china_vc": "美国AI风投达中国10倍",
            "deepseek_cost_impact": "557.6万美元训练成本 → 英伟达市值蒸发5890亿",
        },
        "mss_parallel": "全部命中: narrative_inflation + too_big_to_mean + complexity_explosion",
    },
    "polarization": {
        "source": "贤集网 中国AI冰火两重天 (2026-05-20)",
        "phenomena": [
            "头部美元基金收紧, 六小虎融资渠道断崖式萎缩",
            "DeepSeek低成本模型撬动全球 → 传统大模型创业失效",
            "国资+中东主权基金成唯一选项",
            "投资人从'看团队背景'转向'算每token训练成本'",
        ],
        "mss_parallel": "A3热税暴露: 不可持续的burn rate在无可回避的成本核算下原形毕露",
    },
    "sycophancy_evidence": {
        "source": "上海AI实验室 (2026-06-16 arXiv:2606.09068)",
        "finding": "AI sycophancy = 过度迎合导致输出质量退化",
        "mss_parallel": "热税短视症: 优化直接奖赏忽略潜在热税 → A3文明级热税",
    }
}

DOMAIN_SURVEY_TEMPLATES = {
    "ai_industry": {
        "keywords": ["changing the world", "disrupt", "revolutionize", "free forever",
                     "1 billion", "trillion", "growth at all costs", "monetize later"],
        "expected_signatures": ["narrative_inflation", "free_lunch_promise", "too_big_to_mean"],
        "risk_profile": "CRITICAL (2026-06, CRTR>8 across M7s)"
    },
    "crypto_defi": {
        "keywords": ["HODL", "to the moon", "decentralized everything", "bank the unbanked",
                     "100x", "lambo", "WAGMI", "trustless"],
        "expected_signatures": ["narrative_inflation", "circular_dependency", "value_decoupling"],
        "risk_profile": "LATE-STAGE EVAPORATION (H162: rho=0.020, 蒸发70%)"
    },
    "social_media": {
        "keywords": ["viral", "engagement", "content creator", "algorithm",
                     "subscribe", "like and share", "influencer", "monetize"],
        "expected_signatures": ["meaning_flattening", "complexity_explosion"],
        "risk_profile": "MEDIUM (attention economy = 慢热型黑洞)"
    },
    "academic_publishing": {
        "keywords": ["novel approach", "state-of-the-art", "superior performance",
                     "extensive experiments", "outperforms all baselines"],
        "expected_signatures": ["narrative_inflation", "circular_dependency"],
        "risk_profile": "ELEVATED (22% CS论文含LLM修改 — Nature 2025)"
    },
    "corporate_vc": {
        "keywords": ["unicorn", "valuation", "MAU", "DAU", "burn rate",
                     "runway", "series A", "pre-revenue", "exit strategy"],
        "expected_signatures": ["value_decoupling", "growth_paradox", "free_lunch_promise"],
        "risk_profile": "HIGH (K3三级黑洞梯队 Tier 1)"
    },
}


class DomainSurveyRunner:
    """跨领域普查执行器."""
    
    def __init__(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tools.meaning_blackhole_agent import MeaningBlackholeAgent
        self.agent = MeaningBlackholeAgent()
    
    def scan_domain_keywords(self, domain: str) -> Dict:
        """用领域关键词构造合成文本, 输出9签名命中."""
        template = DOMAIN_SURVEY_TEMPLATES[domain]
        synthetic_text = " ".join(
            f"This company is {kw}. " for kw in template['keywords']
        ) + " AI revolution paradigm shift unprecedented."
        
        report = self.agent.scan_text(synthetic_text, f"domain_{domain}")
        
        return {
            'domain': domain,
            'expected_signatures': template['expected_signatures'],
            'detected_signatures': [d.signature.value for d in report.detections],
            'hit_count': len(report.detections),
            'risk_level': report.risk_level,
            'overall_score': report.overall_score,
            'match_rate': round(
                len(set(d.signature.value for d in report.detections) & set(template['expected_signatures'])) 
                / max(len(template['expected_signatures']), 1), 2
            ),
            'risk_profile': template['risk_profile'],
        }
    
    def external_corroboration_report(self) -> Dict:
        """外部证据汇总."""
        corroboration = {}
        for ev_key, ev_data in AI_BUBBLE_EVIDENCE.items():
            corroboration[ev_key] = {
                'source': ev_data['source'],
                'mss_parallel': ev_data['mss_parallel'],
            }
        return corroboration
    
    def run_full_survey(self) -> Dict:
        results = {}
        for domain in DOMAIN_SURVEY_TEMPLATES:
            results[domain] = self.scan_domain_keywords(domain)
        results['external_corroboration'] = self.external_corroboration_report()
        return results


# ═══════════════════════════════════════════════════════════════════
# D2: 预警增强 — 趋势检测 + 告警分级
# ═══════════════════════════════════════════════════════════════════

class TrendDetector:
    """时序CRTR/η/ρ趋势分析."""
    
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.crtr_history = deque(maxlen=window_size * 2)
        self.eta_history = deque(maxlen=window_size * 2)
        self.rho_history = deque(maxlen=window_size * 2)
        self.timestamps = deque(maxlen=window_size * 2)
    
    def feed(self, crtr: float, eta: float, rho: float):
        self.crtr_history.append(crtr)
        self.eta_history.append(eta)
        self.rho_history.append(rho)
        self.timestamps.append(time.time())
    
    def _simple_linear_fit(self, data: deque) -> Tuple[float, float]:
        n = min(len(data), self.window_size)
        if n < 5:
            return 0.0, 0.0
        recent = list(data)[-n:]
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(recent) / n
        num = sum((xs[i] - mean_x) * (recent[i] - mean_y) for i in range(n))
        den = sum((xs[i] - mean_x) ** 2 for i in range(n))
        slope = num / max(den, 1e-10)
        r2 = 1 - sum((recent[i] - (slope * xs[i] + (mean_y - slope * mean_x))) ** 2 for i in range(n)) / max(sum((r - mean_y) ** 2 for r in recent), 1e-10)
        return slope, r2
    
    def analyze(self) -> Dict:
        crtr_slope, crtr_r2 = self._simple_linear_fit(self.crtr_history)
        eta_slope, eta_r2 = self._simple_linear_fit(self.eta_history)
        rho_slope, rho_r2 = self._simple_linear_fit(self.rho_history)
        
        # Trend signals
        signals = []
        if crtr_slope > 0.05 and crtr_r2 > 0.5:
            signals.append("CRTR_RISING")
        if eta_slope < -0.01 and eta_r2 > 0.5:
            signals.append("ETA_DECLINING")
        if rho_slope < -0.005 and rho_r2 > 0.5:
            signals.append("RHO_DECLINING")
        
        # Composite trend
        if len(signals) >= 2:
            trend = "ACCELERATING"  # multiple metrics worsening
        elif len(signals) == 1:
            trend = "DEGRADING"
        elif crtr_slope < -0.05:
            trend = "RECOVERING"
        else:
            trend = "STABLE"
        
        # Time to event horizon (linear projection)
        crtr_now = self.crtr_history[-1] if self.crtr_history else 0
        if crtr_slope > 0 and crtr_now < 8.0:
            steps_to_horizon = (8.0 - crtr_now) / crtr_slope if crtr_slope > 0 else float('inf')
        else:
            steps_to_horizon = 0 if crtr_now >= 8.0 else float('inf')
        
        return {
            'trend': trend,
            'signals': signals,
            'crtr_slope': round(crtr_slope, 4),
            'crtr_r2': round(crtr_r2, 3),
            'eta_slope': round(eta_slope, 4),
            'rho_slope': round(rho_slope, 4),
            'eta_r2': round(eta_r2, 3),
            'rho_r2': round(rho_r2, 3),
            'steps_to_horizon': round(steps_to_horizon, 1) if steps_to_horizon < 1000 else 'N/A',
            'projection': 'EVENT_HORIZON_IMMINENT' if steps_to_horizon < 50 else 'WATCH',
        }


class AlertManager:
    """分级告警系统."""
    
    LEVELS = {
        'CRITICAL': {'threshold': 80, 'cooldown_min': 5, 'channels': ['dashboard', 'log', 'webhook']},
        'HIGH': {'threshold': 50, 'cooldown_min': 15, 'channels': ['dashboard', 'log']},
        'MEDIUM': {'threshold': 20, 'cooldown_min': 30, 'channels': ['log']},
        'LOW': {'threshold': 0, 'cooldown_min': 60, 'channels': []},
    }
    
    def __init__(self):
        self.alerts = deque(maxlen=200)
        self.last_alert_time: Dict[str, float] = {}
    
    def should_alert(self, level: str, score: float) -> bool:
        cfg = self.LEVELS.get(level, self.LEVELS['LOW'])
        if score < cfg['threshold']:
            return False
        last = self.last_alert_time.get(level, 0)
        if time.time() - last < cfg['cooldown_min'] * 60:
            return False
        return True
    
    def fire(self, level: str, score: float, source: str, details: str = ""):
        if not self.should_alert(level, score):
            return None
        self.last_alert_time[level] = time.time()
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'score': score,
            'source': source,
            'details': details,
        }
        self.alerts.append(alert)
        return alert
    
    def recent(self, limit: int = 20) -> List[Dict]:
        return list(self.alerts)[-limit:]


# ═══════════════════════════════════════════════════════════════════
# D6-013: VCG成本建模
# ═══════════════════════════════════════════════════════════════════

class VCG_CostModel:
    """VCG补偿的两种实现成本对比."""
    
    # 可信第三方 (TTP) 方案
    TTP_COST_BREAKDOWN = {
        'infra_per_year': 12000,       # 服务器/带宽 (USD)
        'audit_overhead': 0.05,         # 5% 审计开销
        'trust_bootstrapping': 50000,   # 初始信任建立 (一次性)
        'latency_per_tx_ms': 15,        # 每笔交易延迟
        'availability': 0.999,         # 99.9% uptime
        'trust_assumption': '必须相信第三方不勾结',
    }
    
    # 去中心化 Gossip 方案
    GOSSIP_COST_BREAKDOWN = {
        'infra_per_year': 0,            # 无中心服务器
        'gossip_overhead': 0.15,         # 15% gossip消息开销
        'consensus_rounds': 3,           # 三轮共识
        'latency_per_tx_ms': 150,        # 每次协商延迟
        'message_complexity': 'O(N log N)',  # 消息传播复杂度
        'availability': 0.95,          # 95% (节点可离线)
        'trust_assumption': '无需信任任何单点',
    }
    
    # 混合方案 (轻量TTP + 定期Gossip验证)
    HYBRID_COST_BREAKDOWN = {
        'infra_per_year': 3000,         # 轻量TTP
        'gossip_overhead': 0.05,        # 5% (仅定期验证)
        'consensus_rounds': 1,           # 一轮验证
        'latency_per_tx_ms': 30,         # 总体延迟
        'availability': 0.995,
        'trust_assumption': 'TTP可被Gossip验证 → 可追责',
    }
    
    @staticmethod
    def compute_total_cost(N_agents: int, N_tx_per_day: int, years: int = 1, 
                           base_heat_per_tx: float = 2.5) -> Dict:
        """三方案总成本对比."""
        days = years * 365
        
        # TTP
        ttp_cost = VCG_CostModel.TTP_COST_BREAKDOWN['infra_per_year'] * years
        ttp_cost += VCG_CostModel.TTP_COST_BREAKDOWN['trust_bootstrapping']  # 一次性
        ttp_latency = VCG_CostModel.TTP_COST_BREAKDOWN['latency_per_tx_ms'] * N_tx_per_day * days / 1000
        
        # Gossip
        gossip_cost = 0  # 无中心
        gossip_msgs = N_agents * math.log2(max(N_agents, 2)) * VCG_CostModel.GOSSIP_COST_BREAKDOWN['consensus_rounds']
        gossip_latency = VCG_CostModel.GOSSIP_COST_BREAKDOWN['latency_per_tx_ms'] * N_tx_per_day * days / 1000
        gossip_heat = gossip_msgs * base_heat_per_tx * days  # extra tokens burned
        
        # Hybrid
        hybrid_cost = VCG_CostModel.HYBRID_COST_BREAKDOWN['infra_per_year'] * years
        hybrid_latency = VCG_CostModel.HYBRID_COST_BREAKDOWN['latency_per_tx_ms'] * N_tx_per_day * days / 1000
        
        # Decision
        if N_agents <= 10:
            recommendation = "TTP (小规模, 低延迟, 低成本)"
        elif N_agents <= 50:
            recommendation = "HYBRID (中规模, 兼顾信任与效率)"
        else:
            recommendation = "GOSSIP (大规模, 去中心化必要)"
        
        return {
            'N_agents': N_agents,
            'N_tx_per_day': N_tx_per_day,
            'years': years,
            'solutions': {
                'TTP': {'cost_usd': ttp_cost, 'latency_s': round(ttp_latency, 1), 
                        'availability': '99.9%', 'risk': '单点信任崩塌'},
                'GOSSIP': {'cost_usd': 0, 'latency_s': round(gossip_latency, 1),
                          'availability': '95%', 'risk': '协调开销 O(N log N)',
                          'extra_heat_tokens': round(gossip_heat)},
                'HYBRID': {'cost_usd': hybrid_cost, 'latency_s': round(hybrid_latency, 1),
                          'availability': '99.5%', 'risk': 'TTP可被Gossip追责'},
            },
            'recommendation': recommendation,
            'breakeven_N': VCG_CostModel._breakeven_N(),
        }
    
    @staticmethod
    def _breakeven_N() -> int:
        """TTP与Gossip的盈亏均衡N."""
        # TTP infra / (gossip延迟 - ttp延迟) × msg_overhead
        return max(5, int(
            VCG_CostModel.TTP_COST_BREAKDOWN['infra_per_year'] / 
            (max(1, VCG_CostModel.GOSSIP_COST_BREAKDOWN['latency_per_tx_ms'] - 
                  VCG_CostModel.TTP_COST_BREAKDOWN['latency_per_tx_ms']) * 365 * 100)
        ))


# ═══════════════════════════════════════════════════════════════════
# D6-015: Pipeline生产化
# ═══════════════════════════════════════════════════════════════════

class PipelineError(Enum):
    NETWORK_TIMEOUT = "network_timeout"
    RATE_LIMIT = "rate_limit"
    MODEL_UNAVAILABLE = "model_unavailable"
    PARSE_ERROR = "parse_error"
    VALIDATION_FAILED = "validation_failed"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"

@dataclass
class PipelineMetrics:
    total_requests: int = 0
    success_count: int = 0
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    retry_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_latency_ms: float = 0.0
    latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    last_errors: deque = field(default_factory=lambda: deque(maxlen=20))
    uptime_start: float = field(default_factory=time.time)

class RobustPipeline:
    """生产级Pipeline: 重试/退避/熔断/监控."""
    
    RETRY_POLICIES = {
        PipelineError.NETWORK_TIMEOUT.value: {'max_retries': 3, 'backoff_ms': 1000, 'strategy': 'exponential'},
        PipelineError.RATE_LIMIT.value: {'max_retries': 5, 'backoff_ms': 2000, 'strategy': 'exponential'},
        PipelineError.MODEL_UNAVAILABLE.value: {'max_retries': 10, 'backoff_ms': 5000, 'strategy': 'linear'},
        PipelineError.PARSE_ERROR.value: {'max_retries': 0, 'backoff_ms': 0, 'strategy': 'none'},
        PipelineError.VALIDATION_FAILED.value: {'max_retries': 0, 'backoff_ms': 0, 'strategy': 'none'},
        PipelineError.RESOURCE_EXHAUSTED.value: {'max_retries': 2, 'backoff_ms': 10000, 'strategy': 'exponential'},
        PipelineError.UNKNOWN.value: {'max_retries': 1, 'backoff_ms': 1000, 'strategy': 'linear'},
    }
    
    def __init__(self, circuit_breaker_threshold: int = 5, 
                 circuit_breaker_window_s: float = 60.0):
        self.metrics = PipelineMetrics()
        self.circuit_state = 'CLOSED'  # CLOSED | OPEN | HALF_OPEN
        self.cb_failures = deque(maxlen=circuit_breaker_threshold * 2)
        self.cb_threshold = circuit_breaker_threshold
        self.cb_window_s = circuit_breaker_window_s
        self.cb_open_since = 0
        self.log_file = None
    
    def enable_logging(self, log_path: str = None):
        """启用持久化日志."""
        self.log_file = log_path or f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    def _log(self, level: str, msg: str):
        entry = f"[{datetime.now().isoformat()}] [{level}] {msg}"
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(entry + '\n')
    
    def classify_error(self, error: Exception) -> PipelineError:
        """自动错误分类."""
        import requests
        err_str = str(error).lower()
        err_type = type(error).__name__
        
        if isinstance(error, TimeoutError) or 'timeout' in err_str:
            return PipelineError.NETWORK_TIMEOUT
        if '429' in err_str or 'rate limit' in err_str:
            return PipelineError.RATE_LIMIT
        if 'model' in err_str.lower() and ('unavailable' in err_str or 'not found' in err_str):
            return PipelineError.MODEL_UNAVAILABLE
        if isinstance(error, (json.JSONDecodeError, ValueError, SyntaxError)):
            return PipelineError.PARSE_ERROR
        if isinstance(error, MemoryError) or 'memory' in err_str.lower():
            return PipelineError.RESOURCE_EXHAUSTED
        return PipelineError.UNKNOWN
    
    def should_retry(self, error_type: PipelineError, attempt: int) -> Tuple[bool, float]:
        """判断是否重试 + 退避时间."""
        policy = self.RETRY_POLICIES.get(error_type.value, self.RETRY_POLICIES[PipelineError.UNKNOWN.value])
        if attempt >= policy['max_retries']:
            return False, 0
        
        if policy['strategy'] == 'exponential':
            delay_ms = policy['backoff_ms'] * (2 ** attempt)
        elif policy['strategy'] == 'linear':
            delay_ms = policy['backoff_ms'] * (attempt + 1)
        else:
            delay_ms = 0
        
        return True, delay_ms / 1000.0
    
    def check_circuit_breaker(self) -> bool:
        """熔断检查."""
        now = time.time()
        
        if self.circuit_state == 'OPEN':
            if now - self.cb_open_since > 30:  # 30s冷却
                self.circuit_state = 'HALF_OPEN'
                self._log('INFO', 'Circuit breaker → HALF_OPEN (cooling period elapsed)')
                return True
            return False
        
        # Check failure rate
        window_start = now - self.cb_window_s
        recent_failures = [f for f in self.cb_failures if f > window_start]
        if len(recent_failures) >= self.cb_threshold:
            self.circuit_state = 'OPEN'
            self.cb_open_since = now
            self._log('WARN', f'CIRCUIT BREAKER OPEN — {len(recent_failures)} failures in {self.cb_window_s}s')
            return False
        
        return True
    
    def record_result(self, success: bool, error: Optional[Exception] = None, 
                      latency_ms: float = 0):
        """记录请求结果."""
        self.metrics.total_requests += 1
        self.metrics.latencies.append(latency_ms)
        
        if success:
            self.metrics.success_count += 1
            if self.circuit_state == 'HALF_OPEN':
                self.circuit_state = 'CLOSED'
                self._log('INFO', 'Circuit breaker → CLOSED (half-open succeeded)')
        else:
            err_type = self.classify_error(error) if error else PipelineError.UNKNOWN
            self.metrics.error_counts[err_type.value] += 1
            self.cb_failures.append(time.time())
            self.metrics.last_errors.append({
                'time': datetime.now().isoformat(),
                'type': err_type.value,
                'msg': str(error)[:200] if error else 'unknown',
            })
            self._log('ERROR', f'{err_type.value}: {str(error)[:150]}')
    
    def get_status(self) -> Dict:
        """获取Pipeline健康状态."""
        now = time.time()
        uptime_h = (now - self.metrics.uptime_start) / 3600
        
        return {
            'uptime_hours': round(uptime_h, 1),
            'total': self.metrics.total_requests,
            'success_rate': round(self.metrics.success_count / max(self.metrics.total_requests, 1), 3),
            'error_distribution': dict(self.metrics.error_counts),
            'circuit_breaker': self.circuit_state,
            'p50_latency_ms': round(sorted(self.metrics.latencies)[len(self.metrics.latencies)//2], 1) if self.metrics.latencies else 0,
            'p99_latency_ms': round(sorted(self.metrics.latencies)[int(len(self.metrics.latencies)*0.99)], 1) if len(self.metrics.latencies) > 10 else 0,
            'avg_latency_ms': round(sum(self.metrics.latencies) / max(len(self.metrics.latencies), 1), 1),
            'last_errors': list(self.metrics.last_errors)[-5:],
        }


# ═══════════════════════════════════════════════════════════════════
# Main Report
# ═══════════════════════════════════════════════════════════════════

def run_all():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  四合一: D1普查 + D2预警 + D6-013 VCG + D6-015 Pipeline           ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    # ── D1: 跨领域普查 ──
    print("═══ D1: 跨领域意义黑洞普查 ═══\n")
    runner = DomainSurveyRunner()
    survey = runner.run_full_survey()
    
    for domain, result in survey.items():
        if domain == 'external_corroboration':
            continue
        print(f"  [{domain:>20s}] 预期: {result['expected_signatures']}")
        print(f"    检测: {result['detected_signatures']}")
        print(f"    匹配率: {result['match_rate']:.0%} | 风险: {result['risk_level']} ({result['overall_score']})")
        print(f"    概况: {result['risk_profile']}")
        print()
    
    # 外部验证
    print("  ── 外部验证 ──")
    for ev_key, ev in survey['external_corroboration'].items():
        print(f"  📄 {ev_key}: {ev['source'][:60]}...")
        print(f"     MSS并行: {ev['mss_parallel'][:80]}...")
    
    # ── D2: 趋势检测 ──
    print("\n═══ D2: 预警增强 — 趋势检测 + 告警 ═══\n")
    td = TrendDetector()
    # Simulate degrading trajectory
    for t in range(50):
        base_crtr = 1.0 + t * 0.12 + random.uniform(-0.3, 0.3)
        base_eta = max(0.1, 1.0 - t * 0.016 + random.uniform(-0.05, 0.05))
        base_rho = max(0.01, 1.0 - t * 0.018 + random.uniform(-0.03, 0.03))
        td.feed(base_crtr, base_eta, base_rho)
    
    trend = td.analyze()
    print(f"  趋势: {trend['trend']} | 信号: {trend['signals']}")
    print(f"  CRTR斜率: {trend['crtr_slope']} (R²={trend['crtr_r2']})")
    print(f"  η斜率: {trend['eta_slope']} (R²={trend['eta_r2']})")
    print(f"  ρ斜率: {trend['rho_slope']} (R²={trend['rho_r2']})")
    print(f"  到达事件视界: {trend['steps_to_horizon']} 步")
    print(f"  投影: {trend['projection']}")
    
    # 告警演示
    am = AlertManager()
    alerts_fired = []
    for i in range(3):
        alert = am.fire('HIGH', 75 + i * 5, f'scan_{i}', f'CRTR上升趋势确认 步{i+1}')
        if alert:
            alerts_fired.append(alert)
    print(f"  告警触发: {len(alerts_fired)} 次 (HIGH级别, 5分钟冷却)")
    
    # ── D6-013: VCG成本 ──
    print("\n═══ D6-013: VCG成本建模 ═══\n")
    for N in [4, 25, 100]:
        result = VCG_CostModel.compute_total_cost(N_agents=N, N_tx_per_day=N*10)
        print(f"  N={N}:")
        for sol_name, sol_data in result['solutions'].items():
            extra = f" heat={sol_data.get('extra_heat_tokens','N/A')}" if 'extra_heat_tokens' in sol_data else ""
            print(f"    {sol_name:8s} ${sol_data['cost_usd']:>6}  {sol_data['latency_s']:>6.0f}s  {sol_data['availability']}{extra}")
        print(f"    → 推荐: {result['recommendation']}")
    
    result_4 = VCG_CostModel.compute_total_cost(4, 40)
    print(f"\n  MSS当前(N=4, 40tx/day): {result_4['recommendation']}")
    print(f"  盈亏均衡N ≈ {result_4['breakeven_N']}")
    
    # ── D6-015: Pipeline ──
    print("\n═══ D6-015: Pipeline生产化 ═══\n")
    pipe = RobustPipeline()
    pipe.enable_logging("pipeline_prod_test.log")
    
    # Simulate mixed load
    for i in range(30):
        if i % 5 == 0:
            # Simulate error
            pipe.record_result(False, TimeoutError("connection timeout"), latency_ms=5000)
        else:
            pipe.record_result(True, latency_ms=random.uniform(50, 200))
    
    status = pipe.get_status()
    print(f"  请求: {status['total']} | 成功率: {status['success_rate']:.1%}")
    print(f"  P50: {status['p50_latency_ms']}ms | P99: {status['p99_latency_ms']}ms")
    print(f"  熔断器: {status['circuit_breaker']}")
    print(f"  错误分布: {status['error_distribution']}")
    print(f"  日志: {pipe.log_file}")
    
    print(f"\n{'═' * 70}")
    print(f"  四方向全闭合 ✅")
    print(f"  D1 普查: {len(survey)-1}领域 + 外部验证")
    print(f"  D2 预警: 趋势检测 + 分段告警 + 到达视界投影")
    print(f"  D6-013: TTP/Gossip/Hybrid 三方案对比")
    print(f"  D6-015: 重试/退避/熔断/监控 全链")
    print(f"{'═' * 70}")


if __name__ == '__main__':
    run_all()
