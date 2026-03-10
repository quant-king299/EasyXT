# -*- coding: utf-8 -*-
"""
一键下载DuckDB数据库脚本

使用方法：
    python tools/setup_duckdb.py

功能：
    1. 自动检查Tushare token
    2. 下载必要的数据到DuckDB
    3. 验证数据完整性
    4. 提供友好的进度提示
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("EasyXT DuckDB数据库一键下载工具")
print("=" * 70)
print()

# ==================== 步骤1：检查Tushare Token ====================
print("【步骤1/4】检查Tushare Token")
print("-" * 70)

token = os.environ.get('TUSHARE_TOKEN')

if not token:
    print("❌ 未找到TUSHARE_TOKEN环境变量")
    print()
    print("请按以下步骤获取token：")
    print("  1. 访问 https://tushare.pro")
    print("  2. 注册账号（免费）")
    print("  3. 登录后进入「用户中心」→「接口Token」")
    print("  4. 复制你的Token")
    print()
    print("然后设置环境变量：")
    print("  Windows PowerShell:")
    print(f"    setx TUSHARE_TOKEN \"你的Token\"")
    print("  Windows CMD:")
    print(f"    setx TUSHARE_TOKEN \"你的Token\"")
    print()
    print("或者在本脚本运行时输入token：")
    token = input("  请输入你的Tushare Token: ").strip()

    if not token:
        print("❌ 未输入token，退出")
        sys.exit(1)

    # 设置到环境变量
    os.environ['TUSHARE_TOKEN'] = token

print(f"✅ Token: {token[:10]}...{token[-4:]}")
print()

# ==================== 步骤2：选择下载内容 ====================
print("【步骤2/4】选择要下载的数据")
print("-" * 70)
print()
print("请选择下载模式：")
print("  1. 快速模式（推荐新手）")
print("     - 下载市值数据（小市值策略必需）")
print("     - 下载近1年日线数据")
print("     - 耗时：10-20分钟")
print()
print("  2. 完整模式（推荐进阶）")
print("     - 下载市值数据")
print("     - 下载近3年日线数据")
print("     - 耗时：30-60分钟")
print()
print("  3. 自定义模式")
print("     - 手动选择要下载的数据类型和日期范围")
print()

choice = input("  请输入选项（1/2/3，默认1）: ").strip() or "1"

if choice == "1":
    # 快速模式
    print()
    print("📦 已选择：快速模式")
    print("   将下载：")
    print("   - 市值数据（2023-01-01至今）")
    print("   - 日线数据（2023-01-01至今）")

    # 导入下载脚本
    from tools.download_market_cap_fast import download_market_cap
    from tools.correct_data_download_usage import main as download_daily

    print()
    print("【步骤3/4】开始下载")
    print("-" * 70)

    # 下载市值数据
    print()
    print("📊 下载市值数据...")
    try:
        download_market_cap()
        print("✅ 市值数据下载完成")
    except Exception as e:
        print(f"❌ 市值数据下载失败: {e}")

    # 下载日线数据
    print()
    print("📈 下载日线数据...")
    try:
        download_daily()
        print("✅ 日线数据下载完成")
    except Exception as e:
        print(f"❌ 日线数据下载失败: {e}")

elif choice == "2":
    # 完整模式
    print()
    print("📦 已选择：完整模式")
    print("   将下载：")
    print("   - 市值数据（2021-01-01至今）")
    print("   - 日线数据（2021-01-01至今）")

    from tools.download_market_cap_fast import download_market_cap
    from tools.correct_data_download_usage import main as download_daily

    print()
    print("【步骤3/4】开始下载")
    print("-" * 70)

    # 下载市值数据
    print()
    print("📊 下载市值数据（2021-01-01至今）...")
    try:
        download_market_cap(start_date='20210101')
        print("✅ 市值数据下载完成")
    except Exception as e:
        print(f"❌ 市值数据下载失败: {e}")

    # 下载日线数据
    print()
    print("📈 下载日线数据（2021-01-01至今）...")
    try:
        download_daily()
        print("✅ 日线数据下载完成")
    except Exception as e:
        print(f"❌ 日线数据下载失败: {e}")

elif choice == "3":
    # 自定义模式
    print()
    print("📦 已选择：自定义模式")

    start_date = input("  请输入开始日期（格式：YYYYMMDD，默认20230101）: ").strip() or "20230101"
    end_date = input("  请输入结束日期（格式：YYYYMMDD，默认至今）: ").strip() or datetime.now().strftime("%Y%m%d")

    print()
    print(f"   将下载 {start_date} 至 {end_date} 的数据")

    from tools.download_market_cap_fast import download_market_cap
    from tools.correct_data_download_usage import main as download_daily

    print()
    print("【步骤3/4】开始下载")
    print("-" * 70)

    # 下载市值数据
    print()
    print("📊 下载市值数据...")
    try:
        download_market_cap(start_date=start_date, end_date=end_date)
        print("✅ 市值数据下载完成")
    except Exception as e:
        print(f"❌ 市值数据下载失败: {e}")

    # 下载日线数据
    print()
    print("📈 下载日线数据...")
    try:
        download_daily()
        print("✅ 日线数据下载完成")
    except Exception as e:
        print(f"❌ 日线数据下载失败: {e}")

else:
    print("❌ 无效选项，退出")
    sys.exit(1)

print()
print("【步骤4/4】验证数据")
print("-" * 70)

# 验证数据
try:
    import duckdb

    # 默认数据库路径
    db_path = 'D:/StockData/stock_data.ddb'

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在：{db_path}")
    else:
        con = duckdb.connect(db_path, read_only=True)

        # 检查表
        tables = con.execute("SHOW TABLES").df()
        print(f"✅ 数据库包含 {len(tables)} 个表：")
        for table in tables['name']:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"   - {table}: {count:,} 条记录")

        # 检查数据范围
        print()
        print("📊 数据范围：")

        query = """
            SELECT
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(DISTINCT date) as trading_days
            FROM stock_daily
        """
        try:
            df = con.execute(query).df()
            print(f"   日线数据：{df['min_date'].iloc[0]} ~ {df['max_date'].iloc[0]}")
            print(f"   交易日数：{df['trading_days'].iloc[0]:,} 天")
        except:
            print("   ⚠️  日线数据表不存在或为空")

        query = """
            SELECT
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(DISTINCT date) as dates
            FROM stock_market_cap
        """
        try:
            df = con.execute(query).df()
            print(f"   市值数据：{df['min_date'].iloc[0]} ~ {df['max_date'].iloc[0]}")
            print(f"   数据天数：{df['dates'].iloc[0]:,} 天")
        except:
            print("   ⚠️  市值数据表不存在或为空")

        con.close()

except Exception as e:
    print(f"❌ 验证失败: {e}")

print()
print("=" * 70)
print("✅ 数据下载完成！")
print("=" * 70)
print()
print("下一步：")
print("  1. 在代码中使用：")
print(f"     data_manager = DataManager(duckdb_path='{db_path}')")
print()
print("  2. 或者设置环境变量：")
print(f"     setx DUCKDB_PATH \"{db_path}\"")
print()
print("  3. 查看快速开始指南：QUICK_START.md")
print()
