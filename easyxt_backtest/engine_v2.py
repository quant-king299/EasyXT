# -*- coding: utf-8 -*-
"""
基于 Backtrader 的回测引擎 v2（完全修复版）

保留 easyxt_backtest 的简洁API，底层使用成熟的 Backtrader 框架
修复了所有已知的除零错误和数据问题
"""
import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import warnings

# 导入原有的数据管理器
from easyxt_backtest.data_manager import DataManager
from easyxt_backtest.strategy_base import StrategyBase


@dataclass
class BacktestResult:
    """回测结果（保持与原接口兼容）"""
    trades: pd.DataFrame  # 所有交易记录
    portfolio_history: pd.DataFrame  # 每日持仓历史
    returns: pd.Series  # 每日收益率
    performance: dict  # 性能指标

    def print_summary(self):
        """打印回测结果摘要"""
        print("\n" + "="*70)
        print("回测结果摘要")
        print("="*70)

        perf = self.performance
        print(f"\n【收益指标】")
        print(f"  总收益率:     {perf.get('total_return', 0):.2%}")
        print(f"  年化收益率:   {perf.get('annual_return', 0):.2%}")
        print(f"  初始资金:     {perf.get('initial_cash', 0):,.2f} 元")
        print(f"  最终资金:     {perf.get('final_value', 0):,.2f} 元")

        print(f"\n【风险指标】")
        print(f"  最大回撤:     {perf.get('max_drawdown', 0):.2%}")
        print(f"  波动率:       {perf.get('volatility', 0):.2%}")
        print(f"  夏普比率:     {perf.get('sharpe_ratio', 0):.2f}")

        print(f"\n【交易统计】")
        print(f"  总交易次数:   {len(self.trades)}")
        print(f"  交易天数:     {len(self.portfolio_history)}")

        print("\n" + "="*70)


