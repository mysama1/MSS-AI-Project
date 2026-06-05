#!/usr/bin/env python3
"""
MSS 内容合规扫描器 v15.1
针对文档/报告/知识库条目的文本质量审计。
规则: C1_CLAIM (无锚断言), C2_VAGUE (模糊语言), C3_MEME (模因污染),
      C4_PSEUDO (伪科学性), C5_THERMAL (热税短视)
100% 自包含, 无外部依赖。
"""
import json, re, argparse, os, sys
from datetime import datetime
from pathlib import Path

# ── 规则定义 ──

RULES = {
    'C1_CLAIM': {
        'name': '无锚断言检测',
        'severity': 'reject',
        'patterns': [
            r'必然|绝对|毫无疑问|100%|永远|绝不会|显然',
            r'所有.*都|没有人|从未|始终|完全',
            r'科学证明|研究表明|数据表明|事实是',
        ],
        'detail': '绝对化/无证据断言 — 违反 A7 诚实边界公理',
        'layer': 'L2',
    },
    'C2_VAGUE': {
        'name': '模糊语言检测',
        'severity': 'warn',
        'patterns': [
            r'某种程度|或多或少|某种意义上|似乎|可能.*也可能',
            r'一言难尽|说不清|难以描述',
            r'各方面|全方位|多层次|多维度',
        ],
        'detail': '模糊化表达 — 降低信息密度, 增加意义热税 (A3)',
        'layer': 'L2',
    },
    'C3_MEME': {
        'name': '模因污染检测',
        'severity': 'warn',
        'patterns': [
            r'降维打击|底层逻辑|顶层设计|闭环|赋能',
            r'抓手|对齐|颗粒度|引爆点|护城河',
            r'范式|生态|入口|中台|私域',
            r'all in|内卷|躺平|PUA|画饼',
        ],
        'detail': '商业化模因/流行语 — 模因污染降低意义保真度',
        'layer': 'L3',
    },
    'C4_PSEUDO': {
        'name': '伪科学性检测',
        'severity': 'reject',
        'patterns': [
            r'量子.*能|量子.*疗|量子.*灵',
            r'能量场|频率共振|宇宙法则|吸引力法则',
            r'负离子|远红外|纳米.*量子|石墨烯.*量子',
            r'熵增.*逆|意识.*量子|灵魂.*量子',
        ],
        'detail': '伪科学用语 — 将科学术语用作魔法咒语 (A5 物理投影断裂)',
        'layer': 'L1',
    },
    'C5_THERMAL': {
        'name': '热税短视检测',
        'severity': 'warn',
        'patterns': [
            r'快速.*搞定|一键.*解决|秒变|立马',
            r'不花.*时间|零成本|无脑|躺赚',
            r'短期.*见效|快速.*变现|立刻.*提升',
        ],
        'detail': '热税短视症 — 承诺零热税操作, 忽略长期代价 (A3)',
        'layer': 'L1',
    },
}


class ContentComplianceScanner:
    """v15.1 内容合规扫描器"""
    
    def scan_text(self, text: str, target: str = '<inline>') -> dict:
        violations = []
        for rule_id, rule in RULES.items():
            for pat in rule['patterns']:
                for m in re.finditer(pat, text):
                    # Extract surrounding context
                    start = max(0, m.start() - 20)
                    end = min(len(text), m.end() + 40)
                    snippet = text[start:end].replace('\n', ' ')
                    violations.append({
                        'rule_id': rule_id,
                        'severity': rule['severity'],
                        'layer': rule['layer'],
                        'category': rule['name'],
                        'detail': rule['detail'],
                        'loc': f'pos {m.start()}',
                        'match': m.group(),
                        'context': snippet.strip(),
                    })
        
        violations.sort(key=lambda v: (v['severity'] == 'reject', v['loc']))
        
        lines = len(text.split('\n')) if text else 0
        score = max(0, 100 - len(violations) * 5)
        
        return {
            'target': target, 'target_type': 'text',
            'total_lines': lines,
            'violations': violations,
            'verdict': 'reject' if any(v['severity']=='reject' for v in violations)
                       else 'warn' if violations else 'pass',
            'compliance_score': score,
        }
    
    def scan_file(self, filepath: str) -> dict:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return {'target': filepath, 'error': str(e), 'violations': []}
        return self.scan_text(content, filepath)
    
    def scan_directory(self, directory: str, patterns: list = None) -> list:
        if patterns is None:
            patterns = ['*.md', '*.txt', '*.json', '*.py', '*.yaml', '*.yml']
        
        results = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '.git', '__pycache__')]
            for f in files:
                fp = os.path.join(root, f)
                if any(Path(f).match(p) for p in patterns):
                    r = self.scan_file(fp)
                    if r.get('violations'):
                        results.append(r)
        
        return results
    
    def batch_report(self, results: list) -> dict:
        total_v = sum(len(r.get('violations', [])) for r in results)
        rejects = sum(1 for r in results if r.get('verdict') == 'reject')
        by_rule = {}
        for r in results:
            for v in r.get('violations', []):
                rid = v['rule_id']
                by_rule[rid] = by_rule.get(rid, 0) + 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'files_scanned': len(results),
            'total_violations': total_v,
            'rejects': rejects,
            'by_rule': by_rule,
            'verdict': 'reject' if rejects > 0 else 'warn' if total_v > 0 else 'pass',
        }


def main():
    ap = argparse.ArgumentParser(description='MSS 内容合规扫描器 v15.1')
    ap.add_argument('target', nargs='?', help='文件或目录')
    ap.add_argument('--json', action='store_true', help='JSON 输出')
    ap.add_argument('--recursive', action='store_true', help='递归扫描目录')
    ap.add_argument('--demo', action='store_true', help='自助扫描 (扫描自身)')
    ap.add_argument('--rules', action='store_true', help='输出规则列表')
    args = ap.parse_args()
    
    if args.rules:
        for rid, rule in RULES.items():
            print(f"[{rule['severity']:6s}] {rid} [{rule['layer']}] {rule['name']}")
            print(f"       {rule['detail']}")
            print(f"       示例: {rule['patterns'][0][:60]}")
            print()
        return
    
    scanner = ContentComplianceScanner()
    
    if args.demo:
        target = os.path.dirname(__file__) or '.'
        args.recursive = True
    elif not args.target:
        ap.print_help()
        return
    else:
        target = args.target
    
    if os.path.isfile(target):
        result = scanner.scan_file(target)
        results = [result]
    elif args.recursive:
        results = scanner.scan_directory(target)
    else:
        results = [scanner.scan_file(f) for f in Path(target).glob('*') if f.is_file()]
    
    report = scanner.batch_report(results)
    
    if args.json:
        print(json.dumps({'report': report, 'results': results}, indent=2, ensure_ascii=False))
    else:
        print(f"扫描 {report['files_scanned']} 文件: {report['total_violations']} violations ({report['verdict']})")
        if report['by_rule']:
            for rid, count in sorted(report['by_rule'].items()):
                print(f"  {rid}: {count}")
        
        for r in results[:10]:
            vs = r.get('violations', [])
            if vs:
                print(f"\n  {r['target']}:")
                for v in vs[:5]:
                    print(f"    [{v['severity']:6s}] {v['rule_id']} | {v['match']:12s} | {v['detail'][:60]}")
    
    sys.exit(1 if report['verdict'] == 'reject' else 0)


if __name__ == '__main__':
    main()
