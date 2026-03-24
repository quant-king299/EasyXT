"""
策略配置文件

从YAML配置自动生成
"""

# 回测参数
BACKTEST_CONFIG = {'start_date': '20240102', 'end_date': '20241231', 'initial_cash': 1000000, 'commission': 0.001, 'slippage': 0.001}

# 股票池配置
UNIVERSE_CONFIG = {'type': 'index', 'index_code': '399101.SZ'}

# 打分因子配置
SCORING_FACTORS_CONFIG = [
    {
        'name': '市值因子',
        'factor_type': 'fundamental',
        'field': 'market_cap',
        'direction': -1,
        'weight': 1.0,
        'normalize': True,
        'neutralize': {'enabled': False}
    }
]

# 组合构建配置
PORTFOLIO_CONFIG = {'select_method': 'top_n', 'top_n': 10, 'weight_method': 'equal', 'risk_control': {'max_position_count': 20, 'max_single_weight': 0.2, 'min_single_weight': 0.05}}

# 调仓配置
REBALANCE_CONFIG = {'frequency': 'monthly', 'rebalance_day': 1, 'trade_time': 'open', 'execution': {'type': 'close', 'max_trade_ratio': 0.2}}