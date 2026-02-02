#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
511380.SH 网格策略回测
专门针对债券ETF的网格策略实现和参数优化
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import json

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "101因子" / "101因子分析平台" / "src"))

try:
    import backtrader as bt
    BACKTRADER_AVAILABLE = True
except ImportError:
    BACKTRADER_AVAILABLE = False
    print("[ERROR] Backtrader未安装，请先安装: pip install backtrader")

from data_manager import LocalDataManager


class GridStrategy(bt.Strategy):
    """
    网格交易策略

    核心逻辑：
    1. 在价格区间内设置多个网格线
    2. 价格每跌到一个网格线买入
    3. 价格每涨到一个网格线卖出
    4. 适合震荡行情的ETF品种
    """

    params = (
        ('grid_count', 15),           # 网格数量（增加到15以获得更多交易）
        ('price_range', 0.05),        # 价格区间比例（扩大到5%）
        ('position_size', 1000),      # 每格交易数量
        ('base_price', None),         # 基准价格（None则使用首日收盘价）
        ('enable_trailing', True),    # 是否启用动态调整（默认启用）
        ('trailing_period', 5),       # 动态调整周期（缩短到5天）
    )

    def __init__(self):
        self.order = None
        self.grid_lines = []  # 网格线价格列表
        self.grid_positions = {}  # 每个网格线的持仓状态
        self.base_price = self.params.base_price
        self.current_grid_index = -1  # 当前所在的网格索引

        # 记录交易
        self.trade_log = []
        self.equity_curve = []

        # 动态调整相关
        self.last_adjust_date = None
        self.price_high = None
        self.price_low = None

        # 性能统计
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0
        self.total_loss = 0

    def next(self):
        """每个bar调用一次"""
        # 如果第一个数据点，初始化网格
        if len(self.data) == 1:
            self._init_grid()
            return

        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)

        # 记录净值
        self.equity_curve.append({
            'date': current_date,
            'price': current_price,
            'portfolio_value': self.broker.getvalue(),
            'position': self.getposition(self.data).size
        })

        # 动态调整基准价
        if self.params.enable_trailing:
            if self.last_adjust_date is None:
                self.last_adjust_date = current_date
                self.price_high = current_price
                self.price_low = current_price
            else:
                days_since_adjust = (current_date - self.last_adjust_date).days
                if days_since_adjust >= self.params.trailing_period:
                    self._adjust_base_price(current_price)
                    self.last_adjust_date = current_date

            # 更新高低点
            self.price_high = max(self.price_high, current_price)
            self.price_low = min(self.price_low, current_price)

        # 检查是否到达网格线
        self._check_grid_triggers(current_price, current_date)

    def _init_grid(self):
        """初始化网格线"""
        if self.base_price is None:
            self.base_price = self.data.close[0]

        price_range = self.base_price * self.params.price_range
        grid_spacing = price_range / self.params.grid_count

        # 创建网格线（从下到上）
        for i in range(self.params.grid_count + 1):
            grid_price = self.base_price - (price_range / 2) + (i * grid_spacing)
            self.grid_lines.append(grid_price)
            self.grid_positions[grid_price] = 0  # 0表示该网格无持仓

        print(f"[网格初始化] 基准价: {self.base_price:.3f}, 网格数: {self.params.grid_count}")
        print(f"[网格线] {len(self.grid_lines)}条: {[f'{p:.3f}' for p in self.grid_lines[:5]]}...")

    def _check_grid_triggers(self, current_price: float, current_date):
        """检查是否触发网格交易"""
        # 找到当前价格所在的网格区间
        for i in range(len(self.grid_lines) - 1):
            lower_grid = self.grid_lines[i]
            upper_grid = self.grid_lines[i + 1]

            # 如果价格在当前网格区间内
            if lower_grid <= current_price <= upper_grid:
                # 如果是新进入的网格（从上方进入，买入）
                if self.current_grid_index < i:
                    self._execute_grid_trade(lower_grid, current_price, 'buy', current_date)
                    self.current_grid_index = i

                # 如果是新进入的网格（从下方进入，卖出）
                elif self.current_grid_index > i:
                    self._execute_grid_trade(upper_grid, current_price, 'sell', current_date)
                    self.current_grid_index = i

                break

    def _execute_grid_trade(self, trigger_price: float, current_price: float,
                          action: str, current_date):
        """执行网格交易"""
        current_pos = self.getposition(self.data).size

        if action == 'buy':
            # 买入
            if not self.order:  # 没有挂单
                size = self.params.position_size
                self.order = self.buy(size=size)
                self.trade_log.append({
                    'date': current_date,
                    'action': 'buy',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

        elif action == 'sell':
            # 卖出（需要持仓）
            if not self.order and current_pos >= self.params.position_size:
                size = self.params.position_size
                self.order = self.sell(size=size)
                self.trade_log.append({
                    'date': current_date,
                    'action': 'sell',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

    def _adjust_base_price(self, current_price: float):
        """动态调整基准价格"""
        # 使用最近的高低点重新计算基准价
        new_base = (self.price_high + self.price_low) / 2

        # 只有当变化超过10%时才调整（扩大阈值以获得更多交易）
        if abs(new_base - self.base_price) / self.base_price > 0.10:
            print(f"[动态调整] 基准价: {self.base_price:.3f} -> {new_base:.3f}")
            self.base_price = new_base

            # 重新初始化网格
            price_range = self.base_price * self.params.price_range
            grid_spacing = price_range / self.params.grid_count

            self.grid_lines = []
            self.grid_positions = {}
            for i in range(self.params.grid_count + 1):
                grid_price = self.base_price - (price_range / 2) + (i * grid_spacing)
                self.grid_lines.append(grid_price)
                self.grid_positions[grid_price] = 0

            # 重置当前网格索引
            self.current_grid_index = -1

            # 重置高低点
            self.price_high = current_price
            self.price_low = current_price

            print(f"[网格重新初始化] 新范围: {self.grid_lines[0]:.3f} ~ {self.grid_lines[-1]:.3f}")

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.total_trades += 1
                # 这里简化处理，实际应该在平仓时统计盈亏
            elif order.issell():
                pass

        self.order = None

    def get_trade_log(self) -> pd.DataFrame:
        """获取交易日志"""
        return pd.DataFrame(self.trade_log)

    def get_equity_curve(self) -> pd.DataFrame:
        """获取净值曲线"""
        return pd.DataFrame(self.equity_curve)

    def stop(self):
        """策略停止时调用"""
        final_value = self.broker.getvalue()
        # 使用 cerebro 的初始资金值
        starting_cash = 100000  # 这应该从参数传入
        total_return = (final_value - starting_cash) / starting_cash * 100
        print(f"\n{'='*60}")
        print(f"回测完成")
        print(f"初始资金: {starting_cash:,.2f}")
        print(f"最终资金: {final_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"总交易次数: {len(self.trade_log)}")
        print(f"{'='*60}\n")


class GridBacktester:
    """
    网格策略回测器

    提供完整的回测、分析和参数优化功能
    """

    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.0001):
        """
        初始化回测器

        Args:
            initial_cash: 初始资金（默认10万）
            commission: 手续费率（默认万分之一，适合ETF）
        """
        self.initial_cash = initial_cash
        self.commission = commission

    def _load_data_from_qmt(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """智能加载分钟数据：优先DuckDB，备选QMT"""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        # 尝试1: 优先从DuckDB读取（快速，离线）
        try:
            print(f"[数据获取] 尝试从DuckDB读取...")
            data_manager = LocalDataManager()
            data_dict = data_manager.load_data(
                symbols=[stock_code],
                start_date=start_date,
                end_date=end_date
            )

            if data_dict and stock_code in data_dict and not data_dict[stock_code].empty:
                df = data_dict[stock_code]
                print(f"[数据获取] ✓ 从DuckDB读取成功 ({len(df):,} 条)")
                print(f"[数据范围] {df.index[0]} ~ {df.index[-1]}")
                return df

        except Exception as e:
            print(f"[数据获取] DuckDB读取失败: {e}")

        # 尝试2: 从QMT读取（备选方案）
        try:
            from xtquant import xtdata
        except ImportError:
            raise Exception("xtquant未安装，且DuckDB无数据，无法获取数据")

        print(f"[数据获取] 从QMT获取 {stock_code} 分钟数据...")
        print(f"[数据获取] 请求日期范围: {start_date} ~ {end_date}")

        start_time_str = start_dt.strftime('%Y%m%d')
        end_time_str = end_dt.strftime('%Y%m%d')

        print(f"[数据获取] QMT下载参数: {start_time_str} ~ {end_time_str}")

        # 下载历史数据
        xtdata.download_history_data(
            stock_code=stock_code,
            period='1m',
            start_time=start_time_str,
            end_time=end_time_str
        )

        # 获取市场数据（使用count=0获取全部数据）
        data = xtdata.get_market_data(
            stock_list=[stock_code],
            period='1m',
            count=0
        )

        print(f"[数据获取] QMT返回原始数据: {len(data['time'].columns) if 'time' in data else 0} 条")

        if not data or 'time' not in data:
            raise Exception(f"无法从QMT获取{stock_code}的数据")

        # 转换数据格式
        time_df = data['time']
        timestamps = time_df.columns.tolist()

        records = []
        seen_timestamps = set()

        for idx, ts in enumerate(timestamps):
            try:
                dt = pd.to_datetime(ts)

                # 去重
                if dt in seen_timestamps:
                    continue
                seen_timestamps.add(dt)

                # 过滤日期范围
                if start_dt <= dt <= end_dt:
                    records.append({
                        'datetime': dt,
                        'open': float(data['open'].iloc[0, idx]),
                        'high': float(data['high'].iloc[0, idx]),
                        'low': float(data['low'].iloc[0, idx]),
                        'close': float(data['close'].iloc[0, idx]),
                        'volume': float(data['volume'].iloc[0, idx]),
                        'amount': float(data['amount'].iloc[0, idx])
                    })
            except:
                continue

        df = pd.DataFrame(records)

        if df.empty:
            raise Exception(f"没有{start_date}到{end_date}的数据")

        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)

        # 删除重复索引
        df = df[~df.index.duplicated(keep='first')]

        print(f"[数据获取] ✓ 从QMT获取成功 ({len(df):,} 条)")
        print(f"[数据范围] {df.index[0]} ~ {df.index[-1]}")
        print(f"[价格范围] {df['close'].min():.3f} ~ {df['close'].max():.3f}")

        # 尝试自动保存到DuckDB（下次更快）
        try:
            print(f"[数据保存] 尝试保存到DuckDB...")
            # 注意：如果数据库被锁定会跳过
            data_manager.save_data(stock_code, df, '1m')
            print(f"[数据保存] ✓ 已保存到DuckDB")
        except Exception as e:
            print(f"[数据保存] 跳过（可能数据库被占用）")

        return df

    def _calculate_win_rate(self, trade_log: pd.DataFrame):
        """从交易日志计算真实的胜率"""
        if trade_log.empty:
            return 0, 0, 0.0

        # 配对买入和卖出，计算每对交易的盈亏
        buy_trades = trade_log[trade_log['action'] == 'buy'].copy()
        sell_trades = trade_log[trade_log['action'] == 'sell'].copy()

        if buy_trades.empty or sell_trades.empty:
            return 0, 0, 0.0

        # 按日期排序
        buy_trades = buy_trades.sort_values('date').reset_index(drop=True)
        sell_trades = sell_trades.sort_values('date').reset_index(drop=True)

        # 简单的FIFO配对：第一个买入配第一个卖出
        pairs = min(len(buy_trades), len(sell_trades))
        won_count = 0
        lost_count = 0

        for i in range(pairs):
            buy_price = buy_trades.iloc[i]['price']
            sell_price = sell_trades.iloc[i]['price']

            # 卖出价 > 买入价 = 盈利
            if sell_price > buy_price:
                won_count += 1
            else:
                lost_count += 1

        total_pairs = won_count + lost_count
        win_rate = won_count / total_pairs if total_pairs > 0 else 0.0

        print(f"[胜率统计] 总交易对: {total_pairs}, 盈利: {won_count}, 亏损: {lost_count}, 胜率: {win_rate*100:.1f}%")

        return won_count, lost_count, win_rate

    def run_backtest(self,
                    stock_code: str,
                    start_date: str,
                    end_date: str,
                    grid_count: int = 15,
                    price_range: float = 0.05,
                    position_size: int = 1000,
                    base_price: float = None,
                    enable_trailing: bool = True,
                    data_freq: str = 'minutely') -> Dict[str, Any]:
        """
        运行单次回测

        Args:
            stock_code: 股票代码（如511380.SH）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            grid_count: 网格数量
            price_range: 价格区间比例
            position_size: 每格交易数量
            base_price: 基准价格（None则使用首日收盘价）
            enable_trailing: 是否启用动态调整
            data_freq: 数据频率（daily/minutely）
        """
        if not BACKTRADER_AVAILABLE:
            raise Exception("Backtrader未安装")

        # 获取数据（优先使用QMT分钟数据）
        stock_data = self._load_data_from_qmt(stock_code, start_date, end_date)

        if stock_data.empty:
            raise Exception(f"无法获取{stock_code}的数据")

        # 创建回测引擎
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=self.commission)

        # 添加数据
        data_feed = bt.feeds.PandasData(dataname=stock_data)
        cerebro.adddata(data_feed)

        # 添加策略
        cerebro.addstrategy(
            GridStrategy,
            grid_count=grid_count,
            price_range=price_range,
            position_size=position_size,
            base_price=base_price,
            enable_trailing=enable_trailing
        )

        # 添加分析器
        cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
        cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
        cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')

        # 运行回测
        print(f"\n{'='*60}")
        print(f"开始回测: {stock_code}")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_cash:,.2f}")
        print(f"网格参数: 数量={grid_count}, 区间={price_range*100:.1f}%, 每格={position_size}股")
        print(f"{'='*60}\n")

        results = cerebro.run()
        strategy = results[0]

        # 获取分析结果
        sharpe = results[0].analyzers.sharpe.get_analysis()
        drawdown = results[0].analyzers.drawdown.get_analysis()
        returns = results[0].analyzers.returns.get_analysis()
        trades = results[0].analyzers.trades.get_analysis()

        # 获取交易日志（实际订单数量）
        trade_log = strategy.get_trade_log()
        actual_trade_count = len(trade_log)

        # 计算真实的胜率（从交易日志中配对买卖）
        won_count, lost_count, win_rate = self._calculate_win_rate(trade_log)

        # 提取关键指标
        metrics = {
            'initial_cash': self.initial_cash,
            'final_value': cerebro.broker.getvalue(),
            'total_return': (cerebro.broker.getvalue() - self.initial_cash) / self.initial_cash,
            'sharpe_ratio': sharpe.get('sharperatio', 0) if 'sharperatio' in sharpe else None,
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) if drawdown else 0,
            'max_drawdown_len': drawdown.get('max', {}).get('len', 0) if drawdown else 0,
            'total_trades': actual_trade_count,  # 实际订单数量
            'won_trades': won_count,  # 盈利交易对数
            'lost_trades': lost_count,  # 亏损交易对数
            'win_rate': win_rate,  # 胜率
        }

        return {
            'metrics': metrics,
            'trade_log': strategy.get_trade_log(),
            'equity_curve': strategy.get_equity_curve(),
            'params': {
                'grid_count': grid_count,
                'price_range': price_range,
                'position_size': position_size,
                'base_price': base_price,
                'enable_trailing': enable_trailing
            }
        }


class GridParameterOptimizer:
    """
    网格策略参数优化器

    使用网格搜索或遗传算法优化策略参数
    """

    def __init__(self, backtester: GridBacktester):
        self.backtester = backtester

    def grid_search(self,
                   stock_code: str,
                   start_date: str,
                   end_date: str,
                   param_grid: Dict[str, List],
                   optimization_metric: str = 'total_return') -> pd.DataFrame:
        """
        网格搜索参数优化

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            param_grid: 参数网格
                {
                    'grid_count': [5, 10, 15, 20],
                    'price_range': [0.01, 0.02, 0.03, 0.05],
                    'position_size': [500, 1000, 2000]
                }
            optimization_metric: 优化目标指标

        Returns:
            优化结果DataFrame
        """
        results = []
        total_combinations = 1
        for param_values in param_grid.values():
            total_combinations *= len(param_values)

        print(f"\n{'='*60}")
        print(f"参数优化开始")
        print(f"总参数组合数: {total_combinations}")
        print(f"优化目标: {optimization_metric}")
        print(f"{'='*60}\n")

        count = 0
        # 生成所有参数组合
        import itertools
        keys = list(param_grid.keys())
        values = list(param_grid.values())

        for combination in itertools.product(*values):
            params = dict(zip(keys, combination))
            count += 1

            try:
                print(f"[{count}/{total_combinations}] 测试参数: {params}")

                result = self.backtester.run_backtest(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    **params
                )

                results.append({
                    **params,
                    **result['metrics']
                })

            except Exception as e:
                print(f"  ✗ 失败: {e}")
                continue

        # 转换为DataFrame并排序
        results_df = pd.DataFrame(results)

        # 计算综合评分
        results_df['score'] = (
            results_df['total_return'] * 0.4 +           # 收益率权重40%
            results_df['sharpe_ratio'].fillna(0) * 0.3 +  # 夏普比率权重30%
            (10 - results_df['max_drawdown']) * 0.2 +    # 回撤越小越好（权重20%）
            results_df['win_rate'] * 100 * 0.1           # 胜率权重10%
        )

        # 按优化指标排序（降序）
        results_df = results_df.sort_values(by=optimization_metric, ascending=False)

        print(f"\n{'='*60}")
        print(f"优化完成！最佳参数:")
        best_params = results_df.iloc[0]
        print(f"收益率: {best_params['total_return']*100:.2f}%")
        print(f"夏普比率: {best_params['sharpe_ratio']:.2f}")
        print(f"最大回撤: {best_params['max_drawdown']:.2f}%")
        print(f"参数: {dict(results_df[keys].iloc[0])}")
        print(f"{'='*60}\n")

        return results_df


# 导入必要的模块
try:
    import backtrader.analyzers as btanalyzers
except:
    pass


if __name__ == "__main__":
    # 示例：运行511380.SH的回测
    backtester = GridBacktester(initial_cash=100000, commission=0.0001)

    result = backtester.run_backtest(
        stock_code='511380.SH',
        start_date='2024-01-01',
        end_date='2024-12-31',
        grid_count=10,
        price_range=0.02,
        position_size=1000,
        enable_trailing=False
    )

    print("\n回测结果:")
    print(f"总收益率: {result['metrics']['total_return']*100:.2f}%")
    sharpe = result['metrics'].get('sharpe_ratio')
    print(f"夏普比率: {sharpe:.2f}" if sharpe is not None else "夏普比率: N/A")
    print(f"最大回撤: {result['metrics']['max_drawdown']:.2f}%")
    print(f"交易次数: {result['metrics']['total_trades']}")
    print(f"盈利交易: {result['metrics'].get('won_trades', 0)}")
    print(f"亏损交易: {result['metrics'].get('lost_trades', 0)}")
    print(f"胜率: {result['metrics'].get('win_rate', 0)*100:.2f}%")
