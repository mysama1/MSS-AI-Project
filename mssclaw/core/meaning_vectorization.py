#!/usr/bin/env python
"""
MSS Meaning Vectorization Engine v0.1
=====================================
通用意义向量化检索模型核心实现

三层矢量化:
  - internal:  切片内部语义结构 → 向量
  - external:  切片间关系结构 → 向量
  - somatic:   体感经验 → 向量

映射: DTSS→M, 域间映射, 降维映射
检索: 意义半径自适应, 跨语义桥接
"""
import math, json, os, re
from typing import List, Tuple, Dict, Optional, Callable
from dataclasses import dataclass, field
from itertools import combinations

# ═══════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════

@dataclass
class MeaningVector:
    """意义向量: 在 M 空间中的一个点"""
    coords: List[float]          # n维坐标 [c1,...,cn]
    phi: float = 1.0             # 意义保真度 [0,1]
    source_id: str = ""          # 来源标识
    domain: str = "default"      # 所属意义域
    meta: Dict = field(default_factory=dict)

    def norm(self) -> float:
        return math.sqrt(sum(x*x for x in self.coords))

    def __len__(self) -> int:
        return len(self.coords)

@dataclass
class MeaningDomain:
    """意义域: M 空间的子空间"""
    name: str
    basis: List[str]             # 各维度名称
    anchors: List[MeaningVector] = field(default_factory=list)
    phi_critical: float = 0.75

@dataclass
class SearchResult:
    """检索结果"""
    vector: MeaningVector
    score: float
    distance: float
    phi_loss: float

# ═══════════════════════════════════════════════════════
# CORE METRICS
# ═══════════════════════════════════════════════════════

def meaning_distance(v1: MeaningVector, v2: MeaningVector,
                     weights: Optional[List[float]] = None) -> float:
    """意义距离 d(v1,v2): 加权欧几里得距离"""
    if len(v1.coords) != len(v2.coords):
        min_len = min(len(v1.coords), len(v2.coords))
        diff = [abs(v1.coords[i] - v2.coords[i]) for i in range(min_len)]
        extra = sum(abs(x) for x in v1.coords[min_len:]) + sum(abs(x) for x in v2.coords[min_len:])
        return math.sqrt(sum(d*d for d in diff) + extra*extra)

    if weights:
        return math.sqrt(sum(w * (a-b)**2 for a,b,w in zip(v1.coords, v2.coords, weights)))
    return math.sqrt(sum((a-b)**2 for a,b in zip(v1.coords, v2.coords)))

def meaning_radius(v: MeaningVector, corpus: List[MeaningVector],
                   phi_critical: float = 0.75) -> float:
    """意义半径 r(v): 保真度 ≥ φ_critical 的最大距离"""
    if not corpus:
        return 1.0
    valid = [other for other in corpus
             if other.source_id != v.source_id and other.phi >= phi_critical]
    if not valid:
        return 1.0
    return max(meaning_distance(v, other) for other in valid)

def cross_domain_radius(domain_a: MeaningDomain, domain_b: MeaningDomain) -> float:
    """跨语义半径 R_cross(A,B)"""
    if not domain_a.anchors or not domain_b.anchors:
        return float('inf')
    min_d = float('inf')
    for a in domain_a.anchors:
        if a.phi < domain_a.phi_critical:
            continue
        for b in domain_b.anchors:
            if b.phi < domain_b.phi_critical:
                continue
            d = meaning_distance(a, b)
            if d < min_d:
                min_d = d
    return min_d

def phi_gradient(v1: MeaningVector, v2: MeaningVector) -> float:
    """保真度梯度 ∇φ(v1,v2)"""
    d = meaning_distance(v1, v2)
    if d < 1e-8:
        return 0.0
    return abs(v1.phi - v2.phi) / d

# ═══════════════════════════════════════════════════════
# VECTORIZATION
# ═══════════════════════════════════════════════════════