class _BacktraderStrategyAdapter(bt.Strategy):
    """
    Backtrader策略适配器（完全修复版）

    将 easyxt_backtest 的选股策略转换为 Backtrader 策略
    所有可能的除零和数据问题都已修复
    """

    params = (
        ('user_strategy', None),  # 用户定义的 StrategyBase 实例
        ('data_manager', None),   # 数据管理器
        ('rebalance_dates', []),  # 调仓日期列表
        ('rebalance_dates_set', set()),  # 调仓日期集合（快速查找）
        ('trading_dates', []),    # 所有交易日列表
    )

    def __init__(self):
        self.user_strategy = self.params.user_strategy
        self.data_manager = self.params.data_manager
        self.rebalance_dates = self.params.rebalance_dates
        self.rebalance_dates_set = self.params.rebalance_dates_set
        self.trading_dates = self.params.trading_dates

        # 记录交易历史（格式：date, symbol, direction, volume, price, amount）
        self.trade_log = []
        self.portfolio_values = []

        # 记录已经调仓过的日期
        self._rebalanced_dates = set()

    def next(self):
        """每个bar调用一次"""
        # ✅ 保护：确保有足够的数据
        try:
            if len(self.data0) < 1:  # 使用第一个数据源
                return
        except:
            return

        # ✅ 保护：安全获取日期
        current_date_str = None
        try:
            current_date = self.data.datetime.date(0)
            # ✅ 验证日期是否合理（不是1970年这种默认日期）
            if current_date.year >= 2000 and current_date.year <= 2100:
                current_date_str = current_date.strftime('%Y%m%d')
        except:
            pass

        # 如果日期无效，跳过此次记录
        if not current_date_str:
            return

        # 记录每日净值
        try:
            total_value = self.broker.getvalue()
            cash = self.broker.getcash()

            # ✅ 保护：检查总资产是否有效
            if total_value is not None and total_value > 0 and not np.isnan(total_value) and not np.isinf(total_value):
                self.portfolio_values.append({
                    'date': current_date_str,
                    'value': float(total_value),
                    'cash': float(cash),
                    'position_count': len(self.positions)
                })
        except Exception as e:
            print(f"    [WARNING] 记录净值失败: {e}")
            return

        # ✅ 检查是否需要调仓（使用交易日匹配）
        should_rebalance = False
        matched_rebalance_date = None

        # 方案1: 当前日期本身就是调仓日
        if current_date_str in self.rebalance_dates_set:
            should_rebalance = True
            matched_rebalance_date = current_date_str
        else:
            # 方案2: 当前日期是某个调仓日之后的第一个交易日
            # 例如：调仓日是20240101（非交易日），当前是20240102（交易日）→ 需要调仓
            for rebalance_date in self.rebalance_dates:
                if rebalance_date not in self._rebalanced_dates:  # 还没调仓过
                    if current_date_str >= rebalance_date:
                        should_rebalance = True
                        matched_rebalance_date = rebalance_date
                        break

        # 执行调仓
        if should_rebalance and matched_rebalance_date not in self._rebalanced_dates:
            try:
                self._rebalance(matched_rebalance_date, current_date_str)
                self._rebalanced_dates.add(matched_rebalance_date)
            except Exception as e:
                print(f"  [ERROR] 调仓失败: {e}")
                import traceback
                traceback.print_exc()

        # 🔍 调试：每20个bar显示一次进度
        try:
            if len(self.portfolio_values) % 20 == 0:
                rebalance_count = len(self._rebalanced_dates)
                total_rebalance = len(self.rebalance_dates)
                print(f"  [进度] 日期: {current_date_str}, 已调仓: {rebalance_count}/{total_rebalance}")
        except:
            pass

    def _rebalance(self, rebalance_date_str: str, actual_date_str: str = None):
        """执行调仓

        Args:
            rebalance_date_str: 计划调仓日期（例如：20240101）
            actual_date_str: 实际执行日期（例如：20240102，如果调仓日不是交易日）
        """
        if actual_date_str is None:
            actual_date_str = rebalance_date_str

        date_display = f"{rebalance_date_str}" if rebalance_date_str == actual_date_str else f"{rebalance_date_str} (实际: {actual_date_str})"

        print(f"\n{'='*70}")
        print(f"[{date_display}] 🔔 触发调仓！")
        print(f"{'='*70}")

        # 获取当前总资产
        try:
            total_value = self.broker.getvalue()
        except:
            print(f"  [ERROR] 无法获取总资产")
            return

        # ✅ 保护：检查总资产是否有效
        if total_value is None or total_value <= 0 or np.isnan(total_value) or np.isinf(total_value):
            print(f"  [ERROR] 总资产无效 ({total_value})，跳过调仓")
            return

        print(f"  当前总资产: {total_value:,.2f}")

        # 1. 选股
        try:
            print(f"  🔍 调用 select_stocks('{rebalance_date_str}')...")
            selected_stocks = self.user_strategy.select_stocks(rebalance_date_str)
            print(f"  ✅ 选中股票: {len(selected_stocks)} 只")
            if selected_stocks:
                print(f"     股票列表: {', '.join(selected_stocks[:5])}{'...' if len(selected_stocks) > 5 else ''}")
        except Exception as e:
            print(f"  ❌ [ERROR] 选股失败: {e}")
            import traceback
            traceback.print_exc()
            return

        if not selected_stocks:
            print("  ⚠️  [WARNING] 未选中任何股票，清仓")
            self._close_all_positions()
            return

        # 2. 获取目标权重
        try:
            print(f"  🔍 调用 get_target_weights('{rebalance_date_str}', {len(selected_stocks)}只)...")
            target_weights = self.user_strategy.get_target_weights(rebalance_date_str, selected_stocks)
            print(f"  ✅ 目标权重: {len(target_weights)} 只")
            if target_weights:
                for symbol, weight in list(target_weights.items())[:3]:
                    print(f"     {symbol}: {weight:.2%}")
                if len(target_weights) > 3:
                    print(f"     ... 共 {len(target_weights)} 只")
        except Exception as e:
            print(f"  ❌ [ERROR] 获取目标权重失败: {e}")
            import traceback
            traceback.print_exc()
            return

        if not target_weights:
            print("  ⚠️  [WARNING] 目标权重为空，清仓")
            self._close_all_positions()
            return

        # 3. 执行调仓
        self._execute_rebalance(target_weights, rebalance_date_str, actual_date_str, total_value)

    def _execute_rebalance(self, target_weights: Dict[str, float], rebalance_date_str: str, actual_date_str: str, total_value: float):
        """执行调仓逻辑（完全修复版）"""
        print(f"\n  📊 当前总资产: {total_value:,.2f}")

        # ✅ 保护：验证权重总和
        weight_sum = sum(target_weights.values())
        if weight_sum <= 0 or weight_sum > 1.5:  # 允许1.5的误差范围
            print(f"  ❌ [ERROR] 权重总和异常 ({weight_sum:.2f})，跳过调仓")
            return

        print(f"  ✅ 权重总和: {weight_sum:.2%}")

        # 显示当前持仓
        print(f"\n  📈 当前持仓:")
        has_positions = False
        for data in self.datas:
            try:
                position = self.getposition(data)
                if position.size > 0:
                    has_positions = True
                    try:
                        price = float(data.close[0])
                        value = position.size * price
                        print(f"     {data._name}: {position.size}股 × {price:.2f} = {value:,.2f}")
                    except:
                        print(f"     {data._name}: {position.size}股")
            except:
                pass
        if not has_positions:
            print(f"     (空仓)")

        # 第一遍：卖出不在目标中的股票
        print(f"\n  🔻 第一步: 卖出非目标股票")
        sell_count = 0
        for data in self.datas:
            try:
                if data._name in target_weights:
                    continue

                position = self.getposition(data)
                if position.size > 0:
                    # 获取卖出价格
                    try:
                        sell_price = float(data.close[0])
                    except:
                        sell_price = 0.0

                    # 执行卖出
                    self.order = self.sell(data=data, size=position.size)
                    print(f"     [SELL] {data._name} {position.size}股 @ {sell_price:.2f}")

                    # 记录交易
                    self.trade_log.append({
                        'date': actual_date_str,
                        'symbol': data._name,
                        'direction': 'sell',
                        'volume': int(position.size),
                        'price': float(sell_price),
                        'amount': float(position.size * sell_price)
                    })
                    sell_count += 1
            except Exception as e:
                print(f"     [WARNING] 卖出 {data._name} 失败: {e}")
                continue

        if sell_count == 0:
            print(f"     (无需卖出)")

        # 第二遍：买入/调整目标股票
        print(f"\n  🔺 第二步: 买入/调整目标股票")
        buy_count = 0
        ok_count = 0

        for symbol, weight in target_weights.items():
            try:
                # ✅ 保护：检查权重
                if weight <= 0 or weight > 1:
                    print(f"     [SKIP] {symbol} 权重无效 ({weight})")
                    continue

                target_value = total_value * weight

                # 找到对应的数据源
                target_data = None
                for data in self.datas:
                    if data._name == symbol:
                        target_data = data
                        break

                if target_data is None:
                    print(f"     [SKIP] {symbol} 数据源不存在")
                    continue

                # ✅ 保护：检查数据源是否有数据
                if len(target_data) < 1:
                    print(f"     [SKIP] {symbol} 数据不足（长度0）")
                    continue

                # 获取当前持仓
                current_position = self.getposition(target_data)
                current_size = current_position.size

                # ✅ 保护：安全获取价格
                try:
                    current_price = float(target_data.close[0])
                except:
                    print(f"     [SKIP] {symbol} 无法获取价格")
                    continue

                # ✅ 保护：检查价格是否有效
                if current_price <= 0 or np.isnan(current_price) or np.isinf(current_price):
                    print(f"     [SKIP] {symbol} 价格无效 ({current_price})")
                    continue

                # 计算目标持仓数量
                try:
                    target_size = int(target_value / current_price / 100) * 100  # 整手
                except ZeroDivisionError:
                    print(f"     [SKIP] {symbol} 价格为0，无法计算持仓数量")
                    continue

                # 调整持仓
                diff = target_size - current_size

                if diff > 0:
                    # 需要买入
                    self.order = self.buy(data=target_data, size=diff)
                    cost = diff * current_price
                    print(f"     [BUY] {symbol} {diff}股 @ {current_price:.2f} (成本: {cost:,.2f})")

                    # 记录交易
                    self.trade_log.append({
                        'date': actual_date_str,
                        'symbol': symbol,
                        'direction': 'buy',
                        'volume': int(diff),
                        'price': float(current_price),
                        'amount': float(cost)
                    })
                    buy_count += 1
                elif diff < 0:
                    # 需要卖出
                    self.order = self.sell(data=target_data, size=abs(diff))
                    sell_amount = abs(diff) * current_price
                    print(f"     [SELL] {symbol} {abs(diff)}股 @ {current_price:.2f}")

                    # 记录交易
                    self.trade_log.append({
                        'date': actual_date_str,
                        'symbol': symbol,
                        'direction': 'sell',
                        'volume': int(abs(diff)),
                        'price': float(current_price),
                        'amount': float(sell_amount)
                    })
                    buy_count += 1
                else:
                    print(f"     [OK] {symbol} 持仓已达标 ({current_size}股, 价值: {current_size * current_price:,.2f})")
                    ok_count += 1

            except Exception as e:
                print(f"     [ERROR] 处理 {symbol} 失败: {e}")
                import traceback
                traceback.print_exc()
                continue

        if buy_count == 0 and ok_count == 0:
            print(f"     (无任何交易)")

        print(f"\n  📊 调仓完成: 买入/调整 {buy_count} 只, 保持 {ok_count} 只")
        print(f"{'='*70}\n")

    def _close_all_positions(self):
        """清空所有持仓"""
        for data in self.datas:
            try:
                position = self.getposition(data)
                if position.size > 0:
                    self.order = self.sell(data=data, size=position.size)
            except Exception as e:
                print(f"    [WARNING] 清仓 {data._name} 失败: {e}")
                continue

    def notify_trade(self, trade):
        """交易完成通知（已禁用，交易记录在买卖时直接记录）"""
        # 我们已经在 _execute_rebalance 中记录了所有交易
        # 这里不再重复记录，避免格式冲突
        pass


