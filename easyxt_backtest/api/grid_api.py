# -*- coding: utf-8 -*-
"""
网格交易策略 API

提供简洁的 API 用于网格交易策略回测
支持3种网格策略：固定网格、自适应网格、ATR动态网格
"""
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import datetime
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ..strategies.grid_strategy import GridStrategy, AdaptiveGridStrategy, ATRGridStrategy


class GridBacktestEngine:
    """
    网格交易策略回测引擎

    提供3种网格策略的统一回测接口：
    1. fixed - 固定网格策略
    2. adaptive - 自适应网格策略
    3. atr - ATR动态网格策略

    使用HybridDataManager获取数据（支持DuckDB/QMT/Tushare）
    """

    def __init__(self,
                 initial_cash: float = 100000.0,
                 commission: float = 0.0001,
                 data_manager=None):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金（默认10万）
            commission: 手续费率（默认万分之一，适合ETF）
            data_manager: 数据管理器（HybridDataManager实例）
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.data_manager = data_manager

        # 导入数据管理器（延迟导入避免循环依赖）
        if data_manager is None:
            try:
                from core.data_manager import HybridDataManager
                self.data_manager = HybridDataManager()
            except ImportError:
                print("[WARNING] 无法导入HybridDataManager，部分功能可能受限")
                self.data_manager = None

    def run_backtest(self,
                    stock_code: str,
                    start_date: str,
                    end_date: str,
                    strategy_mode: str = 'fixed',
                    # 固定网格参数
                    grid_count: int = 15,
                    price_range: float = 0.05,
                    enable_trailing: bool = True,
                    # 自适应网格参数
                    buy_threshold: float = 0.01,
                    sell_threshold: float = 0.01,
                    max_position: int = 10000,
                    # ATR网格参数
                    atr_period: int = 300,
                    atr_multiplier: float = 6.0,
                    trailing_period: int = 20,
                    # 通用参数
                    position_size: int = 1000,
                    base_price: float = None,
                    data_period: str = '1d') -> Dict[str, Any]:
        """
        运行单次回测（支持三种策略模式）

        Args:
            stock_code: 股票代码（如511380.SH）
            start_date: 开始日期（YYYY-MM-DD或YYYYMMDD）
            end_date: 结束日期（YYYY-MM-DD或YYYYMMDD）
            strategy_mode: 策略模式 ('fixed'/'adaptive'/'atr')
            grid_count: 固定网格数量
            price_range: 固定网格价格区间比例
            enable_trailing: 固定网格是否启用动态调整
            buy_threshold: 自适应网格买入阈值
            sell_threshold: 自适应网格卖出阈值
            max_position: 自适应网格最大持仓
            atr_period: ATR网格周期
            atr_multiplier: ATR网格倍数
            trailing_period: 动态调整周期（天）
            position_size: 每格交易数量
            base_price: 基准价格（None则使用首日收盘价）
            data_period: 数据周期（1m/5m/15m/30m/1h/1d/1w）

        Returns:
            Dict: {
                'metrics': {...},           # 性能指标
                'trade_log': DataFrame,     # 交易日志
                'equity_curve': DataFrame,  # 净值曲线
                'params': {...}             # 使用的参数
            }
        """
        # 获取数据
        stock_data = self._load_data(stock_code, start_date, end_date, data_period)

        if stock_data.empty:
            raise Exception(f"无法获取{stock_code}的数据")

        # 创建回测引擎
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=self.commission)

        # 添加数据
        data_feed = bt.feeds.PandasData(dataname=stock_data)
        cerebro.adddata(data_feed)

        # 根据策略模式添加不同的策略
        if strategy_mode == 'fixed':
            cerebro.addstrategy(
                GridStrategy,
                grid_count=grid_count,
                price_range=price_range,
                position_size=position_size,
                base_price=base_price,
                enable_trailing=enable_trailing
            )
            print(f"[策略模式] 固定网格")
            print(f"[参数] 网格数={grid_count}, 区间={price_range*100:.1f}%, 动态调整={enable_trailing}")

        elif strategy_mode == 'adaptive':
            cerebro.addstrategy(
                AdaptiveGridStrategy,
                buy_threshold=buy_threshold,
                sell_threshold=sell_threshold,
                position_size=position_size,
                base_price=base_price,
                max_position=max_position
            )
            print(f"[策略模式] 自适应网格")
            print(f"[参数] 买入阈值={buy_threshold*100:.2f}%, 卖出阈值={sell_threshold*100:.2f}%")

        elif strategy_mode == 'atr':
            cerebro.addstrategy(
                ATRGridStrategy,
                atr_period=atr_period,
                atr_multiplier=atr_multiplier,
                position_size=position_size,
                base_price=base_price,
                enable_trailing=enable_trailing,
                trailing_period=trailing_period
            )
            print(f"[策略模式] ATR动态网格")
            print(f"[参数] ATR周期={atr_period}, ATR倍数={atr_multiplier}")

        else:
            raise ValueError(f"未知的策略模式: {strategy_mode}")

        # 添加分析器
        try:
            import backtrader.analyzers as btanalyzers
            cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
            cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
            cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
        except ImportError:
            print("[WARNING] Backtrader分析器导入失败")

        # 运行回测
        print(f"\n{'='*60}")
        print(f"开始回测: {stock_code}")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_cash:,.2f}")
        print(f"每格交易数量: {position_size}股")
        print(f"{'='*60}\n")

        results = cerebro.run()
        strategy = results[0]

        # 获取分析结果
        metrics = self._extract_metrics(cerebro, results, strategy)

        # 构建返回的参数字典
        params_dict = {
            'strategy_mode': strategy_mode,
            'position_size': position_size,
            'base_price': base_price,
            'data_period': data_period
        }

        # 根据策略模式添加特定参数
        if strategy_mode == 'fixed':
            params_dict.update({
                'grid_count': grid_count,
                'price_range': price_range,
                'enable_trailing': enable_trailing
            })
        elif strategy_mode == 'adaptive':
            params_dict.update({
                'buy_threshold': buy_threshold,
                'sell_threshold': sell_threshold,
                'max_position': max_position
            })
        elif strategy_mode == 'atr':
            params_dict.update({
                'atr_period': atr_period,
                'atr_multiplier': atr_multiplier,
                'trailing_period': trailing_period
            })

        return {
            'metrics': metrics,
            'trade_log': strategy.get_trade_log(),
            'equity_curve': strategy.get_equity_curve(),
            'params': params_dict
        }

    def _load_data(self, stock_code: str, start_date: str, end_date: str, period: str = '1d') -> pd.DataFrame:
        """
        加载K线数据（使用HybridDataManager）

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD 或 YYYYMMDD)
            end_date: 结束日期 (YYYY-MM-DD 或 YYYYMMDD)
            period: 数据周期

        Returns:
            pd.DataFrame: K线数据
        """
        if self.data_manager is None:
            raise Exception("数据管理器未初始化")

        # 转换日期格式为 YYYYMMDD（HybridDataManager 要求）
        def parse_date(date_str):
            """解析日期字符串并返回 YYYYMMDD 格式"""
            if '-' in date_str:
                # YYYY-MM-DD 格式
                return date_str.replace('-', '')
            else:
                # 已经是 YYYYMMDD 格式或其他格式
                return date_str

        start_date_YYYYMMDD = parse_date(start_date)
        end_date_YYYYMMDD = parse_date(end_date)

        # 使用HybridDataManager获取数据
        try:
            df = self.data_manager.get_price(
                symbol=stock_code,
                start_date=start_date_YYYYMMDD,
                end_date=end_date_YYYYMMDD,
                period=period
            )

            if df.empty:
                raise Exception(f"没有{stock_code}的数据")

            print(f"[数据加载] 原始数据形状: {df.shape}, 列: {df.columns.tolist()}")
            print(f"[数据加载] 前3行数据:\n{df.head(3)}")

            # 保存原始数据用于调试
            df_original = df.copy()

            # 确保列名是小写
            df.columns = df.columns.str.lower()

            # QMT数据格式处理：symbol列是多余的，date列包含实际日期
            if 'date' in df.columns:
                print(f"[数据加载] 检测到 date 列，类型: {df['date'].dtype}")

                # 如果date列是整数（Unix时间戳毫秒），需要转换
                if df['date'].dtype in ['int64', 'int32', 'uint64', 'uint32']:
                    print(f"[数据加载] date列是Unix时间戳，转换为datetime")
                    df['date'] = pd.to_datetime(df['date'], unit='ms')
                else:
                    # 尝试直接转换
                    try:
                        df['date'] = pd.to_datetime(df['date'])
                    except:
                        pass

                # 设置date为索引
                df = df.set_index('date')
                df.index.name = 'datetime'

            elif isinstance(df.index, pd.MultiIndex):
                print(f"[数据加载] 检测到MultiIndex")
                # 提取日期索引（level 0）
                df.index = df.index.get_level_values(0)
                # 如果是Unix时间戳，需要转换
                if df.index.dtype in ['int64', 'int32', 'uint64', 'uint32']:
                    df.index = pd.to_datetime(df.index, unit='ms')
                else:
                    df.index = pd.to_datetime(df.index)
                df.index.name = 'datetime'

            else:
                # 尝试将索引转换为 datetime
                try:
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'datetime'
                except Exception as e:
                    print(f"[WARNING] 索引转换失败: {e}")

            # 删除不需要的列
            cols_to_drop = ['symbol', 'amount']
            for col in cols_to_drop:
                if col in df.columns:
                    df = df.drop(columns=[col])

            # 确保必要的列存在
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"数据缺少必要列: {col}，当前列: {df.columns.tolist()}")

            # 删除重复索引
            df = df[~df.index.duplicated(keep='first')]

            # 排序
            df = df.sort_index()

            # 确保索引是 datetime 类型
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.to_datetime(df.index)
                except:
                    raise ValueError(f"无法将索引转换为DatetimeIndex，当前类型: {type(df.index)}")

            print(f"[数据加载] 成功加载 {len(df)} 条数据")
            print(f"[数据范围] {df.index[0]} ~ {df.index[-1]}")
            print(f"[数据验证] 数据类型: {df.dtypes.to_dict()}")

            return df

        except Exception as e:
            print(f"[ERROR] 数据加载失败: {e}")
            raise

    def _extract_metrics(self, cerebro, results, strategy) -> Dict[str, Any]:
        """
        提取回测指标

        Args:
            cerebro: Backtrader引擎
            results: 回测结果
            strategy: 策略实例

        Returns:
            Dict: 性能指标
        """
        metrics = {
            'initial_cash': self.initial_cash,
            'final_value': cerebro.broker.getvalue(),
            'total_return': (cerebro.broker.getvalue() - self.initial_cash) / self.initial_cash,
        }

        # 尝试提取分析器结果
        try:
            strat_result = results[0]

            # 打印调试信息
            if hasattr(strat_result, 'analyzers'):
                print(f"[分析器] 分析器对象类型: {type(strat_result.analyzers)}")
                try:
                    # 遍历可用的分析器
                    analyzer_names = []
                    for analyzer in strat_result.analyzers:
                        analyzer_names.append(analyzer.alias)
                    print(f"[分析器] 可用的分析器: {analyzer_names}")
                except:
                    print(f"[分析器] 无法获取分析器名称列表")
            else:
                print(f"[WARNING] 策略没有analyzers属性")

            # 夏普比率
            sharpe_from_analyzer = None
            try:
                sharpe_analyzer = strat_result.analyzers.sharpe
                sharpe_analysis = sharpe_analyzer.get_analysis()
                print(f"[分析器] 夏普比率分析结果: {sharpe_analysis}")
                if sharpe_analysis and 'sharperatio' in sharpe_analysis:
                    sharpe_from_analyzer = sharpe_analysis['sharperatio']
                    if sharpe_from_analyzer is not None:
                        metrics['sharpe_ratio'] = sharpe_from_analyzer
                        print(f"[分析器] 夏普比率: {metrics['sharpe_ratio']}")
                    else:
                        print(f"[WARNING] 分析器返回的夏普比率为 None，将手动计算")
                else:
                    print(f"[WARNING] 夏普比率分析结果中没有sharperatio键，将手动计算")
            except (AttributeError, KeyError) as e:
                print(f"[WARNING] 提取夏普比率失败: {e}，将手动计算")

            # 回撤
            try:
                drawdown_analyzer = strat_result.analyzers.drawdown
                drawdown = drawdown_analyzer.get_analysis()
                print(f"[分析器] 回撤分析结果: {drawdown}")
                if drawdown and 'max' in drawdown:
                    metrics['max_drawdown'] = drawdown['max'].get('drawdown', 0)
                    metrics['max_drawdown_len'] = drawdown['max'].get('len', 0)
            except (AttributeError, KeyError) as e:
                print(f"[WARNING] 提取回撤失败: {e}")

        except Exception as e:
            print(f"[WARNING] 提取分析器指标失败: {e}")
            import traceback
            traceback.print_exc()

        # 计算胜率
        trade_log = strategy.get_trade_log()
        if not trade_log.empty:
            won_count, lost_count, win_rate = self._calculate_win_rate(trade_log)
            metrics['total_trades'] = len(trade_log)
            metrics['won_trades'] = won_count
            metrics['lost_trades'] = lost_count
            metrics['win_rate'] = win_rate
        else:
            metrics['total_trades'] = 0
            metrics['won_trades'] = 0
            metrics['lost_trades'] = 0
            metrics['win_rate'] = 0.0

        # 如果分析器没有返回夏普比率，手动计算
        if 'sharpe_ratio' not in metrics or metrics['sharpe_ratio'] is None:
            print(f"[夏普比率] 手动计算夏普比率...")
            equity_curve = strategy.get_equity_curve()
            if not equity_curve.empty and len(equity_curve) > 2:
                # 计算日收益率
                portfolio_values = equity_curve['portfolio_value'].values
                returns = np.diff(portfolio_values) / portfolio_values[:-1]

                # 过滤掉NaN和无穷大
                returns = returns[np.isfinite(returns)]

                if len(returns) > 1 and returns.std() > 0:
                    # 年化夏普比率（假设无风险利率=0）
                    # 公式：Sharpe = (平均收益率 / 收益率标准差) * sqrt(252)
                    daily_return = returns.mean()
                    daily_vol = returns.std()

                    # 根据数据周期调整年化系数
                    data_period = strategy.params.get('data_period', '1d') if hasattr(strategy.params, 'get') else '1d'

                    # 估算年化系数（基于数据周期）
                    period_factor_map = {
                        '1m': 252 * 4 * 60,   # 1分钟：252天 * 4小时 * 60分钟
                        '5m': 252 * 4 * 12,    # 5分钟：252天 * 4小时 * 12（5分钟1小时12个）
                        '15m': 252 * 4 * 4,    # 15分钟：252天 * 4小时 * 4（15分钟1小时4个）
                        '30m': 252 * 8,        # 30分钟：252天 * 8（30分钟1天8个，假设4小时交易时间）
                        '1h': 252 * 4,         # 1小时：252天 * 4小时
                        '1d': 252,             # 日线：252天
                        '1w': 52,              # 周线：52周
                    }
                    annual_factor = period_factor_map.get(data_period, 252)

                    # 计算年化夏普比率
                    sharpe = (daily_return * annual_factor) / (daily_vol * np.sqrt(annual_factor))

                    metrics['sharpe_ratio'] = sharpe
                    print(f"[夏普比率] 手动计算完成: {sharpe:.4f}")
                    print(f"  日均收益率: {daily_return:.6f}")
                    print(f"  日波动率: {daily_vol:.6f}")
                    print(f"  年化系数: {annual_factor}")
                else:
                    metrics['sharpe_ratio'] = None
                    print(f"[WARNING] 无法计算夏普比率：数据点太少({len(returns)})或波动率为0")
            else:
                metrics['sharpe_ratio'] = None
                print(f"[WARNING] 无法计算夏普比率：净值曲线数据不足")

        return metrics

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


