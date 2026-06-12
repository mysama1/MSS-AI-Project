import sys; sys.path.insert(0, '.')
from mss_agent.agents.audit_agent import AuditAgent
a = AuditAgent(name='test')
print(f"Role: {a.role}")
print(f"Capabilities: {a.capabilities}")
dims = a._dimensions if hasattr(a, '_dimensions') else None
if dims:
    print(f"Dimensions ({len(dims)}): {list(dims.keys())}")
    for k, v in dims.items():
        checks = len(v) if isinstance(v, (list, dict)) else '?'
        print(f"  {k}: {checks} checks")
else:
    print("No _dimensions found — checking class attrs...")
    import inspect
    src = inspect.getsource(AuditAgent)
    for line in src.split('\n'):
        if any(w in line.lower() for w in ['dimension', 'audit_', '_check', '审查', '维度']):
            print(f"  {line.strip()[:100]}")
