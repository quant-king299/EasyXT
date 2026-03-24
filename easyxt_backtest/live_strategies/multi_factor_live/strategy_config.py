"""
策略配置文件

从YAML配置自动生成
"""

# 回测参数
BACKTEST_CONFIG = {'start_date': '20200101', 'end_date': '20231231', 'initial_cash': 1000000, 'commission': 0.001, 'slippage': 0.001}

# 股票池配置
UNIVERSE_CONFIG = {'type': 'index', 'index_code': '000300.SH'}

# 打分因子配置
SCORING_FACTORS_CONFIG = [
    {
        'name': '市值因子',
        'factor_type': 'fundamental',
        'field': 'market_cap',
        'direction': -1,
        'weight': 0.5,
        'normalize': True,
        'neutralize': {'enabled': True, 'by': ['industry']}
    },    {
        'name': 'ROE因子',
        'factor_type': 'fundamental',
        'field': 'roe',
        'direction': 1,
        'weight': 0.3,
        'normalize': True,
        'neutralize': {'enabled': True, 'by': ['industry']}
    },    {
        'name': '动量因子',
        'factor_type': 'technical',
        'field': 'momentum_20',
        'direction': 1,
        'weight': 0.2,
        'normalize': True,
        'neutralize': {'enabled': False}
    }
]

# 组合构建配置
PORTFOLIO_CONFIG = {'select_method': 'top_n', 'top_n': 15, 'weight_method': 'equal', 'risk_control': {'max_position_count': 20, 'max_single_weight': 0.15, 'min_single_weight': 0.03, 'industry_max_weight': 0.4, 'max_turnover': 0.5}}

# 调仓配置
REBALANCE_CONFIG = {'frequency': 'quarterly', 'rebalance_day': 1, 'trade_time': 'close', 'execution': {'type': 'close', 'max_trade_ratio': 0.3}}