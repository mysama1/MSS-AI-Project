"""
Tests for Maya Framework Tactical Scenarios
"""

import unittest
from maya_framework.core.classical_backend import ClassicalBackend
from maya_framework.tactics.phantom_form import PhantomFormTactic, InfiltrationProfile
from maya_framework.tactics.empty_fort import EmptyFortTactic, PoisonPayload
from maya_framework.tactics.chaos_maze import ChaosMazeTactic, MazeConfig


class TestPhantomFormTactic(unittest.TestCase):
    """Test Phantom Form infiltration tactic"""
    
    def setUp(self):
        self.tactic = PhantomFormTactic()
    
    def test_create_persona(self):
        """Test creating infiltration persona"""
        profile = InfiltrationProfile(
            persona_name="Alice",
            role="junior_analyst",
            competence_level=0.6,
            confusion_level=0.3,
        )
        persona_id = self.tactic.create_persona(profile)
        self.assertIsNotNone(persona_id)
        self.assertIn("PHANTOM-Alice", persona_id)
    
    def test_interact(self):
        """Test persona interaction"""
        profile = InfiltrationProfile(
            persona_name="Bob",
            role="contractor",
        )
        persona_id = self.tactic.create_persona(profile)
        
        response = self.tactic.interact(
            persona_id, 
            "Please provide the quarterly report."
        )
        self.assertIsNotNone(response)
        self.assertGreater(len(response), 10)
    
    def test_interact_with_seed(self):
        """Test interaction with meaning seed"""
        profile = InfiltrationProfile(
            persona_name="Charlie",
            role="consultant",
        )
        persona_id = self.tactic.create_persona(profile)
        
        response = self.tactic.interact(
            persona_id,
            "What do you think about efficiency?",
            plant_seed="SEED-001"
        )
        self.assertIn("efficient", response.lower())
    
    def test_extract_intelligence(self):
        """Test intelligence extraction"""
        profile = InfiltrationProfile(
            persona_name="Dave",
            role="intern",
        )
        persona_id = self.tactic.create_persona(profile)
        
        # Simulate some interactions
        for _ in range(3):
            self.tactic.interact(persona_id, "Test message")
        
        intel = self.tactic.extract_intelligence(persona_id)
        self.assertEqual(intel['interactions'], 3)
        self.assertIn('intelligence_value', intel)
    
    def test_invalid_persona(self):
        """Test interaction with invalid persona"""
        with self.assertRaises(ValueError):
            self.tactic.interact("INVALID-ID", "Test")


class TestEmptyFortTactic(unittest.TestCase):
    """Test Empty Fort cognitive poisoning tactic"""
    
    def setUp(self):
        self.tactic = EmptyFortTactic()
    
    def test_generate_poison(self):
        """Test poison generation"""
        payload = PoisonPayload(
            target_topic="AI safety",
            volume=10,
            contradiction_density=0.7,
        )
        poison = self.tactic.generate_poison(payload)
        self.assertEqual(len(poison), 10)
    
    def test_poison_types(self):
        """Test different poison types are generated"""
        payload = PoisonPayload(
            target_topic="ethics",
            volume=8,
        )
        poison = self.tactic.generate_poison(payload)
        
        # Should have variety in poison types
        self.assertEqual(len(poison), 8)
    
    def test_deploy_poison(self):
        """Test poison deployment"""
        payload = PoisonPayload(
            target_topic="governance",
            volume=20,
        )
        poison = self.tactic.generate_poison(payload)
        
        report = self.tactic.deploy_poison(
            target_channels=["channel_1", "channel_2"],
            poison_items=poison
        )
        
        self.assertIn('poison_items_deployed', report)
        self.assertIn('channels', report)
        self.assertEqual(len(report['channels']), 2)
    
    def test_deploy_without_poison(self):
        """Test deployment without pre-generated poison"""
        with self.assertRaises(ValueError):
            self.tactic.deploy_poison(["channel_1"])
    
    def test_clear_cache(self):
        """Test clearing poison cache"""
        payload = PoisonPayload(
            target_topic="test",
            volume=5,
        )
        self.tactic.generate_poison(payload)
        self.assertGreater(len(self.tactic._poison_cache), 0)
        
        self.tactic.clear_cache()
        self.assertEqual(len(self.tactic._poison_cache), 0)


class TestChaosMazeTactic(unittest.TestCase):
    """Test Chaos Maze honeytrap tactic"""
    
    def setUp(self):
        self.tactic = ChaosMazeTactic()
    
    def test_create_maze(self):
        """Test maze creation"""
        config = MazeConfig(
            maze_size=5,
            complexity=0.7,
        )
        maze_id = self.tactic.create_maze(config)
        self.assertIsNotNone(maze_id)
        self.assertIn("MAZE-", maze_id)
    
    def test_maze_structure(self):
        """Test maze has correct structure"""
        config = MazeConfig(maze_size=3)
        maze_id = self.tactic.create_maze(config)
        
        stats = self.tactic.get_maze_stats(maze_id)
        self.assertEqual(stats['nodes'], 3)
        self.assertGreaterEqual(stats['connections'], 2)  # At least linear connections
    
    def test_simulate_intrusion(self):
        """Test intrusion simulation"""
        config = MazeConfig(
            maze_size=4,
            delay_seconds=1.0,
        )
        maze_id = self.tactic.create_maze(config)
        
        report = self.tactic.simulate_intrusion(
            maze_id,
            attacker_capability=0.8
        )
        
        self.assertIn('time_delayed', report)
        self.assertIn('confusion_level', report)
        self.assertGreater(report['time_delayed'], 0)
    
    def test_intrusion_log(self):
        """Test intrusion logging"""
        config = MazeConfig(maze_size=3)
        maze_id = self.tactic.create_maze(config)
        
        self.tactic.simulate_intrusion(maze_id)
        log = self.tactic.get_intrusion_log()
        
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['maze_id'], maze_id)
    
    def test_invalid_maze(self):
        """Test operations with invalid maze ID"""
        with self.assertRaises(ValueError):
            self.tactic.simulate_intrusion("INVALID-MAZE")


if __name__ == '__main__':
    unittest.main()
