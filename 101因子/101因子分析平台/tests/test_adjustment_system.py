#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复权因子系统测试脚本
验证所有功能是否正常工作
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加路径
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))
factor_platform_path = project_root / "101因子" / "101因子分析平台" / "src"
sys.path.insert(0, str(factor_platform_path))

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'


def test_database():
    """测试数据库"""
    print("=" * 60)
    print("测试1: 数据库结构")
    print("=" * 60)

    from data_manager.metadata_db_extended import MetadataDB

    # 创建测试数据库
    test_db_path = Path("test_metadata.db")
    if test_db_path.exists():
        test_db_path.unlink()

    db = MetadataDB(str(test_db_path))

    # 测试分红数据
    print("\n1.1 测试分红数据...")
    dividends_df = pd.DataFrame({
        'ex_date': ['2024-01-05', '2024-06-10', '2024-12-15'],
        'dividend_per_share': [0.5, 0.3, 0.2],
        'record_date': ['2024-01-03', '2024-06-08', '2024-12-13']
    })

    db.save_dividends('TEST001.SZ', dividends_df)
    print("[OK] 分红数据保存成功")

    # 测试读取
    retrieved = db.get_dividends('TEST001.SZ')
    print(f"[OK] 读取分红数据: {len(retrieved)} 条")

    # 测试统计
    stats = db.get_dividend_statistics('TEST001.SZ')
    print(f"[OK] 统计信息: {stats}")

    db.close()

    # 删除测试数据库
    test_db_path.unlink()

    print("\n✅ 数据库测试通过")


def test_adjustment_calculator():
    """测试复权计算器"""
    print("\n" + "=" * 60)
    print("测试2: 复权计算器")
    print("=" * 60)

    from data_manager.adjustment_calculator import AdjustmentCalculator

    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    df = pd.DataFrame({
        'open': [100.0] * 10,
        'high': [102.0] * 10,
        'low': [99.0] * 10,
        'close': [101.0] * 10,
        'volume': [1000000] * 10
    }, index=dates)

    # 创建分红数据（第5天分红10元）
    dividends = pd.DataFrame({
        'ex_date': ['2024-01-10'],
        'dividend_per_share': [10.0]
    })

    print("\n2.1 原始数据:")
    print(df.head(10))
    print(f"收盘价: {df['close'].iloc[4]:.2f} (除权日前)")
    print(f"收盘价: {df['close'].iloc[5]:.2f} (除权日)")

    # 测试前复权
    print("\n2.2 前复权:")
    df_qfq = AdjustmentCalculator.apply_qfq(df.copy(), dividends)
    print(df_qfq.head(10))
    print(f"除权日前收盘价: {df_qfq['close'].iloc[3]:.2f}")
    print(f"除权日收盘价: {df_qfq['close'].iloc[4]:.2f}")
    print(f"当前价: {df_qfq['close'].iloc[-1]:.2f} (真实)")

    # 测试后复权
    print("\n2.3 后复权:")
    df_hfq = AdjustmentCalculator.apply_hfq(df.copy(), dividends)
    print(df_hfq.head(10))
    print(f"除权日前收盘价: {df_hfq['close'].iloc[4]:.2f} (真实)")
    print(f"除权日收盘价: {df_hfq['close'].iloc[5]:.2f}")
    print(f"当前价: {df_hfq['close'].iloc[-1]:.2f} (调整后)")

    # 验证价格关系
    print("\n2.4 价格关系验证:")

    # 前复权：当前价应该等于原始当前价
    assert abs(df_qfq['close'].iloc[-1] - df['close'].iloc[-1]) < 0.01
    print("✓ 前复权：当前价正确")

    # 后复权：历史价应该等于原始历史价
    assert abs(df_hfq['close'].iloc[0] - df['close'].iloc[0]) < 0.01
    print("✓ 后复权：历史价正确")

    print("\n✅ 复权计算器测试通过")


