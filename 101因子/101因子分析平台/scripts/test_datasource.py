# -*- coding: utf-8 -*-
"""
测试数据源是否正常工作
"""
import sys
from pathlib import Path

# 添加工作空间到路径
# 从 scripts/xxx.py -> 回到项目根目录 -> 再回到上级目录(miniqmt扩展)
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]  # 101因子分析平台
workspace_dir = project_root.parents[0]  # miniqmt扩展

# 确保在正确的目录
if workspace_dir.name == '101因子':
    workspace_dir = workspace_dir.parents[0]

if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))

print(f"Workspace: {workspace_dir}")

import warnings
warnings.filterwarnings('ignore')

from gui_app.backtest.data_manager import DataManager

def test_datasource():
    """测试数据源"""
    print("="*70)
    print("Testing Data Source")
    print("="*70)

    # 创建数据管理器
    dm = DataManager()

    # 显示连接状态
    print("\nConnection Status:")
    status = dm.get_connection_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    # 测试获取数据
    print("\nTesting data download...")
    symbol = '000001.SZ'
    start_date = '2024-01-01'
    end_date = '2024-12-31'

    print(f"  Symbol: {symbol}")
    print(f"  Date Range: {start_date} to {end_date}")

    try:
        df = dm.get_stock_data(symbol, start_date, end_date, period='1d')

        if not df.empty:
            print(f"\n[SUCCESS] Data downloaded!")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)}")
            print(f"\n  Preview:")
            print(df.tail())
            print(f"\n  Data types:")
            print(df.dtypes)
        else:
            print(f"\n[FAILED] Empty data returned")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_datasource()
