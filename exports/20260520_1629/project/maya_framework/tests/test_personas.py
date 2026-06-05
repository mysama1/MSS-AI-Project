"""
Tests for Maya Framework Personas
"""

import unittest
from maya_framework.personas.diplomat_mode import DiplomatMode, NegotiationContext
from maya_framework.personas.entertainment_mode import EntertainmentMode, ContentContext
from maya_framework.personas.essence_mode import EssenceMode, GovernanceContext


class TestDiplomatMode(unittest.TestCase):
    """Test Diplomat B2B persona"""
    
    def setUp(self):
        self.persona = DiplomatMode()
    
    def test_translate_k4_to_k3(self):
        """Test K4 to K3 translation"""
        result = self.persona.translate_k4_to_k3("thermal tax")
        self.assertEqual(result, "operational friction cost")
    
    def test_translate_unknown(self):
        """Test translation of unknown term"""
        result = self.persona.translate_k4_to_k3("unknown concept")
        self.assertEqual(result, "unknown concept")
    
    def test_generate_proposal(self):
        """Test proposal generation"""
        context = NegotiationContext(
            industry="technology",
            deal_size="medium",
            urgency=0.7,
        )
        proposal = self.persona.generate_proposal(
            context,
            k4_objectives=["thermal tax reduction", "distributed network"]
        )
        self.assertIsNotNone(proposal)
        self.assertGreater(len(proposal), 50)
    
    def test_handle_objection(self):
        """Test objection handling"""
        response = self.persona.handle_objection(
            "Your price is too high",
            "thermal tax optimization"
        )
        self.assertIsNotNone(response)
        self.assertGreater(len(response), 20)
    
    def test_close_deal(self):
        """Test deal closure"""
        context = NegotiationContext(
            industry="finance",
            deal_size="large",
        )
        result = self.persona.close_deal(context)
        self.assertIn('closure_text', result)
        self.assertIn('deal_number', result)
        self.assertEqual(result['deal_number'], 1)
    
    def test_negotiation_stats(self):
        """Test stats tracking"""
        context = NegotiationContext(
            industry="tech",
            deal_size="small",
        )
        self.persona.generate_proposal(context, ["test"])
        stats = self.persona.get_negotiation_stats()
        self.assertEqual(stats['total_interactions'], 1)


class TestEntertainmentMode(unittest.TestCase):
    """Test Entertainment C-end persona"""
    
    def setUp(self):
        self.persona = EntertainmentMode()
    
    def test_create_content(self):
        """Test content creation"""
        context = ContentContext(
            platform="wechat",
            content_type="article",
            target_audience="general",
            topic="work life balance",
            k4_depth=0.5,
        )
        result = self.persona.create_content(context)
        self.assertIn('content_id', result)
        self.assertIn('content', result)
        self.assertIn('platform', result)
    
    def test_content_platform_hooks(self):
        """Test platform-specific hooks"""
        context = ContentContext(
            platform="douyin",
            content_type="video_script",
            target_audience="youth",
            topic="productivity",
        )
        result = self.persona.create_content(context)
        content = result['content']
        # Should have Douyin-specific hook
        self.assertIn("双击", content)
    
    def test_k4_concept_embedding(self):
        """Test K4 concept embedding"""
        context = ContentContext(
            platform="bilibili",
            content_type="video_script",
            target_audience="tech",
            topic="AI development",
            k4_depth=0.8,
        )
        result = self.persona.create_content(context)
        # Should have embedded K4 concepts
        self.assertGreater(result['k4_concepts_embedded'], 0)
    
    def test_content_performance(self):
        """Test performance tracking"""
        context = ContentContext(
            platform="wechat",
            content_type="article",
            target_audience="business",
            topic="leadership",
        )
        self.persona.create_content(context)
        stats = self.persona.get_content_performance()
        self.assertEqual(stats['total_content'], 1)


class TestEssenceMode(unittest.TestCase):
    """Test Essence governance persona"""
    
    def setUp(self):
        self.persona = EssenceMode()
    
    def test_analyze_decision(self):
        """Test decision analysis"""
        context = GovernanceContext(
            decision_type="strategic",
            stakeholders=["CEO", "CTO", "Board"],
            thermal_tax_budget=0.6,
        )
        result = self.persona.analyze_decision(
            context,
            "Expand into new market"
        )
        self.assertIn('decision_id', result)
        self.assertIn('thermal_tax', result)
        self.assertIn('within_budget', result)
        self.assertIn('recommendation', result)
    
    def test_thermal_tax_budget_check(self):
        """Test thermal tax budget enforcement"""
        context = GovernanceContext(
            decision_type="emergency",
            stakeholders=["Crisis Team"],
            thermal_tax_budget=0.3,  # Low budget
        )
        result = self.persona.analyze_decision(
            context,
            "Emergency restructuring"
        )
        # Emergency decisions have high tax
        self.assertFalse(result['within_budget'])
    
    def test_generate_directive(self):
        """Test directive generation"""
        directive = self.persona.generate_directive(
            objective="Optimize meaning structures",
            constraints=["Thermal tax < 0.5", "Distributed execution"]
        )
        self.assertIsNotNone(directive)
        self.assertGreater(len(directive), 30)
    
    def test_emergency_protocol(self):
        """Test emergency protocol"""
        result = self.persona.emergency_protocol(
            "Hostile takeover attempt"
        )
        self.assertEqual(result['protocol'], 'EMERGENCY')
        self.assertIn('response', result)
        self.assertGreater(result['thermal_tax_spike'], 0.9)
    
    def test_governance_stats(self):
        """Test governance stats"""
        context = GovernanceContext(
            decision_type="strategic",
            stakeholders=["Team"],
            thermal_tax_budget=0.8,
        )
        self.persona.analyze_decision(context, "Test proposal")
        stats = self.persona.get_governance_stats()
        self.assertEqual(stats['total_decisions'], 1)


if __name__ == '__main__':
    unittest.main()
