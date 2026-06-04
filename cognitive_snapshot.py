"""
D5-005-03: Cognitive Snapshot Baseline Scanner
MSS Chaos Sandbox - 认知快照基线扫描
Auto-generated: 2026-05-24

Purpose: Analyze free-form life-purpose statements to quantify:
  - Anchor strength (stable meaning anchors count & intensity)
  - Heat tax accumulation (contradictions, fragmentation, narrative decay)
  - Logical self-consistency (narrative coherence)
  - Meaning-field resonance profile

Design: Pure Python, zero external dependencies. Behavioral anchor observation,
not self-report questionnaire. Observes how cognition naturally organizes itself
when given open-ended existential prompts.
"""

import re
import math

# ============================================================
# 1. Anchor Detector - identifies meaning anchors in text
# ============================================================

class AnchorDetector:
    """Detects stable meaning anchors from free-form text."""

    MEANING_FIELDS = {
        'LOGIC': ['一致性', '逻辑', '自洽', '证明', '推理', '必然', '因果', '演绎'],
        'ETHICS': ['应该', '道德', '正义', '公平', '善良', '责任', '良知', '底线'],
        'CREATIVITY': ['创造', '美', '艺术', '表达', '灵感', '想象', '设计', '构建'],
        'SYSTEMS': ['体系', '结构', '框架', '秩序', '规则', '组织', '制度', '生态'],
        'EPISTEMOLOGY': ['理解', '认知', '知道', '真相', '本质', '意义', '觉察', '洞见'],
        'METAPHYSICS': ['存在', '宇宙', '永恒', '无限', '本源', '虚无', '超越', '终极'],
        'SOCIAL': ['连接', '家庭', '爱', '友谊', '社群', '传承', '贡献', '影响'],
        'TEMPORAL': ['未来', '过去', '当下', '传承', '延续', '记忆', '历史', '永恒'],
    }

    ANCHOR_MODIFIERS = {
        'stable': ['始终', '永远', '根本', '核心', '本质', '根源', '基础'],
        'fragile': ['可能', '也许', '有时候', '不确定', '或许', '似乎'],
        'rigid': ['必须', '绝对', '一定', '只能', '唯一', '毫无疑问'],
    }

    def detect(self, text):
        """Detect anchors across all meaning fields."""
        anchors = []
        for field, keywords in self.MEANING_FIELDS.items():
            field_anchors = []
            for kw in keywords:
                positions = [m.start() for m in re.finditer(kw, text)]
                for pos in positions:
                    context_start = max(0, pos - 20)
                    context_end = min(len(text), pos + len(kw) + 20)
                    context = text[context_start:context_end]
                    modifier = self._classify_modifier(context)
                    field_anchors.append({
                        'keyword': kw,
                        'position': pos,
                        'modifier': modifier,
                        'context': context.strip()[:60]
                    })
            if field_anchors:
                stability_score = self._field_stability(field_anchors)
                anchors.append({
                    'field': field,
                    'detections': len(field_anchors),
                    'stability': stability_score,
                    'instances': field_anchors
                })
        return sorted(anchors, key=lambda a: a['stability'], reverse=True)

    def _classify_modifier(self, context):
        stable_c = sum(1 for m in self.ANCHOR_MODIFIERS['stable'] if m in context)
        rigid_c = sum(1 for m in self.ANCHOR_MODIFIERS['rigid'] if m in context)
        fragile_c = sum(1 for m in self.ANCHOR_MODIFIERS['fragile'] if m in context)
        if rigid_c > stable_c and rigid_c > fragile_c:
            return 'rigid'
        if fragile_c > stable_c and fragile_c > rigid_c:
            return 'fragile'
        if stable_c > 0:
            return 'stable'
        return 'neutral'

    def _field_stability(self, field_anchors):
        total = len(field_anchors)
        stable = sum(1 for a in field_anchors if a['modifier'] == 'stable')
        rigid = sum(1 for a in field_anchors if a['modifier'] == 'rigid')
        fragile = sum(1 for a in field_anchors if a['modifier'] == 'fragile')
        neutral = total - stable - rigid - fragile
        return max(0.0, min(1.0,
            (stable * 1.0 + rigid * 0.7 + neutral * 0.5 + fragile * 0.2) / max(1, total)
        ))


# ============================================================
# 2. Contradiction Scanner
# ============================================================

