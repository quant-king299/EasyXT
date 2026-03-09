"""
数据下载和查询的正确使用方式示例

这个文件演示了如何正确使用EasyXT项目中的不同数据管理器
"""

# ==========================================
# 方式1: 数据下载 - 使用LocalDataManager
# ==========================================
print("=" * 60)
print("方式1: 数据下载 - 使用LocalDataManager")
print("=" * 60)

import sys
sys.path.append('101因子/101因子分析平台/src')

try:
    from data_manager import LocalDataManager

    # 创建本地数据管理器（用于下载数据）
    dm_download = LocalDataManager()

    # 下载数据
    print("正在下载数据...")
    dm_download.download_and_save(
        symbols=['000001.SZ', '600000.SH'],
        start_date='2020-01-01',
        end_date='2023-12-31',
        symbol_type='stock'
    )
    print("✓ 数据下载完成")

except Exception as e:
    print(f"❌ LocalDataManager使用失败: {e}")
    print("提示：请确保101因子平台的相关依赖已安装")


# ==========================================
# 方式2: 数据查询 - 使用easyxt_backtest.DataManager
# ==========================================
print("\n" + "=" * 60)
print("方式2: 数据查询 - 使用easyxt_backtest.DataManager")
print("=" * 60)

try:
    from easyxt_backtest import DataManager

    # 创建数据管理器（用于查询数据）
    dm_query = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

    # 查询数据
    print("正在查询数据...")
    data = dm_query.get_price(
        symbols=['000001.SZ'],
        start_date='2020-01-01',
        end_date='2020-01-10'
    )

    if data is not None and not data.empty:
        print(f"✓ 查询成功，获取到 {len(data)} 条数据")
        print(data.head())
    else:
        print("⚠️ 查询成功但没有数据（可能是数据库中没有数据）")

    dm_query.close()

except Exception as e:
    print(f"❌ DataManager查询失败: {e}")
    print("提示：请确保DuckDB数据库文件存在")


# ==========================================
# 关键区别说明
# ==========================================
print("\n" + "=" * 60)
print("📝 关键区别说明")
print("=" * 60)

print("""
1. LocalDataManager (101因子平台)
   - 用途：数据下载和管理
   - 位置：101因子/101因子分析平台/src/data_manager.py
   - 主要方法：
     * download_and_save() - 下载数据
     * get_price() - 查询本地parquet数据
     * update_data() - 更新数据

2. DataManager (easyxt_backtest)
   - 用途：数据查询和回测
   - 位置：easyxt_backtest/data_manager.py
   - 主要方法：
     * get_price() - 查询价格数据
     * get_fundamentals() - 查询基本面数据
     * get_trading_dates() - 查询交易日
     * 不包含下载功能！

3. 推荐使用流程：
   Step 1: 使用LocalDataManager下载数据
   Step 2: 使用DataManager进行回测查询

示例流程：
```python
# 第一步：下载数据
from data_manager import LocalDataManager
dm = LocalDataManager()
dm.download_and_save(symbols=['000001.SZ'], ...)

# 第二步：回测时查询数据
from easyxt_backtest import DataManager
dm = DataManager(duckdb_path='...')
data = dm.get_price(symbols=['000001.SZ'], ...)
```
""")

print("=" * 60)
print("示例执行完成！")
print("=" * 60)
