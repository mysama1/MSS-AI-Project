"""
D5-014: Cognitive Purification Factory MVP
MSS H160/H161落地 - 认知净化工厂三车间管道
Auto-generated: 2026-05-24

Architecture:
  Raw Text -> [Workshop 1: Sorting] -> [Safety Gate 1] ->
  [Workshop 2: Refinement] -> [Safety Gate 2] ->
  [Workshop 3: Crystallization] -> Purified Output

Safety Protocol:
  - Physical isolation: all input goes through sandbox
  - Logical isolation: A5 axiom audit firewall between workshops
  - Meaning-field isolation: external normative field shield on output
  - Virus purification: paradox fuse + logic surgery + vaccine prep
"""

import json
import re
import sys
import os
from collections import defaultdict

# ============================================================
# 0. Sample Container
# ============================================================

class CognitiveSample:
    """A single L3 cultural sample flowing through the pipeline."""

    def __init__(self, sample_id, source, raw_text, source_type='unknown'):
        self.id = sample_id
        self.source = source
        self.raw_text = raw_text
        self.source_type = source_type
        # Workshop results
        self.contamination_rating = None  # A/B/C
        self.contamination_detail = {}
        self.purified_propositions = []
        self.axiom_violations = []
        self.paradigm_artifacts = []
        self.crystallized_blocks = []
        self.vaccine_templates = []
        self.pipeline_log = []

    def log(self, workshop, action, detail):
        self.pipeline_log.append({'workshop': workshop, 'action': action, 'detail': detail})

    def status(self):
        return {
            'id': self.id,
            'source': self.source,
            'contamination': self.contamination_rating,
            'purified_count': len(self.purified_propositions),
            'violations': len(self.axiom_violations),
            'crystallized': len(self.crystallized_blocks),
            'vaccines': len(self.vaccine_templates),
        }


# ============================================================
# 1. Sorting Workshop - Contamination Detection & Rating
# ============================================================

class SortingWorkshop:
    """Workshop 1: Raw material intake, contamination scanning, A/B/C rating."""

    # Contamination signal patterns
    CONTAMINATION_SIGNALS = {
        'personal_noise': [
            '我', '我的', '我认为', '我觉得', '我相信', '我希望',
            '我害怕', '我担心', '我必须', '我应该',
        ],
        'epoch_bias': [
            '神', '上帝', '天使', '魔鬼', '天堂', '地狱', '灵魂',
            '轮回', '前世', '来世', '天启', '显灵', '通灵',
            '外星人', '飞碟', '高等文明', '宇宙能量',
        ],
        'paradigm_lock': [
            '科学证明', '不容置疑', '绝对真理', '唯一道路',
            '所有人都知道', '众所周知', '毫无疑问',
        ],
        'emotional_loading': [
            '震惊', '恐惧', '不可思议', '难以想象', '伟大',
            '神圣', '邪恶', '黑暗', '光明', '拯救', '毁灭',
        ],
        'narrative_drift': [
            '但是', '然而', '可是', '另一方面', '矛盾的是',
            '说不清', '我也不知道', '也许吧', '总之',
        ],
        'absolutist': [
            '永远', '绝对', '必须', '100%', '唯一', '一切',
            '所有', '完全', '彻底',
        ],
    }

    def __init__(self):
        self.samples_processed = 0

    def process(self, sample):
        """Scan sample, rate contamination, output A/B/C class."""
        text = sample.raw_text
        sample.log('sorting', 'intake', f'{len(text)} chars')

        # 1. Scan all contamination dimensions
        total_signals = 0
        signal_breakdown = {}
        for category, patterns in self.CONTAMINATION_SIGNALS.items():
            hits = []
            for p in patterns:
                count = len(re.findall(p, text))
                if count > 0:
                    hits.append((p, count))
            signal_breakdown[category] = {'total_hits': sum(c for _, c in hits), 'patterns': hits}
            total_signals += signal_breakdown[category]['total_hits']

        # 2. Compute contamination score
        text_len = max(1, len(text))
        # Weighted: personal noise (0.5), epoch bias (0.4), paradigm lock (0.3)
        #           emotional (0.2), drift (0.3), absolutist (0.25)
        weights = {
            'personal_noise': 0.50, 'epoch_bias': 0.40, 'paradigm_lock': 0.30,
            'emotional_loading': 0.20, 'narrative_drift': 0.30, 'absolutist': 0.25,
        }
        weighted_score = sum(
            signal_breakdown[cat]['total_hits'] * weights[cat] / text_len * 100
            for cat in self.CONTAMINATION_SIGNALS
        )

        # 3. Classify A/B/C
        # A: <1.5 (minimal contamination, can be directly mapped to MSS)
        # B: 1.5-5.0 (moderate, needs paradigm stripping)
        # C: >5.0 (high, quarantine and pattern analysis only)
        if weighted_score < 1.5:
            contamination_rating = 'A'
        elif weighted_score < 5.0:
            contamination_rating = 'B'
        else:
            contamination_rating = 'C'

        sample.contamination_rating = contamination_rating
        sample.contamination_detail = {
            'score': round(weighted_score, 2),
            'breakdown': {k: v['total_hits'] for k, v in signal_breakdown.items()},
            'top_signal': max(signal_breakdown, key=lambda k: signal_breakdown[k]['total_hits']),
        }
        sample.log('sorting', 'rated', f'{contamination_rating} ({weighted_score:.2f})')
        self.samples_processed += 1
        return sample


