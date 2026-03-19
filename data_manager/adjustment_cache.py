#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复权查询模块 - QMT API方案

核心思想：
1. 存储层：只保存原始数据（不复权）
2. 查询层：需要复权时直接调用QMT API
3. 无需本地计算，无需维护分红数据

优势：
- 使用QMT官方复权算法（准确性100%）
- 代码极简，易于维护
- 无需自己实现复权算法

劣势：
- 依赖QMT在线环境
"""

import pandas as pd
import duckdb
from typing import Literal
import warnings

# 复权类型定义
AdjustType = Literal['none', 'front', 'back', 'geometric_front', 'geometric_back']

ADJUST_TYPE_NAMES = {
    'none': '不复权',
    'front': '前复权',
    'back': '后复权',
    'geometric_front': '等比前复权',
    'geometric_back': '等比后复权'
}

# 复权类型映射到QMT的dividend_type参数
ADJUST_TO_QMT_DIVIDEND_TYPE = {
    'none': 0,           # 不复权
    'front': 1,          # 前复权
    'back': 2,           # 后复权
    'geometric_front': 3, # 等比前复权
    'geometric_back': 4   # 等比后复权
}


class AdjustmentCache:
    """
    复权查询管理器（QMT API方案）

    功能：
    1. 不复权：从DuckDB读取原始数据
    2. 需要复权：直接调用QMT API获取
    """

    def __init__(self, duckdb_path: str):
        """
        初始化复权管理器

        Args:
            duckdb_path: DuckDB数据库路径
        """
        self.duckdb_path = duckdb_path
        self.qmt_available = False
        self.xtdata = None

        # 尝试导入xtdata
        try:
            import xtdata
            self.xtdata = xtdata
            self.qmt_available = True
        except ImportError:
            warnings.warn("xtdata未安装，复权功能将不可用")

    def get_adjusted_data(self,
                         stock_code: str,
                         start_date: str,
                         end_date: str,
                         adjust_type: AdjustType,
                         con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        """
        获取复权数据

        策略：
        1. 不复权（none）：从DuckDB读取原始数据
        2. 需要复权：直接调用QMT API

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型
            con: DuckDB连接

        Returns:
            复权后的数据
        """
        # 1. 不复权：直接返回原始数据
        if adjust_type == 'none':
            return self._get_raw_data(stock_code, start_date, end_date, con)

        # 2. 需要复权：调用QMT API
        return self._get_from_qmt_api(stock_code, start_date, end_date, adjust_type)

    def _get_raw_data(self,
                     stock_code: str,
                     start_date: str,
                     end_date: str,
                     con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        """从DuckDB获取原始数据"""
        query = f"""
            SELECT
                stock_code, date, period,
                open, high, low, close, volume, amount,
                created_at, updated_at
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """
        return con.execute(query).df()

    def _get_from_qmt_api(self,
                         stock_code: str,
                         start_date: str,
                         end_date: str,
                         adjust_type: AdjustType) -> pd.DataFrame:
        """
        从QMT API获取复权数据

        使用xtdata.get_market_data_ex(dividend_type=...)直接获取复权数据
        """
        if not self.qmt_available:
            warnings.warn("QMT不可用，无法获取复权数据")
            return pd.DataFrame()

        # 转换复权类型
        dividend_type = ADJUST_TO_QMT_DIVIDEND_TYPE.get(adjust_type, 0)

        try:
            # 调用QMT API获取复权数据
            data = self.xtdata.get_market_data_ex(
                stock_list=[stock_code],
                period='1d',
                start_time=start_date,
                end_time=end_date,
                dividend_type=dividend_type,
                fill_prompt=True
            )

            if data is None or data.empty:
                return pd.DataFrame()

            # 格式化数据
            return self._format_qmt_data(data, stock_code)

        except Exception as e:
            warnings.warn(f"QMT API调用失败: {e}")
            return pd.DataFrame()

    def _format_qmt_data(self, data: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        格式化QMT返回的数据

        QMT返回的数据格式需要转换为我们统一的格式
        """
        if data.empty:
            return pd.DataFrame()

        # 重置索引（如果有多级索引）
        if isinstance(data.index, pd.MultiIndex):
            data = data.reset_index()

        # 确保列名统一
        column_mapping = {
            'time': 'date',
            'trade_time': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
            'code': 'stock_code'
        }

        # 重命名列
        data = data.rename(columns=column_mapping)

        # 确保有stock_code列
        if 'stock_code' not in data.columns:
            data['stock_code'] = stock_code

        # 确保有period列
        if 'period' not in data.columns:
            data['period'] = '1d'

        # 选择需要的列
        required_columns = [
            'stock_code', 'date', 'period',
            'open', 'high', 'low', 'close', 'volume', 'amount'
        ]

        # 只保留存在的列
        available_columns = [col for col in required_columns if col in data.columns]
        data = data[available_columns]

        return data

    def invalidate_cache(self, stock_code: str, con: duckdb.DuckDBPyConnection):
        """
        缓存失效（API方案无需实现）

        API方案每次都从QMT获取最新数据，无需本地缓存管理
        """
        pass


def test_adjustment_cache():
    """测试复权查询（QMT API方案）"""
    print("=" * 60)
    print("复权查询测试（QMT API方案）")
    print("=" * 60)

    db_path = r'D:/StockData/stock_data.ddb'
    cache = AdjustmentCache(db_path)

    con = duckdb.connect(db_path)

    test_stock = '511380.SH'
    start_date = '2024-01-01'
    end_date = '2024-01-31'

    # 测试1: 不复权
    print("\n[1] 查询不复权数据（从DuckDB）...")
    df_none = cache.get_adjusted_data(test_stock, start_date, end_date, 'none', con)
    print(f"  返回 {len(df_none)} 条数据")
    if not df_none.empty:
        print(f"  列: {list(df_none.columns)}")

    # 测试2: 前复权
    print("\n[2] 查询前复权数据（从QMT API）...")
    df_front = cache.get_adjusted_data(test_stock, start_date, end_date, 'front', con)
    print(f"  返回 {len(df_front)} 条数据")
    if not df_front.empty:
        print(f"  列: {list(df_front.columns)}")
        # 验证价格是否被复权
        if 'close' in df_front.columns:
            print(f"  最新收盘价: {df_front['close'].iloc[-1]:.3f}")

    # 测试3: 后复权
    print("\n[3] 查询后复权数据（从QMT API）...")
    df_back = cache.get_adjusted_data(test_stock, start_date, end_date, 'back', con)
    print(f"  返回 {len(df_back)} 条数据")

    con.close()
    print("\n[OK] 测试完成")
    print("\n核心优势:")
    print("  - 无需本地计算复权")
    print("  - 使用QMT官方算法")
    print("  - 代码简洁易维护")


if __name__ == "__main__":
    test_adjustment_cache()
