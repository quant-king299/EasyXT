"""
本地数据管理系统使用示例
演示如何使用本地数据管理器加速数据加载
"""

import sys
from pathlib import Path

# 添加src目录到路径
project_root = Path(__file__).parents[1]
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))


def example_1_basic_usage():
    """示例1：基本使用"""
    print("\n" + "="*70)
    print("示例1：基本使用 - 下载和加载数据")
    print("="*70)

    from data_manager import LocalDataManager

    # 创建数据管理器
    manager = LocalDataManager()

    # 下载几只股票的数据（测试）
    print("\n1️⃣ 下载测试数据...")
    manager.download_and_save(
        symbols=['000001.SZ', '600000.SH'],
        start_date='2023-01-01',
        end_date='2023-12-31',
        symbol_type='stock'
    )

    # 加载数据
    print("\n2️⃣ 从本地加载数据...")
    data = manager.load_data(['000001.SZ', '600000.SH'])

    for symbol, df in data.items():
        print(f"\n{symbol}:")
        print(f"  形状: {df.shape}")
        print(f"  日期范围: {df.index.min()} ~ {df.index.max()}")
        print(f"  列: {list(df.columns)}")

    # 查看统计
    print("\n3️⃣ 数据统计:")
    manager.print_summary()

    manager.close()


def example_2_factor_calculation():
    """示例2：因子计算"""
    print("\n" + "="*70)
    print("示例2：使用本地数据计算因子")
    print("="*70)

    from factor_engine.calculator_with_local_data import create_calculator

    # 创建计算器（启用本地缓存）
    calculator = create_calculator(use_cache=True)

    # 加载数据
    print("\n📊 加载数据...")
    symbols = ['000001.SZ', '600000.SH']
    calculator.load_data(symbols, '2023-01-01', '2023-12-31')

    # 查看数据
    if not calculator.data.empty:
        print(f"\n✅ 数据加载成功:")
        print(f"  形状: {calculator.data.shape}")
        print(f"  股票: {calculator.data.index.get_level_values('symbol').unique().tolist()}")

        # 这里可以计算因子
        print("\n📈 数据已准备好，可以计算因子了！")
        print("示例：计算alpha001因子")
        # factor = calculator.calculate_single_factor(calculator.data, 'alpha001')

    # 查看本地数据状态
    print("\n📂 本地数据状态:")
    calculator.print_data_summary()

    calculator.close()


def example_3_incremental_update():
    """示例3：增量更新"""
    print("\n" + "="*70)
    print("示例3：增量更新数据")
    print("="*70)

    from data_manager import LocalDataManager

    manager = LocalDataManager()

    # 查看当前状态
    print("\n📊 当前数据状态:")
    manager.print_summary()

    # 增量更新（只下载最近几天的数据）
    print("\n🔄 执行增量更新...")
    manager.update_data(days_back=5)

    # 更新后的状态
    print("\n📊 更新后数据状态:")
    manager.print_summary()

    # 查看最近的更新日志
    print("\n📝 最近更新日志:")
    logs = manager.metadata.get_recent_logs(5)
    for log in logs:
        status_icon = "✅" if log['status'] == 'success' else "⚠️"
        print(f"{status_icon} {log['update_time']} | {log['operation']} | "
              f"标的: {log['symbols_count']} | 记录: {log['records_count']:,}")

    manager.close()


def example_4_batch_operations():
    """示例4：批量操作"""
    print("\n" + "="*70)
    print("示例4：批量数据操作")
    print("="*70)

    from data_manager import LocalDataManager

    manager = LocalDataManager()

    # 准备测试数据
    test_symbols = [
        '000001.SZ', '000002.SZ', '600000.SH',
        '600036.SH', '600519.SH'
    ]

    print(f"\n📥 批量下载 {len(test_symbols)} 只股票...")

    import time
    start = time.time()

    manager.download_and_save(
        symbols=test_symbols,
        start_date='2023-01-01',
        end_date='2023-12-31',
        symbol_type='stock'
    )

    elapsed = time.time() - start
    print(f"\n⏱️  下载耗时: {elapsed:.2f}秒")

    # 批量加载
    print("\n📤 批量加载数据...")
    start = time.time()

    data = manager.load_data(test_symbols)

    elapsed = time.time() - start
    print(f"⏱️  加载耗时: {elapsed:.2f}秒")
    print(f"📊 成功加载: {len(data)} 只股票")

    # 批量导出
    print("\n💾 批量导出为CSV...")
    manager.export_data(
        symbols=test_symbols,
        output_dir='./output',
        format='csv'
    )

    manager.close()


