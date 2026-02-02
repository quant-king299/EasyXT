#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块股票加载器
从QMT获取各种板块的股票列表

支持板块：
- 沪深300
- 中证500
- 中证1000
- 上证50
- 科创板
- 创业板
- 全A股
"""

from typing import List, Dict
import pandas as pd


class BoardStocksLoader:
    """板块股票加载器"""

    def __init__(self):
        """初始化加载器"""
        try:
            from xtquant import xtdata
            self.xtdata = xtdata
            self.available = True
            print("[INFO] QMT xtdata 可用")
        except ImportError:
            self.available = False
            self.xtdata = None
            print("[ERROR] QMT xtdata 不可用")

    def get_board_stocks(self, board_name: str) -> List[str]:
        """
        获取板块股票列表

        Args:
            board_name: 板块名称
                - '沪深300' 或 'hs300'
                - '中证500' 或 'zz500'
                - '中证1000' 或 'zz1000'
                - '上证50' 或 'sz50'
                - '科创板' 或 'kcb'
                - '创业板' 或 'cyb'
                - '全A股' 或 'all'

        Returns:
            List[str]: 股票代码列表
        """
        if not self.available:
            print("[ERROR] QMT 不可用，无法获取板块股票")
            return []

        # 标准化板块名称
        board_name = board_name.lower().replace(' ', '')

        # 板块映射
        board_map = {
            'hs300': '沪深300',
            '沪深300': 'hs300',
            'zz500': '中证500',
            '中证500': 'zz500',
            'zz1000': '中证1000',
            '中证1000': 'zz1000',
            'sz50': '上证50',
            '上证50': 'sz50',
            'kcb': '科创板',
            '科创板': 'kcb',
            'cyb': '创业板',
            '创业板': 'cyb',
            'all': '全A股',
            '全a股': 'all'
        }

        board_code = board_map.get(board_name)
        if not board_code:
            print(f"[ERROR] 未知板块: {board_name}")
            return []

        print(f"[板块加载] 获取 {board_code} 股票列表...")

        try:
            if board_code == 'all':
                # 获取全A股
                stocks = self._get_all_a_shares()
            elif board_code == 'hs300':
                stocks = self._get_index_stocks('000300.SH')
            elif board_code == 'zz500':
                stocks = self._get_index_stocks('000905.SH')
            elif board_code == 'zz1000':
                stocks = self._get_index_stocks('000852.SH')
            elif board_code == 'sz50':
                stocks = self._get_index_stocks('000016.SH')
            else:
                # 科创板、创业板等
                stocks = self._get_market_board(board_code)

            print(f"[OK] 获取到 {len(stocks)} 只股票")
            return stocks

        except Exception as e:
            print(f"[ERROR] 获取板块股票失败: {e}")
            return []

    def _get_all_a_shares(self) -> List[str]:
        """获取全A股列表"""
        try:
            # 获取所有板块
            all_stocks = []

            # 上海市场
            sh_stocks = self.xtdata.get_stock_list_in_sector('SH')
            if sh_stocks:
                all_stocks.extend(sh_stocks)

            # 深圳市场
            sz_stocks = self.xtdata.get_stock_list_in_sector('SZ')
            if sz_stocks:
                all_stocks.extend(sz_stocks)

            # 北京市场
            bj_stocks = self.xtdata.get_stock_list_in_sector('BJ')
            if bj_stocks:
                all_stocks.extend(bj_stocks)

            # 去重
            all_stocks = list(set(all_stocks))
            return all_stocks

        except Exception as e:
            print(f"[ERROR] 获取全A股失败: {e}")
            return []

    def _get_index_stocks(self, index_code: str) -> List[str]:
        """获取指数成分股"""
        try:
            # 获取指数成分股
            stocks = self.xtdata.get_stock_list_in_sector(index_code)

            if stocks:
                return stocks
            else:
                print(f"[WARNING] 未获取到 {index_code} 的成分股")
                return []

        except Exception as e:
            print(f"[ERROR] 获取指数成分股失败: {e}")
            return []

    def _get_market_board(self, board_code: str) -> List[str]:
        """获取市场板块股票"""
        try:
            # 尝试直接获取板块
            stocks = self.xtdata.get_stock_list_in_sector(board_code)

            if not stocks:
                # 尝试其他方法
                if board_code == 'kcb':
                    stocks = self.xtdata.get_stock_list_in_sector('SH')  # 简化处理
                    # 过滤688开头（科创板）
                    stocks = [s for s in stocks if s.startswith('688')]
                elif board_code == 'cyb':
                    stocks = self.xtdata.get_stock_list_in_sector('SZ')  # 简化处理
                    # 过滤300开头（创业板）
                    stocks = [s for s in stocks if s.startswith('300')]

            return stocks if stocks else []

        except Exception as e:
            print(f"[ERROR] 获取市场板块失败: {e}")
            return []

    def get_available_boards(self) -> Dict[str, str]:
        """获取可用的板块列表"""
        return {
            '沪深300': 'hs300',
            '中证500': 'zz500',
            '中证1000': 'zz1000',
            '上证50': 'sz50',
            '科创板': 'kcb',
            '创业板': 'cyb',
            '全A股': 'all'
        }

    def load_from_csv(self, csv_path: str) -> List[str]:
        """
        从CSV文件加载股票列表

        CSV格式要求：
        - 第一列：股票代码
        - 可选：第二列：股票名称

        Args:
            csv_path: CSV文件路径

        Returns:
            List[str]: 股票代码列表
        """
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')

            # 尝试不同的列名
            code_col = None
            for col in df.columns:
                if 'code' in col.lower() or '代码' in col or '股票' in col:
                    code_col = col
                    break

            if code_col is None:
                # 使用第一列
                code_col = df.columns[0]

            stocks = df[code_col].dropna().unique().tolist()

            # 清理股票代码（去除空格、.SH等后缀）
            cleaned_stocks = []
            for stock in stocks:
                stock_str = str(stock).strip().upper()
                # 确保格式正确（如 000001.SZ）
                if '.' not in stock_str:
                    # 添加市场后缀
                    if stock_str.startswith('6'):
                        stock_str += '.SH'
                    elif stock_str.startswith('0') or stock_str.startswith('3'):
                        stock_str += '.SZ'
                    elif stock_str.startswith('8'):
                        stock_str += '.BJ'
                cleaned_stocks.append(stock_str)

            print(f"[CSV加载] 从 {csv_path} 加载 {len(cleaned_stocks)} 只股票")
            return cleaned_stocks

        except Exception as e:
            print(f"[ERROR] CSV加载失败: {e}")
            return []


# 测试代码
if __name__ == "__main__":
    print("="*80)
    print("板块股票加载器测试")
    print("="*80)

    loader = BoardStocksLoader()

    # 测试1：获取板块股票
    print("\n【测试1】获取上证50股票")
    stocks = loader.get_board_stocks('上证50')
    if stocks:
        print(f"前10只: {stocks[:10]}")

    # 测试2：从CSV加载
    print("\n【测试2】从CSV加载（如果存在）")
    import os
    csv_files = [
        'stock_list.csv',
        'my_stocks.csv',
        'stocks.csv'
    ]

    for csv_file in csv_files:
        if os.path.exists(csv_file):
            stocks = loader.load_from_csv(csv_file)
            if stocks:
                print(f"加载成功: {stocks[:5]}...")
                break
    else:
        print("未找到CSV文件，跳过测试")

    # 测试3：显示可用板块
    print("\n【测试3】可用板块")
    boards = loader.get_available_boards()
    for name, code in boards.items():
        print(f"  {name}: {code}")
