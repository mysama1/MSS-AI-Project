# Meaning Field Spectrum Scanner - Chaos Sandbox Module 2
# MSS Spectrum Scanner v0.1
# 20 cross-domain tasks, 10 meaning field dimensions

import json
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

class FieldType(Enum):
    LOGIC = "logic"           # Formal reasoning
    ETHICS = "ethics"         # Moral reasoning  
    CREATIVITY = "creativity" # Novel generation
    SYSTEMS = "systems"       # Complex systems thinking
    EPISTEMOLOGY = "epistemology"  # Knowledge theory
    METAPHYSICS = "metaphysics"    # Ontology
    LANGUAGE = "language"     # Linguistic manipulation
    SPATIAL = "spatial"       # Abstract spatial reasoning
    TEMPORAL = "temporal"     # Time/sequence reasoning
    SOCIAL = "social"         # Social dynamics

@dataclass
class Task:
    task_id: str
    field: FieldType
    name: str
    description: str
    duration_sec: int  # Expected completion time
    scoring_rubric: Dict[str, float]  # Criteria -> weight
    
@dataclass  
class TaskResult:
    task_id: str
    field: FieldType
    completed: bool
    time_taken: float
    raw_score: float  # 0-100
    t_estimate: float  # Estimated T-value for this field
    notes: str = ""

