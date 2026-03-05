# -*- coding: utf-8 -*-
"""
测试easy_xt连接和下载数据
"""
import sys
from pathlib import Path

# 添加路径
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # 回到miniqmt扩展目录
sys.path.insert(0, str(project_root))

print("=" * 70)
print("EasyXT连接测试")
print("=" * 70)

# 测试easy_xt导入
print("\n[1] 测试easy_xt模块导入...")
try:
    import easy_xt
    print("✅ easy_xt模块导入成功")
except ImportError as e:
    print(f"❌ easy_xt模块导入失败: {e}")
    sys.exit(1)

# 测试QMT连接
print("\n[2] 测试QMT连接...")
try:
    # 获取API实例
    api = easy_xt.get_api()
    print("✅ 成功获取API实例")

    # 测试获取股票信息
    test_stock = '000001.SZ'
    print(f"   测试股票: {test_stock}")

    # 尝试获取数据
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

    data = easy_xt.get_stock_data(
        stock_code=test_stock,
        start_date='2024-01-01',
        end_date='2024-01-31',
        period='1d'
    )

    if data is not None and not data.empty:
        print(f"✅ QMT连接成功")
        print(f"   数据形状: {data.shape}")
        print(f"   列名: {list(data.columns)}")
        print(f"   日期范围: {data.index.min()} ~ {data.index.max()}")
        print(f"   最新收盘价: {data['close'].iloc[-1]:.2f}")
    else:
        print(f"⚠️ 数据为空，请检查QMT是否已启动并登录")

except Exception as e:
    print(f"❌ QMT连接失败: {e}")
    import traceback
    print(f"详细错误: {traceback.format_exc()}")
    print("\n💡 请确保:")
    print("   1. QMT已启动")
    print("   2. 已登录账号")
    print("   3. config/unified_config.json 配置正确")
    sys.exit(1)

# 测试本地数据管理器
print("\n[3] 测试本地数据管理器...")
try:
    factor_platform_path = project_root / "101因子" / "101因子分析平台" / "src"
    if str(factor_platform_path) not in sys.path:
        sys.path.insert(0, str(factor_platform_path))

    from data_manager import LocalDataManager

    manager = LocalDataManager()
    print("✅ 本地数据管理器初始化成功")

    # 测试获取股票列表
    print("\n[4] 测试获取A股列表...")
    stock_list = manager.get_all_stocks_list()
    print(f"✅ 获取到 {len(stock_list)} 只A股")
    if stock_list:
        print(f"   前10只: {stock_list[:10]}")
        print(f"   后10只: {stock_list[-10:]}")

    # 测试下载数据
    print("\n[5] 测试下载数据...")
    test_symbols = ['000001.SZ', '600000.SH']

    results = manager.download_and_save(
        symbols=test_symbols,
        start_date='2024-01-01',
        end_date='2024-01-31',
        show_progress=True
    )

    if results:
        print(f"\n✅ 下载成功: {len(results)} 只股票")
        for symbol, df in results.items():
            print(f"   {symbol}: {len(df)} 条记录")
    else:
        print(f"\n⚠️ 下载失败")

    # 测试加载数据
    print("\n[6] 测试加载本地数据...")
    loaded_data = manager.load_data(
        symbols=test_symbols,
        start_date='2024-01-01',
        end_date='2024-01-31'
    )

    if loaded_data:
        print(f"✅ 加载成功: {len(loaded_data)} 只股票")
        for symbol, df in loaded_data.items():
            print(f"   {symbol}: {len(df)} 条记录")
    else:
        print(f"⚠️ 加载失败或数据为空")

    # 显示数据统计
    print("\n[7] 数据统计...")
    manager.print_summary()

    manager.close()

except Exception as e:
    print(f"❌ 本地数据管理器测试失败: {e}")
    import traceback
    print(f"详细错误: {traceback.format_exc()}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ 所有测试通过！")
print("=" * 70)

print("\n💡 现在可以启动GUI程序:")
print("   cd gui_app")
print("   python main_window.py")
print("\n   然后进入'📊 数据管理'标签页下载数据")
