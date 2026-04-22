# -*- coding: utf-8 -*-
"""
数据下载管理器
将每日指标数据下载到DuckDB数据库
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import sys
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from src.data_manager.duckdb_data_manager import DuckDBDataManager


class DataDownloadManager:
    """
    数据下载管理器

    功能：
    1. 从QMT或Tushare下载每日指标数据
    2. 存储到DuckDB数据库
    3. 提供数据查询功能
    """

    def __init__(self, tushare_token: Optional[str] = None):
        """
        初始化下载管理器

        Args:
            tushare_token: Tushare Pro API token (可选)
        """
        self.tushare_token = tushare_token
        self.tushare_pro = None

        # 初始化DuckDB数据管理器
        config = {
            'data_paths': {
                'root_dir': 'D:/StockData',
                'database': 'stock_data.ddb',
                'metadata': 'stock_data.ddb'  # 使用DuckDB统一存储
            }
        }
        self.db_manager = DuckDBDataManager(config)

        print(f"[INFO] 数据库路径: {self.db_manager.db_path}")

        # 初始化Tushare（如果提供token）
        if tushare_token:
            try:
                import tushare as ts
                self.tushare_pro = ts.pro_api(tushare_token)
                print("[INFO] Tushare Pro initialized successfully")
            except ImportError:
                print("[WARN] tushare package not installed")
            except Exception as e:
                print(f"[WARN] Failed to initialize Tushare: {e}")

    def download_daily_basic_qmt(self,
                                stock_list: List[str],
                                start_date: str,
                                end_date: str) -> pd.DataFrame:
        """
        从QMT下载每日指标数据

        Args:
            stock_list: 股票列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            DataFrame with daily basic data
        """
        print(f"\n[INFO] 尝试从QMT下载每日指标数据...")
        print(f"  股票数: {len(stock_list)}")
        print(f"  日期范围: {start_date} - {end_date}")

        try:
            # 尝试从DuckDB获取现有数据
            # 如果数据已存在，则不需要重新下载
            existing_data = self.load_daily_basic_from_duckdb()

            if not existing_data.empty:
                print(f"[INFO] DuckDB中已有 {len(existing_data)} 条记录")
                # 检查是否需要更新
                max_date = existing_data['trade_date'].max()
                print(f"[INFO] 最新数据日期: {max_date}")

                # 如果用户请求的日期范围已完全覆盖，直接返回
                if (pd.to_datetime(end_date) <= pd.to_datetime(max_date)):
                    print("[INFO] 数据已完整，无需下载")
                    return existing_data

            # 从QMT下载数据
            import xtquant.xtdata as xt_data

            all_data = []

            for i, symbol in enumerate(stock_list, 1):
                print(f"[{i}/{len(stock_list)}] 下载 {symbol}...", end=' ')

                try:
                    # 获取日线行情数据
                    data = xt_data.get_market_data_ex(
                        stock_list=[symbol],
                        period='1d',
                        start_time=start_date,
                        end_time=end_date,
                        fill_data=True
                    )

                    if data and symbol in data:
                        df = data[symbol]

                        if not df.empty:
                            # 标准化列名
                            df.columns = df.columns.str.lower()

                            # 添加股票代码和日期
                            df['ts_code'] = symbol
                            if 'time' in df.columns:
                                df['trade_date'] = pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y%m%d')

                            # 选择需要的字段
                            # QMT可能不直接提供PE、PB，这里先返回基础数据
                            result = {
                                'ts_code': symbol,
                                'trade_date': df['trade_date'],
                                'close': df['close'] if 'close' in df.columns else None,
                                'open': df['open'] if 'open' in df.columns else None,
                                'high': df['high'] if 'high' in df.columns else None,
                                'low': df['low'] if 'low' in df.columns else None,
                                'volume': df['volume'] if 'volume' in df.columns else None,
                                'amount': df['amount'] if 'amount' in df.columns else None,
                            }

                            all_data.append(pd.DataFrame(result))
                            print(f"[OK] {len(df)} records")
                        else:
                            print(f"[SKIP] No data")
                    else:
                        print(f"[SKIP] No data")

                except Exception as e:
                    print(f"[ERROR] {e}")
                    continue

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                print(f"\n[SUCCESS] QMT下载完成: {len(combined_df)} 条记录")
                return combined_df
            else:
                print(f"\n[WARN] QMT未获取到数据，将尝试Tushare")
                return pd.DataFrame()

        except ImportError:
            print(f"\n[ERROR] QMT (xtquant) 未安装")
            return pd.DataFrame()
        except Exception as e:
            print(f"\n[ERROR] QMT下载失败: {e}")
            return pd.DataFrame()

    def download_daily_basic_tushare(self,
                                    start_date: str,
                                    end_date: str) -> pd.DataFrame:
        """
        从Tushare下载每日指标数据

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            DataFrame with daily basic data
        """
        if not self.tushare_pro:
            print("[ERROR] Tushare Pro未初始化，请提供token")
            return pd.DataFrame()

        print(f"\n[INFO] 从Tushare下载每日指标数据...")
        print(f"  日期范围: {start_date} - {end_date}")

        try:
            all_data = []

            # 生成日期列表
            date_range = pd.date_range(start_date, end_date, freq='D')
            trade_dates = [d.strftime('%Y%m%d') for d in date_range]

            for i, trade_date in enumerate(trade_dates, 1):
                print(f"[{i}/{len(trade_dates)}] 下载 {trade_date}...", end=' ')

                try:
                    # 调用Tushare API
                    df = self.tushare_pro.daily_basic(
                        trade_date=trade_date,
                        fields='ts_code,trade_date,close,turnover_rate,volume,amount,pe,pb,total_mv,circ_mv'
                    )

                    if df is not None and not df.empty:
                        all_data.append(df)
                        print(f"[OK] {len(df)} stocks")
                    else:
                        print(f"[SKIP] No data")

                    # 避免请求过快
                    import time
                    time.sleep(0.1)

                except Exception as e:
                    print(f"[ERROR] {e}")
                    continue

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                print(f"\n[SUCCESS] Tushare下载完成: {len(combined_df)} 条记录")
                return combined_df
            else:
                print(f"\n[WARN] Tushare未获取到数据")
                return pd.DataFrame()

        except Exception as e:
            print(f"\n[ERROR] Tushare下载失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def save_to_duckdb(self, df: pd.DataFrame, table_name: str = 'daily_basic') -> bool:
        """
        保存数据到DuckDB

        Args:
            df: 数据DataFrame
            table_name: 表名

        Returns:
            是否保存成功
        """
        if df.empty:
            print("[WARN] 数据为空，跳过保存")
            return False

        try:
            # 使用DuckDB存储
            self.db_manager.storage.save_data(
                df,
                table_name=table_name,
                if_exists='append'  # 追加数据
            )

            print(f"\n[SUCCESS] 数据已保存到DuckDB表: {table_name}")
            print(f"  记录数: {len(df)}")

            return True

        except Exception as e:
            print(f"[ERROR] 保存到DuckDB失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_daily_basic_from_duckdb(self) -> pd.DataFrame:
        """
        从DuckDB加载每日指标数据

        Returns:
            DataFrame with daily basic data
        """
        try:
            # 从DuckDB读取数据
            df = self.db_manager.storage.load_data(
                table_name='daily_basic'
            )

            if not df.empty:
                print(f"[INFO] 从DuckDB加载了 {len(df)} 条记录")
            else:
                print(f"[WARN] DuckDB中暂无数据")

            return df

        except Exception as e:
            print(f"[ERROR] 从DuckDB加载失败: {e}")
            return pd.DataFrame()

    def get_data_summary(self) -> Dict:
        """
        获取数据摘要

        Returns:
            数据摘要字典
        """
        df = self.load_daily_basic_from_duckdb()

        if df.empty:
            return {
                'total_records': 0,
                'date_range': 'N/A',
                'stock_count': 0,
                'fields': [],
                'table_size': 'N/A'
            }

        # 获取表大小
        try:
            import os
            table_size = os.path.getsize(self.db_manager.db_path) / (1024 * 1024)  # MB
        except:
            table_size = 0

        summary = {
            'total_records': len(df),
            'date_range': f"{df['trade_date'].min()} - {df['trade_date'].max()}" if 'trade_date' in df.columns else 'N/A',
            'stock_count': df['ts_code'].nunique() if 'ts_code' in df.columns else 0,
            'fields': df.columns.tolist(),
            'table_size': f"{table_size:.2f} MB"
        }

        return summary


def test_download_manager():
    """测试下载管理器"""
    print("=" * 70)
    print("数据下载管理器测试")
    print("=" * 70)

    # 创建管理器
    manager = DataDownloadManager()

    # 测试数据摘要
    summary = manager.get_data_summary()
    print(f"\n数据摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_download_manager()
