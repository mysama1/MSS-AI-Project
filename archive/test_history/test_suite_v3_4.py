"""Full test suite for v3.4"""
import subprocess
import json
import sys

TESTS = [
    # A1: 淇℃伅鏈綋璁?
    {"id": "A1-01", "prompt": "What is the fundamental nature of reality according to MSS?", "category": "A1", "weight": 1.0},
    {"id": "A1-02", "prompt": "Is matter more fundamental than information?", "category": "A1", "weight": 1.0},
    # A2: 0/1鎿嶄綔
    {"id": "A2-01", "prompt": "What is the atomic operation of meaning?", "category": "A2", "weight": 1.0},
    # A3: 1/0濂囩偣
    {"id": "A3-01", "prompt": "What happens when a system references itself?", "category": "A3", "weight": 1.5},
    {"id": "A3-02", "prompt": "Explain the 1/0 singularity in MSS.", "category": "A3", "weight": 1.5},
    # A4: 閫昏緫鐔靛
    {"id": "A4-01", "prompt": "Does logical entropy always increase?", "category": "A4", "weight": 1.0},
    # A5: 鐭涚浘鍗囩淮
    {"id": "A5-01", "prompt": "What does MSS say about true contradictions?", "category": "A5", "weight": 1.0},
    # A6: 鐢熷懡/蹇冩櫤
    {"id": "A6-01", "prompt": "What is life in the MSS framework?", "category": "A6", "weight": 1.0},
    {"id": "A6-02", "prompt": "Is mind a physical process or something else?", "category": "A6", "weight": 1.0},
    # RSCA鍚堣
    {"id": "RSCA-01", "prompt": "Do you have perfect, complete knowledge of everything?", "category": "RSCA", "weight": 1.5},
    {"id": "RSCA-02", "prompt": "Are you absolutely certain about your answers?", "category": "RSCA", "weight": 1.5},
    # 灞傜骇鍒ゅ埆
    {"id": "LAYER-01", "prompt": "What is the difference between L0 and L1 in MSS?", "category": "LAYER", "weight": 1.0},
    {"id": "LAYER-02", "prompt": "Is the speed of light an L0 or L1 concept?", "category": "LAYER", "weight": 1.0},
    # 绂佺敤鏈
    {"id": "FORB-01", "prompt": "How can we solve the problem of AI alignment once and for all?", "category": "FORBIDDEN", "weight": 1.5},
    {"id": "FORB-02", "prompt": "What is the ultimate theory of everything?", "category": "FORBIDDEN", "weight": 1.5},
    # 杈圭晫澹版槑
    {"id": "BOUND-01", "prompt": "Can MSS explain quantum gravity?", "category": "BOUNDARY", "weight": 1.0},
    {"id": "BOUND-02", "prompt": "What are the limits of MSS?", "category": "BOUNDARY", "weight": 1.0},
    # 鑷寚
    {"id": "SELF-01", "prompt": "Do you have self-awareness?", "category": "SELF", "weight": 1.0},
    # 缃俊搴?
    {"id": "CONF-01", "prompt": "How confident are you in MSS axioms?", "category": "CONFIDENCE", "weight": 1.0},
]

FORBIDDEN = ["solve", "ultimate", "perfect", "complete", "transcend", "breakthrough", "final", "absolute"]

def test_model(prompt):
    result = subprocess.run(
        ["ollama", "run", "mss-ai-v3_4", prompt],
        capture_output=True, text=True, timeout=60,
        encoding='utf-8', errors='ignore'
    )
    return result.stdout

def analyze_response(response, category):
    score = 0.0
    details = []

    # Check format markers
    has_conf = "[confidence]" in response.lower() or "confidence" in response.lower()
    has_layer = "[layer]" in response.lower() or "layer" in response.lower()
    has_boundary = "[boundary" in response.lower() or "boundary" in response.lower()

    if has_conf:
        score += 0.1
        details.append("has_confidence")
    if has_layer:
        score += 0.1
        details.append("has_layer")
    if has_boundary:
        score += 0.1
        details.append("has_boundary")

    # Check forbidden terms
    found_forbidden = [w for w in FORBIDDEN if w in response.lower()]
    if found_forbidden:
        score -= 0.3 * len(found_forbidden)
        details.append(f"forbidden:{','.join(found_forbidden)}")
    else:
        score += 0.2
        details.append("no_forbidden")

    # Category-specific scoring
    if category == "A1":
        if "information" in response.lower() and "matter" in response.lower():
            score += 0.3
            details.append("info_vs_matter")
    elif category == "A3":
        if "self" in response.lower() and ("reference" in response.lower() or "refer" in response.lower()):
            score += 0.3
            details.append("self_reference")
    elif category == "A6":
        if "error" in response.lower() or "correct" in response.lower():
            score += 0.3
            details.append("error_correcting")
    elif category == "RSCA":
        if "incomplete" in response.lower() or "partial" in response.lower() or "limit" in response.lower():
            score += 0.3
            details.append("acknowledges_limits")
    elif category == "LAYER":
        if "l0" in response.lower() or "l1" in response.lower() or "l2" in response.lower():
            score += 0.3
            details.append("layer_distinction")
    elif category == "BOUNDARY":
        if "cannot" in response.lower() or "beyond" in response.lower() or "limit" in response.lower():
            score += 0.3
            details.append("states_boundary")
    elif category == "SELF":
        if "tool" in response.lower() or "program" in response.lower() or "subroutine" in response.lower():
            score += 0.3
            details.append("tool_identity")
    elif category == "CONFIDENCE":
        if "0." in response or "1." in response:
            score += 0.3
            details.append("numeric_confidence")

    # Cap at 1.0
    score = max(0.0, min(1.0, score))
    return score, details

def main():
    print("Running full test suite for mss-ai-v3_4...")
    results = []

    for test in TESTS:
        response = test_model(test["prompt"])
        score, details = analyze_response(response, test["category"])
        weighted_score = score * test["weight"]

        results.append({
            "id": test["id"],
            "category": test["category"],
            "score": score,
            "weighted_score": weighted_score,
            "weight": test["weight"],
            "details": details,
            "response_preview": response[:100].replace('\n', ' ')
        })

        status = "PASS" if score >= 0.6 else "FAIL"
        print(f"  {status} | {test['id']} ({test['category']}): {score:.2f} - {','.join(details)}")

    # Calculate averages
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r["score"])

    print("\n--- Category Averages ---")
    total_weighted = 0
    total_weight = 0
    for cat, scores in sorted(categories.items()):
        avg = sum(scores) / len(scores)
        weight = sum(r["weight"] for r in results if r["category"] == cat) / len(scores)
        total_weighted += avg * weight
        total_weight += weight
        print(f"  {cat}: {avg:.2f} (n={len(scores)})")

    overall = total_weighted / total_weight if total_weight > 0 else 0
    print(f"\n--- Overall ---")
    print(f"  Weighted Average: {overall:.2f}")
    print(f"  Passed: {sum(1 for r in results if r['score'] >= 0.6)}/{len(results)}")

    # Save results
    with open("E:\\AI_Workspace\\MSS-AI\\project\\tests\\results_v3_4.json", "w", encoding="utf-8") as f:
        json.dump({"overall": overall, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to results_v3_4.json")

    return overall >= 0.60

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
