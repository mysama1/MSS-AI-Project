#!/usr/bin/env python3
"""
MSS 组织韧性扫描器 v15.1
基于 v15.1 六公理 + 三层归因模型, 从热税/意义势能/创新率/韧性指数四维评估组织健康度。
100% 自包含, 无外部依赖。输入为 JSON 部门数据, 输出诊断+建议。
"""
import json, math, argparse, sys, os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ── v15.1 公理引用 ──
A1 = "意义本体公理: 意义是客观存在的实体, 不可被创造或消灭, 仅可被损耗或转移"
A2 = "物理投影公理: L1逻辑层独立于物理层, 物理层是L1的投影而非支撑"
A3 = "不可约化热税公理: 任何操作都会产生不可逆的热税, 无操作也会累积热税"
A6 = "矛盾升维公理: 矛盾不可在原层解决, 必须升维到更高层寻找方案"

CALIBRATION = {
    "O_d_base": 0.12,
    "O_d_per_approval": 0.07,
    "O_d_per_meeting_h": 0.015,
    "phi_per_satisfaction": 12.0,
    "phi_per_headcount": 0.4,
    "gamma_base": 0.08,
    "R_threshold": 0.35,
    "RESILIENCE_A": 0.80,
    "RESILIENCE_B": 0.55,
    "RESILIENCE_C": 0.30,
    # ── 三层调谐度校准 ──
    "H_max_i": 120.0,               # 个体认知带宽 (bits/s, Miller修正)
    "H_max_o_base": 200.0,          # 组织信息承载力基数
    "H_max_c_base": 1000.0,         # 文明信息承载力基数
    "T_threshold_high": 0.70,
    "T_threshold_medium": 0.50,
    "T_threshold_low": 0.30,
    "T_blackhole": 0.15,            # 意义黑洞阈值
    "T_o_peak_low": 0.25,           # T_o 峰值 O_d 下界
    "T_o_peak_high": 0.40,          # T_o 峰值 O_d 上界
    # 向上涌现权重
    "w_leader": 0.40,               # 高层 T_i 权重
    "w_middle": 0.35,               # 中层 T_i 权重
    "w_base": 0.25,                 # 基层 T_i 权重
}

# ── 个体 T_i 显化信号权重 (8信号) ──
TI_SIGNAL_WEIGHTS = {
    "deep_work_hrs":     0.20,  # 深度工作时长/天
    "anti_consensus":     0.18,  # 反共识表达频率
    "creation_ratio":     0.15,  # 创造/消费比
    "metacognition":      0.14,  # 元认知频率
    "long_read":          0.12,  # 长文本完读率
    "decision_delay":     0.10,  # 决策延迟容忍 (小时)
    "emotion_granularity":0.06,  # 情绪粒度 (词汇量/40)
    "sleep_quality":      0.05,  # 睡眠质量 (PSQI倒数)
}

DEPT_WEIGHTS = {
    "RND": 1.5, "PRODUCT": 1.3, "STRATEGY": 1.2,
    "SALES": 1.0, "OPERATIONS": 0.9, "ADMIN": 0.6,
}

DEPT_NAMES = {
    "RND": "研发", "PRODUCT": "产品", "STRATEGY": "战略",
    "SALES": "销售", "OPERATIONS": "运营", "ADMIN": "行政支撑",
}

# ── 数据模型 ──

@dataclass
class DeptMetrics:
    dept_id: str; dept_name: str; dept_type: str
    O_d: float = 0.0; phi: float = 100.0; gamma: float = 0.0; R: float = 1.0
    headcount: int = 0; approval_layers: int = 0; meeting_h: float = 0.0
    lead_time_days: float = 0.0; satisfaction: float = 5.0


