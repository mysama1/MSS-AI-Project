#!/usr/bin/env python3
"""MSS KB Deep Structural Audit — contradiction, version drift, semantic conflict, gap detection."""
import os, json, re, hashlib
from collections import defaultdict
from pathlib import Path

KB = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'
LAYERS = ['L0_FOUNDATION', 'L1_CORE_THEORY', 'L2_APPLIED_THEORY', 'L3_STRATEGIC', 'L4_META']

def load_all():
    entries = {}
    for layer in LAYERS:
        d = os.path.join(KB, layer)
        if not os.path.isdir(d): continue
        for f in os.listdir(d):
            if not f.endswith('.jsonl'): continue
            m = re.match(r'h(\d+)', f)
            if not m: continue
            hid = int(m.group(1))
            fp = os.path.join(d, f)
            try:
                for enc in ['utf-8-sig', 'utf-8', 'gbk']:
                    try:
                        with open(fp, encoding=enc) as fh:
                            for line in fh:
                                if line.strip().startswith('{'):
                                    e = json.loads(line.strip())
                                    break
                            break
                    except: continue
                entries[hid] = {
                    'h_id': hid, 'title': str(e.get('title','')), 'layer': layer,
                    'content': str(e.get('content','')), 'version': str(e.get('version','')),
                    'axioms': e.get('axioms', []), 't_value': e.get('t_value'),
                    'references': e.get('references', []), 'tags': e.get('tags', []),
                    'created': str(e.get('created','')), 'confidence': e.get('confidence'),
                    'summary': str(e.get('summary','')), 'filename': f
                }
            except: pass
    return entries

def audit_axiom_contradictions(entries):
    """Find entries referencing deprecated axioms (A7, A8, old-A3)."""
    findings = []
    DEPRECATED = {'A7', 'A8', 'old A3', 'v13.1', 'v12.2', 'omega_rulings'}
    for hid, e in entries.items():
        c = e['content'].lower()
        for dep in DEPRECATED:
            if dep in c:
                findings.append({
                    'type': 'DEPRECATED_REF', 'severity': 'HIGH',
                    'entry': f'H{hid}', 'detail': f"References deprecated: '{dep}'",
                    'title': e['title'][:60], 'fix': 'Update to v15.1 axioms'
                })
                break
    return findings

def audit_version_drift(entries):
    """Find entries with conflicting version numbers for same concepts."""
    findings = []
    # Group by topic base name (strip version suffixes)
    topics = defaultdict(list)
    for hid, e in entries.items():
        base = re.sub(r'\s*v\d+\.\d+.*$', '', str(e.get('title','')))[:40]
        topics[base].append((hid, e.get('version','')))
    
    for base, items in topics.items():
        if len(items) > 1:
            versions = sorted(set(v for _, v in items if v))
            if len(versions) > 1:
                findings.append({
                    'type': 'VERSION_DRIFT', 'severity': 'MEDIUM',
                    'topic': base, 'versions': versions,
                    'entries': [f'H{h}' for h,_ in items],
                    'fix': 'Keep latest version, archive old'
                })
    return findings[:20]

def audit_hollow_entries(entries):
    """Find entries with near-empty content or circular self-references."""
    findings = []
    for hid, e in entries.items():
        c = e['content']
        t = e['title']
        # Content < 30 chars
        if len(c) < 30:
            findings.append({
                'type': 'HOLLOW', 'severity': 'MEDIUM',
                'entry': f'H{hid}', 'title': t[:60],
                'detail': f'Content only {len(c)} chars',
                'fix': 'Expand or mark as tombstone'
            })
        # Content is just a tombstone marker
        elif '已废止' in c and len(c) < 100:
            findings.append({
                'type': 'TOMBSTONE', 'severity': 'LOW',
                'entry': f'H{hid}', 'title': t[:60],
                'detail': 'Deprecated/tombstone entry',
                'fix': 'Verify no active entries reference this'
            })
    return findings

def audit_broken_chains(entries):
    """Find entries referencing H-IDs that don't exist."""
    findings = []
    all_hids = set(entries.keys())
    ref_pattern = re.compile(r'H(\d{3,4})')
    
    for hid, e in entries.items():
        refs = set(int(m) for m in ref_pattern.findall(e['content'] + e.get('summary','')))
        for ref_hid in refs:
            if ref_hid != hid and ref_hid not in all_hids:
                findings.append({
                    'type': 'BROKEN_REF', 'severity': 'HIGH',
                    'entry': f'H{hid}', 'target': f'H{ref_hid}',
                    'detail': f'H{hid} references non-existent H{ref_hid}',
                    'fix': f'Create H{ref_hid} or remove reference'
                })
    return findings

