"""
EasyXT学习实例 21 - xqshare跨平台支持（Mac/Linux）
学习目标：掌握使用xqshare远程客户端在Mac/Linux平台上使用EasyXT

适用场景：
- macOS 用户：无需安装虚拟机即可使用 EasyXT
- Linux 用户：在服务器上部署量化策略
- Windows 用户：作为备用数据源（QMT不可用时）

前置条件：
1. 安装 xqshare: pip install xqshare
2. 配置环境变量（或创建 .env 文件）：
   export XQSHARE_REMOTE_HOST="your-server-ip"
   export XQSHARE_REMOTE_PORT="18812"

贡献者：@jasonhu - 感谢贡献xqshare跨平台支持功能！
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 使用统一路径管理器
from core.path_manager import init_paths
init_paths()

import easy_xt

# ============================================================================
# 第1课：环境配置和连接
# ============================================================================

def lesson_01_environment_setup():
    """第1课：环境配置和数据服务连接"""
    print("=" * 80)
    print("第1课：xqshare 环境配置和数据服务连接")
    print("=" * 80)

    # 1. 检查环境变量
    print("\n1️⃣ 检查 xqshare 环境配置")
    print("-" * 80)

    xqshare_host = os.environ.get('XQSHARE_REMOTE_HOST')
    xqshare_port = os.environ.get('XQSHARE_REMOTE_PORT')

    if xqshare_host:
        print(f"✓ XQSHARE_REMOTE_HOST: {xqshare_host}")
        print(f"✓ XQSHARE_REMOTE_PORT: {xqshare_port or '18812'}")
    else:
        print("⚠️  未检测到 XQSHARE_REMOTE_HOST 环境变量")
        print("💡 提示：")
        print("   方法1：设置环境变量")
        print("   export XQSHARE_REMOTE_HOST='your-server-ip'")
        print("   export XQSHARE_REMOTE_PORT='18812'")
        print()
        print("   方法2：创建 .env 文件")
        print("   echo 'XQSHARE_REMOTE_HOST=your-server-ip' >> .env")
        print("   echo 'XQSHARE_REMOTE_PORT=18812' >> .env")
        print()
        return False

    # 2. 创建API实例
    print("\n2️⃣ 创建 EasyXT API 实例")
    print("-" * 80)
    api = easy_xt.get_api()
    print("✓ API实例创建成功")

    # 3. 初始化数据服务（自动检测并使用 xqshare）
    print("\n3️⃣ 初始化数据服务（自动降级）")
    print("-" * 80)
    print("数据源优先级：")
    print("  1️⃣  QMT (本地)")
    print("  2️⃣  xqshare (远程) ← Mac/Linux 自动使用")
    print("  3️⃣  TDX (通达信)")
    print("  4️⃣  Eastmoney (东方财富)")
    print()

    try:
        success = api.init_data()
        if success:
            print("✓ 数据服务初始化成功")

            # 获取当前使用的数据源
            active_source = api.data.get_active_source()
            print(f"✓ 当前使用数据源: {active_source}")

            if active_source == 'xqshare':
                print("✓ 正在使用 xqshare 远程客户端")
                print("🌍 跨平台模式已启用")

            return True
        else:
            print("✗ 数据服务初始化失败")
            return False
    except Exception as e:
        print(f"✗ 数据服务初始化异常: {e}")
        return False


# ============================================================================
# 第2课：查询日K线数据
# ============================================================================

def lesson_02_query_daily_kline():
    """第2课：查询日K线数据"""
    print("\n" + "=" * 80)
    print("第2课：查询日K线数据")
    print("=" * 80)

    api = easy_xt.get_api()

    # 1. 获取单只股票的日K数据
    print("\n1️⃣ 查询单只股票日K线")
    print("-" * 80)

    stock_code = '000001.SZ'  # 平安银行
    print(f"股票代码: {stock_code}")
    print(f"查询时间范围: 最近30个交易日")
    print()

    try:
        # 获取最近30天的日K数据
        df = api.data.get_price(
            codes=[stock_code],
            count=30,
            period='1d',  # 1d=日线, 1w=周线, 1m=分钟线
            fields=['open', 'high', 'low', 'close', 'volume', 'amount']
        )

        if df is not None and not df.empty:
            print("✓ 数据获取成功")
            print(f"数据形状: {df.shape}")
            print()
            print("最新5个交易日数据:")
            print("-" * 80)
            print(df.tail().to_string())
            print()

            # 数据统计
            print("数据统计:")
            print(f"  最新收盘价: {df['close'].iloc[-1]:.2f}")
            print(f"  期间最高价: {df['high'].max():.2f}")
            print(f"  期间最低价: {df['low'].min():.2f}")
            print(f"  平均成交量: {df['volume'].mean():,.0f}")

        else:
            print("✗ 未获取到数据")
            return False

    except Exception as e:
        print(f"✗ 获取数据失败: {e}")
        return False

    # 2. 获取多只股票的日K数据
    print("\n2️⃣ 查询多只股票日K线")
    print("-" * 80)

    stock_list = ['000001.SZ', '000002.SZ', '600000.SH']
    print(f"股票列表: {stock_list}")
    print()

    try:
        df = api.data.get_price(
            codes=stock_list,
            count=10,
            period='1d'
        )

        if df is not None and not df.empty:
            print("✓ 数据获取成功")
            print(f"数据形状: {df.shape}")
            print()
            print("各股票最新收盘价:")
            print("-" * 80)

            # 按股票分组显示最新数据
            for code in stock_list:
                stock_data = df[df['code'] == code]
                if not stock_data.empty:
                    latest = stock_data.iloc[-1]
                    print(f"{code}: {latest['close']:.2f}")

        else:
            print("✗ 未获取到数据")

    except Exception as e:
        print(f"✗ 获取数据失败: {e}")

    return True


# ============================================================================
# 第3课：查询指定日期范围的K线
# ============================================================================

def lesson_03_query_date_range():
    """第3课：查询指定日期范围的K线数据"""
    print("\n" + "=" * 80)
    print("第3课：查询指定日期范围的K线数据")
    print("=" * 80)

    api = easy_xt.get_api()

    # 查询2024年的数据
    print("\n1️⃣ 查询2024年日K线数据")
    print("-" * 80)

    stock_code = '511090.SH'  # 30年国债ETF
    start_date = '20240101'
    end_date = '20241231'

    print(f"股票代码: {stock_code}")
    print(f"查询范围: {start_date} ~ {end_date}")
    print()

    try:
        df = api.data.get_price(
            codes=[stock_code],
            start=start_date,
            end=end_date,
            period='1d'
        )

        if df is not None and not df.empty:
            print("✓ 数据获取成功")
            print(f"数据形状: {df.shape} (共 {len(df)} 个交易日)")
            print()
            print("年初和年末数据对比:")
            print("-" * 80)
            year_start = df.iloc[0]
            year_end = df.iloc[-1]

            print(f"年初 ({year_start['time']}):")
            print(f"  开盘: {year_start['open']:.3f}")
            print(f"  收盘: {year_start['close']:.3f}")
            print()
            print(f"年末 ({year_end['time']}):")
            print(f"  开盘: {year_end['open']:.3f}")
            print(f"  收盘: {year_end['close']:.3f}")
            print()

            # 计算年度收益率
            annual_return = (year_end['close'] - year_start['close']) / year_start['close'] * 100
            print(f"年度收益率: {annual_return:+.2f}%")

        else:
            print("✗ 未获取到数据")

    except Exception as e:
        print(f"✗ 获取数据失败: {e}")


# ============================================================================
# 第4课：查询账户资产
# ============================================================================

def lesson_04_query_account_assets():
    """第4课：查询账户资产信息"""
    print("\n" + "=" * 80)
    print("第4课：查询账户资产信息")
    print("=" * 80)

    # ⚠️ 注意：查询账户资产需要初始化交易服务
    print("\n⚠️  重要提示：")
    print("-" * 80)
    print("查询账户资产需要初始化交易服务，这需要：")
    print("1. 设置正确的 QMT 路径（或 xqshare 远程路径）")
    print("2. 账户已在 QMT 客户端登录")
    print("3. 账户 ID 配置正确")
    print()

    # 配置信息（请根据实际情况修改）
    QMT_PATH = os.environ.get('QMT_PATH', r'D:\国金QMT交易端模拟\userdata_mini')
    ACCOUNT_ID = os.environ.get('QMT_ACCOUNT_ID', '39020958')

    print(f"QMT 路径: {QMT_PATH}")
    print(f"账户 ID: {ACCOUNT_ID}")
    print()

    api = easy_xt.get_api()

    # 1. 初始化交易服务
    print("1️⃣ 初始化交易服务")
    print("-" * 80)

    try:
        # xqshare 模式下，路径参数会被忽略
        success = api.init_trade(QMT_PATH, 'xqshare_session')

        if success:
            print("✓ 交易服务初始化成功")

            # 检查是否使用 xqshare
            if os.environ.get('XQSHARE_REMOTE_HOST'):
                print("✓ 使用 xqshare 远程交易服务")

        else:
            print("✗ 交易服务初始化失败")
            print("💡 可能原因：")
            print("   1. QMT 客户端未启动")
            print("   2. 账户未登录")
            print("   3. 路径配置错误")
            print("   4. xqshare 服务未连接")
            return False

    except Exception as e:
        print(f"✗ 交易服务初始化异常: {e}")
        return False

    # 2. 添加交易账户
    print("\n2️⃣ 添加交易账户")
    print("-" * 80)

    try:
        success = api.trade.add_account(ACCOUNT_ID, 'STOCK')
        if success:
            print(f"✓ 账户 {ACCOUNT_ID} 添加成功")
        else:
            print(f"✗ 账户 {ACCOUNT_ID} 添加失败")
            return False
    except Exception as e:
        print(f"✗ 添加账户异常: {e}")
        return False

    # 3. 查询账户资产
    print("\n3️⃣ 查询账户资产")
    print("-" * 80)

    try:
        assets = api.trade.get_account_asset(ACCOUNT_ID)

        if assets:
            print("✓ 资产查询成功")
            print()
            print("账户资产信息:")
            print("-" * 80)

            # 解析资产信息
            total_asset = assets.get('总资产', 0)
            cash = assets.get('可用资金', 0)
            market_value = assets.get('证券市值', 0)
            frozen_cash = assets.get('冻结资金', 0)
            position_pnl = assets.get('持仓盈亏', 0)

            print(f"总资产: ¥{total_asset:,.2f}")
            print(f"可用资金: ¥{cash:,.2f}")
            print(f"证券市值: ¥{market_value:,.2f}")
            print(f"冻结资金: ¥{frozen_cash:,.2f}")
            print(f"持仓盈亏: ¥{position_pnl:,.2f}")

            # 资产配置比例
            if total_asset > 0:
                cash_ratio = cash / total_asset * 100
                stock_ratio = market_value / total_asset * 100
                print()
                print("资产配置:")
                print(f"  现金占比: {cash_ratio:.2f}%")
                print(f"  股票占比: {stock_ratio:.2f}%")

            return True

        else:
            print("✗ 未获取到资产信息")
            return False

    except Exception as e:
        print(f"✗ 查询资产失败: {e}")
        print("💡 可能原因：")
        print("   1. 账户 ID 不正确")
        print("   2. 账户未登录")
        print("   3. xqshare 连接中断")
        return False


# ============================================================================
# 第5课：查询持仓
# ============================================================================

def lesson_05_query_positions():
    """第5课：查询持仓信息"""
    print("\n" + "=" * 80)
    print("第5课：查询持仓信息")
    print("=" * 80)

    api = easy_xt.get_api()
    ACCOUNT_ID = os.environ.get('QMT_ACCOUNT_ID', '39020958')

    try:
        positions = api.trade.get_positions(ACCOUNT_ID)

        if positions is not None and not positions.empty:
            print("✓ 持仓查询成功")
            print(f"持仓数量: {len(positions)} 只股票")
            print()
            print("持仓明细:")
            print("-" * 80)
            print(positions.to_string())

            # 持仓统计
            if len(positions) > 0:
                print()
                print("持仓统计:")
                print(f"  持仓品种数: {len(positions)}")
                if '市值' in positions.columns:
                    total_market_value = positions['市值'].sum()
                    print(f"  持仓总市值: ¥{total_market_value:,.2f}")
                if '持仓盈亏' in positions.columns:
                    total_pnl = positions['持仓盈亏'].sum()
                    print(f"  总持仓盈亏: ¥{total_pnl:,.2f}")

        else:
            print("✓ 当前无持仓")

    except Exception as e:
        print(f"✗ 查询持仓失败: {e}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print(" " * 15 + "xqshare 跨平台支持学习实例")
    print(" " * 20 + "Mac/Linux 用户专用")
    print("=" * 80)
    print()
    print("感谢 @jasonhu 贡献的 xqshare 跨平台支持功能！")
    print()

    # 第1课：环境配置和连接
    if not lesson_01_environment_setup():
        print("\n⚠️  环境配置失败，请检查 xqshare 配置")
        return

    input("\n按回车键继续到第2课...")

    # 第2课：查询日K线
    if not lesson_02_query_daily_kline():
        return

    input("\n按回车键继续到第3课...")

    # 第3课：查询指定日期范围
    lesson_03_query_date_range()

    input("\n按回车键继续到第4课...")

    # 第4课：查询账户资产（需要交易服务）
    if not lesson_04_query_account_assets():
        print("\n💡 跳过第5课（需要交易服务）")
    else:
        input("\n按回车键继续到第5课...")
        # 第5课：查询持仓
        lesson_05_query_positions()

    # 总结
    print("\n" + "=" * 80)
    print("[OK] 学习完成！")
    print("=" * 80)
    print()
    print("你已掌握：")
    print("[OK] xqshare 环境配置")
    print("[OK] 数据服务连接（自动降级到 xqshare）")
    print("[OK] 查询日K线数据")
    print("[OK] 查询账户资产")
    print("[OK] 查询持仓信息")
    print()
    print("[TIPS] 进阶学习：")
    print("- 查看 02_交易基础.py 了解更多交易功能")
    print("- 查看 03_高级交易.py 了解条件单、策略交易")
    print("- 查看 strategies/ 目录中的完整策略示例")
    print()
    print("[SUCCESS] 跨平台量化交易，从此开始！")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n\n✗ 程序异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "=" * 80)
        print("程序结束")
        print("=" * 80)
        input("\n按回车键退出...")
