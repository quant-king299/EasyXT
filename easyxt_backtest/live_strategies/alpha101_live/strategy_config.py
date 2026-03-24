"""
策略配置文件

从YAML配置自动生成
"""

# 回测参数
BACKTEST_CONFIG = {'start_date': '20200101', 'end_date': '20231231', 'initial_cash': 1000000, 'commission': 0.001, 'slippage': 0.001}

# 股票池配置
UNIVERSE_CONFIG = {'type': 'index', 'index_code': '000852.SH'}

# 打分因子配置
SCORING_FACTORS_CONFIG = [
    {
        'name': 'Alpha001',
        'factor_type': 'alpha101',
        'field': 'alpha001',
        'direction': 1,
        'weight': 0.4,
        'normalize': True,
        'neutralize': {'enabled': True, 'by': ['industry', 'market_cap']}
    },    {
        'name': 'Alpha006',
        'factor_type': 'alpha101',
        'field': 'alpha006',
        'direction': 1,
        'weight': 0.3,
        'normalize': True,
        'neutralize': {'enabled': True, 'by': ['industry']}
    },    {
        'name': 'Alpha014',
        'factor_type': 'alpha101',
        'field': 'alpha014',
        'direction': 1,
        'weight': 0.3,
        'normalize': True,
        'neutralize': {'enabled': True, 'by': ['industry']}
    }
]

# 组合构建配置
PORTFOLIO_CONFIG = {'select_method': 'top_n', 'top_n': 20, 'weight_method': 'equal', 'risk_control': {'max_position_count': 30, 'max_single_weight': 0.1, 'min_single_weight': 0.02}}

# 调仓配置
REBALANCE_CONFIG = {'frequency': 'monthly', 'rebalance_day': 1, 'trade_time': 'close', 'execution': {'type': 'close', 'max_trade_ratio': 0.25}}