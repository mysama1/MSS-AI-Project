#!/usr/bin/env python3
"""MSS KB Deep Audit — Contradiction, duplication, version conflict detection."""
import os, json, re, hashlib
from collections import defaultdict
from pathlib import Path

KB = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'
LAYERS = ['L0_FOUNDATION', 'L1_CORE_THEORY', 'L2_APPLIED_THEORY', 'L3_STRATEGIC', 'L4_META']

def load_all_entries():
    """Load all H-ID entries from 5-layer KB."""
    entries = {}
    for layer in LAYERS:
        layer_dir = os.path.join(KB, layer)
        if not os.path.exists(layer_dir):
            continue
        for f in os.listdir(layer_dir):
            if not f.endswith('.jsonl'):
                continue
            m = re.match(r'h(\d+)', f)
            if not m:
                continue
            hid = int(m.group(1))
            fpath = os.path.join(layer_dir, f)
            try:
                for enc in ['utf-8-sig', 'utf-8', 'gbk']:
                    try:
                        with open(fpath, encoding=enc) as fh:
                            for line in fh:
                                if line.strip().startswith('{'):
                                    entry = json.loads(line.strip())
                                    break
                        break
                    except: continue
                
                title = entry.get('title', entry.get('name', ''))
                content = entry.get('content', '')
                if not content:
                    content = ' '.join(str(v) for v in entry.values() if isinstance(v, str))
                
                entries[hid] = {
                    'h_id': f'H{hid}',
                    'title': str(title),
                    'layer': layer,
                    'filename': f,
                    'content': content,
                    'version': entry.get('version', ''),
                    'axioms': entry.get('axioms', []),
                    't_value': entry.get('t_value', None),
                    'raw': json.dumps(entry, ensure_ascii=False)[:2000]
                }
            except Exception as e:
                print(f"  ⚠️ Skip H{hid}: {e}")
    
    return entries

# ── Audit Rules ───────────────────────────────────────

def audit_contradictions(entries):
    """A5: Find entries that make contradictory claims about the same topic."""
    findings = []
    
    # Check for contradictory axiom versions
    axiom_entries = {}
    for hid, e in entries.items():
        content = e['content'].lower()
        for axiom in ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8']:
            if axiom in content and 'axiom' in content[:200]:
                axiom_entries.setdefault(axiom, []).append(hid)
    
    # Check version conflicts
    version_map = defaultdict(list)
    for hid, e in entries.items():
        v = e.get('version', '')
        if v:
            base = re.sub(r'_v\d+', '', e.get('title', '')[:30])
            version_map[base].append((hid, v))
    
    for base, vers in version_map.items():
        if len(vers) > 1:
            versions = sorted(set(v[1] for v in vers))
            if len(versions) > 1:
                findings.append({
                    'type': 'VERSION_CONFLICT',
                    'severity': 'MEDIUM',
                    'detail': f'Multiple versions: {versions}',
                    'entries': [f'H{h}' for h, _ in vers],
                    'recommendation': f'Keep latest ({versions[-1]}), archive old'
                })
    
    # Check for duplicated content
    hashes = defaultdict(list)
    for hid, e in entries.items():
        h = hashlib.md5(e['content'][:500].encode()).hexdigest()
        hashes[h].append(hid)
    
    for h, hids in hashes.items():
        if len(hids) > 1:
            findings.append({
                'type': 'CONTENT_DUPLICATE',
                'severity': 'HIGH',
                'detail': f'Identical content ({len(hids)} copies)',
                'entries': [f'H{hid}' for hid in hids],
                'recommendation': 'Merge or delete duplicates'
            })
    
    return findings


def audit_heat_tax(entries):
    """A3: Find entries with excessive heat tax (orphaned, circular, low value)."""
    findings = []
    
    # Find entries referencing non-existent H-IDs
    all_hids = set(entries.keys())
    for hid, e in entries.items():
        refs = re.findall(r'H(\d{3,4})', e['content'])
        for ref in refs:
            ref_hid = int(ref)
            if ref_hid != hid and ref_hid not in all_hids:
                findings.append({
                    'type': 'BROKEN_REFERENCE',
                    'severity': 'MEDIUM',
                    'detail': f'H{hid} references non-existent H{ref_hid}',
                    'entries': [f'H{hid}'],
                    'recommendation': 'Update reference or create missing entry'
                })
    
    # Find entries with empty/missing content
    for hid, e in entries.items():
        if len(e['content']) < 50:
            findings.append({
                'type': 'STUB_ENTRY',
                'severity': 'HIGH',
                'detail': f'H{hid}: {e["title"][:50]} — content < 50 chars',
                'entries': [f'H{hid}'],
                'recommendation': 'Expand or mark as placeholder'
            })
    
    # Find recovered entries that may be stale
    recovered = [hid for hid, e in entries.items() if '_recovered' in e.get('version', '')]
    if recovered:
        findings.append({
            'type': 'RECOVERED_STALE',
            'severity': 'LOW',
            'detail': f'{len(recovered)} IMA-recovered entries may need re-verification',
            'entries': [f'H{hid}' for hid in recovered[:10]],
            'recommendation': 'Re-verify with user if content is still accurate'
        })
    
    return findings