def backtest_grid_fixed(stock_code: str,
                       start_date: str,
                       end_date: str,
                       grid_count: int = 15,
                       price_range: float = 0.05,
                       position_size: int = 1000,
                       **kwargs) -> Dict[str, Any]:
    """
    快速回测：固定网格策略

    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        grid_count: 网格数量
        price_range: 价格区间比例
        position_size: 每格交易数量
        **kwargs: 其他参数

    Returns:
        回测结果字典
    """
    engine = GridBacktestEngine(**kwargs)
    return engine.run_backtest(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        strategy_mode='fixed',
        grid_count=grid_count,
        price_range=price_range,
        position_size=position_size
    )


def backtest_grid_adaptive(stock_code: str,
                          start_date: str,
                          end_date: str,
                          buy_threshold: float = 0.01,
                          sell_threshold: float = 0.01,
                          position_size: int = 1000,
                          **kwargs) -> Dict[str, Any]:
    """
    快速回测：自适应网格策略

    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        buy_threshold: 买入阈值
        sell_threshold: 卖出阈值
        position_size: 每次交易数量
        **kwargs: 其他参数

    Returns:
        回测结果字典
    """
    engine = GridBacktestEngine(**kwargs)
    return engine.run_backtest(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        strategy_mode='adaptive',
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        position_size=position_size
    )


def backtest_grid_atr(stock_code: str,
                     start_date: str,
                     end_date: str,
                     atr_period: int = 300,
                     atr_multiplier: float = 6.0,
                     position_size: int = 1000,
                     **kwargs) -> Dict[str, Any]:
    """
    快速回测：ATR动态网格策略

    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        atr_period: ATR周期
        atr_multiplier: ATR倍数
        position_size: 每次交易数量
        **kwargs: 其他参数

    Returns:
        回测结果字典
    """
    engine = GridBacktestEngine(**kwargs)
    return engine.run_backtest(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        strategy_mode='atr',
        atr_period=atr_period,
        atr_multiplier=atr_multiplier,
        position_size=position_size
    )