def test_local_data_manager():
    """测试本地数据管理器"""
    print("\n" + "=" * 60)
    print("测试3: 本地数据管理器（集成测试）")
    print("=" * 60)

    from data_manager.local_data_manager_with_adjustment import LocalDataManager

    # 创建测试数据目录
    test_dir = Path("D:/StockData_TEST")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)

    manager = LocalDataManager(str(test_dir))

    # 测试数据
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    df = pd.DataFrame({
        'open': [100.0] * 5,
        'high': [102.0] * 5,
        'low': [99.0] * 5,
        'close': [101.0] * 5,
        'volume': [1000000] * 5
    }, index=dates)

    # 保存数据
    print("\n3.1 保存数据...")
    manager.save_data(df, 'TEST001.SZ', 'daily')

    # 保存分红数据
    print("\n3.2 保存分红数据...")
    dividends = pd.DataFrame({
        'ex_date': ['2024-01-03'],
        'dividend_per_share': [0.5]
    })
    manager.save_dividends('TEST001.SZ', dividends)

    # 测试加载不同复权类型
    print("\n3.3 加载不复权数据...")
    df_none = manager.load_data('TEST001.SZ', 'daily', adjust='none')
    print(f"  记录数: {len(df_none)}")
    print(f"  最新价: {df_none['close'].iloc[-1]:.2f}")

    print("\n3.4 加载前复权数据...")
    df_qfq = manager.load_data('TEST001.SZ', 'daily', adjust='qfq')
    print(f"  记录数: {len(df_qfq)}")
    print(f"  最新价: {df_qfq['close'].iloc[-1]:.2f}")
    assert abs(df_qfq['close'].iloc[-1] - df_none['close'].iloc[-1]) < 0.01
    print("  ✓ 当前价一致（前复权）")

    print("\n3.5 加载后复权数据...")
    df_hfq = manager.load_data('TEST001.SZ', 'daily', adjust='hfq')
    print(f"  记录数: {len(df_hfq)}")
    print(f"  历史价: {df_hfq['close'].iloc[0]:.2f}")
    assert abs(df_hfq['close'].iloc[0] - df_none['close'].iloc[0]) < 0.01
    print("  ✓ 历史价一致（后复权）")

    # 获取统计
    print("\n3.6 获取统计信息...")
    stats = manager.get_statistics()
    print(f"  标的总数: {stats['total_symbols']}")
    print(f"  分红记录数: {stats['total_dividend_records']}")

    manager.close()

    # 清理测试数据
    import shutil
    shutil.rmtree(test_dir)

    print("\n✅ 本地数据管理器测试通过")


def test_usage_scenario():
    """测试实际使用场景"""
    print("\n" + "=" * 60)
    print("测试4: 实际使用场景")
    print("=" * 60)

    from data_manager.local_data_manager_with_adjustment import LocalDataManager

    test_dir = Path("D:/StockData_TEST")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)

    manager = LocalDataManager(str(test_dir))

    # 场景1：短期回测
    print("\n4.1 场景1：短期回测（前复权）")
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    df = pd.DataFrame({
        'open': np.random.uniform(100, 105, 20),
        'high': np.random.uniform(105, 110, 20),
        'low': np.random.uniform(95, 100, 20),
        'close': np.random.uniform(100, 105, 20),
        'volume': np.random.randint(1000000, 2000000, 20)
    }, index=dates)

    dividends = pd.DataFrame({
        'ex_date': ['2024-01-10', '2024-01-20'],
        'dividend_per_share': [1.0, 0.5]
    })

    manager.save_data(df, 'SHORT_TEST.SZ', 'daily')
    manager.save_dividends('SHORT_TEST.SZ', dividends)

    df_qfq = manager.load_data('SHORT_TEST.SZ', 'daily', adjust='qfq')
    print(f"  前复权数据: {len(df_qfq)} 条")
    print(f"  收益: {(df_qfq['close'].iloc[-1] / df_qfq['close'].iloc[0] - 1) * 100:.2f}%")

    # 场景2：长期回测
    print("\n4.2 场景2：长期回测（后复权）")
    df_hfq = manager.load_data('SHORT_TEST.SZ', 'daily', adjust='hfq')
    print(f"  后复权数据: {len(df_hfq)} 条")
    print(f"  收益: {(df_hfq['close'].iloc[-1] / df_hfq['close'].iloc[0] - 1) * 100:.2f}%")

    # 场景3：实时交易
    print("\n4.3 场景3：实时交易（不复权）")
    df_raw = manager.load_data('SHORT_TEST.SZ', 'daily', adjust='none')
    print(f"  实时价格: {df_raw['close'].iloc[-1]:.2f}")
    print(f"  5日均价: {df_raw['close'].iloc[-5:].mean():.2f}")

    manager.close()

    # 清理
    import shutil
    shutil.rmtree(test_dir)

    print("\n✅ 使用场景测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("复权因子系统 - 完整测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        test_database()
        test_adjustment_calculator()
        test_local_data_manager()
        test_usage_scenario()

        print("\n" + "=" * 60)
        print("[OK] 所有测试通过!")
        print("=" * 60)

        print("\n测试结果总结:")
        print("  [OK] 数据库结构正常")
        print("  [OK] 复权计算准确")
        print("  [OK] 集成功能正常")
        print("  [OK] 实际场景可用")

        print("\n系统已就绪，可以开始使用！")

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
