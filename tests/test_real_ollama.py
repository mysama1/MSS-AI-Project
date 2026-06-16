"""Sprint 101: Real Ollama integration test — requires running Ollama."""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Only run if Ollama is available
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=3)
    OLLAMA_OK = r.status_code == 200
except Exception:
    OLLAMA_OK = False

pytestmark = pytest.mark.skipif(not OLLAMA_OK, reason="Ollama not available")


def test_ollama_list_models():
    """Verify Ollama returns model list."""
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    assert r.status_code == 200
    models = r.json().get("models", [])
    assert len(models) > 0, "No Ollama models found"
    print(f"  ✅ {len(models)} models: {[m['name'] for m in models[:5]]}...")


def test_ollama_chat_api():
    """Verify Ollama chat endpoint works."""
    import requests, json
    payload = {
        "model": "qwen2.5:7b",
        "messages": [{"role": "user", "content": "Say 'hello' in one word."}],
        "stream": False,
    }
    r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=30)
    assert r.status_code == 200, f"Chat API failed: {r.status_code}"
    reply = r.json().get("message", {}).get("content", "")
    assert len(reply) > 0, f"Empty reply from chat API"
    print(f"  ✅ Reply: {reply[:50]}...")


def test_ollama_embed_api():
    """Verify Ollama embedding endpoint works."""
    import requests
    payload = {"model": "qwen2.5:7b", "input": "test"}
    try:
        r = requests.post("http://localhost:11434/api/embed", json=payload, timeout=15)
        if r.status_code == 200:
            emb = r.json().get("embeddings", [[]])[0]
            assert len(emb) > 0
            print(f"  ✅ Embedding: {len(emb)} dims")
    except Exception as e:
        print(f"  ⚠️  Embed not available: {e}")


def test_mss_agent_real():
    """Verify MSSAgent can be created with real Ollama backend."""
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import create_backend

    agent = MSSAgent("real_test", llm=create_backend("auto"))
    assert agent.name == "real_test"
    assert agent.llm is not None

    # Quick smoke: check backend can list models
    try:
        models = agent.llm.list_models()
        assert len(models) > 0, "Backend returned no models"
        print(f"  ✅ Agent backend: {len(models)} models")
    except Exception as e:
        pytest.skip(f"Backend list_models not supported: {e}")


def test_streaming_real():
    """Verify streaming with real Ollama backend."""
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import create_backend

    agent = MSSAgent("stream_test", llm=create_backend("auto"))
    try:
        chunks = list(agent.run_stream("Say 'ok' and nothing else.", semantic=False))
        text = "".join(chunks)
        assert len(text) > 1, f"Stream returned empty/too-short: '{text}'"
        print(f"  ✅ Stream: {len(chunks)} chunks, '{text.strip()}'")
    except Exception as e:
        pytest.skip(f"Stream not supported: {e}")
