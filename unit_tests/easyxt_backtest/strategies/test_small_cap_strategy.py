#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小市值策略单元测试

测试目标：easyxt_backtest/strategies/small_cap_strategy.py
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from easyxt_backtest.strategies.small_cap_strategy import (
    SmallCapStrategy,
    SmallCapStrategyV2,
    logger,
)


def test_module_has_logger():
    """验证模块已正确定义 logger。"""
    assert logger is not None
    assert logger.name == 'easyxt_backtest.strategies.small_cap_strategy'


def test_small_cap_strategy_can_be_instantiated():
    """验证 SmallCapStrategy 实例化时不会因缺失 logger 而抛 NameError。"""
    strategy = SmallCapStrategy()
    assert strategy is not None
    assert strategy.index_code == '399101.SZ'
    assert strategy.select_num == 5
    assert strategy.rebalance_freq == 'monthly'


def test_small_cap_strategy_with_custom_params():
    """验证使用自定义参数实例化时 logger 正常工作。"""
    strategy = SmallCapStrategy(
        index_code='000300.SH',
        select_num=10,
        universe_size=100,
        rebalance_freq='weekly'
    )
    assert strategy.index_code == '000300.SH'
    assert strategy.select_num == 10
    assert strategy.universe_size == 100
    assert strategy.rebalance_freq == 'weekly'


class FakeDataManager:
    def __init__(self, components=None):
        self.components = components or []
        self.requested_codes = None

    def get_index_components(self, index_code, date):
        return self.components

    def get_fundamentals(self, codes, date, fields):
        self.requested_codes = codes
        return pd.DataFrame({"symbol": codes or [], "circ_mv": range(len(codes or []))})


def test_strict_mode_does_not_fallback_to_unverifiable_current_universe():
    manager = FakeDataManager()
    strategy = SmallCapStrategy(data_manager=manager)

    assert strategy.select_stocks("20200102") == []
    assert manager.requested_codes is None


def test_explicit_point_in_time_universe_includes_later_delisted_stock():
    history = pd.DataFrame({
        "symbol": ["OLD.SZ", "LIVE.SZ"],
        "effective_from": ["2010-01-01", "2010-01-01"],
        "effective_to": ["2020-12-31", "2099-12-31"],
    })
    manager = FakeDataManager()
    strategy = SmallCapStrategy(
        select_num=2,
        data_manager=manager,
        universe_history=history,
    )

    assert set(strategy.select_stocks("20200102")) == {"OLD.SZ", "LIVE.SZ"}
    assert manager.requested_codes == ["LIVE.SZ", "OLD.SZ"]


def test_v2_binds_constructor_arguments_correctly():
    manager = FakeDataManager(["000001.SZ"])
    strategy = SmallCapStrategyV2(
        rebalance_freq="weekly",
        data_manager=manager,
    )

    assert strategy.rebalance_freq == "weekly"
    assert strategy.data_manager is manager
    assert strategy.universe_size is None
