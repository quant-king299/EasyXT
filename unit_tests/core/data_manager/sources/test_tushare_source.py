# -*- coding: utf-8 -*-
"""
TushareSource 单元测试

测试 TushareSource.get_price() 的列校验逻辑，
这些测试不依赖真实 Tushare API。
"""

import pandas as pd
import pytest

from core.data_manager.sources.tushare_source import TushareSource


@pytest.fixture
def source():
    """返回一个已连接、可用 token 的 TushareSource 实例"""
    src = TushareSource(config={
        'token': 'test_token',
        'api_delay': 0,  # 避免测试中出现真实睡眠
    })
    src.is_connected = True
    return src


@pytest.fixture
def make_daily(source):
    """辅助构造：mock _connection.daily 返回指定 DataFrame"""
    def _make_daily(df):
        fake_conn = type('FakeConnection', (), {'daily': lambda *args, **kwargs: df})()
        source._connection = fake_conn
        return fake_conn
    return _make_daily


class TestTushareSourceGetPriceColumns:
    """测试 get_price() 的列校验行为"""

    def test_returns_dataframe_with_all_columns(self, source, make_daily):
        """所有必要列和可选列都存在时，返回完整 DataFrame"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'high': [11.0],
            'low': [9.0],
            'close': [10.5],
            'vol': [1000],
            'amount': [10500.0],
        })
        make_daily(df)

        result = source.get_price('000001', '20240101', '20240101')

        assert result is not None
        assert list(result.columns) == [
            'symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount'
        ]
        assert result['symbol'].iloc[0] == '000001.SZ'
        assert result['date'].iloc[0] == '20240101'

    def test_returns_none_when_symbol_missing(self, source, make_daily):
        """缺少 symbol 列时返回 None"""
        df = pd.DataFrame({
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.5],
        })
        make_daily(df)

        result = source.get_price('000001', '20240101', '20240101')

        assert result is None

    def test_returns_none_when_date_missing(self, source, make_daily):
        """缺少 date 列时返回 None"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'open': [10.0],
            'close': [10.5],
        })
        make_daily(df)

        result = source.get_price('000001', '20240101', '20240101')

        assert result is None

    def test_returns_available_optional_columns_only(self, source, make_daily):
        """只缺少部分可选列时，返回必要列 + 存在的可选列"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.5],
        })
        make_daily(df)

        result = source.get_price('000001', '20240101', '20240101')

        assert result is not None
        assert list(result.columns) == ['symbol', 'date', 'open', 'close']

    def test_returns_none_when_empty_dataframe(self, source, make_daily):
        """返回空 DataFrame 时返回 None"""
        df = pd.DataFrame()
        make_daily(df)

        result = source.get_price('000001', '20240101', '20240101')

        assert result is None

    def test_returns_none_when_both_required_missing(self, source, make_daily):
        """必要列全部缺失时返回 None"""
        df = pd.DataFrame({
            'open': [10.0],
            'close': [10.5],
        })
        make_daily(df)

        result = source.get_price('000001', '20240101', '20240101')

        assert result is None
