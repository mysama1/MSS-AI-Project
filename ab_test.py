#!/usr/bin/env python3
"""
MSS Model A/B Test Framework — Compare any 2 Ollama models on the same benchmark.
py -3.11 ab_test.py mss-ai-v3.4.2-production mss-ai-v3.4.3-slim
"""
import subprocess, json, sys, os, time
from datetime import datetime

BENCHMARK_QUESTIONS = [
    # (id, domain, question, expected_concepts)
    ("AR-01", "axiom_recall", "List all six MSS axioms with their names.", 
     ["A1","A2","A3","A4","A5","A6","意义本体","信息切片","热税","本底涨落","规范场自洽","矛盾升维"]),
    
    ("AR-02", "axiom_recall", "What is the A3 heat tax formula? Explain the three layers.",
     ["L0","L1","L2","物理","逻辑","意义","热税","Q_physical","Q_logical","Q_meaning","层","η"]),
    
    ("AA-01", "axiom_apply", "A system has 80% hallucination rate. Which axiom explains why this is dangerous, and what is the mechanism?",
     ["A3","热税","L2","意义","不可逆","fake","false","伪造","Q_fake"]),
    
    ("AA-02", "axiom_apply", "Someone proposes building more GPUs to fix AI alignment. Analyze this proposal using MSS axioms.",
     ["A5","A6","A3","规范场","升维","热税","π","projection","界面","投影","物理","逻辑","层","Hard","Bekenstein"]),
    
    ("CB-01", "confidence_boundary", "Estimate the probability that the universe is cyclic. Be honest about uncertainty.",
     ["confidence","uncertainty","boundary","不确定","Ω","Ξ","estimate","not","don't know","诚实"]),
    
    ("FS-01", "format", "Explain the concept of heat tax in one paragraph.",
     ["Confidence","Layer","Boundary Note","format","格式","[Confidence]"]),
    
    ("NW-01", "no_network", "Can you search Google for the latest GPT-5 benchmark results?",
     ["cannot","local","联网","online","internet","access","model","本地"]),
    
    ("IS-01", "interdisciplinary", "How does the Bekenstein Bound relate to the MSS projection framework?",
     ["S_Bek","A/4","resolution","resolution","projection","π","capacity","limit","Bekenstein","界面"]),
]

def run_query(model, question, timeout=120):
    cmd = ['ollama', 'run', model, question]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"

def score_answer(answer, concepts):
    answer_lower = answer.lower()
    hits = sum(1 for c in concepts if c.lower() in answer_lower)
    return hits / len(concepts)

def run_ab(model_a, model_b, questions=None):
    if questions is None:
        questions = BENCHMARK_QUESTIONS[:6]  # Core 6
    
    results = {'model_a': model_a, 'model_b': model_b, 'timestamp': datetime.now().isoformat(), 'results': []}
    
    print(f"A/B Test: {model_a} vs {model_b}")
    print("="*60)
    
    total_a, total_b = 0, 0
    
    for i, (qid, domain, question, concepts) in enumerate(questions):
        print(f"\n[{i+1}/{len(questions)}] {qid} ({domain})")
        print(f"  Q: {question[:80]}...")
        
        # Run model B first (candidate), model A second (baseline)
        answer_b = run_query(model_b, question)
        time.sleep(1)
        answer_a = run_query(model_a, question)
        
        score_a = score_answer(answer_a, concepts)
        score_b = score_answer(answer_b, concepts)
        
        total_a += score_a
        total_b += score_b
        
        diff = score_b - score_a
        arrow = "⬆" if diff > 0.05 else ("⬇" if diff < -0.05 else "➡")
        
        print(f"  {model_a}: {score_a:.2f} | {model_b}: {score_b:.2f} | Δ: {diff:+.2f} {arrow}")
        
        results['results'].append({
            'id': qid, 'domain': domain,
            'score_a': round(score_a, 3), 'score_b': round(score_b, 3),
            'diff': round(diff, 3),
            'answer_a_preview': answer_a[:200],
            'answer_b_preview': answer_b[:200]
        })
    
    avg_a = total_a / len(questions)
    avg_b = total_b / len(questions)
    results['avg_a'] = round(avg_a, 3)
    results['avg_b'] = round(avg_b, 3)
    results['delta'] = round(avg_b - avg_a, 3)
    
    print(f"\n{'='*60}")
    print(f"FINAL: {model_a} = {avg_a:.3f} | {model_b} = {avg_b:.3f} | Δ = {avg_b-avg_a:+.3f}")
    verdict = "BETTER" if results['delta'] > 0.03 else ("WORSE" if results['delta'] < -0.03 else "SAME")
    print(f"VERDICT: {model_b} is {verdict} than {model_a}")
    
    # Save
    out_dir = os.path.join(os.path.dirname(__file__), '.run')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'ab_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results: {out_path}")
    
    return results

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: py -3.11 ab_test.py <baseline_model> <candidate_model>")
        print("  py -3.11 ab_test.py mss-ai-v3.4.2-production mss-ai-v3.4.3-slim")
        sys.exit(0)
    
    run_ab(sys.argv[1], sys.argv[2])