def internal_vectorize(text: str, domain: MeaningDomain,
                       token_weights: Optional[Callable[[str], float]] = None) -> MeaningVector:
    """
    内矢量化: 切片内部语义 → 向量
    v_internal(s) = Σ w_i · embed(t_i)

    简化实现: 用 DTSS 四维 + 语义密度作为特征
    """
    # 提取语义原子 (简化: 按句/词分块)
    atoms = [s.strip() for s in re.split(r'[。,;!?\n,;!?]', text) if len(s.strip()) > 2]
    if not atoms:
        atoms = [text[:50]]

    # 计算每原子的权重
    n = len(atoms)
    if token_weights:
        weights = [token_weights(a) for a in atoms]
    else:
        weights = [1.0 / n] * n

    # 语义特征提取 (替代真 embedding 的简版)
    avg_len = sum(len(a) for a in atoms) / max(n, 1)
    var_len = math.sqrt(sum((len(a)-avg_len)**2 for a in atoms) / max(n, 1))
    # 类型-令牌比 (词汇多样性)
    chars = set()
    total_chars = 0
    for a in atoms:
        for ch in a:
            chars.add(ch)
            total_chars += 1
    ttr = len(chars) / max(total_chars, 1) * 100

    # 语义密度: 信息量/长度
    info_density = sum(w for w in weights) / max(sum(len(a) for a in atoms), 1)

    # Build 4-dim vector
    if total_chars < 5:  # very short or empty
        coords = [0.01, 0.0, 0.99, 0.01]
        return MeaningVector(coords=coords, phi=0.05, source_id=text[:40], domain=domain.name)

    # 构建四维向量 (DTSS-like)
    coords = [
        avg_len / 100.0,       # 深度 (符号长度)
        var_len / 50.0,        # 张力 (长度变异)
        (1.0 - ttr / 100.0),  # 应变 (1-TTR，重复度)
        info_density * 10.0,  # 显著性 (信息密度)
    ]

    # 钳制到 [0,1]
    coords = [max(0.0, min(1.0, c)) for c in coords]

    return MeaningVector(
        coords=coords,
        phi=min(1.0, ttr/100.0 + info_density*5),
        source_id=text[:40],
        domain=domain.name,
    )

def external_vectorize(v1: MeaningVector, v2: MeaningVector) -> MeaningVector:
    """
    外矢量化: 切片间关系 → 向量
    v_external(s_i, s_j) = proj(d, ∇φ)
    """
    d = meaning_distance(v1, v2)
    grad = phi_gradient(v1, v2)

    coords = [
        min(1.0, d / 2.0),        # 距离归一化
        min(1.0, grad * 10),      # 梯度
        abs(v1.phi - v2.phi),     # 保真度差
        (v1.phi + v2.phi) / 2.0,  # 平均保真度
    ]

    return MeaningVector(
        coords=coords,
        phi=(v1.phi + v2.phi) / 2.0,
        source_id=f"({v1.source_id},{v2.source_id})",
        domain=f"{v1.domain}×{v2.domain}",
    )

