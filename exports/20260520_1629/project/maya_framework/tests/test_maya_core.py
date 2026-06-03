"""
Tests for Maya Framework Core Components
"""

import unittest
from maya_framework.core.classical_backend import ClassicalBackend, FittingConfig, FittingMode
from maya_framework.core.meaning_seed import MeaningSeed, SeedType, SeedLibrary


class TestClassicalBackend(unittest.TestCase):
    """Test classical fitting backend"""
    
    def setUp(self):
        self.backend = ClassicalBackend()
    
    def test_generate_smooth(self):
        """Test smooth mode generation"""
        config = FittingConfig(mode=FittingMode.SMOOTH)
        result = self.backend.generate("Test prompt", config)
        self.assertIn("[SMOOTH]", result)
        self.assertGreater(len(result), 50)
    
    def test_generate_chaos(self):
        """Test chaos mode generation"""
        config = FittingConfig(mode=FittingMode.CHAOS)
        result = self.backend.generate("Test prompt", config)
        self.assertIn("[CHAOS]", result)
        self.assertIn("while simultaneously", result)
    
    def test_generate_poison(self):
        """Test poison mode generation"""
        config = FittingConfig(mode=FittingMode.POISON)
        result = self.backend.generate("Test prompt", config)
        self.assertIn("[POISON]", result)
        self.assertIn("yet", result)
    
    def test_generate_mimic(self):
        """Test mimic mode generation"""
        config = FittingConfig(mode=FittingMode.MIMIC, persona_hint="analyst")
        result = self.backend.generate("Test prompt", config)
        self.assertIn("[MIMIC:analyst]", result)
    
    def test_default_config(self):
        """Test default configuration"""
        result = self.backend.generate("Test prompt")
        self.assertIn("[SMOOTH]", result)
    
    def test_heat_tax_tracking(self):
        """Test heat tax accumulation"""
        initial_tax = self.backend.get_heat_tax()
        self.assertEqual(initial_tax, 0.0)
        
        self.backend.generate("Test")
        # Heat tax should still be 0 in mock implementation
        self.backend.reset_heat_tax()
        self.assertEqual(self.backend.get_heat_tax(), 0.0)


class TestMeaningSeed(unittest.TestCase):
    """Test meaning seed operations"""
    
    def test_seed_creation(self):
        """Test creating a meaning seed"""
        seed = MeaningSeed(
            seed_id="TEST-001",
            seed_type=SeedType.COGNITIVE,
            payload={'concept': 'test'},
            carrier_phrase="This is a test carrier.",
        )
        self.assertEqual(seed.seed_id, "TEST-001")
        self.assertEqual(seed.seed_type, SeedType.COGNITIVE)
    
    def test_seed_serialization(self):
        """Test seed JSON serialization"""
        seed = MeaningSeed(
            seed_id="TEST-002",
            seed_type=SeedType.LOGICAL,
            payload={'key': 'value'},
            carrier_phrase="Carrier text.",
        )
        json_str = seed.to_json()
        self.assertIn("TEST-002", json_str)
        self.assertIn("LOGICAL", json_str)
        
        restored = MeaningSeed.from_json(json_str)
        self.assertEqual(restored.seed_id, seed.seed_id)
        self.assertEqual(restored.payload, seed.payload)
    
    def test_seed_embedding(self):
        """Test embedding seed in text"""
        seed = MeaningSeed(
            seed_id="TEST-003",
            seed_type=SeedType.EMOTIONAL,
            payload={'emotion': 'curiosity'},
            carrier_phrase="Isn't it fascinating how things connect?",
        )
        text = "Some initial text."
        embedded = seed.embed(text)
        self.assertIn(text, embedded)
        self.assertIn(seed.carrier_phrase, embedded)
    
    def test_seed_extraction(self):
        """Test extracting seed from text"""
        seed = MeaningSeed(
            seed_id="TEST-004",
            seed_type=SeedType.SEMANTIC,
            payload={'meaning': 'depth'},
            carrier_phrase="Look deeper.",
        )
        text = seed.embed("Base text.")
        extracted = seed.extract(text)
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted['meaning'], 'depth')
    
    def test_seed_extraction_failure(self):
        """Test extraction when seed not present"""
        seed = MeaningSeed(
            seed_id="TEST-005",
            seed_type=SeedType.COGNITIVE,
            payload={'test': 'data'},
            carrier_phrase="Unique phrase.",
        )
        extracted = seed.extract("Text without the phrase.")
        self.assertIsNone(extracted)


class TestSeedLibrary(unittest.TestCase):
    """Test seed library operations"""
    
    def setUp(self):
        self.library = SeedLibrary()
    
    def test_default_seeds_loaded(self):
        """Test that default seeds are loaded"""
        seeds = self.library.list_seeds()
        self.assertGreater(len(seeds), 0)
    
    def test_get_seed(self):
        """Test retrieving a seed"""
        seed = self.library.get_seed("SEED-001")
        self.assertIsNotNone(seed)
        self.assertEqual(seed.seed_id, "SEED-001")
    
    def test_get_nonexistent_seed(self):
        """Test retrieving non-existent seed"""
        seed = self.library.get_seed("NONEXISTENT")
        self.assertIsNone(seed)
    
    def test_add_custom_seed(self):
        """Test adding custom seed"""
        new_seed = MeaningSeed(
            seed_id="CUSTOM-001",
            seed_type=SeedType.COGNITIVE,
            payload={'custom': 'data'},
            carrier_phrase="Custom carrier.",
        )
        self.library.add_seed(new_seed)
        retrieved = self.library.get_seed("CUSTOM-001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.seed_id, "CUSTOM-001")


if __name__ == '__main__':
    unittest.main()