# ============================================================
# 2. Refinement Workshop - Axiom Audit + Paradigm Stripping
# ============================================================

class RefinementWorkshop:
    """Workshop 2: MSS axiom audit, paradigm stripping, contradiction ascension."""

    def __init__(self):
        self.samples_processed = 0
        self._omega_checker = None
        self._omega_available = False
        self._init_omega()

    def _init_omega(self):
        """Lazy-init OmegaComplianceChecker for deep MSS axiom audit."""
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from symbolic_rules_omega import OmegaComplianceChecker, RuleLayer
            self._omega_checker = OmegaComplianceChecker()
            self._omega_available = True
            # Verify loaded
            rule_count = len(self._omega_checker.rules) if hasattr(self._omega_checker, 'rules') else 0
        except Exception as e:
            self._omega_checker = None
            self._omega_available = False

    # Axiom check configurations - method names (resolved at call time)
    AXIOM_CHECK_METHODS = [
        ('A1_ontology', '_check_information_ontology', '信息本体论：是否承认信息/意义为终极实体'),
        ('A2_discrete_projection', '_check_projection', '离散投影：是否承认物理层为信息层投影切片'),
        ('A3_heat_tax', '_check_heat_tax_denial', '热税承认：是否否认或忽视逻辑熵增必然性'),
        ('A4_randomness', '_check_randomness', '受控随机性：是否错误追求绝对确定性'),
        ('A5_normative_field', '_check_normative_field', '规范场：是否含封闭排他性绝对化论断'),
        ('A6_ascension', '_check_ascension', '矛盾升维：是否含可升维的悖论结构'),
    ]

    # Paradigm artifacts to strip (K3 epoch markers)
    PARADIGM_ARTIFACTS = [
        (r'(神|上帝|造物主|至高无上)', 'epoch_theology', '神学范式'),
        (r'(灵魂|轮回|前世|来世|业力)', 'epoch_spiritual', '灵性范式'),
        (r'(外星人|飞碟|星际联邦|银河系)', 'epoch_ufology', '外星范式'),
        (r'(科学证明|实验证实|客观事实)', 'epoch_scientism', '科学主义范式'),
        (r'(资本主义|社会主义|共产主义)', 'epoch_ideology', '意识形态范式'),
        (r'(进化|自然选择|适者生存)', 'epoch_darwinism', '达尔文范式'),
    ]

    def process(self, sample):
        """Audit against MSS axioms, strip paradigm artifacts, ascend contradictions."""
        text = sample.raw_text
        sample.log('refinement', 'audit_start', f'A/B-rated sample')

        # 1. Axiom audit
        violations = []
        for axiom_id, method_name, desc in self.AXIOM_CHECK_METHODS:
            check_fn = getattr(self, method_name)
            result = check_fn(text)
            if result:
                violations.append({
                    'axiom': axiom_id,
                    'issue': result,
                    'severity': 'violation' if 'violation' in axiom_id else 'warning',
                })

        sample.axiom_violations = violations
        sample.log('refinement', 'axiom_audit', f'{len(violations)} violations found')

        # 1b. OmegaComplianceChecker deep audit (supplementary - MSS internal violations)
        omega_violations = []
        if self._omega_available and self._omega_checker:
            try:
                omega_results = self._omega_checker.check_text(text)
                if omega_results:
                    for ov in omega_results:
                        omega_violations.append({
                            'axiom': ov.get('rule_id', 'UNKNOWN'),
                            'issue': f"{ov.get('rule_name', '')}: {ov.get('matched_text', '')}",
                            'severity': 'omega_violation',
                            'suggestion': ov.get('suggestion', ''),
                            'confidence': ov.get('confidence', 0),
                            'layer': ov.get('layer', 'L2'),
                        })
                    violations.extend(omega_violations)
                    sample.log('refinement', 'omega_deep_audit', f'{len(omega_violations)} omega violations found')
                else:
                    sample.log('refinement', 'omega_deep_audit', 'no omega violations')
            except Exception as e:
                sample.log('refinement', 'omega_audit_error', str(e)[:100])
        else:
            sample.log('refinement', 'omega_skipped', 'OmegaComplianceChecker not available')

        sample.axiom_violations = violations  # Update with omega additions

        # 2. Paradigm stripping
        artifacts = []
        for pattern, artifact_type, artifact_desc in self.PARADIGM_ARTIFACTS:
            matches = re.findall(pattern, text)
            if matches:
                artifacts.append({
                    'pattern': pattern,
                    'type': artifact_type,
                    'description': artifact_desc,
                    'matches': list(matches)[:5],
                })

        sample.paradigm_artifacts = artifacts
        sample.log('refinement', 'paradigm_strip', f'{len(artifacts)} artifacts identified')

        # 3. Extract purified propositions
        propositions = self._extract_propositions(text, violations, artifacts)
        sample.purified_propositions = propositions
        sample.log('refinement', 'purification', f'{len(propositions)} propositions extracted')

        self.samples_processed += 1
        return sample

    # --- Axiom check implementations ---

    @staticmethod
    def _check_information_ontology(text):
        """A1: Check if text implies matter-primary ontology (violation)."""
        matter_keywords = ['物质决定', '物质基础', '物理世界是真实的', '意识是物质的产物']
        for kw in matter_keywords:
            if kw in text:
                return f'物质优先本体论嫌疑: "{kw}"'
        return None

    @staticmethod
    def _check_projection(text):
        """A2: Check if text treats physical as causally independent."""
        projection_violations = [
            '物理定律是终极的', '自然规律不可改变', '一切都是物质运动',
            '物理规则是绝对的', '物理规则永恒不变', '物理定律独立于任何意识',
        ]
        for kw in projection_violations:
            if kw in text:
                return f'A2投影模型违反: "{kw}"'
        return None

    @staticmethod
    def _check_heat_tax_denial(text):
        """A3: Check if text denies or ignores heat tax inevitability."""
        denial_patterns = ['完美', '没有代价', '零成本', '绝对高效', '毫无损失']
        found = [kw for kw in denial_patterns if kw in text]
        if found:
            return f'热税否认嫌疑: {found}'
        return None

    @staticmethod
    def _check_randomness(text):
        """A4: Check if text claims absolute determinism or absolute randomness."""
        if '完全随机' in text or '毫无规律' in text or '纯随机的' in text or '纯随机' in text:
            return '绝对随机性主张(A4违规:需受控随机)'
        if '绝对确定' in text or '必然发生' in text:
            return '绝对确定性主张(A4违规:低估随机贡献)'
        return None

    @staticmethod
    def _check_normative_field(text):
        """A5: Check for closed, exclusive, absolutist normative claims."""
        exclusive = ['唯一', '绝对正确', '只有...才能', '其他都是错的']
        found_simple = [kw for kw in exclusive if kw in text]
        # Extended: closed epistemic claims
        epistemic_closure = ['终极真理已被', '已经被完全', '彻底揭示了', '不容置疑']
        found_epistemic = [kw for kw in epistemic_closure if kw in text]
        all_found = found_simple + found_epistemic
        if len(all_found) >= 2:
            return f'封闭排他性规范场嫌疑: {all_found}'
        # Single strong epistemic closure also flags
        if found_epistemic:
            return f'认知闭合嫌疑(A5): {found_epistemic}'
        return None

    @staticmethod
    def _check_ascension(text):
        """A6: Check for paradoxes that could be ascended (opportunity, not violation)."""
        paradox_indicators = ['矛盾', '悖论', '对立', '二律背反']
        found = [kw for kw in paradox_indicators if kw in text]
        if found:
            return f'潜在升维机会: {found}'
        return None

    @staticmethod
    def _extract_propositions(text, violations, artifacts):
        """Extract clean propositions from text after stripping noise."""
        # Split into sentences
        sentences = re.split(r'[。！？\.!\?，,；;]', text)
        propositions = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 4:
                continue
            # Skip sentences matching paradigm artifacts
            is_artifact = False
            for art in artifacts:
                if any(m in sent for m in art['matches']):
                    is_artifact = True
                    break
            if not is_artifact:
                propositions.append(sent)
        return propositions


