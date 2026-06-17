"""
pytest tests for H648 defer_guard — 逆优先级闭锁协议
"""
import sys
sys.path.insert(0, '.')
import pytest
from mssclaw.core.defer_guard import (
    DeferGuard, DeferState, get_guard, reset_guard,
    auto_register_dangerous_actions, DANGEROUS_ACTIONS
)


class TestDeferGuardBasic:
    """基础生命周期测试."""

    def setup_method(self):
        reset_guard()

    def test_register_and_check_blocked(self):
        g = DeferGuard()
        g.register('restart', ['push', 'commit'])
        ok, missing = g.can_execute('restart')
        assert not ok
        assert missing == {'push', 'commit'}

    def test_partial_satisfy_still_blocked(self):
        g = DeferGuard()
        g.register('restart', ['push', 'commit', 'artifact'])
        g.satisfy('push')
        ok, missing = g.can_execute('restart')
        assert not ok
        assert missing == {'commit', 'artifact'}

    def test_all_satisfied_releases(self):
        g = DeferGuard()
        g.register('restart', ['push', 'commit'])
        g.satisfy('push')
        g.satisfy('commit')
        ok, _ = g.can_execute('restart')
        assert ok

    def test_execute_success(self):
        g = DeferGuard()
        g.register('restart', ['push'])
        g.satisfy('push')
        ok, msg = g.execute('restart')
        assert ok
        assert 'executing' in msg

    def test_execute_blocked(self):
        g = DeferGuard()
        g.register('restart', ['push'])
        ok, msg = g.execute('restart')
        assert not ok
        assert 'BLOCKED' in msg


class TestDeferGuardForce:
    """紧急覆盖测试."""

    def setup_method(self):
        reset_guard()

    def test_force_override(self):
        g = DeferGuard()
        g.register('shutdown', ['drain'])
        ok, msg = g.execute('shutdown', force=True, force_reason='emergency')
        assert ok
        assert 'FORCED' in msg


class TestDeferGuardDangerousActions:
    """预定义危险操作测试."""

    def setup_method(self):
        reset_guard()

    def test_all_five_registered(self):
        g = DeferGuard()
        auto_register_dangerous_actions(g)
        assert len(DANGEROUS_ACTIONS) == 5
        for name in DANGEROUS_ACTIONS:
            ok, missing = g.can_execute(name)
            assert not ok, f"{name} should be blocked initially"

    def test_gateway_restart_requires_three(self):
        g = DeferGuard()
        auto_register_dangerous_actions(g)
        _, missing = g.can_execute('gateway_restart')
        assert missing == {'git_push', 'artifact_write', 'commit'}


class TestDeferGuardStatus:
    """状态查询测试."""

    def setup_method(self):
        reset_guard()

    def test_status_empty(self):
        g = DeferGuard()
        s = g.status()
        assert s['completed'] == []
        assert s['ready_count'] == 0
        assert s['blocked_count'] == 0

    def test_status_with_registered(self):
        g = DeferGuard()
        g.register('a', ['x'])
        g.register('b', ['y'])
        s = g.status()
        assert s['blocked_count'] == 2

    def test_status_after_satisfy(self):
        g = DeferGuard()
        g.register('a', ['x'])
        g.satisfy('x')
        s = g.status()
        assert s['ready_count'] == 1
        assert s['blocked_count'] == 0