def audit_boundary(entries):
    """A1/A4: Find boundary issues — missing layer attribution, unknown content."""
    findings = []
    
    # Check for entries missing t_value
    no_t = [hid for hid, e in entries.items() if e.get('t_value') is None]
    if no_t:
        findings.append({
            'type': 'MISSING_T_VALUE',
            'severity': 'LOW',
            'detail': f'{len(no_t)} entries missing t_value (meaning density score)',
            'entries': [f'H{hid}' for hid in no_t[:10]],
            'recommendation': 'Assign t_value for completeness'
        })
    
    # Check for entries missing axiom references
    no_axiom = [hid for hid, e in entries.items() if not e.get('axioms')]
    if no_axiom:
        findings.append({
            'type': 'MISSING_AXIOM_REF',
            'severity': 'MEDIUM',
            'detail': f'{len(no_axiom)} entries missing axiom references',
            'entries': [f'H{hid}' for hid in no_axiom[:10]],
            'recommendation': 'Tag with relevant MSS axioms'
        })
    
    return findings


def audit_consistency(entries):
    """Cross-layer consistency check."""
    findings = []
    
    # Check that v17.8 entries reference the right axioms
    for hid in range(513, 520):
        if hid in entries:
            e = entries[hid]
            axioms = e.get('axioms', [])
            if not axioms or all(a not in str(axioms) for a in ['A1','A2','A3','A4','A5','A6']):
                findings.append({
                    'type': 'MISSING_AXIOM_ANCHOR',
                    'severity': 'MEDIUM',
                    'detail': f'H{hid}: {e["title"][:50]} — v17.8 entry missing axiom anchor',
                    'entries': [f'H{hid}'],
                    'recommendation': 'Add A1-A6 axiom references'
                })
    
    return findings

# ── Main ──────────────────────────────────────────────

print("="*60)
print("MSS KB Deep Audit — A3+A5 Framework")
print("="*60)

entries = load_all_entries()
print(f"\nLoaded {len(entries)} entries")

# Run all audits
all_findings = {
    'contradictions': audit_contradictions(entries),
    'heat_tax': audit_heat_tax(entries),
    'boundary': audit_boundary(entries),
    'consistency': audit_consistency(entries),
}

# Print results
total = sum(len(v) for v in all_findings.values())
print(f"\nFindings: {total} total\n")

for category, findings in all_findings.items():
    if not findings:
        continue
    icon = {'contradictions': 'A5', 'heat_tax': 'A3', 'boundary': 'A1', 'consistency': 'A6'}
    print(f"--- {category.upper()} ({icon.get(category,'?')}) : {len(findings)} findings ---")
    for f in findings[:5]:
        sev = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(f['severity'], '⚪')
        print(f"  {sev} [{f['type']}] {f['detail']}")
        print(f"     → {f['recommendation']}")
        if len(f['entries']) <= 5:
            print(f"     Entries: {', '.join(f['entries'])}")
        else:
            print(f"     Entries: {', '.join(f['entries'][:5])} ... ({len(f['entries'])} total)")
    if len(findings) > 5:
        print(f"  ... and {len(findings)-5} more")
    print()

# Summary
critical = sum(1 for cat in all_findings.values() for f in cat if f['severity'] == 'HIGH')
medium = sum(1 for cat in all_findings.values() for f in cat if f['severity'] == 'MEDIUM')
low = sum(1 for cat in all_findings.values() for f in cat if f['severity'] == 'LOW')
print(f"Summary: 🔴{critical} HIGH  🟡{medium} MEDIUM  🟢{low} LOW")
print(f"KB Health Score: {100 - (critical*20 + medium*5 + low*2)}/100")
