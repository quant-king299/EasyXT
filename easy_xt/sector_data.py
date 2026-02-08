"""
板块数据模块

提供板块相关的数据查询功能，包括：
1. 行业板块
2. 概念板块
3. 地域板块

功能：
- 获取板块列表
- 获取板块成分股
- 获取板块涨跌幅排行
- 获取板块资金流向
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


class SectorData:
    """板块数据类"""

    def __init__(self):
        """初始化"""
        self._init_akshare()
        self._sector_cache = {}

    def _init_akshare(self):
        """初始化akshare"""
        try:
            import akshare as ak
            self.ak = ak
            self.ak_available = True
        except ImportError:
            self.ak = None
            self.ak_available = False
            print("[WARNING] 未安装akshare，板块数据功能不可用")
            print("[TIPS] 运行: pip install akshare")

    # ============================================================
    # 板块列表
    # ============================================================

    def get_industry_sectors(self) -> pd.DataFrame:
        """
        获取行业板块列表

        Returns:
            pd.DataFrame: 行业板块列表
            - 板块名称
            - 板块代码
            - 最新价
            - 涨跌幅
            - 成交量
            - 成交额
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            # 获取行业板块
            df = self.ak.stock_board_industry_name_em()

            # 重命名列
            df = df.rename(columns={
                '板块名称': 'sector_name',
                '最新价': 'latest_price',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '成交量': 'volume',
                '成交额': 'amount',
                '主力净流入': 'net_flow_main',
                '涨跌家数': 'up_down_count',
                '领涨股票': 'leading_stock',
                '更新时间': 'update_time'
            })

            self._sector_cache['industry'] = df
            return df

        except Exception as e:
            print(f"[ERROR] 获取行业板块失败: {e}")
            return pd.DataFrame()

    def get_concept_sectors(self) -> pd.DataFrame:
        """
        获取概念板块列表

        Returns:
            pd.DataFrame: 概念板块列表
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            # 获取概念板块
            df = self.ak.stock_board_concept_name_em()

            # 重命名列
            df = df.rename(columns={
                '板块名称': 'sector_name',
                '最新价': 'latest_price',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '成交量': 'volume',
                '成交额': 'amount',
                '主力净流入': 'net_flow_main',
                '涨跌家数': 'up_down_count',
                '领涨股票': 'leading_stock',
                '更新时间': 'update_time'
            })

            self._sector_cache['concept'] = df
            return df

        except Exception as e:
            print(f"[ERROR] 获取概念板块失败: {e}")
            return pd.DataFrame()

    def get_all_sectors(self) -> Dict[str, pd.DataFrame]:
        """
        获取所有板块列表

        Returns:
            Dict: {
                'industry': 行业板块DataFrame,
                'concept': 概念板块DataFrame
            }
        """
        result = {}

        try:
            result['industry'] = self.get_industry_sectors()
        except Exception as e:
            print(f"[ERROR] 获取行业板块失败: {e}")

        try:
            result['concept'] = self.get_concept_sectors()
        except Exception as e:
            print(f"[ERROR] 获取概念板块失败: {e}")

        return result

    # ============================================================
    # 板块成分股
    # ============================================================

    def get_sector_stocks(self, sector_name: str, sector_type: str = 'industry') -> pd.DataFrame:
        """
        获取板块成分股

        Args:
            sector_name: 板块名称，如 "白酒", "人工智能"
            sector_type: 板块类型，'industry' 或 'concept'

        Returns:
            pd.DataFrame: 成分股列表
            - 股票代码
            - 股票名称
            - 最新价
            - 涨跌幅
            - 成交量
            - 成交额
            - 市值
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            if sector_type == 'industry':
                df = self.ak.stock_board_industry_cons_em(symbol=sector_name)
            else:
                df = self.ak.stock_board_concept_cons_em(symbol=sector_name)

            # 重命名列
            df = df.rename(columns={
                '代码': 'stock_code',
                '名称': 'stock_name',
                '最新价': 'latest_price',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '最高': 'high',
                '最低': 'low',
                '今开': 'open',
                '昨收': 'pre_close',
                '换手率': 'turnover',
                '市盈率-动态': 'pe_ratio',
                '市净率': 'pb_ratio'
            })

            # 转换股票代码格式
            df['stock_code_full'] = df['stock_code'].apply(self._convert_to_full_code)

            return df

        except Exception as e:
            print(f"[ERROR] 获取板块成分股失败 {sector_name}: {e}")
            return pd.DataFrame()

    def _convert_to_full_code(self, code: str) -> str:
        """
        转换股票代码为完整格式

        Args:
            code: 股票代码，如 '000001'

        Returns:
            str: 完整代码，如 '000001.SZ'
        """
        if not code:
            return code

        code = code.replace('stk', '')

        if code.startswith('6'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"

    # ============================================================
    # 板块排行
    # ============================================================

    def get_sector_rank(self, sector_type: str = 'industry',
                       by: str = 'change_pct',
                       ascending: bool = False,
                       top_n: int = 50) -> pd.DataFrame:
        """
        获取板块排行

        Args:
            sector_type: 板块类型，'industry' 或 'concept'
            by: 排序字段，可选：
                - 'change_pct': 涨跌幅（默认）
                - 'amount': 成交额
                - 'net_flow_main': 主力净流入
                - 'volume': 成交量
            ascending: 是否升序，默认False（降序）
            top_n: 返回前N个，默认50

        Returns:
            pd.DataFrame: 排行榜
        """
        if sector_type == 'industry':
            df = self.get_industry_sectors()
        else:
            df = self.get_concept_sectors()

        if df.empty:
            return pd.DataFrame()

        # 过滤有效数据
        if by not in df.columns:
            print(f"[WARNING] 排序字段 {by} 不存在，可用字段: {list(df.columns)}")
            return pd.DataFrame()

        # 排序
        df_sorted = df.sort_values(by=by, ascending=ascending).head(top_n)

        # 添加排名
        df_sorted = df_sorted.reset_index(drop=True)
        df_sorted.index = df_sorted.index + 1
        df_sorted.index.name = 'rank'

        return df_sorted

    def get_top_sectors(self, sector_type: str = 'industry',
                       top_n: int = 10) -> pd.DataFrame:
        """
        获取涨幅榜前N名板块

        Args:
            sector_type: 板块类型
            top_n: 前N名

        Returns:
            pd.DataFrame: 涨幅榜
        """
        return self.get_sector_rank(
            sector_type=sector_type,
            by='change_pct',
            ascending=False,
            top_n=top_n
        )

    def get_bottom_sectors(self, sector_type: str = 'industry',
                          top_n: int = 10) -> pd.DataFrame:
        """
        获取跌幅榜前N名板块

        Args:
            sector_type: 板块类型
            top_n: 前N名

        Returns:
            pd.DataFrame: 跌幅榜
        """
        return self.get_sector_rank(
            sector_type=sector_type,
            by='change_pct',
            ascending=True,
            top_n=top_n
        )

    # ============================================================
    # 板块资金流向
    # ============================================================

    def get_sector_flow_rank(self, sector_type: str = 'industry',
                            top_n: int = 20) -> pd.DataFrame:
        """
        获取板块资金流向排行

        Args:
            sector_type: 板块类型
            top_n: 前N名

        Returns:
            pd.DataFrame: 资金流向排行
        """
        return self.get_sector_rank(
            sector_type=sector_type,
            by='net_flow_main',
            ascending=False,
            top_n=top_n
        )

    # ============================================================
    # 板块历史行情
    # ============================================================

    def get_sector_history(self, sector_name: str,
                          sector_type: str = 'industry',
                          period: str = 'daily',
                          start_date: str = None,
                          end_date: str = None) -> pd.DataFrame:
        """
        获取板块历史行情

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            period: 周期，'daily' 日线, 'weekly' 周线
            start_date: 开始日期，格式 '20240101'
            end_date: 结束日期，格式 '20241231'

        Returns:
            pd.DataFrame: 历史行情
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            if sector_type == 'industry':
                df = self.ak.stock_board_industry_history_em(
                    symbol=sector_name,
                    period=period,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                df = self.ak.stock_board_concept_history_em(
                    symbol=sector_name,
                    period=period,
                    start_date=start_date,
                    end_date=end_date
                )

            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '收盘价': 'close',
                '开盘价': 'open',
                '最高价': 'high',
                '最低价': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '换手率': 'turnover'
            })

            return df

        except Exception as e:
            print(f"[ERROR] 获取板块历史行情失败 {sector_name}: {e}")
            return pd.DataFrame()

    # ============================================================
    # 智能搜索
    # ============================================================

    def search_sector(self, keyword: str, sector_type: str = None) -> Dict[str, pd.DataFrame]:
        """
        搜索板块

        Args:
            keyword: 关键词
            sector_type: 板块类型，None表示搜索所有类型

        Returns:
            Dict: 搜索结果
        """
        result = {}

        if sector_type is None or sector_type == 'industry':
            df_industry = self.get_industry_sectors()
            if not df_industry.empty:
                matched = df_industry[
                    df_industry['sector_name'].str.contains(keyword, na=False)
                ]
                if not matched.empty:
                    result['industry'] = matched

        if sector_type is None or sector_type == 'concept':
            df_concept = self.get_concept_sectors()
            if not df_concept.empty:
                matched = df_concept[
                    df_concept['sector_name'].str.contains(keyword, na=False)
                ]
                if not matched.empty:
                    result['concept'] = matched

        return result


# ============================================================
# 便捷函数
# ============================================================

def get_industry_sectors() -> pd.DataFrame:
    """快捷函数：获取行业板块列表"""
    sd = SectorData()
    return sd.get_industry_sectors()


def get_concept_sectors() -> pd.DataFrame:
    """快捷函数：获取概念板块列表"""
    sd = SectorData()
    return sd.get_concept_sectors()


def get_sector_stocks(sector_name: str, sector_type: str = 'industry') -> pd.DataFrame:
    """快捷函数：获取板块成分股"""
    sd = SectorData()
    return sd.get_sector_stocks(sector_name, sector_type)


def get_top_sectors(sector_type: str = 'industry', top_n: int = 10) -> pd.DataFrame:
    """快捷函数：获取涨幅榜"""
    sd = SectorData()
    return sd.get_top_sectors(sector_type, top_n)


def get_sector_flow_rank(sector_type: str = 'industry', top_n: int = 20) -> pd.DataFrame:
    """快捷函数：获取资金流向排行"""
    sd = SectorData()
    return sd.get_sector_flow_rank(sector_type, top_n)


if __name__ == "__main__":
    """测试代码"""
    print("=" * 70)
    print("  板块数据模块测试")
    print("=" * 70)

    sd = SectorData()

    # 测试1: 获取行业板块列表
    print("\n[测试1] 获取行业板块列表...")
    try:
        df = sd.get_industry_sectors()
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 个行业板块")
            print("\n  前5名:")
            print(df.head().to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试2: 获取涨幅榜
    print("\n[测试2] 获取行业板块涨幅榜...")
    try:
        df = sd.get_top_sectors('industry', top_n=5)
        if not df.empty:
            print("[OK] 成功!")
            print(df.to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试3: 获取板块成分股
    print("\n[测试3] 获取板块成分股（白酒）...")
    try:
        df = sd.get_sector_stocks('白酒', 'industry')
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 只成分股")
            print("\n  前5只:")
            print(df.head().to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试4: 搜索板块
    print("\n[测试4] 搜索板块（关键词：科技）...")
    try:
        result = sd.search_sector('科技')
        print("[OK] 成功!")
        for sector_type, df in result.items():
            print(f"\n  {sector_type} 板块:")
            print(df['sector_name'].tolist())
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print("  测试完成!")
    print("=" * 70)
