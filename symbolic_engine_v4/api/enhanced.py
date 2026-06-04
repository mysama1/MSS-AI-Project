"""
MSS Symbolic Engine v4.0 - Enhanced API
Additional API endpoints and features
"""

import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from symbolic_engine_v4.core import CSRGraph, ConceptNode, ConceptEdge, RelationType, LayerTier
from symbolic_engine_v4.parser import JSONLParser
from symbolic_engine_v4.reasoner.path_finder import AStarPathFinder

class EnhancedSymbolicEngineAPI:
    """Enhanced API with additional features"""
    
    def __init__(self):
        self.graph = CSRGraph()
        self.parser = JSONLParser()
        self.finder = None
        self.loaded = False
    
    def load_knowledge_base(self, kb_dir: str) -> dict:
        """Load knowledge base from directory"""
        try:
            nodes, edges = self.parser.parse_directory(kb_dir)
            
            for node in nodes:
                self.graph.add_node(node)
            for edge in edges:
                self.graph.add_edge(edge)
            
            self.finder = AStarPathFinder(self.graph)
            self.loaded = True
            
            return {
                "status": "success",
                "nodes_loaded": len(nodes),
                "edges_loaded": len(edges),
                "total_nodes": self.graph.node_count,
                "total_edges": self.graph.edge_count
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_stats(self) -> dict:
        """Get graph statistics"""
        if not self.loaded:
            return {"status": "error", "message": "Knowledge base not loaded"}
        
        # Layer distribution
        layers = {}
        for node in self.graph:
            layer = node.layer.value
            layers[layer] = layers.get(layer, 0) + 1
        
        # Node types
        types = {}
        for node in self.graph:
            ntype = node.node_type.value
            types[ntype] = types.get(ntype, 0) + 1
        
        return {
            "status": "success",
            "total_nodes": self.graph.node_count,
            "total_edges": self.graph.edge_count,
            "avg_degree": round(self.graph.edge_count / max(self.graph.node_count, 1), 3),
            "layer_distribution": layers,
            "node_types": types
        }
    
    def find_path(self, source: str, target: str, max_depth: int = 5) -> dict:
        """Find path between two nodes"""
        if not self.loaded:
            return {"status": "error", "message": "Knowledge base not loaded"}
        
        if not self.finder:
            return {"status": "error", "message": "Path finder not initialized"}
        
        result = self.finder.find_path(source, target, max_depth)
        
        if result:
            return {
                "status": "success",
                "path_found": True,
                "path_length": result["path_length"],
                "total_cost": result["total_cost"],
                "path": result["path"]
            }
        else:
            return {
                "status": "success",
                "path_found": False,
                "message": "No path found within depth limit"
            }
    
    def search_nodes(self, query: str, layer: str = None) -> dict:
        """Search nodes by title or content"""
        if not self.loaded:
            return {"status": "error", "message": "Knowledge base not loaded"}
        
        results = []
        query_lower = query.lower()
        
        for node in self.graph:
            # Filter by layer if specified
            if layer and node.layer.value != layer:
                continue
            
            # Search in title and content
            if (query_lower in node.title.lower() or 
                query_lower in node.content.lower()):
                results.append({
                    "id": node.id,
                    "title": node.title,
                    "layer": node.layer.value,
                    "node_type": node.node_type.value,
                    "confidence": node.confidence
                })
        
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": results[:20]  # Limit to 20 results
        }
    
    def get_node_details(self, node_id: str) -> dict:
        """Get detailed information about a node"""
        if not self.loaded:
            return {"status": "error", "message": "Knowledge base not loaded"}
        
        node = self.graph.get_node(node_id)
        if not node:
            return {"status": "error", "message": f"Node {node_id} not found"}
        
        # Get neighbors
        neighbors = []
        for neighbor, edge_type in self.graph.get_neighbors(node_id):
            neighbors.append({
                "id": neighbor.id,
                "title": neighbor.title,
                "relation": edge_type.value if hasattr(edge_type, 'value') else str(edge_type)
            })
        
        return {
            "status": "success",
            "node": {
                "id": node.id,
                "title": node.title,
                "content": node.content[:500] + "..." if len(node.content) > 500 else node.content,
                "layer": node.layer.value,
                "node_type": node.node_type.value,
                "confidence": node.confidence,
                "metadata": node.metadata,
                "neighbors_count": len(neighbors),
                "neighbors": neighbors
            }
        }
    
    def analyze_layer_connectivity(self) -> dict:
        """Analyze connectivity between layers"""
        if not self.loaded:
            return {"status": "error", "message": "Knowledge base not loaded"}
        
        # Count edges between layers
        layer_connections = {}
        
        for node in self.graph:
            neighbors = self.graph.get_neighbors(node.id)
            for neighbor, edge_type in neighbors:
                source_layer = node.layer.value
                target_layer = neighbor.layer.value
                
                key = f"{source_layer}->{target_layer}"
                layer_connections[key] = layer_connections.get(key, 0) + 1
        
        return {
            "status": "success",
            "layer_connections": layer_connections
        }

# Create global API instance
api = EnhancedSymbolicEngineAPI()

class EnhancedHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler"""
    
    def log_message(self, format, *args):
        pass
    
    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return
        
        if path == "/load":
            kb_dir = data.get("kb_dir", r"C:\MSS-AI-Project\knowledge_base")
            result = api.load_knowledge_base(kb_dir)
            self._send_json(result)
        
        elif path == "/path":
            source = data.get("source", "")
            target = data.get("target", "")
            max_depth = data.get("max_depth", 5)
            
            if not source or not target:
                self._send_json({"error": "Missing source or target"}, 400)
                return
            
            result = api.find_path(source, target, max_depth)
            self._send_json(result)
        
        elif path == "/search":
            query = data.get("query", "")
            layer = data.get("layer", None)
            
            if not query:
                self._send_json({"error": "Missing query"}, 400)
                return
            
            result = api.search_nodes(query, layer)
            self._send_json(result)
        
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/health":
            self._send_json({
                "status": "healthy",
                "service": "mss-symbolic-engine-enhanced",
                "version": "4.0.0",
                "loaded": api.loaded
            })
        
        elif path == "/stats":
            result = api.get_stats()
            self._send_json(result)
        
        elif path.startswith("/node/"):
            node_id = path[6:]  # Remove "/node/"
            result = api.get_node_details(node_id)
            self._send_json(result)
        
        elif path == "/connectivity":
            result = api.analyze_layer_connectivity()
            self._send_json(result)
        
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def start_enhanced_api(host="localhost", port=8851):
    """Start enhanced API server"""
    server = HTTPServer((host, port), EnhancedHandler)
    print(f"MSS Symbolic Engine v4.0 - Enhanced API")
    print(f"Running at http://{host}:{port}")
    print(f"Endpoints:")
    print(f"  GET  /health        - Health check")
    print(f"  GET  /stats         - Graph statistics")
    print(f"  GET  /node/<id>     - Node details")
    print(f"  GET  /connectivity  - Layer connectivity")
    print(f"  POST /load          - Load knowledge base")
    print(f"  POST /path          - Find path")
    print(f"  POST /search        - Search nodes")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    start_enhanced_api()