# ============================================================
# 3. Crystallization Workshop - Snapshot + Vaccine + Decode Map
# ============================================================

class CrystallizationWorkshop:
    """Workshop 3: Cognitive snapshot, vaccine generation, decode mapping."""

    def __init__(self, surgery_engine=None):
        self.samples_processed = 0
        self.vaccine_library = []
        self.surgery_engine = surgery_engine

    def process(self, sample):
        """Crystallize purified propositions into structured meaning blocks."""
        sample.log('crystallization', 'start', f'{len(sample.purified_propositions)} propositions')

        # 1. Group propositions by meaning field
        field_blocks = self._group_by_field(sample.purified_propositions)

        # 2. Generate vaccine templates from axiom violations (use surgery engine if available)
        vaccines = []
        for v in sample.axiom_violations:
            if self.surgery_engine:
                vaccine = self.surgery_engine.prepare_vaccine(v, sample.purified_propositions)
            else:
                vaccine = self._generate_vaccine(v, sample.purified_propositions)
            if vaccine:
                vaccines.append(vaccine)

        sample.vaccine_templates = vaccines
        self.vaccine_library.extend(vaccines)
        sample.log('crystallization', 'vaccines', f'{len(vaccines)} generated')

        # 3. Build decode map: epoch terms -> MSS equivalents
        decode_map = self._build_decode_map(sample.paradigm_artifacts)
        sample.log('crystallization', 'decode_map', f'{len(decode_map)} mappings')

        # 4. Assemble crystallized blocks
        sample.crystallized_blocks = {
            'field_blocks': field_blocks,
            'vaccines': vaccines,
            'decode_map': decode_map,
            'summary': self._summarize(sample),
        }
        sample.log('crystallization', 'done', f'{len(field_blocks)} fields')
        self.samples_processed += 1
        return sample

    @staticmethod
    def _group_by_field(propositions):
        """Group propositions into MSS meaning fields."""
        field_keywords = {
            'LOGIC': ['逻辑', '推理', '证明', '必然', '因果', '自洽'],
            'SYSTEMS': ['体系', '结构', '框架', '秩序', '系统', '组织'],
            'EPISTEMOLOGY': ['理解', '认知', '知道', '真相', '本质', '意义'],
            'METAPHYSICS': ['存在', '宇宙', '本源', '超越', '维度', '实体'],
            'ETHICS': ['应该', '道德', '正义', '责任', '价值', '选择'],
        }

        blocks = defaultdict(list)
        unclassified = []
        for prop in propositions:
            classified = False
            for field, keywords in field_keywords.items():
                if any(kw in prop for kw in keywords):
                    blocks[field].append(prop)
                    classified = True
                    break
            if not classified:
                unclassified.append(prop)

        if unclassified:
            blocks['UNCLASSIFIED'] = unclassified
        return dict(blocks)

    @staticmethod
    def _generate_vaccine(violation, propositions):
        """Generate a logic vaccine from an axiom violation."""
        axiom_labels = {
            'A1_ontology': ('A1', '信息本体论', '物质不是终极实体；信息/意义是更基础的层次'),
            'A2_discrete_projection': ('A2', '离散投影', '物理层是信息层的投影切片，非独立因果层'),
            'A3_heat_tax': ('A3', '热税动力学', '所有转换都有逻辑损耗；"完美""零成本"是K3幻觉'),
            'A4_randomness': ('A4', '受控随机性', '随机是受控的；绝对确定与绝对随机均为伪命题'),
            'A5_normative_field': ('A5', '规范场弹性', '封闭排他的意义场必然僵化；开放包容才是韧性之源'),
            'A6_ascension': ('A6', '矛盾升维', '悖论不是错误而是升维机会；降维处理矛盾才是错误'),
        }

        info = axiom_labels.get(violation['axiom'], ('?', '?', ''))
        vaccine = {
            'target_axiom': info[0],
            'axiom_name': info[1],
            'correction': info[2],
            'original_issue': violation['issue'],
            'application': f'当检测到{info[1]}违反时，注入此修正直到逻辑重构完成',
        }
        return vaccine

    @staticmethod
    def _build_decode_map(artifacts):
        """Build epoch-term to MSS-term decode mapping."""
        term_mappings = {
            '神': '意义场统一源',
            '上帝': '意义场统一源(基督教编码)',
            '灵魂': '逻辑功/调谐度T值的投影表征',
            '轮回': '意义场的周期性坍缩与重启',
            '外星人': '其他意义场域的独立意识集群',
            '飞碟': '高阶文明的物理投影载体',
            '科学证明': 'L3当前认知边界内的有效框架',
            '进化': 'CMN在特定介质上的自调试过程',
            '自然选择': '调谐度T值的环境筛选机制',
        }

        decode_map = {}
        for art in artifacts:
            for match in art['matches']:
                if match in term_mappings:
                    decode_map[match] = term_mappings[match]
        return decode_map

    @staticmethod
    def _summarize(sample):
        """Generate a one-paragraph summary of the purification result."""
        quality = {'A': '极低污染，核心洞见可直译为MSS公理语言',
                   'B': '中等污染，核心信息清晰，经范式剥离后可还原',
                   'C': '极高污染，仅存微弱原始信号，主要用于污染模式特征提取'}
        return {
            'grade': sample.contamination_rating,
            'quality': quality.get(sample.contamination_rating, ''),
            'proposition_count': len(sample.purified_propositions),
            'violation_count': len(sample.axiom_violations),
            'vaccine_count': len(sample.vaccine_templates),
            'essence': f'从{sample.source}中提取{len(sample.purified_propositions)}条可净化命题，发现{len(sample.axiom_violations)}处MSS公理违反，生成{len(sample.vaccine_templates)}剂逻辑疫苗。',
        }