def example_5_data_info():
    """示例5：查询数据信息"""
    print("\n" + "="*70)
    print("示例5：查询数据信息")
    print("="*70)

    from data_manager import LocalDataManager

    manager = LocalDataManager()

    # 获取所有标的
    print("\n📋 所有可用标的:")
    all_symbols = manager.get_all_symbols()
    print(f"总数: {len(all_symbols)}")
    print(f"股票: {len([s for s in all_symbols if manager.metadata.get_data_version(s)])}")

    # 查看单个标的信息
    if all_symbols:
        symbol = all_symbols[0]
        print(f"\n📊 {symbol} 详细信息:")
        info = manager.get_data_info(symbol)
        if info:
            print(f"  文件大小: {info.get('file_size_mb', 0):.2f} MB")
            print(f"  记录数: {info.get('num_rows', 0):,}")
            print(f"  日期范围: {info.get('start_date')} ~ {info.get('end_date')}")
            print(f"  压缩格式: {info.get('compression', 'N/A')}")

    # 获取存储统计
    print("\n💾 存储统计:")
    stats = manager.get_statistics()
    print(f"  总标的: {stats.get('total_symbols', 0)}")
    print(f"  总记录: {stats.get('total_records', 0):,}")
    print(f"  总空间: {stats.get('total_size_mb', 0):.2f} MB")

    manager.close()


def example_6_performance_comparison():
    """示例6：性能对比"""
    print("\n" + "="*70)
    print("示例6：本地缓存 vs QMT直接下载 - 性能对比")
    print("="*70)

    import time

    from data_manager import LocalDataManager
    from factor_engine.calculator_with_local_data import create_calculator

    test_symbols = ['000001.SZ', '600000.SH', '000002.SZ']
    start_date = '2023-01-01'
    end_date = '2023-12-31'

    # 测试1：使用本地缓存
    print("\n1️⃣ 使用本地缓存:")
    calculator_with_cache = create_calculator(use_cache=True)

    start = time.time()
    calculator_with_cache.load_data(test_symbols, start_date, end_date)
    cache_time = time.time() - start

    print(f"⏱️  耗时: {cache_time:.2f}秒")

    calculator_with_cache.close()

    # 测试2：不使用缓存（每次都下载）
    print("\n2️⃣ 不使用缓存（每次都从QMT下载）:")
    calculator_without_cache = create_calculator(use_cache=False)

    start = time.time()
    calculator_without_cache.load_data(test_symbols, start_date, end_date)
    download_time = time.time() - start

    print(f"⏱️  耗时: {download_time:.2f}秒")

    calculator_without_cache.close()

    # 对比
    print("\n📊 性能对比:")
    print(f"  本地缓存: {cache_time:.2f}秒")
    print(f"  QMT下载: {download_time:.2f}秒")
    print(f"  加速比: {download_time/cache_time:.1f}x")
    print(f"  时间节省: {((download_time-cache_time)/download_time*100):.1f}%")


def main():
    """主菜单"""
    examples = {
        '1': ('基本使用 - 下载和加载数据', example_1_basic_usage),
        '2': ('因子计算 - 使用本地数据', example_2_factor_calculation),
        '3': ('增量更新 - 更新现有数据', example_3_incremental_update),
        '4': ('批量操作 - 批量处理数据', example_4_batch_operations),
        '5': ('数据信息 - 查询数据详情', example_5_data_info),
        '6': ('性能对比 - 本地 vs QMT', example_6_performance_comparison),
    }

    while True:
        print("\n" + "="*70)
        print("本地数据管理系统 - 使用示例")
        print("="*70)

        for key, (name, _) in examples.items():
            print(f"{key}. {name}")

        print("0. 退出")

        choice = input("\n请选择示例 (0-6): ").strip()

        if choice == '0':
            print("\n👋 再见!")
            break
        elif choice in examples:
            _, func = examples[choice]
            try:
                func()
            except Exception as e:
                print(f"\n❌ 执行示例时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\n⚠️ 无效选项，请重新选择")


if __name__ == '__main__':
    main()
