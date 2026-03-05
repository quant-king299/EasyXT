# -*- coding: utf-8 -*-
"""
批量下载A股和可转债历史数据
支持断点续传、进度显示、多批次处理
"""
import sys
from pathlib import Path
import warnings
import pandas as pd
import json
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# 添加路径
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
sys.path.insert(0, str(project_root / 'src'))

from data_manager import LocalDataManager


class FullDataDownloader:
    """
    完整数据下载器

    功能：
    1. 下载全部A股和可转债
    2. 支持断点续传
    3. 显示实时进度
    4. 生成下载报告
    """

    def __init__(self,
                 years_back: int = 10,
                 include_stocks: bool = True,
                 include_bonds: bool = True):
        """
        初始化下载器

        Args:
            years_back: 回溯年数
            include_stocks: 是否下载股票
            include_bonds: 是否下载可转债
        """
        self.years_back = years_back
        self.include_stocks = include_stocks
        self.include_bonds = include_bonds

        # 创建数据管理器
        self.manager = LocalDataManager()

        # 日期范围
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.start_date = (datetime.now() - timedelta(days=365 * years_back)).strftime('%Y-%m-%d')

        # 进度文件
        self.progress_file = project_root / 'data' / 'download_progress.json'
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载进度
        self.progress = self._load_progress()

        # 下载统计
        self.stats = {
            'stocks': {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0},
            'bonds': {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
        }

        print("\n" + "=" * 70)
        print("完整数据下载器")
        print("=" * 70)
        print(f"日期范围: {self.start_date} ~ {self.end_date} (最近{years_back}年)")
        print(f"下载股票: {'是' if include_stocks else '否'}")
        print(f"下载可转债: {'是' if include_bonds else '否'}")
        print(f"数据目录: {self.manager.root_dir}")
        print("=" * 70 + "\n")

    def _load_progress(self) -> dict:
        """加载下载进度"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'stocks': {'completed': [], 'failed': []},
            'bonds': {'completed': [], 'failed': []},
            'last_update': None
        }

    def _save_progress(self):
        """保存下载进度"""
        self.progress['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)

    def _print_progress(self, symbol_type: str, current: int, total: int,
                       success: int, failed: int, skipped: int):
        """打印进度"""
        pct = (current / total) * 100 if total > 0 else 0
        print(f"\r[{symbol_type.upper()}] 进度: {current}/{total} ({pct:.1f}%) | "
              f"成功: {success} | 失败: {failed} | 跳过: {skipped}", end='', flush=True)

    def download_stocks(self):
        """下载全部A股数据"""
        if not self.include_stocks:
            return

        print("\n" + "=" * 70)
        print("开始下载A股数据")
        print("=" * 70 + "\n")

        # 获取股票列表
        stock_list = self.manager.get_all_stocks_list(
            include_st=True,
            include_sz=True,
            include_bj=True,
            exclude_st=True,
            exclude_delisted=True
        )

        if not stock_list:
            print("⚠️ 未获取到股票列表")
            return

        # 过滤已完成的股票
        completed = set(self.progress['stocks']['completed'])
        remaining = [s for s in stock_list if s not in completed]

        self.stats['stocks']['total'] = len(stock_list)
        self.stats['stocks']['skipped'] = len(completed)

        print(f"股票总数: {len(stock_list)}")
        print(f"已完成: {len(completed)}")
        print(f"待下载: {len(remaining)}")
        print(f"开始下载...\n")

        # 批量下载
        batch_size = 100
        for i in range(0, len(remaining), batch_size):
            batch = remaining[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(remaining) + batch_size - 1) // batch_size

            print(f"\n[批次 {batch_num}/{total_batches}] 下载 {len(batch)} 只股票")

            for j, symbol in enumerate(batch):
                current = len(completed) + j + 1

                try:
                    # 检查是否已经有本地数据
                    existing_df = self.manager.storage.load_data(symbol, 'daily')
                    if not existing_df.empty:
                        # 检查数据是否需要更新
                        last_date = existing_df.index.max()
                        if pd.to_datetime(last_date) >= pd.to_datetime(self.end_date) - pd.Timedelta(days=5):
                            self.stats['stocks']['skipped'] += 1
                            self.progress['stocks']['completed'].append(symbol)
                            self._print_progress('stocks', current, len(stock_list),
                                               self.stats['stocks']['success'],
                                               self.stats['stocks']['failed'],
                                               self.stats['stocks']['skipped'])
                            continue

                    # 下载数据
                    df = self.manager._fetch_from_source(symbol, self.start_date, self.end_date)

                    if df.empty:
                        self.stats['stocks']['failed'] += 1
                        self.progress['stocks']['failed'].append(symbol)
                        self._print_progress('stocks', current, len(stock_list),
                                           self.stats['stocks']['success'],
                                           self.stats['stocks']['failed'],
                                           self.stats['stocks']['skipped'])
                        continue

                    # 保存数据
                    success, file_size = self.manager.storage.save_data(df, symbol, 'daily')

                    if success:
                        self.manager.metadata.update_data_version(
                            symbol=symbol,
                            symbol_type='stock',
                            start_date=str(df.index.min().date()),
                            end_date=str(df.index.max().date()),
                            record_count=len(df),
                            file_size=file_size
                        )

                        self.stats['stocks']['success'] += 1
                        self.progress['stocks']['completed'].append(symbol)
                    else:
                        self.stats['stocks']['failed'] += 1
                        self.progress['stocks']['failed'].append(symbol)

                except Exception as e:
                    self.stats['stocks']['failed'] += 1
                    if symbol not in self.progress['stocks']['failed']:
                        self.progress['stocks']['failed'].append(symbol)

                self._print_progress('stocks', current, len(stock_list),
                                   self.stats['stocks']['success'],
                                   self.stats['stocks']['failed'],
                                   self.stats['stocks']['skipped'])

            # 保存进度
            self._save_progress()

        print(f"\n\nA股数据下载完成!")
        print(f"成功: {self.stats['stocks']['success']} | "
              f"失败: {self.stats['stocks']['failed']} | "
              f"跳过: {self.stats['stocks']['skipped']}")

    def download_bonds(self):
        """下载可转债数据"""
        if not self.include_bonds:
            return

        print("\n" + "=" * 70)
        print("开始下载可转债数据")
        print("=" * 70 + "\n")

        # 获取可转债列表
        bond_list = self.manager.get_all_convertible_bonds_list()

        if not bond_list:
            print("⚠️ 未获取到可转债列表")
            return

        # 过滤已完成的转债
        completed = set(self.progress['bonds']['completed'])
        remaining = [b for b in bond_list if b not in completed]

        self.stats['bonds']['total'] = len(bond_list)
        self.stats['bonds']['skipped'] = len(completed)

        print(f"可转债总数: {len(bond_list)}")
        print(f"已完成: {len(completed)}")
        print(f"待下载: {len(remaining)}")
        print(f"开始下载...\n")

        # 批量下载
        batch_size = 50
        for i in range(0, len(remaining), batch_size):
            batch = remaining[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(remaining) + batch_size - 1) // batch_size

            print(f"\n[批次 {batch_num}/{total_batches}] 下载 {len(batch)} 只可转债")

            for j, symbol in enumerate(batch):
                current = len(completed) + j + 1

                try:
                    # 检查是否已经有本地数据
                    existing_df = self.manager.storage.load_data(symbol, 'daily')
                    if not existing_df.empty:
                        # 检查数据是否需要更新
                        last_date = existing_df.index.max()
                        if pd.to_datetime(last_date) >= pd.to_datetime(self.end_date) - pd.Timedelta(days=5):
                            self.stats['bonds']['skipped'] += 1
                            self.progress['bonds']['completed'].append(symbol)
                            self._print_progress('bonds', current, len(bond_list),
                                               self.stats['bonds']['success'],
                                               self.stats['bonds']['failed'],
                                               self.stats['bonds']['skipped'])
                            continue

                    # 下载数据
                    df = self.manager._fetch_from_source(symbol, self.start_date, self.end_date)

                    if df.empty:
                        self.stats['bonds']['failed'] += 1
                        self.progress['bonds']['failed'].append(symbol)
                        self._print_progress('bonds', current, len(bond_list),
                                           self.stats['bonds']['success'],
                                           self.stats['bonds']['failed'],
                                           self.stats['bonds']['skipped'])
                        continue

                    # 保存数据
                    success, file_size = self.manager.storage.save_data(df, symbol, 'daily')

                    if success:
                        self.manager.metadata.update_data_version(
                            symbol=symbol,
                            symbol_type='bond',
                            start_date=str(df.index.min().date()),
                            end_date=str(df.index.max().date()),
                            record_count=len(df),
                            file_size=file_size
                        )

                        self.stats['bonds']['success'] += 1
                        self.progress['bonds']['completed'].append(symbol)
                    else:
                        self.stats['bonds']['failed'] += 1
                        self.progress['bonds']['failed'].append(symbol)

                except Exception as e:
                    self.stats['bonds']['failed'] += 1
                    if symbol not in self.progress['bonds']['failed']:
                        self.progress['bonds']['failed'].append(symbol)

                self._print_progress('bonds', current, len(bond_list),
                                   self.stats['bonds']['success'],
                                   self.stats['bonds']['failed'],
                                   self.stats['bonds']['skipped'])

            # 保存进度
            self._save_progress()

        print(f"\n\n可转债数据下载完成!")
        print(f"成功: {self.stats['bonds']['success']} | "
              f"失败: {self.stats['bonds']['failed']} | "
              f"跳过: {self.stats['bonds']['skipped']}")

    def generate_report(self):
        """生成下载报告"""
        print("\n" + "=" * 70)
        print("下载报告")
        print("=" * 70)

        # 获取数据统计
        stats = self.manager.get_statistics()

        print(f"\n【股票数据】")
        print(f"  总数: {self.stats['stocks']['total']}")
        print(f"  成功: {self.stats['stocks']['success']}")
        print(f"  失败: {self.stats['stocks']['failed']}")
        print(f"  跳过: {self.stats['stocks']['skipped']}")

        if self.stats['stocks']['total'] > 0:
            success_rate = (self.stats['stocks']['success'] / self.stats['stocks']['total']) * 100
            print(f"  成功率: {success_rate:.1f}%")

        print(f"\n【可转债数据】")
        print(f"  总数: {self.stats['bonds']['total']}")
        print(f"  成功: {self.stats['bonds']['success']}")
        print(f"  失败: {self.stats['bonds']['failed']}")
        print(f"  跳过: {self.stats['bonds']['skipped']}")

        if self.stats['bonds']['total'] > 0:
            success_rate = (self.stats['bonds']['success'] / self.stats['bonds']['total']) * 100
            print(f"  成功率: {success_rate:.1f}%")

        print(f"\n【存储统计】")
        self.manager.print_summary()

        # 保存报告
        report_file = project_root / 'data' / 'download_report.json'
        report_data = {
            'download_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range': {'start': self.start_date, 'end': self.end_date},
            'years_back': self.years_back,
            'stocks': self.stats['stocks'],
            'bonds': self.stats['bonds'],
            'storage_stats': stats
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存到: {report_file}")
        print("=" * 70 + "\n")

    def run(self):
        """执行完整下载流程"""
        try:
            # 下载股票
            if self.include_stocks:
                self.download_stocks()

            # 下载可转债
            if self.include_bonds:
                self.download_bonds()

            # 生成报告
            self.generate_report()

            print("✅ 下载任务完成!")

        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断下载")
            print("💾 进度已保存，下次运行将从断点继续")
            self._save_progress()

        except Exception as e:
            print(f"\n\n❌ 下载失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.manager.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量下载A股和可转债历史数据')
    parser.add_argument('--years', type=int, default=10,
                       help='回溯年数 (默认: 10)')
    parser.add_argument('--stocks', action='store_true', default=True,
                       help='下载股票数据')
    parser.add_argument('--no-stocks', action='store_false', dest='stocks',
                       help='不下载股票数据')
    parser.add_argument('--bonds', action='store_true', default=True,
                       help='下载可转债数据')
    parser.add_argument('--no-bonds', action='store_false', dest='bonds',
                       help='不下载可转债数据')
    parser.add_argument('--reset', action='store_true',
                       help='重置进度，重新下载所有数据')

    args = parser.parse_args()

    # 创建下载器
    downloader = FullDataDownloader(
        years_back=args.years,
        include_stocks=args.stocks,
        include_bonds=args.bonds
    )

    # 重置进度
    if args.reset:
        print("⚠️ 重置下载进度...")
        downloader.progress = {
            'stocks': {'completed': [], 'failed': []},
            'bonds': {'completed': [], 'failed': []},
            'last_update': None
        }
        downloader._save_progress()

    # 运行下载
    downloader.run()


if __name__ == '__main__':
    main()
