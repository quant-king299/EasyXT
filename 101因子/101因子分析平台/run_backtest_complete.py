# -*- coding: utf-8 -*-
"""
完整回测脚本 - 使用完整功能（非简化版）
直接运行回测并输出JSON结果
"""
import sys
import json
from pathlib import Path
import io

# 添加easyxt_backtest到路径
backtest_path = Path(r"C:\Users\Administrator\Desktop\miniqmt扩展\easyxt_backtest")
sys.path.insert(0, str(backtest_path))

# 直接导入各个模块（不使用包导入，避免相对导入问题）
import data_manager
import strategy_base
import engine
import performance

# 导入策略 - 直接使用完整代码而不是导入模块
from typing import List, Dict
import pandas as pd

class SmallCapStrategyComplete(strategy_base.StrategyBase):
    """
    小市值策略 - 完整版

    直接在这里实现，避免相对导入问题
    """

    def __init__(self,
                 index_code: str = '399101.SZ',
                 select_num: int = 5,
                 rebalance_freq: str = 'monthly',
                 data_manager = None):
        super().__init__(data_manager)
        self.index_code = index_code
        self.select_num = select_num
        self.rebalance_freq = rebalance_freq

    def select_stocks(self, date: str) -> List[str]:
        """选股"""
        if not self.data_manager:
            raise ValueError("需要提供data_manager")

        print(f"\n  [选股] {date}")

        # 1. 获取指数成分股
        index_cons = self.data_manager.get_index_components(self.index_code, date)

        if not index_cons:
            print(f"    [WARNING] 未获取到指数成分股")
            return []

        print(f"    指数成分股: {len(index_cons)} 只")

        # 2. 获取市值数据
        try:
            df_mv = self.data_manager.get_fundamentals(
                codes=index_cons,
                date=date,
                fields=['circ_mv']
            )

            if df_mv is None or df_mv.empty:
                print(f"    [WARNING] 未获取到市值数据")
                return []

            df_mv = df_mv.dropna(subset=['circ_mv'])

            if df_mv.empty:
                print(f"    [WARNING] 过滤后无有效市值数据")
                return []

            print(f"    有效市值数据: {len(df_mv)} 只")

        except Exception as e:
            print(f"    [ERROR] 获取市值数据失败: {e}")
            return []

        # 3. 按市值排序，选择最小的N只
        df_mv_sorted = df_mv.sort_values('circ_mv', ascending=True)
        selected = df_mv_sorted.head(self.select_num).index.tolist()

        print(f"    选中股票: {len(selected)} 只")
        for i, stock in enumerate(selected, 1):
            mv = df_mv_sorted.loc[stock, 'circ_mv']
            print(f"      {i}. {stock} - 市值: {mv:,.0f} 万元")

        return selected

    def get_target_weights(self, date: str, selected_stocks: List[str]) -> Dict[str, float]:
        """等权重配置"""
        if not selected_stocks:
            return {}

        weight = 1.0 / len(selected_stocks)
        weights = {stock: weight for stock in selected_stocks}

        print(f"  [权重] 等权重配置，每只股票 {weight:.2%}")
        return weights

    def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取调仓日期"""
        if not self.data_manager:
            raise ValueError("需要提供data_manager")

        all_dates = self.data_manager.get_trading_dates(start_date, end_date)

        if not all_dates:
            return []

        # 每月第一个交易日调仓
        rebalance_dates = []
        last_month = None

        for date in all_dates:
            month = date[:6]
            if month != last_month:
                rebalance_dates.append(date)
                last_month = month

        return rebalance_dates


class SilentOutput:
    """静默输出上下文"""
    def __enter__(self):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        return sys.stdout, sys.stderr

    def __exit__(self, *args):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


def main():
    """主函数"""
    if len(sys.argv) < 5:
        print(json.dumps({"error": "参数不足"}))
        return

    start_date = sys.argv[1]
    end_date = sys.argv[2]
    num_stocks = int(sys.argv[3])
    initial_cash = float(sys.argv[4])

    try:
        # 抑制所有输出
        with SilentOutput():
            # 初始化
            dm = data_manager.DataManager()
            strategy = SmallCapStrategyComplete(
                index_code='399101.SZ',
                select_num=num_stocks
            )
            strategy.data_manager = dm

            # 运行回测
            backtest_engine = engine.BacktestEngine(
                data_manager=dm,
                initial_cash=initial_cash
            )

            results = backtest_engine.run_backtest(strategy, start_date, end_date)

        # 输出结果（恢复输出）
        output = {
            "success": True,
            "performance": {
                "total_return": float(results.performance['total_return']),
                "annual_return": float(results.performance['annual_return']),
                "max_drawdown": float(results.performance['max_drawdown']),
                "sharpe_ratio": float(results.performance['sharpe_ratio']),
                "volatility": float(results.performance['volatility'])
            },
            "trades_count": int(len(results.trades)),
            "trading_days": int(len(results.returns))
        }

        sys.stdout.write(json.dumps(output, ensure_ascii=False))
        sys.stdout.flush()

    except Exception as e:
        import traceback
        error_output = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        sys.stdout.write(json.dumps(error_output, ensure_ascii=False))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
