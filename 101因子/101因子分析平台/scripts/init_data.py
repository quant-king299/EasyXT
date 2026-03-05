"""
数据初始化脚本
用于首次下载和初始化本地数据
"""

import sys
from pathlib import Path

# 添加src目录到路径
project_root = Path(__file__).parents[1]
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from data_manager import LocalDataManager


def init_sample_data():
    """初始化示例数据（用于测试）"""
    print("\n" + "="*70)
    print("101因子平台 - 数据初始化向导")
    print("="*70)

    print("\n请选择初始化模式：")
    print("1. 快速测试模式（10只股票，2年数据）")
    print("2. 标准模式（100只股票，5年数据）")
    print("3. 完整模式（全市场股票，10年数据）")
    print("4. 自定义模式")

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice == '1':
        symbols = [
            '000001.SZ', '000002.SZ', '000004.SZ', '000005.SZ', '000006.SZ',
            '600000.SH', '600036.SH', '600519.SH', '601318.SH', '601398.SH'
        ]
        years = 2
    elif choice == '2':
        symbols = [
            # 沪深300成分股部分（示例）
            '000001.SZ', '000002.SZ', '000063.SZ', '000069.SZ', '000100.SZ',
            '000157.SZ', '000166.SZ', '000333.SZ', '000338.SZ', '000651.SZ',
            '600000.SH', '600036.SH', '600519.SH', '600900.SH', '601318.SH',
            '601398.SH', '601857.SH', '601988.SH', '603259.SH', '688981.SH'
        ]
        years = 5
    elif choice == '3':
        print("\n⚠️  完整模式将下载全市场数据，可能需要较长时间和较大空间")
        confirm = input("确认继续? (y/n): ").strip().lower()
        if confirm != 'y':
            return

        # 这里应该从QMT获取完整列表
        print("\n提示：完整模式需要实现_get_stock_list()方法")
        print("暂时使用标准模式...")
        symbols = [
            '000001.SZ', '000002.SZ', '000004.SZ', '000005.SZ', '000006.SZ',
            '600000.SH', '600036.SH', '600519.SH', '601318.SH', '601398.SH'
        ]
        years = 10
    else:
        custom_symbols = input("请输入股票代码（用逗号分隔）: ").strip()
        symbols = [s.strip() for s in custom_symbols.split(',') if s.strip()]
        years = int(input("请输入下载数据年数: ").strip())

    # 初始化数据管理器
    manager = LocalDataManager()

    # 下载
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')

    print(f"\n开始下载 {len(symbols)} 只标的的数据...")
    print(f"时间范围: {start_date} ~ {end_date}\n")

    manager.download_and_save(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        symbol_type='stock'
    )

    # 显示摘要
    manager.print_summary()

    # 保存股票列表配置
    config_file = project_root / 'config' / 'symbols.txt'
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(symbols))

    print(f"\n✅ 数据初始化完成!")
    print(f"股票列表已保存到: {config_file}")

    manager.close()


def update_existing_data():
    """更新现有数据"""
    print("\n" + "="*70)
    print("101因子平台 - 数据更新")
    print("="*70)

    manager = LocalDataManager()

    # 获取当前数据统计
    print("\n当前数据状态:")
    manager.print_summary()

    print("\n开始增量更新...")
    manager.update_data()

    print("\n更新后数据状态:")
    manager.print_summary()

    manager.close()


def show_data_status():
    """显示数据状态"""
    print("\n" + "="*70)
    print("101因子平台 - 数据状态")
    print("="*70)

    manager = LocalDataManager()
    manager.print_summary()

    # 获取最近更新日志
    print("\n最近更新记录:")
    logs = manager.metadata.get_recent_logs(5)

    if logs:
        for log in logs:
            status_icon = "✅" if log['status'] == 'success' else "⚠️"
            print(f"{status_icon} {log['update_time']} | "
                  f"{log['operation']} | "
                  f"标的: {log['symbols_count']} | "
                  f"记录: {log['records_count']:,} | "
                  f"耗时: {log['duration_seconds']:.1f}秒")
    else:
        print("暂无更新记录")

    manager.close()


def main():
    """主菜单"""
    while True:
        print("\n" + "="*70)
        print("101因子平台 - 数据管理工具")
        print("="*70)
        print("\n请选择操作：")
        print("1. 初始化数据（首次使用）")
        print("2. 更新数据（增量更新）")
        print("3. 查看数据状态")
        print("4. 退出")

        choice = input("\n请输入选项 (1-4): ").strip()

        if choice == '1':
            init_sample_data()
        elif choice == '2':
            update_existing_data()
        elif choice == '3':
            show_data_status()
        elif choice == '4':
            print("\n再见!")
            break
        else:
            print("\n⚠️ 无效选项，请重新选择")


if __name__ == '__main__':
    main()
