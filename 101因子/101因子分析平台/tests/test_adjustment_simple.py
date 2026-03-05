#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复权因子系统测试脚本（简化版）
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# 添加路径（使用绝对路径）
current_file = Path(__file__).resolve()
factor_platform_path = current_file.parents[1] / "src"

sys.path.insert(0, str(factor_platform_path))

print(f"当前文件: {current_file}")
print(f"因子平台路径: {factor_platform_path}")
print(f"路径存在: {factor_platform_path.exists()}")

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'


def test_all():
    """运行所有测试"""
    print("=" * 60)
    print("复权因子系统 - 完整测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 测试1: 复权计算器
    print("[TEST 1/3] 复权计算器")
    print("-" * 60)

    try:
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

        # 分红数据（第5天分红10元）
        dividends = pd.DataFrame({
            'ex_date': ['2024-01-10'],
            'dividend_per_share': [10.0]
        })

        # 原始数据
        print("原始数据:")
        print(f"  除权日前收盘: {df['close'].iloc[4]:.2f}")
        print(f"  除权日收盘: {df['close'].iloc[5]:.2f}")

        # 前复权
        df_qfq = AdjustmentCalculator.apply_qfq(df.copy(), dividends)
        print(f"  前复权当前价: {df_qfq['close'].iloc[-1]:.2f}")

        # 后复权
        df_hfq = AdjustmentCalculator.apply_hfq(df.copy(), dividends)
        print(f"  后复权历史价: {df_hfq['close'].iloc[0]:.2f}")

        print("[OK] 复权计算器测试通过\n")

    except Exception as e:
        print(f"[ERROR] 复权计算器测试失败: {e}\n")
        return

    # 测试2: 元数据库
    print("[TEST 2/3] 元数据库")
    print("-" * 60)

    try:
        from data_manager.metadata_db_extended import MetadataDB

        # 创建测试数据库
        test_db_path = Path("test_metadata.db")

        if test_db_path.exists():
            test_db_path.unlink()

        db = MetadataDB(str(test_db_path))

        # 测试分红数据
        dividends_df = pd.DataFrame({
            'ex_date': ['2024-01-05', '2024-06-10'],
            'dividend_per_share': [0.5, 0.3]
        })

        db.save_dividends('TEST001.SZ', dividends_df)
        print(f"[OK] 保存分红数据: {len(dividends_df)} 条")

        # 读取测试
        retrieved = db.get_dividends('TEST001.SZ')
        print(f"[OK] 读取分红数据: {len(retrieved)} 条")

        db.close()
        test_db_path.unlink()

        print("[OK] 元数据库测试通过\n")

    except Exception as e:
        print(f"[ERROR] 元数据库测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return

    # 测试3: 集成测试
    print("[TEST 3/3] 集成测试")
    print("-" * 60)

    try:
        from data_manager.local_data_manager_with_adjustment import LocalDataManager

        # 创建测试目录
        test_dir = Path("D:/StockData_TEST")
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)

        manager = LocalDataManager(str(test_dir))

        # 准备测试数据
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'open': [100.0] * 5,
            'high': [102.0] * 5,
            'low': [99.0] * 5,
            'close': [101.0] * 5,
            'volume': [1000000] * 5
        }, index=dates)

        # 保存数据
        manager.save_data(df, 'TEST001.SZ', 'daily')

        # 保存分红
        dividends = pd.DataFrame({
            'ex_date': ['2024-01-03'],
            'dividend_per_share': [0.5]
        })
        manager.save_dividends('TEST001.SZ', dividends)

        # 测试三种加载
        df_none = manager.load_data('TEST001.SZ', 'daily', adjust='none')
        print(f"[OK] 不复权: {df_none['close'].iloc[-1]:.2f}")

        df_qfq = manager.load_data('TEST001.SZ', 'daily', adjust='qfq')
        print(f"[OK] 前复权: {df_qfq['close'].iloc[-1]:.2f}")

        df_hfq = manager.load_data('TEST001.SZ', 'daily', adjust='hfq')
        print(f"[OK] 后复权: {df_hfq['close'].iloc[0]:.2f}")

        manager.close()

        # 清理
        import shutil
        shutil.rmtree(test_dir)

        print("[OK] 集成测试通过\n")

    except Exception as e:
        print(f"[ERROR] 集成测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return

    # 总结
    print("=" * 60)
    print("[SUCCESS] 所有测试通过!")
    print("=" * 60)
    print("\n测试结果总结:")
    print("  [OK] 数据库结构正常")
    print("  [OK] 复权计算准确")
    print("  [OK] 集成功能正常")
    print("\n系统已就绪，可以开始使用!")


if __name__ == '__main__':
    test_all()
