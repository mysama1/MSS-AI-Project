"""
MSS Symbolic Engine v4.0 - RESTful API
Simple Flask-based API for symbolic reasoning operations
"""

import json
import time
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading

# Import core components
from ..core import CSRGraph, ConceptNode, ConceptEdge, QueryResult, ValidationResult
from ..core.types import RelationType, NodeType, LayerTier
from ..parser import JSONLParser

class SymbolicEngineAPI:
    """Symbolic Engine API handler"""

    def __init__(self):
        self.graph = CSRGraph(max_nodes=100000)
        self.parser = JSONLParser()
        self.knowledge_base_loaded = False
        self.query_count = 0
        self.start_time = time.time()

    def load_knowledge_base(self, directory: str) -> Dict[str, Any]:
        """Load knowledge base from directory"""
        start = time.time()
        nodes, edges = self.parser.parse_directory(directory)

        # Add nodes to graph
        for node in nodes:
            self.graph.add_node(node)

        # Add edges to graph
        added_edges = 0
        for edge in edges:
            if self.graph.add_edge(edge):
                added_edges += 1

        self.knowledge_base_loaded = True
        load_time = time.time() - start

        return {
            "status": "success",
            "nodes_loaded": len(nodes),
            "edges_loaded": added_edges,
            "load_time_ms": round(load_time * 1000, 2)
        }

    def analyze(self, query: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze a query against the knowledge base"""
        start = time.time()
        self.query_count += 1

        if not self.knowledge_base_loaded:
            return {
                "status": "error",
                "error": "Knowledge base not loaded"
            }

        # Simple keyword-based node lookup
        results = []
        query_lower = query.lower()

        for node in self.graph:
            score = 0
            if query_lower in node.title.lower():
                score += 0.5
            if query_lower in node.content.lower():
                score += 0.3
            if any(query_lower in tag.lower() for tag in node.tags):
                score += 0.2

            if score > 0:
                results.append({
                    "id": node.id,
                    "title": node.title,
                    "layer": node.layer.value,
                    "score": round(score, 3),
                    "snippet": node.content[:200] + "..." if len(node.content) > 200 else node.content
                })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        execution_time = time.time() - start

        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": results[:10],  # Return top 10
            "execution_time_ms": round(execution_time * 1000, 2)
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        uptime = time.time() - self.start_time

        return {
            "status": "success",
            "version": "4.0.0",
            "uptime_seconds": round(uptime, 2),
            "query_count": self.query_count,
            "knowledge_base_loaded": self.knowledge_base_loaded,
            "graph_stats": {
                "nodes": self.graph.node_count,
                "edges": self.graph.edge_count
            }
        }

    def validate(self, node_id: str) -> Dict[str, Any]:
        """Validate a node against Ω级 rules"""
        node = self.graph.get_node(node_id)

        if not node:
            return {
                "status": "error",
                "error": f"Node {node_id} not found"
            }

        # Simple validation checks
        violations = []
        warnings = []

        # Check for absolute claims
        absolute_terms = ["100%", "绝对", "永远", "终极", "完美"]
        for term in absolute_terms:
            if term in node.content:
                violations.append(f"Contains absolute term: '{term}'")

        # Check content length
        if len(node.content) < 50:
            warnings.append("Content is very short")

        # Check layer consistency
        if node.layer == LayerTier.L1_CORE and node.node_type != NodeType.AXIOM:
            warnings.append("L1 node should be AXIOM type")

        score = max(0, 1.0 - len(violations) * 0.2)

        return {
            "status": "success",
            "node_id": node_id,
            "validation": {
                "is_valid": len(violations) == 0,
                "score": round(score, 2),
                "violations": violations,
                "warnings": warnings
            }
        }

class APIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Symbolic Engine API"""

    engine = SymbolicEngineAPI()

    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._send_json({"status": "healthy", "engine": "v4.0.0"})

        elif path == "/stats":
            result = self.engine.get_stats()
            self._send_json(result)

        elif path == "/analyze":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            if query:
                result = self.engine.analyze(query)
                self._send_json(result)
            else:
                self._send_json({"status": "error", "error": "Missing query parameter 'q'"}, 400)

        else:
            self._send_json({"status": "error", "error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"status": "error", "error": "Invalid JSON"}, 400)
            return

        if path == "/load":
            directory = data.get("directory", r"C:\MSS-AI-Project\knowledge_base")
            result = self.engine.load_knowledge_base(directory)
            self._send_json(result)

        elif path == "/analyze":
            query = data.get("query", "")
            options = data.get("options", {})
            if query:
                result = self.engine.analyze(query)
                self._send_json(result)
            else:
                self._send_json({"status": "error", "error": "Missing query"}, 400)

        elif path == "/validate":
            node_id = data.get("node_id", "")
            if node_id:
                result = self.engine.validate(node_id)
                self._send_json(result)
            else:
                self._send_json({"status": "error", "error": "Missing node_id"}, 400)

        else:
            self._send_json({"status": "error", "error": "Not found"}, 404)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def start_server(host: str = "localhost", port: int = 8848):
    """Start the API server"""
    server = HTTPServer((host, port), APIHandler)
    print(f"MSS Symbolic Engine v4.0 API Server")
    print(f"Running at http://{host}:{port}")
    print(f"Endpoints:")
    print(f"  GET  /health       - Health check")
    print(f"  GET  /stats        - Engine statistics")
    print(f"  GET  /analyze?q=   - Analyze query")
    print(f"  POST /load         - Load knowledge base")
    print(f"  POST /analyze      - Analyze query")
    print(f"  POST /validate     - Validate node")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    start_server()
