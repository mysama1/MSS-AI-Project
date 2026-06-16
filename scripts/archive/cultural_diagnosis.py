#!/usr/bin/env python3
"""MSS Cultural Diagnosis Toolkit v1.0

可复用的文化产品三层意义场分析框架。
基于 H486(核壳分离定理) + H487(意义真空双重属性) + H488(三重曝光叠加态)

Usage:
  python cultural_diagnosis.py --analyze <product_name>
  python cultural_diagnosis.py --template > template.md
"""

import json, sys, argparse
from typing import Dict, List, Optional, Tuple

# ── 文化产品意义场诊断模型 ──

class MeaningFieldDiagnosis:
    """对单一文化产品进行意义场三层诊断"""
    
    def __init__(self, name: str):
        self.name = name
        self.l1_core: Dict = {}   # L1逻辑核
        self.l2_shell: Dict = {}  # L2叙事壳
        self.l3_projection: Dict = {}  # L3投射层
        self.anchors: List[Dict] = []  # 意义锚点列表
        self.vacuum: Dict = {}    # 意义真空分析
        self.verdict: Dict = {}   # 终审裁定
        
    def set_l1(self, description: str, grade: str = "K3|K4", rigidity: float = 0.0):
        """设定逻辑核：刚性规则系统"""
        self.l1_core = {"description": description, "paradigm": grade, "rigidity": rigidity}
        
    def set_l2(self, description: str, grade: str = "K3|K4", heat_tax: float = 0.0):
        """设定叙事壳：感性表达层"""
        self.l2_shell = {"description": description, "paradigm": grade, "heat_tax": heat_tax}
        
    def set_l3(self, description: str, empathy_index: float = 0.0):
        """设定投射层：当代共鸣"""
        self.l3_projection = {"description": description, "empathy_index": empathy_index}
        
    def add_anchor(self, original: str, reinterpretation: str, tax_reduction: float = 0.0, closure: float = 0.0):
        """添加意义锚点及其重映射"""
        self.anchors.append({
            "original": original,
            "reinterpretation": reinterpretation,
            "heat_tax_reduction": tax_reduction,  # 0-1
            "logical_closure": closure,  # 0-1, 1=完美闭环
        })
        
    def set_vacuum(self, description: str, closure_degree: float = 0.5, is_intentional: bool = False):
        """设定意义真空：半开半闭的动力平衡"""
        self.vacuum = {
            "description": description,
            "closure_degree": closure_degree,  # 0=全开, 1=全闭, 0.5=最优
            "is_intentional": is_intentional,
            "status": "optimal" if 0.4 <= closure_degree <= 0.7 else (
                "over-closed" if closure_degree > 0.7 else "over-open"
            ),
        }
        
    def evaluate(self) -> Dict:
        """综合评估：计算意义密度、热税、范式升维"""
        # 核心指标
        n_anchors = len(self.anchors)
        avg_tax_reduction = sum(a["heat_tax_reduction"] for a in self.anchors) / max(n_anchors, 1)
        avg_closure = sum(a["logical_closure"] for a in self.anchors) / max(n_anchors, 1)
        
        # 意义密度 ρ = Π(E) / min(S)
        empathy = self.l3_projection.get("empathy_index", 0.5)
        heat_tax = max(self.l2_shell.get("heat_tax", 0.5), 0.01)
        meaning_density = empathy / heat_tax
        
        # 范式升维判定
        l2_grade = self.l2_shell.get("paradigm", "K3")
        l1_grade = self.l1_core.get("paradigm", "K3")
        paradigm_shift = "K3→K4" if "K3" in str(l2_grade) and "K4" in str(l1_grade) else (
            "K4→K3" if "K4" in str(l2_grade) and "K3" in str(l1_grade) else "none"
        )
        
        self.verdict = {
            "meaning_density": round(meaning_density, 2),
            "heat_tax_original": self.l2_shell.get("heat_tax", 0.5),
            "heat_tax_after": round(heat_tax * (1 - avg_tax_reduction), 2),
            "tax_reduction_pct": round(avg_tax_reduction * 100, 0),
            "anchor_closure": round(avg_closure, 2),
            "paradigm_shift": paradigm_shift,
            "is_vacuum_optimal": self.vacuum.get("status") == "optimal",
        }
        self.verdict["verdict"] = self._generate_verdict(self.verdict)
        return self.verdict
    
    @staticmethod
    def _generate_verdict(v: dict) -> str:
        # Composite score: density * closure * tax_benefit
        score = v["meaning_density"] * v["anchor_closure"] * (v["tax_reduction_pct"] / 50)
        if score > 1.5 or (v["anchor_closure"] > 0.85 and v["tax_reduction_pct"] > 80):
            return "PERFECT: 教科书级核壳置换案例"
        elif score > 0.8 or (v["anchor_closure"] > 0.7 and v["tax_reduction_pct"] > 50):
            return "STRONG: 显著的意义密度提升"
        elif score > 0.3:
            return "MODERATE: 有意义的重新诠释"
        else:
            return "WEAK: 硬套，意义密度无实质提升"
    
    def to_report(self) -> str:
        """生成人类可读的MSS诊断报告"""
        v = self.verdict or self.evaluate()
        lines = [
            f"# MSS 意义场诊断报告: {self.name}",
            "",
            "## L1 逻辑核",
            f"- 描述: {self.l1_core.get('description', 'N/A')}",
            f"- 刚性等级: {self.l1_core.get('rigidity', 'N/A')}",
            "",
            "## L2 叙事壳",
            f"- 原壳: {self.l2_shell.get('description', 'N/A')}",
            f"- 原壳热税: {self.l2_shell.get('heat_tax', 'N/A')}",
            "",
            f"## L3 投射层",
            f"- 当代共鸣: {self.l3_projection.get('description', 'N/A')}",
            f"- 共情指数: {self.l3_projection.get('empathy_index', 'N/A')}",
            "",
            "## 意义锚点",
        ]
        for i, a in enumerate(self.anchors, 1):
            lines.append(f"{i}. {a['original']} → {a['reinterpretation']}")
            lines.append(f"   热税降低 {a['heat_tax_reduction']*100:.0f}% | 逻辑闭合 {a['logical_closure']*100:.0f}%")
        
        lines += [
            "",
            "## 意义真空",
            f"- 闭合度: {self.vacuum.get('closure_degree', 'N/A')} ({self.vacuum.get('status', 'N/A')})",
            f"- 是否为创作意图: {'是' if self.vacuum.get('is_intentional') else '否'}",
            f"- 描述: {self.vacuum.get('description', 'N/A')}",
            "",
            "## 诊断结果",
            f"- 意义密度: {v['meaning_density']}",
            f"- 热税: {v['heat_tax_original']} → {v['heat_tax_after']} (降低 {v['tax_reduction_pct']:.0f}%)",
            f"- 锚点闭合: {v['anchor_closure']}",
            f"- 范式升维: {v['paradigm_shift']}",
            f"- 真空状态: {'✅ 最优' if v['is_vacuum_optimal'] else '⚠️ 需调整'}",
            "",
            f"**终审裁定**: {v['verdict']}",
        ]
        return "\n".join(lines)


