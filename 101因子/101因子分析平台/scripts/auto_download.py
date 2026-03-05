# -*- coding: utf-8 -*-
"""
自动下载测试数据
非交互式脚本，适合定时任务
"""
import sys
from pathlib import Path

# 添加src目录到路径
project_root = Path(__file__).parents[1]
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from data_manager import LocalDataManager


def auto_download_test_data():
    """自动下载测试数据"""
    print("\n" + "="*70)
    print("自动下载测试数据")
    print("="*70)

    # 创建数据管理器
    manager = LocalDataManager()

    # 测试股票列表
    test_symbols = [
        # 大盘蓝筹
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600000.SH',  # 浦发银行
        '600036.SH',  # 招商银行
        '600519.SH',  # 贵州茅台
        '601318.SH',  # 中国平安
        '601398.SH',  # 工商银行
        '601857.SH',  # 中国石油
        # 科技股
        '000063.SZ',  # 中兴通讯
        '000725.SZ',  # 京东方A
    ]

    # 时间范围：最近2年
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')

    print(f"\n[INFO] 下载配置:")
    print(f"  股票数量: {len(test_symbols)}")
    print(f"  时间范围: {start_date} ~ {end_date}")
    print(f"  存储位置: {manager.root_dir}")
    print(f"\n开始下载...\n")

    # 下载数据
    results = manager.download_and_save(
        symbols=test_symbols,
        start_date=start_date,
        end_date=end_date,
        symbol_type='stock',
        show_progress=True
    )

    # 显示结果
    print(f"\n" + "="*70)
    print(f"下载完成！")
    print(f"="*70)
    print(f"成功: {len(results)}/{len(test_symbols)} 只股票")

    if results:
        print(f"\n数据预览:")
        for symbol, df in list(results.items())[:3]:  # 显示前3只
            print(f"\n{symbol}:")
            print(f"  记录数: {len(df)}")
            print(f"  日期范围: {df.index.min()} ~ {df.index.max()}")
            print(f"  最新收盘价: {df['close'].iloc[-1]:.2f}")

    # 数据统计
    print(f"\n数据存储统计:")
    manager.print_summary()

    manager.close()

    print(f"\n[SUCCESS] 数据下载完成！")
    print(f"数据已保存到: {manager.root_dir}")
    print(f"下次加载时将从本地读取，速度会快很多！")


if __name__ == '__main__':
    try:
        auto_download_test_data()
    except Exception as e:
        print(f"\n[ERROR] 下载失败: {e}")
        import traceback
        traceback.print_exc()
