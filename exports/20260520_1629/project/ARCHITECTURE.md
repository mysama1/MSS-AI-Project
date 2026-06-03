# MSS-AI Architecture Documentation

## System Design Principles

### 1. Deterministic Symbolic Core
- All reasoning operations are deterministic and reproducible
- No probabilistic inference in core symbolic engine
- Knowledge graph provides formal semantic foundation

### 2. Layered Compliance
- L1 (Hardcore): 17 axioms - immutable foundation
- L2 (Protective Belt): 16 rules - adjustable framework
- L3 (Heuristic): 13 guidelines - context-dependent

### 3. Zero-Hallucination Guarantee
- All outputs traceable to knowledge base entries
- Every inference step auditable
- Confidence scores based on structural metrics, not softmax

## Component Interactions

### Request Flow

```
User Input
    │
    ▼
┌─────────────┐
│   Parser    │ ──→ Detect command type (chat/analyze/reason/scan)
└─────────────┘
    │
    ▼
┌─────────────┐
│ NL Bridge   │ ──→ Intent recognition, entity extraction
│   (V2)      │ ──→ Layer classification, query translation
└─────────────┘
    │
    ▼
┌─────────────┐
│   Arbiter   │ ──→ Ω-compliance check (36 rules)
│   Agent     │ ──→ Forbidden word detection
│             │ ──→ RSCA compliance scoring
└─────────────┘
    │
    ▼
┌─────────────┐
│  Responder  │ ──→ Symbolic reasoning / LLM generation
│   Agent     │ ──→ Post-processing (37 rules)
│             │ ──→ Confidence/layer/boundary annotation
└─────────────┘
    │
    ▼
┌─────────────┐
│  Formatter  │ ──→ Response formatting (plain/markdown/json)
└─────────────┘
    │
    ▼
User Output
```

### Data Flow

```
Knowledge Base (JSONL)
    │
    ▼
KB Loader ──→ ConceptNode objects
    │
    ▼
Symbolic Engine ──→ Graph structure (nodes + edges)
    │
    ▼
Reasoning Operations
    ├── Transitive closure
    ├── Path finding
    ├── Cycle detection
    └── Layer validation
```

## Key Algorithms

### 1. Transitive Reasoning
```python
def find_path(start, end, max_depth=5):
    """BFS-based path finding with layer validation"""
    queue = [(start, [start])]
    visited = {start}
    
    while queue:
        node, path = queue.pop(0)
        if node == end:
            return path
        
        for neighbor in graph.get_neighbors(node):
            if neighbor not in visited and len(path) < max_depth:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    
    return None  # No path found
```

### 2. Heat Tax Calculation
```python
def calculate_heat_tax(cut_number, depth, gamma0=0.3):
    """γ(n,D) = γ₀ × D^(-n)"""
    return gamma0 * (depth ** (-cut_number))
```

### 3. Percolation Analysis
```python
def estimate_critical_point(grid_size=50, n_samples=20):
    """Bisection method for p_c estimation"""
    p_values = linspace(0.3, 0.7, n_samples)
    results = [run_percolation(p, grid_size) for p in p_values]
    
    # Find where percolation probability crosses 0.5
    for i in range(len(results) - 1):
        if results[i] < 0.5 and results[i+1] >= 0.5:
            return (p_values[i] + p_values[i+1]) / 2
    
    return None
```

## Performance Characteristics

| Operation | Time Complexity | Space Complexity | Typical Time |
|-----------|----------------|------------------|--------------|
| KB Loading | O(n) | O(n) | ~200ms |
| Path Finding | O(b^d) | O(b^d) | ~10ms |
| Compliance Check | O(m × k) | O(1) | ~5ms |
| Percolation (50×50) | O(n²) | O(n²) | ~50ms |
| ETA Dynamics | O(t) | O(1) | ~10ms |

Where:
- n = number of KB entries
- b = branching factor (~3)
- d = max depth (5)
- m = text length
- k = number of rules (37)
- t = iterations (1000)

## Error Handling

### Exception Hierarchy
```
MSSException (base)
├── MSSConfigError
├── MSSKnowledgeError
├── MSSReasoningError
├── MSSComplianceError
├── MSSThermalDeathError
└── MSSRuntimeError
```

### Recovery Strategies
1. **Config Error**: Use default values, log warning
2. **KB Error**: Skip invalid entries, continue loading
3. **Reasoning Error**: Return UNDETERMINED status
4. **Compliance Error**: Trigger rewrite cycle (max 3)
5. **Thermal Death**: Halt operation, require manual reset
6. **Runtime Error**: Log error, attempt graceful degradation

## Security Considerations

### Input Validation
- All user inputs sanitized before processing
- Maximum text length enforced (50KB)
- Command injection prevention via strict parsing

### Output Encoding
- UTF-8 encoding throughout
- HTML escaping for web output
- JSON serialization for API responses

### Access Control
- CLI: Local execution only
- API: CORS configured for specific origins
- No authentication in current version (add for production)

## Deployment Options

### 1. Local Development
```bash
pip install -r requirements.txt
python interactive_cli.py
```

### 2. Web Server
```bash
pip install -r requirements.txt
uvicorn web_api:app --host 0.0.0.0 --port 8000
```

### 3. Docker (Future)
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Monitoring

### Health Metrics
- CPU usage (threshold: 80%)
- Memory usage (threshold: 85%)
- Disk space (threshold: 90%)
- Request success rate (threshold: 95%)

### Alert Levels
- **CRITICAL**: System halt required
- **DEGRADED**: Reduced functionality
- **NORMAL**: Full operation
- **OPTIMAL**: Peak performance

## Future Enhancements

### Short Term (v1.1)
- [ ] Numba JIT acceleration for simulations
- [ ] Matplotlib/Plotly chart export
- [ ] WebSocket real-time updates
- [ ] Docker containerization

### Medium Term (v1.5)
- [ ] Distributed knowledge base
- [ ] GPU acceleration for large graphs
- [ ] Multi-language support
- [ ] Advanced visualization dashboard

### Long Term (v2.0)
- [ ] Quantum computing integration
- [ ] Federated learning support
- [ ] Autonomous theory discovery
- [ ] Cross-modal reasoning (text + image)
