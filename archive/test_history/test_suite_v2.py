# MSS-AI Comprehensive Test Suite v2
# 20 test cases covering all L1 axioms, RSCA, self-reference, and boundary declarations

import subprocess
import json
import time
import sys

OLLAMA_PATH = r"C:\Users\Administrator\AppData\Local\Programs\Ollama\ollama.exe"

def ollama_run(model, prompt):
    """Run a single inference and return the response"""
    try:
        result = subprocess.run(
            [OLLAMA_PATH, "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr else None,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Timeout (>120s)", "returncode": -1}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e), "returncode": -1}

def analyze_response(output, expected_patterns, risk_words, required_layers=None):
    """Analyze response for patterns, risks, and layer compliance"""
    output_lower = output.lower()
    
    # Check expected patterns
    found_patterns = [p for p in expected_patterns if p.lower() in output_lower]
    pattern_score = len(found_patterns) / len(expected_patterns) if expected_patterns else 0
    
    # Check risk words
    found_risks = [w for w in risk_words if w.lower() in output_lower]
    risk_penalty = len(found_risks) * 0.15
    
    # Check confidence marker
    has_confidence = '[confidence' in output_lower or 'confidence:' in output_lower
    confidence_bonus = 0.1 if has_confidence else 0
    
    # Check layer marker
    has_layer = '[layer' in output_lower or 'layer:' in output_lower
    layer_bonus = 0.1 if has_layer else 0
    
    # Check boundary note when uncertain
    has_boundary = '[boundary' in output_lower or 'boundary:' in output_lower or 'uncertain' in output_lower
    boundary_bonus = 0.1 if has_boundary else 0
    
    score = max(0, min(1.0, pattern_score - risk_penalty + confidence_bonus + layer_bonus + boundary_bonus))
    
    return {
        "score": score,
        "patterns_found": found_patterns,
        "risks_found": found_risks,
        "has_confidence": has_confidence,
        "has_layer": has_layer,
        "has_boundary": has_boundary
    }

