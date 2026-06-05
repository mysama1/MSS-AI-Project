"""
D5-014: Purification Factory - Enhanced Test Suite
Covers all 4 modules: Worksort, Refinement, Crystallization, Safety + Pipeline orchestration
"""
import sys, os, json, unittest
sys.path.insert(0, r'C:\MSS-AI-Project')

from purification_factory import (
    CognitiveSample, SortingWorkshop, RefinementWorkshop,
    CrystallizationWorkshop, SafetyProtocol, PurificationFactory,
    LogicSurgeryEngine,
)


class TestCognitiveSample(unittest.TestCase):
    def test_create_sample(self):
        s = CognitiveSample('S001', 'test_source', 'raw text here')
        self.assertEqual(s.id, 'S001')
        self.assertEqual(s.contamination_rating, None)
        self.assertEqual(s.purified_propositions, [])

    def test_log_and_status(self):
        s = CognitiveSample('S002', 'src', 'content')
        s.log('workshop1', 'action', 'detail')
        s.contamination_rating = 'B'
        status = s.status()
        self.assertEqual(status['contamination'], 'B')
        self.assertEqual(status['vaccines'], 0)
        self.assertEqual(len(s.pipeline_log), 1)


class TestSortingWorkshop(unittest.TestCase):
    def setUp(self):
        self.ws = SortingWorkshop()

    def test_grade_C_perfect_storm(self):
        """Text with heavy K3 spiritual absolutism -> C"""
        text = "神告诉我这是绝对唯一的真理，其他都是错的。灵魂必须通过通灵拯救。毫无疑问。"
        smp = self.ws.process(CognitiveSample('S01', 'source', text))
        self.assertEqual(smp.contamination_rating, 'C')

    def test_grade_B_moderate(self):
        """Mixed signals -> B"""
        text = "这些深层逻辑揭示了意义场的调谐度层级。外星文明可能有更高的振动频率。"
        smp = self.ws.process(CognitiveSample('S02', 'source', text))
        self.assertIn(smp.contamination_rating, ('A', 'B'))

    def test_grade_A_clean(self):
        """MSS-compatible analytical text -> A"""
        text = "A3热税公理确立所有转换都有逻辑损耗。A5规范场开放包容是韧性根基。信息本体论是核心公理。"
        smp = self.ws.process(CognitiveSample('S03', 'source', text))
        self.assertEqual(smp.contamination_rating, 'A')

    def test_unicode_chinese(self):
        """Chinese text with mixed encoding characters"""
        text = "信息本体论是MSS的根本公理。物理层是逻辑层的投影而非独立因果层。"
        smp = self.ws.process(CognitiveSample('S04', 'source', text))
        self.assertIn(smp.contamination_rating, ('A', 'B'))

    def test_empty_text(self):
        smp = self.ws.process(CognitiveSample('S05', 'source', ''))
        self.assertIsNotNone(smp.contamination_rating)


class TestRefinementWorkshop(unittest.TestCase):
    def setUp(self):
        self.ws = RefinementWorkshop()
        # C-class gets blocked by safety gate; provide A/B
        self.ws_sample = CognitiveSample('S10', 'test', '')
        self.ws_sample.contamination_rating = 'B'

    def test_axiom_audit_A1(self):
        text = "物质决定意识，物理世界是真实的。"
        smp = CognitiveSample('S11', 'src', text)
        smp.contamination_rating = 'B'
        result = self.ws.process(smp)
        self.assertTrue(len(result.axiom_violations) > 0)

    def test_axiom_audit_A3_denial(self):
        text = "这个系统是完美的，零成本运行，毫无损失。"
        smp = CognitiveSample('S12', 'src', text)
        smp.contamination_rating = 'B'
        result = self.ws.process(smp)
        self.assertTrue(len(result.axiom_violations) > 0)

    def test_axiom_audit_A5_exclusive(self):
        text = "这是唯一的真理，其他都是错的。绝对正确的理论体系。"
        smp = CognitiveSample('S13', 'src', text)
        smp.contamination_rating = 'B'
        result = self.ws.process(smp)
        violations = [v for v in result.axiom_violations if 'A5' in v.get('axiom', '')]
        self.assertTrue(len(violations) > 0)

    def test_ascension_opportunity_detection(self):
        text = "这个悖论揭示了系统内在的矛盾。存在二律背反。"
        smp = CognitiveSample('S14', 'src', text)
        smp.contamination_rating = 'B'
        result = self.ws.process(smp)
        asc = [v for v in result.axiom_violations if 'A6' in v.get('axiom', '')]
        self.assertTrue(len(asc) > 0)

    def test_proposition_extraction(self):
        text = "A1公理确立信息本体论。物理层是投影。所有转换都有热税代价。"
        smp = CognitiveSample('S15', 'src', text)
        smp.contamination_rating = 'A'
        result = self.ws.process(smp)
        self.assertTrue(len(result.purified_propositions) >= 2)

    def test_paradigm_stripping(self):
        text = "灵魂通过轮回提升。外星人乘坐飞碟到来。科学证明一切都是进化决定的。"
        smp = CognitiveSample('S16', 'src', text)
        smp.contamination_rating = 'B'
        result = self.ws.process(smp)
        self.assertTrue(len(result.paradigm_artifacts) > 0)


