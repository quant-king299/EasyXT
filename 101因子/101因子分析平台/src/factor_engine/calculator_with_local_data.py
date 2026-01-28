"""
集成本地数据管理的因子计算器
在原有因子计算器基础上增加本地数据缓存功能
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
import sys

# 导入原有因子计算器
try:
    from .calculator import FactorCalculator
except ImportError:
    # 如果原有计算器不存在，创建基础版本
    from ..data_manager import LocalDataManager

    class FactorCalculator:
        """因子计算器基础版本"""

        def __init__(self):
            self.data_manager = LocalDataManager()
            self.data = None

# 导入本地数据管理器
from ..data_manager import LocalDataManager


class FactorCalculatorWithDataCache(FactorCalculator):
    """
    带本地数据缓存的因子计算器

    功能：
    1. 优先从本地加载数据（快速）
    2. 本地缺失时才从QMT下载
    3. 自动缓存下载的数据
    """

    def __init__(self, use_local_cache: bool = True):
        """
        初始化计算器

        Args:
            use_local_cache: 是否使用本地缓存
        """
        super().__init__()

        self.use_local_cache = use_local_cache

        if use_local_cache:
            self.local_data_manager = LocalDataManager()
            print("✅ 本地数据缓存已启用")
        else:
            self.local_data_manager = None
            print("⚠️ 本地数据缓存未启用，每次都将从QMT下载")

    def load_data(self, symbols: List[str], start_date: str, end_date: str,
                  fields: List[str] = None) -> pd.DataFrame:
        """
        加载股票数据（优先使用本地缓存）

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fields: 字段列表

        Returns:
            DataFrame: 多级索引 [date, symbol]
        """
        print(f"\n{'='*60}")
        print(f"加载数据: {len(symbols)} 只标的")
        print(f"日期范围: {start_date} ~ {end_date}")
        print(f"{'='*60}\n")

        # 如果启用本地缓存
        if self.use_local_cache and self.local_data_manager:
            print("📂 尝试从本地加载数据...")

            # 从本地加载
            local_data = self.local_data_manager.load_data(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                check_local=False  # 不自动下载，稍后手动处理
            )

            if local_data:
                print(f"✅ 从本地加载 {len(local_data)} 只标的")

                # 合并为单个DataFrame
                df_list = []
                for symbol, df in local_data.items():
                    df = df.copy()
                    df['symbol'] = symbol
                    df_list.append(df)

                if df_list:
                    self.data = pd.concat(df_list)
                    self.data = self.data.reset_index().set_index(['date', 'symbol']).sort_index()

                    # 检查是否有缺失的标的
                    missing = set(symbols) - set(local_data.keys())
                    if missing:
                        print(f"⚠️ 本地缺失 {len(missing)} 只标的，尝试下载...")

                        # 下载缺失的数据
                        downloaded = self.local_data_manager.download_and_save(
                            symbols=list(missing),
                            start_date=start_date,
                            end_date=end_date,
                            symbol_type='stock',
                            show_progress=True
                        )

                        # 合并下载的数据
                        if downloaded:
                            for symbol, df in downloaded.items():
                                df = df.copy()
                                df['symbol'] = symbol
                                df_list.append(df)

                            self.data = pd.concat(df_list)
                            self.data = self.data.reset_index().set_index(['date', 'symbol']).sort_index()

                    print(f"✅ 数据加载完成: {self.data.shape}")
                    return self.data

        # 如果本地缓存未启用或加载失败，使用原有方法
        print("📡 从QMT下载数据...")

        # 调用父类方法或直接从数据源下载
        if hasattr(super(), 'load_data'):
            self.data = super().load_data(symbols, start_date, end_date)

            # 如果启用了本地缓存，保存下载的数据
            if self.use_local_cache and self.local_data_manager and not self.data.empty:
                print("💾 保存数据到本地缓存...")

                # 按标的分组保存
                for symbol in symbols:
                    try:
                        symbol_data = self.data.xs(symbol, level='symbol', drop_level=False)
                        self.local_data_manager.storage.save_data(
                            symbol_data.reset_index(level='symbol', drop=True),
                            symbol,
                            data_type='daily'
                        )
                    except:
                        continue

                print("✅ 数据已缓存到本地")

        return self.data

    def get_data_status(self) -> Dict:
        """
        获取本地数据状态

        Returns:
            数据状态字典
        """
        if not self.use_local_cache or not self.local_data_manager:
            return {'cache_enabled': False}

        return self.local_data_manager.get_statistics()

    def update_local_data(self, symbols: List[str] = None):
        """
        更新本地数据

        Args:
            symbols: 要更新的标的列表，None表示全部
        """
        if not self.use_local_cache or not self.local_data_manager:
            print("⚠️ 本地缓存未启用")
            return

        print("🔄 更新本地数据...")
        self.local_data_manager.update_data(symbols=symbols)
        print("✅ 更新完成")

    def print_data_summary(self):
        """打印数据摘要"""
        if not self.use_local_cache or not self.local_data_manager:
            return

        self.local_data_manager.print_summary()

    def close(self):
        """关闭计算器"""
        if self.local_data_manager:
            self.local_data_manager.close()


# 便捷函数
def create_calculator(use_cache: bool = True) -> FactorCalculatorWithDataCache:
    """
    创建因子计算器

    Args:
        use_cache: 是否使用本地缓存

    Returns:
        因子计算器实例
    """
    return FactorCalculatorWithDataCache(use_local_cache=use_cache)


if __name__ == '__main__':
    # 测试代码
    print("测试因子计算器（带本地数据缓存）\n")

    # 创建计算器
    calculator = create_calculator(use_cache=True)

    # 加载数据
    symbols = ['000001.SZ', '600000.SH']
    start_date = '2023-01-01'
    end_date = '2023-12-31'

    calculator.load_data(symbols, start_date, end_date)

    # 打印数据摘要
    calculator.print_data_summary()

    # 如果需要，可以计算因子
    if not calculator.data.empty:
        print(f"\n✅ 数据已准备好，可以计算因子")
        print(f"数据形状: {calculator.data.shape}")
        print(f"数据列: {list(calculator.data.columns)}")

    # 关闭
    calculator.close()
