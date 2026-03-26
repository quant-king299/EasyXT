"""
下载指定股票的多个周期历史数据

功能：
1. 下载指定股票的所有周期历史数据
2. 支持自定义时间范围
3. 显示下载进度和结果
4. 验证下载的数据

使用方法：
1. 确保QMT客户端已启动
2. 运行脚本：python tools/download_stock_periods.py
3. 按提示输入股票代码和时间范围

作者：EasyXT团队
日期：2026-03-26
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 尝试导入xtquant
try:
    from xtquant import xtdata
    print("[OK] xtquant已安装")
except ImportError:
    print("[ERROR] xtquant未安装，请先安装miniQMT")
    sys.exit(1)


def check_qmt_connection():
    """检查QMT连接状态"""
    print("\n[检查] QMT连接状态...")
    try:
        client = xtdata.get_client()
        if client and client.is_connected():
            print("[OK] QMT服务已启动并连接")
            return True
        else:
            print("[ERROR] QMT服务未启动")
            print("\n解决方案：")
            print("  1. 启动QMT客户端（XtQuant.exe）")
            print("  2. 等待QMT完全启动")
            print("  3. 重新运行此脚本")
            return False
    except Exception as e:
        print(f"[ERROR] 无法连接QMT: {e}")
        return False


def download_period_data(stock_code, period, start_date, end_date):
    """
    下载指定周期的数据

    Args:
        stock_code: 股票代码
        period: 周期 (1m, 5m, 15m, 30m, 1h, 1d)
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)

    Returns:
        bool: 下载是否成功
    """
    try:
        print(f"  下载 {stock_code} {period} 数据 ({start_date} ~ {end_date})...", end='')

        # 下载历史数据
        xtdata.download_history_data2(
            stock_list=[stock_code],
            period=period,
            start_time=start_date,
            end_time=end_date
        )

        print(" ✓")

        # 验证数据
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=[stock_code],
            period=period,
            count=1
        )

        if data and stock_code in data:
            df = data[stock_code]
            if df is not None and not df.empty:
                return True

        return False

    except Exception as e:
        print(f" ✗ 错误: {e}")
        return False


def verify_period_data(stock_code, period):
    """验证某个周期的数据"""
    try:
        data = xtdata.get_market_data_ex(
            field_list=['close', 'volume'],
            stock_list=[stock_code],
            period=period,
            count=100
        )

        if data and stock_code in data:
            df = data[stock_code]
            if df is not None and not df.empty:
                return True, len(df)
        return False, 0

    except Exception as e:
        return False, 0


def download_all_periods(stock_code, start_date=None, end_date=None):
    """
    下载所有周期的数据

    Args:
        stock_code: 股票代码
        start_date: 开始日期 (YYYYMMDD)，默认为3个月前
        end_date: 结束日期 (YYYYMMDD)，默认为今天
    """
    print("\n" + "=" * 70)
    print("多周期历史数据下载工具")
    print("=" * 70)

    # 设置默认时间范围
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    if start_date is None:
        # 默认下载最近3个月的数据
        start_dt = datetime.now() - timedelta(days=90)
        start_date = start_dt.strftime('%Y%m%d')

    print(f"\n股票代码: {stock_code}")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"下载周期: 1m, 5m, 15m, 30m, 1h, 1d")

    # 定义要下载的周期
    periods = [
        ('1m', '1分钟'),
        ('5m', '5分钟'),
        ('15m', '15分钟'),
        ('30m', '30分钟'),
        ('1h', '1小时'),
        ('1d', '日线')
    ]

    # 统计结果
    success_count = 0
    fail_count = 0
    results = {}

    print("\n[开始下载]")
    print("-" * 70)

    # 逐个周期下载
    for period_code, period_name in periods:
        success = download_period_data(stock_code, period_code, start_date, end_date)
        results[period_code] = success

        if success:
            success_count += 1
        else:
            fail_count += 1

    print("-" * 70)

    # 显示下载结果
    print("\n[下载结果]")
    print("-" * 70)
    for period_code, period_name in periods:
        status = "✓ 成功" if results[period_code] else "✗ 失败"
        print(f"  {period_name:8} ({period_code}): {status}")

    print("-" * 70)
    print(f"总计: {success_count} 个周期成功, {fail_count} 个周期失败")

    # 验证下载的数据
    print("\n[验证数据]")
    print("-" * 70)

    for period_code, period_name in periods:
        has_data, count = verify_period_data(stock_code, period_code)
        if has_data:
            print(f"  {period_name:8} ({period_code}): ✓ 有数据 ({count} 条)")
        else:
            print(f"  {period_name:8} ({period_code}): ✗ 无数据")

    print("-" * 70)

    # 提示
    if fail_count > 0:
        print("\n[提示]")
        print("部分周期下载失败，可能的原因：")
        print("  1. 网络连接问题")
        print("  2. QMT服务未完全启动")
        print("  3. 时间范围过大导致超时")
        print("\n建议：")
        print("  - 缩短时间范围（如只下载最近1个月）")
        print("  - 检查网络连接")
        print("  - 重启QMT客户端后重试")


def interactive_mode():
    """交互模式"""
    print("\n" + "=" * 70)
    print("多周期历史数据下载工具 - 交互模式")
    print("=" * 70)

    # 输入股票代码
    stock_code = input("\n请输入股票代码 (默认: 000001.SZ): ").strip()
    if not stock_code:
        stock_code = '000001.SZ'

    # 输入开始日期
    start_date = input("请输入开始日期 (YYYYMMDD, 默认: 3个月前): ").strip()
    if not start_date:
        start_dt = datetime.now() - timedelta(days=90)
        start_date = start_dt.strftime('%Y%m%d')

    # 输入结束日期
    end_date = input("请输入结束日期 (YYYYMMDD, 默认: 今天): ").strip()
    if not end_date:
        end_date = datetime.now().strftime('%Y%m%d')

    # 确认
    print(f"\n配置确认：")
    print(f"  股票代码: {stock_code}")
    print(f"  开始日期: {start_date}")
    print(f"  结束日期: {end_date}")
    print(f"  下载周期: 1m, 5m, 15m, 30m, 1h, 1d")

    confirm = input("\n确认下载? (y/n, 默认: y): ").strip().lower()
    if confirm and confirm != 'y':
        print("已取消")
        return

    # 开始下载
    download_all_periods(stock_code, start_date, end_date)


def main():
    """主函数"""
    # 检查QMT连接
    if not check_qmt_connection():
        return

    # 检查命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        stock_code = sys.argv[1]
        start_date = sys.argv[2] if len(sys.argv) > 2 else None
        end_date = sys.argv[3] if len(sys.argv) > 3 else None
        download_all_periods(stock_code, start_date, end_date)
    else:
        # 交互模式
        interactive_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断下载")
    except Exception as e:
        print(f"\n[ERROR] 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