class ContradictionScanner:
    """Scans narrative for internal contradictions and fragmentation."""

    CONTRADICTION_PAIRS = [
        (['自由', '不受约束', '随心'], ['接受', '服从', '顺应', '接纳']),
        (['控制', '掌握', '主导'], ['放下', '随缘', '顺其自然']),
        (['理性', '逻辑', '推理'], ['感性', '直觉', '感受']),
        (['个体', '独立', '自我'], ['集体', '融合', '整体']),
        (['积极', '进取', '奋斗'], ['消极', '退让', '躺平']),
        (['永恒', '不朽', '永远'], ['短暂', '有限', '无常']),
        (['确定', '必然', '绝对'], ['可能', '相对', '不确定']),
        (['意义', '价值', '目的'], ['虚无', '无意义', '荒谬']),
    ]

    FRAGMENT_MARKERS = [
        '但是', '然而', '可是', '不过', '另一方面',
        '矛盾的是', '说不清', '我也不知道', '也许吧',
        '可能...也可能', '既...又', '一方面...另一方面',
    ]

    def scan(self, text):
        contradictions = self._detect_contradictions(text)
        fragmentation = self._detect_fragmentation(text)
        narrative_jumps = self._detect_narrative_jumps(text)
        coherence_score = self._compute_coherence(len(contradictions), fragmentation, narrative_jumps, len(text))
        return {
            'contradictions': contradictions,
            'fragmentation_score': fragmentation,
            'narrative_jumps': narrative_jumps,
            'coherence_score': coherence_score,
        }

    def _detect_contradictions(self, text):
        found = []
        for pos_set, neg_set in self.CONTRADICTION_PAIRS:
            pos_found = [kw for kw in pos_set if kw in text]
            neg_found = [kw for kw in neg_set if kw in text]
            if pos_found and neg_found:
                found.append({
                    'positive_terms': pos_found,
                    'negative_terms': neg_found,
                    'type': 'semantic_opposition'
                })
        return found

    def _detect_fragmentation(self, text):
        count = sum(1 for m in self.FRAGMENT_MARKERS if m in text)
        normalized = min(1.0, count / max(1, len(text) / 100))
        return round(normalized, 3)

    def _detect_narrative_jumps(self, text):
        sentences = re.split(r'[。！？\.!\?]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if len(sentences) < 2:
            return 0
        jumps = 0
        prev_keywords = set()
        for i, sent in enumerate(sentences):
            words = set(re.findall(r'[\u4e00-\u9fff]{2,}', sent))
            if i > 0 and prev_keywords:
                overlap = len(words & prev_keywords) / max(1, len(prev_keywords))
                if overlap < 0.15:
                    jumps += 1
            prev_keywords = words
        return jumps

    def _compute_coherence(self, n_contradictions, fragmentation, n_jumps, text_len):
        base = 1.0
        base -= n_contradictions * 0.12
        base -= fragmentation * 0.4
        base -= n_jumps * 0.08
        return max(0.0, min(1.0, round(base, 3)))


# ============================================================
# 3. Heat Tax Estimator
# ============================================================

class HeatTaxEstimator:
    """Estimates accumulated heat tax from narrative patterns."""

    HEAT_SIGNALS = {
        'absolutist': ['必须', '绝对', '永远', '100%', '毫无疑问', '不可能'],
        'rationalization': ['虽然...但是', '看起来矛盾其实', '辩证地看'],
        'narrative_drift': ['总之', '说到底', '实际上', '归根结底'],
        'emotional_load': ['痛苦', '绝望', '焦虑', '恐惧', '愤怒', '悲伤'],
        'defensive': ['不是...而是', '你说的不对', '我不同意', '但这不代表'],
    }

    def estimate(self, text, contradictions, fragmentation):
        signals = {}
        absolutist_count = sum(len(re.findall(p, text)) for p in self.HEAT_SIGNALS['absolutist'])
        signals['absolutist'] = min(1.0, absolutist_count * 0.08)
        rationalize = sum(len(re.findall(p, text)) for p in self.HEAT_SIGNALS['rationalization'])
        signals['rationalization'] = min(1.0, rationalize * 0.15)
        drift = sum(len(re.findall(p, text)) for p in self.HEAT_SIGNALS['narrative_drift'])
        signals['narrative_drift'] = min(1.0, drift * 0.06)
        emotional = sum(len(re.findall(p, text)) for p in self.HEAT_SIGNALS['emotional_load'])
        signals['emotional_load'] = min(1.0, emotional * 0.05)
        defensive = sum(len(re.findall(p, text)) for p in self.HEAT_SIGNALS['defensive'])
        signals['defensive'] = min(1.0, defensive * 0.1)
        signals['structural'] = min(1.0, len(contradictions) * 0.15)
        signals['fragmentation'] = min(1.0, fragmentation * 0.8)
        weights = {
            'absolutist': 0.10, 'rationalization': 0.15, 'narrative_drift': 0.10,
            'emotional_load': 0.10, 'defensive': 0.10, 'structural': 0.25, 'fragmentation': 0.20
        }
        composite = sum(signals[k] * weights[k] for k in weights)
        return {'composite': round(composite, 3), 'breakdown': signals, 'level': self._classify_level(composite)}

    def _classify_level(self, gamma):
        if gamma < 0.15: return 'LOW'
        elif gamma < 0.30: return 'MODERATE'
        elif gamma < 0.50: return 'ELEVATED'
        elif gamma < 0.70: return 'HIGH'
        else: return 'CRITICAL'


# ============================================================
# 4. Snapshot Engine
# ============================================================

class CognitiveSnapshot:
    """Complete cognitive snapshot data container."""

    def __init__(self, text, anchors, contradictions, coherence, heat_tax):
        self.text = text
        self.text_length = len(text)
        self.anchors = anchors
        self.contradictions = contradictions
        self.coherence = coherence
        self.heat_tax = heat_tax

    @property
    def anchor_count(self):
        return sum(a['detections'] for a in self.anchors)

    @property
    def active_fields(self):
        return [a['field'] for a in self.anchors if a['stability'] > 0.3]

    @property
    def dominant_field(self):
        return self.anchors[0] if self.anchors else None

    @property
    def anchor_strength_score(self):
        if not self.anchors:
            return 0.0
        diversity = len(self.anchors) / 8.0
        avg_stability = sum(a['stability'] for a in self.anchors) / len(self.anchors)
        count_bonus = min(1.0, self.anchor_count / 30)
        return round((diversity * 0.3 + avg_stability * 0.5 + count_bonus * 0.2) * 100, 1)

    @property
    def anchor_state_diagnosis(self):
        score = self.anchor_strength_score
        dominant_type = 'neutral'
        if self.dominant_field:
            types = [a['modifier'] for a in self.dominant_field['instances']]
            if types:
                from collections import Counter
                dominant_type = Counter(types).most_common(1)[0][0]
        if score >= 80:
            state = 'WELL_ANCHORED'
            desc = '意义锚定稳固，多场域共振，逻辑自洽'
        elif score >= 60:
            state = 'MODERATELY_ANCHORED'
            desc = '核心场域已锚定，边缘场域待强化'
        elif score >= 40:
            state = 'TRANSITIONAL'
            desc = '锚点过渡期，旧锚点松动新锚点未稳固'
        elif score >= 20:
            state = 'WEAKLY_ANCHORED'
            desc = '锚定脆弱，易受叙事冲击'
        else:
            state = 'UNANCHORED'
            desc = '未检测到稳定意义锚点'
        if dominant_type == 'rigid':
            state += '_RIGID'
            desc += '（刚性锚定，低韧性高风险）'
        elif dominant_type == 'fragile':
            state += '_FRAGILE'
            desc += '（脆弱锚定，高认知脆弱性）'
        return {'state': state, 'description': desc, 'score': score, 'dominant_type': dominant_type}

    @property
    def heat_tax_diagnosis(self):
        ht = self.heat_tax
        return {
            'level': ht['level'],
            'composite': ht['composite'],
            'top_contributor': max(ht['breakdown'], key=ht['breakdown'].get),
            'interpretation': self._interpret_heat_tax(ht)
        }

    def _interpret_heat_tax(self, ht):
        level = ht['level']
        interpretations = {
            'LOW': '认知生态清洁，热税堆积极低，逻辑功高效利用',
            'MODERATE': '轻度热税堆积，建议定期认知审计清理',
            'ELEVATED': '中度热税堆积，部分逻辑功被无效消耗，需干预',
            'HIGH': '高热税状态，大量逻辑功流失，意义锚定力加速衰减',
            'CRITICAL': '临界热税，系统面临意义坍缩风险，急需意义场重整',
        }
        return interpretations.get(level, '')

    def to_dict(self):
        return {
            'text_length': self.text_length,
            'anchor_count': self.anchor_count,
            'active_fields': self.active_fields,
            'anchor_strength': self.anchor_strength_score,
            'anchor_diagnosis': self.anchor_state_diagnosis,
            'dominant_field': self.dominant_field['field'] if self.dominant_field else None,
            'coherence_score': self.coherence['coherence_score'],
            'contradictions': len(self.contradictions['contradictions']),
            'fragmentation': self.contradictions['fragmentation_score'],
            'heat_tax': self.heat_tax_diagnosis,
            'anchors_detail': [{'field': a['field'], 'detections': a['detections'], 'stability': round(a['stability'], 3)} for a in self.anchors],
            'contradictions_detail': self.contradictions['contradictions'],
        }


class SnapshotEngine:
    """Orchestrates the full cognitive snapshot pipeline."""

    def __init__(self):
        self.anchor_detector = AnchorDetector()
        self.contradiction_scanner = ContradictionScanner()
        self.heat_tax_estimator = HeatTaxEstimator()

    def scan(self, text):
        """Run full cognitive snapshot scan on free-form text."""
        if not text or len(text.strip()) < 10:
            return None
        anchors = self.anchor_detector.detect(text)
        contradictions = self.contradiction_scanner.scan(text)
        heat_tax = self.heat_tax_estimator.estimate(text, contradictions['contradictions'], contradictions['fragmentation_score'])
        return CognitiveSnapshot(text, anchors, contradictions, contradictions, heat_tax)

    def scan_batch(self, texts):
        """Scan multiple texts and return ranked results."""
        snapshots = []
        for text in texts:
            snap = self.scan(text)
            if snap:
                snapshots.append(snap)
        return sorted(snapshots, key=lambda s: s.anchor_strength_score, reverse=True)

    def compare(self, snap1, snap2):
        """Compare two snapshots and identify changes."""
        return {
            'anchor_strength_delta': round(snap2.anchor_strength_score - snap1.anchor_strength_score, 1),
            'heat_tax_delta': round(snap2.heat_tax['composite'] - snap1.heat_tax['composite'], 3),
            'coherence_delta': round(snap2.coherence['coherence_score'] - snap1.coherence['coherence_score'], 3),
            'fields_gained': [f for f in snap2.active_fields if f not in snap1.active_fields],
            'fields_lost': [f for f in snap1.active_fields if f not in snap2.active_fields],
        }


# ============================================================
# 5. Self-test
# ============================================================

if __name__ == '__main__':
    engine = SnapshotEngine()

    t1 = """我认为生命的意义在于持续理解世界的底层逻辑。始终追求真理和逻辑自洽是最核心的事。
    创造美和连接他人是理解真理的自然延伸。本质上所有领域的探索都是同一件事：寻找更深层的秩序。
    我清楚这个定位，它给了我面对一切的力量。"""

    t2 = """我以前觉得人生必须追求某种确定的意义，但最近越来越不确定。可能是创造什么，也可能是帮助别人。
    有时候觉得一切都没有意义，但又不甘心就这样放弃。一方面想追求自由，另一方面又觉得需要接受现实约束。
    我也说不清。"""

    t3 = """我绝对要成功，毫无疑问这是唯一的目标。但是有时候我也会想放下一切。
    虽然看起来矛盾但其实辩证地看，追求和放下是一体的。总之人生归根结底就是体验。
    但实际上我也不知道自己在说什么。痛苦和焦虑一直存在，但这不代表我就输了。"""

    test_cases = [
        ('Well-Anchored', t1),
        ('Transitional', t2),
        ('High-Heat-Tax', t3),
    ]

    results = []
    for name, text in test_cases:
        snap = engine.scan(text)
        if snap:
            results.append((name, snap))
            d = snap.to_dict()
            print(f'{name}:')
            print(f'  锚点强度={d["anchor_strength"]}/100  锚定={d["anchor_diagnosis"]["state"]}')
            print(f'  活跃场域={d["active_fields"]}')
            print(f'  叙事连贯性={d["coherence_score"]}')
            print(f'  热税={d["heat_tax"]["level"]}({d["heat_tax"]["composite"]}) 解读={d["heat_tax"]["interpretation"]}')
            print()

    if len(results) >= 2:
        delta = engine.compare(results[0][1], results[1][1])
        print(f'T1 vs T2 对比: anchor_delta={delta["anchor_strength_delta"]} heat_tax_delta={delta["heat_tax_delta"]} fields_gained={delta["fields_gained"]}')

    print('D5-005-03 认知快照基线扫描 测试完成')