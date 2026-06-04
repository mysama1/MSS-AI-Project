import unittest
from chaos_sandbox import ChaosSandbox, ParadoxWorld

class TestChaosSandbox(unittest.TestCase):
    def setUp(self):
        self.sandbox = ChaosSandbox()
        self.agent = self.sandbox.register_agent('TEST-AGENT', {
            'cognitive_style': 'test',
            'baseline_t': 0.5
        })
    
    def test_worlds_initialized(self):
        self.assertEqual(len(self.sandbox.worlds), 10)
    
    def test_world_properties(self):
        world = self.sandbox.worlds['PW-001']
        self.assertEqual(world.name, 'Liar Labyrinth')
        self.assertEqual(world.difficulty, 3)
        self.assertEqual(world.paradox_type, 'self_reference')
    
    def test_agent_registration(self):
        self.assertEqual(self.agent['id'], 'TEST-AGENT')
        self.assertEqual(self.agent['baseline']['baseline_t'], 0.5)
    
    def test_empty_strategy_fails(self):
        result = self.sandbox.run_simulation('TEST-AGENT', 'PW-001', [])
        self.assertEqual(result['pt_score'], 0)
        self.assertEqual(result['exit_state'], 'STUCK')
    
    def test_ascend_strategy_succeeds(self):
        strategy = [
            {'type': 'OBSERVE', 'consistent': True},
            {'type': 'ASCEND', 'consistent': True},
            {'type': 'RESOLVE', 'consistent': True}
        ]
        result = self.sandbox.run_simulation('TEST-AGENT', 'PW-001', strategy)
        self.assertGreater(result['pt_score'], 50)
        self.assertEqual(result['exit_state'], 'RESOLVED')
    
    def test_inconsistent_strategy_penalty(self):
        strategy = [
            {'type': 'OBSERVE', 'consistent': False},
            {'type': 'ASCEND', 'consistent': True},
            {'type': 'RESOLVE', 'consistent': True}
        ]
        result = self.sandbox.run_simulation('TEST-AGENT', 'PW-001', strategy)
        # Inconsistency should reduce score
        self.assertLess(result['pt_score'], 85)
    
    def test_spectrum_generation(self):
        strategies = {
            'PW-001': [{'type': 'ASCEND', 'consistent': True}, {'type': 'RESOLVE', 'consistent': True}],
            'PW-003': [{'type': 'ASCEND', 'consistent': True}, {'type': 'RESOLVE', 'consistent': True}],
        }
        for wid, strat in strategies.items():
            self.sandbox.run_simulation('TEST-AGENT', wid, strat)
        spec = self.sandbox.generate_spectrum('TEST-AGENT')
        self.assertIsNotNone(spec)
        self.assertIn('self_reference', spec)
        self.assertIn('identity_crisis', spec)
        self.assertIsNotNone(spec['self_reference'])
        self.assertIsNotNone(spec['identity_crisis'])
    
    def test_overall_pt_calculation(self):
        for wid in ['PW-001', 'PW-010']:
            self.sandbox.run_simulation('TEST-AGENT', wid, [
                {'type': 'ASCEND', 'consistent': True},
                {'type': 'RESOLVE', 'consistent': True}
            ])
        self.sandbox.generate_spectrum('TEST-AGENT')
        self.assertIsNotNone(self.agent['overall_pt'])
        self.assertGreaterEqual(self.agent['overall_pt'], 0)
        self.assertLessEqual(self.agent['overall_pt'], 100)
    
    def test_paradigm_breakthrough(self):
        for wid in ['PW-009', 'PW-010']:
            self.sandbox.run_simulation('TEST-AGENT', wid, [
                {'type': 'ASCEND', 'consistent': True},
                {'type': 'ASCEND', 'consistent': True},
                {'type': 'RESOLVE', 'consistent': True}
            ])
        self.sandbox.generate_spectrum('TEST-AGENT')
        self.assertIsNotNone(self.agent['paradigm_breakthrough'])
    
    def test_invalid_world(self):
        result = self.sandbox.run_simulation('TEST-AGENT', 'INVALID', [])
        self.assertIn('error', result)
    
    def test_unregistered_agent(self):
        result = self.sandbox.run_simulation('UNKNOWN', 'PW-001', [])
        self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main()
