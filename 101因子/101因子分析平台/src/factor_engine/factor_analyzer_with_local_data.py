# -*- coding: utf-8 -*-
"""
便捷因子分析接口
自动使用本地数据系统，大幅提升数据加载速度
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from pathlib import Path
import sys

# 导入本地数据管理
try:
    from ..data_manager import LocalDataManager, get_local_data_manager
    from .calculator_with_local_data import FactorCalculatorWithDataCache
except ImportError:
    # 备用导入路径
    project_root = Path(__file__).parents[2]
    sys.path.insert(0, str(project_root / 'src'))
    from data_manager import LocalDataManager, get_local_data_manager
    from factor_engine.calculator_with_local_data import FactorCalculatorWithDataCache


class EasyFactorAnalyzer:
    """
    便捷因子分析器

    功能：
    1. 自动使用本地缓存数据
    2. 便捷的因子计算接口
    3. 支持自定义因子
    4. 自动数据更新
    """

    def __init__(self, use_local_cache: bool = True):
        """
        初始化分析器

        Args:
            use_local_cache: 是否使用本地缓存
        """
        self.use_local_cache = use_local_cache

        # 创建带缓存的计算器
        self.calculator = FactorCalculatorWithDataCache(use_local_cache=use_local_cache)

        # 数据管理器
        self.data_manager = get_local_data_manager() if use_local_cache else None

        print(f"✅ 因子分析器已初始化 (本地缓存: {'启用' if use_local_cache else '禁用'})")

    def load_data(self,
                  symbols: Union[str, List[str]],
                  start_date: str,
                  end_date: str,
                  fields: List[str] = None) -> pd.DataFrame:
        """
        加载数据（自动使用本地缓存）

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fields: 字段列表

        Returns:
            DataFrame: 多级索引 [date, symbol]
        """
        return self.calculator.load_data(symbols, start_date, end_date, fields)

    def calculate_factor(self,
                        data: pd.DataFrame,
                        factor_name: str,
                        factor_func: callable = None,
                        **kwargs) -> pd.DataFrame:
        """
        计算因子

        Args:
            data: 价格数据
            factor_name: 因子名称
            factor_func: 因子计算函数
            **kwargs: 额外参数

        Returns:
            因子值DataFrame
        """
        if factor_func is None:
            # 使用默认因子计算方法
            if hasattr(self.calculator, 'calculate_factor'):
                return self.calculator.calculate_factor(data, factor_name, **kwargs)
            else:
                raise ValueError("未提供因子计算函数")
        else:
            # 使用自定义函数
            return factor_func(data, **kwargs)

    def ic_analysis(self,
                   factor_data: pd.DataFrame,
                   price_data: pd.DataFrame,
                   periods: int = 5) -> pd.DataFrame:
        """
        IC分析

        Args:
            factor_data: 因子数据
            price_data: 价格数据
            periods: 未来期数

        Returns:
            IC分析结果
        """
        # 导入IC分析模块
        try:
            from easy_xt.alpha_analysis.ic_ir_analysis import ICAnalyzer
            analyzer = ICAnalyzer()
            return analyzer.calculate_ic(factor_data, price_data, periods)
        except ImportError:
            # 简单IC计算
            return self._simple_ic_analysis(factor_data, price_data, periods)

    def _simple_ic_analysis(self, factor_data: pd.DataFrame,
                           price_data: pd.DataFrame,
                           periods: int = 5) -> pd.DataFrame:
        """简单的IC计算"""
        # 计算未来收益
        returns = price_data.pct_change(periods).shift(-periods)

        # 对齐数据
        common_dates = sorted(set(factor_data.index) & set(returns.index))
        common_stocks = sorted(set(factor_data.columns) & set(returns.columns))

        factor_aligned = factor_data.loc[common_dates, common_stocks]
        returns_aligned = returns.loc[common_dates, common_stocks]

        # 计算IC
        ic_series = factor_aligned.corrwith(returns_aligned, axis=1)

        result = pd.DataFrame({
            'date': ic_series.index,
            'IC': ic_series.values
        })

        # 计算统计指标
        result['IC Mean'] = result['IC'].mean()
        result['IC Std'] = result['IC'].std()
        result['ICIR'] = result['IC Mean'] / result['IC Std'] if result['IC Std'] > 0 else 0
        result['IC > 0'] = (result['IC'] > 0).sum() / len(result) * 100

        return result

    def layered_backtest(self,
                        factor_data: pd.DataFrame,
                        price_data: pd.DataFrame,
                        n_layers: int = 5,
                        periods: int = 1):
        """
        分层回测

        Args:
            factor_data: 因子数据
            price_data: 价格数据
            n_layers: 分层数
            periods: 持有期

        Returns:
            回测结果
        """
        try:
            from easy_xt.alpha_analysis.layered_backtest import LayeredBacktester
            backtester = LayeredBacktester(price_data, factor_data)
            backtester.calculate_layer_returns(n_layers=n_layers, periods=periods)
            backtester.calculate_long_short_returns(n_layers=n_layers, periods=periods)
            backtester.calculate_backtest_metrics()
            return backtester
        except ImportError:
            print("⚠️ 分层回测模块未安装")
            return None

    def update_data(self, symbols: List[str] = None):
        """更新本地数据"""
        if self.data_manager:
            self.data_manager.update_data(symbols=symbols)
            print("✅ 数据已更新")
        else:
            print("⚠️ 本地缓存未启用")

    def get_data_status(self) -> Dict:
        """获取数据状态"""
        if self.data_manager:
            return self.data_manager.get_statistics()
        return {}

    def print_data_summary(self):
        """打印数据摘要"""
        if self.data_manager:
            self.data_manager.print_summary()


# 便捷函数
def create_analyzer(use_cache: bool = True) -> EasyFactorAnalyzer:
    """
    创建因子分析器

    Args:
        use_cache: 是否使用本地缓存

    Returns:
        EasyFactorAnalyzer实例
    """
    return EasyFactorAnalyzer(use_local_cache=use_cache)


def quick_factor_analysis(symbols: Union[str, List[str]],
                         factor_func: callable,
                         start_date: str,
                         end_date: str,
                         n_layers: int = 5) -> Dict:
    """
    快速因子分析

    Args:
        symbols: 股票代码
        factor_func: 因子计算函数
        start_date: 开始日期
        end_date: 结束日期
        n_layers: 分层数

    Returns:
        分析结果字典
    """
    # 创建分析器
    analyzer = create_analyzer(use_cache=True)

    # 加载数据
    data = analyzer.load_data(symbols, start_date, end_date)

    if data is None or data.empty:
        return {'error': '数据加载失败'}

    # 计算因子
    factor_data = factor_func(data)

    # 获取价格数据
    price_data = data['close'].unstack(level='symbol')

    # IC分析
    ic_result = analyzer.ic_analysis(factor_data, price_data)

    # 分层回测
    backtest_result = analyzer.layered_backtest(factor_data, price_data, n_layers)

    return {
        'ic_analysis': ic_result,
        'backtest': backtest_result
    }


# 预定义因子
def calculate_ma_factor(data: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算均线因子"""
    close = data['close'].unstack(level='symbol')
    ma = close.rolling(window=period).mean()
    factor = (close - ma) / ma  # 相对均线偏离度
    return factor