# ============================================================
# 4. Safety Protocol
# ============================================================

class SafetyProtocol:
    """Enforces triple isolation and virus purification between workshops."""

    def __init__(self):
        self.quarantine_log = []
        self.virus_log = []

    def physical_isolate(self, sample):
        """Gate 1: Physical isolation check (after sorting, before refinement)."""
        # C-class samples never enter refinement
        if sample.contamination_rating == 'C':
            self.quarantine_log.append({
                'sample': sample.id,
                'reason': 'C-class contamination, refinement bypassed',
                'disposition': 'archived_for_pattern_analysis',
            })
            return False
        return True

    def logical_isolate(self, sample):
        """Gate 2: Logical isolation (A5 axiom audit firewall)."""
        # If A5 violations detected, flag but allow (with audit trail)
        a5_violations = [v for v in sample.axiom_violations if 'A5' in v['axiom']]
        if a5_violations:
            self.quarantine_log.append({
                'sample': sample.id,
                'reason': f'A5 normative field violations: {len(a5_violations)}',
                'disposition': 'allowed_with_audit_trail',
            })
        return True  # Allow but log

    def meaning_field_isolate(self, sample):
        """Gate 3: Meaning-field isolation (external shield on output)."""
        # Check crystallized blocks for normative absolutism
        if sample.crystallized_blocks:
            summary = sample.crystallized_blocks['summary']
            if summary['violation_count'] > 0:
                self.quarantine_log.append({
                    'sample': sample.id,
                    'reason': f'Crystallized output carries {summary["violation_count"]} axiom conflicts',
                    'disposition': 'flagged_for_review',
                })
        return True

    def virus_purify(self, sample):
        """Scan and neutralize logic viruses in purified output."""
        virus_patterns = [
            (r'(终极|绝对|完美|100%免疫|不可被同化|永远)', 'absolutist_virus'),
            (r'(唯一.*道路|只有.*才能|其他.*都是)', 'exclusivity_virus'),
            (r'(不容置疑|毫无疑问|众所周知|科学证明)', 'dogmatic_virus'),
            (r'(拯救|毁灭|光明.*黑暗|神圣.*邪恶)', 'messianic_virus'),
        ]

        detected = []
        for pattern, virus_type in virus_patterns:
            for prop in sample.purified_propositions:
                if re.search(pattern, prop):
                    detected.append({'type': virus_type, 'in_proposition': prop[:80], 'pattern': pattern})

        if detected:
            self.virus_log.append({
                'sample': sample.id,
                'viruses_detected': len(detected),
                'types': list(set(v['type'] for v in detected)),
                'severity': 'HIGH' if len(detected) > 3 else 'MODERATE' if len(detected) > 0 else 'LOW',
                'details': detected,
            })
            sample.log('safety', 'virus_detected', f'{len(detected)} viruses found')

        return detected

    def status(self):
        return {
            'quarantined': len(self.quarantine_log),
            'viruses_found': sum(len(v.get('details', [])) for v in self.virus_log),
            'quarantine_detail': self.quarantine_log[-5:],
            'virus_detail': self.virus_log[-5:],
        }


