# -*- coding: utf-8 -*-
"""
回测运行包装器
解决相对导入问题
"""
import sys
from pathlib import Path

# 添加easyxt_backtest到路径
backtest_path = Path(r"C:\Users\Administrator\Desktop\miniqmt扩展\easyxt_backtest")
sys.path.insert(0, str(backtest_path))

# 现在可以正常导入了
from easyxt_backtest import DataManager, SmallCapStrategy, BacktestEngine


def run_strategy_backtest(
    start_date: str,
    end_date: str,
    num_stocks: int,
    universe_size: int,
    initial_cash: float,
    progress_callback=None
):
    """
    运行小市值策略回测

    Args:
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        num_stocks: 选股数量
        universe_size: 股票池大小
        initial_cash: 初始资金
        progress_callback: 进度回调函数

    Returns:
        (results, error) - 回测结果和错误信息
    """
    try:
        if progress_callback:
            progress_callback(10, "初始化数据管理器...")

        # 初始化
        dm = DataManager()

        if progress_callback:
            progress_callback(20, "创建策略实例...")

        strategy = SmallCapStrategy(
            universe_size=universe_size,
            num_stocks=num_stocks
        )
        strategy.data_manager = dm

        if progress_callback:
            progress_callback(30, "初始化回测引擎...")

        # 运行回测
        engine = BacktestEngine(data_manager=dm, initial_cash=initial_cash)

        if progress_callback:
            progress_callback(40, "运行回测...")

        results = engine.run_backtest(strategy, start_date, end_date)

        if progress_callback:
            progress_callback(100, "✅ 回测完成！")

        return results, None

    except Exception as e:
        import traceback
        error_msg = f"回测错误: {e}\n\n{traceback.format_exc()}"
        return None, error_msg


if __name__ == "__main__":
    # 测试
    print("Testing backtest wrapper...")
    results, error = run_strategy_backtest(
        start_date="20230101",
        end_date="20231231",
        num_stocks=5,
        universe_size=500,
        initial_cash=1000000
    )

    if error:
        print(f"Error: {error}")
    else:
        print(f"Success! Total return: {results.performance['total_return'] * 100:.2f}%")
