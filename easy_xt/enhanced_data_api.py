"""
增强数据API - 统一数据接口

整合所有新增的数据模块，提供统一、便捷的数据访问接口

主要功能：
1. 因子数据接口
2. 板块数据接口
3. 资金流向接口
4. 龙虎榜接口
5. 综合选股接口
"""

import pandas as pd
from typing import Dict, List, Optional, Union
from datetime import datetime


class EnhancedDataAPI:
    """增强数据API - 统一数据接口"""

    def __init__(self):
        """初始化所有数据模块"""
        from factor_library import FactorLibrary
        from sector_data import SectorData
        from money_flow import MoneyFlowAnalyzer
        from dragon_tiger import DragonTigerData

        self.factor_lib = FactorLibrary()
        self.sector_data = SectorData()
        self.money_flow = MoneyFlowAnalyzer()
        self.dragon_tiger = DragonTigerData()

        print("[OK] EnhancedDataAPI 初始化成功")
        print("[INFO] 可用模块: factor_library, sector_data, money_flow, dragon_tiger")

    # ============================================================
    # 因子数据接口
    # ============================================================

    def get_factors(self,
                   stock_codes: Union[str, List[str]],
                   factor_types: List[str] = None) -> pd.DataFrame:
        """
        获取多因子数据

        Args:
            stock_codes: 股票代码列表
            factor_types: 因子类型列表
                - 'value': 估值因子
                - 'quality': 质量因子
                - 'growth': 成长因子
                - 'momentum': 动量因子
                - 'reversal': 反转因子
                - 'volatility': 波动率因子
                - 'volume_price': 量价因子
                默认: ['value', 'quality', 'momentum']

        Returns:
            pd.DataFrame: 多因子数据

        Example:
            >>> api = EnhancedDataAPI()
            >>> factors = api.get_factors(['000001.SZ', '600000.SH'],
            ...                          factor_types=['value', 'quality'])
        """
        if factor_types is None:
            factor_types = ['value', 'quality', 'momentum']

        return self.factor_lib.get_all_factors(stock_codes, factor_types)

    def get_value_factors(self, stock_codes: Union[str, List[str]]) -> pd.DataFrame:
        """获取估值因子"""
        return self.factor_lib.get_value_factors(stock_codes)

    def get_quality_factors(self, stock_codes: Union[str, List[str]]) -> pd.DataFrame:
        """获取质量因子"""
        return self.factor_lib.get_quality_factors(stock_codes)

    def get_momentum_factors(self,
                            stock_codes: Union[str, List[str]],
                            periods: List[int] = [5, 20, 60]) -> pd.DataFrame:
        """获取动量因子"""
        return self.factor_lib.get_momentum_factors(stock_codes, periods)

    # ============================================================
    # 板块数据接口
    # ============================================================

    def get_top_sectors(self,
                       sector_type: str = 'industry',
                       top_n: int = 10) -> pd.DataFrame:
        """
        获取板块涨幅榜

        Args:
            sector_type: 板块类型，'industry' 或 'concept'
            top_n: 前N名

        Returns:
            pd.DataFrame: 板块涨幅榜
        """
        return self.sector_data.get_top_sectors(sector_type, top_n)

    def get_sector_stocks(self,
                         sector_name: str,
                         sector_type: str = 'industry') -> pd.DataFrame:
        """
        获取板块成分股

        Args:
            sector_name: 板块名称，如 "白酒", "人工智能"
            sector_type: 板块类型

        Returns:
            pd.DataFrame: 成分股列表
        """
        return self.sector_data.get_sector_stocks(sector_name, sector_type)

    def get_sector_flow_rank(self,
                            sector_type: str = 'industry',
                            top_n: int = 20) -> pd.DataFrame:
        """获取板块资金流向排行"""
        return self.sector_data.get_sector_flow_rank(sector_type, top_n)

    def search_sector(self, keyword: str) -> Dict[str, pd.DataFrame]:
        """搜索板块"""
        return self.sector_data.search_sector(keyword)

    # ============================================================
    # 资金流向接口
    # ============================================================

    def get_stock_money_flow(self,
                            stock_code: str,
                            days: int = 5) -> pd.DataFrame:
        """获取个股资金流向"""
        return self.money_flow.get_stock_money_flow(stock_code, days)

    def get_flow_rank(self,
                     stock_pool: List[str] = None,
                     by: str = 'net_flow_main_5d_sum',
                     top_n: int = 50) -> pd.DataFrame:
        """获取资金流向排行"""
        return self.money_flow.get_flow_rank(stock_pool, by, False, top_n)

    def get_continuous_flow_stocks(self,
                                   days: int = 3,
                                   min_amount: float = 0) -> pd.DataFrame:
        """获取连续净流入股票"""
        return self.money_flow.get_continuous_flow_stocks(days, min_amount)

    def calculate_flow_factors(self,
                              stock_codes: Union[str, List[str]],
                              periods: List[int] = [1, 3, 5, 10]) -> pd.DataFrame:
        """计算资金流向因子"""
        return self.money_flow.calculate_flow_factors(stock_codes, periods)

    # ============================================================
    # 龙虎榜接口
    # ============================================================

    def get_daily_dragon_tiger(self, date: str = None) -> pd.DataFrame:
        """获取每日龙虎榜"""
        return self.dragon_tiger.get_daily_list(date)

    def get_institutional_rank(self,
                              date: str = None,
                              top_n: int = 50) -> pd.DataFrame:
        """获取机构净买入排行"""
        return self.dragon_tiger.get_institutional_rank(date, top_n)

    def get_broker_rank(self,
                       date: str = None,
                       top_n: int = 30) -> pd.DataFrame:
        """获取营业部排行"""
        return self.dragon_tiger.get_broker_rank(date, 'net_buy_total', top_n)

    def select_by_institutional(self,
                               date: str = None,
                               min_net_buy: float = 0,
                               top_n: int = 50) -> pd.DataFrame:
        """基于机构席位选股"""
        return self.dragon_tiger.select_by_institutional(date, min_net_buy, top_n)

    # ============================================================
    # 综合选股策略
    # ============================================================

    def select_stocks_multi_factor(self,
                                   stock_pool: List[str],
                                   factor_types: List[str] = None,
                                   top_n: int = 50) -> pd.DataFrame:
        """
        多因子选股

        Args:
            stock_pool: 股票池
            factor_types: 因子类型
            top_n: 返回前N名

        Returns:
            pd.DataFrame: 选股结果

        Example:
            >>> api = EnhancedDataAPI()
            >>> # 从全A股中选择
            >>> all_stocks = api.get_all_a_stocks()
            >>> result = api.select_stocks_multi_factor(
            ...     stock_pool=all_stocks[:100],
            ...     factor_types=['value', 'quality', 'momentum'],
            ...     top_n=20
            ... )
        """
        # 获取因子数据
        df = self.get_factors(stock_pool, factor_types)

        if df.empty:
            return pd.DataFrame()

        # 简单的多因子打分：对各个因子进行标准化并求和
        score_cols = []

        # 估值因子：越小越好（负相关）
        if 'pe_ratio' in df.columns:
            df['pe_score'] = -df['pe_ratio'].rank(pct=True)
            score_cols.append('pe_score')

        # 质量因子：越大越好
        if 'roe' in df.columns:
            df['roe_score'] = df['roe'].rank(pct=True)
            score_cols.append('roe_score')

        # 动量因子：越大越好
        for col in df.columns:
            if 'momentum_' in col:
                df[f'{col}_score'] = df[col].rank(pct=True)
                score_cols.append(f'{col}_score')

        if score_cols:
            df['total_score'] = df[score_cols].mean(axis=1)
            df_result = df.sort_values('total_score', ascending=False).head(top_n)
            return df_result

        return df.head(top_n)

    def select_stocks_sector_flow(self,
                                 sector_type: str = 'industry',
                                 top_n_sectors: int = 5,
                                 top_n_stocks: int = 10) -> Dict[str, pd.DataFrame]:
        """
        基于板块资金流向选股

        策略：
        1. 选择资金流入最多的前N个板块
        2. 获取这些板块的成分股
        3. 按资金流向排序

        Args:
            sector_type: 板块类型
            top_n_sectors: 前N个板块
            top_n_stocks: 每个板块前N只股票

        Returns:
            Dict: {板块名称: 成分股DataFrame}
        """
        result = {}

        # 1. 获取资金流向排行
        sector_rank = self.get_sector_flow_rank(sector_type, top_n_sectors)

        if sector_rank.empty:
            return result

        # 2. 对每个板块获取成分股
        for _, row in sector_rank.iterrows():
            sector_name = row['sector_name']

            stocks = self.get_sector_stocks(sector_name, sector_type)

            if not stocks.empty:
                # 3. 按涨跌幅或资金流向排序
                stocks_sorted = stocks.sort_values('change_pct', ascending=False).head(top_n_stocks)
                result[sector_name] = stocks_sorted

        return result

    def select_stocks_dragon_tiger(self,
                                  date: str = None,
                                  min_net_buy: float = 1000,
                                  top_n: int = 20) -> pd.DataFrame:
        """
        基于龙虎榜选股（机构席位）

        Args:
            date: 日期
            min_net_buy: 最小机构净买入额
            top_n: 前N名

        Returns:
            pd.DataFrame: 选股结果
        """
        return self.select_by_institutional(date, min_net_buy, top_n)

    # ============================================================
    # 快速分析功能
    # ============================================================

    def quick_analysis(self, stock_code: str) -> Dict:
        """
        快速分析一只股票

        返回该股票的：
        - 基本面因子
        - 技术面因子
        - 资金流向
        - 是否在龙虎榜

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 分析结果
        """
        result = {
            'stock_code': stock_code,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 1. 基本面因子
        try:
            value_factors = self.get_value_factors([stock_code])
            if not value_factors.empty:
                result['value'] = value_factors.iloc[0].to_dict()
        except Exception as e:
            result['value'] = f'获取失败: {e}'

        # 2. 质量因子
        try:
            quality_factors = self.get_quality_factors([stock_code])
            if not quality_factors.empty:
                result['quality'] = quality_factors.iloc[0].to_dict()
        except Exception as e:
            result['quality'] = f'获取失败: {e}'

        # 3. 动量因子
        try:
            momentum_factors = self.get_momentum_factors([stock_code], periods=[5, 20])
            if not momentum_factors.empty:
                result['momentum'] = momentum_factors.iloc[0].to_dict()
        except Exception as e:
            result['momentum'] = f'获取失败: {e}'

        # 4. 资金流向
        try:
            flow = self.get_stock_money_flow(stock_code, days=5)
            if not flow.empty:
                result['money_flow'] = {
                    '5日净流入': flow['net_flow_main'].sum() if 'net_flow_main' in flow else 0
                }
        except Exception as e:
            result['money_flow'] = f'获取失败: {e}'

        # 5. 龙虎榜历史
        try:
            lhb = self.dragon_tiger.get_stock_history(stock_code, count=5)
            if not lhb.empty:
                result['dragon_tiger'] = {
                    'recent_count': len(lhb),
                    'last_date': lhb['date'].iloc[0] if 'date' in lhb else ''
                }
            else:
                result['dragon_tiger'] = '无近期记录'
        except Exception as e:
            result['dragon_tiger'] = f'获取失败: {e}'

        return result


# ============================================================
# 便捷函数
# ============================================================

def create_enhanced_api() -> EnhancedDataAPI:
    """创建增强数据API实例"""
    return EnhancedDataAPI()


# 全局单例
_api_instance = None


def get_api() -> EnhancedDataAPI:
    """获取全局API实例（单例模式）"""
    global _api_instance
    if _api_instance is None:
        _api_instance = EnhancedDataAPI()
    return _api_instance


if __name__ == "__main__":
    """测试代码"""
    print("=" * 70)
    print("  增强数据API测试")
    print("=" * 70)

    # 创建API实例
    api = EnhancedDataAPI()

    # 测试代码
    test_codes = ['000001.SZ', '600000.SH']

    # 测试1: 获取因子
    print("\n[测试1] 获取多因子数据...")
    try:
        factors = api.get_factors(test_codes, ['value', 'momentum'])
        if not factors.empty:
            print("[OK] 成功!")
            print(factors.to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试2: 获取板块涨幅榜
    print("\n[测试2] 获取板块涨幅榜...")
    try:
        sectors = api.get_top_sectors('industry', top_n=5)
        if not sectors.empty:
            print("[OK] 成功!")
            print(sectors.to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试3: 快速分析
    print("\n[测试3] 快速分析股票...")
    try:
        analysis = api.quick_analysis('000001.SZ')
        print("[OK] 成功!")
        for key, value in analysis.items():
            if key not in ['stock_code', 'update_time']:
                print(f"\n  {key}:")
                if isinstance(value, dict):
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"    {value}")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print("  测试完成!")
    print("=" * 70)
