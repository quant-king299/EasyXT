# -*- coding: utf-8 -*-
"""
测试QMT连接和获取股票列表
"""
import sys
from pathlib import Path

# 添加路径
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
sys.path.insert(0, str(project_root / 'src'))

print("=" * 70)
print("QMT连接测试")
print("=" * 70)

# 测试xtquant导入
print("\n[1] 测试xtquant模块导入...")
try:
    import xtquant.xtdata as xt_data
    print("✅ xtquant模块导入成功")
    print(f"   模块路径: {xt_data.__file__}")
except ImportError as e:
    print(f"❌ xtquant模块导入失败: {e}")
    print("   请安装xtquant: pip install xtquant")
    sys.exit(1)

# 测试连接
print("\n[2] 测试QMT连接...")
try:
    # 测试获取单只股票信息
    test_stock = '000001.SZ'
    print(f"   测试股票: {test_stock}")
    info = xt_data.get_instrument_detail(test_stock)

    if info and len(info) > 0:
        print(f"✅ QMT连接成功")
        print(f"   股票信息: {info}")
    else:
        print(f"⚠️ 无法获取股票信息，QMT可能未启动")
        print("   请启动QMT并登录")
except Exception as e:
    print(f"❌ QMT连接失败: {e}")
    print("   请确保QMT已启动并登录")
    sys.exit(1)

# 测试获取股票列表的方法
print("\n[3] 测试获取股票列表的方法...")

# 方法1: get_stock_list_in_sector
print("\n   方法1: get_stock_list_in_sector")
sector_names = [
    'SH_A_STOCK', 'SZ_A_STOCK', 'BJ_A_STOCK',
    '沪深A股', 'A股', '全部A股'
]

for sector in sector_names:
    try:
        stocks = xt_data.get_stock_list_in_sector(sector)
        if stocks and len(stocks) > 0:
            print(f"   ✅ {sector}: {len(stocks)} 只股票")
            print(f"      示例: {stocks[:5]}")
        else:
            print(f"   ⚠️ {sector}: 空")
    except Exception as e:
        print(f"   ❌ {sector}: {e}")

# 方法2: get_full_tick
print("\n   方法2: get_full_tick (测试)")
try:
    tick_data = xt_data.get_full_tick(['000001.SZ', '600000.SH'])
    if tick_data:
        print(f"   ✅ get_full_tick 可用")
        print(f"      返回键: {list(tick_data.keys())}")
    else:
        print(f"   ⚠️ get_full_tick 返回空")
except Exception as e:
    print(f"   ❌ get_full_tick: {e}")

# 方法3: download_hist_data
print("\n   方法3: download_hist_data (测试)")
try:
    from datetime import datetime, timedelta
    end_time = datetime.now().strftime('%Y%m%d')
    start_time = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

    print(f"   测试下载: 000001.SZ ({start_time} ~ {end_time})")
    result = xt_data.download_hist_data(
        stock_code='000001.SZ',
        period='1d',
        start_time=start_time,
        end_time=end_time
    )
    print(f"   ✅ download_hist_data 可用")

    # 获取数据
    data = xt_data.get_market_data_ex(
        stock_list=['000001.SZ'],
        period='1d',
        start_time=start_time,
        end_time=end_time
    )
    if data and '000001.SZ' in data:
        df = data['000001.SZ']
        print(f"   ✅ 成功获取数据: {len(df)} 条记录")
        print(f"      列名: {list(df.columns)}")
        print(f"      日期范围: {df.index.min()} ~ {df.index.max()}")
    else:
        print(f"   ⚠️ 数据为空")

except Exception as e:
    print(f"   ❌ download_hist_data: {e}")
    import traceback
    print(f"   详细错误: {traceback.format_exc()}")

# 测试本地数据管理器
print("\n[4] 测试本地数据管理器...")
try:
    from data_manager import LocalDataManager

    manager = LocalDataManager()

    # 测试获取股票列表
    print("\n   获取A股列表...")
    stock_list = manager.get_all_stocks_list()
    print(f"   ✅ 获取到 {len(stock_list)} 只A股")
    if stock_list:
        print(f"      示例: {stock_list[:10]}")

    # 测试获取可转债列表
    print("\n   获取可转债列表...")
    bond_list = manager.get_all_convertible_bonds_list()
    print(f"   ✅ 获取到 {len(bond_list)} 只可转债")
    if bond_list:
        print(f"      示例: {bond_list[:10]}")

    # 测试下载数据
    print("\n   测试下载数据...")
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    print(f"   下载 000001.SZ ({start_date} ~ {end_date})")
    results = manager.download_and_save(
        symbols=['000001.SZ'],
        start_date=start_date,
        end_date=end_date,
        show_progress=True
    )

    if results:
        print(f"   ✅ 下载成功")
        for symbol, df in results.items():
            print(f"      {symbol}: {len(df)} 条记录")

    manager.close()

except Exception as e:
    print(f"❌ 本地数据管理器测试失败: {e}")
    import traceback
    print(f"详细错误: {traceback.format_exc()}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

# 提供使用建议
print("\n💡 使用建议:")
print("1. 如果QMT连接失败，请确保:")
print("   - QMT已启动")
print("   - 已登录账号")
print("   - xtdata模块已正确安装")
print("\n2. 如果获取股票列表为空，系统会使用预定义的股票列表")
print("   预定义列表包含主要的大盘蓝筹股，可以正常使用")
print("\n3. 建议先下载少量股票测试:")
print("   manager.download_and_save(")
print("       symbols=['000001.SZ', '600000.SH'],")
print("       start_date='2024-01-01',")
print("       end_date='2024-12-31'")
print("   )")
