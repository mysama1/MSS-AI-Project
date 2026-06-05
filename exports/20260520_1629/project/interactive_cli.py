"""
MSS-AI Interactive CLI
Command-line interface for MSS-AI system interaction
"""

import sys
import os
import json
import time
from typing import Optional, List, Dict
from enum import Enum

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mss_tactic_integrated import MSSTactic
from nl_bridge_v2 import NLBridgeV2, ResponseFormat


class CLITheme:
    """Terminal color theme"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    
    @classmethod
    def disable(cls):
        """Disable colors for non-supporting terminals"""
        cls.HEADER = ''
        cls.BLUE = ''
        cls.CYAN = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.RED = ''
        cls.ENDC = ''
        cls.BOLD = ''


class CommandType(Enum):
    """Supported CLI commands"""
    CHAT = "/chat"
    ANALYZE = "/analyze"
    REASON = "/reason"
    SCAN = "/scan"
    STATUS = "/status"
    HELP = "/help"
    QUIT = "/quit"
    MODEL = "/model"
    TEST = "/test"


class MSSInteractiveCLI:
    """
    Interactive command-line interface for MSS-AI
    
    Features:
    - Natural language chat with MSS-AI
    - Symbolic reasoning commands
    - System status monitoring
    - Organizational resilience scanning
    - Multi-turn dialogue context
    """
    
    def __init__(self):
        self.theme = CLITheme()
        self.tactic: Optional[MSSTactic] = None
        self.bridge: Optional[NLBridgeV2] = None
        self.session_start = time.time()
        self.command_count = 0
        self.message_count = 0
        
    def initialize(self) -> bool:
        """Initialize MSS-AI system"""
        print(f"{self.theme.HEADER}{self.theme.BOLD}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║           MSS-AI Interactive CLI v1.0                        ║")
        print("║     Meta-Self-Similarity System - Command Interface          ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(f"{self.theme.ENDC}")
        
        print(f"{self.theme.CYAN}Initializing system components...{self.theme.ENDC}")
        
        try:
            # Initialize main tactic engine
            self.tactic = MSSTactic()
            print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Tactic engine loaded")
            
            # Initialize NL bridge
            self.bridge = NLBridgeV2()
            print(f"  {self.theme.GREEN}✓{self.theme.ENDC} NL Bridge V2 loaded")
            
            # Run system check
            print(f"\n{self.theme.CYAN}Running system diagnostics...{self.theme.ENDC}")
            self._run_diagnostics()
            
            print(f"\n{self.theme.GREEN}{self.theme.BOLD}System ready!{self.theme.ENDC}")
            self._print_help()
            
            return True
            
        except Exception as e:
            print(f"{self.theme.RED}Initialization failed: {e}{self.theme.ENDC}")
            return False
    
    def _run_diagnostics(self):
        """Run quick system diagnostics"""
        try:
            # Check symbolic engine
            if hasattr(self.tactic, '_ensure_symbolic_engine_v3'):
                self.tactic._ensure_symbolic_engine_v3()
                print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Symbolic engine v3 active")
            
            # Check health monitor
            if hasattr(self.tactic, 'health_monitor') and self.tactic.health_monitor:
                health = self.tactic.health_monitor.get_health()
                status = "healthy" if health.get('overall', 0) > 0.7 else "degraded"
                print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Health monitor: {status}")
            
            # Check knowledge base
            if hasattr(self.tactic, 'kb_loader') and self.tactic.kb_loader:
                count = len(self.tactic.kb_loader.entries)
                print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Knowledge base: {count} entries")
            
        except Exception as e:
            print(f"  {self.theme.YELLOW}!{self.theme.ENDC} Diagnostic warning: {e}")
    
    def run(self):
        """Main CLI loop"""
        if not self.initialize():
            return
        
        print(f"\n{self.theme.CYAN}Enter commands (type /help for help, /quit to exit):{self.theme.ENDC}\n")
        
        while True:
            try:
                # Get user input
                user_input = input(f"{self.theme.BOLD}MSS>{self.theme.ENDC} ").strip()
                
                if not user_input:
                    continue
                
                self.command_count += 1
                
                # Parse command
                if user_input.startswith('/'):
                    parts = user_input.split(' ', 1)
                    command = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""
                    
                    if command == CommandType.QUIT.value:
                        self._handle_quit()
                        break
                    elif command == CommandType.HELP.value:
                        self._print_help()
                    elif command == CommandType.STATUS.value:
                        self._handle_status()
                    elif command == CommandType.CHAT.value:
                        self._handle_chat(args)
                    elif command == CommandType.ANALYZE.value:
                        self._handle_analyze(args)
                    elif command == CommandType.REASON.value:
                        self._handle_reason(args)
                    elif command == CommandType.SCAN.value:
                        self._handle_scan(args)
                    elif command == CommandType.MODEL.value:
                        self._handle_model(args)
                    elif command == CommandType.TEST.value:
                        self._handle_test()
                    else:
                        print(f"{self.theme.YELLOW}Unknown command: {command}{self.theme.ENDC}")
                        print(f"Type {self.theme.CYAN}/help{self.theme.ENDC} for available commands")
                else:
                    # Default to chat mode
                    self._handle_chat(user_input)
                    
            except KeyboardInterrupt:
                print(f"\n{self.theme.YELLOW}Interrupted. Type /quit to exit.{self.theme.ENDC}")
            except EOFError:
                break
            except Exception as e:
                print(f"{self.theme.RED}Error: {e}{self.theme.ENDC}")
    
    def _handle_chat(self, message: str):
        """Handle chat message"""
        if not message:
            print(f"{self.theme.YELLOW}Please provide a message{self.theme.ENDC}")
            return
        
        print(f"{self.theme.CYAN}Processing...{self.theme.ENDC}")
        start_time = time.time()
        
        try:
            # Use NL Bridge for intent recognition
            if self.bridge:
                result = self.bridge.execute_v2(message, format=ResponseFormat.MARKDOWN)
                
                print(f"\n{self.theme.GREEN}{self.theme.BOLD}MSS-AI:{self.theme.ENDC}")
                print(result.get('response', 'No response generated'))
                
                # Show metadata
                elapsed = time.time() - start_time
                print(f"\n{self.theme.CYAN}[{elapsed:.2f}s | Intent: {result.get('intent', 'unknown')} | Confidence: {result.get('confidence', 0):.2f}]{self.theme.ENDC}")
            else:
                # Fallback to direct tactic
                result = self.tactic.generate(message)
                print(f"\n{self.theme.GREEN}{self.theme.BOLD}MSS-AI:{self.theme.ENDC}")
                print(result)
                
        except Exception as e:
            print(f"{self.theme.RED}Chat error: {e}{self.theme.ENDC}")
    
    def _handle_analyze(self, text: str):
        """Handle text analysis"""
        if not text:
            print(f"{self.theme.YELLOW}Usage: /analyze <text to analyze>{self.theme.ENDC}")
            return
        
        print(f"{self.theme.CYAN}Analyzing text...{self.theme.ENDC}")
        
        try:
            if hasattr(self.tactic, 'analyze'):
                result = self.tactic.analyze(text)
                
                print(f"\n{self.theme.GREEN}{self.theme.BOLD}Analysis Results:{self.theme.ENDC}")
                print(f"  Layer: {result.get('layer', 'UNKNOWN')}")
                print(f"  Confidence: {result.get('confidence', 0):.2f}")
                print(f"  RSCA Check: {'PASS' if result.get('rsca') else 'FAIL'}")
                
                if 'forbidden_words' in result:
                    print(f"  Forbidden Words: {', '.join(result['forbidden_words'])}")
            else:
                print(f"{self.theme.YELLOW}Analyzer not available{self.theme.ENDC}")
                
        except Exception as e:
            print(f"{self.theme.RED}Analysis error: {e}{self.theme.ENDC}")
    
    def _handle_reason(self, query: str):
        """Handle symbolic reasoning"""
        if not query:
            print(f"{self.theme.YELLOW}Usage: /reason <query>{self.theme.ENDC}")
            print(f"Example: /reason A1 implies T1")
            return
        
        print(f"{self.theme.CYAN}Running symbolic reasoning...{self.theme.ENDC}")
        
        try:
            if hasattr(self.tactic, 'symbolic_reason'):
                result = self.tactic.symbolic_reason(query)
                
                print(f"\n{self.theme.GREEN}{self.theme.BOLD}Reasoning Result:{self.theme.ENDC}")
                print(f"  Status: {result.get('status', 'UNKNOWN')}")
                print(f"  Path Length: {result.get('path_length', 0)}")
                
                if 'steps' in result:
                    print(f"\n  Reasoning Path:")
                    for i, step in enumerate(result['steps'], 1):
                        print(f"    {i}. {step}")
            else:
                print(f"{self.theme.YELLOW}Symbolic reasoner not available{self.theme.ENDC}")
                
        except Exception as e:
            print(f"{self.theme.RED}Reasoning error: {e}{self.theme.ENDC}")
    
    def _handle_scan(self, target: str):
        """Handle organizational scan"""
        print(f"{self.theme.CYAN}Running organizational resilience scan...{self.theme.ENDC}")
        
        try:
            if hasattr(self.tactic, 'organizational_resilience_scan'):
                result = self.tactic.organizational_resilience_scan()
                
                print(f"\n{self.theme.GREEN}{self.theme.BOLD}Resilience Scan Results:{self.theme.ENDC}")
                print(f"  Overall Level: {result.get('level', 'UNKNOWN')}")
                print(f"  Phi Score: {result.get('phi', 0):.3f}")
                print(f"  Departments: {result.get('departments', 0)}")
                
                if 'diagnoses' in result:
                    print(f"\n  Diagnoses:")
                    for diag in result['diagnoses']:
                        print(f"    - {diag}")
                        
                if 'recommendations' in result:
                    print(f"\n  Recommendations:")
                    for rec in result['recommendations']:
                        print(f"    - {rec}")
            else:
                print(f"{self.theme.YELLOW}Resilience scanner not available{self.theme.ENDC}")
                
        except Exception as e:
            print(f"{self.theme.RED}Scan error: {e}{self.theme.ENDC}")
    
    def _handle_status(self):
        """Handle status command"""
        print(f"\n{self.theme.GREEN}{self.theme.BOLD}System Status:{self.theme.ENDC}")
        
        uptime = time.time() - self.session_start
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        print(f"  Session Uptime: {hours}h {minutes}m")
        print(f"  Commands Processed: {self.command_count}")
        print(f"  Messages Exchanged: {self.message_count}")
        
        if self.tactic:
            print(f"  Tactic Engine: Active")
            if hasattr(self.tactic, 'health_monitor') and self.tactic.health_monitor:
                health = self.tactic.health_monitor.get_health()
                print(f"  System Health: {health.get('overall', 0):.2f}")
        
        if self.bridge:
            print(f"  NL Bridge: Active (V2)")
    
    def _handle_model(self, args: str):
        """Handle model switching"""
        if not args:
            print(f"{self.theme.YELLOW}Usage: /model <model_name>{self.theme.ENDC}")
            print(f"Available: qwen2.5:7b, mss-ai-v1")
            return
        
        print(f"{self.theme.CYAN}Switching model to {args}...{self.theme.ENDC}")
        
        try:
            if hasattr(self.tactic, 'switch_model'):
                result = self.tactic.switch_model(args)
                print(f"{self.theme.GREEN}Model switched: {result}{self.theme.ENDC}")
            else:
                print(f"{self.theme.YELLOW}Model manager not available{self.theme.ENDC}")
                
        except Exception as e:
            print(f"{self.theme.RED}Model switch error: {e}{self.theme.ENDC}")
    
    def _handle_test(self):
        """Run quick system test"""
        print(f"{self.theme.CYAN}Running system test...{self.theme.ENDC}")
        
        tests_passed = 0
        tests_total = 5
        
        # Test 1: Tactic engine
        try:
            assert self.tactic is not None
            print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Tactic engine")
            tests_passed += 1
        except:
            print(f"  {self.theme.RED}✗{self.theme.ENDC} Tactic engine")
        
        # Test 2: NL Bridge
        try:
            assert self.bridge is not None
            print(f"  {self.theme.GREEN}✓{self.theme.ENDC} NL Bridge")
            tests_passed += 1
        except:
            print(f"  {self.theme.RED}✗{self.theme.ENDC} NL Bridge")
        
        # Test 3: Symbolic engine
        try:
            if hasattr(self.tactic, '_ensure_symbolic_engine_v3'):
                self.tactic._ensure_symbolic_engine_v3()
                print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Symbolic engine")
                tests_passed += 1
            else:
                print(f"  {self.theme.YELLOW}!{self.theme.ENDC} Symbolic engine (lazy init)")
        except Exception as e:
            print(f"  {self.theme.RED}✗{self.theme.ENDC} Symbolic engine: {e}")
        
        # Test 4: Health monitor
        try:
            if hasattr(self.tactic, 'health_monitor') and self.tactic.health_monitor:
                print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Health monitor")
                tests_passed += 1
            else:
                print(f"  {self.theme.YELLOW}!{self.theme.ENDC} Health monitor")
        except:
            print(f"  {self.theme.RED}✗{self.theme.ENDC} Health monitor")
        
        # Test 5: Knowledge base
        try:
            if hasattr(self.tactic, 'kb_loader') and self.tactic.kb_loader:
                count = len(self.tactic.kb_loader.entries)
                print(f"  {self.theme.GREEN}✓{self.theme.ENDC} Knowledge base ({count} entries)")
                tests_passed += 1
            else:
                print(f"  {self.theme.YELLOW}!{self.theme.ENDC} Knowledge base")
        except:
            print(f"  {self.theme.RED}✗{self.theme.ENDC} Knowledge base")
        
        print(f"\n{self.theme.BOLD}Test Results: {tests_passed}/{tests_total} passed{self.theme.ENDC}")
    
    def _handle_quit(self):
        """Handle quit command"""
        print(f"\n{self.theme.GREEN}Thank you for using MSS-AI. Goodbye!{self.theme.ENDC}")
        
        # Save session stats
        uptime = time.time() - self.session_start
        print(f"Session duration: {uptime:.1f}s")
        print(f"Total commands: {self.command_count}")
    
    def _print_help(self):
        """Print help message"""
        print(f"\n{self.theme.BOLD}Available Commands:{self.theme.ENDC}")
        print(f"  {self.theme.CYAN}/chat <message>{self.theme.ENDC}     - Send message to MSS-AI (default)")
        print(f"  {self.theme.CYAN}/analyze <text>{self.theme.ENDC}   - Analyze text layer and compliance")
        print(f"  {self.theme.CYAN}/reason <query>{self.theme.ENDC}    - Symbolic reasoning (e.g., 'A1 implies T1')")
        print(f"  {self.theme.CYAN}/scan{self.theme.ENDC}              - Run organizational resilience scan")
        print(f"  {self.theme.CYAN}/status{self.theme.ENDC}           - Show system status")
        print(f"  {self.theme.CYAN}/model <name>{self.theme.ENDC}      - Switch AI model")
        print(f"  {self.theme.CYAN}/test{self.theme.ENDC}              - Run system diagnostics")
        print(f"  {self.theme.CYAN}/help{self.theme.ENDC}              - Show this help")
        print(f"  {self.theme.CYAN}/quit{self.theme.ENDC}              - Exit CLI")
        print(f"\n{self.theme.BOLD}Tips:{self.theme.ENDC}")
        print(f"  - Type any text without '/' to chat directly")
        print(f"  - Use quotes for multi-word arguments")
        print(f"  - Press Ctrl+C to interrupt long operations")
        print()


def main():
    """CLI entry point"""
    # Check for --no-color flag
    if '--no-color' in sys.argv:
        CLITheme.disable()
    
    cli = MSSInteractiveCLI()
    cli.run()


if __name__ == "__main__":
    main()
