"""
MSS Framework Task Evaluation
Evaluates tasks and task bar design using MSS core axioms
"""

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TaskEvaluation:
    """Task evaluation result"""
    task_id: str
    task_name: str
    logic_rigidity: float  # M_L score (0-1)
    heat_tax: float  # γ score (0-1, lower is better)
    information_slice_quality: float  # A2 compliance (0-1)
    contradiction_handling: float  # A6 compliance (0-1)
    overall_score: float
    recommendations: List[str]

class MSSTaskEvaluator:
    """Evaluate tasks using MSS framework"""
    
    def __init__(self):
        self.evaluations: List[TaskEvaluation] = []
    
    def evaluate_task(self, task: Dict) -> TaskEvaluation:
        """
        Evaluate a single task using MSS framework
        
        A1: Information Ontology - Does the task produce meaningful information?
        A2: Information Slicing - Is the task boundary clearly defined?
        A3: Heat Tax - Is the task efficient (low entropy production)?
        A4: Logic-Physics Entropy Mapping - Is the task grounded in reality?
        A5: Normative Field - Does the task follow MSS principles?
        A6: Contradiction Ascension - Does the task handle conflicts properly?
        """
        task_id = task.get("id", "unknown")
        task_name = task.get("name", "unknown")
        progress = task.get("progress", "0%")
        priority = task.get("priority", 5)
        
        # Parse progress percentage
        progress_pct = self._parse_progress(progress)
        
        # A1: Information Ontology (0-1)
        # Tasks that produce clear, meaningful information score higher
        info_score = self._evaluate_information_ontology(task)
        
        # A2: Information Slicing (0-1)
        # Tasks with clear boundaries and scope score higher
        slice_score = self._evaluate_information_slicing(task)
        
        # A3: Heat Tax (0-1, lower is better)
        # Tasks that are efficient and don't waste resources score higher
        heat_tax = self._evaluate_heat_tax(task, progress_pct)
        
        # A4: Logic-Physics Entropy Mapping (0-1)
        # Tasks grounded in reality and physics score higher
        physics_score = self._evaluate_physics_mapping(task)
        
        # A5: Normative Field (0-1)
        # Tasks following MSS principles score higher
        normative_score = self._evaluate_normative_field(task)
        
        # A6: Contradiction Handling (0-1)
        # Tasks that properly handle conflicts score higher
        contradiction_score = self._evaluate_contradiction_handling(task)
        
        # Calculate overall logic rigidity (M_L)
        # Weighted average of A1, A2, A4, A5, A6
        logic_rigidity = (info_score * 0.2 + 
                         slice_score * 0.2 + 
                         physics_score * 0.2 + 
                         normative_score * 0.2 + 
                         contradiction_score * 0.2)
        
        # Overall score (combining M_L and heat tax)
        # Higher M_L and lower heat tax = better
        overall = logic_rigidity * (1 - heat_tax)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            task, info_score, slice_score, heat_tax, 
            physics_score, normative_score, contradiction_score
        )
        
        return TaskEvaluation(
            task_id=task_id,
            task_name=task_name,
            logic_rigidity=round(logic_rigidity, 3),
            heat_tax=round(heat_tax, 3),
            information_slice_quality=round(slice_score, 3),
            contradiction_handling=round(contradiction_score, 3),
            overall_score=round(overall, 3),
            recommendations=recommendations
        )
    
    def _parse_progress(self, progress: str) -> float:
        """Parse progress percentage from string"""
        try:
            # Extract number before %
            pct_str = progress.split("%")[0].strip()
            return float(pct_str) / 100.0
        except:
            return 0.0
    
    def _evaluate_information_ontology(self, task: Dict) -> float:
        """Evaluate A1: Information Ontology"""
        # Tasks with clear deliverables and outputs score higher
        progress = task.get("progress", "")
        
        # Check if progress description mentions concrete outputs
        concrete_indicators = ["完成", "通过", "实现", "测试", "部署"]
        score = 0.5  # Base score
        
        for indicator in concrete_indicators:
            if indicator in progress:
                score += 0.1
        
        return min(1.0, score)
    
    def _evaluate_information_slicing(self, task: Dict) -> float:
        """Evaluate A2: Information Slicing"""
        # Tasks with clear boundaries and scope score higher
        task_id = task.get("id", "")
        phase = task.get("phase", "")
        week = task.get("week", "")
        
        score = 0.5  # Base score
        
        # Clear ID format
        if task_id and "-" in task_id:
            score += 0.2
        
        # Clear phase assignment
        if phase:
            score += 0.1
        
        # Clear week assignment
        if week and week != "TBD":
            score += 0.2
        
        return min(1.0, score)
    
    def _evaluate_heat_tax(self, task: Dict, progress_pct: float) -> float:
        """Evaluate A3: Heat Tax (lower is better)"""
        # Tasks that are efficient and progressing well score lower heat tax
        priority = task.get("priority", 5)
        
        # Higher priority tasks should have lower heat tax (more efficient)
        # But if they're stuck, heat tax increases
        
        base_tax = 0.3  # Base heat tax
        
        # Adjust based on progress
        if progress_pct < 0.2:
            base_tax += 0.2  # Low progress = higher tax
        elif progress_pct > 0.8:
            base_tax -= 0.1  # High progress = lower tax
        
        # Adjust based on priority (high priority should be efficient)
        if priority >= 8:
            base_tax -= 0.1
        elif priority <= 4:
            base_tax += 0.1
        
        return max(0.0, min(1.0, base_tax))
    
    def _evaluate_physics_mapping(self, task: Dict) -> float:
        """Evaluate A4: Logic-Physics Entropy Mapping"""
        # Tasks grounded in reality score higher
        niche = task.get("niche", "")
        
        score = 0.5  # Base score
        
        # Infrastructure tasks are more grounded
        if "基础设施" in niche:
            score += 0.2
        
        # AI core tasks need strong physics grounding
        if "AI核心" in niche:
            score += 0.1
        
        # Research tasks may be less grounded
        if "理论研究" in niche:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _evaluate_normative_field(self, task: Dict) -> float:
        """Evaluate A5: Normative Field"""
        # Tasks following MSS principles score higher
        task_name = task.get("name", "")
        
        score = 0.6  # Base score (assuming MSS compliance)
        
        # Check for MSS-specific terminology
        mss_terms = ["符号", "逻辑", "热税", "公理", "推理", "合规"]
        for term in mss_terms:
            if term in task_name:
                score += 0.05
        
        return min(1.0, score)
    
    def _evaluate_contradiction_handling(self, task: Dict) -> float:
        """Evaluate A6: Contradiction Handling"""
        # Tasks that properly handle conflicts score higher
        progress = task.get("progress", "")
        
        score = 0.5  # Base score
        
        # Check if task mentions handling issues or conflicts
        conflict_indicators = ["修复", "解决", "优化", "处理", "审计"]
        for indicator in conflict_indicators:
            if indicator in progress:
                score += 0.1
        
        return min(1.0, score)
    
    def _generate_recommendations(self, task: Dict, 
                                 info_score: float, 
                                 slice_score: float,
                                 heat_tax: float,
                                 physics_score: float,
                                 normative_score: float,
                                 contradiction_score: float) -> List[str]:
        """Generate recommendations based on evaluation"""
        recommendations = []
        
        if info_score < 0.6:
            recommendations.append("明确任务产出物，增加可交付成果描述")
        
        if slice_score < 0.6:
            recommendations.append("明确任务边界，细化阶段和周期规划")
        
        if heat_tax > 0.4:
            recommendations.append("优化执行效率，降低资源消耗")
        
        if physics_score < 0.5:
            recommendations.append("加强物理现实映射，确保工程可行性")
        
        if normative_score < 0.7:
            recommendations.append("强化MSS公理体系应用")
        
        if contradiction_score < 0.6:
            recommendations.append("建立矛盾检测与升维处理机制")
        
        if not recommendations:
            recommendations.append("任务状态良好，继续推进")
        
        return recommendations
    
    def evaluate_task_bar(self, task_bar: Dict) -> Dict:
        """Evaluate entire task bar design"""
        # Evaluate all active tasks
        active_tasks = task_bar.get("active_tasks", [])
        
        evaluations = []
        total_ml = 0.0
        total_heat = 0.0
        
        for task in active_tasks:
            eval_result = self.evaluate_task(task)
            evaluations.append(eval_result)
            total_ml += eval_result.logic_rigidity
            total_heat += eval_result.heat_tax
        
        # Calculate averages
        task_count = len(active_tasks)
        avg_ml = total_ml / task_count if task_count > 0 else 0
        avg_heat = total_heat / task_count if task_count > 0 else 0
        
        # Evaluate task bar structure
        structure_score = self._evaluate_task_bar_structure(task_bar)
        
        # Overall assessment
        overall_health = (avg_ml * 0.4 + structure_score * 0.4 + 
                         (1 - avg_heat) * 0.2)
        
        return {
            "overall_health": round(overall_health, 3),
            "average_logic_rigidity": round(avg_ml, 3),
            "average_heat_tax": round(avg_heat, 3),
            "structure_score": round(structure_score, 3),
            "task_evaluations": [
                {
                    "task_id": e.task_id,
                    "task_name": e.task_name,
                    "logic_rigidity": e.logic_rigidity,
                    "heat_tax": e.heat_tax,
                    "overall_score": e.overall_score,
                    "recommendations": e.recommendations
                }
                for e in evaluations
            ],
            "system_recommendations": self._generate_system_recommendations(
                avg_ml, avg_heat, structure_score
            )
        }
    
    def _evaluate_task_bar_structure(self, task_bar: Dict) -> float:
        """Evaluate task bar structure"""
        score = 0.5  # Base score
        
        # Check for required fields
        required_fields = ["version", "last_sync", "phase", "active_tasks", 
                          "system_status"]
        for field in required_fields:
            if field in task_bar:
                score += 0.05
        
        # Check for task diversity
        niches = set()
        for task in task_bar.get("active_tasks", []):
            niches.add(task.get("niche", ""))
        
        if len(niches) >= 3:
            score += 0.1
        
        # Check for status tracking
        if "completed_tasks" in task_bar:
            score += 0.1
        
        if "ongoing_tasks" in task_bar:
            score += 0.1
        
        return min(1.0, score)
    
    def _generate_system_recommendations(self, avg_ml: float, 
                                        avg_heat: float, 
                                        structure_score: float) -> List[str]:
        """Generate system-level recommendations"""
        recommendations = []
        
        if avg_ml < 0.7:
            recommendations.append("整体逻辑刚性偏低，建议强化公理体系应用")
        
        if avg_heat > 0.3:
            recommendations.append("整体热税偏高，建议优化任务执行效率")
        
        if structure_score < 0.7:
            recommendations.append("任务栏结构待完善，建议增加状态跟踪字段")
        
        if not recommendations:
            recommendations.append("任务栏设计良好，继续保持")
        
        return recommendations

# Example usage
if __name__ == "__main__":
    evaluator = MSSTaskEvaluator()
    
    # Example task
    task = {
        "id": "D1-001",
        "name": "符号引擎v4.0架构设计",
        "niche": "AI核心",
        "priority": 10,
        "progress": "55% - 核心模块+插件系统+缓存+集成测试完成",
        "phase": "D1",
        "week": "Week 1"
    }
    
    result = evaluator.evaluate_task(task)
    print(f"Task: {result.task_name}")
    print(f"M_L: {result.logic_rigidity}")
    print(f"Heat Tax: {result.heat_tax}")
    print(f"Overall: {result.overall_score}")
    print(f"Recommendations: {result.recommendations}")
