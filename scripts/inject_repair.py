"""inject repair into layering_linter.py"""
import sys
sys.path.insert(0,r'E:\AI_Workspace\MSS-AI\project')

# Read the file
f = r'E:\AI_Workspace\MSS-AI\project\mssclaw\core\layering_linter.py'
with open(f, 'rb') as fh:
    raw = fh.read()

# Strip BOM if present
if raw[:3] == b'\xef\xbb\xbf':
    raw = raw[3:]
content = raw.decode('utf-8')

# Add repair methods before 'def lint'
repair_code = '''
    def repair(self):
        """P1: Theorem L1 repair suggestions."""
        suggestions = []
        heavy = []
        for src, edges in self.graph.items():
            sl = self.layer_map.get(src, "unclassified")
            for dst, w in edges:
                dl = self.layer_map.get(dst, "unclassified")
                if sl != dl and sl != "unclassified" and dl != "unclassified":
                    heavy.append((src, dst, 0.1 * w, sl, dl))
        heavy.sort(key=lambda x: -x[2])
        for (src, dst, tau, sl, dl) in heavy[:3]:
            suggestions.append({
                "condition": "C2", "action": "move_node",
                "node": src, "from": sl, "to": dl,
                "reason": f"{src}->{dst} tau={tau:.3f}",
                "command": f"move {src} from {sl} to {dl}"
            })
        for layer, stables in self.KNOWN_STABLES.items():
            nodes = [n for n, l in self.layer_map.items() if l == layer]
            if not stables and nodes:
                best = "L2_CORE"
                for l, s in self.KNOWN_STABLES.items():
                    if s and l != layer:
                        best = l
                        break
                suggestions.append({
                    "condition": "C3", "action": "merge_layer",
                    "layer": layer, "nodes": len(nodes),
                    "reason": f"{layer} has no S_i",
                    "command": f"merge {layer} into {best}, or define S_i"
                })
        return {"repair_suggestions": suggestions, "count": len(suggestions)}

'''.replace('\n    def lint', '\n    def lint')

content = content.replace('\n    def lint(self) -> dict:', repair_code + '\n    def lint(self) -> dict:')

# Write back without BOM
with open(f, 'w', encoding='utf-8') as fh:
    fh.write(content)

print("Repair method injected successfully")

# Verify
from mssclaw.core.layering_linter import LayeringLinter
l = LayeringLinter()
r = l.lint()
if hasattr(l, 'repair'):
    reps = l.repair()
    print("Verified: repair() exists, %d suggestions" % reps['count'])
else:
    print("FAILED: repair() not found")
