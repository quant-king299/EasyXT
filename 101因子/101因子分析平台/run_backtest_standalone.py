# -*- coding: utf-8 -*-
"""
独立回测脚本
直接运行回测并输出JSON结果
"""
import sys
import json
from pathlib import Path
import io
from contextlib import redirect_stdout, redirect_stderr

# 添加easyxt_backtest到路径
backtest_path = Path(r"C:\Users\Administrator\Desktop\miniqmt扩展\easyxt_backtest")
sys.path.insert(0, str(backtest_path))

# 直接导入各个模块（不使用包导入）
import data_manager
import strategy_base
import engine
import performance

# 导入策略
sys.path.insert(0, str(backtest_path / "strategies"))
import small_cap_strategy


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
    # 从命令行参数获取配置
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
            strategy = small_cap_strategy.SmallCapStrategy(
                index_code='399101.SZ',  # 中小100指数
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

        # 只输出JSON到stdout
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
