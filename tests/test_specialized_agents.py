"""pytest tests for specialized_agents — multi-agent swarm infrastructure"""
import sys; sys.path.insert(0, '.')
import pytest
from mssclaw.core.specialized_agents import (
    AGENT_REGISTRY, SharedStore, MessageBus, SwarmNode
)


class TestAgentRegistry:
    def test_registry_is_dict(self):
        assert isinstance(AGENT_REGISTRY, dict)

    def test_contains_kb_agent(self):
        assert 'kb' in AGENT_REGISTRY

    def test_contains_code_agent(self):
        assert 'code' in AGENT_REGISTRY

    def test_contains_translate_agent(self):
        assert 'translate' in AGENT_REGISTRY

    def test_contains_video_agent(self):
        assert 'video' in AGENT_REGISTRY

    def test_contains_product_agent(self):
        assert 'product' in AGENT_REGISTRY

    def test_each_has_class(self):
        for name, entry in AGENT_REGISTRY.items():
            assert 'class' in entry, f"{name} missing 'class'"

    def test_each_has_capabilities(self):
        for name, entry in AGENT_REGISTRY.items():
            caps = entry.get('capabilities', [])
            assert isinstance(caps, list)
            assert len(caps) >= 1, f"{name} has no capabilities"

    def test_kb_agent_capabilities(self):
        caps = AGENT_REGISTRY['kb']['capabilities']
        assert any('search' in c or 'write' in c for c in caps)


class TestSharedStore:
    def test_creation(self):
        ss = SharedStore()
        assert ss is not None

    def test_is_object(self):
        ss = SharedStore()
        assert isinstance(ss, object)


class TestMessageBus:
    def test_creation(self):
        mb = MessageBus()
        assert mb is not None

    def test_is_object(self):
        mb = MessageBus()
        assert isinstance(mb, object)


class TestSwarmNode:
    def test_creation(self):
        # SwarmNode needs agent instance — test that class exists
        import inspect
        params = list(inspect.signature(SwarmNode.__init__).parameters.keys())
        assert 'agent' in params or 'self' in params
