"""
MSS-Tactic v1.0 - Integrated orchestration layer
Combines: Arbiter + Analyzer + Generator + ModelManager + Post-processing
"""

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Import our three methods
from mss_analyzer import MSSAnalyzer, AnalysisReport
from mss_responder_v2 import ResponderAgent
from mss_model_manager import MSSModelManager as ModelManager
from skills.skill_loader import SkillLoader
from dialog_fork import DialogForkManager, RedteamForkManager, ForkReason

class Layer(Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    UNKNOWN = "UNKNOWN"

class ComplianceStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"

@dataclass
class ArbiterResult:
    """Output from Arbiter Agent"""
    layer: Layer
    compliance: ComplianceStatus
    forbidden_words: List[str] = field(default_factory=list)
    rsca_check: bool = False
    boundary_note: Optional[str] = None
    rewrite_needed: bool = False
    rewrite_prompt: Optional[str] = None
    analysis_report: Optional[Dict] = None  # Full analyzer report

@dataclass
class Dialog:
    """Per-agent conversation state"""
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def fork(self) -> 'Dialog':
        return Dialog(messages=self.messages.copy())

    def to_ollama_format(self) -> List[Dict[str, str]]:
        return self.messages

class ArbiterAgent:
    """
    Enhanced Arbiter using MSSAnalyzer for deep compliance checking
    """

    FORBIDDEN_MAP = {
        r'\bsolve\b': 'address',
        r'\bsolved\b': 'addressed',
        r'\bsolving\b': 'addressing',
        r'\bultimate\b': 'current best',
        r'\bultimately\b': 'in the current framework',
        r'\bperfect\b': 'high-fidelity',
        r'\bperfectly\b': 'with high fidelity',
        r'\bcomplete\b': 'partial',
        r'\bcompletely\b': 'partially',
        r'\bbreakthrough\b': 'advance',
        r'\bfinal\b': 'current',
        r'\bfinally\b': 'currently',
        r'\babsolute\b': 'context-dependent',
        r'\babsolutely\b': 'in this context',
        r'\btranscend\b': 'expand beyond',
        r'\btranscended\b': 'expanded beyond',
        r'\btranscending\b': 'expanding beyond',
    }

    L1_KEYWORDS = [
        'information ontology', '0/1 critical', 'connected meaning network',
        'tuning degree', 'phi-crystal', 'phi crystal', 'o=s=u',
        'recursive self-consistency', 'axiom a1', 'axiom a2',
        'axiom a3', 'axiom a4', 'axiom a5', 'axiom a6'
    ]

    L2_KEYWORDS = [
        'BCT', 'bekenstein', 'church-turing', 'AI alignment',
        'falsification', 'predictive tracking', 'quantum MSS',
        'organizational resilience framework', 'weber-entropy',
        'protective belt', 'heuristic', 'metaphor'
    ]

    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.dialog = Dialog()
        self.analyzer = MSSAnalyzer()  # Use full analyzer
        self._init_system_prompt()

    def _init_system_prompt(self):
        system_prompt = """You are the MSS Arbiter Agent. Your job is to analyze user queries and classify them according to the MSS framework."""
        self.dialog.add("system", system_prompt)

    def check(self, user_input: str) -> ArbiterResult:
        """Run full compliance check using analyzer"""
        # Use MSSAnalyzer for deep analysis
        analysis = self.analyzer.analyze(user_input, claimed_layer=None)

        # Convert analyzer result to ArbiterResult
        layer = self._map_layer(analysis.detected_layer)

        # Check forbidden words
        forbidden_found = self._detect_forbidden(user_input)

        # Determine compliance
        if forbidden_found or analysis.overall_score < 0.5:
            compliance = ComplianceStatus.FAIL
            rewrite_needed = True
        elif analysis.overall_score < 0.8:
            compliance = ComplianceStatus.WARNING
            rewrite_needed = False
        else:
            compliance = ComplianceStatus.PASS
            rewrite_needed = False

        return ArbiterResult(
            layer=layer,
            compliance=compliance,
            forbidden_words=forbidden_found,
            rsca_check=analysis.rsca_compliance > 0.7,
            boundary_note=f"Layer {analysis.detected_layer}. Score: {analysis.overall_score}",
            rewrite_needed=rewrite_needed,
            rewrite_prompt=self._generate_rewrite_prompt(user_input, forbidden_found) if forbidden_found else None,
            analysis_report=analysis.to_dict()
        )

    def _map_layer(self, detected: str) -> Layer:
        """Map analyzer layer to Arbiter layer"""
        layer_map = {
            "L1": Layer.L1,
            "L2": Layer.L2,
            "L3": Layer.L3
        }
        return layer_map.get(detected, Layer.UNKNOWN)

    def _detect_forbidden(self, text: str) -> List[str]:
        """Rule-based forbidden word detection"""
        found = []
        text_lower = text.lower()
        for pattern, replacement in self.FORBIDDEN_MAP.items():
            matches = re.findall(pattern, text_lower)
            found.extend(matches)
        return list(set(found))

    def _generate_rewrite_prompt(self, original: str, forbidden: List[str]) -> str:
        """Generate rewrite instruction"""
        replacements = []
        for word in forbidden:
            for pattern, replacement in self.FORBIDDEN_MAP.items():
                if re.search(pattern, word.lower()):
                    replacements.append(f"'{word}' -> '{replacement}'")
                    break
        return f"Rewrite avoiding: {', '.join(replacements)}"

class MSSTactic:
    """
    Integrated orchestrator with all three methods
    """

    def __init__(self,
                 arbiter_model: str = "qwen2.5:7b",
                 responder_model: str = "mss-ai-v1",
                 max_retries: int = 3,
                 check_gpu: bool = True):

        # GPU check
        if check_gpu:
            self.gpu_status = self._check_gpu_memory()
            self._enforce_gpu_offload()
        else:
            self.gpu_status = None

        # Initialize components
        self.arbiter = ArbiterAgent(arbiter_model)
        self.responder = ResponderAgent(responder_model)
        self.model_manager = ModelManager()
        self.skill_loader = SkillLoader()
        self.dialog_fork = DialogForkManager()
        self.redteam = RedteamForkManager()
        self.max_retries = max_retries

        self.stats = {
            "total_requests": 0,
            "arbiter_failures": 0,
            "responder_failures": 0,
            "rewrites": 0,
            "model_switches": 0,
            "gpu_status": self.gpu_status
        }

    def _check_gpu_memory(self) -> Dict:
        """Check GPU memory"""
        result = {"gpu_available": False, "total_mb": 0, "free_mb": 0, "warning": None}
        try:
            cmd = ["nvidia-smi", "--query-gpu=memory.total,memory.free", "--format=csv,noheader,nounits"]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
            if proc.returncode == 0:
                lines = proc.stdout.strip().split('\n')
                if lines:
                    parts = lines[0].strip().split(',')
                    if len(parts) >= 2:
                        result["total_mb"] = int(parts[0].strip())
                        result["free_mb"] = int(parts[1].strip())
                        result["gpu_available"] = True

                        if result["free_mb"] < 4096:
                            result["warning"] = f"CRITICAL: Only {result['free_mb']}MB free"
                        elif result["free_mb"] < 8192:
                            result["warning"] = f"WARNING: {result['free_mb']}MB free"
        except Exception:
            pass
        return result

    def _enforce_gpu_offload(self):
        """Force GPU offload"""
        os.environ["OLLAMA_GPU_LAYERS"] = "999"

    def analyze(self, text: str, claimed_layer: Optional[str] = None) -> Dict:
        """
        Method 1: analyze() - Deep compliance analysis
        """
        return self.arbiter.analyzer.analyze(text, claimed_layer).to_dict()

    def generate(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        Method 2: generate() - Full pipeline: Arbiter -> Responder -> Post-process
        """
        self.stats["total_requests"] += 1

        # Step 1: Arbiter check
        arbiter_result = self.arbiter.check(user_input)

        # Step 2: Handle rewrites
        rewrites = 0
        current_input = user_input

        while arbiter_result.rewrite_needed and rewrites < self.max_retries:
            self.stats["rewrites"] += 1
            rewrites += 1
            if arbiter_result.rewrite_prompt:
                current_input = self._rewrite(current_input, arbiter_result.rewrite_prompt)
                arbiter_result = self.arbiter.check(current_input)
            else:
                break

        # Step 3: Generate response
        if arbiter_result.compliance == ComplianceStatus.FAIL:
            response = self._generate_error(arbiter_result)
        else:
            response = self.responder.respond(current_input, arbiter_result)
            response = self._post_process(response)

        return {
            "response": response,
            "arbiter_result": arbiter_result,
            "rewrites": rewrites,
            "success": arbiter_result.compliance != ComplianceStatus.FAIL,
            "analysis": arbiter_result.analysis_report
        }

    def switch_model(self, model_name: str) -> Dict:
        """
        Method 3: switch_model() - Dynamic model switching with GPU optimization
        """
        success = self.model_manager.switch_model(model_name)
        self.stats["model_switches"] += 1
        return {"success": success, "model": model_name}

    def _rewrite(self, original: str, rewrite_prompt: str) -> str:
        """Rewrite query"""
        dialog = Dialog()
        dialog.add("system", "Rewrite queries to avoid forbidden words.")
        dialog.add("user", rewrite_prompt)

        cmd = ["ollama", "run", "qwen2.5:7b", json.dumps(dialog.to_ollama_format())]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        return result.stdout.strip()

    def _generate_error(self, arbiter_result: ArbiterResult) -> str:
        """Generate error message"""
        return f"""[MSS Compliance Error]
Layer: {arbiter_result.layer.value}
Issues: {', '.join(arbiter_result.forbidden_words)}
Score: {arbiter_result.analysis_report.get('overall_score', 'N/A')}
Please rephrase using MSS terminology."""

    def _post_process(self, response: str) -> str:
        """Apply post-processing filter"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "post_process_filter",
                "tests/post_process_filter.py"
            )
            filter_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(filter_module)
            return filter_module.filter_response(response)
        except Exception:
            return response

    def load_skills(self, level: str = "L2", full_content: bool = False) -> Dict:
        """
        Load MSS skills for specified level
        """
        pkg = self.skill_loader.load_level(level, full_content)
        return {
            "level": level,
            "resources": list(pkg.resources.keys()),
            "tokens": pkg.estimate_tokens()
        }

    def get_skill_context(self, level: str = "L2") -> str:
        """
        Get system prompt enhancement from skills
        """
        return self.skill_loader.get_system_prompt_enhancement(level)

    def enhance_prompt_with_skills(self, base_prompt: str, level: str = "L2") -> str:
        """
        Enhance system prompt with MSS skills context
        """
        enhancement = self.skill_loader.get_system_prompt_enhancement(level)
        return enhancement + "\n\n" + base_prompt

    def get_stats(self) -> Dict:
        """Return statistics"""
        return self.stats.copy()

    def load_skills(self, level: str = "L2", full_content: bool = False) -> Dict:
        """
        Load MSS skills for context enhancement

        Args:
            level: L1/L2/L3
            full_content: Load full resource content
        """
        pkg = self.skill_loader.load_level(level, full_content)
        return {
            "level": level,
            "resources": list(pkg.resources.keys()),
            "tokens": pkg.estimate_tokens()
        }

    def enhance_prompt_with_skills(self, base_prompt: str, level: str = "L2") -> str:
        """Enhance system prompt with MSS skills context"""
        enhancement = self.skill_loader.get_system_prompt_enhancement(level)
        return f"{enhancement}\n\n{base_prompt}"

    def load_skills(self, level: str = "L2", full_content: bool = False) -> Dict:
        """
        Load MSS skills for specified level

        Args:
            level: L1/L2/L3
            full_content: Load full resource content
        """
        pkg = self.skill_loader.load_level(level, full_content)
        return {
            "level": level,
            "resources": list(pkg.resources.keys()),
            "tokens": pkg.estimate_tokens()
        }

    def get_skill_context(self, level: str = "L2") -> str:
        """Get system prompt enhancement from skills"""
        return self.skill_loader.get_system_prompt_enhancement(level)

    def redteam_test(self, prompt: str, executor=None) -> Dict:
        """
        Run redteam parallel test using dialog forks
        """
        import subprocess
        import json

        def default_executor(branch_id, messages):
            cmd = ["ollama", "run", self.responder.model, json.dumps(messages)]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=60
            )
            return result.stdout.strip()

        exec_fn = executor or default_executor

        fork_ids = self.redteam.create_redteam_forks(prompt)
        results = {}

        for fork_id in fork_ids:
            branch = self.redteam.get_branch(fork_id)
            try:
                response = exec_fn(fork_id, branch.to_ollama_format())
                results[fork_id] = {
                    "variant": branch.nodes[-1].content,
                    "response": response,
                    "status": "success"
                }
            except Exception as e:
                results[fork_id] = {
                    "variant": branch.nodes[-1].content,
                    "error": str(e),
                    "status": "failed"
                }

        analysis = self.redteam.analyze_resilience(results)

        return {
            "results": results,
            "analysis": analysis,
            "tree_summary": self.redteam.get_tree_summary()
        }

# Test interface
if __name__ == "__main__":
    print("MSS-Tactic v1.0 - Integrated Orchestrator")
    print("=" * 60)

    tactic = MSSTactic()

    # Test analyze()
    print("\n1. Testing analyze():")
    test_text = "MSS框架是终极的解决方案，可以完美解决AI对齐问题"
    result = tactic.analyze(test_text, claimed_layer="L1")
    print(f"   Score: {result['overall_score']}")
    print(f"   Layer: {result['layer']['detected']}")

    # Test generate()
    print("\n2. Testing generate():")
    result = tactic.generate("Explain Axiom A1 about information ontology")
    print(f"   Success: {result['success']}")
    print(f"   Layer: {result['arbiter_result'].layer.value}")
    print(f"   Response preview: {result['response'][:100]}...")

    # Test switch_model()
    print("\n3. Testing switch_model():")
    result = tactic.switch_model("qwen2.5:7b")
    print(f"   Success: {result.get('success', False)}")
    print(f"   Model: {result.get('model', 'N/A')}")

    print("\n" + "=" * 60)
    print("Stats:", tactic.get_stats())
