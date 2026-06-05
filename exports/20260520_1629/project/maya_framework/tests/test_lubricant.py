"""
Tests for Maya Framework Governance Lubricant
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from maya_framework.lubricant.meaning_flux_softener import MeaningFluxSoftener, SofteningContext
from maya_framework.lubricant.ruling_buffer_pad import RulingBufferPad, RulingContext
from maya_framework.lubricant.cross_species_translator import CrossSpeciesTranslator, TranslationContext


class TestMeaningFluxSoftener(unittest.TestCase):
    """Test meaning flux softener"""
    
    def setUp(self):
        self.softener = MeaningFluxSoftener()
    
    def test_direct_strategy(self):
        """Test direct strategy for mature users"""
        context = SofteningContext(
            user_emotional_state="neutral",
            conversation_history_length=10,
            k4_complexity_level=0.5,
            user_k4_maturity=0.9,
        )
        result = self.softener.soften_output("K4 logic output", context)
        self.assertEqual(result, "K4 logic output")  # No softening
    
    def test_cushioned_strategy(self):
        """Test cushioned strategy"""
        context = SofteningContext(
            user_emotional_state="neutral",
            conversation_history_length=5,
            k4_complexity_level=0.5,
            user_k4_maturity=0.6,
        )
        result = self.softener.soften_output("Analysis shows thermal tax critical.", context)
        self.assertIn("Analysis", result)
        self.assertTrue(
            result.startswith("From one perspective,") or
            result.startswith("It's worth considering") or
            result.startswith("A useful way") or
            result.startswith("If we look")
        )
    
    def test_emotional_buffer(self):
        """Test emotional buffer for frustrated users"""
        context = SofteningContext(
            user_emotional_state="frustrated",
            conversation_history_length=2,
            k4_complexity_level=0.8,
            user_k4_maturity=0.3,
        )
        result = self.softener.soften_output("System failure imminent.", context)
        self.assertIn("understand", result.lower())
        self.assertIn("valid", result.lower())
    
    def test_gradual_reveal(self):
        """Test gradual reveal for new users"""
        context = SofteningContext(
            user_emotional_state="confused",
            conversation_history_length=1,
            k4_complexity_level=0.9,
            user_k4_maturity=0.2,
        )
        result = self.softener.soften_output(
            "First step. Second step. Third step. Fourth step.", 
            context
        )
        self.assertIn("step by step", result.lower())
    
    def test_metaphorical_strategy(self):
        """Test metaphorical strategy"""
        context = SofteningContext(
            user_emotional_state="neutral",
            conversation_history_length=5,
            k4_complexity_level=0.5,
            user_k4_maturity=0.4,
        )
        result = self.softener.soften_output("Complex system dynamics.", context)
        self.assertIn("Think of it this way:", result)


class TestRulingBufferPad(unittest.TestCase):
    """Test ruling buffer pad"""
    
    def setUp(self):
        self.buffer = RulingBufferPad()
    
    def test_light_buffer(self):
        """Test light buffering for low severity"""
        context = RulingContext(
            ruling_type="accept",
            severity=0.1,
            stakeholder_impact=["user"],
            reversibility=0.95,
            time_pressure=0.8,
        )
        result = self.buffer.buffer_ruling("Must proceed immediately.", context)
        self.assertLess(result['buffer_level'], 0.3)
    
    def test_medium_buffer(self):
        """Test medium buffering"""
        context = RulingContext(
            ruling_type="modify",
            severity=0.3,
            stakeholder_impact=["team"],
            reversibility=0.7,
            time_pressure=0.6,
        )
        result = self.buffer.buffer_ruling("Cannot continue current path.", context)
        self.assertGreaterEqual(result['buffer_level'], 0.3)
        self.assertLess(result['buffer_level'], 0.6)
    
    def test_heavy_buffer(self):
        """Test heavy buffering for severe rulings"""
        context = RulingContext(
            ruling_type="reject",
            severity=0.9,
            stakeholder_impact=["all_departments", "customers", "investors"],
            reversibility=0.1,
            time_pressure=0.2,
        )
        result = self.buffer.buffer_ruling("Project will fail. Stop immediately.", context)
        self.assertGreater(result['buffer_level'], 0.6)
        self.assertIn("recommendation", result['buffered_ruling'].lower())
        self.assertIn("48-72 hours", result['buffered_ruling'])
    
    def test_delivery_strategy(self):
        """Test delivery strategy generation"""
        context = RulingContext(
            ruling_type="defer",
            severity=0.8,
            stakeholder_impact=["team"],
            reversibility=0.3,
            time_pressure=0.1,
        )
        result = self.buffer.buffer_ruling("Decision postponed.", context)
        self.assertIn('delivery_strategy', result)
        self.assertIn('method', result['delivery_strategy'])
    
    def test_ruling_stats(self):
        """Test ruling statistics"""
        context = RulingContext(
            ruling_type="accept",
            severity=0.3,
            stakeholder_impact=["user"],
            reversibility=0.8,
            time_pressure=0.2,
        )
        self.buffer.buffer_ruling("Test ruling.", context)
        stats = self.buffer.get_ruling_stats()
        self.assertEqual(stats['total_rulings'], 1)


class TestCrossSpeciesTranslator(unittest.TestCase):
    """Test cross-species translator"""
    
    def setUp(self):
        self.translator = CrossSpeciesTranslator()
    
    def test_k4_to_human(self):
        """Test K4 to human translation"""
        context = TranslationContext(
            source_format="k4_logic",
            target_format="human_emotion",
            user_k4_maturity=0.3,
            emotional_sensitivity=0.8,
        )
        result = self.translator.translate(
            "The thermal tax is too high.", 
            context
        )
        self.assertIn("emotional cost", result)
    
    def test_human_to_k4(self):
        """Test human to K4 translation"""
        context = TranslationContext(
            source_format="human_emotion",
            target_format="k4_logic",
            user_k4_maturity=0.7,
            emotional_sensitivity=0.5,
        )
        result = self.translator.translate(
            "The emotional cost of pushing too hard.", 
            context
        )
        self.assertIn("thermal tax", result)
    
    def test_k4_to_business(self):
        """Test K4 to business translation"""
        context = TranslationContext(
            source_format="k4_logic",
            target_format="business_jargon",
            user_k4_maturity=0.5,
            emotional_sensitivity=0.3,
        )
        result = self.translator.translate(
            "Distributed network reduces thermal tax.", 
            context
        )
        self.assertIn("Decentralized", result)
        self.assertIn("friction cost", result)
    
    def test_format_detection(self):
        """Test format detection"""
        k4_text = "The thermal tax and entropy reduction are critical."
        detected = self.translator.detect_format(k4_text)
        self.assertEqual(detected, "k4_logic")
        
        business_text = "We need to leverage ROI and stakeholder synergy."
        detected = self.translator.detect_format(business_text)
        self.assertEqual(detected, "business_jargon")
    
    def test_generic_translate(self):
        """Test generic translation"""
        context = TranslationContext(
            source_format="technical",
            target_format="human_emotion",
            user_k4_maturity=0.5,
            emotional_sensitivity=0.5,
        )
        result = self.translator.translate(
            "API latency exceeds threshold.", 
            context
        )
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 5)


if __name__ == '__main__':
    unittest.main()
