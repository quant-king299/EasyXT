"""
量化因子库模块 - EasyFactor (DuckDB增强版)

专注于DuckDB本地数据库的高效批量因子计算

主要功能：
1. DuckDB本地数据库读取
2. 50+类因子计算：技术面、基本面、量价等
3. 批量因子分析：支持多股票、多因子并行计算
4. 综合评分：多因子加权评分
5. 高性能：批量查询优化
6. 扩展模块：资金流向、龙虎榜、板块数据

数据源：
- DuckDB：本地历史数据库，支持批量查询
- 扩展数据源：akshare（资金流向、龙虎榜、板块数据）

作者：EasyXT团队
版本：3.1 (DuckDB增强版)
日期：2026-02-07
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class DuckDBDataReader:
    """DuckDB数据读取器"""

    def __init__(self, duckdb_path: str):
        """
        初始化DuckDB读取器

        参数:
            duckdb_path: DuckDB数据库文件路径
        """
        self.duckdb_path = duckdb_path
        self.conn = None
        self._connect()

    def _connect(self):
        """连接DuckDB数据库"""
        try:
            import duckdb
            self.conn = duckdb.connect(self.duckdb_path)
            print(f"[OK] 成功连接数据库: {self.duckdb_path}")
        except ImportError:
            print("[ERROR] duckdb未安装，请运行: pip install duckdb")
            raise
        except Exception as e:
            print(f"[ERROR] DuckDB连接失败: {e}")
            raise

    def get_stock_list(self, limit: Optional[int] = None) -> List[str]:
        """
        获取数据库中的股票列表

        参数:
            limit: 限制返回数量，None表示全部

        返回:
            List[str]: 股票代码列表
        """
        if self.conn is None:
            return []

        try:
            sql = "SELECT DISTINCT stock_code FROM stock_daily ORDER BY stock_code"
            if limit:
                sql += f" LIMIT {limit}"

            df = self.conn.execute(sql).fetchdf()
            return df['stock_code'].tolist()
        except Exception as e:
            print(f"[ERROR] 获取股票列表失败: {e}")
            return []

    def get_market_data(self, stock_list: List[str], start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        批量读取市场数据

        参数:
            stock_list: 股票代码列表
            start_date: 开始日期 '2024-01-01'
            end_date: 结束日期 '2024-12-31'

        返回:
            pd.DataFrame: 市场数据
        """
        if self.conn is None:
            return pd.DataFrame()

        try:
            # 构建SQL查询
            stocks_str = "', '".join(stock_list)
            sql = f"""
                SELECT * FROM stock_daily
                WHERE stock_code IN ('{stocks_str}')
                  AND date >= '{start_date}'
            """

            if end_date:
                sql += f" AND date <= '{end_date}'"

            sql += " ORDER BY stock_code, date"

            # 执行查询
            df = self.conn.execute(sql).fetchdf()

            if not df.empty:
                # 统一列名为小写
                df.columns = [col.lower() for col in df.columns]

            return df

        except Exception as e:
            print(f"[ERROR] 数据查询失败: {e}")
            return pd.DataFrame()

    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票基本信息

        参数:
            stock_code: 股票代码

        返回:
            Dict: 股票信息
        """
        if self.conn is None:
            return None

        try:
            sql = f"""
                SELECT
                    stock_code,
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(*) as data_count
                FROM stock_daily
                WHERE stock_code = '{stock_code}'
                GROUP BY stock_code
            """

            result = self.conn.execute(sql).fetchdf()
            return result.iloc[0].to_dict() if not result.empty else None

        except Exception as e:
            print(f"[ERROR] 查询股票信息失败: {e}")
            return None

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("[INFO] 数据库连接已关闭")


class EasyFactor:
    """
    量化因子库 - EasyFactor (DuckDB增强版)

    基于DuckDB本地数据库的高效批量因子计算系统

    主要功能：
    1. 市场数据获取（日线历史数据）
    2. 50+类因子计算
    3. 批量分析（多股票、多因子）
    4. 综合评分（多因子加权）
    5. 资金流向分析（扩展模块）
    6. 龙虎榜数据（扩展模块）
    7. 板块数据分析（扩展模块）

    使用示例：
    >>> from easy_xt.factor_library import EasyFactor
    >>>
    >>> # 初始化（只需指定数据库路径）
    >>> ef = EasyFactor(duckdb_path='D:/StockData/stock_data.ddb')
    >>>
    >>> # 获取数据
    >>> df = ef.get_market_data_ex('000001.SZ', '20240101', '20241231')
    >>>
    >>> # 计算因子
    >>> momentum = ef.get_factor('000001.SZ', 'momentum_20d', '20240101', '20241231')
    >>>
    >>> # 批量分析
    >>> results = ef.analyze_batch(stock_list, '2024-01-01', '2024-11-30')
    >>>
    >>> # 资金流向（扩展功能）
    >>> flow = ef.get_stock_money_flow('000001.SZ', days=5)
    >>>
    >>> # 龙虎榜（扩展功能）
    >>> dt_list = ef.get_dragon_tiger_list('2024-01-01')
    >>>
    >>> # 板块数据（扩展功能）
    >>> sectors = ef.get_industry_sectors()
    """

    def __init__(self, duckdb_path: str, enable_extended_modules: bool = True):
        """
        初始化EasyFactor

        参数:
            duckdb_path: DuckDB数据库文件路径（必需）
            enable_extended_modules: 是否启用扩展模块（资金流向、龙虎榜、板块数据）
        """
        self.duckdb_path = duckdb_path

        # 初始化DuckDB读取器
        self.duckdb_reader = DuckDBDataReader(duckdb_path)
        self.conn = self.duckdb_reader.conn

        # 因子配置
        self._init_factor_config()

        # 初始化扩展模块（可选）
        self.money_flow_analyzer = None
        self.dragon_tiger_analyzer = None
        self.sector_analyzer = None

        if enable_extended_modules:
            self._init_extended_modules()

    def _init_extended_modules(self):
        """初始化扩展模块"""
        # 初始化资金流向分析器
        try:
            from easy_xt.money_flow import MoneyFlowAnalyzer
            self.money_flow_analyzer = MoneyFlowAnalyzer()
            print("[OK] 资金流向模块已加载")
        except Exception as e:
            print(f"[INFO] 资金流向模块加载失败: {e}")

        # 初始化龙虎榜分析器
        try:
            from easy_xt.dragon_tiger import DragonTigerData
            self.dragon_tiger_analyzer = DragonTigerData()
            print("[OK] 龙虎榜模块已加载")
        except Exception as e:
            print(f"[INFO] 龙虎榜模块加载失败: {e}")

        # 初始化板块数据分析器
        try:
            from easy_xt.sector_data import SectorData
            self.sector_analyzer = SectorData()
            print("[OK] 板块数据模块已加载")
        except Exception as e:
            print(f"[INFO] 板块数据模块加载失败: {e}")

    def _init_factor_config(self):
        """初始化因子配置"""
        # 技术面因子
        self.technical_factors = {
            'momentum': ['momentum_5d', 'momentum_10d', 'momentum_20d', 'momentum_60d'],
            'reversal': ['reversal_short', 'reversal_mid', 'reversal_long'],
            'volatility': ['volatility_20d', 'volatility_60d', 'volatility_120d', 'max_drawdown'],
            'ma_signal': ['ma5_signal', 'ma10_signal', 'ma20_signal', 'ma60_signal'],
            'indicator': ['rsi', 'macd', 'kdj', 'atr', 'obv', 'bollinger'],
            'volume_price': ['volume_ratio', 'turnover_rate', 'amplitude']
        }

        # 基本面因子
        self.fundamental_factors = {
            'value': ['pe_ttm', 'pb', 'ps', 'pcf', 'market_cap'],
            'quality': ['roe', 'roa', 'gross_margin', 'net_margin', 'debt_ratio'],
            'growth': ['revenue_growth', 'profit_growth', 'eps_growth']
        }

    # ============================================================
    # 市场数据接口
    # ============================================================

    def get_market_data_ex(self,
                          stock_code: str,
                          start_time: str,
                          end_time: str,
                          period: str = 'daily',
                          count: int = -1,
                          fuquan: str = 'qfq') -> pd.DataFrame:
        """
        获取市场数据

        参数:
            stock_code: 股票代码 '000001.SZ'
            start_time: 开始时间 '20240101'
            end_time: 结束时间 '20241231'
            period: 周期（仅支持daily）
            count: 数据条数
            fuquan: 复权方式（暂未实现）

        返回:
            pd.DataFrame: 市场数据
        """
        if period != 'daily':
            print("[WARNING] DuckDB仅支持日线数据，period参数已忽略")

        df = self.duckdb_reader.get_market_data(
            stock_list=[stock_code],
            start_date=start_time,
            end_date=end_time
        )

        if not df.empty and count > 0 and len(df) > count:
            df = df.tail(count)

        return df

    # ============================================================
    # 因子计算接口
    # ============================================================

    def get_factor(self,
                  stock_code: str,
                  factor_name: str,
                  start_date: str,
                  end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取单个因子

        参数:
            stock_code: 股票代码
            factor_name: 因子名称
            start_date: 开始日期
            end_date: 结束日期

        返回:
            pd.DataFrame: 因子数据
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 获取市场数据
        df = self.get_market_data_ex(stock_code, start_date, end_date)

        if df.empty:
            return pd.DataFrame()

        # 根据因子名称计算
        try:
            if factor_name.startswith('momentum_'):
                period = int(factor_name.split('_')[1].replace('d', ''))
                return self._calc_momentum(df, period)
            elif factor_name.startswith('reversal_'):
                period_map = {'short': 5, 'mid': 20, 'long': 60}
                period = period_map.get(factor_name.split('_')[1], 20)
                return self._calc_reversal(df, period)
            elif factor_name.startswith('volatility_'):
                period = int(factor_name.split('_')[1].replace('d', ''))
                return self._calc_volatility(df, period)
            elif factor_name.startswith('ma') and 'signal' in factor_name:
                period = int(factor_name.replace('ma', '').replace('_signal', ''))
                return self._calc_ma_signal(df, period)
            elif factor_name == 'rsi':
                return self._calc_rsi(df)
            elif factor_name == 'macd':
                return self._calc_macd(df)
            elif factor_name == 'kdj':
                return self._calc_kdj(df)
            elif factor_name == 'atr':
                return self._calc_atr(df)
            elif factor_name == 'obv':
                return self._calc_obv(df)
            elif factor_name == 'bollinger':
                return self._calc_bollinger(df)
            elif factor_name == 'max_drawdown':
                return self._calc_max_drawdown(df)
            elif factor_name in ['volume_ratio', 'turnover_rate', 'amplitude']:
                return self._calc_volume_price(df, factor_name)
            elif factor_name == 'ma_trend':
                return self._calc_ma_trend(df)
            elif factor_name == 'momentum_vol':
                return self._calc_momentum_volume(df)
            elif factor_name == 'price_volume_trend':
                return self._calc_price_volume_trend(df)
            else:
                print(f"[WARNING] 未知因子: {factor_name}")
                return pd.DataFrame()

        except Exception as e:
            print(f"[ERROR] 计算因子失败 {factor_name}: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def get_factor_batch(self,
                        stock_list: List[str],
                        factor_names: List[str],
                        start_date: str,
                        end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        批量获取因子

        参数:
            stock_list: 股票代码列表
            factor_names: 因子名称列表
            start_date: 开始日期
            end_date: 结束日期

        返回:
            Dict[str, pd.DataFrame]: {factor_name: DataFrame}
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 批量读取所有数据（一次性读取，提高效率）
        all_data = self.duckdb_reader.get_market_data(stock_list, start_date, end_date)

        if all_data.empty:
            return {}

        results = {}

        # 批量计算各个因子
        for factor_name in factor_names:
            factor_dfs = []

            for stock_code in stock_list:
                stock_data = all_data[all_data['stock_code'] == stock_code].copy()

                if stock_data.empty:
                    continue

                try:
                    if factor_name.startswith('momentum_'):
                        period = int(factor_name.split('_')[1].replace('d', ''))
                        df = self._calc_momentum(stock_data, period)
                    elif factor_name.startswith('volatility_'):
                        period = int(factor_name.split('_')[1].replace('d', ''))
                        df = self._calc_volatility(stock_data, period)
                    elif factor_name == 'max_drawdown':
                        df = self._calc_max_drawdown(stock_data)
                    elif factor_name == 'ma_trend':
                        df = self._calc_ma_trend(stock_data)
                    elif factor_name.startswith('ma') and 'signal' in factor_name:
                        period = int(factor_name.replace('ma', '').replace('_signal', ''))
                        df = self._calc_ma_signal(stock_data, period)
                    elif factor_name == 'rsi':
                        df = self._calc_rsi(stock_data)
                    elif factor_name == 'macd':
                        df = self._calc_macd(stock_data)
                    elif factor_name == 'kdj':
                        df = self._calc_kdj(stock_data)
                    elif factor_name == 'atr':
                        df = self._calc_atr(stock_data)
                    elif factor_name == 'obv':
                        df = self._calc_obv(stock_data)
                    elif factor_name == 'bollinger':
                        df = self._calc_bollinger(stock_data)
                    elif factor_name in ['volume_ratio', 'turnover_rate', 'amplitude']:
                        df = self._calc_volume_price(stock_data, factor_name)
                    else:
                        continue

                    if not df.empty:
                        df['stock_code'] = stock_code
                        factor_dfs.append(df)

                except Exception as e:
                    print(f"[WARNING] 计算{stock_code}的{factor_name}失败: {e}")
                    continue

            if factor_dfs:
                results[factor_name] = pd.concat(factor_dfs, ignore_index=True)

        return results

    def get_all_factors(self,
                       stock_code: str,
                       start_date: str,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取所有因子

        参数:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        返回:
            pd.DataFrame: 所有因子数据
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        df_price = self.get_market_data_ex(stock_code, start_date, end_date)

        if df_price.empty:
            return pd.DataFrame()

        dfs = []

        # 计算各类因子
        # 动量
        for period in [5, 10, 20, 60]:
            df_momentum = self._calc_momentum(df_price, period)
            if not df_momentum.empty:
                dfs.append(df_momentum)

        # 反转
        for period, label in [(5, 'short'), (20, 'mid'), (60, 'long')]:
            df_reversal = self._calc_reversal(df_price, period)
            if not df_reversal.empty:
                dfs.append(df_reversal)

        # 波动率
        for period in [20, 60, 120]:
            df_vol = self._calc_volatility(df_price, period)
            if not df_vol.empty:
                dfs.append(df_vol)

        # 最大回撤
        df_dd = self._calc_max_drawdown(df_price)
        if not df_dd.empty:
            dfs.append(df_dd)

        # 均线
        for period in [5, 10, 20, 60]:
            df_ma = self._calc_ma_signal(df_price, period)
            if not df_ma.empty:
                dfs.append(df_ma)

        # 均线趋势
        df_ma_trend = self._calc_ma_trend(df_price)
        if not df_ma_trend.empty:
            dfs.append(df_ma_trend)

        # 技术指标
        for indicator in ['rsi', 'macd', 'kdj', 'atr', 'obv', 'bollinger']:
            df_ind = self._calc_indicator(df_price, indicator)
            if not df_ind.empty:
                dfs.append(df_ind)

        # 量价因子
        for vp_factor in ['volume_ratio', 'turnover_rate', 'amplitude']:
            df_vp = self._calc_volume_price(df_price, vp_factor)
            if not df_vp.empty:
                dfs.append(df_vp)

        if not dfs:
            return pd.DataFrame()

        # 合并所有因子
        result = dfs[0]
        for df in dfs[1:]:
            result = pd.merge(result, df, how='outer', left_index=True, right_index=True)

        return result

    # ============================================================
    # 批量分析（核心功能）
    # ============================================================

    def analyze_batch(self,
                     stock_list: List[str],
                     start_date: str,
                     end_date: Optional[str] = None,
                     factor_types: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        批量分析多只股票（高性能优化版）

        参数:
            stock_list: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            factor_types: 要计算的因子类型
                ['momentum', 'volatility', 'volume_price', 'technical', 'score']
                None表示全部计算

        返回:
            Dict[str, pd.DataFrame]: 分析结果字典
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        if factor_types is None:
            factor_types = ['momentum', 'volatility', 'volume_price', 'technical', 'score']

        # 一次性读取所有数据（关键优化）
        print(f"[批量分析] 正在读取 {len(stock_list)} 只股票的数据...")
        all_data = self.duckdb_reader.get_market_data(stock_list, start_date, end_date)

        if all_data.empty:
            print("[ERROR] 未读取到数据")
            return {}

        results = {}

        # 批量计算各类因子
        if 'momentum' in factor_types:
            print(f"[批量计算] 动量因子...")
            results['momentum'] = self._batch_calc_momentum(all_data)

        if 'volatility' in factor_types:
            print(f"[批量计算] 波动率因子...")
            results['volatility'] = self._batch_calc_volatility(all_data)

        if 'volume_price' in factor_types:
            print(f"[批量计算] 量价因子...")
            results['volume_price'] = self._batch_calc_volume_price(all_data)

        if 'technical' in factor_types:
            print(f"[批量计算] 技术指标...")
            results['technical'] = self._batch_calc_technical(all_data)

        if 'score' in factor_types:
            print(f"[批量计算] 综合评分...")
            results['score'] = self._batch_calc_score(all_data, results)

        print(f"[OK] 批量分析完成！")
        return results

    # ============================================================
    # 综合评分
    # ============================================================

    def get_comprehensive_score(self,
                               stock_list: List[str],
                               date: Optional[str] = None) -> pd.DataFrame:
        """
        获取综合评分（批量分析）

        参数:
            stock_list: 股票代码列表
            date: 评分日期，默认为最近交易日

        返回:
            pd.DataFrame: 综合评分
                - score: 综合得分
                - max_score: 最高得分
                - rating: 评级 (A/B/C/D)
        """
        if date is None:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')

        # 使用批量分析（需要计算所有因子才能得出综合评分）
        results = self.analyze_batch(stock_list, start_date, date, factor_types=None)

        return results.get('score', pd.DataFrame())

    # ============================================================
    # 基础信息
    # ============================================================

    def get_stock_list(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        获取股票列表

        参数:
            limit: 限制返回数量

        返回:
            pd.DataFrame: 股票列表
        """
        stock_codes = self.duckdb_reader.get_stock_list(limit=limit)
        return pd.DataFrame({'stock_code': stock_codes})

    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票信息

        参数:
            stock_code: 股票代码

        返回:
            Dict: 股票信息
        """
        return self.duckdb_reader.get_stock_info(stock_code)

    # ============================================================
    # 因子计算辅助函数
    # ============================================================

    def _calc_momentum(self, data: pd.DataFrame, period: int) -> pd.DataFrame:
        """计算动量因子"""
        if len(data) < period + 1:
            return pd.DataFrame()

        close_col = 'close'
        recent_close = data[close_col].iloc[-1]
        past_close = data[close_col].iloc[-period]
        momentum = (recent_close - past_close) / past_close

        result_df = pd.DataFrame({
            f'momentum_{period}d': [momentum]
        }, index=[data.index[-1]])

        return result_df

    def _calc_reversal(self, data: pd.DataFrame, period: int) -> pd.DataFrame:
        """计算反转因子"""
        momentum_df = self._calc_momentum(data, period)
        if not momentum_df.empty:
            momentum_df.columns = [f'reversal_{period}d']
            momentum_df[f'reversal_{period}d'] = -momentum_df[f'reversal_{period}d']
        return momentum_df

    def _calc_volatility(self, data: pd.DataFrame, period: int) -> pd.DataFrame:
        """计算波动率因子"""
        if len(data) < period:
            return pd.DataFrame()

        close_col = 'close'
        returns = data[close_col].pct_change().tail(period).dropna()
        volatility = returns.std() * np.sqrt(252)

        result_df = pd.DataFrame({
            f'volatility_{period}d': [volatility]
        }, index=[data.index[-1]])

        return result_df

    def _calc_max_drawdown(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算最大回撤"""
        if len(data) < 20:
            return pd.DataFrame()

        close_col = 'close'
        recent_data = data.tail(120)

        cummax = recent_data[close_col].cummax()
        drawdown = (recent_data[close_col] - cummax) / cummax
        max_dd = drawdown.min()

        result_df = pd.DataFrame({
            'max_drawdown': [max_dd]
        }, index=[data.index[-1]])

        return result_df

    def _calc_ma_signal(self, data: pd.DataFrame, period: int) -> pd.DataFrame:
        """计算均线信号因子"""
        if len(data) < period:
            return pd.DataFrame()

        close_col = 'close'
        ma = data[close_col].tail(period).mean()
        current_price = data[close_col].iloc[-1]
        signal = 1 if current_price > ma else 0

        result_df = pd.DataFrame({
            f'ma{period}_signal': [signal]
        }, index=[data.index[-1]])

        return result_df

    def _calc_ma_trend(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算均线趋势"""
        if len(data) < 60:
            return pd.DataFrame()

        close_col = 'close'
        ma20 = data[close_col].tail(20).mean()
        ma60 = data[close_col].tail(60).mean()

        result_df = pd.DataFrame({
            'ma_trend': [1 if ma20 > ma60 else 0]
        }, index=[data.index[-1]])

        return result_df

    def _calc_momentum_volume(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算量价动量"""
        if len(data) < 20:
            return pd.DataFrame()

        close_col = 'close'
        vol_col = 'volume'

        price_momentum = data[close_col].iloc[-1] / data[close_col].iloc[-20] - 1
        volume_momentum = data[vol_col].iloc[-1] / data[vol_col].iloc[-20] - 1

        result_df = pd.DataFrame({
            'momentum_vol': [price_momentum * volume_momentum]
        }, index=[data.index[-1]])

        return result_df

    def _calc_indicator(self, data: pd.DataFrame, indicator: str) -> pd.DataFrame:
        """计算技术指标"""
        calc_func = getattr(self, f'_calc_{indicator}', None)
        if calc_func:
            return calc_func(data)
        else:
            return pd.DataFrame()

    def _calc_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算RSI"""
        if len(data) < period:
            return pd.DataFrame()

        close_col = 'close'
        price_changes = data[close_col].diff().tail(period)
        gains = price_changes.where(price_changes > 0, 0).mean()
        losses = -price_changes.where(price_changes < 0, 0).mean()

        if losses == 0:
            rsi = 100
        else:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))

        result_df = pd.DataFrame({'rsi': [rsi]}, index=[data.index[-1]])
        return result_df

    def _calc_macd(self, data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """计算MACD"""
        if len(data) < slow:
            return pd.DataFrame()

        close_col = 'close'
        ema_fast = data[close_col].ewm(span=fast, adjust=False).mean()
        ema_slow = data[close_col].ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = (dif - dea) * 2

        result_df = pd.DataFrame({'macd': [macd_hist.iloc[-1]]}, index=[data.index[-1]])
        return result_df

    def _calc_kdj(self, data: pd.DataFrame, n: int = 9) -> pd.DataFrame:
        """计算KDJ"""
        if len(data) < n:
            return pd.DataFrame()

        close_col = 'close'
        low_col = 'low'
        high_col = 'high'

        low_n = data[low_col].tail(n).min()
        high_n = data[high_col].tail(n).max()
        close = data[close_col].iloc[-1]

        if high_n == low_n:
            rsv = 50
        else:
            rsv = (close - low_n) / (high_n - low_n) * 100

        k = rsv * 1/3 + 50 * 2/3

        result_df = pd.DataFrame({'kdj': [k]}, index=[data.index[-1]])
        return result_df

    def _calc_atr(self, data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算ATR"""
        if len(data) < period + 1:
            return pd.DataFrame()

        high_col = 'high'
        low_col = 'low'
        close_col = 'close'

        high_low = data[high_col] - data[low_col]
        high_close = np.abs(data[high_col] - data[close_col].shift())
        low_close = np.abs(data[low_col] - data[close_col].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.tail(period).mean()

        result_df = pd.DataFrame({'atr': [atr]}, index=[data.index[-1]])
        return result_df

    def _calc_obv(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算OBV"""
        if len(data) < 2:
            return pd.DataFrame()

        close_col = 'close'
        vol_col = 'volume'

        obv = (np.sign(data[close_col].diff()) * data[vol_col]).fillna(0).cumsum()
        obv_value = obv.iloc[-1]

        result_df = pd.DataFrame({'obv': [obv_value]}, index=[data.index[-1]])
        return result_df

    def _calc_bollinger(self, data: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """计算布林带"""
        if len(data) < period:
            return pd.DataFrame()

        close_col = 'close'
        sma = data[close_col].tail(period).mean()
        std = data[close_col].tail(period).std()
        upper = sma + 2 * std
        lower = sma - 2 * std

        current_price = data[close_col].iloc[-1]
        bb_position = (current_price - lower) / (upper - lower)

        result_df = pd.DataFrame({'bollinger': [bb_position]}, index=[data.index[-1]])
        return result_df

    def _calc_volume_price(self, data: pd.DataFrame, factor_name: str) -> pd.DataFrame:
        """计算量价因子"""
        if len(data) < 20:
            return pd.DataFrame()

        result = {}
        vol_col = 'volume'

        if factor_name == 'volume_ratio':
            avg_volume = data[vol_col].tail(20).mean()
            recent_volume = data[vol_col].iloc[-1]
            result['volume_ratio'] = recent_volume / avg_volume if avg_volume > 0 else 0

        elif factor_name == 'turnover_rate':
            if 'amount' in data.columns and 'volume' in data.columns:
                amount_col = 'amount'
                avg_turnover = (data[amount_col].tail(20) / data[vol_col].tail(20)).mean()
                result['turnover_rate'] = avg_turnover
            else:
                result['turnover_rate'] = 0

        elif factor_name == 'amplitude':
            high_col = 'high'
            low_col = 'low'
            recent = data.tail(20)
            amplitude = (recent[high_col] - recent[low_col]) / recent[low_col]
            result['amplitude'] = amplitude.mean()

        result_df = pd.DataFrame(result, index=[data.index[-1]])
        return result_df

    def _calc_price_volume_trend(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算价量趋势"""
        if len(data) < 10:
            return pd.DataFrame()

        close_col = 'close'
        vol_col = 'volume'

        price_trend = 1 if data[close_col].iloc[-1] > data[close_col].iloc[-10] else 0
        vol_trend = 1 if data[vol_col].iloc[-1] > data[vol_col].iloc[-10] else 0

        result_df = pd.DataFrame({
            'price_volume_trend': [1 if price_trend == vol_trend else -1]
        }, index=[data.index[-1]])

        return result_df

    # ============================================================
    # 批量计算函数（DuckDB优化版）
    # ============================================================

    def _batch_calc_momentum(self, data: pd.DataFrame) -> pd.DataFrame:
        """批量计算动量因子"""
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                recent_close = stock_data['close'].iloc[-1]

                for period in [5, 10, 20, 60]:
                    if len(stock_data) >= period:
                        past_close = stock_data['close'].iloc[-period]
                        momentum = (recent_close - past_close) / past_close * 100

                        results.append({
                            'stock_code': stock,
                            'period': f'{period}日',
                            'momentum_pct': round(momentum, 2),
                            'current_price': round(recent_close, 2)
                        })

        return pd.DataFrame(results)

    def _batch_calc_volatility(self, data: pd.DataFrame) -> pd.DataFrame:
        """批量计算波动率"""
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                recent_data = stock_data.tail(20)
                returns = recent_data['close'].pct_change().dropna()

                if len(returns) > 0:
                    volatility = returns.std() * np.sqrt(252) * 100
                    max_drawdown = self._calc_max_dd_value(recent_data['close'])

                    results.append({
                        'stock_code': stock,
                        'volatility_pct': round(volatility, 2),
                        'max_drawdown_pct': round(max_drawdown, 2),
                        'price_range': round(recent_data['high'].max() / recent_data['low'].min() - 1, 4)
                    })

        return pd.DataFrame(results)

    def _calc_max_dd_value(self, price_series: pd.Series) -> float:
        """计算最大回撤值"""
        cummax = price_series.cummax()
        drawdown = (price_series - cummax) / cummax
        return drawdown.min() * 100

    def _batch_calc_volume_price(self, data: pd.DataFrame) -> pd.DataFrame:
        """批量计算量价因子"""
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20 and 'volume' in stock_data.columns:
                recent_data = stock_data.tail(20)
                avg_volume = recent_data['volume'].mean()
                recent_volume = recent_data['volume'].iloc[-1]
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

                price_change = stock_data['close'].pct_change().iloc[-1]
                volume_change = stock_data['volume'].pct_change().iloc[-1]
                trend = 'positive' if (price_change > 0 and volume_change > 0) or (price_change < 0 and volume_change < 0) else 'negative'

                results.append({
                    'stock_code': stock,
                    'volume_ratio': round(volume_ratio, 2),
                    'trend': trend
                })

        return pd.DataFrame(results)

    def _batch_calc_technical(self, data: pd.DataFrame) -> pd.DataFrame:
        """批量计算技术指标"""
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 60:
                current_price = stock_data['close'].iloc[-1]

                for period in [5, 10, 20, 60]:
                    if len(stock_data) >= period:
                        ma = stock_data['close'].tail(period).mean()

                        results.append({
                            'stock_code': stock,
                            'period': f'MA{period}',
                            'ma_value': round(ma, 2),
                            'price_vs_ma_pct': round((current_price - ma) / ma * 100, 2),
                            'signal': 'above' if current_price > ma else 'below'
                        })

        return pd.DataFrame(results)

    def _batch_calc_score(self, data: pd.DataFrame, factor_results: Dict) -> pd.DataFrame:
        """批量计算综合评分"""
        scores = {}

        momentum = factor_results.get('momentum', pd.DataFrame())
        volatility = factor_results.get('volatility', pd.DataFrame())
        volume_price = factor_results.get('volume_price', pd.DataFrame())
        technical = factor_results.get('technical', pd.DataFrame())

        for stock in data['stock_code'].unique():
            score = 0
            count = 0

            # 动量得分
            if not momentum.empty:
                stock_mom = momentum[momentum['period'] == '20日']
                if not stock_mom.empty and stock in stock_mom['stock_code'].values:
                    mom_val = stock_mom[stock_mom['stock_code'] == stock]['momentum_pct'].iloc[0]
                    score += min(mom_val / 5, 10)
                    count += 1

            # 波动率得分
            if not volatility.empty:
                stock_vol = volatility[volatility['stock_code'] == stock]
                if not stock_vol.empty:
                    vol_val = stock_vol['volatility_pct'].iloc[0]
                    score += max(10 - vol_val / 3, 0)
                    count += 1

            # 量价得分
            if not volume_price.empty:
                stock_vp = volume_price[volume_price['stock_code'] == stock]
                if not stock_vp.empty and stock_vp['trend'].iloc[0] == 'positive':
                    score += 5
                    count += 1

            # 技术指标得分
            if not technical.empty:
                stock_tech = technical[(technical['stock_code'] == stock) & (technical['period'] == 'MA20')]
                if not stock_tech.empty and stock_tech['signal'].iloc[0] == 'above':
                    score += 5
                    count += 1

            # 计算评级
            ratio = score / (count * 10) if count * 10 > 0 else 0
            if ratio > 0.7:
                rating = 'A'
            elif ratio > 0.5:
                rating = 'B'
            elif ratio > 0.3:
                rating = 'C'
            else:
                rating = 'D'

            scores[stock] = {
                'score': round(score, 2),
                'max_score': count * 10,
                'rating': rating
            }

        return pd.DataFrame(scores).T

    # ============================================================
    # 扩展模块：资金流向分析
    # ============================================================

    def get_stock_money_flow(self, stock_code: str, days: int = 5, use_cache: bool = True) -> pd.DataFrame:
        """
        获取个股资金流向

        参数:
            stock_code: 股票代码，如 '000001.SZ'
            days: 历史天数
            use_cache: 是否使用DuckDB缓存，默认True

        返回:
            pd.DataFrame: 资金流向数据
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_stock_money_flow(
                stock_code, days, use_cache=use_cache, duckdb_reader=self.duckdb_reader
            )
        except Exception as e:
            print(f"[ERROR] 获取资金流向失败: {e}")
            return pd.DataFrame()

    def get_sector_money_flow(self, sector_name: str, date: str = None) -> pd.DataFrame:
        """
        获取板块资金流向

        参数:
            sector_name: 板块名称，如 '银行'
            date: 日期 '2024-01-01'

        返回:
            pd.DataFrame: 板块资金流向
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_sector_money_flow(sector_name, date)
        except Exception as e:
            print(f"[ERROR] 获取板块资金流向失败: {e}")
            return pd.DataFrame()

    def get_money_flow_rank(self, stock_pool: List[str] = None,
                           top_n: int = 10,
                           use_cache: bool = True) -> pd.DataFrame:
        """
        获取资金流向排名

        参数:
            stock_pool: 股票池列表
            top_n: 返回前N只
            use_cache: 是否使用DuckDB缓存，默认True

        返回:
            pd.DataFrame: 资金流向排名
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_flow_rank(
                stock_pool, top_n=top_n, duckdb_reader=self.duckdb_reader, use_cache=use_cache
            )
        except Exception as e:
            print(f"[ERROR] 获取资金流向排名失败: {e}")
            return pd.DataFrame()

    def get_ths_industry_money_flow(self, top_n: int = 20, use_cache: bool = True) -> pd.DataFrame:
        """
        获取同花顺行业资金流向

        参数:
            top_n: 返回前N个行业
            use_cache: 是否使用DuckDB缓存，默认True

        返回:
            pd.DataFrame: 行业资金流向数据
            - 行业名称: 行业名称
            - 昨日涨跌: 昨日涨跌幅
            - 行业指数: 指数点位
            - 涨跌幅: 涨跌幅
            - 净流入(万): 主力净流入金额（万元）
            - 上涨家数: 板块内上涨股票数
            - 下跌家数: 板块内下跌股票数
            - 领涨股票: 领涨股票
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_ths_industry_money_flow(
                top_n=top_n, use_cache=use_cache, duckdb_reader=self.duckdb_reader
            )
        except Exception as e:
            print(f"[ERROR] 获取行业资金流向失败: {e}")
            return pd.DataFrame()

    def get_ths_concept_money_flow(self, top_n: int = 20, use_cache: bool = True) -> pd.DataFrame:
        """
        获取同花顺概念资金流向

        参数:
            top_n: 返回前N个概念
            use_cache: 是否使用DuckDB缓存，默认True

        返回:
            pd.DataFrame: 概念资金流向数据
            - 板块名称: 概念名称
            - 昨日涨跌: 昨日涨跌幅
            - 板块指数: 指数点位
            - 涨跌幅: 涨跌幅
            - 净流入(万): 主力净流入金额（万元）
            - 上涨家数: 板块内上涨股票数
            - 下跌家数: 板块内下跌股票数
            - 领涨股票: 领涨股票
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_ths_concept_money_flow(
                top_n=top_n, use_cache=use_cache, duckdb_reader=self.duckdb_reader
            )
        except Exception as e:
            print(f"[ERROR] 获取概念资金流向失败: {e}")
            return pd.DataFrame()

    def update_ths_money_flow(self) -> Dict[str, int]:
        """
        更新同花顺行业/概念资金流向数据到DuckDB

        返回:
            Dict[str, int]: 更新结果
            - industry: 行业数量
            - concept: 概念数量
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return {'industry': 0, 'concept': 0}

        try:
            return self.money_flow_analyzer.update_ths_money_flow(duckdb_reader=self.duckdb_reader)
        except Exception as e:
            print(f"[ERROR] 更新同花顺资金流向失败: {e}")
            return {'industry': 0, 'concept': 0}

    def get_north_money_flow(self, days: int = 30, use_cache: bool = True) -> pd.DataFrame:
        """
        获取北向资金历史流向

        参数:
            days: 历史天数
            use_cache: 是否使用DuckDB缓存，默认True

        返回:
            pd.DataFrame: 北向资金流向历史数据
            - date: 日期
            - net_flow: 净流入金额（亿元）
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_north_money_flow(
                days, use_cache=use_cache, duckdb_reader=self.duckdb_reader
            )
        except Exception as e:
            print(f"[ERROR] 获取北向资金流向失败: {e}")
            return pd.DataFrame()

    def get_north_money_sector(self, top_n: int = 20) -> pd.DataFrame:
        """
        获取北向资金行业流向

        参数:
            top_n: 返回前N个行业

        返回:
            pd.DataFrame: 北向资金行业流向
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_north_money_sector(top_n)
        except Exception as e:
            print(f"[ERROR] 获取北向资金行业流向失败: {e}")
            return pd.DataFrame()

    def get_north_money_stock(self, stock_code: str = None, top_n: int = 20) -> pd.DataFrame:
        """
        获取北向资金个股流向

        参数:
            stock_code: 股票代码，None表示返回全部
            top_n: 返回前N只股票

        返回:
            pd.DataFrame: 北向资金个股流向
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_north_money_stock(stock_code, top_n)
        except Exception as e:
            print(f"[ERROR] 获取北向资金个股流向失败: {e}")
            return pd.DataFrame()

    def get_ths_stock_money_flow(self, stock_code: str = None, top_n: int = 20, use_cache: bool = True) -> pd.DataFrame:
        """
        获取同花顺个股资金流向（全市场或指定股票）

        参数:
            stock_code: 股票代码，None表示返回全市场排行
            top_n: 返回前N只股票（仅当stock_code为None时有效）
            use_cache: 是否使用DuckDB缓存，默认True

        返回:
            pd.DataFrame: 个股资金流向
            - 代码: 股票代码
            - 名称: 股票名称
            - 最新价: 最新价格
            - 涨跌幅: 涨跌幅
            - 换手率: 换手率
            - 净流入(万): 净流入金额（万元）
        """
        if self.money_flow_analyzer is None:
            print("[ERROR] 资金流向模块未加载")
            return pd.DataFrame()

        try:
            return self.money_flow_analyzer.get_ths_stock_money_flow(
                stock_code, top_n, use_cache=use_cache, duckdb_reader=self.duckdb_reader
            )
        except Exception as e:
            print(f"[ERROR] 获取个股资金流向失败: {e}")
            return pd.DataFrame()

    # ============================================================
    # 扩展模块：龙虎榜数据
    # ============================================================

    def get_dragon_tiger_list(self, date: str = None) -> pd.DataFrame:
        """
        获取龙虎榜每日列表

        参数:
            date: 日期 '2024-01-01'

        返回:
            pd.DataFrame: 龙虎榜数据
        """
        if self.dragon_tiger_analyzer is None:
            print("[ERROR] 龙虎榜模块未加载")
            return pd.DataFrame()

        try:
            return self.dragon_tiger_analyzer.get_daily_list(date)
        except Exception as e:
            print(f"[ERROR] 获取龙虎榜失败: {e}")
            return pd.DataFrame()

    def get_stock_dragon_tiger_history(self, stock_code: str,
                                       start_date: str = None,
                                       end_date: str = None) -> pd.DataFrame:
        """
        获取个股龙虎榜历史

        参数:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        返回:
            pd.DataFrame: 龙虎榜历史数据
        """
        if self.dragon_tiger_analyzer is None:
            print("[ERROR] 龙虎榜模块未加载")
            return pd.DataFrame()

        try:
            return self.dragon_tiger_analyzer.get_stock_history(
                stock_code, start_date, end_date
            )
        except Exception as e:
            print(f"[ERROR] 获取龙虎榜历史失败: {e}")
            return pd.DataFrame()

    def get_institutional_detail(self, date: str = None) -> pd.DataFrame:
        """
        获取机构龙虎榜明细

        参数:
            date: 日期

        返回:
            pd.DataFrame: 机构明细
        """
        if self.dragon_tiger_analyzer is None:
            print("[ERROR] 龙虎榜模块未加载")
            return pd.DataFrame()

        try:
            return self.dragon_tiger_analyzer.get_institutional_detail(date)
        except Exception as e:
            print(f"[ERROR] 获取机构明细失败: {e}")
            return pd.DataFrame()

    # ============================================================
    # 扩展模块：板块数据
    # ============================================================

    def get_industry_sectors(self) -> pd.DataFrame:
        """
        获取行业板块列表

        返回:
            pd.DataFrame: 行业板块
        """
        if self.sector_analyzer is None:
            print("[ERROR] 板块数据模块未加载")
            return pd.DataFrame()

        try:
            return self.sector_analyzer.get_industry_sectors()
        except Exception as e:
            print(f"[ERROR] 获取行业板块失败: {e}")
            return pd.DataFrame()

    def get_concept_sectors(self) -> pd.DataFrame:
        """
        获取概念板块列表

        返回:
            pd.DataFrame: 概念板块
        """
        if self.sector_analyzer is None:
            print("[ERROR] 板块数据模块未加载")
            return pd.DataFrame()

        try:
            return self.sector_analyzer.get_concept_sectors()
        except Exception as e:
            print(f"[ERROR] 获取概念板块失败: {e}")
            return pd.DataFrame()

    def get_sector_stocks(self, sector_name: str,
                         sector_type: str = 'industry') -> pd.DataFrame:
        """
        获取板块成分股

        参数:
            sector_name: 板块名称
            sector_type: 板块类型 'industry' 或 'concept'

        返回:
            pd.DataFrame: 成分股列表
        """
        if self.sector_analyzer is None:
            print("[ERROR] 板块数据模块未加载")
            return pd.DataFrame()

        try:
            return self.sector_analyzer.get_sector_stocks(sector_name, sector_type)
        except Exception as e:
            print(f"[ERROR] 获取板块成分股失败: {e}")
            return pd.DataFrame()

    def get_sector_rank(self, sector_type: str = 'industry',
                       top_n: int = 10) -> pd.DataFrame:
        """
        获取板块排名

        参数:
            sector_type: 板块类型 'industry' 或 'concept'
            top_n: 返回前N只

        返回:
            pd.DataFrame: 板块排名
        """
        if self.sector_analyzer is None:
            print("[ERROR] 板块数据模块未加载")
            return pd.DataFrame()

        try:
            return self.sector_analyzer.get_sector_rank(sector_type, top_n)
        except Exception as e:
            print(f"[ERROR] 获取板块排名失败: {e}")
            return pd.DataFrame()


# ============================================================
# 便捷函数
# ============================================================

def create_easy_factor(duckdb_path: str,
                       enable_extended_modules: bool = True) -> EasyFactor:
    """
    创建EasyFactor实例

    参数:
        duckdb_path: DuckDB数据库路径
        enable_extended_modules: 是否启用扩展模块（资金流向、龙虎榜、板块数据）
                                  默认True，设为False可加快初始化速度

    返回:
        EasyFactor: 实例

    示例:
    >>> from easy_xt.factor_library import create_easy_factor
    >>> # 基础版本（仅因子计算）
    >>> ef = create_easy_factor('D:/StockData/stock_data.ddb')
    >>> # 完整版本（包含扩展模块）
    >>> ef = create_easy_factor('D:/StockData/stock_data.ddb', enable_extended_modules=True)
    >>> results = ef.analyze_batch(stock_list, '2024-01-01', '2024-11-30')
    """
    return EasyFactor(duckdb_path=duckdb_path, enable_extended_modules=enable_extended_modules)


# ============================================================
# 向后兼容的别名
# ============================================================

# 保留旧名称，向后兼容
def create_duckdb_factor(duckdb_path: str) -> EasyFactor:
    """创建EasyFactor实例（向后兼容）"""
    return create_easy_factor(duckdb_path)


# ============================================================
# 主程序示例
# ============================================================

if __name__ == "__main__":
    print("=" * 90)
    print(" " * 30 + "EasyFactor v3.0 - DuckDB纯化版")
    print("=" * 90)

    # 示例1：初始化
    print("\n[示例1] 初始化EasyFactor")
    print("-" * 90)
    duckdb_path = r'D:/StockData/stock_data.ddb'

    try:
        ef = create_easy_factor(duckdb_path)
        print("[OK] EasyFactor初始化成功")

        # 示例2：获取股票列表
        print("\n[示例2] 获取股票列表")
        print("-" * 90)
        stocks = ef.get_stock_list(limit=10)
        if not stocks.empty:
            print(f"[OK] 数据库中有 {len(stocks)} 只股票")
            print(f"前5只: {stocks['stock_code'][:5].tolist()}")

        # 示例3：批量分析
        print("\n[示例3] 批量因子分析")
        print("-" * 90)
        stock_list = stocks['stock_code'][:5].tolist()
        results = ef.analyze_batch(stock_list, '2024-01-01', '2024-11-30')

        if 'score' in results and not results['score'].empty:
            print("[OK] 综合评分：")
            print(results['score'].sort_values('score', ascending=False))

    except FileNotFoundError:
        print(f"[INFO] DuckDB数据库不存在: {duckdb_path}")
        print("[提示] 请先创建DuckDB数据库或修改路径")

    print("\n" + "=" * 90)
    print(" " * 35 + "EasyFactor初始化完成")
    print("=" * 90)

    print("\n【使用方法】")
    print("""
    from easy_xt.factor_library import create_easy_factor

    # 初始化
    ef = create_easy_factor('D:/StockData/stock_data.ddb')

    # 获取股票列表
    stocks = ef.get_stock_list(limit=100)

    # 批量分析
    results = ef.analyze_batch(
        stock_list=stocks['stock_code'].tolist(),
        start_date='2024-01-01',
        end_date='2024-11-30'
    )

    # 查看综合评分
    print(results['score'])
    """)
