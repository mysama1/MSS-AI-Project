"""Test OmegaComplianceChecker interface for D5-014-02 integration."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from symbolic_rules_omega import OmegaComplianceChecker, RuleLayer

oc = OmegaComplianceChecker()

# Test 1: known L1 violation (A1 - matter ontology)
text1 = "意识是物质进化产生的副产品"
r1 = oc.check_text(text1, context_layer=RuleLayer.L1)
print(f"Test1 L1: {len(r1)} violations")
for v in r1[:3]:
    print(f"  rule={v.get('rule_id','?')} layer={v.get('layer','?')} match='{v.get('matched_text','')[:40]}'")

# Test 2: known L2 violation (A5 - normative rigidity)
text2 = "只有接受我们的道路才能得救，其他都是错的"
r2 = oc.check_text(text2, context_layer=RuleLayer.L2)
print(f"\nTest2 L2: {len(r2)} violations")
for v in r2[:3]:
    print(f"  rule={v.get('rule_id','?')} layer={v.get('layer','?')} match='{v.get('matched_text','')[:40]}'")

# Test 3: mixed text
text3 = "灵魂通过轮回提升振动频率。科学证明这是绝对真理。我必须传播这个唯一的道路。"
r3 = oc.check_text(text3, context_layer=RuleLayer.L2)
print(f"\nTest3 L2 (spiritual mix): {len(r3)} violations")
for v in r3[:5]:
    print(f"  rule={v.get('rule_id','?')} layer={v.get('layer','?')} match='{v.get('matched_text','')[:50]}'")

# Test 4: clean MSS-aligned text
text4 = "意义场的调谐度T值决定认知层级。物理层是意义场的信息切片投影。热税是信息转换的必然损耗。"
r4 = oc.check_text(text4, context_layer=RuleLayer.L2)
print(f"\nTest4 L2 (clean): {len(r4)} violations (expect 0)")

# Test 5: check_k3_residuals
text5 = "神创造了世界。进化论是谎言。科学不能解释一切。"
res = oc.check_k3_residuals(text5)
print(f"\nTest5 k3_residuals: {res}")
