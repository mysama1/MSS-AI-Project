"""Connect heat tax protocol to agent_server and fix report output."""
import sys
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')

# === Part 1: Fix linter report to show repairs ===
f = r'E:\AI_Workspace\MSS-AI\project\mssclaw\core\layering_linter.py'
with open(f, 'rb') as fh:
    raw = fh.read()
if raw[:3] == b'\xef\xbb\xbf':
    raw = raw[3:]
content = raw.decode('utf-8')

old_end = "lines.append(f\"\\n📋 Verdict: {r['verdict']}\")"
new_end = '''    if hasattr(self, 'repair'):
        reps = self.repair()
        if reps['repair_suggestions']:
            lines.append("\\n🔧 Repair Suggestions:")
            for s in reps['repair_suggestions']:
                lines.append(f\"  [{s['condition']}] {s['command']}\")
    lines.append(f\"\\n📋 Verdict: {r['verdict']}\")'''

if old_end in content:
    content = content.replace(old_end, new_end)
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(content)
    print("Linter report now shows repairs")
else:
    print("Could not find injection point in linter")

# === Part 2: Test the full linter output ===
from mssclaw.core.layering_linter import LayeringLinter
l = LayeringLinter()
print(l.report()[:500])
