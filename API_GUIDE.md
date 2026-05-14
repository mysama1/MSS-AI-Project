# MSS-AI API Guide

## Base URL
```
http://localhost:8000
```

## Authentication
Current version does not require authentication. Production deployments should add API key or OAuth2 authentication.

## Endpoints

### 1. Root Endpoint
```
GET /
```
Returns API information.

**Response:**
```json
{
  "name": "MSS-AI API",
  "version": "1.0.0",
  "status": "operational",
  "docs": "/docs"
}
```

### 2. Health Check
```
GET /health
```
Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1704067200.0,
  "uptime": 3600.0,
  "health_score": 0.92
}
```

### 3. Chat
```
POST /chat
```
Natural language conversation with MSS-AI.

**Request Body:**
```json
{
  "message": "Explain the A1 axiom",
  "session_id": "optional-session-id",
  "format": "markdown",
  "include_metadata": true
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message | string | Yes | User message (1-10000 chars) |
| session_id | string | No | Session ID for context persistence |
| format | string | No | Response format: plain/markdown/json (default: markdown) |
| include_metadata | boolean | No | Include reasoning metadata (default: true) |

**Response:**
```json
{
  "response": "A1 (Information Ontology) states that...",
  "intent": "explain_concept",
  "confidence": 0.95,
  "layer": "L1",
  "processing_time": 0.123,
  "session_id": "optional-session-id"
}
```

### 4. Analyze Text
```
POST /analyze
```
Analyze text for MSS compliance.

**Request Body:**
```json
{
  "text": "This text contains an ultimate solution...",
  "claimed_layer": "L2"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| text | string | Yes | Text to analyze (1-50000 chars) |
| claimed_layer | string | No | Claimed MSS layer if known |

**Response:**
```json
{
  "layer": "L3",
  "confidence": 0.78,
  "rsca_compliance": 0.65,
  "forbidden_words": ["ultimate", "solution"],
  "boundary_note": "Contains L2 vocabulary with L3 structure",
  "rewrite_needed": true
}
```

### 5. Symbolic Reasoning
```
POST /reason
```
Execute deterministic symbolic reasoning.

**Request Body:**
```json
{
  "query": "A1 implies T1",
  "start_node": "A1",
  "end_node": "T1",
  "max_depth": 5
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | Yes | Reasoning query |
| start_node | string | No | Starting concept node |
| end_node | string | No | Target concept node |
| max_depth | integer | No | Maximum search depth (1-10, default: 5) |

**Response:**
```json
{
  "status": "PROVEN",
  "path_length": 3,
  "steps": ["A1", "L1-001", "T1"],
  "confidence": 0.92,
  "processing_time": 0.045
}
```

**Status Values:**
- `PROVEN`: Path found with full confidence
- `SUPPORTED`: Path found with partial confidence
- `UNDETERMINED`: No path found
- `CONTRADICTED`: Contradiction detected

### 6. Organizational Scan
```
POST /scan
```
Run organizational resilience scan.

**Request Body:**
```json
{
  "organization_name": "Example Corp",
  "departments": [
    {"name": "R&D", "size": 50, "budget": 1000000},
    {"name": "Marketing", "size": 30, "budget": 500000}
  ],
  "use_demo": false
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| organization_name | string | Yes | Organization name |
| departments | array | No | Department data array |
| use_demo | boolean | No | Use demo data (default: false) |

**Response:**
```json
{
  "organization": "Example Corp",
  "overall_level": "DEGRADED",
  "phi_score": 0.72,
  "departments": 2,
  "diagnoses": ["R&D: Healthy", "Marketing: At Risk"],
  "recommendations": ["Increase Marketing budget", "Add cross-functional teams"],
  "processing_time": 0.234
}
```

### 7. System Status
```
GET /status
```
Returns comprehensive system status.

**Response:**
```json
{
  "status": "operational",
  "version": "1.0",
  "uptime": 7200.5,
  "health_score": 0.91,
  "knowledge_base_entries": 312,
  "tests_passed": 308,
  "tests_total": 308
}
```

### 8. Model Switch
```
POST /model/switch
```
Switch AI model dynamically.

**Request Body:**
```json
{
  "model_name": "mss-ai-v1"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| model_name | string | Yes | Model name to switch to |

**Response:**
```json
{
  "success": true,
  "previous_model": "qwen2.5:7b",
  "current_model": "mss-ai-v1",
  "message": "Model switched from qwen2.5:7b to mss-ai-v1"
}
```

### 9. Knowledge Base Summary
```
GET /knowledge-base
```
Returns knowledge base statistics.

**Response:**
```json
{
  "total_entries": 312,
  "layer_distribution": {
    "L1": 119,
    "L2": 132,
    "L3": 61
  },
  "entry_ids": ["L1-001", "L1-002", "L2-001", ...]
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error description"
}
```

**HTTP Status Codes:**
| Code | Meaning | Typical Cause |
|------|---------|---------------|
| 200 | OK | Successful operation |
| 400 | Bad Request | Invalid request format |
| 422 | Validation Error | Missing required field |
| 500 | Internal Error | System error |
| 503 | Service Unavailable | Component not initialized |

## Rate Limiting
Current version does not implement rate limiting. Production deployments should add:
- Request rate limiting (e.g., 100 requests/minute)
- Concurrent connection limits
- Payload size restrictions

## Examples

### Python Client
```python
import requests

client = requests.Session()
base_url = "http://localhost:8000"

# Chat
response = client.post(f"{base_url}/chat", json={
    "message": "Explain A1 axiom",
    "format": "markdown"
})
print(response.json())

# Analyze
response = client.post(f"{base_url}/analyze", json={
    "text": "This is a test with ultimate solution"
})
print(response.json())

# Reason
response = client.post(f"{base_url}/reason", json={
    "query": "A1 implies T1",
    "max_depth": 5
})
print(response.json())
```

### JavaScript Client
```javascript
const baseUrl = 'http://localhost:8000';

// Chat
fetch(`${baseUrl}/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Explain A1 axiom',
    format: 'markdown'
  })
})
.then(r => r.json())
.then(data => console.log(data));

// Status
fetch(`${baseUrl}/status`)
  .then(r => r.json())
  .then(data => console.log(data));
```

### cURL Examples
```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello MSS-AI"}'

# Analyze
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Test text"}'

# Reason
curl -X POST http://localhost:8000/reason \
  -H "Content-Type: application/json" \
  -d '{"query": "A1 implies T1"}'

# Status
curl http://localhost:8000/status

# KB Summary
curl http://localhost:8000/knowledge-base
```

## WebSocket API (Future)

Real-time updates will be available via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'system_health'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Health update:', data);
};
```
