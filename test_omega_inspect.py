import sys, os, json
sys.path.insert(0, r'C:\MSS-AI-Project')
from symbolic_rules_omega import OmegaComplianceChecker, RuleLayer

oc = OmegaComplianceChecker()

# Check internal state
print('Internal attributes:')
for attr in ['_rules', 'rules', '_loaded_rules', '__dict__', '_compiled_rules']:
    has = hasattr(oc, attr)
    print(f'  {attr}: {has}')
    if has:
        val = getattr(oc, attr)
        if isinstance(val, dict):
            for k, v in val.items():
                print(f'    {k}: {len(v) if isinstance(v, (list, dict)) else type(v).__name__}')
        elif isinstance(val, list):
            print(f'    len={len(val)}')

# Check if rules are compiled
if hasattr(oc, '__dict__'):
    d = oc.__dict__
    for k, v in d.items():
        if 'rule' in k.lower() or 'compile' in k.lower():
            print(f'  __dict__.{k}: {type(v).__name__} len={len(v) if hasattr(v, "__len__") else "N/A"}')

# Try check one more time
r = oc.check_text("意识是物质进化产生的副产品。", context_layer=RuleLayer.L1)
print(f'\ncheck_text result: {r}')

# Try check_k3_residuals
r2 = oc.check_k3_residuals("意识是物质进化产生的副产品。")
print(f'check_k3_residuals: {r2}')