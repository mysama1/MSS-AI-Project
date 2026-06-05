"""
Tests for MSS-AI Interactive CLI
"""

import unittest
import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interactive_cli import MSSInteractiveCLI, CLITheme, CommandType

class TestCLITheme(unittest.TestCase):
    """Test CLI theme colors"""

    def test_colors_enabled_by_default(self):
        """Test colors are enabled by default"""
        theme = CLITheme()
        self.assertEqual(theme.GREEN, '\033[92m')
        self.assertEqual(theme.RED, '\033[91m')

    def test_disable_colors(self):
        """Test color disabling"""
        CLITheme.disable()
        self.assertEqual(CLITheme.GREEN, '')
        self.assertEqual(CLITheme.RED, '')
        # Reset for other tests
        CLITheme.HEADER = '\033[95m'
        CLITheme.GREEN = '\033[92m'
        CLITheme.RED = '\033[91m'

class TestCLIInitialization(unittest.TestCase):
    """Test CLI initialization"""

    def setUp(self):
        self.cli = MSSInteractiveCLI()

    @patch('interactive_cli.MSSTactic')
    @patch('interactive_cli.NLBridgeV2')
    def test_initialize_success(self, mock_bridge, mock_tactic):
        """Test successful initialization"""
        mock_tactic_instance = MagicMock()
        mock_tactic.return_value = mock_tactic_instance
        mock_tactic_instance.health_monitor = None
        mock_tactic_instance.kb_loader = None

        mock_bridge_instance = MagicMock()
        mock_bridge.return_value = mock_bridge_instance

        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = self.cli.initialize()

        self.assertTrue(result)
        self.assertIsNotNone(self.cli.tactic)
        self.assertIsNotNone(self.cli.bridge)

    @patch('interactive_cli.MSSTactic')
    def test_initialize_failure(self, mock_tactic):
        """Test initialization failure"""
        mock_tactic.side_effect = Exception("Init failed")

        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = self.cli.initialize()

        self.assertFalse(result)

class TestCLICommands(unittest.TestCase):
    """Test CLI command handlers"""

    def setUp(self):
        self.cli = MSSInteractiveCLI()
        self.cli.tactic = MagicMock()
        self.cli.bridge = MagicMock()
        self.cli.theme = CLITheme()

    def test_handle_status(self):
        """Test status command"""
        self.cli.tactic.health_monitor = MagicMock()
        self.cli.tactic.health_monitor.get_health.return_value = {'overall': 0.85}
        self.cli.tactic.kb_loader = MagicMock()
        self.cli.tactic.kb_loader.entries = {'a': 1, 'b': 2}

        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.cli._handle_status()
            output = fake_out.getvalue()

        self.assertIn("System Status", output)
        self.assertIn("0.85", output)
        self.assertIn("2", output)

    def test_handle_test(self):
        """Test test command"""
        self.cli.tactic = MagicMock()
        self.cli.bridge = MagicMock()

        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.cli._handle_test()
            output = fake_out.getvalue()

        self.assertIn("Test Results", output)

    def test_handle_quit(self):
        """Test quit command"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.cli._handle_quit()
            output = fake_out.getvalue()

        self.assertIn("Thank you", output)

    def test_print_help(self):
        """Test help display"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.cli._print_help()
            output = fake_out.getvalue()

        self.assertIn("Available Commands", output)
        self.assertIn("/chat", output)
        self.assertIn("/quit", output)

class TestCommandType(unittest.TestCase):
    """Test command type enum"""

    def test_command_values(self):
        """Test command enum values"""
        self.assertEqual(CommandType.CHAT.value, "/chat")
        self.assertEqual(CommandType.ANALYZE.value, "/analyze")
        self.assertEqual(CommandType.QUIT.value, "/quit")

class TestCLIMainLoop(unittest.TestCase):
    """Test main CLI loop"""

    @patch('interactive_cli.MSSTactic')
    @patch('interactive_cli.NLBridgeV2')
    @patch('builtins.input', side_effect=['/test', '/quit'])
    def test_main_loop(self, mock_input, mock_bridge, mock_tactic):
        """Test main loop with test and quit commands"""
        mock_tactic_instance = MagicMock()
        mock_tactic.return_value = mock_tactic_instance
        mock_tactic_instance.health_monitor = None
        mock_tactic_instance.kb_loader = None

        mock_bridge_instance = MagicMock()
        mock_bridge.return_value = mock_bridge_instance

        cli = MSSInteractiveCLI()

        with patch('sys.stdout', new=StringIO()):
            cli.run()

        self.assertEqual(cli.command_count, 2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