def audit_semantic_conflict(entries):
    """Find entries that define the same concept differently."""
    findings = []
    # Check for contradictory t_value usage
    t_values = [(hid, e.get('t_value')) for hid, e in entries.items() if e.get('t_value') is not None]
    # Check for same axiom but contradictory application
    axiom_usage = defaultdict(list)
    for hid, e in entries.items():
        for a in e.get('axioms', []):
            if a:
                axiom_usage[str(a)].append(hid)
    
    # Check for "A7" entries that might violate H521
    for hid, e in entries.items():
        if e.get('axioms') and 'A7' in str(e.get('axioms')):
            findings.append({
                'type': 'A7_VIOLATION', 'severity': 'HIGH',
                'entry': f'H{hid}', 'title': e['title'][:60],
                'detail': 'Claims A7 axiom (not in v15.1 six-axiom framework)',
                'fix': 'Remove A7 or recategorize as derived theorem'
            })
    return findings

def audit_layer_misplacement(entries):
    """Find entries that seem misplaced in their layer."""
    findings = []
    L0_keywords = ['axiom', '公理', 'physics', '物理', 'math', '数学', 'constant', '常数']
    L1_keywords = ['heat tax', '热税', 'meaning field', '意义场', 'theorem', '定理', 'tuning', '调谐']
    L2_keywords = ['K3', 'civilization', '文明', 'industry', '产业', 'v17', 'AI', 'GPT']
    
    layer_kw = {
        'L0_FOUNDATION': (L0_keywords, L1_keywords + L2_keywords),
        'L1_CORE_THEORY': (L1_keywords, L2_keywords),
        'L2_APPLIED_THEORY': (L2_keywords, L0_keywords),
    }
    
    for hid, e in entries.items():
        layer = e['layer']
        if layer not in layer_kw: continue
        own_kw, other_kw = layer_kw[layer]
        content_lower = (e['title'] + e.get('summary','')).lower()
        # Count keyword matches
        own_score = sum(1 for kw in own_kw if kw.lower() in content_lower)
        other_score = sum(1 for kw in other_kw if kw.lower() in content_lower)
        if other_score > own_score and other_score >= 3:
            findings.append({
                'type': 'MISPLACED', 'severity': 'LOW',
                'entry': f'H{hid}', 'layer': layer, 'title': e['title'][:60],
                'detail': f'More L2 keywords than L1/L0',
                'fix': 'Consider moving to application layer'
            })
    return findings[:20]

def audit_confidence_issues(entries):
    """Find entries with suspiciously high confidence or missing confidence."""
    findings = []
    for hid, e in entries.items():
        conf = e.get('confidence')
        if conf is not None:
            if isinstance(conf, (int, float)) and conf >= 0.99:
                findings.append({
                    'type': 'OVERCONFIDENT', 'severity': 'MEDIUM',
                    'entry': f'H{hid}', 'title': e['title'][:60],
                    'detail': f'Confidence {conf} violates H521 (never claim 1.0)',
                    'fix': 'Calibrate confidence to ≤0.95'
                })
    return findings

# ── Main ──
print("="*65)
print("MSS KB Structural Audit — Contradiction, Drift, Conflict")
print("="*65)

entries = load_all()
print(f"\nLoaded {len(entries)} entries from {len(LAYERS)} layers\n")

audits = {
    'Axiom Contradictions': audit_axiom_contradictions(entries),
    'Version Drift': audit_version_drift(entries),
    'Hollow/Tombstone': audit_hollow_entries(entries),
    'Broken References': audit_broken_chains(entries),
    'Semantic Conflicts': audit_semantic_conflict(entries),
    'Layer Misplacement': audit_layer_misplacement(entries),
    'Confidence Issues': audit_confidence_issues(entries),
}

total = 0
for name, findings in audits.items():
    if findings:
        sev_counts = defaultdict(int)
        for f in findings: sev_counts[f['severity']] += 1
        sev_str = ' '.join(f"[{s}:{c}]" for s,c in sorted(sev_counts.items()))
        print(f"--- {name}: {len(findings)} {sev_str}")
        for f in findings[:8]:
            icon = {'HIGH':'🔴','MEDIUM':'🟡','LOW':'🟢'}.get(f['severity'],'')
            print(f"  {icon} [{f['type']}] {f.get('entry','')} {f.get('target','')} {f['detail'][:70]}")
            if 'fix' in f: print(f"     fix: {f['fix']}")
        if len(findings) > 8:
            print(f"  ... +{len(findings)-8} more")
        total += len(findings)
    else:
        print(f"--- {name}: CLEAN ✅")
    print()

h = sum(1 for find in audits.values() for f in find if f['severity']=='HIGH')
m = sum(1 for find in audits.values() for f in find if f['severity']=='MEDIUM')
l = sum(1 for find in audits.values() for f in find if f['severity']=='LOW')
print(f"Total: {total} findings | 🔴{h} HIGH 🟡{m} MEDIUM 🟢{l} LOW")
