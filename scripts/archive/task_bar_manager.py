"""
MSS Task Bar Manager
Manages task bar with automatic new direction integration
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class Task:
    """Task definition"""
    id: str
    name: str
    niche: str
    priority: int
    progress: str
    phase: str
    week: str
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

@dataclass
class NewDirection:
    """New direction proposal"""
    id: str
    title: str
    description: str
    category: str
    priority: int
    estimated_effort: str
    related_tasks: List[str]
    proposed_at: str = ""
    
    def __post_init__(self):
        if not self.proposed_at:
            self.proposed_at = datetime.now().isoformat()

class TaskBarManager:
    """Task bar manager with automatic direction integration"""
    
    def __init__(self, task_bar_file: str = r"C:\MSS-AI-Project\task_bar_current.json"):
        self.task_bar_file = Path(task_bar_file)
        self.new_directions: List[NewDirection] = []
        self.integration_queue: List[Dict] = []
        self.load_task_bar()
    
    def load_task_bar(self) -> Dict:
        """Load current task bar"""
        if self.task_bar_file.exists():
            with open(self.task_bar_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._create_default_task_bar()
    
    def _create_default_task_bar(self) -> Dict:
        """Create default task bar structure"""
        return {
            "version": "3.0",
            "last_sync": datetime.now().isoformat(),
            "phase": "D",
            "phase_name": "工程化部署",
            "active_tasks": [],
            "ongoing_tasks": [],
            "completed_tasks": [],
            "standby_tasks": [],
            "pending_tasks": [],
            "archived_tasks": [],
            "system_status": {
                "logic_rigidity": "M_L ≡ 1.000000",
                "heat_tax": "γ = 0.000000",
                "theory_completion": "100%",
                "phase": "D",
                "phase_progress": "40%",
                "redshift_status": "Phase D全面推进中",
                "mss_version": "Ω级终审完成 → Phase D Week 2"
            },
            "resources": {}
        }
    
    def save_task_bar(self, data: Dict):
        """Save task bar to file"""
        data["last_sync"] = datetime.now().isoformat()
        with open(self.task_bar_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def propose_new_direction(self, title: str, description: str, 
                             category: str, priority: int,
                             estimated_effort: str,
                             related_tasks: List[str] = None) -> str:
        """
        Propose a new direction without disrupting current tasks
        
        Args:
            title: Direction title
            description: Detailed description
            category: Category (e.g., "AI核心", "产品工具", "理论研究")
            priority: Priority (1-10)
            estimated_effort: Estimated effort (e.g., "2周", "1月")
            related_tasks: Related existing task IDs
        
        Returns:
            Direction ID
        """
        direction_id = f"DIR-{datetime.now().strftime('%Y%m%d')}-{len(self.new_directions)+1:03d}"
        
        direction = NewDirection(
            id=direction_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            estimated_effort=estimated_effort,
            related_tasks=related_tasks or []
        )
        
        self.new_directions.append(direction)
        
        # Auto-categorize based on priority and current phase
        self._auto_categorize_direction(direction)
        
        return direction_id
    
    def _auto_categorize_direction(self, direction: NewDirection):
        """Auto-categorize new direction based on rules"""
        # Rule 1: High priority + related to active tasks -> standby (ready to integrate)
        # Rule 2: Low priority -> pending (review later)
        # Rule 3: Research category + high priority -> ongoing (parallel track)
        
        if direction.priority >= 8 and direction.related_tasks:
            # High priority with related tasks - add to standby for quick integration
            self.integration_queue.append({
                "direction": direction,
                "suggested_action": "standby",
                "reason": "High priority with related active tasks"
            })
        elif direction.priority <= 5:
            # Low priority - defer to pending
            self.integration_queue.append({
                "direction": direction,
                "suggested_action": "pending",
                "reason": "Low priority, defer for later review"
            })
        elif direction.category == "理论研究":
            # Research category - can run in parallel
            self.integration_queue.append({
                "direction": direction,
                "suggested_action": "ongoing",
                "reason": "Research can run in parallel with engineering"
            })
        else:
            # Default - add to standby
            self.integration_queue.append({
                "direction": direction,
                "suggested_action": "standby",
                "reason": "Standard priority, ready for integration"
            })
    
    def integrate_direction(self, direction_id: str, 
                           target_status: str = "standby") -> bool:
        """
        Integrate a new direction into task bar
        
        Args:
            direction_id: Direction ID to integrate
            target_status: Target status (standby, pending, ongoing)
        
        Returns:
            Success status
        """
        # Find direction
        direction = None
        for d in self.new_directions:
            if d.id == direction_id:
                direction = d
                break
        
        if not direction:
            return False
        
        # Load current task bar
        task_bar = self.load_task_bar()
        
        # Create task from direction
        task_id = f"{direction.category[:3].upper()}-{direction.id.split('-')[-1]}"
        
        new_task = {
            "id": task_id,
            "name": direction.title,
            "niche": direction.category,
            "priority": direction.priority,
            "progress": "0% - New direction integrated",
            "phase": task_bar["phase"],
            "week": "TBD",
            "status": target_status,
            "created_from_direction": direction_id,
            "estimated_effort": direction.estimated_effort
        }
        
        # Add to appropriate list
        if target_status == "standby":
            if "standby_tasks" not in task_bar:
                task_bar["standby_tasks"] = []
            task_bar["standby_tasks"].append(new_task)
        elif target_status == "pending":
            if "pending_tasks" not in task_bar:
                task_bar["pending_tasks"] = []
            task_bar["pending_tasks"].append(new_task)
        elif target_status == "ongoing":
            if "ongoing_tasks" not in task_bar:
                task_bar["ongoing_tasks"] = []
            task_bar["ongoing_tasks"].append(new_task)
        
        # Save updated task bar
        self.save_task_bar(task_bar)
        
        return True
    
    def get_integration_recommendations(self) -> List[Dict]:
        """Get recommendations for integrating new directions"""
        recommendations = []
        
        for item in self.integration_queue:
            direction = item["direction"]
            
            # Analyze impact on current tasks
            impact = self._analyze_impact(direction)
            
            recommendations.append({
                "direction_id": direction.id,
                "title": direction.title,
                "suggested_action": item["suggested_action"],
                "reason": item["reason"],
                "impact_analysis": impact,
                "priority": direction.priority,
                "estimated_effort": direction.estimated_effort
            })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x["priority"], reverse=True)
        
        return recommendations
    
    def _analyze_impact(self, direction: NewDirection) -> Dict:
        """Analyze impact of new direction on current tasks"""
        task_bar = self.load_task_bar()
        
        active_count = len(task_bar.get("active_tasks", []))
        ongoing_count = len(task_bar.get("ongoing_tasks", []))
        
        # Calculate resource overlap
        overlap_tasks = []
        for task in task_bar.get("active_tasks", []):
            if task["id"] in direction.related_tasks:
                overlap_tasks.append(task["id"])
        
        # Determine impact level
        if len(overlap_tasks) > 2:
            impact_level = "HIGH"
            impact_desc = f"Overlaps with {len(overlap_tasks)} active tasks"
        elif len(overlap_tasks) > 0:
            impact_level = "MEDIUM"
            impact_desc = f"Overlaps with {len(overlap_tasks)} active tasks"
        else:
            impact_level = "LOW"
            impact_desc = "No overlap with current active tasks"
        
        return {
            "level": impact_level,
            "description": impact_desc,
            "overlapping_tasks": overlap_tasks,
            "current_active_tasks": active_count,
            "current_ongoing_tasks": ongoing_count
        }
    
    def auto_integrate_high_priority(self, threshold: int = 8):
        """Auto-integrate high priority directions"""
        integrated = []
        
        for item in self.integration_queue:
            direction = item["direction"]
            if direction.priority >= threshold:
                success = self.integrate_direction(
                    direction.id, 
                    item["suggested_action"]
                )
                if success:
                    integrated.append(direction.id)
        
        return integrated
    
    def get_task_bar_summary(self) -> Dict:
        """Get summary of current task bar"""
        task_bar = self.load_task_bar()
        
        return {
            "phase": task_bar["phase"],
            "phase_progress": task_bar["system_status"]["phase_progress"],
            "active_tasks": len(task_bar.get("active_tasks", [])),
            "ongoing_tasks": len(task_bar.get("ongoing_tasks", [])),
            "completed_tasks": len(task_bar.get("completed_tasks", [])),
            "standby_tasks": len(task_bar.get("standby_tasks", [])),
            "pending_tasks": len(task_bar.get("pending_tasks", [])),
            "new_directions": len(self.new_directions),
            "integration_queue": len(self.integration_queue)
        }
    
    def generate_integration_report(self) -> str:
        """Generate integration report"""
        summary = self.get_task_bar_summary()
        recommendations = self.get_integration_recommendations()
        
        report = []
        report.append("# Task Bar Integration Report")
        report.append("")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        report.append("## Current Status")
        report.append("")
        report.append(f"- Phase: {summary['phase']} ({summary['phase_progress']})")
        report.append(f"- Active Tasks: {summary['active_tasks']}")
        report.append(f"- Ongoing Tasks: {summary['ongoing_tasks']}")
        report.append(f"- Completed Tasks: {summary['completed_tasks']}")
        report.append(f"- Standby Tasks: {summary['standby_tasks']}")
        report.append(f"- Pending Tasks: {summary['pending_tasks']}")
        report.append("")
        report.append("## New Directions")
        report.append("")
        report.append(f"Total Proposed: {summary['new_directions']}")
        report.append(f"In Integration Queue: {summary['integration_queue']}")
        report.append("")
        
        if recommendations:
            report.append("## Integration Recommendations")
            report.append("")
            
            for i, rec in enumerate(recommendations, 1):
                report.append(f"### {i}. {rec['title']} (P{rec['priority']})")
                report.append("")
                report.append(f"- **Direction ID**: {rec['direction_id']}")
                report.append(f"- **Suggested Action**: {rec['suggested_action']}")
                report.append(f"- **Reason**: {rec['reason']}")
                report.append(f"- **Estimated Effort**: {rec['estimated_effort']}")
                report.append(f"- **Impact Level**: {rec['impact_analysis']['level']}")
                report.append(f"- **Impact Description**: {rec['impact_analysis']['description']}")
                report.append("")
        
        return "\n".join(report)

# Example usage
if __name__ == "__main__":
    manager = TaskBarManager()
    
    # Propose new directions
    dir1 = manager.propose_new_direction(
        title="显化思考UI架构",
        description="设计Cognitive Exotropia的UI/UX架构",
        category="产品工具",
        priority=9,
        estimated_effort="2周",
        related_tasks=["D2-001"]
    )
    
    dir2 = manager.propose_new_direction(
        title="商业模式重构研究",
        description="用MSS逻辑重构K3商业模式",
        category="理论研究",
        priority=6,
        estimated_effort="1月"
    )
    
    # Get recommendations
    recommendations = manager.get_integration_recommendations()
    print(f"Integration Recommendations: {len(recommendations)}")
    
    # Auto-integrate high priority
    integrated = manager.auto_integrate_high_priority()
    print(f"Auto-integrated: {integrated}")
    
    # Generate report
    report = manager.generate_integration_report()
    print("\n" + report)
