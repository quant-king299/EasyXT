"""
因子中性化处理模块
实现行业中性、市值中性等处理方法
"""
import pandas as pd
import numpy as np
from typing import Optional, Literal
from sklearn.linear_model import LinearRegression


class FactorNeutralizer:
    """因子中性化处理器"""

    # 申万一级行业分类（简化版，实际应用中需要从数据源获取）
    SW_INDUSTRY_LEVEL1 = {
        '银行': ['601398.SH', '601288.SH', '601939.SH', '601166.SH', '000001.SZ', '600036.SH'],
        '非银金融': ['601318.SH', '601688.SH', '601601.SH', '600030.SH', '600958.SH', '1668.HK'],
        '医药生物': ['000001.SZ', '000002.SZ', '600276.SH'],  # 示例
        '食品饮料': ['600519.SH', '000858.SZ', '000568.SZ'],
        '房地产': ['000002.SZ', '600048.SH', '001979.SZ'],
        '电子': ['000725.SZ', '002415.SZ', '688981.SH'],
        '计算机': ['002415.SZ', '600570.SH', '002405.SZ'],
        '传媒': ['002027.SZ', '300059.SZ', '600037.SH'],
        '通信': ['000063.SZ', '600050.SH', '601728.SH'],
        '电力设备': ['300750.SZ', '688111.SH', '002129.SZ'],
        # ... 更多行业分类
    }

    # 行业代码到名称的映射（反向查找）
    STOCK_INDUSTRY_MAP = {}
    for industry, stocks in SW_INDUSTRY_LEVEL1.items():
        for stock in stocks:
            STOCK_INDUSTRY_MAP[stock] = industry

    @staticmethod
    def get_industry_dummy(stocks: pd.Series) -> pd.DataFrame:
        """
        生成行业哑变量

        Args:
            stocks: 股票代码Series

        Returns:
            DataFrame: 行业哑变量，每行代表一只股票，每列代表一个行业
        """
        # 获取每只股票的行业
        industries = stocks.map(FactorNeutralizer.STOCK_INDUSTRY_MAP)

        # 如果股票没有对应的行业，归类为"其他"
        industries = industries.fillna('其他')

        # 生成哑变量
        dummies = pd.get_dummies(industries, prefix='ind', dtype=float)

        return dummies

    @staticmethod
    def neutralize(factor_data: pd.Series,
                   market_cap: Optional[pd.Series] = None,
                   industry_dummies: Optional[pd.DataFrame] = None,
                   method: Literal['regression', 'orthogonal'] = 'regression') -> pd.Series:
        """
        对因子进行中性化处理

        Args:
            factor_data: 因子数据 (Series with MultiIndex: date, symbol)
            market_cap: 市值数据 (Series with MultiIndex: date, symbol)，用于市值中性
            industry_dummies: 行业哑变量，用于行业中性（如果为None，会自动生成）
            method: 中性化方法
                - 'regression': 线性回归取残差
                - 'orthogonal': 正交化处理（与regression类似，但更高效）

        Returns:
            Series: 中性化后的因子数据

        说明：
            中性化的原理是通过线性回归去除因子中的行业和市值影响：
            1. 行业中性：对每个截面，回归 factor ~ 行业哑变量，取残差
            2. 市值中性：对每个截面，回归 factor ~ log(市值)，取残差
            3. 双中性：对每个截面，回归 factor ~ 行业哑变量 + log(市值)，取残差
        """
        if not isinstance(factor_data.index, pd.MultiIndex):
            raise ValueError("factor_data 必须是 MultiIndex (date, symbol)")

        # 复制原始数据，避免修改
        neutralized_factor = factor_data.copy()

        # 按日期分组处理
        dates = factor_data.index.get_level_values(0).unique()

        for date in dates:
            # 获取当前日期的因子值
            date_mask = factor_data.index.get_level_values(0) == date
            current_factor = factor_data[date_mask]

            if len(current_factor) < 5:  # 样本太少，跳过
                continue

            # 准备回归特征
            X = pd.DataFrame(index=current_factor.index)

            # 添加行业哑变量（如果需要且未提供）
            if industry_dummies is None or True:  # 总是生成行业哑变量
                # 获取当前日期的股票代码
                current_stocks = current_factor.index.get_level_values(1)
                ind_dummies = FactorNeutralizer.get_industry_dummy(current_stocks)
                # 确保索引对齐
                ind_dummies.index = current_factor.index
                X = pd.concat([X, ind_dummies], axis=1)

            # 添加市值特征（对数化）
            if market_cap is not None:
                # 获取当前日期的市值
                current_market_cap = market_cap[date_mask]
                if len(current_market_cap) > 0:
                    # 对数市值，处理异常值
                    log_mc = np.log(current_market_cap.replace(0, np.nan)).fillna(0)
                    X['log_market_cap'] = log_mc

            # 如果没有任何特征，跳过
            if X.empty or X.shape[1] == 0:
                continue

            # 确保没有缺失值
            valid_mask = current_factor.notna()
            X_valid = X[valid_mask]
            y_valid = current_factor[valid_mask]

            if len(y_valid) < 3:  # 样本太少
                continue

            # 方法1: 线性回归取残差
            if method == 'regression':
                model = LinearRegression()
                try:
                    model.fit(X_valid, y_valid)
                    # 预测值
                    y_pred = model.predict(X_valid)
                    # 残差 = 实际值 - 预测值
                    residuals = y_valid - y_pred

                    # 更新中性化后的因子值
                    neutralized_factor.loc[valid_mask] = residuals
                except Exception as e:
                    print(f"[WARNING] 日期 {date} 中性化失败: {e}")
                    continue

            # 方法2: 正交化（使用Gram-Schmidt过程）
            elif method == 'orthogonal':
                try:
                    # 将X和y都标准化
                    X_norm = (X_valid - X_valid.mean()) / (X_valid.std() + 1e-8)
                    y_norm = (y_valid - y_valid.mean()) / (y_valid.std() + 1e-8)

                    # 对每个特征进行正交化
                    y_orthogonal = y_norm.copy()

                    for col in X_norm.columns:
                        feature = X_norm[col].values
                        # 计算投影系数
                        coef = np.dot(y_orthogonal, feature) / np.dot(feature, feature)
                        # 减去投影
                        y_orthogonal = y_orthogonal - coef * feature

                    # 反标准化
                    residuals = y_orthogonal * y_valid.std() + y_valid.mean()
                    neutralized_factor.loc[valid_mask] = residuals
                except Exception as e:
                    print(f"[WARNING] 日期 {date} 正交化失败: {e}")
                    continue

        # 标准化到与原始因子相同的范围
        neutralized_factor = (neutralized_factor - neutralized_factor.mean()) / (neutralized_factor.std() + 1e-8)
        neutralized_factor = neutralized_factor * factor_data.std() + factor_data.mean()

        return neutralized_factor

    @staticmethod
    def neutralize_by_industry(factor_data: pd.Series) -> pd.Series:
        """
        行业中性化

        Args:
            factor_data: 因子数据

        Returns:
            Series: 行业中性化后的因子
        """
        return FactorNeutralizer.neutralize(
            factor_data=factor_data,
            industry_dummies=None,  # 会在函数内部生成
            market_cap=None,
            method='regression'
        )

    @staticmethod
    def neutralize_by_market_cap(factor_data: pd.Series, market_cap: pd.Series) -> pd.Series:
        """
        市值中性化

        Args:
            factor_data: 因子数据
            market_cap: 市值数据

        Returns:
            Series: 市值中性化后的因子
        """
        return FactorNeutralizer.neutralize(
            factor_data=factor_data,
            industry_dummies=None,
            market_cap=market_cap,
            method='regression'
        )

    @staticmethod
    def neutralize_both(factor_data: pd.Series, market_cap: pd.Series) -> pd.Series:
        """
        行业和市值双重中性化

        Args:
            factor_data: 因子数据
            market_cap: 市值数据

        Returns:
            Series: 双重中性化后的因子
        """
        return FactorNeutralizer.neutralize(
            factor_data=factor_data,
            industry_dummies=None,  # 会在函数内部生成
            market_cap=market_cap,
            method='regression'
        )

    @staticmethod
    def add_industry_mapping(market_data: pd.DataFrame) -> pd.DataFrame:
        """
        为市场数据添加行业分类列

        Args:
            market_data: 市场数据 (DataFrame with MultiIndex)

        Returns:
            DataFrame: 添加了'industry'列的数据
        """
        if 'industry' not in market_data.columns:
            # 获取所有股票代码
            symbols = market_data.index.get_level_values(1).unique()

            # 创建行业映射
            symbol_to_industry = pd.Series({
                symbol: FactorNeutralizer.STOCK_INDUSTRY_MAP.get(symbol, '其他')
                for symbol in symbols
            })

            # 添加行业列
            market_data['industry'] = market_data.index.get_level_values(1).map(symbol_to_industry)

        return market_data