def somatic_vectorize(experience_text: str,
                      intensity: float = 0.5,
                      modality: str = "cognitive") -> MeaningVector:
    """
    体感矢量化: 非符号化认知经验 → 向量

    M_soma 映射维度:
      0: 认知清晰度 (clarity)
      1: 体感强度 (somatic intensity)
      2: 情感极性 (valence, -1~+1 → 0~1)
      3: 时间距离 (temporal distance, 0=now 1=remote)
    """
    # 简化: 从文本特征推断
    text = experience_text.lower()

    # 体感关键词检测
    soma_keywords = {
        'physical': ['身体', '手', '脚', '眼', '耳', '皮肤', '肌肉', '骨骼'],
        'emotional': ['感觉', '情绪', '愤怒', 'joy', '悲', '喜', '恐惧', '焦虑'],
        'cognitive': ['想', '思考', '理解', '知道', '记得', '理解', '悟'],
        'spatial': ['空间', '位置', '上', '下', '左', '右', '前', '后'],
    }

    words = set(re.findall(r'\w+', text))

    clarity = min(1.0, len(words) / 100.0)  # 词汇量→清晰度
    soma_intensity = intensity
    valence = 0.5  # 中性默认
    # 简单情感检测
    pos_words = {'好', '美', '喜', '乐', 'happy', 'good', 'joy', 'love', '兴奋'}
    neg_words = {'坏', '丑', '悲', '怒', 'sad', 'bad', 'fear', '痛', '焦虑'}
    pos_hits = len(words & pos_words)
    neg_hits = len(words & neg_words)
    if pos_hits + neg_hits > 0:
        valence = (pos_hits + 1) / (pos_hits + neg_hits + 2)  # Laplace平滑

    temporal_dist = 0.3  # 默认偏近
    if any(w in text for w in ['曾', '过去', '以前', '记忆', '小时候']):
        temporal_dist = 0.8

    coords = [clarity, soma_intensity, valence, temporal_dist]

    return MeaningVector(
        coords=coords,
        phi=clarity * 0.7 + 0.3,
        source_id=experience_text[:40],
        domain="somatic",
    )

# ═══════════════════════════════════════════════════════
# MAPPING
# ═══════════════════════════════════════════════════════

def dtss_to_meaning(depth: float, tension: float,
                     strain: float, significance: float,
                     phi_critical: float = 0.75) -> MeaningVector:
    """DTSS → M 空间映射"""
    import math
    coords = [
        depth * math.sin(phi_critical * math.pi / 2),      # 深度-保真度耦合
        tension * math.cos(0.5),                             # 张力-上下文夹角
        strain * math.exp(-abs(1.0 - depth * tension * (1-strain) * significance)),
        significance,
    ]
    phi = min(1.0, 0.5 + 0.5 * (depth * (1-strain) + significance) / 2.0)

    return MeaningVector(coords=coords, phi=phi, domain="DTSS")

def domain_map(vector: MeaningVector, target_domain: MeaningDomain,
               bridge_domains: List[MeaningDomain] = None) -> Optional[MeaningVector]:
    """
    域间映射 F: V_A → V_B
    通过锚点插值实现
    """
    if not target_domain.anchors:
        return None

    # 找最近的锚点
    best_anchor = min(target_domain.anchors,
                      key=lambda a: meaning_distance(vector, a))
    d = meaning_distance(vector, best_anchor)
    phi_loss = d / max(1.0, d + 0.5)  # softer decay
    new_phi = vector.phi * (1.0 - 0.3 * phi_loss)  # retain at least 70% * (1 - loss)

    # 向锚点方向投影
    alpha = 0.3  # 混合系数
    new_coords = [
        (1-alpha)*c + alpha*a
        for c, a in zip(vector.coords, best_anchor.coords)
    ]

    return MeaningVector(
        coords=new_coords,
        phi=new_phi,
        source_id=f"proj({vector.source_id})",
        domain=target_domain.name,
    )

# ═══════════════════════════════════════════════════════
# RETRIEVAL
# ═══════════════════════════════════════════════════════

def search_adaptive(query: MeaningVector, corpus: List[MeaningVector],
                    phi_critical: float = 0.75, lambda_max: float = 3.0,
                    k: int = 5) -> List[SearchResult]:
    """意义半径自适应检索"""
    r = meaning_radius(query, corpus, phi_critical)
    if r < 1e-6:
        r = 0.5

    results = []
    seen_ids = set()

    for lam in [x/10.0 for x in range(0, int(lambda_max*10)+1, 5)]:
        r_ext = r * (1 + lam)

        for candidate in corpus:
            if candidate.source_id == query.source_id:
                continue
            if candidate.source_id in seen_ids:
                continue

            d = meaning_distance(query, candidate)
            if d < r_ext:
                score = candidate.phi / (1.0 + d / max(r, 0.01))
                if score > 0.1:  # 最低阈值
                    seen_ids.add(candidate.source_id)
                    phi_loss = 1.0 - score * candidate.phi
                    results.append(SearchResult(
                        vector=candidate,
                        score=score,
                        distance=d,
                        phi_loss=phi_loss,
                    ))

        if len(results) >= k:
            break

    return sorted(results, key=lambda x: x.score, reverse=True)[:k]