def calculate_momentum_factor(data: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算动量因子"""
    close = data['close'].unstack(level='symbol')
    ret = close.pct_change(period)
    return ret


def calculate_volatility_factor(data: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算波动率因子"""
    close = data['close'].unstack(level='symbol')
    ret = close.pct_change()
    volatility = ret.rolling(window=period).std()
    return volatility


def calculate_rsrs_factor(data: pd.DataFrame, period: int = 18) -> pd.DataFrame:
    """计算RSRS因子"""
    close = data['close'].unstack(level='symbol')
    high = data['high'].unstack(level='symbol')
    low = data['low'].unstack(level='symbol')

    # 简化版RSRS: (high - low)的回归斜率
    hl = high - low
    rsrs = hl.rolling(window=period).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
    return rsrs


if __name__ == '__main__':
    # 测试代码
    print("测试便捷因子分析器\n")

    # 创建分析器
    analyzer = create_analyzer(use_cache=True)

    # 测试股票
    symbols = ['000001.SZ', '600000.SH']
    start_date = '2023-01-01'
    end_date = '2023-12-31'

    # 加载数据
    data = analyzer.load_data(symbols, start_date, end_date)

    if data is not None and not data.empty:
        print(f"✅ 数据加载成功: {data.shape}")

        # 计算因子
        ma_factor = calculate_ma_factor(data, period=20)
        print(f"✅ MA因子计算完成: {ma_factor.shape}")

        # IC分析
        price_data = data['close'].unstack(level='symbol')
        ic_result = analyzer.ic_analysis(ma_factor, price_data, periods=5)
        print(f"✅ IC分析完成")
        print(f"   IC Mean: {ic_result['IC Mean'].values[0]:.4f}")
        print(f"   ICIR: {ic_result['ICIR'].values[0]:.4f}")

    # 打印数据摘要
    analyzer.print_data_summary()