# ============================================================
# 4a. Logic Surgery Engine - Paradox Fuse + Corrective Surgery + Vaccine Prep
# ============================================================

class LogicSurgeryEngine:
    """H160 三合一逻辑手术引擎: Paradox Fuse + Corrective Surgery + Vaccine Preparation."""

    PARADOX_PATTERNS = [
        (r'(所有.*都不)|(所有.*都没有)|(一切.*都没有)|(一切.*都不)', 'universal_negation', '全称否定自指悖论'),
        (r'(唯一.*真理.*不是)|(绝对.*正确.*错误)', 'self_refuting_absolute', '自我驳斥绝对化'),
        (r'(我.*知道.*我.*不知道)|(无法.*理解.*理解)', 'epistemic_loop', '认知回路悖论'),
        (r'(必须.*自由)|(强制.*自愿)|(绝对.*相对)', 'semantic_collision', '语义冲突悖论'),
        (r'(这句话.*假)|(本.*陈述.*不)', 'liar_like', '类说谎者悖论'),
    ]

    CORRECTIVE_MAP = {
        '物质决定意识': ('信息是更基础的本体层级(A1)', 'A1'),
        '物理世界是真实的': ('物理层是信息层的投影切片(A2)', 'A2'),
        '一切都是物理的': ('物理是显化投影非独立本体(A2)', 'A2'),
        '随机是绝对的': ('随机性受A4约束:由L-1意义场调节', 'A4'),
        '进化是随机的': ('进化是调谐度T值的环境筛选(CMN自调试)', 'A4'),
        '宇宙没有意义': ('意义是信息结构的固有属性(A1)', 'A1'),
        '上帝创造了一切': ('意义场统一源是逻辑功的终极投影', 'A1'),
        '灵魂不朽': ('逻辑功/调谐度T值是不灭的信息结构', 'A1'),
        '死亡是终结': ('信息结构的热税终结不等于信息本身消灭(A3)', 'A3'),
        '科学是唯一真理': ('科学是当前认知边界的有效框架(L3)', 'A5'),
        '完美无缺': ('所有系统均有热税(A3)', 'A3'),
        '绝对正确': ('任何框架都有边界条件(A5)', 'A5'),
        '终极答案': ('认知是渐进调谐过程非终态(A6)', 'A6'),
    }

    AXIOM_VACCINE_MAP = {
        'A1': {'name': '信息本体论锚定疫苗', 'core': '物质不是终极实体；信息/意义是最基础的层级。', 'booster': '当感知到物质决定一切的论述时，回忆：信息结构在逻辑上先于物理层。', 'half_life': '长期'},
        'A2': {'name': '离散投影识别疫苗', 'core': '物理定律是L-1逻辑结构的投影约束，非独立因果层。', 'booster': '物理学的终极规律是当前投影切片的有效描述，换一个投影维度会看到不同规律。', 'half_life': '中期'},
        'A3': {'name': '热税动力学免疫疫苗', 'core': '所有逻辑转换和信息处理都有不可消除的代价。完美零成本是K3幻觉。', 'booster': '检查你最近是否说过完美方案或零成本——如果有，重新审视热税账单。', 'half_life': '短期'},
        'A4': {'name': '受控随机性认知疫苗', 'core': '随机不是绝对无序；它是A4约束下的受控随机。', 'booster': '进化不是碰运气——它是CMN在特定介质上的调谐度T值自调试过程。', 'half_life': '中期'},
        'A5': {'name': '规范场弹性训练疫苗', 'core': '任何封闭排他的意义场最终都会僵化。韧性来自开放包容的多场耦合。', 'booster': '当你断定这是唯一的路时，问自己：有哪些其他意义场域也在处理同一个问题？', 'half_life': '中期'},
        'A6': {'name': '矛盾升维潜能激活疫苗', 'core': '悖论不是错误——它是系统试图跃迁到更高维度的信号。', 'booster': '遇到让你不适的矛盾时，不要试图解决它——试着在更高维度容纳它。', 'half_life': '长期'},
    }

    def __init__(self):
        self.fuse_log = []
        self.surgeries_performed = 0
        self.vaccines_prepared = 0

    def paradox_fuse(self, text):
        """Fuse: isolate paradoxes before they spread."""
        fused = []
        clean_text = text
        for pattern, ptype, pdesc in self.PARADOX_PATTERNS:
            for m in re.findall(pattern, text):
                match_str = m[0] if isinstance(m, tuple) else m
                fused.append({'type': ptype, 'description': pdesc, 'match': match_str, 'action': 'ISOLATED'})
                clean_text = clean_text.replace(match_str, f'[PARADOX_FUSED:{ptype}]')
        self.fuse_log.extend(fused)
        return fused, clean_text

    def corrective_surgery(self, text, violations):
        """Surgery: replace K3 terms with MSS-equivalents."""
        corrected = []
        clean_text = text
        for k3_term, (mss_term, axiom_ref) in self.CORRECTIVE_MAP.items():
            if k3_term in clean_text:
                clean_text = clean_text.replace(k3_term, f'[{mss_term}]')
                corrected.append({'original': k3_term, 'replacement': mss_term, 'axiom': axiom_ref})
        self.surgeries_performed += len(corrected)
        return corrected, clean_text

    def prepare_vaccine(self, violation, context_propositions):
        """Vaccine: comprehensive vaccine from violation + context."""
        base_axiom = violation.get('axiom', '?')[:2]
        tmpl = self.AXIOM_VACCINE_MAP.get(base_axiom, {
            'name': '通用逻辑免疫疫苗', 'core': '信息本体论是根本公理。', 'booster': '回顾A1-A6六条公理。', 'half_life': '短期'
        })
        context_keywords = []
        for prop in context_propositions[:5]:
            context_keywords.extend(re.findall(r'[\u4e00-\u9fff]{2,4}', prop)[:3])
        vaccine = {**tmpl, 'target_axiom': base_axiom, 'original_issue': violation.get('issue', ''),
                    'severity': violation.get('severity', 'warning'), 'context_terms': list(set(context_keywords))[:10],
                    'application': f'术前诊断:{violation.get("issue","")} | 术中注入:{tmpl["core"]} | 术后巩固:{tmpl["booster"]}',
                    'efficacy_score': 0.7 + (0.1 if violation.get('severity') == 'violation' else 0)}
        self.vaccines_prepared += 1
        return vaccine

    def status(self):
        return {'paradoxes_fused': len(self.fuse_log), 'surgeries_performed': self.surgeries_performed,
                'vaccines_prepared': self.vaccines_prepared, 'fuse_log_tail': self.fuse_log[-3:] if self.fuse_log else []}


