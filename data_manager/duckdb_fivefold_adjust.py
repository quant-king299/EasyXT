#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五维复权数据管理模块
实现不复权、前复权、后复权、等比前复权、等比后复权的数据存储和查询

参考文档：duckdb.docx
五维复权体系：在数据导入阶段就自动计算并存储 5 种价格数据
查询时切换复权方式是直接读取字段，实现真正的"零延迟"切换
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, date
import duckdb


class FiveFoldAdjustmentManager:
    """
    五维复权管理器

    功能：
    1. 计算五种复权数据：不复权、前复权、后复权、等比前复权、等比后复权
    2. 存储到 DuckDB 不同列
    3. 查询时直接读取对应复权类型
    """

    # 复权类型枚举
    ADJUST_TYPES = {
        'none': '不复权',
        'front': '前复权',
        'back': '后复权',
        'geometric_front': '等比前复权',
        'geometric_back': '等比后复权'
    }

    def __init__(self, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        """
        初始化五维复权管理器

        Args:
            duckdb_path: DuckDB 数据库路径
        """
        self.duckdb_path = duckdb_path
        self.con = None

    def connect(self):
        """连接数据库"""
        try:
            self.con = duckdb.connect(self.duckdb_path)
            return True
        except Exception as e:
            print(f"[ERROR] 数据库连接失败: {e}")
            return False

    def add_adjustment_columns(self):
        """
        添加五维复权列到现有表

        新增列：
        - open_front, high_front, low_front, close_front (前复权)
        - open_back, high_back, low_back, close_back (后复权)
        - open_geo_front, high_geo_front, low_geo_front, close_geo_front (等比前复权)
        - open_geo_back, high_geo_back, low_geo_back, close_geo_back (等比后复权)
        """
        if not self.con:
            print("[ERROR] 请先连接数据库")
            return False

        print("[INFO] 添加五维复权列...")

        # 定义需要添加的列
        columns_to_add = [
            # 前复权
            ('open_front', 'DECIMAL(28,6)'),
            ('high_front', 'DECIMAL(28,6)'),
            ('low_front', 'DECIMAL(28,6)'),
            ('close_front', 'DECIMAL(28,6)'),
            # 后复权
            ('open_back', 'DECIMAL(28,6)'),
            ('high_back', 'DECIMAL(28,6)'),
            ('low_back', 'DECIMAL(28,6)'),
            ('close_back', 'DECIMAL(28,6)'),
            # 等比前复权
            ('open_geometric_front', 'DECIMAL(28,6)'),
            ('high_geometric_front', 'DECIMAL(28,6)'),
            ('low_geometric_front', 'DECIMAL(28,6)'),
            ('close_geometric_front', 'DECIMAL(28,6)'),
            # 等比后复权
            ('open_geometric_back', 'DECIMAL(28,6)'),
            ('high_geometric_back', 'DECIMAL(28,6)'),
            ('low_geometric_back', 'DECIMAL(28,6)'),
            ('close_geometric_back', 'DECIMAL(28,6)'),
        ]

        # 获取现有列
        existing_columns = self.con.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'stock_daily'
        """).fetchdf()['column_name'].tolist()

        # 先删除已存在的复权列（如果是DOUBLE类型）
        # 原因：可能之前创建的是DOUBLE，需要先删除再重新创建DECIMAL
        to_drop = []
        for col_name, _ in columns_to_add:
            if col_name in existing_columns:
                # 检查该列的数据类型
                col_info = self.con.execute(f"""
                    SELECT data_type FROM information_schema.columns
                    WHERE table_name = 'stock_daily'
                      AND column_name = '{col_name}'
                """).fetchone()

                if col_info and col_info[0] == 'DOUBLE':
                    to_drop.append(col_name)

        if to_drop:
            print(f"[INFO] 删除旧的DOUBLE类型列: {len(to_drop)} 个")
            for col_name in to_drop:
                try:
                    self.con.execute(f"ALTER TABLE stock_daily DROP COLUMN {col_name}")
                    print(f"  [OK] 删除列: {col_name}")
                    existing_columns.remove(col_name)
                except Exception as e:
                    print(f"  [WARN] 删除失败 {col_name}: {e}")

        # 添加新的复权列
        added_count = 0
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                try:
                    self.con.execute(f"""
                        ALTER TABLE stock_daily
                        ADD COLUMN {col_name} {col_type}
                    """)
                    added_count += 1
                    print(f"  [OK] 添加列: {col_name}")
                except Exception as e:
                    print(f"  [SKIP] {col_name}: {e}")
            else:
                print(f"  [EXISTS] {col_name}")

        print(f"[OK] 完成，新增 {added_count} 列")
        return True

    def calculate_adjustment(self, df: pd.DataFrame, dividends: pd.DataFrame = None) -> Dict[str, pd.DataFrame]:
        """
        计算五维复权数据

        Args:
            df: 原始不复权数据（包含 OHLC）
            dividends: 分红数据（可选，包含 ex_date, dividend, bonus_ratio 等）

        Returns:
            包含 5 种复权数据的字典
        """
        results = {}

        # 1. 不复权（原始数据）
        results['none'] = df.copy()

        # 如果没有分红数据，所有复权数据与不复权相同
        if dividends is None or dividends.empty:
            # 没有分红数据时，返回原始价格作为复权数据
            # 这样前复权列至少有值（等于原始价格），而不是NULL
            for adj_type in ['front', 'back', 'geometric_front', 'geometric_back']:
                results[adj_type] = df.copy()
        else:
            # 2. 前复权
            results['front'] = self._calculate_front_adjustment(df, dividends)

            # 3. 后复权
            results['back'] = self._calculate_back_adjustment(df, dividends)

            # 4. 等比前复权
            results['geometric_front'] = self._calculate_geometric_front_adjustment(df, dividends)

            # 5. 等比后复权
            results['geometric_back'] = self._calculate_geometric_back_adjustment(df, dividends)

        return results

    def _calculate_front_adjustment(self, df: pd.DataFrame, dividends: pd.DataFrame) -> pd.DataFrame:
        """
        计算前复权数据

        前复权原理：以当前价格为基准，历史价格按照分红比例进行调整
        公式：复权后价格 = 原始价格 × 累计复权因子
        """
        df_adj = df.copy()

        # 合并分红数据
        dividends_sorted = dividends.sort_values('ex_date')

        # 计算累计复权因子（从后往前）
        cumulative_factor = 1.0
        adjustment_factors = pd.Series(index=df.index, dtype=float)

        for idx in reversed(df.index):
            # 检查这一天或之后是否有分红
            future_dividends_sorted = dividends_sorted[dividends_sorted['ex_date'] > idx]

            if not future_dividends_sorted.empty:
                # 计算复权因子
                for _, div_row in future_dividends_sorted.iterrows():
                    # 现金分红
                    if pd.notna(div_row.get('dividend_per_share')):
                        dividend = div_row['dividend_per_share']
                        # 前复权因子 = (1 - 后续分红 / 之前收盘价)
                        prev_close = df.loc[idx, 'close']
                        if prev_close > 0:
                            cumulative_factor *= (1 - dividend / prev_close)

                    # 送股/转增
                    if pd.notna(div_row.get('bonus_ratio')):
                        bonus = div_row['bonus_ratio']
                        # 10送X股，比例是 X/10
                        bonus_ratio = bonus / 10.0
                        cumulative_factor *= (1 + bonus_ratio)

            adjustment_factors[idx] = cumulative_factor

        # 应用复权因子
        for col in ['open', 'high', 'low', 'close']:
            df_adj[col] = df[col] * adjustment_factors

        return df_adj

    def _calculate_back_adjustment(self, df: pd.DataFrame, dividends: pd.DataFrame) -> pd.DataFrame:
        """
        计算后复权数据

        后复权原理：以历史价格为基准，当前价格按照分红比例进行调整
        """
        df_adj = df.copy()

        # 合并分红数据
        dividends_sorted = dividends.sort_values('ex_date')

        # 计算累计复权因子（从前往后）
        cumulative_factor = 1.0
        adjustment_factors = pd.Series(index=df.index, dtype=float)

        for idx in df.index:
            # 检查这一天是否有分红
            day_dividends_sorted = dividends_sorted[dividends_sorted['ex_date'] == idx]

            if not day_dividends_sorted.empty:
                for _, div_row in day_dividends_sorted.iterrows():
                    # 现金分红
                    if pd.notna(div_row.get('dividend_per_share')):
                        dividend = div_row['dividend_per_share']
                        prev_close = df.loc[idx, 'close'] if idx in df.index else df['close'].iloc[0]
                        if prev_close > 0:
                            # 后复权因子 = (1 - 分红 / 除权前收盘价)
                            cumulative_factor *= (1 - dividend / prev_close)

                    # 送股/转增
                    if pd.notna(div_row.get('bonus_ratio')):
                        bonus = div_row['bonus_ratio']
                        bonus_ratio = bonus / 10.0
                        cumulative_factor *= (1 + bonus_ratio)

            adjustment_factors[idx] = cumulative_factor

        # 应用复权因子（后复权是累计的，需要用最终的因子）
        final_factor = adjustment_factors.iloc[-1]
        for col in ['open', 'high', 'low', 'close']:
            df_adj[col] = df[col] * (final_factor / adjustment_factors)

        return df_adj

    def _calculate_geometric_front_adjustment(self, df: pd.DataFrame, dividends: pd.DataFrame) -> pd.DataFrame:
        """
        计算等比前复权数据

        等比前复权：使用几何平均方式计算前复权，避免复权跳空
        优点：保持价格序列的连续性，K线图不会出现跳空
        """
        df_adj = df.copy()

        # 先计算普通前复权
        df_front = self._calculate_front_adjustment(df, dividends)

        # 计算等比复权因子（几何平均）
        # 使用对数变换避免跳空
        for col in ['open', 'high', 'low', 'close']:
            # 计算收益率
            returns = df_front[col].pct_change()
            # 累计乘积（等比）
            cumulative_return = (1 + returns).cumprod()
            # 应用等比复权
            df_adj[col] = df[col].iloc[0] * cumulative_return
            df_adj[col] = df_adj[col].fillna(df_front[col])

        return df_adj

    def _calculate_geometric_back_adjustment(self, df: pd.DataFrame, dividends: pd.DataFrame) -> pd.DataFrame:
        """
        计算等比后复权数据
        """
        df_adj = df.copy()

        # 先计算普通后复权
        df_back = self._calculate_back_adjustment(df, dividends)

        # 计算等比复权因子（几何平均）
        for col in ['open', 'high', 'low', 'close']:
            # 计算收益率
            returns = df_back[col].pct_change()
            # 累计乘积（等比）
            cumulative_return = (1 + returns).cumprod()
            # 应用等比复权
            df_adj[col] = df[col].iloc[0] * cumulative_return
            df_adj[col] = df_adj[col].fillna(df_back[col])

        return df_adj

    def save_adjusted_data(self, stock_code: str, adjusted_data_dict: Dict[str, pd.DataFrame]):
        """
        保存五维复权数据到 DuckDB

        Args:
            stock_code: 股票代码
            adjusted_data_dict: 五种复权数据字典
        """
        if not self.con:
            print("[ERROR] 请先连接数据库")
            return False

        try:
            # 获取不复权数据作为基准
            df_none = adjusted_data_dict['none'].copy()

            # 添加各种复权类型的列
            for adj_type, df_adj in adjusted_data_dict.items():
                if adj_type == 'none':
                    continue

                # 映射列名
                col_mapping = {
                    'front': ('open_front', 'high_front', 'low_front', 'close_front'),
                    'back': ('open_back', 'high_back', 'low_back', 'close_back'),
                    'geometric_front': ('open_geometric_front', 'high_geometric_front',
                                       'low_geometric_front', 'close_geometric_front'),
                    'geometric_back': ('open_geometric_back', 'high_geometric_back',
                                      'low_geometric_back', 'close_geometric_back'),
                }

                target_cols = col_mapping.get(adj_type)
                if target_cols:
                    for i, price_col in enumerate(['open', 'high', 'low', 'close']):
                        if price_col in df_adj.columns:
                            df_none[target_cols[i]] = df_adj[price_col]

            # 删除旧数据
            self.con.execute(f"DELETE FROM stock_daily WHERE stock_code = '{stock_code}'")

            # 批量插入
            self.con.register('temp_df', df_none)
            self.con.execute("INSERT INTO stock_daily SELECT * FROM temp_df")
            self.con.unregister('temp_df')

            print(f"[OK] {stock_code} 五维复权数据已保存")
            return True

        except Exception as e:
            print(f"[ERROR] 保存失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_data_with_adjustment(self,
                                stock_code: str,
                                start_date: str,
                                end_date: str,
                                adjust_type: str = 'none') -> pd.DataFrame:
        """
        获取指定复权类型的数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型 (none/front/back/geometric_front/geometric_back)

        Returns:
            指定复权类型的数据
        """
        if not self.con:
            return pd.DataFrame()

        if adjust_type not in self.ADJUST_TYPES:
            print(f"[ERROR] 不支持的复权类型: {adjust_type}")
            return pd.DataFrame()

        # 检查复权列是否存在，如果不存在则先添加
        if adjust_type != 'none':
            existing_columns = self.con.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'stock_daily'
            """).fetchdf()['column_name'].tolist()

            # 根据复权类型确定需要检查的列
            required_cols = []
            if adjust_type == 'front':
                required_cols = ['open_front', 'high_front', 'low_front', 'close_front']
            elif adjust_type == 'back':
                required_cols = ['open_back', 'high_back', 'low_back', 'close_back']
            elif adjust_type == 'geometric_front':
                required_cols = ['open_geometric_front', 'high_geometric_front',
                             'low_geometric_front', 'close_geometric_front']
            elif adjust_type == 'geometric_back':
                required_cols = ['open_geometric_back', 'high_geometric_back',
                             'low_geometric_back', 'close_geometric_back']

            # 检查是否所有需要的列都存在
            missing_cols = [col for col in required_cols if col not in existing_columns]

            if missing_cols:
                print(f"[INFO] 复权列不存在，先添加: {missing_cols[:2]}...")
                self.add_adjustment_columns()

        # 根据复权类型选择列
        if adjust_type == 'none':
            price_cols = ['open', 'high', 'low', 'close']
        elif adjust_type == 'front':
            price_cols = ['open_front', 'high_front', 'low_front', 'close_front']
        elif adjust_type == 'back':
            price_cols = ['open_back', 'high_back', 'low_back', 'close_back']
        elif adjust_type == 'geometric_front':
            price_cols = ['open_geometric_front', 'high_geometric_front',
                         'low_geometric_front', 'close_geometric_front']
        elif adjust_type == 'geometric_back':
            price_cols = ['open_geometric_back', 'high_geometric_back',
                         'low_geometric_back', 'close_geometric_back']

        # 构建查询
        query = f"""
            SELECT
                stock_code, date, period,
                {price_cols[0]} as open,
                {price_cols[1]} as high,
                {price_cols[2]} as low,
                {price_cols[3]} as close,
                volume, amount
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """

        try:
            df = self.con.execute(query).df()

            # 如果指定的复权列不存在或不完整，回退到不复权
            if df.empty or df['open'].isna().all():
                if adjust_type != 'none':
                    print(f"[WARNING] {adjust_type} 数据不存在，回退到不复权数据")
                    return self.get_data_with_adjustment(stock_code, start_date, end_date, 'none')

            return df

        except Exception as e:
            print(f"[ERROR] 查询失败: {e}")
            return pd.DataFrame()

    def close(self):
        """关闭数据库连接"""
        if self.con:
            self.con.close()
            self.con = None


def test_fivefold_adjustment():
    """测试五维复权功能"""
    print("=" * 60)
    print("五维复权模块测试")
    print("=" * 60)
    print()

    # 创建管理器
    manager = FiveFoldAdjustmentManager()

    if not manager.connect():
        print("[ERROR] 无法连接数据库")
        return

    # 添加列
    print("[1] 添加五维复权列...")
    manager.add_adjustment_columns()
    print()

    # 测试查询
    print("[2] 测试数据查询...")
    df_none = manager.get_data_with_adjustment('511380.SH', '2024-01-01', '2024-01-31', 'none')
    df_front = manager.get_data_with_adjustment('511380.SH', '2024-01-01', '2024-01-31', 'front')

    print(f"  不复权数据: {len(df_none)} 条")
    print(f"  前复权数据: {len(df_front)} 条")
    print()

    manager.close()
    print("[OK] 测试完成")


if __name__ == "__main__":
    test_fivefold_adjustment()
