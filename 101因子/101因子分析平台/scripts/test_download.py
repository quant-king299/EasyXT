# -*- coding: utf-8 -*-
"""
简单的数据下载测试（无emoji版本）
"""
import sys
import os
from pathlib import Path

# 强制UTF-8输出
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加src目录到路径
project_root = Path(__file__).parents[1]
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

# 禁用警告
import warnings
warnings.filterwarnings('ignore')

from data_manager import LocalDataManager


def main():
    """简单下载测试"""
    print("\n" + "="*70)
    print("Data Download Test")
    print("="*70)

    # 创建管理器
    manager = LocalDataManager()

    # 测试1只股票
    symbol = '000001.SZ'

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    print(f"\nDownloading: {symbol}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Save to: {manager.root_dir}\n")

    # 下载
    results = manager.download_and_save(
        symbols=[symbol],
        start_date=start_date,
        end_date=end_date,
        symbol_type='stock',
        show_progress=True
    )

    # 检查结果
    if symbol in results:
        df = results[symbol]
        print(f"\n[SUCCESS] Download completed!")
        print(f"Records: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print(f"Date range: {df.index.min()} to {df.index.max()}")
        print(f"\nPreview:")
        print(df.tail())

        # 测试保存和加载
        print(f"\n[TEST] Testing save and load...")
        loaded = manager.storage.load_data(symbol, 'daily')
        print(f"Loaded records: {len(loaded)}")

        # 检查文件
        file_info = manager.storage.get_file_info(symbol, 'daily')
        if file_info:
            print(f"File size: {file_info['file_size_mb']:.2f} MB")
            print(f"File path: {file_info['file_path']}")
    else:
        print(f"\n[FAILED] Download failed")

    manager.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
