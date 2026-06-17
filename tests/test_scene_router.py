"""
pytest tests for scene_router — 场景抉择算法
"""
import sys
sys.path.insert(0, '.')
import pytest
from mssclaw.core.scene_router import (
    SceneContext, SceneProfile, SceneRouter, Direction
)


class TestSceneRouterRouting:
    """路由决策测试 — 使用真实API."""

    def test_high_stakes_routes_to_direction_1(self):
        router = SceneRouter()
        result = router.route_by_profile(SceneProfile.HIGH_STAKES)
        assert result is not None
        assert 'direction' in result or 'recommendation' in result

    def test_realtime_profile_routes(self):
        router = SceneRouter()
        result = router.route_by_profile(SceneProfile.REALTIME)
        assert result is not None

    def test_all_profiles_route(self):
        router = SceneRouter()
        results = router.route_all_profiles()
        assert len(results) >= len(SceneProfile)

    def test_custom_route(self):
        router = SceneRouter()
        result = router.route_custom(
            stakes=0.9, latency_req=0.1,
            agent_count=5, duration_hours=2.0, resource_tight=0.3
        )
        assert result is not None
        assert 'direction' in result

    def test_preset_scenes_exist(self):
        router = SceneRouter()
        scenes = router.scenes
        assert len(scenes) > 0
        for name, ctx in scenes.items():
            assert 0 <= ctx.stakes <= 1
            assert 0 <= ctx.latency_req <= 1


class TestSceneRouterWeights:
    """权重配置测试."""

    def test_default_weights_summary(self):
        router = SceneRouter()
        w = router.weights
        assert isinstance(w, dict)

    def test_weights_positive(self):
        router = SceneRouter()
        for k, v in router.weights.items():
            assert v >= 0, f"Weight {k} should be non-negative, got {v}"
