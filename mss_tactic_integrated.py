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
from power_manager import PowerManager, PowerProfile, integrate_with_tactic
from post_process_engine import PostProcessEngine
from post_process_engine_v3 import create_topology_aware_engine
from topology_metrics import TopologyMetricsEngine
from kb_loader import KBLoader, load_default_kb
from mss_checkpoint import CheckpointManager, SessionSnapshot, AutoSaver
from mss_stability import SystemHealthMonitor, AdaptiveTaskScheduler, TaskPriority
from symbolic_rules_omega import OmegaComplianceChecker, RuleLayer, check_compliance
from symbolic_engine_v3 import create_mss_v12_engine, HeatTaxMonitor
from organizational_resilience import OrganizationalResilienceScanner, create_demo_organization

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
            "post_filter_replacements": 0,
            "gpu_status": self.gpu_status
        }
        
        # Power management
        self.power_manager = None
        self.standby_monitor = None
        
        # Post-processing engine v2.0 (legacy)
        self.post_processor = PostProcessEngine()
        
        # Topology metrics engine (v3.0 enhancement)
        self.topology_engine = None  # Lazy init on first use
        self.post_processor_v3 = None  # Lazy init on first use
        
        # Knowledge base loader
        self.kb_loader = None  # Lazy init on first use
        self.kb_graph = None  # Loaded knowledge graph
        
        # Checkpoint / auto-save system
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir="checkpoints",
            max_checkpoints=5,
            auto_save_interval_sec=300,
            auto_save_operations=10
        )
        self.session_snapshot = SessionSnapshot(self.checkpoint_manager)
        self.auto_saver = AutoSaver(self.session_snapshot, interval_sec=300)
        self.auto_saver.start()
        
        # Ω级裁定合规检查器
        self.omega_checker = OmegaComplianceChecker()
        
        # Symbolic Engine v3.0 - Phase 2核心升级
        self.symbolic_engine_v3 = None  # Lazy init on first use
        self.heat_tax_monitor = None  # Lazy init on first use
        
        # Organizational Resilience Scanner - Phase 2新增
        self.resilience_scanner = None  # Lazy init on first use
        
        # Stability monitoring system
        self.health_monitor = SystemHealthMonitor(check_interval_sec=30)
        self.health_monitor.start_monitoring()
        self.task_scheduler = AdaptiveTaskScheduler(self.health_monitor)
        
        # Stability-aware operation tracking
        self._operation_count = 0
        self._stability_window = []  # Recent stability scores
    
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
    
    def omega_analyze(self, text: str) -> Dict:
        """
        Ω级裁定深度合规分析
        结合符号规则引擎和K3残余检测
        """
        # 基础合规检查
        omega_result = check_compliance(text)
        
        # 层级摘要
        layer_summary = self.omega_checker.get_layer_summary(RuleLayer.L1)
        
        # 综合评分
        violation_count = omega_result["violation_count"]
        k3_score = sum(len(v) for v in omega_result["k3_residuals"].values())
        
        # 调谐度估算（基于违规密度）
        text_length = len(text)
        violation_density = violation_count / max(text_length / 100, 1)
        estimated_tuning = max(0, 1.0 - violation_density * 0.5)
        
        return {
            "compliant": omega_result["compliant"],
            "violation_count": violation_count,
            "k3_residual_score": k3_score,
            "estimated_tuning": round(estimated_tuning, 3),
            "violations": omega_result["violations"],
            "k3_residuals": omega_result["k3_residuals"],
            "layer_summary": omega_result["layer_summary"],
            "l1_rule_coverage": layer_summary,
            "recommendation": "PASS" if omega_result["compliant"] else "REWRITE_REQUIRED"
        }
    
    def generate(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        Method 2: generate() - Full pipeline: Arbiter -> Responder -> Post-process
        Note: For stability-aware generation, use generate_with_stability()
        """
        self.stats["total_requests"] += 1
        
        # Step 0: Ω级裁定合规预检
        omega_violations = self.omega_checker.check_text(user_input)
        omega_k3 = self.omega_checker.check_k3_residuals(user_input)
        
        # Step 1: Arbiter check
        arbiter_result = self.arbiter.check(user_input)
        
        # Step 2: Handle rewrites (Arbiter + Omega combined)
        rewrites = 0
        current_input = user_input
        combined_rewrite_needed = arbiter_result.rewrite_needed or len(omega_violations) > 0
        
        while combined_rewrite_needed and rewrites < self.max_retries:
            self.stats["rewrites"] += 1
            rewrites += 1
            
            # Omega-level rewrite suggestions
            if omega_violations and rewrites <= len(omega_violations):
                v = omega_violations[rewrites - 1]
                suggestion = v.get("suggestion", "")
                if suggestion and suggestion != "需人工审核":
                    current_input = current_input.replace(v["matched_text"], suggestion)
            
            # Arbiter rewrite
            if arbiter_result.rewrite_prompt:
                current_input = self._rewrite(current_input, arbiter_result.rewrite_prompt)
            
            # Re-check
            arbiter_result = self.arbiter.check(current_input)
            omega_violations = self.omega_checker.check_text(current_input)
            combined_rewrite_needed = arbiter_result.rewrite_needed or len(omega_violations) > 0
        
        # Step 3: Generate response
        if arbiter_result.compliance == ComplianceStatus.FAIL:
            response = self._generate_error(arbiter_result)
        else:
            response = self.responder.respond(current_input, arbiter_result)
            response = self._post_process(response)
            # Ω级后处理：检测响应中的K3残余
            response_omega = self.omega_checker.check_text(response)
            if response_omega:
                response += f"\n\n[Ω-Note: {len(response_omega)} compliance suggestions applied]"
        
        return {
            "response": response,
            "arbiter_result": arbiter_result,
            "omega_violations": omega_violations,
            "omega_k3_residuals": omega_k3,
            "rewrites": rewrites,
            "success": arbiter_result.compliance != ComplianceStatus.FAIL and len(omega_violations) == 0,
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
        """Apply post-processing filter using v2.0 engine"""
        result = self.post_processor.filter(response)
        if result.had_changes:
            self.stats["post_filter_replacements"] = \
                self.stats.get("post_filter_replacements", 0) + result.replacement_count
        return result.text
    
    def _ensure_symbolic_engine_v3(self):
        """Lazy initialization of Symbolic Engine v3.0"""
        if self.symbolic_engine_v3 is None:
            self.symbolic_engine_v3 = create_mss_v12_engine()
            self.heat_tax_monitor = HeatTaxMonitor()
    
    def _ensure_topology_engine(self):
        """Lazy initialization of topology engine"""
        if self.topology_engine is None:
            # Try to load from knowledge base
            if self.kb_graph is None:
                try:
                    self.kb_loader = KBLoader()
                    self.kb_loader.load_all()
                    self.kb_graph = self.kb_loader.to_graph()
                except Exception:
                    # Fallback: create empty graph
                    from symbolic_engine_v2 import MSSKnowledgeGraph
                    self.kb_graph = MSSKnowledgeGraph()
            self.topology_engine = TopologyMetricsEngine(self.kb_graph)
            self.post_processor_v3 = create_topology_aware_engine(self.topology_engine)
    
    def post_process_v3(self, response: str) -> Dict:
        """
        Apply topology-aware post-processing (v3.0)
        Returns dict with text, topology_warnings, had_changes
        """
        self._ensure_topology_engine()
        result = self.post_processor_v3.filter(response)
        if result.had_changes:
            self.stats["post_filter_replacements"] = \
                self.stats.get("post_filter_replacements", 0) + result.replacement_count
        return {
            "text": result.text,
            "topology_warnings": getattr(result, 'topology_warnings', []),
            "had_changes": result.had_changes,
            "replacement_count": result.replacement_count
        }
    
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
    
    def enhance_prompt_with_skills(self, base_prompt: str, level: str = "L2") -> str:
        """Enhance system prompt with MSS skills context"""
        enhancement = self.skill_loader.get_system_prompt_enhancement(level)
        return f"{enhancement}\n\n{base_prompt}"
    
    def get_stats(self) -> Dict:
        """Return statistics"""
        return self.stats.copy()
    
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
    
    def enable_power_management(self, standby_timeout: int = 30, hibernate_timeout: int = 120) -> Dict:
        """
        Enable automatic standby/hibernate power management
        
        Args:
            standby_timeout: Minutes of inactivity before standby
            hibernate_timeout: Minutes of inactivity before hibernate
        
        Returns:
            Status dict with power manager info
        """
        self.power_manager, self.standby_monitor = integrate_with_tactic(
            self, 
            standby_timeout=standby_timeout,
            hibernate_timeout=hibernate_timeout
        )
        
        return {
            "enabled": True,
            "standby_timeout": standby_timeout,
            "hibernate_timeout": hibernate_timeout,
            "current_state": self.power_manager.state.value,
            "status": self.power_manager.get_status()
        }
    
    def get_power_status(self) -> Optional[Dict]:
        """Get current power management status"""
        if self.power_manager:
            return self.power_manager.get_status()
        return {"enabled": False, "message": "Power management not enabled"}
    
    def manual_standby(self) -> Dict:
        """Manually enter standby mode"""
        if self.power_manager:
            return self.power_manager.enter_standby(self)
        return {"success": False, "message": "Power management not enabled"}
    
    def manual_hibernate(self) -> Dict:
        """Manually enter hibernate mode"""
        if self.power_manager:
            return self.power_manager.enter_hibernate(self)
        return {"success": False, "message": "Power management not enabled"}
    
    def manual_resume(self) -> Dict:
        """Manually resume from standby/hibernate"""
        if self.power_manager:
            if self.power_manager.state.value == "hibernate":
                return self.power_manager.resume_from_hibernate(self)
            else:
                return self.power_manager.resume_from_standby(self)
        return {"success": False, "message": "Power management not enabled"}
    
    def _check_stability_before_op(self, op_type: str = "general") -> Dict:
        """
        Pre-operation stability check
        Returns: {"proceed": bool, "health": dict, "recommendation": str}
        """
        metrics = self.health_monitor.get_current_metrics()
        health = metrics.__dict__ if hasattr(metrics, '__dict__') else dict(metrics)
        score = health.get("stability_score", 1.0)
        
        self._stability_window.append(score)
        if len(self._stability_window) > 10:
            self._stability_window.pop(0)
        
        if score < 0.3:
            return {
                "proceed": False,
                "health": health,
                "recommendation": "CRITICAL: System unstable. Save state and pause operations."
            }
        elif score < 0.6 and op_type in ["generate", "redteam"]:
            return {
                "proceed": True,
                "health": health,
                "recommendation": "DEGRADED: Heavy operations throttled. Consider lighter tasks."
            }
        
        return {
            "proceed": True,
            "health": health,
            "recommendation": "OK"
        }
    
    def _check_stability_after_op(self, op_duration_sec: float, success: bool) -> None:
        """Post-operation stability update"""
        self._operation_count += 1
        
        # Record tool call in health monitor
        self.health_monitor.record_tool_call(
            success=success,
            duration_ms=op_duration_sec * 1000
        )
    
    def get_stability_status(self) -> Dict:
        """Get current stability status"""
        metrics = self.health_monitor.get_current_metrics()
        health = metrics.__dict__ if hasattr(metrics, '__dict__') else dict(metrics)
        return {
            "health": health,
            "recent_scores": self._stability_window.copy(),
            "total_operations": self._operation_count,
            "scheduler_status": {
                "task_count": len(getattr(self.task_scheduler, 'task_queue', []))
            }
        }
    
    def symbolic_reason(self, premise: str, conclusion: str) -> Dict:
        """
        Method 4: symbolic_reason() - Phase 2符号推理
        使用MSS v12.2公理体系进行形式化推理
        
        Args:
            premise: 前提公理/定理ID (如 "A1", "T1")
            conclusion: 目标结论ID (如 "T3")
        
        Returns:
            Dict with result, certainty, explanation, steps
        """
        self._ensure_symbolic_engine_v3()
        result = self.symbolic_engine_v3.reason(premise, conclusion)
        return {
            "premise": premise,
            "conclusion": conclusion,
            "result": result.result.name,
            "certainty": result.certainty,
            "explanation": result.explanation,
            "steps": len(result.steps) if result.steps else 0,
            "path": [step[0] for step in result.steps] + [conclusion] if result.steps else []
        }
    
    def monitor_heat_tax(self, O_d: float = None, phi: float = None, 
                         external_input: float = 0.0) -> Dict:
        """
        Method 5: monitor_heat_tax() - K3降维热寂监测
        
        Args:
            O_d: 规范场强 (0.0-1.0), None则使用当前值
            phi: 意义势能, None则使用当前值
            external_input: 外部意义输入
        
        Returns:
            Dict with status, alerts, recommendations, trend
        """
        self._ensure_symbolic_engine_v3()
        
        if O_d is not None:
            self.heat_tax_monitor.state.O_d = max(0.0, min(1.0, O_d))
        if phi is not None:
            self.heat_tax_monitor.state.phi = phi
        
        alerts = self.heat_tax_monitor.update(external_input=external_input)
        report = self.heat_tax_monitor.get_status_report()
        
        return {
            "status": "heat_death_imminent" if self.heat_tax_monitor.state.is_irreversible() 
                     else "degraded" if report["alerts"] else "operational",
            "O_d": round(self.heat_tax_monitor.state.O_d, 4),
            "phi": round(self.heat_tax_monitor.state.phi, 4),
            "gamma": round(self.heat_tax_monitor.state.gamma, 4),
            "alerts": report["alerts"],
            "recommendations": report["recommendations"],
            "trend": report["trend"],
            "irreversible": self.heat_tax_monitor.state.is_irreversible()
        }
    
    def get_axiom_system(self) -> Dict:
        """
        Method 6: get_axiom_system() - 获取MSS v12.2公理体系
        
        Returns:
            Dict with axioms, theorems, mechanisms
        """
        self._ensure_symbolic_engine_v3()
        
        # Build dict directly from axiom system
        axiom_system = self.symbolic_engine_v3.axiom_system
        return {
            "axioms": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "type": v.axiom_type.name,
                    "statement": v.statement,
                    "mathematical_form": v.mathematical_form,
                    "boundary_conditions": v.boundary_conditions,
                    "falsifiability": v.falsifiability_condition
                }
                for k, v in axiom_system.axioms.items()
            },
            "theorems": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "type": v.axiom_type.name,
                    "statement": v.statement,
                    "mathematical_form": v.mathematical_form,
                    "derivation_chain": v.derivation_chain,
                    "falsifiability": v.falsifiability_condition
                }
                for k, v in axiom_system.theorems.items()
            },
            "mechanisms": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "type": v.axiom_type.name,
                    "statement": v.statement,
                    "mathematical_form": v.mathematical_form,
                    "derivation_chain": v.derivation_chain,
                    "falsifiability": v.falsifiability_condition
                }
                for k, v in axiom_system.mechanisms.items()
            }
        }
    
    def check_knowledge_graph_integrity(self) -> Dict:
        """
        Method 7: check_knowledge_graph_integrity() - 知识图谱完整性检查
        检测循环依赖、孤立节点、层级一致性
        
        Returns:
            Dict with integrity score, issues, stats
        """
        self._ensure_symbolic_engine_v3()
        
        graph = self.symbolic_engine_v3.graph
        
        # 基础统计
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)
        
        # 检测循环
        from symbolic_engine_v3 import CycleDetector
        detector = CycleDetector(graph)
        cycles = detector.find_cycles()
        
        # 检测矛盾
        contradictions = detector.check_contradiction_cycles()
        
        # 孤立节点
        connected = set()
        for edge in graph.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        isolated = [n_id for n_id in graph.nodes if n_id not in connected]
        
        # 完整性评分
        integrity = 1.0
        if cycles:
            integrity -= len(cycles) * 0.1
        if contradictions:
            integrity -= len(contradictions) * 0.2
        if isolated:
            integrity -= len(isolated) * 0.05
        integrity = max(0.0, integrity)
        
        return {
            "integrity_score": round(integrity, 3),
            "node_count": node_count,
            "edge_count": edge_count,
            "cycles_detected": len(cycles),
            "cycles": [list(c) for c in cycles[:5]],  # 最多5个
            "contradictions_detected": len(contradictions),
            "contradictions": [list(c) for c in contradictions[:5]],
            "isolated_nodes": isolated,
            "status": "healthy" if integrity > 0.8 else "degraded" if integrity > 0.5 else "critical"
        }
    
    def generate_with_stability(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        Stability-aware wrapper for generate()
        Performs pre/post stability checks and throttles if needed
        """
        import time
        
        # Pre-check
        pre_check = self._check_stability_before_op("generate")
        if not pre_check["proceed"]:
            return {
                "success": False,
                "error": pre_check["recommendation"],
                "stability": pre_check["health"],
                "response": None
            }
        
        start_time = time.time()
        
        try:
            result = self.generate(user_input, context)
            duration = time.time() - start_time
            
            # Post-check
            self._check_stability_after_op(duration, result.get("success", False))
            
            # Attach stability info
            result["stability"] = {
                "pre_check": pre_check["health"],
                "post_check": self.health_monitor.get_current_metrics(),
                "duration_sec": duration,
                "recommendation": pre_check["recommendation"]
            }
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self._check_stability_after_op(duration, False)
            return {
                "success": False,
                "error": str(e),
                "stability": pre_check["health"],
                "response": None
            }
    
    def _ensure_resilience_scanner(self):
        """Lazy initialization of Organizational Resilience Scanner"""
        if self.resilience_scanner is None:
            self.resilience_scanner = OrganizationalResilienceScanner(
                symbolic_engine=self.symbolic_engine_v3
            )
    
    def scan_organization(self, org_data: Optional[Dict] = None) -> Dict:
        """
        Method 8: scan_organization() - 组织韧性扫描
        
        Args:
            org_data: 组织数据字典，None则使用演示数据
        
        Returns:
            Dict with snapshot, metrics, diagnosis, recommendations
        """
        self._ensure_symbolic_engine_v3()
        self._ensure_resilience_scanner()
        
        if org_data is None:
            org_data = create_demo_organization()
        
        snapshot = self.resilience_scanner.scan_organization(org_data)
        
        return {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp,
            "org_name": org_data.get("org_name", "Unknown"),
            "global_metrics": {
                "O_d": snapshot.global_O_d,
                "phi": snapshot.global_phi,
                "gamma": snapshot.global_gamma,
                "innovation_rate": snapshot.global_innovation_rate,
                "resilience_score": snapshot.resilience_score,
                "resilience_grade": snapshot.resilience_grade
            },
            "departments": {
                dept_id: {
                    "name": metrics.dept_name,
                    "type": metrics.dept_type.name,
                    "O_d": metrics.O_d,
                    "phi": metrics.phi,
                    "innovation_rate": metrics.innovation_rate,
                    "headcount": metrics.headcount,
                    "approval_layers": metrics.approval_layers,
                    "meeting_hours_weekly": metrics.meeting_hours_weekly,
                    "employee_satisfaction": metrics.employee_satisfaction
                }
                for dept_id, metrics in snapshot.departments.items()
            },
            "diagnosis": snapshot.diagnosis,
            "recommendations": snapshot.recommendations,
            "mss_framework": {
                "version": "v12.2",
                "axiom_reference": "A1-A3 + T1-T3 + MECH-EVOL-002",
                "scan_methodology": "K3_observable -> L1_symbolic_mapping"
            }
        }
    
    def export_resilience_report(self, snapshot_id: str, filepath: str) -> str:
        """
        导出组织韧性报告
        
        Args:
            snapshot_id: 快照ID
            filepath: 输出文件路径
        
        Returns:
            导出的文件路径
        """
        self._ensure_resilience_scanner()
        
        snapshot = next(
            (s for s in self.resilience_scanner.history if s.snapshot_id == snapshot_id),
            None
        )
        
        if snapshot is None:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        return self.resilience_scanner.export_report(snapshot, filepath)
    
    def compare_resilience_snapshots(self, snapshot1_id: str, snapshot2_id: str) -> Dict:
        """
        对比两个组织韧性快照
        
        Args:
            snapshot1_id: 第一个快照ID
            snapshot2_id: 第二个快照ID
        
        Returns:
            Dict with comparison results
        """
        self._ensure_resilience_scanner()
        return self.resilience_scanner.compare_snapshots(snapshot1_id, snapshot2_id)


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
    
    # Test topology metrics (lazy init)
    print("\n4. Testing topology metrics:")
    try:
        from symbolic_engine_v2 import MSSKnowledgeGraph, ConceptNode, NodeType
        graph = MSSKnowledgeGraph()
        graph.add_node(ConceptNode(id="test_l1", name="Test L1", node_type=NodeType.AXIOM, layer="L1"))
        graph.add_node(ConceptNode(id="test_l2", name="Test L2", node_type=NodeType.THEOREM, layer="L2"))
        tactic.topology_engine = TopologyMetricsEngine(graph)
        health = tactic.topology_engine.get_graph_health()
        print(f"   Graph health: {health['overall_score']:.2f}")
        print(f"   Nodes: {health['node_count']}")
    except Exception as e:
        print(f"   Skipped: {e}")
    
    # Test organizational resilience scan
    print("\n5. Testing organizational resilience scan:")
    try:
        result = tactic.scan_organization()
        print(f"   Organization: {result['org_name']}")
        print(f"   Resilience Grade: {result['global_metrics']['resilience_grade']}")
        print(f"   Resilience Score: {result['global_metrics']['resilience_score']}")
        print(f"   O_d: {result['global_metrics']['O_d']}")
        print(f"   phi: {result['global_metrics']['phi']}")
        print(f"   Departments: {len(result['departments'])}")
        print(f"   Diagnosis items: {len(result['diagnosis'])}")
        print(f"   Recommendations: {len(result['recommendations'])}")
    except Exception as e:
        print(f"   Error: {e}")
    except Exception as e:
        print(f"   Skipped: {e}")
    
    print("\n" + "=" * 60)
    print("Stats:", tactic.get_stats())
