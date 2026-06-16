"""Patch: add repair() to LayeringLinter."""
import sys
sys.path.insert(0,r'E:\AI_Workspace\MSS-AI\project')
from mssclaw.core.layering_linter import LayeringLinter

# Add repair methods to the class
def _find_heavy_cross_edges(self):
    heavy = []
    for src, edges in self.graph.items():
        sl = self.layer_map.get(src, "unclassified")
        for dst, w in edges:
            dl = self.layer_map.get(dst, "unclassified")
            if sl != dl and sl != "unclassified" and dl != "unclassified":
                heavy.append((src, dst, 0.1*w, sl, dl))
    return sorted(heavy, key=lambda x: -x[2])

def _find_nearest_legitimate_layer(self, empty):
    for l, s in self.KNOWN_STABLES.items():
        if s and l != empty: return l
    return "L2_CORE"

def repair(self):
    suggestions = []
    heavy = self._find_heavy_cross_edges()
    for (src, dst, tau, sl, dl) in heavy[:3]:
        suggestions.append({
            "condition": "C2", "action": "move_node",
            "node": src, "from": sl, "to": dl,
            "reason": "%s->%s tau=%.3f, move to same layer" % (src, dst, tau),
            "command": "move %s from %s to %s" % (src, sl, dl)
        })
    for layer, stables in self.KNOWN_STABLES.items():
        nodes = [n for n, l in self.layer_map.items() if l == layer]
        if not stables and nodes:
            best = self._find_nearest_legitimate_layer(layer)
            suggestions.append({
                "condition": "C3", "action": "merge_layer",
                "layer": layer, "nodes": len(nodes),
                "reason": "%s has no S_i" % layer,
                "command": "merge %s into %s, or define S_i for %s" % (layer, best, layer)
            })
    return {"repair_suggestions": suggestions, "count": len(suggestions)}

# Monkey-patch
LayeringLinter._find_heavy_cross_edges = _find_heavy_cross_edges
LayeringLinter._find_nearest_legitimate_layer = _find_nearest_legitimate_layer
LayeringLinter.repair = repair

# Test
l = LayeringLinter()
r = l.lint()
reps = l.repair()
print('Repair suggestions:', reps['count'])
for s in reps['repair_suggestions']:
    print('  [%s] %s' % (s['condition'], s['command']))
