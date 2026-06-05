"""
Test suite for cognitive_snapshot.py - D5-005-03
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cognitive_snapshot import SnapshotEngine, AnchorDetector, ContradictionScanner, HeatTaxEstimator

engine = SnapshotEngine()
passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f'  PASS: {name}')
    else:
        failed += 1
        print(f'  FAIL: {name}')

# Test 1: Well-anchored subject detection
print('Test 1: Well-anchored subject')
s1 = engine.scan('始终追求真理和逻辑自洽。创造美和连接他人是核心。本质上所有领域寻找更深层的秩序。')
check('anchor_strength >= 50', s1.anchor_strength_score >= 50)
check('active_fields includes LOGIC', 'LOGIC' in s1.active_fields)
check('heat_tax LOW', s1.heat_tax['level'] == 'LOW')

# Test 2: Transitional/unanchored subject
print('Test 2: Transitional subject')
s2 = engine.scan('可能是创造些什么也可能是帮助别人。有时候觉得一切都没有意义但不甘心放弃。我也说不清。')
check('anchor_strength low', s2.anchor_strength_score < 40)
check('high fragmentation', s2.contradictions['fragmentation_score'] >= 0.05)

# Test 3: Contradiction detection
print('Test 3: Contradiction detection')
s3 = engine.scan('我追求自由但同时必须接受服从。理性很重要但感性同样关键。')
check('contradictions detected', len(s3.contradictions['contradictions']) >= 2)

# Test 4: Rigid anchor detection (needs meaning-field keywords to trigger)
print('Test 4: Rigid anchor detection')
ad = AnchorDetector()
anchors = ad.detect('成功必须绝对达成。逻辑推理一定正确毫无疑问。这是唯一目标。')
rigid_count = sum(1 for a in anchors for inst in a['instances'] if inst['modifier'] == 'rigid')
check('rigid modifiers detected', rigid_count >= 1)

# Test 5: Empty input handling
print('Test 5: Empty input')
check('None for empty', engine.scan('') is None)
check('None for short', engine.scan('abc') is None)

# Test 6: Batch scanning
print('Test 6: Batch scanning')
batch = ['追求真理和逻辑自洽的核心意义。', '不知道意义是什么也许虚无。', '必须绝对成功毫无疑问逻辑。']
results = engine.scan_batch(batch)
check('batch returns 3 results', len(results) == 3)
if len(results) >= 1:
    check('batch sorted by strength', results[0].anchor_strength_score >= results[-1].anchor_strength_score)

# Test 7: Snapshot comparison
print('Test 7: Snapshot comparison')
delta = engine.compare(s1, s2)
check('anchor_strength_delta negative (T1 > T2)', delta['anchor_strength_delta'] < 0)
check('heat_tax_delta positive (T2 > T1)', delta['heat_tax_delta'] > 0)

# Test 8: to_dict completeness
print('Test 8: to_dict completeness')
d = s1.to_dict()
required_keys = ['anchor_count', 'active_fields', 'anchor_strength', 'anchor_diagnosis', 'coherence_score', 'heat_tax']
check('all keys present', all(k in d for k in required_keys))

# Test 9: Heat tax breakdown
print('Test 9: Heat tax breakdown')
hte = HeatTaxEstimator()
result = hte.estimate('必须绝对永远成功。痛苦焦虑恐惧。总之不知道。', [], 0.0)
check('composite calculated', result['composite'] > 0)
check('all breakdowns present', set(hte.HEAT_SIGNALS.keys()).issubset(result['breakdown'].keys()))

# Test 10: Contradiction scanner
print('Test 10: Contradiction scanner')
cs = ContradictionScanner()
scan = cs.scan('一方面追求自由另一方面接受约束但是永远需要控制但是可能放下')
check('fragmentation high', scan['fragmentation_score'] >= 0.05)
check('narrative_jumps >= 0', scan['narrative_jumps'] >= 0)
check('coherence in [0,1]', 0 <= scan['coherence_score'] <= 1)

print(f'\n=== Results: {passed}/{passed+failed} PASS ===')
if failed > 0:
    sys.exit(1)