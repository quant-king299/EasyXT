"""
回测引擎模块
实现基于因子的策略回测功能
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.utils.data_utils import align_factor_with_prices


class BacktestEngine:
    """
    回测引擎
    支持基于因子的策略回测，包括多空组合、分层回测等功能
    """
    
    def __init__(self):
        self.results = {}
        self.portfolio_history = {}
        self.performance_metrics = {}

    def _calculate_stock_weights(self, stocks: List[str], factor_values: pd.Series,
                                 weight_method: str, n_stocks: Optional[int] = None) -> Dict[str, float]:
        """
        计算股票权重

        Args:
            stocks: 股票代码列表
            factor_values: 因子值Series（索引包含date和symbol）
            weight_method: 权重分配方式 ('equal', 'fixed_n', 'factor_weighted')
            n_stocks: 固定股票数量（仅用于fixed_n模式）

        Returns:
            Dict[str, float]: 股票代码 -> 权重
        """
        weights = {}

        if weight_method == 'equal':
            # 等权重：平均分配
            weight = 1.0 / len(stocks) if stocks else 0
            weights = {stock: weight for stock in stocks}

        elif weight_method == 'fixed_n':
            # 固定N只：每只固定权重
            if not n_stocks or n_stocks <= 0:
                n_stocks = 10  # 默认10只
            n_stocks = min(n_stocks, len(stocks))

            # 只使用前n_stocks只股票
            selected_stocks = stocks[:n_stocks]
            weight = 1.0 / len(selected_stocks)
            weights = {stock: weight for stock in selected_stocks}

        elif weight_method == 'factor_weighted':
            # 因子值加权：因子值标准化后作为权重
            current_factor_values = factor_values.loc[factor_values.index.get_level_values('symbol').isin(stocks)]

            # 标准化到[0, 1]范围
            min_val = current_factor_values.min()
            max_val = current_factor_values.max()

            if max_val > min_val:
                normalized = (current_factor_values - min_val) / (max_val - min_val)
                # 归一化使得总和为1
                total = normalized.sum()
                if total > 0:
                    for stock, norm_val in zip(stocks, normalized):
                        weights[stock] = norm_val / total
            else:
                # 所有因子值相同，使用等权重
                weight = 1.0 / len(stocks) if stocks else 0
                weights = {stock: weight for stock in stocks}

        return weights

    def backtest_long_short_portfolio(self,
                                      factor_data: pd.Series,
                                      price_data: pd.DataFrame,
                                      top_quantile: float = 0.1,
                                      bottom_quantile: float = 0.1,
                                      rebalance_freq: str = 'monthly',
                                      transaction_cost: float = 0.001,
                                      weight_method: str = 'equal',
                                      fixed_n_stocks: Optional[int] = None) -> Dict:
        """
        多空组合回测

        Args:
            factor_data: 因子数据 (Series with MultiIndex)
            price_data: 价格数据 (DataFrame with MultiIndex)
            top_quantile: 做多组合的分位数
            bottom_quantile: 做空组合的分位数
            rebalance_freq: 调仓频率 ('daily', 'weekly', 'monthly')
            transaction_cost: 交易成本
            weight_method: 权重分配方式 ('equal', 'fixed_n', 'factor_weighted')
            fixed_n_stocks: 固定股票数量（仅用于fixed_n模式）

        Returns:
            Dict: 回测结果
        """
        print(f"[DEBUG] 开始多空组合回测，做多前{top_quantile*100}%，做空后{bottom_quantile*100}%")

        # 调试信息：检查输入数据
        print(f"[DEBUG] factor_data 类型: {type(factor_data)}, 形状: {factor_data.shape if hasattr(factor_data, 'shape') else 'N/A'}")
        print(f"[DEBUG] factor_data 索引类型: {type(factor_data.index)}, 索引名称: {factor_data.index.names if hasattr(factor_data.index, 'names') else 'N/A'}")
        print(f"[DEBUG] price_data 类型: {type(price_data)}, 形状: {price_data.shape if hasattr(price_data, 'shape') else 'N/A'}")
        print(f"[DEBUG] price_data 索引类型: {type(price_data.index)}, 索引名称: {price_data.index.names if hasattr(price_data.index, 'names') else 'N/A'}")

        # 按日期分组，对每个截面进行排序
        dates = sorted(factor_data.index.get_level_values(0).unique())
        print(f"[DEBUG] factor_data 中的日期数量: {len(dates)}")
        print(f"[DEBUG] factor_data 前5个日期: {dates[:5]}")

        # 检查 price_data 中的日期
        price_dates = sorted(price_data.index.get_level_values(0).unique())
        print(f"[DEBUG] price_data 中的日期数量: {len(price_dates)}")
        print(f"[DEBUG] price_data 前5个日期: {price_dates[:5]}")

        # 检查索引名称是否匹配
        if hasattr(factor_data.index, 'names') and hasattr(price_data.index, 'names'):
            if factor_data.index.names != price_data.index.names:
                print(f"[DEBUG] 警告: 索引名称不匹配! factor_data: {factor_data.index.names}, price_data: {price_data.index.names}")
                # 尝试统一索引名称
                if 'date' not in price_data.index.names or 'symbol' not in price_data.index.names:
                    print("[DEBUG] 尝试统一 price_data 索引名称...")
                    # 假设第一个层级是 date，第二个层级是 symbol
                    if len(price_data.index.names) == 2:
                        price_data.index.names = ['date', 'symbol']
                        print(f"[DEBUG] 统一后的 price_data 索引名称: {price_data.index.names}")
        
        daily_returns = []
        long_returns = []  # 做多组合收益
        short_returns = []  # 做空组合收益

        # 交易明细记录
        trade_details = []
        previous_long_stocks = set()
        previous_short_stocks = set()
        
        for i, date in enumerate(dates):
            # 获取当天的因子值
            date_mask = factor_data.index.get_level_values(0) == date
            current_factors = factor_data[date_mask]
            
            if len(current_factors) < 2:
                continue  # 至少需要2个股票
            
            # 排序并选择做多和做空的股票
            sorted_factors = current_factors.sort_values(ascending=False)
            n_stocks = len(sorted_factors)
            
            # 计算需要选择的股票数量
            top_n = max(1, int(n_stocks * top_quantile))
            bottom_n = max(1, int(n_stocks * bottom_quantile))
            
            # 选择做多和做空的股票
            long_stocks = sorted_factors.head(top_n).index.get_level_values(1)
            short_stocks = sorted_factors.tail(bottom_n).index.get_level_values(1)
            
            # 获取这些股票的价格数据
            date_price_mask = price_data.index.get_level_values(0) == date
            date_prices = price_data[date_price_mask]
            
            # 过滤出有价格数据的股票
            long_stocks = [stock for stock in long_stocks if stock in date_prices.index.get_level_values(1)]
            short_stocks = [stock for stock in short_stocks if stock in date_prices.index.get_level_values(1)]
            
            if not long_stocks or not short_stocks:
                continue
            
            # 计算收益率
            # 需要获取下一天的价格来计算当日收益
            if i < len(dates) - 1:  # 不是最后一个日期
                next_date = dates[i + 1]
                next_date_mask = price_data.index.get_level_values(0) == next_date
                next_prices = price_data[next_date_mask]
                
                # 计算做多和做空组合的收益率
                long_stocks_data = {}  # stock -> (current_price, next_price)
                for stock in long_stocks:
                    current_price_data = date_prices[date_prices.index.get_level_values(1) == stock]
                    next_price_data = next_prices[next_prices.index.get_level_values(1) == stock]

                    if len(current_price_data) > 0 and len(next_price_data) > 0:
                        current_price = current_price_data['close'].iloc[0]
                        next_price = next_price_data['close'].iloc[0]
                        if not (np.isnan(current_price) or np.isnan(next_price)):
                            long_stocks_data[stock] = (current_price, next_price)

                short_stocks_data = {}  # stock -> (current_price, next_price)
                for stock in short_stocks:
                    current_price_data = date_prices[date_prices.index.get_level_values(1) == stock]
                    next_price_data = next_prices[next_prices.index.get_level_values(1) == stock]

                    if len(current_price_data) > 0 and len(next_price_data) > 0:
                        current_price = current_price_data['close'].iloc[0]
                        next_price = next_price_data['close'].iloc[0]
                        if not (np.isnan(current_price) or np.isnan(next_price)):
                            short_stocks_data[stock] = (current_price, next_price)

                if long_stocks_data and short_stocks_data:
                    # 计算权重
                    long_weights = self._calculate_stock_weights(
                        list(long_stocks_data.keys()),
                        current_factors,
                        weight_method,
                        fixed_n_stocks
                    )
                    short_weights = self._calculate_stock_weights(
                        list(short_stocks_data.keys()),
                        current_factors,
                        weight_method,
                        fixed_n_stocks
                    )

                    # 记录交易明细
                    current_long_set = set(long_stocks_data.keys())
                    current_short_set = set(short_stocks_data.keys())

                    # 做多组合：新买入的股票
                    for stock in current_long_set - previous_long_stocks:
                        if stock in long_stocks_data and stock in long_weights:
                            price = long_stocks_data[stock][0]
                            # 修复：使用MultiIndex查询因子值
                            if (date, stock) in current_factors.index:
                                factor_val = current_factors.loc[(date, stock)]
                            else:
                                factor_val = np.nan
                            trade_details.append({
                                'date': date,
                                'symbol': stock,
                                'direction': '做多',
                                'action': '买入',
                                'price': price,
                                'weight': long_weights[stock],
                                'factor_value': factor_val
                            })

                    # 做多组合：卖出的股票
                    for stock in previous_long_stocks - current_long_set:
                        trade_details.append({
                            'date': date,
                            'symbol': stock,
                            'direction': '做多',
                            'action': '卖出',
                            'price': np.nan,  # 卖出时使用下一交易日开盘价，这里简化处理
                            'weight': 0,
                            'factor_value': np.nan
                        })

                    # 做空组合：新卖出的股票
                    for stock in current_short_set - previous_short_stocks:
                        if stock in short_stocks_data and stock in short_weights:
                            price = short_stocks_data[stock][0]
                            # 修复：使用MultiIndex查询因子值
                            if (date, stock) in current_factors.index:
                                factor_val = current_factors.loc[(date, stock)]
                            else:
                                factor_val = np.nan
                            trade_details.append({
                                'date': date,
                                'symbol': stock,
                                'direction': '做空',
                                'action': '卖出',
                                'price': price,
                                'weight': short_weights[stock],
                                'factor_value': factor_val
                            })

                    # 做空组合：平仓的股票
                    for stock in previous_short_stocks - current_short_set:
                        trade_details.append({
                            'date': date,
                            'symbol': stock,
                            'direction': '做空',
                            'action': '平仓',
                            'price': np.nan,
                            'weight': 0,
                            'factor_value': np.nan
                        })

                    # 更新上期持仓
                    previous_long_stocks = current_long_set
                    previous_short_stocks = current_short_set

                    # 计算做多组合收益率（加权）
                    long_ret = sum([
                        weight * (next_p / curr_p - 1)
                        for stock, (curr_p, next_p) in long_stocks_data.items()
                        for stock2, weight in long_weights.items() if stock == stock2
                    ])

                    # 计算做空组合收益率（加权）
                    short_ret = sum([
                        weight * (next_p / curr_p - 1)
                        for stock, (curr_p, next_p) in short_stocks_data.items()
                        for stock2, weight in short_weights.items() if stock == stock2
                    ])

                    # 计算多空组合收益率
                    net_return = long_ret - short_ret - transaction_cost  # 减去交易成本

                    daily_returns.append({'date': date, 'return': net_return, 'long_ret': long_ret, 'short_ret': short_ret})
        
        if not daily_returns:
            print("没有足够的数据进行回测")
            return {'error': 'No data for backtesting'}
        
        # 转换为DataFrame
        returns_df = pd.DataFrame(daily_returns)
        returns_df.set_index('date', inplace=True)

        # 计算累计收益
        returns_df['cumulative_return'] = (1 + returns_df['return']).cumprod()

        # 转换交易明细为DataFrame
        trade_details_df = pd.DataFrame(trade_details)
        if not trade_details_df.empty:
            # 按日期排序
            trade_details_df = trade_details_df.sort_values('date')
            print(f"[DEBUG] 交易明细记录数: {len(trade_details_df)}")
        else:
            print("[WARNING] 没有生成交易明细")

        # 计算基准（如果是市场指数数据）
        # 这里简化处理，使用等权重市场收益作为基准
        returns_series = pd.Series(returns_df['return'])  # 强制转换为Series
        cumulative_returns_series = pd.Series(returns_df['cumulative_return'])  # 强制转换为Series
        results = {
            'returns': returns_df,
            'trade_details': trade_details_df,  # 添加交易明细
            'total_return': returns_series.sum(),
            'annual_return': self._calculate_annual_return(returns_series),
            'volatility': returns_series.std() * np.sqrt(252),  # 年化波动率
            'sharpe_ratio': self._calculate_sharpe_ratio(returns_series),
            'max_drawdown': self._calculate_max_drawdown(cumulative_returns_series),
            'win_rate': self._calculate_win_rate(returns_series),
            'long_short_spread': (returns_df['long_ret'] - returns_df['short_ret']).mean()
        }
        
        print(f"回测完成，总收益: {results['total_return']:.2%}")
        print(f"年化收益: {results['annual_return']:.2%}")
        print(f"夏普比率: {results['sharpe_ratio']:.4f}")
        print(f"最大回撤: {results['max_drawdown']:.2%}")
        
        return results
    
    def backtest_quantile_portfolio(self, 
                                    factor_data: pd.Series, 
                                    price_data: pd.DataFrame, 
                                    n_quantiles: int = 5) -> Dict:
        """
        分层回测 - 将股票按因子值分成N层分别回测
        
        Args:
            factor_data: 因子数据 (Series with MultiIndex)
            price_data: 价格数据 (DataFrame with MultiIndex)
            n_quantiles: 分层数量
            
        Returns:
            Dict: 各层回测结果
        """
        print(f"开始分层回测，分成{n_quantiles}层")
        
        # 按日期分组
        dates = sorted(factor_data.index.get_level_values(0).unique())
        
        # 为每一层创建收益序列
        quantile_returns = {f'Q{i+1}': [] for i in range(n_quantiles)}
        
        for date in dates:
            # 获取当天的因子值
            date_mask = factor_data.index.get_level_values(0) == date
            current_factors = factor_data[date_mask]
            
            if len(current_factors) < n_quantiles:
                continue  # 股票太少，跳过
            
            # 按因子值分层 - 使用rank方法进行分层
            try:
                # 使用rank方法计算分位数排名
                ranks = pd.Series(current_factors).rank(method='min')  # 强制转换为Series再调用rank
                n_items = len(ranks)
                items_per_quantile = max(1, n_items // n_quantiles)
                
                # 根据排名分配到各层
                quantile_labels = []
                for i, (idx, rank_val) in enumerate(ranks.items()):
                    quantile_idx = min(i // items_per_quantile, n_quantiles - 1)
                    quantile_labels.append((idx, quantile_idx))
                
                # 创建分层映射
                quantile_mapping = {idx: q_idx for idx, q_idx in quantile_labels}
                
            except Exception as e:
                print(f"分层计算错误: {e}")
                continue
            
            # 获取当天的价格数据
            date_price_mask = price_data.index.get_level_values(0) == date
            date_prices = price_data[date_price_mask]
            
            # 获取下一天的价格数据来计算收益
            date_idx = dates.index(date)
            if date_idx < len(dates) - 1:
                next_date = dates[date_idx + 1]
                next_date_mask = price_data.index.get_level_values(0) == next_date
                next_prices = price_data[next_date_mask]
                
                # 为每一层计算收益
                for q in range(n_quantiles):
                    # 获取该层的股票
                    q_stocks = [idx for idx, q_idx in quantile_mapping.items() if q_idx == q]
                    
                    # 计算该层股票的平均收益
                    layer_returns = []
                    for stock in q_stocks:
                        # 获取股票代码
                        stock_code = stock[1] if isinstance(stock, tuple) else stock
                        
                        # 获取当前和下一天的价格
                        current_price_data = date_prices[date_prices.index.get_level_values(1) == stock_code]
                        next_price_data = next_prices[next_prices.index.get_level_values(1) == stock_code]
                        
                        if len(current_price_data) > 0 and len(next_price_data) > 0:
                            current_price = pd.Series(current_price_data['close']).iloc[0]  # 强制转换为Series再取值
                            next_price = pd.Series(next_price_data['close']).iloc[0]  # 强制转换为Series再取值
                            
                            if not (np.isnan(current_price) or np.isnan(next_price)):
                                stock_return = next_price / current_price - 1
                                layer_returns.append(stock_return)
                    
                    if layer_returns:
                        avg_layer_return = np.mean(layer_returns)
                        quantile_returns[f'Q{q+1}'].append({'date': date, 'return': avg_layer_return})
        
        # 整理结果
        results = {}
        for q_name, q_returns in quantile_returns.items():
            if q_returns:
                q_df = pd.DataFrame(q_returns)
                q_df.set_index('date', inplace=True)
                q_df['cumulative_return'] = (1 + q_df['return']).cumprod()
                
                returns_subseries = pd.Series(q_df['return'])  # 强制转换为Series
                cumulative_subseries = pd.Series(q_df['cumulative_return'])  # 强制转换为Series
                results[q_name] = {
                    'returns': q_df,
                    'total_return': q_df['return'].sum(),
                    'annual_return': self._calculate_annual_return(returns_subseries),
                    'volatility': returns_subseries.std() * np.sqrt(252),
                    'sharpe_ratio': self._calculate_sharpe_ratio(returns_subseries),
                    'max_drawdown': self._calculate_max_drawdown(cumulative_subseries)
                }
        
        print(f"分层回测完成，共{n_quantiles}层")
        for q_name, q_result in results.items():
            print(f"{q_name}: 年化收益 {q_result['annual_return']:.2%}, "
                  f"夏普比率 {q_result['sharpe_ratio']:.4f}")
        
        return results
    
    def _calculate_annual_return(self, returns: pd.Series) -> float:
        """计算年化收益率"""
        if len(returns) == 0:
            return 0.0
        total_return = (1 + returns).prod() - 1
        years = len(returns) / 252  # 假设每年252个交易日
        if years == 0:
            return 0.0
        return (1 + total_return) ** (1 / years) - 1
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """计算夏普比率"""
        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        if returns.std() == 0:
            return np.inf if excess_returns.mean() > 0 else -np.inf
        return excess_returns.mean() / returns.std() * np.sqrt(252)
    
    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """计算最大回撤"""
        if len(cumulative_returns) == 0:
            return 0.0
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        return drawdown.min()
    
    def _calculate_win_rate(self, returns: pd.Series) -> float:
        """计算胜率"""
        if len(returns) == 0:
            return 0.0
        positive_returns = returns[returns > 0]
        return len(positive_returns) / len(returns)
    
    def generate_performance_report(self, backtest_results: Dict) -> Dict:
        """
        生成绩效报告
        
        Args:
            backtest_results: 回测结果
            
        Returns:
            Dict: 绩效报告
        """
        report = {
            'total_return': backtest_results.get('total_return', np.nan),
            'annual_return': backtest_results.get('annual_return', np.nan),
            'volatility': backtest_results.get('volatility', np.nan),
            'sharpe_ratio': backtest_results.get('sharpe_ratio', np.nan),
            'max_drawdown': backtest_results.get('max_drawdown', np.nan),
            'win_rate': backtest_results.get('win_rate', np.nan),
            'long_short_spread': backtest_results.get('long_short_spread', np.nan)
        }
        
        return report


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ', 
               '002594.SZ', '601318.SH', '601398.SH', '601939.SH', '601328.SH']
    
    # 创建多级索引
    index = pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol'])
    
    # 生成测试数据
    np.random.seed(42)
    
    # 因子数据
    factor_data = pd.Series(
        np.random.randn(len(index)), 
        index=index,
        name='factor'
    )
    
    # 价格数据
    base_price = 100
    price_data_list = []
    for symbol in symbols:
        symbol_index = pd.MultiIndex.from_product([dates, [symbol]], names=['date', 'symbol'])
        # 生成带趋势和噪音的价格序列
        returns = np.random.randn(len(dates)) * 0.02
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        symbol_data = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.randn()/100)) for p in prices],
            'low': [p * (1 - abs(np.random.randn()/100)) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=symbol_index)
        price_data_list.append(symbol_data)
    
    price_data = pd.concat(price_data_list)
    
    print(f"测试数据形状: 因子-{factor_data.shape}, 价格-{price_data.shape}")
    print(f"日期范围: {factor_data.index.get_level_values('date').min()} 到 {factor_data.index.get_level_values('date').max()}")
    
    # 创建回测引擎
    backtester = BacktestEngine()
    
    # 运行多空组合回测
    print("\n=== 多空组合回测 ===")
    ls_results = backtester.backtest_long_short_portfolio(
        factor_data=factor_data,
        price_data=price_data,
        top_quantile=0.2,  # 前20%做多
        bottom_quantile=0.2,  # 后20%做空
        transaction_cost=0.001
    )
    
    if 'error' not in ls_results:
        print(f"多空组合总收益: {ls_results['total_return']:.2%}")
        print(f"多空组合年化收益: {ls_results['annual_return']:.2%}")
        print(f"多空组合夏普比率: {ls_results['sharpe_ratio']:.4f}")
    
    # 运行分层回测
    print("\n=== 分层回测 ===")
    quantile_results = backtester.backtest_quantile_portfolio(
        factor_data=factor_data,
        price_data=price_data,
        n_quantiles=5  # 分成5层
    )
    
    for q_name, q_result in quantile_results.items():
        print(f"{q_name}: 年化收益 {q_result['annual_return']:.2%}, "
              f"夏普比率 {q_result['sharpe_ratio']:.4f}")
    
    print("\n回测测试完成!")