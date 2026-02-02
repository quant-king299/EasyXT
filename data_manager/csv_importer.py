#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV导入工具
支持从CSV文件导入股票列表和自定义数据
"""

import pandas as pd
from typing import List, Dict, Optional
from pathlib import Path


class CSVImporter:
    """CSV导入工具"""

    def __init__(self):
        """初始化CSV导入器"""
        pass

    def load_stock_list(self, csv_path: str) -> List[str]:
        """
        从CSV加载股票列表

        支持多种格式：
        格式1：只有股票代码列
        格式2：股票代码 + 股票名称
        格式3：自定义列名

        Args:
            csv_path: CSV文件路径

        Returns:
            List[str]: 股票代码列表
        """
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')  # 兼容BOM

            # 查找股票代码列
            code_col = self._find_code_column(df)

            if code_col is None:
                print(f"[ERROR] CSV中未找到股票代码列")
                print(f"  可用列: {list(df.columns)}")
                return []

            # 提取股票代码
            stocks = df[code_col].dropna().unique().tolist()

            # 标准化股票代码
            normalized_stocks = self._normalize_stock_codes(stocks)

            print(f"[CSV导入] 从 {csv_path} 导入 {len(normalized_stocks)} 只股票")
            return normalized_stocks

        except Exception as e:
            print(f"[ERROR] CSV加载失败: {e}")
            return []

    def _find_code_column(self, df: pd.DataFrame) -> Optional[str]:
        """查找股票代码列"""
        # 常见的列名模式
        patterns = [
            'code', '代码', '股票代码', 'stock_code', 'symbol',
            'stock', '股票', 'security', '证券'
        ]

        for col in df.columns:
            col_lower = col.lower()
            for pattern in patterns:
                if pattern in col_lower:
                    return col

        # 如果没找到，使用第一列
        return df.columns[0] if len(df.columns) > 0 else None

    def _normalize_stock_codes(self, stocks: List[str]) -> List[str]:
        """标准化股票代码"""
        normalized = []

        for stock in stocks:
            stock_str = str(stock).strip().upper()

            # 跳过空值
            if not stock_str or stock_str == 'NAN':
                continue

            # 如果已经包含.后缀，保持不变
            if '.' in stock_str:
                normalized.append(stock_str)
            else:
                # 添加市场后缀
                if stock_str.startswith('6'):
                    normalized.append(f"{stock_str}.SH")
                elif stock_str.startswith('0') or stock_str.startswith('3'):
                    normalized.append(f"{stock_str}.SZ")
                elif stock_str.startswith('8') or stock_str.startswith('4'):
                    normalized.append(f"{stock_str}.BJ")
                else:
                    # 无法判断，默认.SH
                    normalized.append(f"{stock_str}.SH")

        # 去重
        return list(set(normalized))

    def load_stock_data(self, csv_path: str) -> pd.DataFrame:
        """
        从CSV加载股票数据（用于直接导入数据）

        CSV格式要求：
        - 必须列：time/datetime, open, high, low, close, volume
        - 可选列：code, amount

        Args:
            csv_path: CSV文件路径

        Returns:
            DataFrame: 股票数据
        """
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # 标准化列名
            df = self._standardize_column_names(df)

            # 标准化时间列
            time_col = self._find_time_column(df)
            if time_col:
                df[time_col] = pd.to_datetime(df[time_col])
                df.set_index(time_col, inplace=True)

            print(f"[CSV导入] 从 {csv_path} 导入 {len(df)} 条数据")
            return df

        except Exception as e:
            print(f"[ERROR] 数据加载失败: {e}")
            return pd.DataFrame()

    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_map = {
            # 时间列
            'time': 'time',
            'datetime': 'time',
            'date': 'time',
            '日期': 'time',
            '时间': 'time',

            # 价格列
            'open': 'open',
            'Open': 'open',
            '开盘': 'open',
            '开盘价': 'open',

            'high': 'high',
            'High': 'high',
            '最高': 'high',
            '最高价': 'high',

            'low': 'low',
            'Low': 'low',
            '最低': 'low',
            '最低价': 'low',

            'close': 'close',
            'Close': 'close',
            '收盘': 'close',
            '收盘价': 'close',

            # 成交量列
            'volume': 'volume',
            'Volume': 'volume',
            'vol': 'volume',
            '成交量': 'volume',
            'amount': 'volume'
        }

        # 创建新的列名映射
        rename_dict = {}
        for old_col in df.columns:
            for key, value in column_map.items():
                if key in old_col.lower():
                    rename_dict[old_col] = value
                    break

        if rename_dict:
            df = df.rename(columns=rename_dict)

        return df

    def _find_time_column(self, df: pd.DataFrame) -> Optional[str]:
        """查找时间列"""
        time_patterns = ['time', 'datetime', 'date', '日期', '时间']

        for col in df.columns:
            col_lower = col.lower()
            for pattern in time_patterns:
                if pattern in col_lower:
                    return col

        return None

    def export_stock_list(self, stocks: List[str], csv_path: str):
        """
        导出股票列表到CSV

        Args:
            stocks: 股票代码列表
            csv_path: 导出路径
        """
        try:
            df = pd.DataFrame({'股票代码': stocks})
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"[CSV导出] 已导出 {len(stocks)} 只股票到 {csv_path}")

        except Exception as e:
            print(f"[ERROR] CSV导出失败: {e}")

    def create_template(self, csv_path: str, include_examples: bool = True):
        """
        创建CSV模板文件

        Args:
            csv_path: 模板文件路径
            include_examples: 是否包含示例数据
        """
        try:
            if include_examples:
                # 创建带示例的模板
                data = {
                    '股票代码': ['000001.SZ', '000002.SZ', '511380.SH'],
                    '股票名称': ['平安银行', '万科A', '平安中债0-4年国开债ETF']
                }
                df = pd.DataFrame(data)
            else:
                # 创建空模板
                df = pd.DataFrame(columns=['股票代码', '股票名称'])

            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"[模板创建] 已创建CSV模板: {csv_path}")

        except Exception as e:
            print(f"[ERROR] 模板创建失败: {e}")


# 测试代码
if __name__ == "__main__":
    print("="*80)
    print("CSV导入工具测试")
    print("="*80)

    importer = CSVImporter()

    # 测试1：创建模板
    print("\n【测试1】创建CSV模板")
    importer.create_template('stock_list_template.csv', include_examples=True)

    # 测试2：加载刚才创建的模板
    print("\n【测试2】加载股票列表")
    stocks = importer.load_stock_list('stock_list_template.csv')
    if stocks:
        print(f"加载的股票: {stocks}")

    # 测试3：导出股票列表
    print("\n【测试3】导出股票列表")
    test_stocks = ['600000.SH', '000001.SZ', '511380.SH']
    importer.export_stock_list(test_stocks, 'my_stocks.csv')