# ── 预设诊断模板 ──

PRESETS = {
    "final_destination": {
        "name": "《死神来了》二创闭环",
        "l1": ("名单会计学+优先级队列+临界点触发（与工业文明编程/会计/KPI完全同构）", "K4", 0.95),
        "l2": ("哥特宗教叙事：死神/命运/地狱（K3神秘主义）", "K3", 0.90),
        "l3": ("大厂打工人：KPI/排程/对账/末位淘汰", 0.98),
        "anchors": [
            ("Death.programs()", "因果编译器/排程脚本", 0.90, 0.95),
            ("Balance the books", "KPI对账/坏账回收", 0.85, 0.90),
            ("Rube Goldberg链式反应", "最小扰动注入/伪装成自然事故", 0.80, 1.00),
            ("预知能力", "debug log只读权限泄漏", 0.95, 0.95),
            ("跳过机制", "队列迭代器指针移动", 0.90, 1.00),
            ("死神不露脸", "后台守护进程无UI", 0.85, 0.90),
        ],
        "vacuum": ("预知能力的起源故意不解释，保持神秘", 0.60, True),
    },
    "squid_game": {
        "name": "《鱿鱼游戏》MSS解读",
        "l1": ("多轮淘汰制竞技+零和博弈+规则强制执行", "K4", 0.85),
        "l2": ("儿童游戏+死亡惩罚+神秘富人组织（K3恐怖寓言）", "K3", 0.70),
        "l3": ("HR末位淘汰模拟：季度考核→PIP→优化", 0.90),
        "anchors": [
            ("123木头人", "入职培训/试用期考核", 0.70, 0.80),
            ("弹珠游戏", "同事竞争/内部排序", 0.75, 0.85),
            ("最后幸存者胜出", "唯一转正名额", 0.80, 0.75),
        ],
        "vacuum": ("谁在运营这个游戏？富人动机始终模糊", 0.55, True),
    },
}


# ── CLI ──

def main():
    ap = argparse.ArgumentParser(description="MSS Cultural Diagnosis Toolkit")
    ap.add_argument("--analyze", "-a", help="Product name (preset)")
    ap.add_argument("--template", "-t", action="store_true", help="Generate analysis template")
    ap.add_argument("--list", "-l", action="store_true", help="List available presets")
    ap.add_argument("--json", "-j", action="store_true", help="JSON output")
    args = ap.parse_args()
    
    if args.list:
        for name, preset in PRESETS.items():
            print(f"  {name}: {preset['name']}")
        return
    
    if args.template:
        print("""# MSS 意义场诊断模板

## L1 逻辑核
- 什么是这个文化产品的刚性规则系统？
- 它的底层逻辑是什么？（会计/编程/KPI/算法/...）
- 范式等级: K3（神秘主义/宿命论）还是 K4（系统决定论）？

## L2 叙事壳
- 原作用什么方式包装这个逻辑核？
- 这个壳的热税有多高？（需要多少"愿意相信"的代价？）
- 壳的时效性：当代人还能共情吗？

## L3 投射层  
- 当代人会把什么经验投射到这个作品上？
- 共情触发点在哪？（KPI焦虑/系统无力/被优化恐惧/...）
- 这个投射是"硬套"还是"自然坍缩"？

## 意义锚点
| 原作锚点 | 重解释 | 热税降低 | 逻辑闭合 |
|----------|--------|----------|----------|
| ...      | ...    | ...      | ...      |

## 意义真空
- 作品留下的解释缺口是什么？
- 闭合度: 0~1 (最优范围 0.4~0.7)
- 是否是创作者故意保留的？""")
        return
    
    if args.analyze:
        name = args.analyze
        preset = PRESETS.get(name)
        
        if not preset:
            print(f"Unknown preset: {name}")
            print("Available:", ", ".join(PRESETS.keys()))
            sys.exit(1)
        
        d = MeaningFieldDiagnosis(preset["name"])
        d.set_l1(*preset["l1"])
        d.set_l2(*preset["l2"])
        d.set_l3(*preset["l3"])
        for anchor in preset["anchors"]:
            d.add_anchor(*anchor)
        d.set_vacuum(*preset["vacuum"])
        result = d.evaluate()
        
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(d.to_report())
        return
    
    ap.print_help()

if __name__ == "__main__":
    main()