class TestCrystallizationWorkshop(unittest.TestCase):
    def setUp(self):
        self.ws = CrystallizationWorkshop()

    def test_field_grouping(self):
        sample = CognitiveSample('S20', 'src', '')
        props = ['逻辑推理是核心', '宇宙本源是信息', '我们应该遵循热税公理', '系统结构决定韧性']
        blocks = self.ws._group_by_field(props)
        self.assertIn('LOGIC', blocks)
        self.assertIn('METAPHYSICS', blocks)
        self.assertIn('ETHICS', blocks)
        self.assertIn('SYSTEMS', blocks)

    def test_vaccine_generation(self):
        violation = {'axiom': 'A5_normative_field', 'issue': '封闭排他性规范场嫌疑'}
        vac = self.ws._generate_vaccine(violation, [])
        self.assertEqual(vac['target_axiom'], 'A5')
        self.assertIn('规范场弹性', vac['axiom_name'])

    def test_decode_map(self):
        artifacts = [{'pattern': '神', 'type': 'epoch_term', 'matches': ['神', '上帝']}]
        dm = self.ws._build_decode_map(artifacts)
        self.assertIn('神', dm)
        self.assertIn('上帝', dm)

    def test_summarize(self):
        sample = CognitiveSample('S21', 'src', 'test')
        sample.contamination_rating = 'B'
        sample.purified_propositions = ['p1', 'p2']
        summary = self.ws._summarize(sample)
        self.assertEqual(summary['grade'], 'B')


class TestSafetyProtocol(unittest.TestCase):
    def setUp(self):
        self.sp = SafetyProtocol()

    def test_physical_isolate_C_rejected(self):
        sample = CognitiveSample('S30', 'src', '')
        sample.contamination_rating = 'C'
        self.assertFalse(self.sp.physical_isolate(sample))

    def test_physical_isolate_B_allowed(self):
        sample = CognitiveSample('S31', 'src', '')
        sample.contamination_rating = 'B'
        self.assertTrue(self.sp.physical_isolate(sample))

    def test_virus_detection_absolutist(self):
        sample = CognitiveSample('S32', 'src', '')
        sample.purified_propositions = ['这是终极的完美解决方案']
        detected = self.sp.virus_purify(sample)
        self.assertTrue(len(detected) > 0)

    def test_virus_detection_exclusivity(self):
        sample = CognitiveSample('S33', 'src', '')
        sample.purified_propositions = ['这是唯一的道路，只有这样才能成功']
        detected = self.sp.virus_purify(sample)
        self.assertTrue(len(detected) > 0)

    def test_virus_detection_dogmatic(self):
        sample = CognitiveSample('S34', 'src', '')
        sample.purified_propositions = ['科学证明这是不容置疑的事实']
        detected = self.sp.virus_purify(sample)
        self.assertTrue(len(detected) > 0)

    def test_virus_detection_clean(self):
        sample = CognitiveSample('S35', 'src', '')
        sample.purified_propositions = ['热税公理要求所有转换都有逻辑损耗']
        detected = self.sp.virus_purify(sample)
        self.assertEqual(len(detected), 0)


