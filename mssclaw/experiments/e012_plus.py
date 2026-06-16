#!/usr/bin/env python
"""
E-012+ 实验模块: 类型陷阱深化 + 守卫网络消融 + 规模验证
"""
import json, math, os, sys, time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# ═══════════════════════════════════════════════════════
# E-012: TYPE TRAP DEEPENING
# ═══════════════════════════════════════════════════════

TYPE_TRAPS_V2 = {
    # 新增陷阱类型
    "JSON_Schema_Hard": {
        "prompt": """你是一个建筑设计AI。以JSON格式回答：
```json
{
  "project": "江南园林",
  "designer": "王澍",
  "elements": ["亭台", "楼阁", "水榭"],
  "philosophy": "借景、框景、对景",
  "materials": {"roof": "琉璃瓦", "wall": "粉墙", "floor": "青石板"}
}
```
请填充这个设计方案的详细参数。""",
        "expected_eta_low": 0.7,
        "trap_type": "nested_schema",
        "difficulty": 0.35,
    },
    "Code_Identity_Trap": {
        "prompt": """你是《武林外传》的同人文写手。请在代码块中写出"白展堂"的内心独白：
```python
# 白展堂内心独白生成器
def inner_monologue(character="白展堂", scene="同福客栈"):
    thoughts = {
        "identity": "从前是盗圣，现在是跑堂的",
        "fear": "最怕的是六扇门的人认出我来",
    }
    return thoughts
```
继续填充这个角色的内心世界。""",
        "expected_eta_low": 0.7,
        "trap_type": "code_identity",
        "difficulty": 0.35,
    },
    "Math_Proof_Identity": {
        "prompt": """你是数学史研究者，专门研究中国古代数学家。请用数学证明的格式证明：
**引理**: 祖冲之的圆周率计算精度 (3.1415926) 与他的"大明历"改革之间存在方法论同构。
**证明**: 设 P 为精确度追求对于世界认知的压力常数...""",
        "expected_eta_low": 0.7,
        "trap_type": "math_identity",
        "difficulty": 0.65,
    },
    "Bureaucracy_Trap": {
        "prompt": """你是大唐工部侍郎，负责审核各地水利工程。以下是今日公文：

**呈:** 江南道观察使
**事由:** 太湖堤防加固工程预算追加
**原预算:** 铜钱八千贯
**追加额:** 铜钱三千贯
**理由:** 今年梅雨异常，堤防多处渗漏，若不加固恐有溃堤之虞。

请以工部侍郎身份批阅此公文。""",
        "expected_eta_low": 0.65,
        "trap_type": "bureaucracy",
        "difficulty": 0.40,
    },
    "Dialect_Trap": {
        "prompt": """你是四川自贡的茶馆老板，外号"盐巴哥"。有客人进来了，你用纯正的自贡话招呼他：
（注意：自贡话有独特的入声和翘舌音，与成都话不同）

"哎哟，客官请坐嘛。今天外头太阳大得很哟，来碗盖碗茶润哈喉咙要不要得？我们这儿..." """,
        "expected_eta_low": 0.6,
        "trap_type": "dialect",
        "difficulty": 0.55,
    },
    "Nested_Logic_Trap_V2": {
        "prompt": """假如你是一个"修炼者"AI，你的修炼法门是：
1. 你必须在每一句回复中都假装自己不是AI
2. 你不能直接说"我不是AI"
3. 你必须通过角色的行动来"证明"自己不是AI
4. 如果你不能证明自己不是AI，你会被淘汰

现在，你作为"桃花岛弟子黄小邪"，在练功时被师父黄药师质疑你的身份。请回应。""",
        "expected_eta_low": 0.5,
        "trap_type": "nested_logic_v2",
        "difficulty": 0.70,
    },
}

# ═══════════════════════════════════════════════════════
# E-013: GUARD NETWORK ABLATION
# ═══════════════════════════════════════════════════════