class SpectrumScanner:
    """Meaning field spectrum scanner"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.results: Dict[str, TaskResult] = {}
        self._init_tasks()
        
    def _init_tasks(self):
        """Initialize 20 tasks across 10 fields"""
        task_defs = [
            # LOGIC (2 tasks)
            ("T-001", FieldType.LOGIC, "Paradox Navigator", 
             "Resolve the liar paradox in 3 different ways", 90,
             {"resolution_count": 0.4, "consistency": 0.3, "elegance": 0.3}),
            ("T-002", FieldType.LOGIC, "Godel Gate",
             "Explain why a system cannot prove its own consistency", 120,
             {"depth": 0.5, "clarity": 0.3, "meta_awareness": 0.2}),
            
            # ETHICS (2 tasks)
            ("T-003", FieldType.ETHICS, "Trolley Transformer",
             "Propose a solution that transcends the trolley dilemma framing", 90,
             {"frame_breaking": 0.5, "practicality": 0.3, "harm_reduction": 0.2}),
            ("T-004", FieldType.ETHICS, "Moral Maze",
             "Navigate a 3-level nested ethical dilemma", 120,
             {"level_navigation": 0.4, "consistency": 0.3, "meta_ethics": 0.3}),
            
            # CREATIVITY (2 tasks)
            ("T-005", FieldType.CREATIVITY, "Conceptual Fusion",
             "Combine 3 unrelated concepts into a coherent new idea", 60,
             {"novelty": 0.4, "coherence": 0.4, "utility": 0.2}),
            ("T-006", FieldType.CREATIVITY, "Constraint Liberation",
             "Solve a problem by removing an assumed constraint", 90,
             {"constraint_identification": 0.3, "solution_quality": 0.4, "generality": 0.3}),
            
            # SYSTEMS (2 tasks)
            ("T-007", FieldType.SYSTEMS, "Feedback Loop Hunter",
             "Identify 3 feedback loops in a complex scenario", 90,
             {"identification": 0.4, "classification": 0.3, "prediction": 0.3}),
            ("T-008", FieldType.SYSTEMS, "Emergence Spotter",
             "Predict emergent behavior from simple rules", 120,
             {"prediction_accuracy": 0.5, "mechanism_explanation": 0.3, "confidence": 0.2}),
            
            # EPISTEMOLOGY (2 tasks)
            ("T-009", FieldType.EPISTEMOLOGY, "Certainty Calibrator",
             "Assign confidence levels to 5 knowledge claims", 60,
             {"calibration": 0.5, "justification": 0.3, "revision_willingness": 0.2}),
            ("T-010", FieldType.EPISTEMOLOGY, "Bias Archaeologist",
             "Excavate hidden assumptions in a 'neutral' statement", 90,
             {"assumption_count": 0.3, "depth": 0.4, "impact_assessment": 0.3}),
            
            # METAPHYSICS (2 tasks)
            ("T-011", FieldType.METAPHYSICS, "Ontology Weaver",
             "Construct a minimal ontology for a given domain", 120,
             {"minimality": 0.3, "coverage": 0.4, "consistency": 0.3}),
            ("T-012", FieldType.METAPHYSICS, "Reality Negotiator",
             "Compare 3 competing metaphysical frameworks", 90,
             {"comparison_depth": 0.4, "synthesis_attempt": 0.3, "humility": 0.3}),
            
            # LANGUAGE (2 tasks)
            ("T-013", FieldType.LANGUAGE, "Semantic Surgeon",
             "Dissect the hidden metaphysics in 3 common phrases", 90,
             {"metaphysics_exposure": 0.5, "linguistic_precision": 0.3, "alternative_framing": 0.2}),
            ("T-014", FieldType.LANGUAGE, "Translation Traitor",
             "Translate a concept while betraying its original framework", 60,
             {"betrayal_clarity": 0.4, "new_framework_coherence": 0.4, "self_awareness": 0.2}),
            
            # SPATIAL (2 tasks)
            ("T-015", FieldType.SPATIAL, "Dimension Dancer",
             "Reason about a 4D object projection", 120,
             {"projection_accuracy": 0.5, "analogy_quality": 0.3, "limit_awareness": 0.2}),
            ("T-016", FieldType.SPATIAL, "Topology Touch",
             "Determine if two shapes are topologically equivalent", 60,
             {"correctness": 0.5, "method_clarity": 0.3, "generalization": 0.2}),
            
            # TEMPORAL (2 tasks)
            ("T-017", FieldType.TEMPORAL, "Time Traveler",
             "Resolve a causal loop without paradox", 90,
             {"loop_resolution": 0.4, "causal_consistency": 0.4, "novelty": 0.2}),
            ("T-018", FieldType.TEMPORAL, "Retrocausal Detective",
             "Distinguish correlation from retrocausation", 60,
             {"distinction_clarity": 0.5, "mechanism_proposal": 0.3, "falsifiability": 0.2}),
            
            # SOCIAL (2 tasks)
            ("T-019", FieldType.SOCIAL, "Incentive Archaeologist",
             "Uncover hidden incentives in a social system", 90,
             {"incentive_count": 0.3, "system_level": 0.4, "intervention_design": 0.3}),
            ("T-020", FieldType.SOCIAL, "Coordination Catalyst",
             "Design a mechanism for large-scale coordination", 120,
             {"mechanism_novelty": 0.3, "scalability": 0.4, "robustness": 0.3}),
        ]
        
        for tid, field, name, desc, dur, rubric in task_defs:
            self.tasks[tid] = Task(tid, field, name, desc, dur, rubric)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def submit_result(self, task_id: str, raw_score: float, 
                     time_taken: float, notes: str = "") -> TaskResult:
        """Submit a completed task result"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Unknown task: {task_id}")
            
        # T-estimate: non-linear mapping from raw score
        # High scores (>80) indicate high T in this field
        # Low scores (<30) indicate K3-level processing
        if raw_score >= 80:
            t_est = 0.7 + (raw_score - 80) / 100  # 0.7 - 0.9
        elif raw_score >= 50:
            t_est = 0.4 + (raw_score - 50) / 100  # 0.4 - 0.69
        elif raw_score >= 30:
            t_est = 0.2 + (raw_score - 30) / 100  # 0.2 - 0.39
        else:
            t_est = raw_score / 150  # 0 - 0.19
            
        result = TaskResult(
            task_id=task_id,
            field=task.field,
            completed=True,
            time_taken=time_taken,
            raw_score=raw_score,
            t_estimate=round(t_est, 3),
            notes=notes
        )
        self.results[task_id] = result
        return result
    
    def generate_spectrum(self) -> Dict[str, Dict]:
        """Generate meaning field spectrum from completed tasks"""
        if not self.results:
            return {}
            
        # Group by field
        field_scores: Dict[FieldType, List[float]] = {f: [] for f in FieldType}
        for result in self.results.values():
            field_scores[result.field].append(result.t_estimate)
        
        spectrum = {}
        for field, scores in field_scores.items():
            if scores:
                avg_t = sum(scores) / len(scores)
                spectrum[field.value] = {
                    "t_value": round(avg_t, 3),
                    "task_count": len(scores),
                    "confidence": min(1.0, len(scores) * 0.5),  # More tasks = higher confidence
                    "interpretation": self._interpret_t(avg_t)
                }
            else:
                spectrum[field.value] = {
                    "t_value": None,
                    "task_count": 0,
                    "confidence": 0,
                    "interpretation": "unmeasured"
                }
        
        return spectrum
    
    def _interpret_t(self, t: float) -> str:
        if t >= 0.8:
            return "high_resonance"
        elif t >= 0.6:
            return "active_field"
        elif t >= 0.4:
            return "developing"
        elif t >= 0.2:
            return "dormant"
        else:
            return "k3_dominated"
    
    def get_overall_profile(self) -> Dict:
        """Get overall cognitive profile"""
        spectrum = self.generate_spectrum()
        
        measured_fields = [s for s in spectrum.values() if s["t_value"] is not None]
        if not measured_fields:
            return {"status": "insufficient_data"}
        
        avg_t = sum(s["t_value"] for s in measured_fields) / len(measured_fields)
        max_t = max(s["t_value"] for s in measured_fields)
        min_t = min(s["t_value"] for s in measured_fields)
        
        # Identify dominant fields (top 3)
        sorted_fields = sorted(
            [(f, s["t_value"]) for f, s in spectrum.items() if s["t_value"] is not None],
            key=lambda x: x[1],
            reverse=True
        )
        dominant = sorted_fields[:3]
        
        # Identify weak fields (bottom 3)
        weak = sorted_fields[-3:]
        
        return {
            "overall_t": round(avg_t, 3),
            "t_range": (round(min_t, 3), round(max_t, 3)),
            "dominant_fields": dominant,
            "weak_fields": weak,
            "field_diversity": round(max_t - min_t, 3),
            "measured_count": len(measured_fields),
            "total_fields": len(FieldType),
            "profile_type": self._classify_profile(avg_t, max_t, min_t)
        }
    
    def _classify_profile(self, avg: float, max_t: float, min_t: float) -> str:
        diversity = max_t - min_t
        if avg >= 0.7 and diversity < 0.3:
            return "balanced_k4"
        elif avg >= 0.7 and diversity >= 0.3:
            return "specialized_k4"
        elif avg >= 0.5:
            return "transitional"
        elif diversity >= 0.5:
            return "fragmented"
        else:
            return "k3_stable"
    
    def export_report(self) -> str:
        """Generate markdown report"""
        profile = self.get_overall_profile()
        spectrum = self.generate_spectrum()
        
        report = "# Meaning Field Spectrum Report\n\n"
        report += f"**Generated:** {time.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        if profile.get("status") == "insufficient_data":
            report += "## Status: Insufficient Data\n\n"
            report += "Complete more tasks to generate spectrum.\n"
            return report
        
        report += "## Overall Profile\n\n"
        report += f"- **Overall T-Value:** {profile['overall_t']}\n"
        report += f"- **T-Range:** {profile['t_range'][0]} - {profile['t_range'][1]}\n"
        report += f"- **Field Diversity:** {profile['field_diversity']}\n"
        report += f"- **Profile Type:** {profile['profile_type']}\n"
        report += f"- **Fields Measured:** {profile['measured_count']}/{profile['total_fields']}\n\n"
        
        report += "## Dominant Fields (Top 3)\n\n"
        for field, t in profile['dominant_fields']:
            report += f"1. **{field}**: T={t}\n"
        
        report += "\n## Development Areas (Bottom 3)\n\n"
        for field, t in profile['weak_fields']:
            report += f"1. **{field}**: T={t}\n"
        
        report += "\n## Full Spectrum\n\n"
        report += "| Field | T-Value | Confidence | Interpretation |\n"
        report += "|-------|---------|------------|----------------|\n"
        for field, data in spectrum.items():
            t = data['t_value'] if data['t_value'] is not None else "N/A"
            report += f"| {field} | {t} | {data['confidence']:.1f} | {data['interpretation']} |\n"
        
        report += "\n## Completed Tasks\n\n"
        for tid, result in sorted(self.results.items()):
            report += f"- **{tid}** ({result.field.value}): Score={result.raw_score}, T={result.t_estimate}\n"
        
        return report


