import sys
sys.path.insert(0, 'E:\\AI_Workspace\\MSS-AI\\project')

from symbolic_engine_v4.core import CSRGraph, ConceptNode, ConceptEdge, RelationType, LayerTier
from symbolic_engine_v4.parser import JSONLParser

graph = CSRGraph()
parser = JSONLParser()
nodes, edges = parser.parse_directory(r'C:\MSS-AI-Project\knowledge_base')

for node in nodes:
    graph.add_node(node)
for edge in edges:
    graph.add_edge(edge)

print('Loaded:', graph.node_count, 'nodes,', graph.edge_count, 'edges')

# Test path finder
from symbolic_engine_v4.reasoner.path_finder import AStarPathFinder
finder = AStarPathFinder(graph)

# Find a path
if graph.edge_count > 0:
    for node in graph:
        neighbors = graph.get_neighbors(node.id)
        if neighbors:
            target = neighbors[0][0]
            result = finder.find_path(node.id, target.id, max_depth=3)
            if result:
                print('Path found:', node.id, '->', target.id)
                print('Length:', result['path_length'], 'Cost:', result['total_cost'])
            break

print('Path finder test passed')
