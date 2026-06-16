f=r'E:\AI_Workspace\MSS-AI\project\mssclaw\core\layering_linter.py'
c=open(f,'r',encoding='utf-8-sig').read()
c=c.replace('        return report\n','        r["repairs"] = self.repair()["repair_suggestions"]\n        return report\n')
open(f,'w',encoding='utf-8').write(c)
print("Patched. Testing...")

import sys; sys.path.insert(0,'.')
from mssclaw.core.layering_linter import LayeringLinter
l = LayeringLinter()
r = l.lint()
reps = r.get('repairs',[])
print('Repairs:', len(reps), 'suggestions')
for s in reps[:3]:
    print('  [%s] %s' % (s['condition'], s['command']))
