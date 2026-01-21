"""
因子计算基础操作符库
实现WorldQuant 101因子所需的基础操作符
"""
import pandas as pd
import numpy as np
from typing import Union
from scipy.stats import rankdata


def ts_sum(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列求和
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 时间序列求和结果
    """
    return df.rolling(window=window).sum()


def sma(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    简单移动平均
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 简单移动平均结果
    """
    return df.rolling(window=window).mean()


def stddev(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    标准差
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 标准差结果
    """
    return df.rolling(window=window).std()


def correlation(x: pd.DataFrame, y: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    相关系数
    
    Args:
        x: 第一个序列
        y: 第二个序列
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 相关系数结果
    """
    return x.rolling(window=window).corr(y).fillna(0).replace([np.inf, -np.inf], 0)


def covariance(x: pd.DataFrame, y: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    协方差
    
    Args:
        x: 第一个序列
        y: 第二个序列
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 协方差结果
    """
    return x.rolling(window=window).cov(y)


def rolling_rank(na: np.ndarray) -> float:
    """
    滚动排名辅助函数
    
    Args:
        na: 数组
        
    Returns:
        float: 最后一个值的排名
    """
    return rankdata(na, method='min')[-1]


def ts_rank(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列排名
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 时间序列排名结果
    """
    return df.rolling(window).apply(rolling_rank, raw=True)


def ts_min(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列最小值
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 时间序列最小值结果
    """
    return df.rolling(window).min()


def ts_max(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列最大值
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 时间序列最大值结果
    """
    return df.rolling(window).max()


def delta(df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
    """
    差分
    
    Args:
        df: 输入数据
        period: 差分阶数
        
    Returns:
        pd.DataFrame: 差分结果
    """
    return df.diff(periods=period)


def delay(df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
    """
    延迟（滞后）
    
    Args:
        df: 输入数据
        period: 滞后期数
        
    Returns:
        pd.DataFrame: 滞后结果
    """
    return df.shift(periods=period)


def rank(df: pd.DataFrame) -> pd.DataFrame:
    """
    横截面排名（按行排名）
    
    Args:
        df: 输入数据，通常索引为[date, symbol]，列为不同股票在同一天的值
        
    Returns:
        pd.DataFrame: 排名结果（百分比形式）
    """
    # 对于多级索引数据，按日期进行横截面排名
    if isinstance(df.index, pd.MultiIndex):
        # 按第一个级别（日期）进行分组排名
        return df.groupby(level=0).rank(pct=True, method='min')
    else:
        # 如果不是多级索引，按行进行排名
        return df.rank(axis=1, pct=True, method='min')


def scale(df: pd.DataFrame, k: float = 1) -> pd.DataFrame:
    """
    缩放（使绝对值之和等于k）
    
    Args:
        df: 输入数据
        k: 缩放因子
        
    Returns:
        pd.DataFrame: 缩放后的结果
    """
    return df.mul(k).div(np.abs(df).sum(axis=1), axis=0)


def ts_argmax(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列最大值位置
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 最大值位置结果
    """
    return df.rolling(window).apply(np.argmax, raw=True) + 1


def ts_argmin(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列最小值位置
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 最小值位置结果
    """
    return df.rolling(window).apply(np.argmin, raw=True) + 1


def decay_linear(df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
    """
    线性衰减加权移动平均
    
    Args:
        df: 输入数据
        period: 衰减周期
        
    Returns:
        pd.DataFrame: 线性衰减结果
    """
    weights = np.arange(1, period + 1)
    weights = weights / weights.sum()
    
    def linear_decay(x):
        if len(x) < period:
            return np.nan
        return np.sum(weights * x[-period:])
    
    return df.rolling(window=period).apply(linear_decay, raw=True)


def signedpower(df: pd.DataFrame, power: float) -> pd.DataFrame:
    """
    符号幂函数
    
    Args:
        df: 输入数据
        power: 幂次
        
    Returns:
        pd.DataFrame: 符号幂结果
    """
    return np.power(np.abs(df), power) * np.sign(df)


def product(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列乘积
    
    Args:
        df: 输入数据
        window: 时间窗口
        
    Returns:
        pd.DataFrame: 乘积结果
    """
    return df.rolling(window=window).apply(np.prod, raw=True)


def returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算收益率
    
    Args:
        df: 价格数据
        
    Returns:
        pd.DataFrame: 收益率数据
    """
    return df.pct_change()


def sector_industry_exposure(df: pd.DataFrame, classification: str = 'sw_l1') -> pd.DataFrame:
    """
    行业/板块暴露（简化版，实际应用中需要具体的行业分类数据）

    Args:
        df: 因子数据
        classification: 分类标准

    Returns:
        pd.DataFrame: 行业中性化后的数据
    """
    # 这是一个简化版本，实际应用中需要根据股票所属行业进行中性化处理
    # 此处仅作为占位符
    return df


# ==================== Alpha191 新增算子 ====================

def ts_lowday(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列窗口内最小值的位置（从1开始计数）

    Args:
        df: 输入数据
        window: 时间窗口

    Returns:
        pd.DataFrame: 最小值位置结果
    """
    def find_lowday(x):
        if len(x) < window or np.all(np.isnan(x)):
            return np.nan
        # 返回最小值的位置，从末尾开始计数
        return len(x) - np.argmin(x[-window:])

    return df.rolling(window=window).apply(find_lowday, raw=True)


def ts_highday(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列窗口内最大值的位置（从1开始计数）

    Args:
        df: 输入数据
        window: 时间窗口

    Returns:
        pd.DataFrame: 最大值位置结果
    """
    def find_highday(x):
        if len(x) < window or np.all(np.isnan(x)):
            return np.nan
        # 返回最大值的位置，从末尾开始计数
        return len(x) - np.argmax(x[-window:])

    return df.rolling(window=window).apply(find_highday, raw=True)


def wma(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    加权移动平均（指数衰减权重）

    Args:
        df: 输入数据
        window: 时间窗口

    Returns:
        pd.DataFrame: 加权移动平均结果
    """
    # 指数衰减权重：0.9^(window-1), 0.9^(window-2), ..., 0.9^0
    weights = np.array(range(window-1, -1, -1))
    weights = np.power(0.9, weights)
    sum_weights = np.sum(weights)

    def weighted_mean(x):
        if len(x) < window:
            return np.nan
        return np.sum(weights * x[-window:]) / sum_weights

    return df.rolling(window=window).apply(weighted_mean, raw=True)


def count(cond: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列窗口内满足条件的计数

    Args:
        cond: 条件数据（布尔值）
        window: 时间窗口

    Returns:
        pd.DataFrame: 计数结果
    """
    return cond.rolling(window=window).sum()


def sumif(df: pd.DataFrame, window: int = 10, cond: pd.DataFrame = None) -> pd.DataFrame:
    """
    时间序列窗口内条件求和

    Args:
        df: 输入数据
        window: 时间窗口
        cond: 条件（布尔DataFrame）

    Returns:
        pd.DataFrame: 条件求和结果
    """
    if cond is None:
        return df.rolling(window=window).sum()

    # 将不满足条件的值置为0
    masked = df.where(cond, 0)
    return masked.rolling(window=window).sum()


def abs_func(df: pd.DataFrame) -> pd.DataFrame:
    """
    绝对值

    Args:
        df: 输入数据

    Returns:
        pd.DataFrame: 绝对值结果
    """
    return np.abs(df)


def sign_func(df: pd.DataFrame) -> pd.DataFrame:
    """
    符号函数

    Args:
        df: 输入数据

    Returns:
        pd.DataFrame: 符号结果（-1, 0, 1）
    """
    return np.sign(df)


def log_func(df: pd.DataFrame) -> pd.DataFrame:
    """
    自然对数

    Args:
        df: 输入数据

    Returns:
        pd.DataFrame: 对数结果
    """
    return np.log(df.replace(0, np.nan).fillna(1e-10))


def minimum(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """
    两个DataFrame的最小值

    Args:
        df1: 第一个数据
        df2: 第二个数据

    Returns:
        pd.DataFrame: 最小值结果
    """
    return df1.minimum(df2)


def maximum(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """
    两个DataFrame的最大值

    Args:
        df1: 第一个数据
        df2: 第二个数据

    Returns:
        pd.DataFrame: 最大值结果
    """
    return df1.maximum(df2)


def sequence(n: int) -> np.ndarray:
    """
    生成1到n的等差序列

    Args:
        n: 序列长度

    Returns:
        np.ndarray: 序列 [1, 2, ..., n]
    """
    return np.arange(1, n + 1)


def regbeta(df: pd.DataFrame, x: np.ndarray) -> pd.DataFrame:
    """
    线性回归系数（y ~ x的斜率）

    Args:
        df: 因变量（时间序列）
        x: 自变量序列

    Returns:
        pd.DataFrame: 回归系数结果
    """
    window = len(x)

    def calc_beta(y):
        if len(y) < window or np.all(np.isnan(y)):
            return np.nan
        y_valid = y[-window:]
        # 移除NaN值
        mask = ~np.isnan(y_valid)
        if mask.sum() < 2:
            return np.nan
        x_valid = x[mask]
        y_valid = y_valid[mask]
        # 计算回归系数
        if len(x_valid) < 2 or np.std(x_valid) == 0:
            return np.nan
        beta = np.cov(x_valid, y_valid, bias=True)[0, 1] / np.var(x_valid)
        return beta

    return df.rolling(window=window).apply(calc_beta, raw=True)


def sma_ema(df: pd.DataFrame, n: int, m: int) -> pd.DataFrame:
    """
    SMA的指数加权版本（类似于EMA）

    Args:
        df: 输入数据
        n: 总窗口
        m: 平滑参数

    Returns:
        pd.DataFrame: SMA-EMA结果
    """
    # alpha = m/n
    alpha = m / n
    return df.ewm(alpha=alpha, adjust=False).mean()


def ts_prod(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    时间序列乘积

    Args:
        df: 输入数据
        window: 时间窗口

    Returns:
        pd.DataFrame: 乘积结果
    """
    return df.rolling(window=window).apply(lambda x: np.exp(np.sum(np.log(x.replace(0, 1e-10)))) if np.all(x > 0) else np.prod(x), raw=True)


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=20, freq='D')
    symbols = ['A', 'B', 'C']
    
    # 创建多级索引的测试数据
    index = pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol'])
    test_data = pd.DataFrame(
        np.random.randn(60, 1), 
        index=index, 
        columns=['value']
    ).unstack(level=-1)  # 转换为每行为一个日期，每列为一只股票
    
    print("测试数据形状:", test_data.shape)
    print("测试数据:")
    print(test_data.head())
    
    # 测试各种操作符
    print("\n=== 测试操作符 ===")
    
    # 测试ts_sum
    result_ts_sum = ts_sum(test_data, 5)
    print(f"ts_sum结果形状: {result_ts_sum.shape}")
    
    # 测试sma
    result_sma = sma(test_data, 5)
    print(f"sma结果形状: {result_sma.shape}")
    
    # 测试stddev
    result_stddev = stddev(test_data, 5)
    print(f"stddev结果形状: {result_stddev.shape}")
    
    # 测试rank - 使用原数据测试
    original_values = test_data.fillna(0)  # 填充NaN值以便测试
    result_rank = rank(original_values)
    print(f"rank结果形状: {result_rank.shape}")
    print("rank结果示例:")
    print(result_rank.head())
    
    print("\n所有操作符测试完成!")