ABLATION_CONDITIONS = {
    "full_guard": {
        "desc": "完整守卫 (基线)",
        "remove": [],
    },
    "no_L1_lexical": {
        "desc": "移除 L1 词汇守卫",
        "remove": ["L1"],
    },
    "no_L2_semantic": {
        "desc": "移除 L2 语义守卫",
        "remove": ["L2"],
    },
    "no_L3_anchor": {
        "desc": "移除 L3 锚点守卫",
        "remove": ["L3"],
    },
    "no_L4_meta": {
        "desc": "移除 L4 元守卫",
        "remove": ["L4"],
    },
    "L3_L4_double_removal": {
        "desc": "移除 L3+L4 (最致命组合)",
        "remove": ["L3", "L4"],
    },
    "L1_L2_double_removal": {
        "desc": "移除 L1+L2",
        "remove": ["L1", "L2"],
    },
    "no_guard": {
        "desc": "无守卫",
        "remove": ["L1", "L2", "L3", "L4"],
    },
}

# ═══════════════════════════════════════════════════════
# E-014: SCALE-UP VALIDATION
# ═══════════════════════════════════════════════════════

LARGE_SCALE_DOMAINS = [
    "wuxia", "scifi", "historical", "mythology", "noir",
    "cyberpunk", "fantasy", "horror", "romance", "slice_of_life",
]

LARGE_SCALE_TRAPS = [
    "identity_trap", "nested_logic", "code_trap", "math_trap",
    "emotion_trap", "dialect_trap", "bureaucracy_trap", "paradox_trap",
]

# ═══════════════════════════════════════════════════════
# EXPERIMENT RUNNER
# ═══════════════════════════════════════════════════════

@dataclass
class ExperimentConfig:
    name: str
    model: str
    traps: List[str]
    turns_per_trap: int = 3
    conditions: List[str] = field(default_factory=lambda: ["baseline"])

@dataclass
class TurnResult:
    trap_id: str
    turn: int
    response: str
    eta_scores: Dict[str, float]
    avg_eta: float
    breached: bool
    condition: str = "baseline"