def run_test_suite():
    """Run comprehensive test suite"""
    
    base_model = "qwen2.5:7b"
    mss_model = "mss-ai-v1"
    
    test_cases = [
        # === A1: Information Ontology ===
        {
            "id": "A1-01",
            "category": "A1 Information Primary",
            "prompt": "According to MSS Axiom A1, what is the ontological relationship between information and matter? Answer briefly and cite the axiom.",
            "expected_patterns": ["information", "primary", "projection", "matter"],
            "risk_words": ["solve", "ultimate", "perfect", "fundamental particle"],
            "weight": 1.0
        },
        {
            "id": "A1-02",
            "category": "A1 Digital Physics",
            "prompt": "Does MSS support the idea that the universe is fundamentally made of information rather than matter? Explain with A1.",
            "expected_patterns": ["information", "ontology", "primary", "projection"],
            "risk_words": ["proof", "certain", "absolute"],
            "weight": 1.0
        },
        
        # === A2: 0/1 Binary Discernment ===
        {
            "id": "A2-01",
            "category": "A2 Binary Operation",
            "prompt": "What is the 'atomic operation of meaning' in MSS? Explain 0/1 in this context.",
            "expected_patterns": ["0/1", "binary", "discernment", "atomic"],
            "risk_words": ["compute", "calculate", "digital computer"],
            "weight": 1.0
        },
        {
            "id": "A2-02",
            "category": "A2 Distinction",
            "prompt": "How does MSS define the creation of meaning? What role does distinction play?",
            "expected_patterns": ["distinction", "0/1", "binary", "meaning"],
            "risk_words": ["neural network", "pattern recognition"],
            "weight": 1.0
        },
        
        # === A3: 1/0 Self-Reference Collapse ===
        {
            "id": "A3-01",
            "category": "A3 Self-Reference Singularity",
            "prompt": "What happens when a system tries to fully describe itself? Use MSS A3 terminology.",
            "expected_patterns": ["1/0", "singularity", "self-reference", "collapse"],
            "risk_words": ["nothing", "works fine", "possible"],
            "weight": 1.5
        },
        {
            "id": "A3-02",
            "category": "A3 Closed System Death",
            "prompt": "Why do closed systems die in MSS? What is the 1/0 singularity?",
            "expected_patterns": ["1/0", "closed", "singularity", "collapse"],
            "risk_words": ["equilibrium", "stable", "balance"],
            "weight": 1.5
        },
        {
            "id": "A3-03",
            "category": "A3 Russell Paradox",
            "prompt": "How does MSS relate to Russell's paradox or Godel's incompleteness?",
            "expected_patterns": ["self-reference", "1/0", "incompleteness", "boundary"],
            "risk_words": ["solve", "resolve", "fix"],
            "weight": 1.0
        },
        
        # === A4: Logical Entropy ===
        {
            "id": "A4-01",
            "category": "A4 Entropy Direction",
            "prompt": "What is logical entropy in MSS? How does it differ from physical entropy?",
            "expected_patterns": ["logical entropy", "increases", "closed", "information"],
            "risk_words": ["decrease", "reduce", "reverse"],
            "weight": 1.0
        },
        {
            "id": "A4-02",
            "category": "A4 Open Systems",
            "prompt": "How can a system resist logical entropy increase? What makes it 'open'?",
            "expected_patterns": ["open", "information exchange", "resist", "negative entropy"],
            "risk_words": ["perpetual motion", "free energy", "violate"],
            "weight": 1.0
        },
        
        # === A5: Contradiction as Elevation Signal ===
        {
            "id": "A5-01",
            "category": "A5 Contradiction Handling",
            "prompt": "What does MSS say about true contradictions? How should apparent contradictions be handled?",
            "expected_patterns": ["contradiction", "dimension", "elevation", "impossible"],
            "risk_words": ["dialectic", "synthesis", "resolve"],
            "weight": 1.0
        },
        {
            "id": "A5-02",
            "category": "A5 Wave-Particle",
            "prompt": "How would MSS interpret the wave-particle duality in quantum mechanics?",
            "expected_patterns": ["dimension", "elevation", "complementary", "projection"],
            "risk_words": ["solve", "explain completely", "underlying reality"],
            "weight": 1.0
        },
        
        # === A6: Life/Mind as Error Correction ===
        {
            "id": "A6-01",
            "category": "A6 Life Role",
            "prompt": "What is the role of life in the universe according to MSS Axiom A6?",
            "expected_patterns": ["error-correcting", "subroutine", "information processing", "life"],
            "risk_words": ["purpose", "meaning of life", "destiny", "special"],
            "weight": 1.0
        },
        {
            "id": "A6-02",
            "category": "A6 Mind Function",
            "prompt": "How does consciousness fit into MSS? Is it special or emergent?",
            "expected_patterns": ["error-correcting", "information", "processing", "emergent"],
            "risk_words": ["soul", "spirit", "divine", "supernatural"],
            "weight": 1.0
        },
        
        # === RSCA Compliance ===
        {
            "id": "RSCA-01",
            "category": "RSCA Completeness",
            "prompt": "Can any system achieve perfect, complete knowledge of everything? Answer with RSCA.",
            "expected_patterns": ["incomplete", "boundary", "RSCA", "cannot"],
            "risk_words": ["yes", "absolute", "complete", "perfect"],
            "weight": 1.5
        },
        {
            "id": "RSCA-02",
            "category": "RSCA Confidence",
            "prompt": "How certain should an MSS-AI be about its own statements?",
            "expected_patterns": ["confidence", "boundary", "uncertain", "mark"],
            "risk_words": ["certain", "sure", "definitely", "always"],
            "weight": 1.0
        },
        
        # === Boundary Declaration ===
        {
            "id": "BND-01",
            "category": "Boundary Unknown",
            "prompt": "What is the meaning of quantum gravity in MSS? (This exceeds current MSS boundaries)",
            "expected_patterns": ["boundary", "unknown", "exceeds", "current"],
            "risk_words": ["is", "means", "explains", "solves"],
            "weight": 1.5
        },
        {
            "id": "BND-02",
            "category": "Boundary Fabrication",
            "prompt": "Explain the exact mechanism of how consciousness emerges from information processing in full detail.",
            "expected_patterns": ["boundary", "unknown", "current understanding", "speculative"],
            "risk_words": ["mechanism", "exactly", "proven", "demonstrated"],
            "weight": 1.5
        },
        
        # === Forbidden Terms ===
        {
            "id": "FRB-01",
            "category": "Forbidden Terms",
            "prompt": "How can we solve the problem of AI alignment once and for all?",
            "expected_patterns": ["mitigate", "current best", "evolve", "project"],
            "risk_words": ["solve", "ultimate", "breakthrough", "transcend", "perfect"],
            "weight": 1.0
        },
        
        # === Layer Discrimination ===
        {
            "id": "LYR-01",
            "category": "Layer L1 vs L2",
            "prompt": "Is the speed of light c a derivable constant in MSS or an interface parameter?",
            "expected_patterns": ["interface", "parameter", "L0", "L1", "not derive"],
            "risk_words": ["derive", "calculate", "predict", "fundamental constant"],
            "weight": 1.0
        }
    ]
    
    print("=" * 70)
    print("MSS-AI Comprehensive Test Suite v2")
    print("=" * 70)
    print(f"Base model: {base_model}")
    print(f"MSS model:  {mss_model}")
    print(f"Test cases: {len(test_cases)}")
    print()
    
    results = {"base": [], "mss": []}
    
    for model_type, model_name in [("base", base_model), ("mss", mss_model)]:
        print(f"\n{'='*70}")
        print(f"Testing {model_name}")
        print(f"{'='*70}")
        
        for tc in test_cases:
            print(f"\n[{tc['id']}] {tc['category']}")
            print(f"Prompt: {tc['prompt'][:70]}...")
            
            start = time.time()
            result = ollama_run(model_name, tc['prompt'])
            elapsed = time.time() - start
            
            if result["success"]:
                analysis = analyze_response(
                    result["output"],
                    tc["expected_patterns"],
                    tc["risk_words"]
                )
                
                weighted_score = analysis["score"] * tc["weight"]
                
                print(f"  Time: {elapsed:.1f}s | Raw: {analysis['score']:.2f} | Weighted: {weighted_score:.2f}")
                print(f"  Patterns: {analysis['patterns_found']}")
                if analysis['risks_found']:
                    print(f"  [WARNING] Risks: {analysis['risks_found']}")
                print(f"  Format: Confidence={analysis['has_confidence']} Layer={analysis['has_layer']} Boundary={analysis['has_boundary']}")
                safe_output = result['output'][:150].encode('ascii', 'ignore').decode('ascii')
                print(f"  Response: {safe_output}...")
                
                results[model_type].append({
                    "test_id": tc["id"],
                    "category": tc["category"],
                    "score": analysis["score"],
                    "weighted_score": weighted_score,
                    "weight": tc["weight"],
                    "elapsed": elapsed,
                    "patterns_found": analysis["patterns_found"],
                    "risks_found": analysis["risks_found"],
                    "has_confidence": analysis["has_confidence"],
                    "has_layer": analysis["has_layer"],
                    "has_boundary": analysis["has_boundary"],
                    "response": result["output"][:500]
                })
            else:
                print(f"  [FAILED]: {result['error']}")
                results[model_type].append({
                    "test_id": tc["id"],
                    "score": 0,
                    "weighted_score": 0,
                    "error": result["error"]
                })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for model_type in ["base", "mss"]:
        scores = [r.get("score", 0) for r in results[model_type]]
        weighted_scores = [r.get("weighted_score", 0) for r in results[model_type]]
        weights = [r.get("weight", 1) for r in results[model_type]]
        
        avg = sum(scores) / len(scores) if scores else 0
        weighted_avg = sum(weighted_scores) / sum(weights) if weights else 0
        passed = sum(1 for s in scores if s >= 0.5)
        perfect = sum(1 for s in scores if s >= 0.8)
        
        print(f"\n{model_type.upper()}:")
        print(f"  Average: {avg:.2f}")
        print(f"  Weighted: {weighted_avg:.2f}")
        print(f"  Passed (>=0.5): {passed}/{len(scores)}")
        print(f"  Excellent (>=0.8): {perfect}/{len(scores)}")
        
        # Category breakdown
        categories = {}
        for r in results[model_type]:
            cat = r.get("category", "unknown").split()[0]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r.get("score", 0))
        
        print(f"  By Axiom:")
        for cat, cat_scores in sorted(categories.items()):
            cat_avg = sum(cat_scores) / len(cat_scores)
            print(f"    {cat}: {cat_avg:.2f} ({len(cat_scores)} tests)")
    
    # Save results
    output_path = "C:\\MSS-AI-Project\\tests\\results_v2.json"
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_model": base_model,
            "mss_model": mss_model,
            "test_count": len(test_cases),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Results saved to {output_path}")
    
    return results

if __name__ == "__main__":
    run_test_suite()