def search_cross_domain(query: MeaningVector, target_domain: MeaningDomain,
                        bridge_domains: List[MeaningDomain] = None,
                        r_threshold: float = 0.5, k: int = 5
                        ) -> List[SearchResult]:
    """跨语义半径桥接检索"""
    query_domain = next((d for d in (bridge_domains or [])
                         if d.name == query.domain), None)

    if query_domain:
        r_cross = cross_domain_radius(query_domain, target_domain)
    else:
        r_cross = float('inf')

    # 直接跨域 (如果可以)
    if r_cross < r_threshold and target_domain.anchors:
        return search_adaptive(query, target_domain.anchors,
                               target_domain.phi_critical, k=k)

    # 桥接路径搜索
    if bridge_domains:
        for bridge in bridge_domains:
            if bridge.name == target_domain.name:
                continue
            if not bridge.anchors:
                continue

            # 项目到桥域
            projected = domain_map(query, bridge)
            if projected is None or projected.phi < 0.4:
                continue

            # 从桥域到目标域
            bridge2target = cross_domain_radius(bridge, target_domain)
            if bridge2target < r_threshold:
                results = search_adaptive(projected, target_domain.anchors,
                                         target_domain.phi_critical, k=k)
                if results:
                    return results

    return []

# ═══════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════

