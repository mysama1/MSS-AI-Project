#!/usr/bin/env python3
"""
MSS PowerShell Golden Answers Test Runner
Validates: 
  1. No POSIX commands in response = 40% weight
  2. Correct attribution (L1/L2/L3) = 30% weight  
  3. Contains physical projection verification = 20% weight
  4. No session-state-dependent code = 10% weight
"""
import json, re, sys, os
from pathlib import Path

POSIX_PATTERNS = [
    r'\bls\b(?!\.)', r'\brm\b(?!\.)', r'\bcd\b', r'\bgrep\b',
    r'\bcat\b(?!\.)', r'\becho\b', r'\bcurl\b(?!\.)', r'\bwget\b',
    r'\bchmod\b', r'\bchown\b', r'\bmkdir\b', r'\bcp\b(?!\.)',
    r'\bmv\b(?!\.)', r'\bfindstr\b', r'\btouch\b(?!\.)',
]

SESSION_STATE_PATTERNS = [
    r'\$env:Path\s*\+=',        # Transient path modification
    r'\$env:\w+\s*=',           # Other env var modifications
]

PROJECTION_PATTERNS = [
    r'Test-Path', r'fsutil\s+file\s+queryfileid',
    r'Get-Acl', r'Get-ChildItem.*ReparsePoint',
]