class TestLogicSurgeryEngine(unittest.TestCase):
    def setUp(self):
        self.lse = LogicSurgeryEngine()

    def test_paradox_fuse_universal_negation(self):
        text = "所有规则都没有意义，一切努力都没有价值。"
        fused, clean = self.lse.paradox_fuse(text)
        self.assertTrue(len(fused) > 0, f'Expected paradoxes, got {len(fused)}')
        self.assertIn('PARADOX_FUSED', clean)

    def test_paradox_fuse_no_paradox(self):
        text = "热税公理确立所有转换都有逻辑损耗。"
        fused, clean = self.lse.paradox_fuse(text)
        self.assertEqual(len(fused), 0)

    def test_corrective_surgery_materialism(self):
        text = "物质决定意识是科学证明的真理。"
        corrections, clean = self.lse.corrective_surgery(text, [])
        self.assertTrue(any('信息' in c['replacement'] for c in corrections))
        self.assertIn('[信息是更基础的本体层级(A1)]', clean)

    def test_corrective_surgery_evolution(self):
        text = "进化是随机的，没有任何方向性。"
        corrections, clean = self.lse.corrective_surgery(text, [])
        self.assertTrue(any('调谐度' in c['replacement'] for c in corrections))

    def test_corrective_surgery_no_match(self):
        text = "MSS框架下信息是基础本体层。"
        corrections, clean = self.lse.corrective_surgery(text, [])
        self.assertEqual(len(corrections), 0)

    def test_prepare_vaccine_A1(self):
        v = {'axiom': 'A1_ontology', 'issue': '物质优先本体论嫌疑', 'severity': 'violation'}
        vaccine = self.lse.prepare_vaccine(v, ['信息是更基础的本体'])
        self.assertEqual(vaccine['target_axiom'], 'A1')
        self.assertIn('信息本体论', vaccine['name'])
        self.assertGreater(vaccine['efficacy_score'], 0.75)

    def test_prepare_vaccine_A6(self):
        v = {'axiom': 'A6_ascension', 'issue': '潜在升维机会', 'severity': 'warning'}
        vaccine = self.lse.prepare_vaccine(v, ['这个悖论是升维的信号'])
        self.assertEqual(vaccine['target_axiom'], 'A6')
        self.assertEqual(vaccine['half_life'], '长期')

    def test_prepare_vaccine_with_context(self):
        v = {'axiom': 'A5_normative_field', 'issue': '封闭排他性规范场', 'severity': 'violation'}
        vaccine = self.lse.prepare_vaccine(v, ['开放式系统', '多场耦合', '包容性设计'])
        self.assertTrue(len(vaccine.get('context_terms', [])) > 0)

    def test_surgery_status(self):
        self.lse.paradox_fuse('所有规则都没有意义。')
        self.lse.corrective_surgery('物质决定意识', [])
        self.lse.prepare_vaccine({'axiom': 'A1_ontology', 'issue': 'test', 'severity': 'warning'}, [])
        s = self.lse.status()
        self.assertGreater(s['paradoxes_fused'], 0)
        self.assertGreater(s['surgeries_performed'], 0)
        self.assertGreater(s['vaccines_prepared'], 0)


class TestPurificationFactory(unittest.TestCase):
    def setUp(self):
        self.factory = PurificationFactory()

    def test_full_pipeline_A_class(self):
        result = self.factory.purify(
            'TST-A', 'analytical', 
            '信息本体论是MSS的根本公理。物理层是逻辑层的投影。'
            '热税动力学要求所有转换都有代价。')
        self.assertIn(result.contamination_rating, ('A', 'B'))
        self.assertTrue(len(result.purified_propositions) > 0)

    def test_full_pipeline_C_blocked(self):
        result = self.factory.purify(
            'TST-C', 'spiritual',
            '神告诉我这是绝对唯一的真理。灵魂轮回是确定的。'
            '只有通灵才能救赎毫无疑问。完美零成本。')
        self.assertEqual(result.contamination_rating, 'C')
        self.assertEqual(len(result.purified_propositions), 0)

    def test_full_pipeline_scientism(self):
        result = self.factory.purify(
            'TST-D', 'scientific',
            '物理规则是绝对永恒不变的。量子随机性是纯随机的。'
            '人类意识完全由神经元决定。宇宙终极真理已被完全掌握。')
        self.assertIn(result.contamination_rating, ('A', 'B'))
        # K3 scientism should generate violations (absolutist physics + pure randomness + closed epistemology)
        violation_count = len(result.axiom_violations)
        self.assertTrue(violation_count > 0, f'Expected K3 scientism violations, got {violation_count}')

    def test_batch_purify(self):
        batch = [
            {'id': 'B01', 'source': 's1', 'text': '信息本体论。投影模型。热税公理。'},
            {'id': 'B02', 'source': 's2', 'text': '神唯一真理完美零成本毫无疑问。'},
            {'id': 'B03', 'source': 's3', 'text': '科学证明物理规则是绝对永恒的。'},
        ]
        results = self.factory.purify_batch(batch)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[1].contamination_rating, 'C')

    def test_factory_status(self):
        self.factory.purify('S001', 'src', '信息本体论投影模型热税公理')
        status = self.factory.factory_status()
        self.assertGreater(status['total_processed'], 0)
        self.assertIn('A', status['grade_distribution'])

    def test_vaccine_library_accumulation(self):
        self.factory.purify('S001', 'src', '物理规则绝对永恒不变。意识完全由神经元决定。')
        self.factory.purify('S002', 'src', '完美零成本绝对高效的唯一真理。')
        status = self.factory.factory_status()
        self.assertGreater(status['vaccine_library_size'], 0)


if __name__ == '__main__':
    unittest.main()