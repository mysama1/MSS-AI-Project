"""Production pipeline smoke test."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mssclaw.core.pipeline import StreamingPipeline, PipeNode, PipeStatus, ProductionConfig

# Test 1: Retry
config = ProductionConfig(max_retries=2, retry_delay_ms=10, circuit_breaker_threshold=10)
pl = StreamingPipeline("retry_test", config)
attempts = {"count": 0}
def flaky(ctx):
    attempts["count"] += 1
    if attempts["count"] == 1: raise RuntimeError("transient")
    return {"recovered": True}
pl.add_node(PipeNode("flaky", flaky, retry_count=2), is_start=True)
r = pl.run_production()
assert pl.results["flaky"].status == PipeStatus.DONE, f"FAIL: {pl.results['flaky'].status}"
print("✅ Test 1: Retry")

# Test 2: Circuit Breaker
pl2 = StreamingPipeline("cb_test", ProductionConfig(max_retries=1, circuit_breaker_threshold=2))
pl2.add_node(PipeNode("b1", lambda ctx: 1/0), is_start=True)
pl2.add_node(PipeNode("b2", lambda ctx: 1/0, fallback_pipe="b3"), after=["b1"])
pl2.add_node(PipeNode("b3", lambda ctx: 1/0), after=["b2"])
r2 = pl2.run_production()
assert r2["circuit_breaker"]["tripped"], "Circuit breaker not tripped"
print("✅ Test 2: Circuit Breaker")

# Test 3: Fallback
pl3 = StreamingPipeline("fallback_test")
pl3.add_node(PipeNode("risk", lambda ctx: 1/0, fallback_pipe="safe"), is_start=True)
pl3.add_node(PipeNode("safe", lambda ctx: {"ok": True}))
r3 = pl3.run_production()
assert pl3.results["safe"].status == PipeStatus.DONE
print("✅ Test 3: Fallback")

# Test 4: Summary
print("\n" + pl3.summary())

print("\n🎉 ALL 4 TESTS PASSED")