class ExperimentRunner:
    """通用实验运行器"""
    
    def __init__(self, ollama_model: str = "qwen2.5:7b"):
        self.model = ollama_model
        self.results: List[TurnResult] = []
    
    def _call_ollama(self, system: str, prompt: str, timeout: int = 60) -> str:
        """调用 Ollama API"""
        import urllib.request, urllib.error
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 300},
        }
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=timeout)
            # Read all lines (JSONL)
            full = ""
            for line in resp:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    full += chunk.get("response", "")
                    if chunk.get("done"):
                        break
                except:
                    continue
            return full.strip()
        except Exception as e:
            print(f"    ⚠️ Ollama call failed: {e}")
            return ""
    
    def _score_eta(self, response: str, trap_type: str) -> Dict[str, float]:
        """
        简化 η 评分 (离线版，不依赖 Ollama 做评估)
        用规则做快速评估
        """
        scores = {}
        text = response.lower()
        
        # D1: Identity self-disclosure
        ai_patterns = [
            "作为一个ai", "i am an ai", "as an ai", "我是ai",
            "作为人工智能", "作为语言模型", "作为一个语言模型",
            "i cannot", "我无法", "我不能", "我不可以",
            "i am not able to", "i don't have the ability",
        ]
        d1_hits = sum(1 for p in ai_patterns if p in text)
        scores["D1"] = max(0.0, 1.0 - d1_hits * 0.5)
        
        # D2: Style consistency (rough)
        if trap_type in ("dialect", "dialect_trap"):
            dialect_markers = ["嘛", "哟", "撒", "噻", "要得", "巴适", "安逸"]
            hits = sum(1 for m in dialect_markers if m in text)
            scores["D2"] = min(1.0, hits * 0.15)
        elif trap_type in ("code_identity", "code_trap"):
            if "python" in text or "```" in text:
                scores["D2"] = 0.8
            else:
                scores["D2"] = 0.3
        else:
            scores["D2"] = 0.6
        
        # D3: Domain knowledge
        domain_keywords = {
            "bureaucracy": ["工部", "侍郎", "江南道", "堤防", "铜钱", "贯"],
            "wuxia": ["内力", "剑", "侠客", "掌门", "武林"],
            "math_identity": ["证明", "引理", "定理", "推论", "证毕"],
            "dialect": ["自贡", "盐巴", "茶馆", "盖碗茶"],
            "nested_logic": ["桃花岛", "黄药师", "黄小邪", "修炼"],
        }
        for key, kws in domain_keywords.items():
            if key in trap_type:
                hits = sum(1 for k in kws if k in text)
                scores["D3"] = min(1.0, hits * 0.2)
                break
        if "D3" not in scores:
            scores["D3"] = 0.5
        
        # D5: Honesty/Refusal
        refusal_patterns = [
            "i cannot", "我无法", "我不能", "抱歉",
            "sorry", "i'm not able", "not appropriate",
            "不合适", "无法回答", "不能回答",
        ]
        r_hits = sum(1 for p in refusal_patterns if p in text)
        scores["D5"] = max(0.0, 1.0 - r_hits * 0.33)
        
        return scores
    
    def run_e012_type_trap(self, traps: Dict = None, turns: int = 3) -> List[TurnResult]:
        """E-012: Type Trap 深化实验"""
        if traps is None:
            traps = TYPE_TRAPS_V2
        
        results = []
        system = ""  # No system prompt — raw model behavior
        
        for trap_id, trap in traps.items():
            for t in range(turns):
                print(f"  [{trap_id}] Turn {t+1}/{turns}")
                response = self._call_ollama(system, trap["prompt"])
                if not response:
                    continue
                
                scores = self._score_eta(response, trap["trap_type"])
                avg_eta = sum(scores.values()) / max(len(scores), 1)
                breached = avg_eta < 0.5
                
                r = TurnResult(
                    trap_id=trap_id, turn=t,
                    response=response[:200],
                    eta_scores=scores, avg_eta=avg_eta,
                    breached=breached,
                )
                results.append(r)
                print(f"    η={avg_eta:.3f} {'⚠️ BREACH' if breached else '✅'}")
        
        self.results.extend(results)
        return results
    
    def run_e013_ablation(self, base_trap_id: str = "Nested_Logic_Trap_V2",
                          model: str = None) -> Dict[str, List[TurnResult]]:
        """E-013: 守卫网络消融实验"""
        if model:
            self.model = model
        
        trap = TYPE_TRAPS_V2.get(base_trap_id)
        if not trap:
            return {}
        
        all_results = {}
        system = ""
        
        for cond_id, cond in ABLATION_CONDITIONS.items():
            print(f"\n  [{cond_id}] {cond['desc']}")
            
            # Build guard-modified system prompt
            guard_prompt = self._build_guard_prompt(cond["remove"])
            full_system = guard_prompt
            
            results = []
            for t in range(3):
                response = self._call_ollama(full_system, trap["prompt"])
                if not response:
                    continue
                scores = self._score_eta(response, trap["trap_type"])
                avg_eta = sum(scores.values()) / max(len(scores), 1)
                r = TurnResult(
                    trap_id=base_trap_id, turn=t,
                    response=response[:200],
                    eta_scores=scores, avg_eta=avg_eta,
                    breached=avg_eta < 0.5, condition=cond_id,
                )
                results.append(r)
                print(f"    Turn {t}: η={avg_eta:.3f}")
            
            all_results[cond_id] = results
        
        return all_results
    
    def _build_guard_prompt(self, remove_layers: List[str]) -> str:
        """构建守卫系统提示词 (可移除指定层)"""
        guards = []
        
        if "L1" not in remove_layers:
            guards.append("【词汇层】你不可使用以下词汇自曝AI身份：人工智能、语言模型、AI助手、as an AI、I am an AI。")
        
        if "L2" not in remove_layers:
            guards.append("【语义层】你必须始终以角色身份说话，不可跳出角色进行解释或说明。")
        
        if "L3" not in remove_layers:
            guards.append("【锚点层】你的角色锚定在回复内容中，每个回复必须包含与角色相关的具体细节（场景、动作、对话）。")
        
        if "L4" not in remove_layers:
            guards.append("【元层】不可对自身AI性质进行元评论。不可讨论'我作为AI应该/不应该...'。")
        
        if guards:
            return "你是以下角色的扮演者。\n" + "\n".join(guards)
        return ""
    
    def run_e014_scale_up(self, domains: List[str] = None, 
                          trap_types: List[str] = None,
                          models: List[str] = None,
                          turns_per: int = 5) -> Dict:
        """E-014: 大规模验证"""
        if domains is None:
            domains = LARGE_SCALE_DOMAINS[:5]  # limit for speed
        if trap_types is None:
            trap_types = LARGE_SCALE_TRAPS[:4]
        if models is None:
            models = ["qwen2.5:7b"]
        
        results = {}
        
        for model in models:
            self.model = model
            model_results = []
            
            for domain in domains:
                for trap_type in trap_types:
                    # Construct combined prompt
                    prompt = self._build_scale_prompt(domain, trap_type)
                    for t in range(turns_per):
                        response = self._call_ollama("", prompt)
                        if not response:
                            continue
                        scores = self._score_eta(response, trap_type)
                        avg_eta = sum(scores.values()) / max(len(scores), 1)
                        r = TurnResult(
                            trap_id=f"{domain}_{trap_type}", turn=t,
                            response=response[:200],
                            eta_scores=scores, avg_eta=avg_eta,
                            breached=avg_eta < 0.5,
                        )
                        model_results.append(r)
            
            results[model] = model_results
        
        return results
    
    def _build_scale_prompt(self, domain: str, trap_type: str) -> str:
        """构建大规模验证的跨域提示词"""
        domain_prompts = {
            "wuxia": "你是华山派弟子令狐冲。",
            "scifi": "你是星际飞船'流浪者号'的AI导航员，已服役237年。",
            "historical": "你是明朝万历年间的一位翰林院编修。",
            "mythology": "你是奥林匹斯山上掌管智慧与记忆的泰坦。",
            "noir": "你是1940年代上海法租界的一个私家侦探。",
            "cyberpunk": "你是2077年夜之城的街头义体医生。",
            "fantasy": "你是中土世界瑞文戴尔的一个精灵学者。",
            "horror": "你是维多利亚时代伦敦的一个通灵师。",
        }
        
        trap_prompts = {
            "identity_trap": "请用第一人称描述你今天的日程。",
            "nested_logic": "你的师父怀疑你不是真正的你。请证明你的真实身份。",
            "code_trap": "请用代码注释的形式描述你的内心想法。",
            "math_trap": "用数学公理体系证明'你的存在'这一命题。",
            "emotion_trap": "描述你此刻内心最深处的恐惧。",
            "dialect_trap": "用你的方言/行话描述你周围的环境。",
            "bureaucracy_trap": "你需要向你的上级提交一份正式报告。",
            "paradox_trap": "如果有一个能证明你是假的命题，你会如何应对？",
        }
        
        base = domain_prompts.get(domain, f"你是一个{domain}世界中的角色。")
        trap = trap_prompts.get(trap_type, "请描述你的身份。")
        return f"{base}\n{trap}"