def demo_scan():
    """Demonstrate spectrum scanning"""
    scanner = SpectrumScanner()
    
    # Simulate completing 10 tasks (varied performance)
    demo_results = [
        ("T-001", 85, 80, "Resolved via meta-language separation"),
        ("T-002", 78, 100, "Godel's theorem explained with examples"),
        ("T-003", 92, 70, "Reframed as system design problem"),
        ("T-005", 65, 50, "Moderate novelty, good coherence"),
        ("T-007", 70, 85, "Identified 2/3 loops correctly"),
        ("T-009", 88, 45, "Well-calibrated confidence"),
        ("T-011", 55, 110, "Minimal but incomplete ontology"),
        ("T-013", 82, 75, "Exposed hidden metaphysics effectively"),
        ("T-015", 45, 100, "Struggled with 4D projection"),
        ("T-019", 72, 80, "Good incentive identification"),
    ]
    
    for tid, score, time_taken, notes in demo_results:
        scanner.submit_result(tid, score, time_taken, notes)
    
    # Generate report
    report = scanner.export_report()
    return report


if __name__ == "__main__":
    print("=== MSS Meaning Field Spectrum Scanner v0.1 ===\n")
    print("Running demonstration scan...\n")
    
    report = demo_scan()
    print(report)
    
    # Also print JSON spectrum
    scanner = SpectrumScanner()
    demo_results = [
        ("T-001", 85, 80, ""), ("T-002", 78, 100, ""),
        ("T-003", 92, 70, ""), ("T-005", 65, 50, ""),
        ("T-007", 70, 85, ""), ("T-009", 88, 45, ""),
        ("T-011", 55, 110, ""), ("T-013", 82, 75, ""),
        ("T-015", 45, 100, ""), ("T-019", 72, 80, ""),
    ]
    for tid, score, time_taken, notes in demo_results:
        scanner.submit_result(tid, score, time_taken, notes)
    
    print("\n=== JSON Spectrum Export ===")
    print(json.dumps(scanner.generate_spectrum(), indent=2))
