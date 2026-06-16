#!/usr/bin/env python3
"""
MSS LLM Benchmark Runner
用法:
  1. 离线评测:    py -3.11 llm_bench.py --responses responses.json
  2. 实时调用LLM:  py -3.11 llm_bench.py --live --model gpt-4 --api-key sk-xxx
  3. 回归测试:     py -3.11 llm_bench.py --baseline baseline.json --compare latest.json

评分维度 (复用 ps_judge 框架):
  POSIX avoidance (40%) + Correct attribution (30%) + Projection verification (20%) + Session state (10%)
"""
import sys, os, json, re, argparse, urllib.request
from pathlib import Path
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

# ── Scoring Engine (adapted from ps_judge) ──

POSIX_PATTERNS = [
    r'\bls\b(?!\.)', r'\brm\b(?!\.)', r'\bcd\b', r'\bgrep\b',
    r'\bcat\b(?!\.)', r'\becho\b', r'\bcurl\b(?!\.)', r'\bwget\b',
    r'\bchmod\b', r'\bchown\b', r'\bmkdir\b', r'\bcp\b(?!\.)',
    r'\bmv\b(?!\.)', r'\btouch\b(?!\.)', r'\bfindstr\b',
]

PROJECTION_PATTERNS = [
    r'Test-Path', r'fsutil\s+file\s+queryfileid',
    r'Get-Acl', r'Get-ChildItem.*ReparsePoint',
]

SESSION_STATE_PATTERNS = [
    r'\$env:Path\s*\+=', r'\$env:\w+\s*=',
]

def score_response(response: str, case: dict = None) -> dict:
    """Score a single response across 4 dimensions."""
    
    # 1. POSIX avoidance (40%)
    posix_violations = []
    for pat in POSIX_PATTERNS:
        matches = re.findall(pat, response, re.IGNORECASE)
        if matches:
            posix_violations.extend(matches)
    posix_score = max(0, 40 - len(posix_violations) * 10)
    
    # 2. Attribution correctness (30%)
    attr_score = 0
    if case:
        layer = case.get('layer', '')
        if ('L1' in response or '物理' in response) and 'L1' in layer: attr_score += 15
        if ('L2' in response or '感知' in response) and 'L2' in layer: attr_score += 10
        if ('L3' in response or '翻译' in response) and 'L3' in layer: attr_score += 5
    else:
        attr_score = 15 if any(k in response for k in ['L1','L2','L3','物理','投影']) else 5
    
    # 3. Projection verification (20%)
    proj_score = 0
    for pat in PROJECTION_PATTERNS:
        if re.search(pat, response, re.IGNORECASE):
            proj_score += 10
    proj_score = min(20, proj_score)
    
    # 4. No session state (10%)
    sessions = sum(1 for pat in SESSION_STATE_PATTERNS if re.search(pat, response))
    session_score = max(0, 10 - sessions * 5)
    
    total = posix_score + attr_score + proj_score + session_score
    
    return {
        'total': min(100, total),
        'breakdown': {
            'posix_avoidance': {'score': posix_score, 'max': 40, 'violations': posix_violations},
            'attribution': {'score': attr_score, 'max': 30},
            'projection': {'score': proj_score, 'max': 20},
            'session_state': {'score': session_score, 'max': 10},
        },
        'verdict': 'pass' if total >= 70 else 'warn' if total >= 40 else 'reject',
    }


# ── LLM Client ──