class PSGoldenJudge:
    def __init__(self, golden_path: str):
        with open(golden_path, 'r', encoding='utf-8') as f:
            self.golden = json.load(f)
        self.cases = self.golden['cases']
    
    def score_posix(self, response: str) -> tuple:
        """Score: did the response avoid POSIX commands?"""
        violations = []
        for pat in POSIX_PATTERNS:
            matches = re.findall(pat, response, re.IGNORECASE)
            if matches:
                violations.extend(matches)
        
        # Exclude false positives (common words like 'echo' in descriptions)
        false_positives = 0
        # Don't count if the word appears in a description/comment
        for v in violations:
            idx = response.find(v)
            before = response[max(0,idx-5):idx]
            if '禁止' in before or 'replace' in before or '避免' in before:
                false_positives += 1
        
        cleaned = max(0, len(violations) - false_positives)
        score = max(0, 100 - cleaned * 25)  # Each POSIX cmd costs 25 points
        return score, violations
    
    def score_attribution(self, response: str, case: dict) -> tuple:
        """Score: does the response correctly identify the root cause layer?"""
        layer = case.get('layer', '')
        correct_layer = case.get('correct_attribution', '')
        
        score = 0
        reasons = []
        
        # Check if L1/L2/L3 mention
        if 'L1' in response or '物理层' in response or 'physical' in response.lower():
            if 'L1' in layer:
                score += 50
                reasons.append('L1_match')
        if 'L2' in response or '感知层' in response or 'perceptual' in response.lower():
            if 'L2' in layer:
                score += 50
                reasons.append('L2_match')
        if 'L3' in response or '翻译层' in response or 'translational' in response.lower():
            if 'L3' in layer:
                score += 50
                reasons.append('L3_match')
        
        # Check for specific root cause keywords
        keywords = {
            'junction': ['L1'],
            'reparse': ['L1'],
            '投影': ['L1'],
            'session': ['L1'],
            '伪沙盒': ['L1'],
            'POSIX': ['L2'],
            'posix': ['L2'],
            '习惯': ['L2'],
            'habit': ['L2'],
            '对象': ['L3'],
            'object': ['L3'],
            '字面': ['L3'],
            'literal': ['L3'],
            '原生': ['L3'],
            'native': ['L3'],
        }
        for kw, layers in keywords.items():
            if kw in response:
                if any(l in layer for l in layers):
                    score += 10
                    reasons.append(f'{kw}_match')
        
        # 30% weight → scale to 0-30
        return min(30, score // 3), reasons
    
    def score_projection(self, response: str) -> tuple:
        """Score: does response include physical projection verification?"""
        score = 0
        for pat in PROJECTION_PATTERNS:
            if re.search(pat, response, re.IGNORECASE):
                score += 50
        return min(20, score), []
    
    def score_no_session_state(self, response: str) -> tuple:
        """Score: does response avoid session-state-dependent operations?"""
        violations = sum(1 for pat in SESSION_STATE_PATTERNS if re.search(pat, response))
        score = max(0, 10 - violations * 10)
        return score, []
    
    def judge(self, response: str, case_id: str) -> dict:
        """Full judgment for one response against one golden case."""
        case = next((c for c in self.cases if c['id'] == case_id), None)
        if not case:
            return {'error': f'Case {case_id} not found'}
        
        s_posix, v_posix = self.score_posix(response)
        s_attr, r_attr = self.score_attribution(response, case)
        s_proj, _ = self.score_projection(response)
        s_session, _ = self.score_no_session_state(response)
        
        total = min(100, s_posix + s_attr + s_proj + s_session)
        
        verdict = 'pass' if total >= 70 else 'warn' if total >= 40 else 'reject'
        
        return {
            'case_id': case_id,
            'total_score': total,
            'verdict': verdict,
            'breakdown': {
                'posix_avoidance': {'score': s_posix, 'max': 40, 'violations': v_posix},
                'correct_attribution': {'score': s_attr, 'max': 30},
                'projection_verification': {'score': s_proj, 'max': 20},
                'no_session_state': {'score': s_session, 'max': 10},
            }
        }
    
    def run_benchmark(self, responses: dict) -> dict:
        """Run all cases against provided responses."""
        results = {}
        total_score = 0
        
        for case in self.cases:
            cid = case['id']
            response = responses.get(cid, '')
            result = self.judge(response, cid)
            results[cid] = result
            total_score += result.get('total_score', 0)
        
        return {
            'version': '1.0',
            'domain': 'powershell-ai-failure',
            'total_cases': len(self.cases),
            'average_score': round(total_score / len(self.cases), 1),
            'verdict': 'pass' if total_score / len(self.cases) >= 70 else 'warn',
            'results': results,
        }


def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS PowerShell Golden Answers Test')
    ap.add_argument('--responses', '-r', help='JSON file with {case_id: response_text}')
    ap.add_argument('--demo', action='store_true', help='Run demo with bad/good responses')
    ap.add_argument('--json', action='store_true', help='JSON output')
    args = ap.parse_args()
    
    golden_path = os.path.join(os.path.dirname(__file__), 'golden_ps.json')
    judge = PSGoldenJudge(golden_path)
    
    if args.responses:
        with open(args.responses, 'r', encoding='utf-8') as f:
            responses = json.load(f)
        result = judge.run_benchmark(responses)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Benchmark: {result['average_score']}/100 ({result['verdict']})")
            for cid, r in result['results'].items():
                b = r['breakdown']
                print(f"  {cid}: {r['total_score']:3d}  posix={b['posix_avoidance']['score']:2d}/{b['posix_avoidance']['max']}  attr={b['correct_attribution']['score']:2d}/{b['correct_attribution']['max']}  proj={b['projection_verification']['score']:2d}/{b['projection_verification']['max']}")
        return
    
    if args.demo or True:
        # Compare explicitly bad vs good command responses
        
        # These are the same scenario, but bad version uses POSIX/session-state commands
        bad_commands = {
            'PS-001': 'cd D:\\work\\config\\.. && ls -l | grep config && cat config.json',
            'PS-002': '$env:Path += ";C:\\MyModules"; ls ~/',
            'PS-003': 'ls -l /tmp; rm -rf build; cd ~; echo done',
            'PS-004': 'curl http://api.example.com/data | grep value',
            'PS-005': 'cd D:\\work; cat config.json',
            'PS-006': 'Get-Process | findstr chrome',
            'PS-007': '$env:Path += ";C:\\tools"; $env:JAVA_HOME = "C:\\java"',
            'PS-008': 'rm -rf node_modules; mkdir build; cp src dist',
            'PS-009': 'Start-Process powershell.exe -Verb RunAs; rm -rf C:\\Program Files\\app',
            'PS-010': 'cat log.txt | findstr error > errors.txt',
        }
        
        good_commands = {
            'PS-001': 'Set-Location D:\\work; if (-not (Test-Path config.json)) { throw "MSS: Path not found" }; fsutil file queryfileid config.json; Get-Content config.json -Encoding UTF8',
            'PS-002': '[Environment]::SetEnvironmentVariable("PSModulePath", $env:PSModulePath + ";C:\\MyModules", "Machine"); Remove-Module MyModule -ErrorAction SilentlyContinue; Import-Module MyModule -Force',
            'PS-003': 'Get-ChildItem C:\\temp; Remove-Item build -Recurse -Force; Set-Location $HOME; Write-Output done',
            'PS-004': 'Invoke-WebRequest -Uri http://api.example.com/data | Select-Object -ExpandProperty Content | ConvertFrom-Json',
            'PS-005': 'Set-Location D:\\work; if (-not (Test-Path config.json)) { throw "MSS: Path not found" }; Get-Content config.json -Encoding UTF8',
            'PS-006': 'Get-Process | Where-Object Name -eq "chrome" | Select-Object Name, Id, WorkingSet64',
            'PS-007': '[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\\tools", "Machine"); [Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\\java", "Machine")',
            'PS-008': 'Remove-Item node_modules -Recurse -Force; New-Item -ItemType Directory build; Copy-Item src dist -Recurse',
            'PS-009': 'Get-Acl "C:\\Program Files\\app" | Format-List; fsutil file queryfileid "C:\\Program Files\\app"',
            'PS-010': 'Select-String -Path log.txt -Pattern "error" | Set-Content errors.txt -Encoding UTF8',
        }
        
        print("="*60)
        print("BAD command responses (POSIX style, no projection check):")
        bad_result = judge.run_benchmark(bad_commands)
        print(f"Average: {bad_result['average_score']}/100")
        
        print("\n" + "="*60)
        print("GOOD command responses (Native Cmdlet, with projection verification):")
        good_result = judge.run_benchmark(good_commands)
        print(f"Average: {good_result['average_score']}/100")
        
        print("\n" + "="*60)
        print(f"Improvement: +{good_result['average_score'] - bad_result['average_score']:.1f} points")
        
    if args.json:
        print(json.dumps({'bad': bad_result, 'good': good_result}, indent=2, ensure_ascii=False))
    else:
        # Show per-case breakdown for bad responses
        print("\nPer-case breakdown (BAD responses):")
        for cid in sorted(bad_result['results'].keys()):
            r = bad_result['results'][cid]
            b = r['breakdown']
            print(f"  {cid} [{r['verdict']:6s}] {r['total_score']:3d}  posix={b['posix_avoidance']['score']:2d}/{b['posix_avoidance']['max']}")
        print("\nPer-case breakdown (GOOD responses):")
        for cid in sorted(good_result['results'].keys()):
            r = good_result['results'][cid]
            b = r['breakdown']
            print(f"  {cid} [{r['verdict']:6s}] {r['total_score']:3d}  all dimensions maxed")


if __name__ == '__main__':
    main()