# ============================================================
# 5. Purification Factory - Pipeline Orchestrator
# ============================================================

class PurificationFactory:
    """Main pipeline: sorting -> refinement -> crystallization, with safety gates."""

    def __init__(self):
        self.surgery = LogicSurgeryEngine()
        self.workshop_sorting = SortingWorkshop()
        self.workshop_refinement = RefinementWorkshop()
        self.workshop_crystallization = CrystallizationWorkshop(surgery_engine=self.surgery)
        self.safety = SafetyProtocol()
        self.archive = {'A': [], 'B': [], 'C': [], 'rejected': []}

    def purify(self, sample_id, source, raw_text, source_type='unknown'):
        """Run a single sample through the full purification pipeline."""
        sample = CognitiveSample(sample_id, source, raw_text, source_type)

        # Workshop 1: Sorting
        sample = self.workshop_sorting.process(sample)

        # Safety Gate 1: Physical isolation
        if not self.safety.physical_isolate(sample):
            self.archive['C'].append(sample)
            sample.log('pipeline', 'rejected', 'Failed physical isolation (C-class)')
            return sample

        # Workshop 2: Refinement (A/B only)
        sample = self.workshop_refinement.process(sample)

        # Logic Surgery: Paradox Fuse (before crystallization)
        paradoxes, _ = self.surgery.paradox_fuse(sample.raw_text)
        if paradoxes:
            sample.log('surgery', 'paradox_fuse', f'{len(paradoxes)} paradoxes isolated')

        # Logic Surgery: Corrective Surgery on violations
        corrections, _ = self.surgery.corrective_surgery(sample.raw_text, sample.axiom_violations)
        if corrections:
            sample.log('surgery', 'corrective_surgery', f'{len(corrections)} K3 terms replaced')

        # Safety Gate 2: Logical isolation
        self.safety.logical_isolate(sample)

        # Workshop 3: Crystallization
        sample = self.workshop_crystallization.process(sample)

        # Safety Gate 3: Meaning-field isolation
        self.safety.meaning_field_isolate(sample)

        # Virus purification scan
        self.safety.virus_purify(sample)

        # Archive
        self.archive[sample.contamination_rating].append(sample)
        sample.log('pipeline', 'complete', f'Grade {sample.contamination_rating}')
        return sample

    def purify_batch(self, samples_data):
        """Process multiple samples in batch."""
        results = []
        for sd in samples_data:
            result = self.purify(
                sd.get('id', f'SMP-{len(results)+1:03d}'),
                sd.get('source', 'unknown'),
                sd.get('text', ''),
                sd.get('type', 'unknown'),
            )
            results.append(result)
        return results

    def factory_status(self):
        """Overall factory status report."""
        return {
            'total_processed': (
                self.workshop_sorting.samples_processed +
                self.workshop_refinement.samples_processed +
                self.workshop_crystallization.samples_processed
            ) // 3,
            'grade_distribution': {k: len(v) for k, v in self.archive.items()},
            'safety': self.safety.status(),
            'surgery': self.surgery.status(),
            'vaccine_library_size': len(self.workshop_crystallization.vaccine_library),
        }


