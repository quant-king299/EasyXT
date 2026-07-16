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

from easyxt_backtest.strategies.small_cap_strategy import SmallCapStrategy, logger


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
