# -*- coding: utf-8 -*-
"""
QMTSource 单元测试

测试 QMT 数据源的状态判断和生命周期管理，
这些测试不依赖 xtquant 环境。
"""

import pytest
from core.data_manager.sources.qmt_source import QMTSource


@pytest.fixture
def source():
    """返回一个未连接的 QMTSource 实例"""
    return QMTSource(config={})


class TestQMTSourceIsAvailable:
    """测试 is_available() 行为"""

    def test_is_available_returns_true_when_connected(self, source):
        """连接状态为 True 时，is_available() 应返回 True"""
        source.is_connected = True
        assert source.is_available() is True

    def test_is_available_returns_false_when_not_connected(self, source):
        """连接状态为 False 时，is_available() 应返回 False"""
        source.is_connected = False
        assert source.is_available() is False

    def test_is_available_does_not_call_xtdata(self, source, monkeypatch):
        """is_available() 不应再调用 xtdata API 做真实探测"""
        probe_called = False

        def fake_get_market_data_ex(*args, **kwargs):
            nonlocal probe_called
            probe_called = True
            return None

        fake_xtdata = type('FakeXtdata', (), {
            'get_market_data_ex': fake_get_market_data_ex
        })()
        monkeypatch.setitem(__import__('sys').modules, 'xtquant.xtdata', fake_xtdata)
        monkeypatch.setitem(__import__('sys').modules, 'xtquant', type('xtquant', (), {'xtdata': fake_xtdata})())

        source.is_connected = True
        result = source.is_available()

        assert result is True
        assert probe_called is False, "is_available() 不应调用 xtdata API"


class TestQMTSourceClose:
    """测试 close() 行为"""

    def test_close_resets_is_connected(self, source):
        """close() 应将 is_connected 重置为 False"""
        source.is_connected = True
        source.close()
        assert source.is_connected is False

    def test_close_clears_cache(self, source):
        """close() 应清空内部缓存"""
        source._cache['key'] = 'value'
        source.close()
        assert source._cache == {}

    def test_close_resets_last_used(self, source):
        """close() 应将 _last_used 重置为 None"""
        source._last_used = '2024-01-01'
        source.close()
        assert source._last_used is None

    def test_close_after_close_stays_inactive(self, source):
        """多次调用 close() 后状态应保持 inactive"""
        source.is_connected = True
        source.close()
        source.close()
        assert source.is_connected is False
        assert source.is_available() is False
