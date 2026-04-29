# -*- coding: utf-8 -*-
"""
统一的 Backtrader 底层引擎

这是所有回测策略的核心，提供：
- 统一的 Cerebro 管理
- 统一的数据加载
- 统一的性能分析
- 统一的结果提取
"""

import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime


class BacktestCore:
    """
    统一的 Backtrader 底层引擎

    所有回测策略（技术指标、选股、网格等）都基于这个核心
    """

    def __init__(self,
                 initial_cash: float = 100000.0,
                 commission: float = 0.001):
        """
        初始化回测核心

        Args:
            initial_cash: 初始资金
            commission: 佣金率
        """
        self.initial_cash = initial_cash
        self.commission = commission

        # 创建 Cerebro 引擎
        self.cerebro = bt.Cerebro()

        # 设置初始资金和佣金
        self.cerebro.broker.setcash(initial_cash)
        self.cerebro.broker.setcommission(commission=commission)

        # 设置默认每手股数（中国股市为100股/手）
        self.cerebro.addsizer(bt.sizers.FixedSize, stake=100)

        # 添加分析器
        self._add_analyzers()

        # 数据源列表
        self.data_feeds = []

        # 运行结果
        self.results = None

    def _add_analyzers(self):
        """添加性能分析器"""
        self.cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', riskfreerate=0.03)
        self.cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(btanalyzers.TimeReturn, _name='timereturn')

    def add_data(self, data, name: Optional[str] = None):
        """
        添加数据源

        Args:
            data: 数据源（PandasData 或其他格式）
            name: 数据源名称
        """
        if name is not None:
            data._name = name

        self.cerebro.adddata(data)
        self.data_feeds.append(data)

        return self

    def add_strategy(self, strategy_class, **kwargs):
        """
        添加策略

        Args:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.cerebro.addstrategy(strategy_class, **kwargs)
        return self

    def run(self):
        """运行回测"""
        self.results = self.cerebro.run()
        return self.results

    def get_broker_value(self):
        """获取当前账户价值"""
        return self.cerebro.broker.getvalue()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        if not self.results or len(self.results) == 0:
            return self._get_empty_metrics()

        strat = self.results[0]
        metrics = {}

        # 提取各项指标
        try:
            # 夏普比率
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            metrics['sharpe_ratio'] = sharpe_analysis.get('sharperatio', 0)

            # 最大回撤
            drawdown_analysis = strat.analyzers.drawdown.get_analysis()
            raw_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0)
            metrics['max_drawdown'] = raw_drawdown / 100.0 if raw_drawdown != 0 else 0

            # 总收益率
            returns_analysis = strat.analyzers.returns.get_analysis()
            total_return = returns_analysis.get('rtot', 0)
            metrics['total_return'] = total_return

            # 年化收益率
            annual_return = returns_analysis.get('ravg', 0)
            metrics['annual_return'] = annual_return * 252  # 假设252个交易日

            # 初始资金和最终资金
            metrics['initial_cash'] = self.initial_cash
            metrics['final_value'] = self.get_broker_value()

        except Exception as e:
            print(f"[WARNING] 提取性能指标时出错: {e}")
            return self._get_empty_metrics()

        return metrics

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """返回空指标（用于测试）"""
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'total_return': 0,
            'annual_return': 0,
            'initial_cash': self.initial_cash,
            'final_value': self.initial_cash,
        }

    def get_full_results(self) -> Dict[str, Any]:
        """
        获取完整的回测结果（含交易记录和净值曲线）

        Returns:
            包含 metrics, trades, portfolio_curve, risk_analysis 的字典
        """
        metrics = self.get_performance_metrics()

        trades = []
        portfolio_curve = {'dates': [], 'values': []}
        risk_analysis = {}

        if not self.results or len(self.results) == 0:
            return {
                'metrics': metrics,
                'trades': trades,
                'portfolio_curve': portfolio_curve,
                'risk_analysis': risk_analysis,
            }

        strat = self.results[0]

        # 提取交易记录
        try:
            trade_analysis = strat.analyzers.trades.get_analysis()
            total = trade_analysis.get('total', {})
            won = trade_analysis.get('won', {})
            lost = trade_analysis.get('lost', {})
            trades = [
                ('总交易次数', total.get('total', 0), ''),
                ('盈利次数', won.get('total', 0), ''),
                ('亏损次数', lost.get('total', 0), ''),
                ('胜率', f"{won.get('total', 0) / max(total.get('total', 1), 1) * 100:.1f}%", ''),
            ]
        except Exception as e:
            print(f"[WARNING] 提取交易记录时出错: {e}")

        # 构建净值曲线
        try:
            timereturn_analysis = strat.analyzers.timereturn.get_analysis()
            if timereturn_analysis:
                cumulative_value = self.initial_cash
                dates = []
                values = []
                for date_key, ret in timereturn_analysis.items():
                    cumulative_value *= (1 + ret)
                    dates.append(str(date_key))
                    values.append(round(cumulative_value, 2))
                portfolio_curve = {'dates': dates, 'values': values}
        except Exception as e:
            print(f"[WARNING] 构建净值曲线时出错: {e}")

        # 计算风险指标
        try:
            risk_analysis = {
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'total_return': metrics.get('total_return', 0),
                'annual_return': metrics.get('annual_return', 0),
                'volatility': metrics.get('volatility', 0),
                'calmar_ratio': metrics.get('calmar_ratio', 0),
                'initial_cash': metrics.get('initial_cash', self.initial_cash),
                'final_value': metrics.get('final_value', self.initial_cash),
            }
        except Exception as e:
            print(f"[WARNING] 计算风险指标时出错: {e}")

        return {
            'metrics': metrics,
            'trades': trades,
            'portfolio_curve': portfolio_curve,
            'risk_analysis': risk_analysis,
        }


class DataManager:
    """
    统一的数据管理器

    提供数据加载和预处理功能
    """

    @staticmethod
    def load_stock_data(stock_code: str,
                       start_date: str,
                       end_date: str,
                       data_source=None) -> pd.DataFrame:
        """
        加载股票数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            data_source: 数据源（可选）

        Returns:
            股票数据 DataFrame，索引为日期
        """
        # 优先使用项目的LocalDataManager（更可靠）
        try:
            import sys
            from pathlib import Path as _Path
            # 直接指向101因子平台的数据管理模块，不经过项目根桥接
            _factor_src = _Path(__file__).resolve().parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(_factor_src) not in sys.path:
                sys.path.insert(0, str(_factor_src))
            from data_manager import LocalDataManager
            dm = LocalDataManager()

            print(f"  [数据加载] 使用LocalDataManager加载 {stock_code}...")

            # load_data期望的日期格式是YYYY-MM-DD
            data_dict = dm.load_data(
                symbols=[stock_code],
                start_date=start_date,
                end_date=end_date
            )

            if data_dict and stock_code in data_dict:
                df = data_dict[stock_code]

                if df is not None and not df.empty:
                    # 确保索引是日期类型
                    if not isinstance(df.index, pd.DatetimeIndex):
                        try:
                            df.index = pd.to_datetime(df.index)
                        except:
                            # 如果转换失败，尝试重置索引
                            df = df.reset_index()
                            if 'date' in df.columns:
                                df['date'] = pd.to_datetime(df['date'])
                                df.set_index('date', inplace=True)
                            elif 'datetime' in df.columns:
                                df['datetime'] = pd.to_datetime(df['datetime'])
                                df.set_index('datetime', inplace=True)

                    print(f"  [OK] 数据加载成功: {len(df)} 条记录 ({df.index.min().strftime('%Y-%m-%d')} 至 {df.index.max().strftime('%Y-%m-%d')})")
                    return df
                else:
                    print(f"  [WARNING] LocalDataManager返回空数据")
                    return pd.DataFrame()
            else:
                print(f"  [WARNING] LocalDataManager未找到 {stock_code} 的数据")
                return pd.DataFrame()

        except ImportError as e:
            print(f"  [ERROR] 无法导入 LocalDataManager: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"  [ERROR] LocalDataManager加载失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @staticmethod
    def prepare_backtrader_data(df: pd.DataFrame) -> bt.feeds.PandasData:
        """
        将 DataFrame 转换为 Backtrader 数据源

        Args:
            df: 股票数据

        Returns:
            Backtrader 数据源
        """
        if df.empty:
            raise ValueError("数据为空")

        # 确保索引是日期时间格式
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # 创建 Backtrader 数据源
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # 使用索引作为日期
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )

        return data

    def get_connection_status(self) -> dict:
        """
        获取数据源连接状态

        Returns:
            dict: 包含 active_source 和 source_status 的字典
        """
        # 尝试检查各个数据源的可用性
        source_status = {
            'qmt': {'available': False, 'connected': False},
            'duckdb': {'available': False, 'connected': False},
            'local': {'available': False, 'connected': False},
            'qstock': {'available': False, 'connected': False},
            'akshare': {'available': False, 'connected': False},
        }

        # 检查 QMT
        try:
            import easy_xt
            api = easy_xt.get_api()
            if hasattr(api, 'data') and hasattr(api.data, 'get_current_price'):
                # 尝试获取一个测试数据
                test_df = api.data.get_current_price(['000001.SZ'])
                if test_df is not None and not test_df.empty:
                    source_status['qmt']['available'] = True
                    source_status['qmt']['connected'] = True
                else:
                    source_status['qmt']['available'] = True
                    source_status['qmt']['connected'] = False
        except:
            pass

        # 检查 DuckDB
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            duckdb_path = os.getenv('DUCKDB_PATH')
            if duckdb_path and os.path.exists(duckdb_path):
                import duckdb
                conn = duckdb.connect(duckdb_path)
                # 简单测试查询
                result = conn.execute("SELECT 1").fetchone()
                if result:
                    source_status['duckdb']['available'] = True
                    source_status['duckdb']['connected'] = True
                conn.close()
        except:
            pass

        # 检查 qstock
        try:
            import qstock
            source_status['qstock']['available'] = True
            source_status['qstock']['connected'] = True
        except:
            pass

        # 检查 akshare
        try:
            import akshare as ak
            source_status['akshare']['available'] = True
            source_status['akshare']['connected'] = True
        except:
            pass

        # 本地缓存总是可用的
        source_status['local']['available'] = True
        source_status['local']['connected'] = True

        # 确定活跃数据源（优先级：qmt > duckdb > qstock > akshare > local > mock）
        active_source = 'mock'
        if source_status['qmt']['connected']:
            active_source = 'qmt'
        elif source_status['duckdb']['connected']:
            active_source = 'duckdb'
        elif source_status['qstock']['connected']:
            active_source = 'qstock'
        elif source_status['akshare']['connected']:
            active_source = 'akshare'
        elif source_status['local']['connected']:
            active_source = 'local'

        return {
            'active_source': active_source,
            'source_status': source_status
        }

    def refresh_source_status(self):
        """
        刷新数据源状态

        此方法用于重新检查所有数据源的可用性
        """
        # 触发状态重新检查
        # 实际检查会在下次调用 get_connection_status() 时进行
        pass