@dataclass
class OrgSnapshot:
    snapshot_id: str; timestamp: str
    departments: Dict[str, DeptMetrics] = field(default_factory=dict)
    O_d: float = 0.0; phi: float = 100.0; gamma: float = 0.0; R: float = 1.0
    M: float = 0.0; grade: str = "UNKNOWN"
    diagnosis: List[dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    T_o: float = 0.0          # 组织调谐度
    T_o_grade: str = "?"
    T_i_leaders: Dict[str, float] = field(default_factory=dict)  # 领导层个体 T_i
    H_org: float = 0.0        # 组织健康度综合指标


@dataclass
class TuningSignals:
    """个体调谐度 8 条显化信号"""
    label: str = ""
    deep_work_hrs: float = 0.0       # 日均深度工作时长 (h)
    anti_consensus: float = 0.0       # 反共识表达 (次/月, 归一化到[0,1])
    creation_ratio: float = 0.0       # 创造/消费比 [0,1]
    metacognition: float = 0.0        # 元认知频率 (次/天, 归一化到[0,1])
    long_read: float = 0.0            # 长文本完读率 [0,1]
    decision_delay: float = 0.0       # 决策延迟容忍 (h, 归一化到[0,1])
    emotion_granularity: float = 0.0  # 情绪粒度 [0,1]
    sleep_quality: float = 0.0        # 睡眠质量 [0,1]


# ── 三层调谐度计算器 ──

class TuningDegreeCalculator:
    """v15.1 三层调谐度计算器"""
    
    @staticmethod
    def individual(signals: TuningSignals) -> dict:
        """计算个体调谐度 T_i ∈ [0,1]"""
        # 归一化: 将原始信号映射到 [0,1]
        norm = {
            'deep_work_hrs':      min(1.0, signals.deep_work_hrs / 8.0),
            'anti_consensus':     min(1.0, signals.anti_consensus / 12.0),
            'creation_ratio':     min(1.0, signals.creation_ratio),
            'metacognition':      min(1.0, signals.metacognition / 5.0),
            'long_read':          min(1.0, signals.long_read),
            'decision_delay':     min(1.0, signals.decision_delay / 48.0),
            'emotion_granularity': min(1.0, signals.emotion_granularity),
            'sleep_quality':      min(1.0, signals.sleep_quality),
        }
        
        total_w = 0.0
        weighted_sum = 0.0
        breakdown = {}
        for f, nv in norm.items():
            w = TI_SIGNAL_WEIGHTS.get(f, 0.1)
            weighted_sum += nv * w
            total_w += w
            breakdown[f] = round(nv * w, 3)
        
        T_i = round(weighted_sum / total_w, 4) if total_w > 0 else 0.0
        
        if T_i < CALIBRATION["T_blackhole"]:
            grade = "BLACKHOLE"
        elif T_i < CALIBRATION["T_threshold_low"]:
            grade = "LOW"
        elif T_i < CALIBRATION["T_threshold_medium"]:
            grade = "MEDIUM"
        elif T_i < CALIBRATION["T_threshold_high"]:
            grade = "HIGH"
        else:
            grade = "PEAK"
        
        return {
            "T_i": T_i, "grade": grade,
            "breakdown": breakdown,
            "risk": T_i < CALIBRATION["T_blackhole"],
            "label": signals.label or "anonymous",
        }
    
    @staticmethod
    def organizational(snapshot: OrgSnapshot) -> dict:
        """
        计算组织调谐度 T_o
        T_o = (Φ/Φ_max)^α × (1-O_d)^β × (R/R_max)^γ
        且含 T_i_leaders 加权贡献
        """
        alpha, beta, gamma_w = 0.4, 0.35, 0.25
        phi_norm = min(snapshot.phi / 200.0, 1.0)
        od_inv = max(0.01, 1.0 - snapshot.O_d)
        r_norm = min(snapshot.R / 0.7, 1.0)
        
        T_o_structure = (phi_norm ** alpha) * (od_inv ** beta) * (r_norm ** gamma_w)
        
        # 如果有领导层 T_i, 加权融合
        if snapshot.T_i_leaders:
            w_total = 0.0
            t_leader = 0.0
            for label, ti in snapshot.T_i_leaders.items():
                w = CALIBRATION.get("w_leader", 0.4)
                t_leader += ti * w
                w_total += w
            if w_total > 0:
                T_o_people = t_leader / w_total
                T_o = round(0.5 * T_o_structure + 0.5 * T_o_people, 4)
            else:
                T_o = round(T_o_structure, 4)
        else:
            T_o = round(T_o_structure, 4)
        
        # 规范场抑制: O_d > 0.6 时强制拉低
        if snapshot.O_d > 0.6:
            T_o *= max(0.3, 1.0 - (snapshot.O_d - 0.6))
        
        T_o = round(min(1.0, max(0.0, T_o)), 4)
        
        if T_o < CALIBRATION["T_blackhole"]:
            grade = "BLACKHOLE"
        elif T_o < CALIBRATION["T_threshold_low"]:
            grade = "LOW"
        elif T_o < CALIBRATION["T_threshold_medium"]:
            grade = "MEDIUM"
        elif T_o < CALIBRATION["T_threshold_high"]:
            grade = "HIGH"
        else:
            grade = "PEAK"
        
        # 混沌边缘检测
        at_edge = CALIBRATION["T_o_peak_low"] <= snapshot.O_d <= CALIBRATION["T_o_peak_high"]
        
        return {
            "T_o": T_o, "grade": grade,
            "T_o_structure": T_o_structure,
            "at_chaos_edge": at_edge,
            "phi_factor": phi_norm,
            "od_inv_factor": od_inv,
            "r_factor": r_norm,
        }
    
    @staticmethod
    def relationship(snapshot: OrgSnapshot) -> dict:
        """计算 T_o 与其他指标的关系网"""
        T_o = snapshot.T_o
        M = snapshot.M
        O_d = snapshot.O_d
        
        meaning_efficiency = round(T_o / max(M, 0.01), 2)  # 意义效率
        
        # 诊断关系
        if T_o > M + 0.2:
            mode = "HIGH_T_LOW_M"  # 有灵魂但快死
        elif M > T_o + 0.2:
            mode = "HIGH_M_LOW_T"  # 高效但盲目
        elif T_o < CALIBRATION["T_blackhole"] and M < 0.3:
            mode = "BLACKHOLE"      # 双低 — 意义黑洞
        else:
            mode = "BALANCED"       # 相对平衡
        
        return {
            "meaning_efficiency": meaning_efficiency,
            "mode": mode,
            "T_o_vs_M_delta": round(T_o - M, 4),
            "health_index": round((T_o + M) / 2, 4),  # H_org
        }


# ── 扫描器 ──

class OrgResilienceScanner:
    """v15.1 组织韧性扫描器"""
    
    def compute_dept(self, data: dict) -> DeptMetrics:
        dtype = data.get("dept_type", "ADMIN")
        layers = data.get("approval_layers", 3)
        mtg_h = data.get("meeting_hours_weekly", 12.0)
        lt = data.get("project_lead_time", 30.0)
        sat = data.get("employee_satisfaction", 5.0)
        hc = data.get("headcount", 10)
        
        # 规范场强 O_d ∈ [0,1] — 越高越官僚
        O_d = CALIBRATION["O_d_base"]
        O_d += layers * CALIBRATION["O_d_per_approval"]
        O_d += mtg_h * CALIBRATION["O_d_per_meeting_h"]
        O_d += max(0, (lt - 30) / 400)  # 长交付周期惩罚
        O_d = round(min(1.0, O_d), 4)
        
        # 意义势能 φ — 越高越好
        phi = CALIBRATION["phi_per_satisfaction"] * sat
        phi += CALIBRATION["phi_per_headcount"] * hc
        phi *= DEPT_WEIGHTS.get(dtype, 1.0)
        phi = round(max(0, phi), 2)
        
        # 热税系数 γ
        gamma = round(CALIBRATION["gamma_base"] * math.exp(2.5 * O_d), 4)
        
        # 创新率 R
        R = round((phi / 120.0) * max(0.05, 1.0 - O_d), 4)
        
        return DeptMetrics(
            dept_id=data.get("dept_id","?"), dept_name=data.get("dept_name","?"),
            dept_type=dtype, O_d=O_d, phi=phi, gamma=gamma, R=R,
            headcount=hc, approval_layers=layers, meeting_h=mtg_h,
            lead_time_days=lt, satisfaction=sat,
        )
    
    def scan(self, org_data: dict) -> OrgSnapshot:
        snap = OrgSnapshot(
            snapshot_id=f"ORG-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            timestamp=datetime.now().isoformat(),
        )
        
        total_wO, total_wp, total_w = 0.0, 0.0, 0.0
        for d in org_data.get("departments", []):
            m = self.compute_dept(d)
            snap.departments[m.dept_id] = m
            w = DEPT_WEIGHTS.get(m.dept_type, 1.0)
            total_wO += m.O_d * w; total_wp += m.phi * w; total_w += w
        
        if total_w > 0:
            snap.O_d = round(total_wO / total_w, 4)
            snap.phi = round(total_wp / total_w, 2)
        
        snap.gamma = round(CALIBRATION["gamma_base"] * math.exp(2.5 * snap.O_d), 4)
        snap.R = round((snap.phi / 140.0) * max(0.05, 1.0 - snap.O_d), 4)
        
        # 韧性指数 M = φ × (1-O_d) × R × (1-γ/γ_max) / 4
        gamma_max = CALIBRATION["gamma_base"] * math.exp(2.5)
        M = (snap.phi / 200) * (1 - snap.O_d) * (snap.R / 0.5) * max(0, 1 - snap.gamma / gamma_max)
        snap.M = round(min(1.0, max(0, M)), 4)
        
        if snap.M >= CALIBRATION["RESILIENCE_A"]:
            snap.grade = "A"
        elif snap.M >= CALIBRATION["RESILIENCE_B"]:
            snap.grade = "B"
        elif snap.M >= CALIBRATION["RESILIENCE_C"]:
            snap.grade = "C"
        else:
            snap.grade = "D"
        
        snap.diagnosis = self._diagnose(snap)
        snap.recommendations = self._recommend(snap)
        
        # 计算组织调谐度
        tcalc = TuningDegreeCalculator()
        td = tcalc.organizational(snap)
        snap.T_o = td["T_o"]
        snap.T_o_grade = td["grade"]
        
        # 计算关系网
        rel = tcalc.relationship(snap)
        snap.H_org = rel["health_index"]
        
        return snap
    
    def _diagnose(self, s: OrgSnapshot) -> list:
        d = []
        if s.O_d > 0.55:
            d.append({"level":"CRITICAL","layer":"L1","category":"规范场强过高",
                "msg":f"O_d={s.O_d:.2f} — 组织规范场强超过不可逆临界点, 创新空间被压缩"})
        elif s.O_d > 0.40:
            d.append({"level":"WARN","layer":"L1","category":"规范场强偏高",
                "msg":f"O_d={s.O_d:.2f} — 建议压缩审批层级和会议时长"})
        
        if s.phi < 50:
            d.append({"level":"CRITICAL","layer":"L1","category":"意义势能过低",
                "msg":f"Φ={s.phi:.1f} — 员工满意度和创新动力严重不足 (A1)"})
        elif s.phi < 80:
            d.append({"level":"WARN","layer":"L1","category":"意义势能偏低",
                "msg":f"Φ={s.phi:.1f} — 建议提升组织活力 (A1)"})
        
        if s.R < CALIBRATION["R_threshold"]:
            d.append({"level":"WARN","layer":"L2","category":"创新率不足",
                "msg":f"R={s.R:.3f} — 低于警戒线, 组织可能陷入K3热寂同化 (A3+A6)"})
        
        # 部门瓶颈检测
        for did, m in s.departments.items():
            if m.O_d > s.O_d + 0.15:
                d.append({"level":"WARN","layer":"L3","category":"部门瓶颈",
                    "msg":f"{m.dept_name}: O_d={m.O_d:.2f} 显著高于全局 {s.O_d:.2f} — 组织瓶颈 (A6)"})
        
        return d
    
    def _recommend(self, s: OrgSnapshot) -> list:
        recs = []
        if s.O_d > 0.50:
            recs.append("【L1-紧急】压缩审批至≤2层, 推行异步协作替代同步会议")
        if s.phi < 80:
            recs.append("【L1-重要】开展意义对齐工作坊, 建立内部创新基金")
        if s.R < 0.35:
            recs.append("【L2-重要】激活矛盾上报通道, 引入外部共创 (A6升维)")
        if s.grade == "D":
            recs.append("【生死线】组织已进入热寂临界 — 必须重组架构/更换领导层/引入外部冲击 (A3)")
        elif s.grade == "C":
            recs.append("【预警】3个月内完成规范场优化, 否则进入D级")
        if not recs:
            recs.append("【健康】组织韧性良好, 保持开放性和创新活力")
        return recs
    
    def trend(self, snap_a: OrgSnapshot, snap_b: OrgSnapshot) -> dict:
        dM = round(snap_b.M - snap_a.M, 4)
        return {
            "M_delta": dM,
            "grade_delta": f"{snap_a.grade}→{snap_b.grade}",
            "trend": "improving" if dM > 0 else "declining" if dM < 0 else "stable",
            "O_d_delta": round(snap_b.O_d - snap_a.O_d, 4),
            "phi_delta": round(snap_b.phi - snap_a.phi, 2),
        }


# ── CLI ──

DEMO_ORG = {
    "org_name": "示例科技公司",
    "departments": [
        {"dept_id":"D01","dept_name":"研发中心","dept_type":"RND","headcount":45,"approval_layers":2,"meeting_hours_weekly":8,"project_lead_time":35,"employee_satisfaction":8.2},
        {"dept_id":"D02","dept_name":"产品部","dept_type":"PRODUCT","headcount":20,"approval_layers":3,"meeting_hours_weekly":12,"project_lead_time":28,"employee_satisfaction":7.5},
        {"dept_id":"D03","dept_name":"运营中心","dept_type":"OPERATIONS","headcount":30,"approval_layers":4,"meeting_hours_weekly":18,"project_lead_time":14,"employee_satisfaction":6.8},
        {"dept_id":"D04","dept_name":"行政支撑","dept_type":"ADMIN","headcount":15,"approval_layers":5,"meeting_hours_weekly":6,"project_lead_time":7,"employee_satisfaction":6.5},
        {"dept_id":"D05","dept_name":"战略部","dept_type":"STRATEGY","headcount":8,"approval_layers":2,"meeting_hours_weekly":5,"project_lead_time":60,"employee_satisfaction":8.5},
    ]
}

def main():
    ap = argparse.ArgumentParser(description='MSS 组织韧性扫描器 v15.1')
    ap.add_argument('file', nargs='?', help='JSON 部门数据文件')
    ap.add_argument('--demo', action='store_true', help='运行演示')
    ap.add_argument('--json', action='store_true', help='JSON 输出')
    ap.add_argument('--tuning', action='store_true', help='输出完整调谐度分析')
    ap.add_argument('--individual', nargs=8, metavar=('DW','AC','CR','MC','LR','DD','EG','SQ'),
                    type=float, help='8个个体T_i信号: 深度工作 反共识 创造比 元认知 长文本 延迟容忍 情绪粒度 睡眠')
    args = ap.parse_args()
    
    scanner = OrgResilienceScanner()
    tcalc = TuningDegreeCalculator()
    
    # 个体调谐度
    if args.individual:
        vals = args.individual
        s = TuningSignals(
            label="用户输入",
            deep_work_hrs=vals[0], anti_consensus=vals[1],
            creation_ratio=vals[2], metacognition=vals[3],
            long_read=vals[4], decision_delay=vals[5],
            emotion_granularity=vals[6], sleep_quality=vals[7],
        )
        r = tcalc.individual(s)
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            print(f"个体调谐度: T_i={r['T_i']:.3f} [{r['grade']}]")
            print(f"{'风险: 接近意义黑洞!' if r['risk'] else '状态: 安全'}")
            for k, v in r['breakdown'].items():
                print(f"  {k:20s} {v:.3f}")
        return
    
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        args.demo = True
        data = DEMO_ORG
    
    snap = scanner.scan(data)
    
    if args.json:
        rel = tcalc.relationship(snap)
        out = {
            'org_name': data.get('org_name','?'),
            'snapshot': snap.snapshot_id,
            'timestamp': snap.timestamp,
            'global': {'O_d':snap.O_d,'phi':snap.phi,'gamma':snap.gamma,'R':snap.R,'M':snap.M,'grade':snap.grade},
            'tuning': {'T_o':snap.T_o,'T_o_grade':snap.T_o_grade,'H_org':snap.H_org},
            'departments': {k:{'name':v.dept_name,'type':v.dept_type,'O_d':v.O_d,'phi':v.phi,'R':v.R} for k,v in snap.departments.items()},
            'diagnosis': snap.diagnosis,
            'recommendations': snap.recommendations,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"组织: {data.get('org_name','?')}")
        print(f"  O_d={snap.O_d:.2f}  Φ={snap.phi:.1f}  γ={snap.gamma:.3f}  R={snap.R:.3f}  M={snap.M:.3f}  [{snap.grade}级]")
        if args.tuning:
            print(f"\n🎯 调谐度分析:")
            print(f"  T_o={snap.T_o:.3f} [{snap.T_o_grade}]  |  健康度 H_org={snap.H_org:.3f}")
            rel = tcalc.relationship(snap)
            mode_map = {
                "HIGH_T_LOW_M": "⚠️ 有灵魂但快死 — 意义密度高但韧性不足",
                "HIGH_M_LOW_T": "⚠️ 高效但盲目 — 运转良好但缺乏方向",
                "BLACKHOLE": "❌ 意义黑洞 — 双低, 接近热寂临界",
                "BALANCED": "✅ 相对平衡",
            }
            print(f"  模式: {mode_map.get(rel['mode'], rel['mode'])}")
            print(f"  意义效率: {rel['meaning_efficiency']}")
        print(f"\n诊断 ({len(snap.diagnosis)}):")
        for d in snap.diagnosis:
            print(f"  [{d['level']:8s}] {d['category']}: {d['msg'][:80]}")
        print(f"\n建议:")
        for r in snap.recommendations:
            print(f"  • {r[:80]}")

if __name__ == '__main__':
    main()
