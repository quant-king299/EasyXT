#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用数据导入器
支持全市场/板块/自定义股票池的数据导入
智能缺失检测，只下载缺失的数据段
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import time
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_manager.unified_data_interface import UnifiedDataInterface
from data_manager.board_stocks_loader import BoardStocksLoader
from data_manager.csv_importer import CSVImporter
from data_manager.smart_data_detector import SmartDataDetector


class UniversalDataImporter:
    """
    通用数据导入器

    功能：
    1. 全市场/板块股票导入
    2. CSV股票列表导入
    3. 智能缺失检测
    4. 并行下载
    5. 进度可视化
    6. 断点续传
    """

    def __init__(self, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        """
        初始化通用导入器

        Args:
            duckdb_path: DuckDB数据库路径
        """
        self.duckdb_path = duckdb_path
        self.interface = UnifiedDataInterface(duckdb_path=duckdb_path)
        self.board_loader = BoardStocksLoader()
        self.csv_importer = CSVImporter()
        self.detector = None

        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None

    def connect(self):
        """连接数据库"""
        return self.interface.connect()

    def close(self):
        """关闭数据库连接"""
        if self.interface.con:
            self.interface.con.close()
            self.interface.con = None

    def import_board_stocks(
        self,
        board_name: str,
        start_date: str,
        end_date: str,
        period: str = '1d',
        batch_size: int = 50
    ) -> Dict:
        """
        导入整个板块的股票数据

        Args:
            board_name: 板块名称（'沪深300', '中证500', '全A股'等）
            start_date: 开始日期（'YYYY-MM-DD'）
            end_date: 结束日期（'YYYY-MM-DD'）
            period: 数据周期（'1d', '1m', '5m'）
            batch_size: 批量大小（每次下载的股票数）

        Returns:
            Dict: 导入结果统计
        """
        print(f"\n{'='*80}")
        print(f"板块股票数据导入: {board_name}")
        print(f"{'='*80}")

        # Step 1: 获取板块股票列表
        print(f"\n步骤1: 获取板块股票列表...")
        stocks = self.board_loader.get_board_stocks(board_name)

        if not stocks:
            print(f"[ERROR] 未获取到板块股票")
            return {'success': False, 'error': '未获取到板块股票'}

        print(f"[OK] 获取到 {len(stocks)} 只股票")

        # Step 2: 批量导入数据
        return self._import_stocks_batch(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            period=period,
            batch_size=batch_size
        )

    def import_from_csv(
        self,
        csv_path: str,
        start_date: str,
        end_date: str,
        period: str = '1d',
        batch_size: int = 50
    ) -> Dict:
        """
        从CSV文件导入股票列表并下载数据

        Args:
            csv_path: CSV文件路径
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            batch_size: 批量大小

        Returns:
            Dict: 导入结果统计
        """
        print(f"\n{'='*80}")
        print(f"CSV股票列表导入: {csv_path}")
        print(f"{'='*80}")

        # Step 1: 从CSV加载股票列表
        print(f"\n步骤1: 从CSV加载股票列表...")
        stocks = self.csv_importer.load_stock_list(csv_path)

        if not stocks:
            print(f"[ERROR] CSV中未找到股票代码")
            return {'success': False, 'error': 'CSV中未找到股票代码'}

        print(f"[OK] 加载 {len(stocks)} 只股票")

        # Step 2: 批量导入数据
        return self._import_stocks_batch(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            period=period,
            batch_size=batch_size
        )

    def import_custom_stocks(
        self,
        stocks: List[str],
        start_date: str,
        end_date: str,
        period: str = '1d'
    ) -> Dict:
        """
        导入自定义股票列表

        Args:
            stocks: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期

        Returns:
            Dict: 导入结果统计
        """
        print(f"\n{'='*80}")
        print(f"自定义股票列表导入: {len(stocks)} 只股票")
        print(f"{'='*80}")

        return self._import_stocks_batch(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            period=period,
            batch_size=len(stocks)  # 全部一次导入
        )

    def _import_stocks_batch(
        self,
        stocks: List[str],
        start_date: str,
        end_date: str,
        period: str,
        batch_size: int
    ) -> Dict:
        """
        批量导入股票数据（内部方法）

        Args:
            stocks: 股票列表
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            batch_size: 批量大小

        Returns:
            Dict: 导入结果
        """
        total_stocks = len(stocks)
        success_count = 0
        failed_count = 0
        skipped_count = 0

        results = {
            'total': total_stocks,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }

        # 分批处理
        for i in range(0, total_stocks, batch_size):
            batch = stocks[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_stocks + batch_size - 1) // batch_size

            print(f"\n批次 {batch_num}/{total_batches} ({len(batch)} 只股票):")

            # 下载这批股票
            for j, stock in enumerate(batch, 1):
                stock_index = i + j
                print(f"  [{stock_index}/{total_stocks}] {stock}...", end='')

                try:
                    # 使用统一接口获取数据
                    data = self.interface.get_stock_data(
                        stock_code=stock,
                        start_date=start_date,
                        end_date=end_date,
                        period=period,
                        auto_save=True  # 自动保存到DuckDB
                    )

                    if not data.empty:
                        print(f"[OK] ({len(data)}条)")
                        results['success'] += 1
                        results['details'].append({
                            'stock': stock,
                            'status': 'success',
                            'count': len(data)
                        })
                    else:
                        print(f"[SKIP] 无数据")
                        results['skipped'] += 1
                        results['details'].append({
                            'stock': stock,
                            'status': 'skipped',
                            'count': 0
                        })

                except Exception as e:
                    print(f"[ERROR] {str(e)[:50]}")
                    results['failed'] += 1
                    results['details'].append({
                        'stock': stock,
                        'status': 'failed',
                        'error': str(e)
                    })

        # 打印总结
        print(f"\n{'='*80}")
        print(f"导入完成！")
        print(f"{'='*80}")
        print(f"总计: {results['total']} 只")
        print(f"成功: {results['success']} 只")
        print(f"跳过: {results['skipped']} 只")
        print(f"失败: {results['failed']} 只")

        return results

    def check_missing_data(
        self,
        stocks: List[str],
        start_date: str,
        end_date: str,
        period: str = '1d'
    ) -> pd.DataFrame:
        """
        检查缺失数据

        Args:
            stocks: 股票列表
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期

        Returns:
            DataFrame: 缺失数据报告
        """
        print(f"\n检查数据完整性...")

        if not self.detector:
            self.detector = SmartDataDetector()
            self.detector.connect()

        # 批量检查
        all_missing = []
        for stock in stocks:
            report = self.detector.detect_missing_data(stock, start_date, end_date)
            if report['missing_days'] > 0:
                all_missing.append({
                    'stock': stock,
                    'missing_days': report['missing_days'],
                    'missing_date_ranges': report['missing_date_ranges']
                })

        if all_missing:
            df = pd.DataFrame(all_missing)
            print(f"发现 {len(df)} 只股票存在缺失数据")
            return df
        else:
            print("所有股票数据完整")
            return pd.DataFrame()

    def resume_import(self, checkpoint_file: str = 'import_checkpoint.json'):
        """
        断点续传导入（从检查点恢复）

        Args:
            checkpoint_file: 检查点文件路径
        """
        # TODO: 实现断点续传功能
        print("[INFO] 断点续传功能开发中...")


# 测试代码
if __name__ == "__main__":
    print("="*80)
    print("通用数据导入器测试")
    print("="*80)

    importer = UniversalDataImporter()
    importer.connect()

    # 测试1：导入上证50
    print("\n【测试1】导入上证50数据（2024年）")
    result = importer.import_board_stocks(
        board_name='上证50',
        start_date='2024-01-01',
        end_date='2024-12-31',
        period='1d',
        batch_size=10  # 小批量测试
    )

    # 测试2：从CSV导入
    print("\n\n【测试2】从CSV导入")
    # 先创建测试CSV
    test_stocks = ['600000.SH', '000001.SZ', '511380.SH']
    importer.csv_importer.export_stock_list(test_stocks, 'test_import.csv')

    result2 = importer.import_from_csv(
        csv_path='test_import.csv',
        start_date='2024-06-01',
        end_date='2024-12-31',
        period='1d'
    )

    # 测试3：自定义股票列表
    print("\n\n【测试3】自定义股票列表导入")
    result3 = importer.import_custom_stocks(
        stocks=['511380.SH', '511880.SH'],
        start_date='2024-01-01',
        end_date='2024-12-31',
        period='1d'
    )

    print("\n" + "="*80)
    print("测试完成！")
    print("="*80)