def test_neutralization():
    """测试中性化功能"""
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=10, freq='D')
    symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH']

    # 创建MultiIndex
    index = pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol'])

    # 创建因子值（模拟有行业和市值偏差）
    np.random.seed(42)
    factor_values = []

    for date in dates:
        for symbol in symbols:
            # 模拟：银行股因子值偏高
            base_value = np.random.randn()
            if symbol in ['600000.SH', '600036.SH', '601398.SH']:
                base_value += 1.0
            factor_values.append(base_value)

    factor_data = pd.Series(factor_values, index=index, name='factor')

    # 创建市值数据
    market_cap = pd.Series(np.random.uniform(100, 1000, len(index)), index=index)

    print("原始因子统计:")
    print(factor_data.groupby(level=1).mean())

    # 行业中性化
    neutralized_ind = FactorNeutralizer.neutralize_by_industry(factor_data)
    print("\n行业中性后因子统计:")
    print(neutralized_ind.groupby(level=1).mean())

    # 市值中性化
    neutralized_mc = FactorNeutralizer.neutralize_by_market_cap(factor_data, market_cap)
    print("\n市值中性后因子统计:")
    print(neutralized_mc.groupby(level=1).mean())

    # 双重中性化
    neutralized_both = FactorNeutralizer.neutralize_both(factor_data, market_cap)
    print("\n双重中性后因子统计:")
    print(neutralized_both.groupby(level=1).mean())


if __name__ == '__main__':
    test_neutralization()
