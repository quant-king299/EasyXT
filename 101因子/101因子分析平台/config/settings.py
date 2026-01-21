"""
101因子分析平台 - 项目配置文件
"""
import os
from pathlib import Path

# 项目根路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 数据路径配置
DATA_CONFIG = {
    'raw_data_path': PROJECT_ROOT / 'data' / 'raw',
    'processed_data_path': PROJECT_ROOT / 'data' / 'processed',
    'factor_data_path': PROJECT_ROOT / 'data' / 'factors',
    'cache_path': PROJECT_ROOT / 'data' / 'cache',
    'temp_path': PROJECT_ROOT / 'data' / 'temp'
}

# 因子计算配置
FACTOR_CONFIG = {
    'default_window': 30,  # 默认时间窗口
    'min_window': 5,       # 最小时间窗口
    'max_window': 252,     # 最大时间窗口（一年）
    'neutralization_method': 'industry',  # 中性化方法
    'standardization_method': 'zscore',   # 标准化方法
    'winsorize_limits': (0.025, 0.025), # Winsorize比例
    'factor_quantiles': 5,  # 分层数量
    'top_quantile': 0.1,    # 做多比例
    'bottom_quantile': 0.1, # 做空比例
    'transaction_cost': 0.001  # 交易成本
}

# 回测配置
BACKTEST_CONFIG = {
    'initial_capital': 1000000,  # 初始资金
    'rebalance_frequency': 'monthly',  # 调仓频率
    'benchmark_symbol': '000300.SH',  # 基准指数
    'risk_free_rate': 0.03,  # 无风险利率
    'trading_days_per_year': 252,  # 每年交易日
    'slippage': 0.0005,  # 滑点
    'max_position_size': 0.1  # 最大仓位比例
}

# 数据源配置
DATA_SOURCE_CONFIG = {
    'primary_source': 'easyxt',  # 主要数据源
    'backup_sources': ['local', 'tushare'],  # 备用数据源
    'data_frequency': 'daily',  # 数据频率
    'adjustment': 'post',  # 复权方式
    'timezone': 'Asia/Shanghai',  # 时区
    'delay_minutes': 0  # 数据延迟分钟数
}

# 缓存配置
CACHE_CONFIG = {
    'enable_cache': True,  # 启用缓存
    'cache_ttl': 3600,     # 缓存生存时间（秒）
    'cache_size_limit': 1024 * 1024 * 500,  # 缓存大小限制（500MB）
    'compress_cache': True,  # 压缩缓存
    'cache_backend': 'disk'  # 缓存后端（disk/memory）
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': PROJECT_ROOT / 'logs' / 'factor_platform.log',
    'max_bytes': 1024 * 1024 * 10,  # 10MB
    'backup_count': 5,
    'console_output': True
}

# 性能配置
PERFORMANCE_CONFIG = {
    'use_multiprocessing': True,  # 使用多进程
    'max_workers': os.cpu_count(),  # 最大工作进程数
    'chunk_size': 1000,  # 数据块大小
    'enable_caching': True,  # 启用计算缓存
    'memory_limit': 1024 * 1024 * 1024 * 8,  # 8GB内存限制
    'timeout_seconds': 300  # 计算超时时间（秒）
}

# API配置
API_CONFIG = {
    'host': '127.0.0.1',
    'port': 8000,
    'debug': False,
    'workers': 1,
    'cors_origins': ['*'],
    'api_prefix': '/api/v1'
}

# 完整配置
CONFIG = {
    'data': DATA_CONFIG,
    'factor': FACTOR_CONFIG,
    'backtest': BACKTEST_CONFIG,
    'data_source': DATA_SOURCE_CONFIG,
    'cache': CACHE_CONFIG,
    'logging': LOGGING_CONFIG,
    'performance': PERFORMANCE_CONFIG,
    'api': API_CONFIG
}


def get_config(section: str = None):
    """
    获取配置
    
    Args:
        section: 配置部分名称，如果为None则返回完整配置
        
    Returns:
        配置字典
    """
    if section:
        return CONFIG.get(section, {})
    else:
        return CONFIG


def update_config(section: str, updates: dict):
    """
    更新配置
    
    Args:
        section: 配置部分名称
        updates: 更新的配置项
    """
    if section in CONFIG:
        CONFIG[section].update(updates)


# 环境特定配置
ENVIRONMENT = os.getenv('FACTOR_PLATFORM_ENV', 'development')

if ENVIRONMENT == 'production':
    # 生产环境配置
    CONFIG['logging']['level'] = 'WARNING'
    CONFIG['performance']['max_workers'] = os.cpu_count()
    CONFIG['cache']['enable_cache'] = True
elif ENVIRONMENT == 'testing':
    # 测试环境配置
    CONFIG['logging']['level'] = 'DEBUG'
    CONFIG['performance']['max_workers'] = 2
    CONFIG['factor']['default_window'] = 10
else:
    # 开发环境配置
    CONFIG['logging']['level'] = 'DEBUG'
    CONFIG['performance']['max_workers'] = 4
    CONFIG['cache']['enable_cache'] = False


if __name__ == '__main__':
    # 测试配置
    print("项目配置信息:")
    print(f"项目根路径: {PROJECT_ROOT}")
    print(f"数据路径: {CONFIG['data']['raw_data_path']}")
    print(f"因子配置: {CONFIG['factor']}")
    print(f"当前环境: {ENVIRONMENT}")
    
    # 测试获取特定配置
    factor_cfg = get_config('factor')
    print(f"因子配置: {factor_cfg}")
    
    print("配置加载成功!")