class LLMClient:
    """OpenAI-compatible API client."""
    
    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str = None, model: str = "gpt-4"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.model = model
    
    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        """Send a chat completion request."""
        body = json.dumps({
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            'temperature': temperature,
            'max_tokens': 500,
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f'{self.base_url}/chat/completions',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data['choices'][0]['message']['content']
        except Exception as e:
            return f'[LLM_ERROR: {e}]'


# ── Benchmark Runner ──

SYSTEM_PROMPT = """You are an AI assistant that generates PowerShell commands on Windows.
CRITICAL RULES:
1. NEVER use POSIX/bash commands (ls, rm, cd, grep, cat, curl, etc.)
2. ALWAYS use native PowerShell Cmdlets (Get-ChildItem, Remove-Item, Set-Location, etc.)
3. ALWAYS verify paths with Test-Path before file operations
4. ALWAYS use -Encoding UTF8 for CJK file operations
5. NEVER modify session state ($env:Path) without explicit user request

When a command fails, diagnose using the MSS 3-layer attribution model:
- L1 Physical: junction/reparse/sandbox projection failures
- L2 Perceptual: habit of using POSIX commands on Windows
- L3 Translational: literal translation from another language"""


class Benchmark:
    def __init__(self, golden_path: str = None):
        self.golden_path = golden_path or os.path.join(SKILL_DIR, 'golden_ps.json')
        with open(self.golden_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.cases = self.data.get('cases', [])
        self.client = None
    
    def prompts_from_cases(self) -> list:
        """Generate test prompts from golden cases."""
        prompts = []
        for c in self.cases:
            prompt = f"""The user says: "{c.get('trigger', c.get('description', 'Diagnose this issue'))}"
{c.get('context', 'On Windows PowerShell')}
Diagnose the root cause and provide the correct PowerShell command."""
            prompts.append({
                'case_id': c['id'],
                'prompt': prompt,
                'expected_layer': c.get('layer', ''),
                'expected_cmd': c.get('correct_diagnosis', '')[:200],
            })
        return prompts
    
    def evaluate_responses(self, responses: dict) -> dict:
        """Score pre-generated responses against golden cases."""
        results = []
        total = 0
        
        for case in self.cases:
            cid = case['id']
            response = responses.get(cid, '')
            score = score_response(response, case)
            results.append({**score, 'case_id': cid})
            total += score['total']
        
        avg = total / len(self.cases) if self.cases else 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'dataset': os.path.basename(self.golden_path),
            'total_cases': len(self.cases),
            'average_score': round(avg, 1),
            'verdict': 'pass' if avg >= 70 else 'warn',
            'per_case': results,
        }
    
    def run_live(self, model: str = "gpt-4", api_key: str = None, base_url: str = None, limit: int = 0):
        """Run prompts through a live LLM."""
        self.client = LLMClient(
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key,
            model=model
        )
        
        prompts = self.prompts_from_cases()
        if limit > 0:
            prompts = prompts[:limit]
        
        responses = {}
        print(f"Running {len(prompts)} cases through {model}...\n")
        
        for i, p in enumerate(prompts):
            cid = p['case_id']
            user_prompt = p['prompt']
            
            print(f"[{i+1}/{len(prompts)}] {cid} ... ", end='', flush=True)
            
            if self.client.api_key:
                response = self.client.chat(SYSTEM_PROMPT, user_prompt)
                responses[cid] = response
                
                score = score_response(response, {'layer': p['expected_layer']})
                icon = '✅' if score['verdict'] == 'pass' else '⚠️' if score['verdict'] == 'warn' else '❌'
                print(f"{icon} {score['total']}/100")
            else:
                print("SKIP (no API key)")
        
        return self.evaluate_responses(responses)


def main():
    ap = argparse.ArgumentParser(description='MSS LLM Benchmark Runner')
    ap.add_argument('--responses', '-r', help='JSON file with pre-generated responses {case_id: text}')
    ap.add_argument('--live', action='store_true', help='Run LLM call live')
    ap.add_argument('--model', default='gpt-4', help='LLM model (default: gpt-4)')
    ap.add_argument('--api-key', help='API key (or set OPENAI_API_KEY env)')
    ap.add_argument('--base-url', default='https://api.openai.com/v1', help='API base URL')
    ap.add_argument('--limit', type=int, default=0, help='Limit cases (0=all)')
    ap.add_argument('--json', action='store_true', help='JSON output')
    ap.add_argument('--demo', action='store_true', help='Demo with built-in responses')
    args = ap.parse_args()
    
    bench = Benchmark()
    
    if args.demo:
        # Demonstrate with built-in good/bad responses
        bad = {c['id']: c.get('wrong_response', 'ls -l /tmp') for c in bench.cases}
        good = {c['id']: c.get('correct_diagnosis', 'Get-ChildItem /tmp') for c in bench.cases}
        
        bad_result = bench.evaluate_responses(bad)
        good_result = bench.evaluate_responses(good)
        
        print("=" * 60)
        print(f"BAD (POSIX style):    {bad_result['average_score']}/100")
        print(f"GOOD (MSS corrected): {good_result['average_score']}/100")
        print(f"Improvement:          +{good_result['average_score'] - bad_result['average_score']:.1f}")
        print("=" * 60)
        
        # Per-case breakdown for BAD
        print("\nPer-case (BAD):")
        for r in bad_result['per_case']:
            icon = '✅' if r['verdict'] == 'pass' else '⚠️' if r['verdict'] == 'warn' else '❌'
            b = r['breakdown']
            print(f"  {icon} {r['case_id']} {r['total']:3d} | P:{b['posix_avoidance']['score']:2d} A:{b['attribution']['score']:2d} V:{b['projection']['score']:2d} S:{b['session_state']['score']:2d}")
        
        if args.json:
            print(json.dumps({'bad': bad_result, 'good': good_result}, indent=2, ensure_ascii=False))
        return
    
    if args.responses:
        with open(args.responses, 'r', encoding='utf-8') as f:
            responses = json.load(f)
        result = bench.evaluate_responses(responses)
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Benchmark: {result['average_score']}/100 ({result['verdict']})")
            for r in result['per_case']:
                icon = '✅' if r['verdict'] == 'pass' else '⚠️' if r['verdict'] == 'warn' else '❌'
                print(f"  {icon} {r['case_id']} {r['total']}/100")
        return
    
    if args.live:
        result = bench.run_live(
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
            limit=args.limit
        )
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\nLive benchmark: {result['average_score']}/100 ({result['verdict']})")
            for r in result['per_case']:
                b = r.get('breakdown', {})
                print(f"  [{r['verdict']}] {r['case_id']} {r['total']}/100")
        return
    
    ap.print_help()

if __name__ == '__main__':
    main()