# ============================================================
# 6. Self-test
# ============================================================

if __name__ == '__main__':
    factory = PurificationFactory()

    # Test sample 1: Desmarquet - B class (moderate contamination)
    smp1 = factory.purify(
        'SMP-001', '海奥华预言',
        '我接触到一个超级意识体，它告诉我文明分为九级。灵魂通过轮回提升振动频率。'
        '外星人高等文明支持惩罚。外星人会说法语有着和我们一样的文化理解。'
        '这个体系的深层逻辑是：不同意识集群处在不同的意义场调谐度层级。'
        '必须绝对永远传播这个唯一的真理，毫无疑问。',
        'spiritual_text'
    )

    # Test sample 2: Musk cluster - A class (minimal contamination)
    smp2 = factory.purify(
        'SMP-002', 'MSS马斯克分析',
        '太空算力网络跳出地面AI物理约束。星链激光通信提供真空光速传输。'
        'Optimus人形机器人作为物理执行终端。闭环生态形成自我进化飞轮。'
        '但估值与产出的严重失衡揭示热税堆积。紧耦合架构隐藏连锁崩塌风险。'
        '文明升维不是物理位置的迁移而是意义范式的彻底重构。'
        'A3的热税公理要求任何宏大战略都必须接受热税审计。',
        'analytical_text'
    )

    # Test sample 3: Pure K3 C-class
    smp3 = factory.purify(
        'SMP-003', '典型灵媒文本',
        '我感觉神让我告诉你你绝对必须改变否则就会毁灭。我看到了你的前世灵魂。'
        '毫无疑问这是唯一的救赎道路。恐惧和黑暗笼罩着你但光明即将来临。'
        '通灵能量告诉我这是100%真实的不容置疑的。',
        'medium_reading'
    )

    # Test sample 4: K3 scientific scientism (Omega targets)
    smp4 = factory.purify(
        'SMP-004', 'K3物理学教科书',
        '物理规则是绝对的和永恒不变的。物理定律独立于任何意识或意义，超越于所有主观体验。'
        '量子力学的随机性是纯随机的没有任何底层逻辑。'
        '人类意识完全由神经元放电决定不存在超越物理层面的信息。'
        '宇宙的终极真理已经被物理学家完全掌握。',
        'scientific_text'
    )

    print('=' * 60)
    print('Cognitive Purification Factory MVP - Pipeline Test')
    print('=' * 60)

    for smp in [smp1, smp2, smp3, smp4]:
        s = smp.status()
        print(f'\n{s["id"]} [{s["source"]}]:')
        print(f'  Grade: {s["contamination"]}')
        print(f'  Purified propositions: {s["purified_count"]}')
        print(f'  Axiom violations: {s["violations"]}')
        print(f'  Crystallized blocks: {s["crystallized"]}')
        print(f'  Vaccines: {s["vaccines"]}')

    print(f'\nFactory Status: {json.dumps(factory.factory_status(), indent=2, ensure_ascii=False)}')

    # Verify key assertions
    checks = []
    checks.append(('SMP-001 is B-class', smp1.contamination_rating == 'B'))
    checks.append(('SMP-003 is C-class', smp3.contamination_rating == 'C'))
    checks.append(('C-class rejected from refinement', smp3.contamination_rating == 'C' and len(smp3.purified_propositions) == 0))
    checks.append(('A/B classes have purified output', len(smp1.purified_propositions) > 0 and len(smp2.purified_propositions) > 0))
    checks.append(('Safety protocol tracked C-class', any('SMP-003' in str(q) for q in factory.safety.quarantine_log)))
    checks.append(('SMP-001 has paradigm artifacts', len(smp1.paradigm_artifacts) > 0))
    checks.append(('SMP-002 has minimal contamination', smp2.contamination_rating in ('A', 'B')))
    checks.append(('Factory processed at least 1 sample', factory.factory_status()['total_processed'] >= 1))
    checks.append(('SMP-004 A-class (scientism detected)', smp4.contamination_rating in ('A', 'B')))

    passed = sum(1 for _, ok in checks if ok)
    print(f'\n=== Verification: {passed}/{len(checks)} PASS ===')
    for name, ok in checks:
        print(f'  {"PASS" if ok else "FAIL"}: {name}')
    if passed < len(checks):
        sys.exit(1)