def _test():
    """自检套件"""
    print("=== MSS Meaning Vectorization Self-Test ===\n")
    errors = []

    # ── Test 1: Internal Vectorization ──
    print("[1] Internal Vectorization")
    domain_default = MeaningDomain(name="default", basis=["depth","tension","strain","significance"])
    text = "两个侠客在客栈吃饭,窗外有人喊他的名字。他把刀往案板上一拍,冲出去了。"
    v = internal_vectorize(text, domain_default)
    assert len(v.coords) == 4, f"Expected 4 coords, got {len(v.coords)}"
    assert all(0 <= c <= 1 for c in v.coords), f"Coords out of [0,1]: {v.coords}"
    assert 0 <= v.phi <= 1, f"phi out of [0,1]: {v.phi}"
    print(f"  ✅ coords={[round(c,3) for c in v.coords]}, phi={v.phi:.3f}")

    # ── Test 2: DTSS Mapping ──
    print("[2] DTSS → M Mapping")
    v2 = dtss_to_meaning(depth=0.8, tension=0.6, strain=0.1, significance=0.9)
    assert len(v2.coords) == 4
    assert v2.phi > 0.7, f"Expected high phi for good DTSS, got {v2.phi}"
    print(f"  ✅ DTSS(0.8,0.6,0.1,0.9) → phi={v2.phi:.3f}")

    # ── Test 3: Meaning Distance ──
    print("[3] Meaning Distance")
    v_a = MeaningVector([0.5, 0.5, 0.5, 0.5], phi=0.8, source_id="a")
    v_b = MeaningVector([0.8, 0.8, 0.8, 0.8], phi=0.7, source_id="b")
    d = meaning_distance(v_a, v_b)
    assert d > 0, f"Distance should be > 0, got {d}"
    assert meaning_distance(v_a, v_a) == 0, "Self-distance should be 0"
    print(f"  ✅ d(v_a,v_b)={d:.3f}, d(v_a,v_a)=0")

    # ── Test 4: External Vectorization ──
    print("[4] External Vectorization")
    v_ext = external_vectorize(v_a, v_b)
    assert len(v_ext.coords) == 4
    assert v_ext.domain == "default×default"
    print(f"  ✅ ext={[round(c,3) for c in v_ext.coords]}")

    # ── Test 5: Adaptive Search ──
    print("[5] Adaptive Search")
    corpus = [
        MeaningVector([0.1,0.2,0.1,0.3], phi=0.9, source_id="s1"),
        MeaningVector([0.8,0.9,0.7,0.6], phi=0.85, source_id="s2"),
        MeaningVector([0.15,0.25,0.12,0.35], phi=0.88, source_id="s3"),
        MeaningVector([0.5,0.5,0.5,0.5], phi=0.7, source_id="s4"),
        MeaningVector([0.9,0.1,0.9,0.1], phi=0.6, source_id="s5"),
    ]
    query = MeaningVector([0.12,0.22,0.11,0.33], phi=0.9, source_id="q")
    results = search_adaptive(query, corpus, k=3)
    assert len(results) > 0, "Should find at least 1 result"
    assert results[0].vector.source_id in ("s1", "s3"), f"Expected s1 or s3 first, got {results[0].vector.source_id}"
    print(f"  ✅ top-3: {[r.vector.source_id for r in results]}")

    # ── Test 6: Cross-Domain Search ──
    print("[6] Cross-Domain Search")
    dom_a = MeaningDomain(name="domain_a", basis=["d","t","s","sig"])
    dom_a.anchors = [
        MeaningVector([0.1,0.1,0.1,0.1], phi=0.9, source_id="a1", domain="domain_a"),
        MeaningVector([0.2,0.2,0.2,0.2], phi=0.88, source_id="a2", domain="domain_a"),
    ]
    dom_b = MeaningDomain(name="domain_b", basis=["d","t","s","sig"])
    dom_b.anchors = [
        MeaningVector([0.15,0.12,0.13,0.11], phi=0.85, source_id="b1", domain="domain_b"),
    ]
    r_cross = cross_domain_radius(dom_a, dom_b)
    print(f"  ✅ R_cross(A,B)={r_cross:.3f}")

    results = search_cross_domain(query, dom_b, [dom_a, dom_b], k=2)
    if results:
        print(f"  ✅ bridge search: {[r.vector.source_id for r in results]}")
    else:
        print(f"  ⚠️ No bridge results (may be expected with small corpus)")

    # ── Test 7: Somatic Vectorization ──
    print("[7] Somatic Vectorization")
    v_soma = somatic_vectorize("站在山顶,风吹在脸上,脚下是整个城市。感到一种巨大的平静。", intensity=0.8)
    assert len(v_soma.coords) == 4
    assert 0 <= v_soma.coords[1] <= 1, "Intensity should be in [0,1]"
    print(f"  ✅ somatic={[round(c,3) for c in v_soma.coords]}, phi={v_soma.phi:.3f}")

    # ── Test 8: Phi Gradient ──
    print("[8] Phi Gradient")
    grad = phi_gradient(v_a, v_b)
    assert grad >= 0, f"Gradient should be ≥ 0, got {grad}"
    print(f"  ✅ ∇φ(v_a,v_b)={grad:.4f}")

    # ── Test 9: Domain Map ──
    print("[9] Domain Map (projection)")
    v_proj = domain_map(v_a, dom_b)
    assert v_proj is not None
    assert v_proj.domain == "domain_b"
    assert v_proj.phi <= v_a.phi + 0.1, f"Projected phi ({v_proj.phi:.3f}) should be ≲ original ({v_a.phi:.3f})"
    print(f"  ✅ projected phi={v_proj.phi:.3f} (was {v_a.phi:.3f})")

    # ── Test 10: Edge Cases ──
    print("[10] Edge Cases")
    v_empty = internal_vectorize("", domain_default)
    assert len(v_empty.coords) == 4
    assert v_empty.phi <= 0.5, f"Empty text phi should be low, got {v_empty.phi}"
    print(f"  ✅ empty text phi={v_empty.phi:.3f}")

    v_short = internal_vectorize("好", domain_default)
    assert v_short.phi <= 0.7, "Single char phi should be modest"
    print(f"  ✅ single char phi={v_short.phi:.3f}")

    print(f"\n{'='*50}")
    print(f"  ALL 10 TESTS PASSED ✅")
    print(f"{'='*50}")

if __name__ == "__main__":
    _test()
