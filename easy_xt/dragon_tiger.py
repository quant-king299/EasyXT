"""
龙虎榜数据模块

提供龙虎榜相关数据查询和分析功能

主要功能：
1. 龙虎榜榜单获取（每日）
2. 机构席位买卖明细
3. 营业部席位排行
4. 龙虎榜统计分析
5. 龙虎榜选股策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class DragonTigerData:
    """龙虎榜数据类"""

    def __init__(self):
        """初始化"""
        self._init_akshare()

    def _init_akshare(self):
        """初始化akshare"""
        try:
            import akshare as ak
            self.ak = ak
            self.ak_available = True
        except ImportError:
            self.ak = None
            self.ak_available = False
            print("[WARNING] 未安装akshare，龙虎榜功能不可用")
            print("[TIPS] 运行: pip install akshare")

    # ============================================================
    # 龙虎榜榜单
    # ============================================================

    def get_daily_list(self, date: str = None) -> pd.DataFrame:
        """
        获取每日龙虎榜

        Args:
            date: 日期，格式 '20240101'，None表示最新

        Returns:
            pd.DataFrame: 龙虎榜数据
            - 代码
            - 名称
            - 原因
            - 当日涨跌幅
            - 当日收盘价
            - 龙虎榜净买入额
            - 龙虎榜买入额
            - 龙虎榜卖出额
            - 市场总成交额
            - 净买入额占总成交比
            - 换手率
            - 日期
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            # 使用东方财富龙虎榜接口（更稳定）
            if date is None:
                # 获取最近3天的数据
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')
                df = self.ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

                # 取最新一天的数据
                if not df.empty and '上榜日' in df.columns:
                    latest_date = df['上榜日'].max()
                    df = df[df['上榜日'] == latest_date]
            else:
                # 获取指定日期的数据（使用前后3天范围）
                target_date = datetime.strptime(date, '%Y%m%d')
                start_date = (target_date - timedelta(days=3)).strftime('%Y%m%d')
                end_date = (target_date + timedelta(days=3)).strftime('%Y%m%d')

                df = self.ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

                # 筛选指定日期
                if not df.empty and '上榜日' in df.columns:
                    df = df[df['上榜日'] == date]

            if not df.empty:
                # 重命名列（根据实际返回的列名进行映射）
                df = df.rename(columns={
                    '代码': 'stock_code',
                    '名称': 'stock_name',
                    '上榜日': 'date',
                    '收盘价': 'close',
                    '涨跌幅': 'change_pct',
                    '龙虎榜净买额': 'net_buy_amount',
                    '龙虎榜买额': 'buy_amount',
                    '龙虎榜卖额': 'sell_amount',
                    '龙虎榜成交额': 'lhb_amount',
                    '市场总成交额': 'total_amount',
                    '净买额占总成交比': 'net_buy_ratio',
                    '换手率': 'turnover',
                    '流通市值': 'circ_mv',
                    '上榜原因': 'reason'
                })

                # 添加完整代码
                df['stock_code_full'] = df['stock_code'].apply(self._convert_to_full_code)

                # 选择需要的列
                required_cols = ['stock_code', 'stock_name', 'date', 'close', 'change_pct',
                                'net_buy_amount', 'buy_amount', 'sell_amount']
                existing_cols = [col for col in required_cols if col in df.columns]
                df = df[existing_cols + [col for col in df.columns if col not in required_cols]]

            return df

        except Exception as e:
            print(f"[ERROR] 获取龙虎榜失败 {date}: {e}")
            return pd.DataFrame()

    def get_stock_history(self, stock_code: str,
                         start_date: str = None,
                         end_date: str = None,
                         count: int = 10) -> pd.DataFrame:
        """
        获取个股历史龙虎榜记录

        Args:
            stock_code: 股票代码，如 '000001.SZ'
            start_date: 开始日期
            end_date: 结束日期
            count: 返回最近N条记录

        Returns:
            pd.DataFrame: 历史龙虎榜记录
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            # 转换代码
            symbol = stock_code.split('.')[0]

            # 设置日期范围
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')

            # 获取区间龙虎榜数据
            df = self.ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

            if df.empty:
                return pd.DataFrame()

            # 筛选指定股票
            if '代码' in df.columns:
                df = df[df['代码'] == symbol].copy()
            else:
                return pd.DataFrame()

            if df.empty:
                return pd.DataFrame()

            # 重命名列
            df = df.rename(columns={
                '代码': 'stock_code',
                '名称': 'stock_name',
                '上榜日': 'date',
                '上榜原因': 'reason',
                '收盘价': 'close',
                '涨跌幅': 'change_pct',
                '龙虎榜净买额': 'net_buy_amount',
                '龙虎榜买额': 'buy_amount',
                '龙虎榜卖额': 'sell_amount'
            })

            # 返回最近N条（按日期降序）
            if 'date' in df.columns:
                df = df.sort_values('date', ascending=False).head(count)

            return df

        except Exception as e:
            print(f"[ERROR] 获取个股历史龙虎榜失败 {stock_code}: {e}")
            return pd.DataFrame()

    def _convert_to_full_code(self, code: str) -> str:
        """转换股票代码为完整格式"""
        if not code:
            return code

        code = str(code).replace('stk', '').replace('.', '')

        if code.startswith('6') or code.startswith('5'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"

    # ============================================================
    # 机构席位
    # ============================================================

    def get_institutional_detail(self, date: str = None) -> pd.DataFrame:
        """
        获取机构席位明细

        Args:
            date: 日期

        Returns:
            pd.DataFrame: 机构席位买卖明细
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            # 获取机构席位明细
            # 使用东方财富机构统计接口
            df = self.ak.stock_lhb_jgzz_sina(symbol='1')  # '1' 表示全部

            if not df.empty and date:
                # 如果指定了日期，筛选数据
                df = df[df['日期'] == date] if '日期' in df.columns else df

            if df.empty:
                return pd.DataFrame()

            # 重命名列
            df = df.rename(columns={
                '代码': 'stock_code',
                '名称': 'stock_name',
                '龙虎榜榜次': 'rank_count',
                '机构买入总额': 'inst_buy_total',
                '机构卖出总额': 'inst_sell_total',
                '机构净买入总额': 'inst_net_buy',
                '机构买入次数': 'inst_buy_count',
                '机构卖出次数': 'inst_sell_count',
                '机构上榜次数': 'inst_list_count',
                '日期': 'date'
            })

            return df

        except Exception as e:
            print(f"[ERROR] 获取机构席位明细失败: {e}")
            return pd.DataFrame()

    def get_institutional_rank(self, date: str = None,
                              top_n: int = 50) -> pd.DataFrame:
        """
        获取机构净买入排行

        Args:
            date: 日期
            top_n: 前N名

        Returns:
            pd.DataFrame: 机构净买入排行
        """
        df = self.get_institutional_detail(date)

        if df.empty:
            return pd.DataFrame()

        # 按机构净买入排序
        df_ranked = df.sort_values('inst_net_buy', ascending=False).head(top_n)

        return df_ranked

    # ============================================================
    # 营业部席位
    # ============================================================

    def get_broker_detail(self, date: str = None) -> pd.DataFrame:
        """
        获取营业部席位明细

        Args:
            date: 日期

        Returns:
            pd.DataFrame: 营业部席位明细
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        try:
            # 获取营业部席位明细
            # 使用东方财富营业部排行接口
            df = self.ak.stock_lhb_yybph_em(symbol='1')  # '1' 表示全部

            if not df.empty and date:
                # 如果指定了日期，筛选数据
                df = df[df['日期'] == date] if '日期' in df.columns else df

            if df.empty:
                return pd.DataFrame()

            # 重命名列
            df = df.rename(columns={
                '营业部名称': 'broker_name',
                '营业部代码': 'broker_code',
                '买入总额': 'buy_total',
                '卖出总额': 'sell_total',
                '净买入总额': 'net_buy_total',
                '买入次数': 'buy_count',
                '卖出次数': 'sell_count',
                '上榜次数': 'list_count',
                '日期': 'date'
            })

            return df

        except Exception as e:
            print(f"[ERROR] 获取营业部席位明细失败: {e}")
            return pd.DataFrame()

    def get_broker_rank(self, date: str = None,
                       by: str = 'net_buy_total',
                       top_n: int = 30) -> pd.DataFrame:
        """
        获取营业部席位排行

        Args:
            date: 日期
            by: 排序字段
            top_n: 前N名

        Returns:
            pd.DataFrame: 营业部排行
        """
        df = self.get_broker_detail(date)

        if df.empty:
            return pd.DataFrame()

        if by not in df.columns:
            print(f"[WARNING] 排序字段 {by} 不存在")
            return pd.DataFrame()

        # 排序
        df_ranked = df.sort_values(by, ascending=False).head(top_n)

        return df_ranked

    # ============================================================
    # 统计分析
    # ============================================================

    def analyze_stock(self, stock_code: str,
                     days: int = 30) -> Dict:
        """
        分析个股龙虎榜统计信息

        Args:
            stock_code: 股票代码
            days: 统计天数

        Returns:
            Dict: 统计信息
        """
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        df = self.get_stock_history(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            count=100
        )

        if df.empty:
            return {}

        result = {
            'stock_code': stock_code,
            'period_days': days,
            'list_count': len(df),
            'total_net_buy': df['net_buy_amount'].sum(),
            'avg_net_buy': df['net_buy_amount'].mean(),
            'total_buy': df['buy_amount'].sum(),
            'total_sell': df['sell_amount'].sum(),
            'avg_change_pct': df['change_pct'].mean(),
            'max_net_buy': df['net_buy_amount'].max(),
            'min_net_buy': df['net_buy_amount'].min(),
            'recent_net_buy': df['net_buy_amount'].iloc[0] if len(df) > 0 else 0
        }

        return result

    def get_hot_seats(self, date: str = None,
                     top_n: int = 20) -> Dict[str, pd.DataFrame]:
        """
        获取热门席位（机构+营业部）

        Args:
            date: 日期
            top_n: 前N名

        Returns:
            Dict: {
                'institutional': 机构席位排行,
                'broker': 营业部席位排行
            }
        """
        result = {}

        try:
            inst_df = self.get_institutional_rank(date, top_n)
            if not inst_df.empty:
                result['institutional'] = inst_df
        except Exception as e:
            print(f"[ERROR] 获取机构席位失败: {e}")

        try:
            broker_df = self.get_broker_rank(date, 'net_buy_total', top_n)
            if not broker_df.empty:
                result['broker'] = broker_df
        except Exception as e:
            print(f"[ERROR] 获取营业部席位失败: {e}")

        return result

    # ============================================================
    # 选股策略
    # ============================================================

    def select_by_institutional(self, date: str = None,
                                min_net_buy: float = 0,
                                top_n: int = 50) -> pd.DataFrame:
        """
        基于机构席位选股

        策略：机构净买入 > min_net_buy

        Args:
            date: 日期
            min_net_buy: 最小净买入额（万元）
            top_n: 前N名

        Returns:
            pd.DataFrame: 选股结果
        """
        df = self.get_institutional_detail(date)

        if df.empty:
            return pd.DataFrame()

        # 筛选条件
        df_filtered = df[df['inst_net_buy'] >= min_net_buy]

        # 排序并取前N名
        df_result = df_filtered.sort_values('inst_net_buy', ascending=False).head(top_n)

        return df_result

    def select_by_continuous(self, stock_pool: List[str] = None,
                            min_count: int = 3,
                            days: int = 30) -> pd.DataFrame:
        """
        选择连续上榜的股票

        策略：N日内上榜次数 >= min_count

        Args:
            stock_pool: 股票池，None表示全市场
            min_count: 最小上榜次数
            days: 统计天数

        Returns:
            pd.DataFrame: 选股结果
        """
        if not self.ak_available:
            raise ImportError("请先安装akshare: pip install akshare")

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        try:
            # 获取期间所有龙虎榜数据
            df = self.ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

            if df.empty:
                return pd.DataFrame()

            # 重命名
            df = df.rename(columns={'代码': 'stock_code', '名称': 'stock_name'})

            # 统计每只股票的上榜次数
            count_df = df.groupby(['stock_code', 'stock_name']).size().reset_index(name='list_count')

            # 筛选连续上榜股票
            count_df = count_df[count_df['list_count'] >= min_count]

            # 排序
            count_df = count_df.sort_values('list_count', ascending=False)

            # 如果指定了股票池，进行筛选
            if stock_pool:
                symbols = [code.split('.')[0] for code in stock_pool]
                count_df = count_df[count_df['stock_code'].isin(symbols)]

            return count_df

        except Exception as e:
            print(f"[ERROR] 选择连续上榜股票失败: {e}")
            return pd.DataFrame()


# ============================================================
# 便捷函数
# ============================================================

def get_daily_dragon_tiger(date: str = None) -> pd.DataFrame:
    """快捷函数：获取每日龙虎榜"""
    dt = DragonTigerData()
    return dt.get_daily_list(date)


def get_institutional_rank(date: str = None, top_n: int = 50) -> pd.DataFrame:
    """快捷函数：获取机构净买入排行"""
    dt = DragonTigerData()
    return dt.get_institutional_rank(date, top_n)


def get_broker_rank(date: str = None, top_n: int = 30) -> pd.DataFrame:
    """快捷函数：获取营业部排行"""
    dt = DragonTigerData()
    return dt.get_broker_rank(date, 'net_buy_total', top_n)


def select_by_institutional(date: str = None,
                            min_net_buy: float = 0,
                            top_n: int = 50) -> pd.DataFrame:
    """快捷函数：基于机构席位选股"""
    dt = DragonTigerData()
    return dt.select_by_institutional(date, min_net_buy, top_n)


if __name__ == "__main__":
    """测试代码"""
    print("=" * 70)
    print("  龙虎榜数据模块测试")
    print("=" * 70)

    dt = DragonTigerData()

    # 测试1: 获取每日龙虎榜
    print("\n[测试1] 获取最新龙虎榜...")
    try:
        df = dt.get_daily_list()
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 只股票上榜")
            print("\n  前5名:")
            print(df.head().to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试2: 机构席位排行
    print("\n[测试2] 获取机构净买入排行...")
    try:
        df = dt.get_institutional_rank(top_n=5)
        if not df.empty:
            print("[OK] 成功!")
            print(df.to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试3: 营业部排行
    print("\n[测试3] 获取营业部净买入排行...")
    try:
        df = dt.get_broker_rank(top_n=5)
        if not df.empty:
            print("[OK] 成功!")
            print(df.to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试4: 个股历史龙虎榜
    print("\n[测试4] 获取个股历史龙虎榜...")
    try:
        df = dt.get_stock_history('000001.SZ', count=10)
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 条记录")
            print(df.to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试5: 基于机构席位选股
    print("\n[测试5] 基于机构席位选股...")
    try:
        df = dt.select_by_institutional(min_net_buy=1000, top_n=10)
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 只股票")
            print(df.head().to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print("  测试完成!")
    print("=" * 70)
