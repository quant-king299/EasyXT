# -*- coding: utf-8 -*-
"""
直接测试QMT数据获取（绕过初始化打印）
"""
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 添加工作空间到路径
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
workspace_dir = project_root.parents[0]
if workspace_dir.name == '101因子':
    workspace_dir = workspace_dir.parents[0]

if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))

print(f"Workspace: {workspace_dir}")

def test_qmt_direct():
    """直接测试QMT数据"""
    print("\n" + "="*70)
    print("Direct QMT Data Test")
    print("="*70)

    try:
        # 直接导入xtdata
        import xtquant.xtdata as xt_data

        print("\n[OK] xtdata imported successfully")

        # 测试获取数据
        symbol = '000001.SZ'
        start_time = '20240101'
        end_time = '20241231'

        print(f"\n[TEST] Downloading {symbol}...")
        print(f"  Time range: {start_time} to {end_time}")

        # 获取数据
        data = xt_data.get_market_data_ex(
            stock_list=[symbol],
            period='1d',
            start_time=start_time,
            end_time=end_time,
            fill_data=True
        )

        if data and symbol in data:
            df = data[symbol]

            print(f"\n[SUCCESS] Data downloaded!")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)}")
            print(f"\n  Preview:")
            print(df.tail())

            print(f"\n[INFO] Data types:")
            print(df.dtypes)

            print(f"\n[INFO] Basic statistics:")
            print(df.describe())

            # 保存测试
            print(f"\n[TEST] Saving to local Parquet file...")

            # 导入我们的存储
            sys.path.insert(0, str(project_root / 'src'))
            from data_manager import LocalDataManager

            manager = LocalDataManager()

            # 标准化列名
            df.columns = df.columns.str.lower()

            # 确保日期索引
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            # 保存
            success, size = manager.storage.save_data(df, symbol, 'daily')

            if success:
                print(f"[SUCCESS] Saved to: {manager.storage.root_dir / 'daily' / f'{symbol}.parquet'}")
                print(f"  File size: {size:.2f} MB")

                # 测试加载
                print(f"\n[TEST] Loading back from Parquet...")
                loaded = manager.storage.load_data(symbol, 'daily')
                print(f"[OK] Loaded {len(loaded)} records")

            manager.close()

        else:
            print(f"\n[FAILED] No data returned")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import pandas as pd  # 确保pandas已导入
    test_qmt_direct()
