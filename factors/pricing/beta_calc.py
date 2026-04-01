"""
Beta系数计算器

计算个股对定价因子的Beta暴露度。

Beta衡量股票对因子的敏感度：
- beta_mkt: 对市场因子的敏感度
- beta_smb: 对规模因子的敏感度
- beta_hml: 对价值因子的敏感度

使用方法：滚动回归计算Beta系数
- 使用过去N日的数据进行回归
- 标准窗口：60个交易日（约3个月）

参考：
- Fama, E. F., & French, K. R. (1992). The cross-section of expected stock returns.

使用示例：
>>> from factors.pricing import BetaCalculator
>>> calc = BetaCalculator(data_manager)
>>> beta = calc.calculate_stock_beta('000001.SZ', '2024-01-15', window=60)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Union
from datetime import datetime, timedelta
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class BetaCalculator:
    """
    个股Beta系数计算器

    计算股票对定价因子的Beta暴露度
    """

    def __init__(self, data_manager=None):
        """
        初始化

        参数:
            data_manager: 数据管理器（需要支持获取股票和因子数据）
        """
        self.data_manager = data_manager

    def calculate_stock_beta(self,
                              stock_code: str,
                              trade_date: str,
                              window: int = 60,
                              pricing_factors: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        计算个股的Beta系数

        参数:
            stock_code: 股票代码 '000001.SZ'
            trade_date: 计算日期 '2024-01-15'
            window: 回归窗口（交易日数）
            pricing_factors: 定价因子时间序列（可选）

        返回:
            dict: {
                'beta_mkt': 市场Beta,
                'beta_smb': 规模Beta,
                'beta_hml': 价值Beta,
                'alpha': 截距项（Alpha）,
                'r_squared': 拟合优度,
                'n_obs': 观测值数量
            }
        """
        if self.data_manager is None:
            raise ValueError("需要data_manager来获取数据")

        # 1. 获取个股历史收益率
        stock_returns = self._get_stock_returns(stock_code, trade_date, window)

        if stock_returns is None or len(stock_returns) < 20:
            return {
                'beta_mkt': np.nan,
                'beta_smb': np.nan,
                'beta_hml': np.nan,
                'alpha': np.nan,
                'r_squared': np.nan,
                'n_obs': 0
            }

        # 2. 获取定价因子历史数据
        if pricing_factors is None:
            pricing_factors = self._get_pricing_factors(trade_date, window)

        if pricing_factors is None or pricing_factors.empty:
            return {
                'beta_mkt': np.nan,
                'beta_smb': np.nan,
                'beta_hml': np.nan,
                'alpha': np.nan,
                'r_squared': np.nan,
                'n_obs': 0
            }

        # 3. 对齐数据
        merged_data = pd.merge(
            stock_returns.to_frame('stock_return'),
            pricing_factors,
            left_index=True,
            right_index=True,
            how='inner'
        )

        if len(merged_data) < 20:  # 至少需要20个观测值
            return {
                'beta_mkt': np.nan,
                'beta_smb': np.nan,
                'beta_hml': np.nan,
                'alpha': np.nan,
                'r_squared': np.nan,
                'n_obs': 0
            }

        # 4. 执行回归分析
        try:
            # 准备数据
            y = merged_data['stock_return'].values
            X = merged_data[['MKT', 'SMB', 'HML']].values

            # 添加常数项（截距）
            X = sm.add_constant(X)

            # 执行OLS回归
            import statsmodels.api as sm
            model = sm.OLS(y, X, missing='drop').fit()

            # 提取结果
            results = {
                'alpha': model.params[0],  # 截距项
                'beta_mkt': model.params[1],  # MKT系数
                'beta_smb': model.params[2],  # SMB系数
                'beta_hml': model.params[3],  # HML系数
                'r_squared': model.rsquared,  # 拟合优度
                'n_obs': int(model.nobs)  # 观测值数量
            }

            # 添加t统计量和p值
            results['alpha_tstat'] = model.tvalues[0]
            results['alpha_pvalue'] = model.pvalues[0]
            results['beta_mkt_tstat'] = model.tvalues[1]
            results['beta_smb_tstat'] = model.tvalues[2]
            results['beta_hml_tstat'] = model.tvalues[3]

            return results

        except ImportError:
            # 如果没有statsmodels，使用scipy简化回归
            return self._simple_regression(merged_data)

        except Exception as e:
            print(f"[WARNING] {stock_code} Beta计算失败: {e}")
            return {
                'beta_mkt': np.nan,
                'beta_smb': np.nan,
                'beta_hml': np.nan,
                'alpha': np.nan,
                'r_squared': np.nan,
                'n_obs': 0
            }

    def _simple_regression(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        使用scipy进行简化回归（当statsmodels不可用时）

        参数:
            data: 包含stock_return和定价因子的DataFrame

        返回:
            dict: 回归结果
        """
        y = data['stock_return'].values
        x_mkt = data['MKT'].values
        x_smb = data['SMB'].values
        x_hml = data['HML'].values

        # 单独回归每个因子（简化版本）
        beta_mkt, _, r_mkt, _, _ = stats.linregress(x_mkt, y)
        beta_smb, _, r_smb, _, _ = stats.linregress(x_smb, y)
        beta_hml, _, r_hml, _, _ = stats.linregress(x_hml, y)

        # 简化的alpha（使用市场回归的截距）
        alpha = y.mean() - beta_mkt * x_mkt.mean()

        # 简化的R²
        r_squared = r_mkt ** 2

        return {
            'alpha': alpha,
            'beta_mkt': beta_mkt,
            'beta_smb': beta_smb,
            'beta_hml': beta_hml,
            'r_squared': r_squared,
            'n_obs': len(y)
        }

    def _get_stock_returns(self,
                            stock_code: str,
                            trade_date: str,
                            window: int) -> Optional[pd.Series]:
        """
        获取个股历史收益率

        参数:
            stock_code: 股票代码
            trade_date: 当前日期
            window: 窗口大小

        返回:
            pd.Series: 收益率序列
        """
        if self.data_manager is None:
            return None

        try:
            # 计算开始日期
            end_dt = datetime.strptime(trade_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=window * 2)  # 考虑非交易日
            start_date = start_dt.strftime('%Y-%m-%d')

            # 获取价格数据
            if hasattr(self.data_manager, 'get_market_data'):
                df = self.data_manager.get_market_data(
                    stock_list=[stock_code],
                    start_date=start_date,
                    end_date=trade_date
                )

                if df.empty:
                    return None

                # 计算收益率
                df = df.sort_values('date')
                df['return'] = df['close'].pct_change()

                # 取最后window个交易日
                returns = df['return'].dropna().tail(window)

                return returns

            else:
                return None

        except Exception as e:
            print(f"[WARNING] 获取{stock_code}收益率失败: {e}")
            return None

    def _get_pricing_factors(self,
                              trade_date: str,
                              window: int) -> Optional[pd.DataFrame]:
        """
        获取定价因子历史数据

        参数:
            trade_date: 当前日期
            window: 窗口大小

        返回:
            pd.DataFrame: 定价因子时间序列
        """
        if self.data_manager is None:
            return None

        try:
            # 计算开始日期
            end_dt = datetime.strptime(trade_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=window * 2)
            start_date = start_dt.strftime('%Y-%m-%d')

            # 尝试从数据库获取定价因子
            if hasattr(self.data_manager, 'conn'):
                # DuckDBDataReader风格
                query = f"""
                SELECT trade_date, MKT, SMB, HML
                FROM pricing_factors
                WHERE trade_date >= '{start_date}'
                AND trade_date <= '{trade_date}'
                ORDER BY trade_date
                """

                import duckdb
                df = self.data_manager.conn.execute(query).fetchdf()

                if not df.empty:
                    df = df.set_index('trade_date')
                    return df

            return None

        except Exception as e:
            print(f"[WARNING] 获取定价因子失败: {e}")
            return None

    def batch_calculate_beta(self,
                              stock_list: list,
                              trade_date: str,
                              window: int = 60) -> pd.DataFrame:
        """
        批量计算多只股票的Beta系数

        参数:
            stock_list: 股票代码列表
            trade_date: 计算日期
            window: 回归窗口

        返回:
            pd.DataFrame: Beta系数表
        """
        results = []

        for stock_code in stock_list:
            try:
                beta = self.calculate_stock_beta(stock_code, trade_date, window)
                beta['stock_code'] = stock_code
                beta['trade_date'] = trade_date
                results.append(beta)

            except Exception as e:
                print(f"[WARNING] {stock_code} Beta计算失败: {e}")
                continue

        if results:
            return pd.DataFrame(results)
        else:
            return pd.DataFrame()


# ============================================================
# 便捷函数
# ============================================================

def calculate_stock_beta(stock_code: str,
                          trade_date: str,
                          data_manager,
                          window: int = 60) -> Dict[str, float]:
    """
    便捷函数：计算个股Beta系数

    参数:
        stock_code: 股票代码
        trade_date: 交易日期
        data_manager: 数据管理器
        window: 回归窗口

    返回:
        dict: Beta系数
    """
    calc = BetaCalculator(data_manager)
    return calc.calculate_stock_beta(stock_code, trade_date, window)


if __name__ == "__main__":
    print("=" * 70)
    print(" " * 25 + "Beta系数计算器")
    print("=" * 70)

    print("\n[功能说明]")
    print("- beta_mkt: 对市场因子的敏感度（>1表示进攻型，<1表示防御型）")
    print("- beta_smb: 对规模因子的敏感度（>0表示偏向小盘股）")
    print("- beta_hml: 对价值因子的敏感度（>0表示偏向价值股）")
    print("- alpha: 回归截距（超额收益）")
    print("- r_squared: 拟合优度（越接近1解释力越强）")

    print("\n[使用示例]")
    print("""
    from factors.pricing import BetaCalculator

    calc = BetaCalculator(data_manager)

    # 计算单只股票的Beta
    beta = calc.calculate_stock_beta('000001.SZ', '2024-01-15', window=60)
    print(beta)

    # 批量计算
    stock_list = ['000001.SZ', '000002.SZ', '600000.SH']
    beta_df = calc.batch_calculate_beta(stock_list, '2024-01-15')
    print(beta_df)
    """)

    print("\n[依赖]")
    print("- statsmodels（推荐）：完整的回归统计")
    print("- scipy（备选）：简化的回归计算")

    print("\n" + "=" * 70)
