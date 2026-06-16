#!/usr/bin/env python3
"""MSS-AI Core Reasoning Service v1.0
Architecture: Core reasoning engine (zero system dependency)
Interface: REST /v1/reason | /v1/verify | /v1/infer
Backend: Ollama :11434/v1/chat/completions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import requests
import json
import re

app = FastAPI(title="MSS-AI Core", version="1.0.0")

# ===== Models =====

class ReasonRequest(BaseModel):
    ctx: str
    trace_id: Optional[str] = str(uuid.uuid4())
    mode: str = "strict"

class ReasonResponse(BaseModel):
    verdict: str
    basis: List[str]
    reasoning: List[str]
    trace_id: str

class VerifyRequest(BaseModel):
    proposition: str
    ctx: str
    trace_id: Optional[str] = str(uuid.uuid4())

class VerifyResponse(BaseModel):
    valid: bool
    confidence: float
    counter_examples: List[str]
    trace_id: str

class InferRequest(BaseModel):
    pattern: str
    ctx: str
    trace_id: Optional[str] = str(uuid.uuid4())

class InferResponse(BaseModel):
    result: str
    steps: List[Dict[str, Any]]
    trace_id: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    trace_id: str

# ===== Config =====

OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"
MODEL_NAME = "mss-ai-v3_6:latest"

SYSTEM_PROMPT = """You are MSS-AI Core Reasoning Engine. Output ONLY valid JSON with these fields:
- verdict: "YES", "NO", or "NEED_MORE_INFO"
- basis: array of references like ["[ref:...]"]
- reasoning: array of step-by-step logic like ["1) ...", "2) ..."]
Rules:
1. Input: receive ctx (context + constraints), do NOT fetch external info
2. Output: strict JSON, no extra text, no markdown, no think tags
3. No tool calls, no function calls, no Action/Observation
4. If ctx is empty or constraints conflict, output error JSON"""

# ===== Core =====

def call_ollama(system_prompt: str, user_ctx: str, trace_id: str) -> str:
    """Call Ollama for reasoning"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_ctx}
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048}
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]

def parse_response(text: str) -> Dict:
    """Parse model response JSON"""
    try:
        data = json.loads(text)
        return data
    except:
        pass

    # Try extracting JSON from text (handle markdown wrapping)
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass

    return {"verdict": "NEED_MORE_INFO", "basis": [], "reasoning": [f"Parse failed: {text[:100]}"]}

# ===== Routes =====

@app.post("/v1/reason", response_model=ReasonResponse)
async def reason(req: ReasonRequest):
    if not req.ctx or not req.ctx.strip():
        raise HTTPException(status_code=400, detail="ctx required")

    user_ctx = f"[CONTEXT]\n{req.ctx}\n\n[INSTRUCTION]\nAnalyze and output JSON with verdict/basis/reasoning."

    raw = call_ollama(SYSTEM_PROMPT, user_ctx, req.trace_id)
    result = parse_response(raw)

    return ReasonResponse(
        verdict=str(result.get("verdict", "NEED_MORE_INFO")),
        basis=result.get("basis", []),
        reasoning=result.get("reasoning", []),
        trace_id=req.trace_id
    )

@app.post("/v1/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest):
    if not req.proposition or not req.proposition.strip():
        raise HTTPException(status_code=400, detail="proposition required")

    user_ctx = f"[PROPOSITION]\n{req.proposition}\n\n[CONTEXT]\n{req.ctx}\n\n[INSTRUCTION]\nVerify if proposition holds. Output JSON with valid(bool)/confidence(float)/counter_examples(array)."

    raw = call_ollama(SYSTEM_PROMPT, user_ctx, req.trace_id)
    result = parse_response(raw)

    return VerifyResponse(
        valid=bool(result.get("valid", False)),
        confidence=float(result.get("confidence", 0.0)),
        counter_examples=result.get("counter_examples", []),
        trace_id=req.trace_id
    )

@app.post("/v1/infer", response_model=InferResponse)
async def infer(req: InferRequest):
    if not req.pattern or not req.pattern.strip():
        raise HTTPException(status_code=400, detail="pattern required")

    user_ctx = f"[PATTERN]\n{req.pattern}\n\n[CONTEXT]\n{req.ctx}\n\n[INSTRUCTION]\nInfer result from pattern. Output JSON with result(string)/steps(array of dicts)."

    raw = call_ollama(SYSTEM_PROMPT, user_ctx, req.trace_id)
    result = parse_response(raw)

    return InferResponse(
        result=str(result.get("result", "")),
        steps=result.get("steps", []),
        trace_id=req.trace_id
    )

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mss-ai-core", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
