# 方向抉择算法: MCDP(1) vs Phase(2) 自动路由
"""
Scene Router v1.0 — 根据Agent/场景特征自动选择最优处理方向

方向1 (MCDP — Multi-Criteria Decision Process):
  适用: 结构化多准则决策, 确定性场景, 已知约束
  
方向2 (Phase — Phase Transition Detection):
  适用: 相变/临界现象检测, 非结构化环境, 统计性质

路由逻辑基于6个维度评分:
  1. 结构化程度 (0=完全随机, 1=完全结构化)
  2. 信息完备度 (0=部分可观测, 1=完全可观测)
  3. 约束明确度 (边缘是否清晰)
  4. 相变敏感度 (系统是否对参数微小变化敏感)
  5. Agent数量 (多→MCDP, 少→Phase)
  6. 博弈性质 (零和→MCDP, 协作→Phase)
"""
import numpy as np, json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

DIR_MCDP = 1
DIR_PHASE = 2
DIR_HYBRID = 3

@dataclass
class SceneProfile:
    name: str
    structure: float       # [0,1] 结构化程度
    information: float     # [0,1] 信息完备度
    constraint_clarity: float  # [0,1] 约束明确度
    phase_sensitivity: float   # [0,1] 相变敏感度
    n_agents: int           # Agent数量
    game_type: float        # [-1,1] -1=纯竞争, 0=混合, 1=纯协作
    
    weights: dict = field(default_factory=lambda: {
        "structure": 0.25,
        "information": 0.20,
        "constraint_clarity": 0.15,
        "phase_sensitivity": 0.20,
        "n_agents": 0.10,
        "game_type": 0.10
    })

def compute_scores(profile: SceneProfile) -> dict:
    """计算MCDP倾向度和Phase倾向度"""
    w = profile.weights
    
    # MCDP benefit: high structure + information + constraint + many agents + competitive
    mcdp_raw = (
        w["structure"] * profile.structure +
        w["information"] * profile.information +
        w["constraint_clarity"] * profile.constraint_clarity +
        w["n_agents"] * min(profile.n_agents / 10, 1.0) +
        w["game_type"] * (1 - (profile.game_type + 1) / 2)  # competitive→MCDP advantage
    )
    
    # Phase benefit: high sensitivity + cooperative + low structure
    phase_raw = (
        w["phase_sensitivity"] * profile.phase_sensitivity +
        w["structure"] * (1 - profile.structure) +  # low structure → phase
        w["information"] * (1 - profile.information) +  # partial info → phase
        w["game_type"] * (profile.game_type + 1) / 2  # cooperative → phase
    )
    
    # Normalize
    total = mcdp_raw + phase_raw + 1e-9
    return {
        "mcdp_score": mcdp_raw / total,
        "phase_score": phase_raw / total,
        "mcdp_raw": mcdp_raw,
        "phase_raw": phase_raw
    }

def decide(profile: SceneProfile, threshold: float = 0.55) -> dict:
    """主决策函数"""
    scores = compute_scores(profile)
    m, p = scores["mcdp_score"], scores["phase_score"]
    
    if abs(m - p) < 0.1:
        direction = DIR_HYBRID
        confidence = 1.0 - abs(m - p)
    elif m > p:
        direction = DIR_MCDP if m > threshold else DIR_HYBRID
        confidence = m
    else:
        direction = DIR_PHASE if p > threshold else DIR_HYBRID
        confidence = p
    
    # CRTR (Cognitive Resource Trust Ratio) = confidence × (1 - ambiguity)
    ambiguity = min(m, p) / max(m, p)  # 1=完全模糊, 0=完全明确
    crtr = confidence * (1 - ambiguity)
    
    return {
        "direction": direction,
        "direction_name": {1: "MCDP", 2: "Phase", 3: "Hybrid"}[direction],
        "confidence": round(confidence, 4),
        "crtr": round(crtr, 4),
        "mcdp_score": round(m, 4),
        "phase_score": round(p, 4),
        "profile": profile.name
    }

# === 基准场景库 ===
SCENES = {
    "supply_chain": SceneProfile(
        name="供应链优化",
        structure=0.85, information=0.8, constraint_clarity=0.9,
        phase_sensitivity=0.2, n_agents=8, game_type=-0.3  # 半竞争
    ),
    "trust_network": SceneProfile(
        name="信任网络演化",
        structure=0.3, information=0.4, constraint_clarity=0.2,
        phase_sensitivity=0.85, n_agents=50, game_type=0.5  # 半协作
    ),
    "meaning_field": SceneProfile(
        name="意义场稳定化",
        structure=0.15, information=0.25, constraint_clarity=0.1,
        phase_sensitivity=0.95, n_agents=100, game_type=0.8  # 高度协作
    ),
    "resource_allocation": SceneProfile(
        name="资源分配",
        structure=0.9, information=0.95, constraint_clarity=0.85,
        phase_sensitivity=0.1, n_agents=5, game_type=-0.5  # 竞争
    ),
    "fraud_detection": SceneProfile(
        name="欺诈检测",
        structure=0.5, information=0.3, constraint_clarity=0.4,
        phase_sensitivity=0.7, n_agents=20, game_type=-0.8  # 高度对抗
    ),
    "cultural_diffusion": SceneProfile(
        name="文化扩散",
        structure=0.2, information=0.15, constraint_clarity=0.05,
        phase_sensitivity=0.9, n_agents=500, game_type=0.6  # 协作扩散
    ),
    "price_negotiation": SceneProfile(
        name="价格谈判",
        structure=0.7, information=0.6, constraint_clarity=0.65,
        phase_sensitivity=0.3, n_agents=2, game_type=-1.0  # 纯零和
    ),
    "knowledge_synthesis": SceneProfile(
        name="知识综合",
        structure=0.35, information=0.5, constraint_clarity=0.3,
        phase_sensitivity=0.6, n_agents=3, game_type=0.9  # 高度协作
    ),
}

# === 路由决策 ===
print("=" * 70)
print("Scene Router v1.0 — MCDP vs Phase 自动抉择")
print("=" * 70)

results = {}
for name, profile in SCENES.items():
    decision = decide(profile)
    results[name] = decision
    arrow = {"MCDP": "⬅️ 方向1", "Phase": "➡️ 方向2", "Hybrid": "🔄 混合"}[decision["direction_name"]]
    print(f"\n{profile.name}:")
    print(f"  路由 → {arrow}  (conf={decision['confidence']:.3f}, CRTR={decision['crtr']:.3f})")
    print(f"  MCDP={decision['mcdp_score']:.3f}  Phase={decision['phase_score']:.3f}")

# Save
out_path = Path("E:/AI_Workspace/MSS-AI/project/kb/L3_EMPIRICAL/scene_router_results.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(str(out_path), "w") as f:
    json.dump({"version": "SceneRouter v1.0", "results": results}, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out_path}")

# === 灵敏度分析 ===
print(f"\n{'='*70}")
print("灵敏度分析: 信息完备度对路由的影响 (fraud_detection基准)")
base = SCENES["fraud_detection"]
for info in np.linspace(0.1, 0.9, 9):
    p = SceneProfile(name=f"info={info:.1f}", 
                     structure=base.structure, information=info,
                     constraint_clarity=base.constraint_clarity,
                     phase_sensitivity=base.phase_sensitivity,
                     n_agents=base.n_agents, game_type=base.game_type)
    d = decide(p)
    print(f"  info={info:.1f} → {d['direction_name']:6s}  M={d['mcdp_score']:.3f}  P={d['phase_score']:.3f}  CRTR={d['crtr']:.3f}")
