# -*- coding: utf-8 -*-
"""
批量下载股票数据到本地存储（修复版）
"""
import sys
from pathlib import Path
import warnings
import pandas as pd
warnings.filterwarnings('ignore')

# 添加路径
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
workspace_dir = project_root.parents[0]
if workspace_dir.name == '101因子':
    workspace_dir = workspace_dir.parents[0]

sys.path.insert(0, str(workspace_dir))
sys.path.insert(0, str(project_root / 'src'))


def batch_download_stocks():
    """批量下载股票数据"""
    print("\n" + "="*70)
    print("Batch Stock Download to Local Storage")
    print("="*70)

    # 导入模块
    import xtquant.xtdata as xt_data
    from data_manager import LocalDataManager

    # 创建数据管理器
    manager = LocalDataManager()
    print(f"\n[INFO] Data will be saved to: {manager.root_dir}")

    # 股票列表
    stock_list = [
        # 大盘蓝筹
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600000.SH',  # 浦发银行
        '600036.SH',  # 招商银行
        '600519.SH',  # 贵州茅台
        '601318.SH',  # 中国平安
        '601398.SH',  # 工商银行
        '601857.SH',  # 中国石油
        # 科技股
        '000063.SZ',  # 中兴通讯
        '000725.SZ',  # 京东方A
    ]

    # 时间范围：最近2年
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y%m%d')

    print(f"\n[INFO] Download configuration:")
    print(f"  Stocks: {len(stock_list)}")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"\n[INFO] Starting download...\n")

    success_count = 0
    failed_symbols = []

    for i, symbol in enumerate(stock_list, 1):
        print(f"[{i}/{len(stock_list)}] {symbol}...", end=' ')

        try:
            # 从QMT下载数据
            data = xt_data.get_market_data_ex(
                stock_list=[symbol],
                period='1d',
                start_time=start_date,
                end_time=end_date,
                fill_data=True
            )

            if data and symbol in data:
                df = data[symbol]

                # 标准化数据
                df.columns = df.columns.str.lower()

                # 转换时间戳索引
                if 'time' in df.columns:
                    df['date'] = pd.to_datetime(df['time'], unit='ms')
                    df = df.set_index('date')
                elif not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)

                # 保存到本地
                success, file_size = manager.storage.save_data(df, symbol, 'daily')

                if success:
                    # 更新元数据
                    manager.metadata.update_data_version(
                        symbol=symbol,
                        symbol_type='stock',
                        start_date=str(df.index.min().date()),
                        end_date=str(df.index.max().date()),
                        record_count=len(df),
                        file_size=file_size
                    )

                    print(f"[OK] {len(df)} records, {file_size:.2f} MB")
                    success_count += 1
                else:
                    print(f"[FAILED] Save failed")
                    failed_symbols.append(symbol)
            else:
                print(f"[FAILED] No data")
                failed_symbols.append(symbol)

        except Exception as e:
            print(f"[ERROR] {e}")
            failed_symbols.append(symbol)

    # 打印总结
    print(f"\n" + "="*70)
    print(f"[SUMMARY] Download completed!")
    print(f"[SUCCESS] {success_count}/{len(stock_list)} stocks downloaded")
    if failed_symbols:
        print(f"[FAILED] {len(failed_symbols)} stocks failed:")
        for s in failed_symbols:
            print(f"  - {s}")

    # 显示统计
    print(f"\n[INFO] Storage statistics:")
    manager.print_summary()

    manager.close()

    print(f"\n[SUCCESS] Data saved to: {manager.root_dir}")
    print(f"[INFO] Next time you load data, it will be much faster!")


if __name__ == '__main__':
    try:
        batch_download_stocks()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
