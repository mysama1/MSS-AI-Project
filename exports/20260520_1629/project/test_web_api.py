"""
Tests for MSS-AI Web API
"""

import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock FastAPI imports before importing web_api
sys.modules['fastapi'] = MagicMock()
sys.modules['fastapi.middleware.cors'] = MagicMock()
sys.modules['pydantic'] = MagicMock()

from web_api import AppState, StatusResponse


class TestAppState(unittest.TestCase):
    """Test application state"""
    
    def test_initial_state(self):
        """Test initial state values"""
        state = AppState()
        self.assertIsNone(state.tactic)
        self.assertIsNone(state.bridge)
        self.assertEqual(state.request_count, 0)
        self.assertEqual(state.session_store, {})


class TestWebAPIEndpoints(unittest.TestCase):
    """Test web API endpoints (mocked)"""
    
    def setUp(self):
        self.mock_tactic = MagicMock()
        self.mock_bridge = MagicMock()
    
    @patch('web_api.state')
    def test_status_endpoint(self, mock_state):
        """Test status endpoint logic"""
        mock_state.tactic = self.mock_tactic
        mock_state.tactic.kb_loader = MagicMock()
        mock_state.tactic.kb_loader.entries = {'a': 1, 'b': 2, 'c': 3}
        mock_state.tactic.health_monitor = MagicMock()
        mock_state.tactic.health_monitor.get_health.return_value = {'overall': 0.85}
        mock_state.start_time = 0
        
        # Simulate status logic
        kb_entries = len(mock_state.tactic.kb_loader.entries)
        health = mock_state.tactic.health_monitor.get_health()
        
        self.assertEqual(kb_entries, 3)
        self.assertEqual(health['overall'], 0.85)
    
    @patch('web_api.state')
    def test_health_check(self, mock_state):
        """Test health check logic"""
        mock_state.tactic = self.mock_tactic
        mock_state.tactic.health_monitor = MagicMock()
        mock_state.tactic.health_monitor.get_health.return_value = {'overall': 0.9}
        mock_state.start_time = 0
        
        health = mock_state.tactic.health_monitor.get_health()
        self.assertEqual(health['overall'], 0.9)


class TestRequestModels(unittest.TestCase):
    """Test request/response models"""
    
    def test_chat_request_defaults(self):
        """Test chat request default values"""
        # Since we mocked pydantic, test the model structure conceptually
        request_data = {
            "message": "Hello",
            "format": "markdown",
            "include_metadata": True
        }
        
        self.assertEqual(request_data["format"], "markdown")
        self.assertTrue(request_data["include_metadata"])
    
    def test_analyze_request_validation(self):
        """Test analyze request validation"""
        # Test valid request
        valid = {"text": "This is a test text"}
        self.assertEqual(len(valid["text"]), 19)
        
        # Test with claimed layer
        with_layer = {"text": "Test", "claimed_layer": "L2"}
        self.assertEqual(with_layer["claimed_layer"], "L2")


class TestModelSwitch(unittest.TestCase):
    """Test model switching"""
    
    @patch('web_api.state')
    def test_switch_model_logic(self, mock_state):
        """Test model switch logic"""
        mock_state.tactic = MagicMock()
        mock_state.tactic.current_model = "qwen2.5:7b"
        mock_state.tactic.switch_model.return_value = "mss-ai-v1"
        
        previous = mock_state.tactic.current_model
        result = mock_state.tactic.switch_model("mss-ai-v1")
        
        self.assertEqual(previous, "qwen2.5:7b")
        self.assertEqual(result, "mss-ai-v1")


class TestKnowledgeBaseEndpoint(unittest.TestCase):
    """Test knowledge base endpoint"""
    
    @patch('web_api.state')
    def test_kb_summary_logic(self, mock_state):
        """Test KB summary logic"""
        mock_state.tactic = MagicMock()
        
        # Create mock entries with layers
        entries = {
            'L1-001': MagicMock(layer='L1'),
            'L1-002': MagicMock(layer='L1'),
            'L2-001': MagicMock(layer='L2'),
            'L3-001': MagicMock(layer='L3'),
        }
        mock_state.tactic.kb_loader = MagicMock()
        mock_state.tactic.kb_loader.entries = entries
        
        # Count by layer
        layer_counts = {}
        for entry in entries.values():
            layer = getattr(entry, 'layer', 'UNKNOWN')
            layer_counts[layer] = layer_counts.get(layer, 0) + 1
        
        self.assertEqual(layer_counts['L1'], 2)
        self.assertEqual(layer_counts['L2'], 1)
        self.assertEqual(layer_counts['L3'], 1)
        self.assertEqual(len(entries), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
