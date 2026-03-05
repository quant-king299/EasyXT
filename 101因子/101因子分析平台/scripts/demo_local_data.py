# -*- coding: utf-8 -*-
"""
演示：使用本地数据加速因子计算
"""
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 添加路径
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
workspace_dir = project_root.parents[0]
if workspace_dir.name == '101因子':
    workspace_dir = workspace_dir.parents[0]

sys.path.insert(0, str(workspace_dir))
sys.path.insert(0, str(project_root / 'src'))


def demo_local_data():
    """演示本地数据的使用"""
    print("\n" + "="*70)
    print("Demo: Using Local Data for Factor Calculation")
    print("="*70)

    from data_manager import LocalDataManager
    import time

    # 创建数据管理器
    manager = LocalDataManager()

    print(f"\n[INFO] Local data location: {manager.root_dir}")

    # 查看本地有哪些数据
    symbols = manager.get_all_symbols()
    print(f"\n[INFO] Available stocks in local storage: {len(symbols)}")
    for s in symbols:
        info = manager.get_data_info(s)
        if info:
            print(f"  {s}: {info['num_rows']} records, {info['file_size_mb']:.2f} MB")

    # 测试加载速度
    print(f"\n[TEST] Loading data from local storage...")
    start = time.time()

    data = manager.load_data(symbols, start_date='2024-01-01', end_date='2024-12-31')

    elapsed = time.time() - start
    print(f"[OK] Loaded {len(data)} stocks in {elapsed:.2f} seconds")

    # 显示数据预览
    if data:
        print(f"\n[INFO] Data preview:")
        for symbol, df in list(data.items())[:3]:
            print(f"\n{symbol}:")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Latest close price: {df['close'].iloc[-1]:.2f}")
            print(f"  Date range: {df.index.min()} to {df.index.max()}")

    # 对比：如果从QMT下载需要多久
    print(f"\n[INFO] Speed comparison:")
    print(f"  Local storage: {elapsed:.2f} seconds")
    print(f"  QMT download: ~60 seconds (estimated)")
    print(f"  Speed improvement: ~{60/elapsed:.0f}x faster!")

    # 演示因子计算（使用本地数据）
    print(f"\n[TEST] Calculating a simple factor using local data...")

    if data and '000001.SZ' in data:
        df = data['000001.SZ']

        # 计算一个简单的动量因子
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma20'] = df['close'].rolling(20).mean()

        print(f"[OK] Factor calculated")
        print(f"\n  Latest values for 000001.SZ:")
        print(f"    Close: {df['close'].iloc[-1]:.2f}")
        print(f"    5-day momentum: {df['momentum_5'].iloc[-1]*100:.2f}%")
        print(f"    10-day momentum: {df['momentum_10'].iloc[-1]*100:.2f}%")
        print(f"    MA5: {df['ma5'].iloc[-1]:.2f}")
        print(f"    MA20: {df['ma20'].iloc[-1]:.2f}")

    # 演示数据更新
    print(f"\n[INFO] To update data later, you can run:")
    print(f"  manager.update_data()  # Incremental update")
    print(f"  manager.download_and_save([...])  # Download new stocks")

    manager.close()

    print(f"\n" + "="*70)
    print(f"[SUCCESS] Demo completed!")
    print(f"[INFO] Your local data system is ready to use!")
    print(f"="*70)


if __name__ == '__main__':
    try:
        demo_local_data()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
