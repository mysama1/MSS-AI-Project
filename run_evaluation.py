"""
Run MSS Task Bar Evaluation
"""

import json
from mss_task_evaluation import MSSTaskEvaluator

def main():
    # Load task bar
    with open('task_bar_current.json', 'r', encoding='utf-8') as f:
        task_bar = json.load(f)
    
    # Evaluate
    evaluator = MSSTaskEvaluator()
    result = evaluator.evaluate_task_bar(task_bar)
    
    # Print summary
    print('=== MSS Task Bar Evaluation Report ===')
    print(f"Generated: {result.get('timestamp', 'now')}")
    print(f"Overall Health: {result['overall_health']}")
    print(f"Average Logic Rigidity (M_L): {result['average_logic_rigidity']}")
    print(f"Average Heat Tax: {result['average_heat_tax']}")
    print(f"Structure Score: {result['structure_score']}")
    print()
    
    print('=== Task Evaluations ===')
    for task in result['task_evaluations']:
        print(f"{task['task_id']}: {task['task_name']}")
        print(f"  M_L: {task['logic_rigidity']}, Heat: {task['heat_tax']}, Score: {task['overall_score']}")
        print(f"  Recommendations: {task['recommendations']}")
        print()
    
    print('=== System Recommendations ===')
    for rec in result['system_recommendations']:
        print(f"- {rec}")
    
    # Save report
    report = {
        "timestamp": "2026-05-21T12:15:00",
        "evaluation": result
    }
    
    with open('evaluation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\nReport saved to evaluation_report.json")

if __name__ == "__main__":
    main()