class BacktestEngineV2:
    """
    基于 Backtrader 的回测引擎 v2（完全修复版）

    保留原有的简洁API，底层使用 Backtrader 执行
    所有已知的除零错误都已修复
    """

    def __init__(self,
                 initial_cash: float = 1000000,
                 commission: float = 0.001,
                 slippage: float = 0.0,
                 data_manager: Optional[DataManager] = None):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金
            commission: 佣金率（默认0.1%）
            slippage: 滑点率（默认0%）
            data_manager: 数据管理器
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage

        # 数据管理器
        if data_manager is None:
            data_manager = DataManager()
        self.data_manager = data_manager

        # 性能分析器
        from easyxt_backtest.performance import PerformanceAnalyzer
        self.performance_analyzer = PerformanceAnalyzer()

    def run_backtest(self,
                    strategy: StrategyBase,
                    start_date: str,
                    end_date: str) -> BacktestResult:
        """
        运行回测

        Args:
            strategy: 策略实例（StrategyBase）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            BacktestResult
        """
        print(f"\n{'='*70}")
        print(f"开始回测（基于 Backtrader v2 - 完全修复版）: {start_date} ~ {end_date}")
        print(f"{'='*70}")

        # 注入data_manager到策略
        strategy.data_manager = self.data_manager

        # 获取调仓日期
        rebalance_dates = strategy.get_rebalance_dates(start_date, end_date)
        print(f"\n调仓日期: {len(rebalance_dates)} 个")
        for i, date in enumerate(rebalance_dates, 1):
            print(f"  {i}. {date}")

        # 创建 Cerebro 引擎
        cerebro = bt.Cerebro()

        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)

        # 设置手续费
        cerebro.broker.setcommission(commission=self.commission)

        # ✅ 不添加 Backtrader 分析器（避免除零错误）
        # 我们会在 _extract_result 中使用自己的 PerformanceAnalyzer

        # 获取所有交易日
        try:
            trading_days = self.data_manager.get_trading_dates(start_date, end_date)
        except Exception as e:
            print(f"  [ERROR] 获取交易日失败: {e}")
            trading_days = []

        # 获取所有需要加载的股票代码
        all_symbols = self._get_all_symbols(strategy, start_date, end_date)

        print(f"\n加载数据: {len(all_symbols)} 只股票")

        # ✅ 为每只股票添加数据源（带完整验证）
        valid_symbols = []
        for symbol in all_symbols:
            df = self._load_symbol_data(symbol, start_date, end_date)

            if df is not None and not df.empty and len(df) > 0:
                try:
                    # ✅ 不设置 fromdate/todate，让 Backtrader 使用 DataFrame 中的所有数据
                    # 因为 DataFrame 已经被 _load_symbol_data 过滤到正确的日期范围了
                    data = bt.feeds.PandasData(
                        dataname=df,
                        name=symbol
                    )

                    cerebro.adddata(data)
                    valid_symbols.append(symbol)

                    # 🔍 调试：显示数据范围
                    print(f"  [DEBUG] {symbol}: {len(df)}条, {df.index[0]} ~ {df.index[-1]}")
                except Exception as e:
                    print(f"  [WARNING] {symbol} 添加数据源失败: {e}")
            else:
                print(f"  [WARNING] {symbol} 无有效数据")

        print(f"  有效数据: {len(valid_symbols)} 只股票")

        # ✅ 检查是否有有效数据
        if len(valid_symbols) == 0:
            print(f"\n[ERROR] 没有有效数据，无法回测")
            return self._create_empty_result()

        # 添加策略
        cerebro.addstrategy(
            _BacktraderStrategyAdapter,
            user_strategy=strategy,
            data_manager=self.data_manager,
            rebalance_dates=rebalance_dates,
            rebalance_dates_set=set(rebalance_dates),  # 转换为集合以便快速查找
            trading_dates=trading_days
        )

        # 运行回测
        print(f"\n开始执行回测...")

        # 🔍 调试：显示数据源信息
        print(f"\n[调试] Cerebro 数据源信息:")
        for i, data in enumerate(cerebro.datas):
            print(f"  数据源 {i+1}: {data._name if hasattr(data, '_name') else 'Unknown'}")
            try:
                print(f"    数据长度: {len(data)} 条")
                if len(data) > 0:
                    print(f"    第一条: {data.datetime.date(0)}")
                    print(f"    最后一条: {data.datetime.date(-1)}")
            except Exception as e:
                print(f"    读取失败: {e}")

        try:
            print(f"\n[调试] 开始调用 cerebro.run()...")
            results = cerebro.run()
            print(f"[调试] cerebro.run() 完成，返回 {len(results)} 个策略")
        except Exception as e:
            print(f"\n[ERROR] 回测执行失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_empty_result()

        # 提取结果
        if results and len(results) > 0:
            strat = results[0]
            result = self._extract_result(strat, trading_days)
        else:
            print(f"\n[WARNING] 无回测结果")
            result = self._create_empty_result()

        print(f"\n{'='*70}")
        print(f"回测完成！")
        print(f"{'='*70}\n")

        return result

    def _get_all_symbols(self, strategy: StrategyBase, start_date: str, end_date: str) -> List[str]:
        """获取所有可能涉及的股票代码"""
        try:
            rebalance_dates = strategy.get_rebalance_dates(start_date, end_date)
        except:
            return []

        all_symbols = set()

        # 只检查前几个调仓日，避免调用太多
        for date in rebalance_dates[:3]:
            try:
                symbols = strategy.select_stocks(date)
                all_symbols.update(symbols)
            except:
                continue

        return list(all_symbols)

    def _load_symbol_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        加载单只股票的数据（完全修复版）

        所有可能的无效数据都会被过滤
        """
        try:
            df = self.data_manager.get_price(
                codes=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                return None

            # 🔍 调试：检查原始数据结构
            print(f"  [DEBUG] {symbol} 原始数据: 形状={df.shape}, 列={list(df.columns)}, 索引名={df.index.name}")
            if len(df.index) > 0:
                print(f"  [DEBUG] {symbol} 索引类型: {type(df.index)}")
                print(f"  [DEBUG] {symbol} 第一个索引值: {df.index[0]} (类型: {type(df.index[0])})")
                if isinstance(df.index, pd.MultiIndex):
                    print(f"  [DEBUG] {symbol} MultiIndex级别: {df.index.names}")
                    print(f"  [DEBUG] {symbol} MultiIndex前3个: {list(df.index[:3])}")

            # ✅ QMT 返回的数据：日期在索引中，但索引名可能是 None 或 'time'
            # 需要保留索引作为日期，而不是 reset_index

            # 确保有必要的列（不包括 date，因为 date 在索引中）
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                print(f"  [ERROR] {symbol} 缺少必要的列: {df.columns}")
                return None

            # ✅ 过滤掉所有无效数据
            # 1. 价格 <= 0 的行
            for price_col in ['open', 'high', 'low', 'close']:
                if price_col in df.columns:
                    df = df[df[price_col] > 0]

            # 2. 成交量 < 0 的行
            if 'volume' in df.columns:
                df = df[df['volume'] >= 0]

            # 3. 包含 NaN 或 Inf 的行
            df = df.dropna(subset=['open', 'high', 'low', 'close'])

            # 检查过滤后是否还有数据
            if df.empty:
                return None

            # ✅ 验证数据有效性
            # 确保 high >= low
            df = df[df['high'] >= df['low']]

            # 确保 close 在 high 和 low 之间
            df = df[(df['close'] <= df['high']) & (df['close'] >= df['low'])]

            if df.empty:
                return None

            # ✅ 核心修复：处理 QMT 返回的 MultiIndex 格式
            # QMT 返回的 DataFrame 索引是 MultiIndex，格式：(date, symbol)
            # date 是 Unix 时间戳（毫秒），symbol 是股票代码
            try:
                if isinstance(df.index, pd.MultiIndex):
                    # MultiIndex 格式：(date, symbol)
                    # 级别0是date（Unix时间戳），级别1是symbol
                    df.index = df.index.get_level_values(0)  # 提取级别0（date）
                    # 将 Unix 时间戳（毫秒）转换为 datetime
                    df.index = pd.to_datetime(df.index, unit='ms')
                    df.index.name = 'datetime'
                    print(f"  [OK] {symbol} 从MultiIndex提取日期索引（Unix时间戳）")
                elif not isinstance(df.index, pd.DatetimeIndex):
                    # 普通索引，尝试转换
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'datetime'
                else:
                    # 已经是 DatetimeIndex，直接使用
                    df.index.name = 'datetime'

                # 验证日期是否合理
                if df.index.min().year < 2000 or df.index.max().year > 2100:
                    print(f"  [WARNING] {symbol} 日期范围异常: {df.index.min()} ~ {df.index.max()}")
                    return None

            except Exception as e:
                print(f"  [ERROR] {symbol} 日期解析失败: {e}, 索引类型: {type(df.index)}")
                return None

            # 确保按日期排序
            df.sort_index(inplace=True)

            # 去重（保留最后一条）
            df = df[~df.index.duplicated(keep='last')]

            print(f"  [OK] {symbol}: {len(df)}条, {df.index[0]} ~ {df.index[-1]}")

            return df

        except Exception as e:
            print(f"  [ERROR] {symbol} 数据加载失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_result(self, strategy, trading_days: List[str]) -> BacktestResult:
        """
        从 Backtrader 策略中提取结果（完全修复版）

        所有可能的除零问题都已处理
        """
        # 1. 交易记录
        if hasattr(strategy, 'trade_log') and strategy.trade_log:
            trades_df = pd.DataFrame(strategy.trade_log)
            print(f"\n[调试] 交易记录: {len(trades_df)} 笔")
            if not trades_df.empty:
                print(f"[调试] 交易记录列: {list(trades_df.columns)}")
                print(f"[调试] 前3笔交易:\n{trades_df.head(3)}")
        else:
            trades_df = pd.DataFrame()
            print(f"\n[调试] 无交易记录")

        # 2. 持仓历史
        if hasattr(strategy, 'portfolio_values') and strategy.portfolio_values:
            portfolio_df = pd.DataFrame(strategy.portfolio_values)
            if not portfolio_df.empty and 'date' in portfolio_df.columns:
                portfolio_df.set_index('date', inplace=True)
        else:
            portfolio_df = pd.DataFrame()

        # 3. ✅ 计算每日收益率（避免除零）
        if hasattr(strategy, 'portfolio_values') and len(strategy.portfolio_values) > 1:
            try:
                # ✅ 提取日期和值，保持日期索引
                dates = [pv['date'] for pv in strategy.portfolio_values]
                values = [pv['value'] for pv in strategy.portfolio_values]

                # ✅ 保护：过滤掉无效值
                valid_data = [
                    (d, v) for d, v in zip(dates, values)
                    if v is not None and v > 0 and not np.isnan(v) and not np.isinf(v)
                ]

                if len(valid_data) > 1:
                    valid_dates, valid_values = zip(*valid_data)
                    returns_series = pd.Series(valid_values, index=valid_dates).pct_change()

                    # ✅ 保护：处理 pct_change 产生的 inf/nan
                    returns_series = returns_series.replace([np.inf, -np.inf], 0)
                    returns_series = returns_series.fillna(0)
                else:
                    returns_series = pd.Series()
            except Exception as e:
                print(f"  [WARNING] 计算收益率失败: {e}")
                returns_series = pd.Series()
        else:
            returns_series = pd.Series()

        # 4. 性能指标
        try:
            if not returns_series.empty:
                performance = self.performance_analyzer.analyze(
                    returns=returns_series,
                    initial_cash=self.initial_cash
                )
            else:
                performance = self._create_empty_performance()
        except Exception as e:
            print(f"  [WARNING] 计算性能指标失败: {e}")
            performance = self._create_empty_performance()

        # 添加额外的统计
        if hasattr(strategy, 'trade_log'):
            performance['total_trades'] = len(strategy.trade_log)
        else:
            performance['total_trades'] = 0

        if hasattr(strategy, 'portfolio_values'):
            performance['trading_days'] = len(strategy.portfolio_values)
        else:
            performance['trading_days'] = 0

        return BacktestResult(
            trades=trades_df,
            portfolio_history=portfolio_df,
            returns=returns_series,
            performance=performance
        )

    def _create_empty_result(self) -> BacktestResult:
        """创建空结果（回测失败时使用）"""
        return BacktestResult(
            trades=pd.DataFrame(),
            portfolio_history=pd.DataFrame(),
            returns=pd.Series(),
            performance=self._create_empty_performance()
        )

    def _create_empty_performance(self) -> dict:
        """创建空性能指标"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'initial_cash': self.initial_cash,
            'final_value': self.initial_cash,
            'total_trades': 0,
            'trading_days': 0
        }


# 向后兼容的别名
BacktestEngine = BacktestEngineV2
