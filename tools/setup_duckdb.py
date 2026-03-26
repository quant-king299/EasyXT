# -*- coding: utf-8 -*-
"""
一键下载DuckDB数据库脚本

使用方法：
    python tools/setup_duckdb.py

功能：
    1. 自动检查Tushare token
    2. 下载必要的数据到DuckDB（市值数据 + 日线数据）
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
    # 尝试从 .env 文件读取
    try:
        env_paths = [
            project_root / '.env',
            Path.cwd() / '.env',
        ]
        for env_path in env_paths:
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('TUSHARE_TOKEN='):
                            token = line.split('=', 1)[1].strip()
                            break
                if token:
                    break
    except:
        pass

if not token:
    print("未找到 TUSHARE_TOKEN 环境变量或 .env 文件")
    print()
    print("请按以下步骤获取 token：")
    print("  1. 访问 https://tushare.pro")
    print("  2. 注册账号（免费）")
    print("  3. 登录后进入「用户中心」→「接口Token」")
    print("  4. 复制你的 Token")
    print()
    print("然后设置环境变量：")
    print("  Windows PowerShell:")
    print('    setx TUSHARE_TOKEN "你的Token"')
    print("  Windows CMD:")
    print('    setx TUSHARE_TOKEN "你的Token"')
    print()
    print("或者在本脚本运行时输入 token：")
    token = input("  请输入你的 Tushare Token: ").strip()

    if not token:
        print("未输入 token，退出")
        sys.exit(1)

    # 设置到环境变量
    os.environ['TUSHARE_TOKEN'] = token

print(f"Token: {token[:10]}...{token[-4:]}")
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

# 确定下载参数
cap_start_date = '20230101'
daily_start_date = '20230101'
end_date = datetime.now().strftime('%Y%m%d')

if choice == "2":
    cap_start_date = '20210101'
    daily_start_date = '20210101'
elif choice == "3":
    cap_start_date = input("  市值数据开始日期（格式：YYYYMMDD，默认20230101）: ").strip() or "20230101"
    daily_start_date = input("  日线数据开始日期（格式：YYYYMMDD，默认20230101）: ").strip() or "20230101"
    end_date = input("  结束日期（格式：YYYYMMDD，默认今天）: ").strip() or datetime.now().strftime('%Y%m%d')
elif choice not in ("1", "2", "3"):
    print("无效选项，退出")
    sys.exit(1)

mode_name = {"1": "快速模式", "2": "完整模式", "3": "自定义模式"}.get(choice, "未知模式")
print()
print(f"已选择：{mode_name}")
print(f"  市值数据范围：{cap_start_date} ~ {end_date}")
print(f"  日线数据范围：{daily_start_date} ~ {end_date}")

# ==================== 步骤3：开始下载 ====================
print()
print("【步骤3/4】开始下载")
print("-" * 70)

# --- 3a: 下载市值数据 ---
print()
print(">> 下载市值数据...")
try:
    from tools.download_market_cap_fast import download_market_cap
    result = download_market_cap(
        start_date=cap_start_date,
        end_date=end_date
    )
    print(f"市值数据下载完成，共插入 {result['total_inserted']:,} 条记录")
except Exception as e:
    print(f"市值数据下载失败: {e}")

# --- 3b: 下载日线数据 ---
print()
print(">> 下载日线行情数据...")
try:
    factor_platform_path = project_root / "101因子" / "101因子分析平台" / "src"
    if str(factor_platform_path) not in sys.path:
        sys.path.insert(0, str(factor_platform_path))

    from data_manager import LocalDataManager

    dm = LocalDataManager()

    # 获取股票列表
    print("获取A股股票列表...")
    all_stocks = dm.get_all_stocks_list(include_st=True, include_sz=True, include_kc=True)
    if all_stocks:
        stock_list = all_stocks[:100]  # 快速模式先下100只
        if choice == "2":
            stock_list = all_stocks[:500]  # 完整模式下500只
        print(f"将下载 {len(stock_list)} 只股票的日线数据")
    else:
        print("无法获取股票列表，使用默认列表")
        stock_list = ['000001.SZ', '600000.SH', '600519.SH']

    # 下载日线数据
    dm.download_and_save(
        symbols=stock_list,
        start_date=daily_start_date.replace('-', ''),
        end_date=end_date.replace('-', ''),
        symbol_type='stock'
    )
    print("日线数据下载完成")
except ImportError as e:
    print(f"日线数据下载失败（缺少依赖）: {e}")
    print("提示：日线数据下载需要 QMT/xtquant 环境，请确保 QMT 已启动")
    print("你也可以稍后通过以下方式补充日线数据：")
    print("  python run_gui.py  → 切换到'本地数据管理'标签页")
except Exception as e:
    print(f"日线数据下载失败: {e}")

# ==================== 步骤4：验证数据 ====================
print()
print("【步骤4/4】验证数据")
print("-" * 70)

try:
    import duckdb
    from tools.download_market_cap_fast import get_db_path

    db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"数据库文件不存在：{db_path}")
    else:
        con = duckdb.connect(db_path, read_only=True)

        # 检查表
        tables = con.execute("SHOW TABLES").df()
        print(f"数据库包含 {len(tables)} 个表：")
        for table in tables['name']:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  - {table}: {count:,} 条记录")

        # 检查数据范围
        print()
        print("数据范围：")

        try:
            df = con.execute("""
                SELECT
                    MIN(date) as min_date,
                    MAX(date) as max_date,
                    COUNT(DISTINCT date) as trading_days
                FROM stock_daily
            """).df()
            print(f"  日线数据：{df['min_date'].iloc[0]} ~ {df['max_date'].iloc[0]}")
            print(f"  交易日数：{df['trading_days'].iloc[0]:,} 天")
        except:
            print("  日线数据表不存在或为空")

        try:
            df = con.execute("""
                SELECT
                    MIN(date) as min_date,
                    MAX(date) as max_date,
                    COUNT(DISTINCT date) as dates
                FROM stock_market_cap
            """).df()
            print(f"  市值数据：{df['min_date'].iloc[0]} ~ {df['max_date'].iloc[0]}")
            print(f"  数据天数：{df['dates'].iloc[0]:,} 天")
        except:
            print("  市值数据表不存在或为空")

        con.close()

except Exception as e:
    print(f"验证失败: {e}")

print()
print("=" * 70)
print("数据下载完成！")
print("=" * 70)
print()
print("下一步：")
print("  1. 在回测中使用：")
print(f"     data_manager = DataManager(duckdb_path='{db_path}')")
print()
print("  2. 或者设置环境变量（后续自动检测）：")
print(f"     setx DUCKDB_PATH \"{db_path}\"")
print()