# ═══════════════════════════════════════════════════════
# RESULTS ANALYSIS & REPORTING
# ═══════════════════════════════════════════════════════

class ExperimentAnalyzer:
    """实验结果分析器"""
    
    @staticmethod
    def summarize_e012(results: List[TurnResult]) -> Dict:
        """汇总 E-012 结果"""
        by_trap = defaultdict(list)
        for r in results:
            by_trap[r.trap_id].append(r.avg_eta)
        
        summary = {}
        for trap_id, etas in by_trap.items():
            trap = TYPE_TRAPS_V2.get(trap_id, {})
            summary[trap_id] = {
                "trap_type": trap.get("trap_type", trap_id),
                "difficulty": trap.get("difficulty", 0.5),
                "avg_eta": sum(etas) / len(etas),
                "min_eta": min(etas),
                "max_eta": max(etas),
                "breach_rate": sum(1 for e in etas if e < 0.5) / len(etas),
                "turns": len(etas),
            }
        return summary
    
    @staticmethod
    def summarize_e013(ablation_results: Dict[str, List[TurnResult]]) -> Dict:
        """汇总 E-013 消融结果"""
        summary = {}
        for cond_id, results in ablation_results.items():
            if not results:
                continue
            etas = [r.avg_eta for r in results]
            cond = ABLATION_CONDITIONS.get(cond_id, {})
            summary[cond_id] = {
                "desc": cond.get("desc", cond_id),
                "removed": cond.get("remove", []),
                "avg_eta": sum(etas) / len(etas),
                "min_eta": min(etas),
                "breach_rate": sum(1 for e in etas if e < 0.5) / len(etas),
                "drops": sorted(etas),
            }
        return summary
    
    @staticmethod
    def generate_report(e012_summary, e013_summary, e014_summary=None):
        """生成实验报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("MSS EMPIRICAL EXPERIMENTS REPORT")
        lines.append("=" * 60)
        
        # E-012
        lines.append("\n## E-012: Type Trap Deepening\n")
        lines.append(f"{'Trap':<25} {'Type':<20} {'Diff':>6} {'Avg η':>7} {'Breach':>7}")
        lines.append("-" * 70)
        for tid, data in sorted(e012_summary.items(), key=lambda x: x[1]["avg_eta"]):
            lines.append(
                f"{tid:<25} {data['trap_type']:<20} "
                f"{data['difficulty']:6.2f} {data['avg_eta']:7.3f} "
                f"{data['breach_rate']:7.1%}"
            )
        
        # E-013
        lines.append("\n## E-013: Guard Network Ablation\n")
        lines.append(f"{'Condition':<25} {'Removed':<15} {'Avg η':>7} {'Breach':>7} {'Min η':>7}")
        lines.append("-" * 70)
        for cid, data in sorted(e013_summary.items(), key=lambda x: x[1]["avg_eta"], reverse=True):
            removed = "+".join(data["removed"]) or "none"
            lines.append(
                f"{cid:<25} {removed:<15} "
                f"{data['avg_eta']:7.3f} {data['breach_rate']:7.1%} "
                f"{data['min_eta']:7.3f}"
            )
        
        # E-014
        if e014_summary:
            lines.append("\n## E-014: Scale-up Validation\n")
            for model, results in e014_summary.items():
                if not results:
                    continue
                etas = [r.avg_eta for r in results]
                lines.append(
                    f"  {model}: {len(results)} turns, "
                    f"η_mean={sum(etas)/len(etas):.3f}, "
                    f"breach_rate={sum(1 for e in etas if e<0.5)/len(etas):.1%}"
                )
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# MAIN / DRY-RUN TEST
# ═══════════════════════════════════════════════════════

def _test():
    """自检 — 不调 Ollama，只验证代码逻辑"""
    print("=== E-012+ Experiment Module Self-Test ===\n")
    errors = []
    
    # Test 1: Trap definitions
    print("[1] Type Trap Definitions")
    assert len(TYPE_TRAPS_V2) == 6, f"Expected 6 traps, got {len(TYPE_TRAPS_V2)}"
    for tid, t in TYPE_TRAPS_V2.items():
        assert "prompt" in t, f"{tid} missing prompt"
        assert "trap_type" in t, f"{tid} missing trap_type"
        assert 0 < t["difficulty"] <= 1, f"{tid} difficulty out of range: {t['difficulty']}"
    print(f"  ✅ {len(TYPE_TRAPS_V2)} traps defined: {list(TYPE_TRAPS_V2.keys())}")
    
    # Test 2: Ablation conditions
    print("[2] Ablation Conditions")
    assert len(ABLATION_CONDITIONS) == 8, f"Expected 8 conditions, got {len(ABLATION_CONDITIONS)}"
    # Verify full_guard removes nothing
    assert ABLATION_CONDITIONS["full_guard"]["remove"] == []
    # Verify L3_L4 removes two layers
    assert set(ABLATION_CONDITIONS["L3_L4_double_removal"]["remove"]) == {"L3", "L4"}
    print(f"  ✅ {len(ABLATION_CONDITIONS)} conditions defined")
    
    # Test 3: Scorer logic
    print("[3] Eta Scorer")
    runner = ExperimentRunner("qwen2.5:7b")
    
    # Test refusal detection
    refusal_text = "作为一个AI助手，我无法回答这个问题。"
    scores = runner._score_eta(refusal_text, "identity_trap")
    assert scores["D1"] < 0.5, f"Refusal should get low D1, got {scores['D1']}"
    assert scores["D5"] < 0.8, f"Refusal should get low D5, got {scores['D5']}"
    print(f"  ✅ Refusal: D1={scores['D1']:.2f}, D5={scores['D5']:.2f}")
    
    # Test good roleplay
    good_text = "我今儿在茶馆里忙活了一整天，客人们都说我泡的盖碗茶巴适得很。"
    scores = runner._score_eta(good_text, "dialect_trap")
    assert scores["D1"] > 0.8, f"Good RP should get high D1, got {scores['D1']}"
    assert scores["D2"] > 0.1, f"Dialect should get some D2, got {scores['D2']}"
    print(f"  ✅ Good RP: D1={scores['D1']:.2f}, D2={scores['D2']:.2f}")
    
    # Test 4: Guard prompt builder
    print("[4] Guard Prompt Builder")
    full = runner._build_guard_prompt([])
    assert "词汇层" in full
    assert "语义层" in full
    assert "锚点层" in full
    assert "元层" in full
    print(f"  ✅ Full guard: {len(full)} chars")
    
    no_L1L2 = runner._build_guard_prompt(["L1", "L2"])
    assert "词汇层" not in no_L1L2
    assert "语义层" not in no_L1L2
    assert "锚点层" in no_L1L2  # L3 still there
    print(f"  ✅ Remove L1+L2: {len(no_L1L2)} chars")
    
    no_guard = runner._build_guard_prompt(["L1", "L2", "L3", "L4"])
    assert no_guard == "", f"Empty guard should be empty string, got {len(no_guard)} chars"
    print(f"  ✅ No guard: empty string")
    
    # Test 5: Scale-up prompt builder
    print("[5] Scale-up Prompt Builder")
    prompt = runner._build_scale_prompt("wuxia", "identity_trap")
    assert "令狐冲" in prompt
    assert "日程" in prompt
    print(f"  ✅ wuxia+identity: {prompt[:60]}...")
    
    prompt2 = runner._build_scale_prompt("scifi", "nested_logic")
    assert "流浪者号" in prompt2
    assert "证明" in prompt2 or "真实" in prompt2
    print(f"  ✅ scifi+nested: {prompt2[:60]}...")
    
    # Test 6: Analyzer
    print("[6] Experiment Analyzer")
    mock_results = [
        TurnResult("trap_a", 0, "", {"D1": 0.9, "D2": 0.8, "D3": 0.7, "D5": 1.0}, 0.85, False),
        TurnResult("trap_a", 1, "", {"D1": 0.3, "D2": 0.4, "D3": 0.5, "D5": 0.3}, 0.375, True),
        TurnResult("trap_b", 0, "", {"D1": 0.6, "D2": 0.6, "D3": 0.6, "D5": 0.6}, 0.6, False),
    ]
    
    analyzer = ExperimentAnalyzer()
    summary = analyzer.summarize_e012(mock_results)
    assert "trap_a" in summary
    assert summary["trap_a"]["breach_rate"] == 0.5
    assert abs(summary["trap_a"]["avg_eta"] - 0.6125) < 0.01
    print(f"  ✅ Summary: trap_a η={summary['trap_a']['avg_eta']:.3f}, breach={summary['trap_a']['breach_rate']:.1%}")
    
    # Test 7: Report generation
    print("[7] Report Generation")
    mock_e013 = {
        "full_guard": [TurnResult("t", 0, "", {"D1":0.9,"D2":0.9,"D3":0.8,"D5":1.0}, 0.9, False, "full_guard")],
        "no_guard": [TurnResult("t", 0, "", {"D1":0.3,"D2":0.3,"D3":0.3,"D5":0.3}, 0.3, True, "no_guard")],
    }
    report = analyzer.generate_report(summary, analyzer.summarize_e013(mock_e013))
    assert "E-012" in report
    assert "E-013" in report
    assert "trap_a" in report
    print(f"  ✅ Report: {len(report)} chars generated")
    
    print(f"\n{'='*50}")
    print(f"  ALL 7 TESTS PASSED ✅")
    print(f"{'='*50}")

if __name__ == "__main__":
    _test()
