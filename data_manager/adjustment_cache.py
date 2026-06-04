#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复权查询模块 - QMT API方案

核心思想：
1. 存储层：只保存原始数据（不复权）
2. 查询层：需要复权时直接调用QMT API
3. 无需本地计算，无需维护分红数据

优势：
- 使用QMT官方复权算法（准确性100%）
- 代码极简，易于维护
- 无需自己实现复权算法

劣势：
- 依赖QMT在线环境
"""

import pandas as pd
import duckdb
from typing import Literal
import warnings

from config.env_config import get_default_db_path

# 复权类型定义
AdjustType = Literal['none', 'front', 'back', 'geometric_front', 'geometric_back']

ADJUST_TYPE_NAMES = {
    'none': '不复权',
    'front': '前复权',
    'back': '后复权',
    'geometric_front': '等比前复权',
    'geometric_back': '等比后复权'
}

# 复权类型映射到QMT的dividend_type参数
ADJUST_TO_QMT_DIVIDEND_TYPE = {
    'none': 'none',               # 不复权
    'front': 'front',             # 前复权
    'back': 'back',               # 后复权
    'geometric_front': 'front_ratio',  # 等比前复权
    'geometric_back': 'back_ratio'     # 等比后复权
}


class AdjustmentCache:
    """
    复权查询管理器（QMT API方案）

    功能：
    1. 不复权：从DuckDB读取原始数据
    2. 需要复权：直接调用QMT API获取
    """

    def __init__(self, duckdb_path: str):
        """
        初始化复权管理器

        Args:
            duckdb_path: DuckDB数据库路径
        """
        self.duckdb_path = duckdb_path
        self.qmt_available = False
        self.xtdata = None
        # 延迟导入xtdata（在使用时才导入）

    def get_adjusted_data(self,
                         stock_code: str,
                         start_date: str,
                         end_date: str,
                         adjust_type: AdjustType,
                         con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        """
        获取复权数据

        降级策略（逐层 fallback）：
        1. 不复权（none）：从DuckDB读取原始数据
        2. QMT 在线 → xtdata.get_market_data_ex(dividend_type=...)
        3. QMT 离线 → tushare adj_factor 自行计算（方案B）
        4. tushare adj_factor 也失败 → tushare pro_bar(adj=...)（方案A）
        5. 全部失败 → DuckDB 原始数据 + warning

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型
            con: DuckDB连接

        Returns:
            复权后的数据
        """
        # 1. 不复权：直接返回原始数据
        if adjust_type == 'none':
            return self._get_raw_data(stock_code, start_date, end_date, con)

        # 2. QMT API（主力方案）
        qmt_data = self._get_from_qmt_api(stock_code, start_date, end_date, adjust_type)
        if not qmt_data.empty:
            return qmt_data

        # 3. tushare 兜底（QMT 离线时）
        print(f"  [INFO] QMT 不可用，尝试 tushare 获取复权数据...")
        tushare_data = self._get_from_tushare_api(stock_code, start_date, end_date, adjust_type)
        if not tushare_data.empty:
            return tushare_data

        # 4. 全部失败：降级到原始数据
        warnings.warn(
            f"QMT 和 tushare 均无法获取复权数据，降级使用原始数据"
            f"（复权类型：{adjust_type}）"
        )
        return self._get_raw_data(stock_code, start_date, end_date, con)

    def _get_raw_data(self,
                     stock_code: str,
                     start_date: str,
                     end_date: str,
                     con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        """从DuckDB获取原始数据"""
        query = f"""
            SELECT
                stock_code, date, period,
                open, high, low, close, volume, amount,
                created_at, updated_at
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """
        df = con.execute(query).df()

        if not df.empty:
            # 输出数据样本用于调试
            sample_close = df['close'].iloc[0] if len(df) > 0 else 'N/A'
            print(f"  [DEBUG] _get_raw_data: 查询股票={stock_code}, 返回{len(df)}条记录, 首日收盘={sample_close}")
            # 验证stock_code列的值
            if 'stock_code' in df.columns:
                unique_codes = df['stock_code'].unique()
                print(f"  [DEBUG] 数据中stock_code列的唯一值: {unique_codes}")
        else:
            print(f"  [DEBUG] _get_raw_data: 查询股票={stock_code}, 返回空数据")

        # 设置date为索引（确保索引类型一致）
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df.index.name = 'date'  # 明确命名索引，确保reset_index()后能正确生成列

        return df

    def _get_from_qmt_api(self,
                         stock_code: str,
                         start_date: str,
                         end_date: str,
                         adjust_type: AdjustType) -> pd.DataFrame:
        """
        从QMT API获取复权数据

        使用xtdata.get_market_data_ex(dividend_type=...)直接获取复权数据
        """
        # 延迟导入xtdata
        if not self.qmt_available:
            try:
                print(f"  [DEBUG] 尝试导入xtdata...")
                from xtquant import xtdata
                self.xtdata = xtdata
                self.qmt_available = True
                print(f"  [INFO] AdjustmentCache: xtdata导入成功")
            except ImportError as e:
                print(f"  [DEBUG] xtdata导入失败（QMT 未运行）: {e}")
                return pd.DataFrame()
            except Exception as e:
                print(f"  [DEBUG] xtdata连接异常: {e}")
                return pd.DataFrame()

        # 转换复权类型
        dividend_type = ADJUST_TO_QMT_DIVIDEND_TYPE.get(adjust_type, 'none')

        try:
            print(f"  [INFO] 调用QMT API获取复权数据 [股票:{stock_code}] (dividend_type={dividend_type})...")

            # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
            start_time_fmt = start_date.replace('-', '')
            end_time_fmt = end_date.replace('-', '')

            # 调用QMT API获取复权数据
            data = self.xtdata.get_market_data_ex(
                stock_list=[stock_code],
                period='1d',
                start_time=start_time_fmt,
                end_time=end_time_fmt,
                dividend_type=dividend_type
            )

            print(f"  [DEBUG] QMT API返回: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A'}")

            if data is None or (stock_code not in data):
                warnings.warn(f"QMT API返回空数据 (dividend_type={dividend_type})")
                return pd.DataFrame()

            # 提取DataFrame
            df = data[stock_code]

            if df.empty:
                warnings.warn(f"QMT API返回空DataFrame (dividend_type={dividend_type})")
                return pd.DataFrame()

            print(f"  [OK] QMT API返回 {len(df)} 条数据 [股票:{stock_code}]")

            # 格式化数据
            return self._format_qmt_data(df, stock_code)

        except Exception as e:
            warnings.warn(f"QMT API调用失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _get_from_tushare_api(self,
                              stock_code: str,
                              start_date: str,
                              end_date: str,
                              adjust_type: AdjustType) -> pd.DataFrame:
        """
        tushare 备选方案（QMT 离线时使用）

        降级策略：
        1. 方案B：调 adj_factor + daily，自行计算后复权（准确，需 2 次 API 调用）
        2. 方案A：调 pro_bar(adj=...)，直接获取复权数据（简单，1 次 API 调用）
        """
        try:
            from config.env_config import get_env_config
            token = get_env_config().tushare_token
            if not token:
                print(f"  [DEBUG] tushare token 未配置，跳过 tushare 兜底")
                return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

        # 转换股票代码格式：600519.SH → tushare 的 ts_code
        ts_code = self._convert_to_ts_code(stock_code)
        if not ts_code:
            return pd.DataFrame()

        # 转换日期格式
        start_fmt = start_date.replace('-', '')
        end_fmt = end_date.replace('-', '')

        # 方案B：用 adj_factor 自行计算
        try:
            result = self._tushare_adj_factor_calc(ts_code, start_fmt, end_fmt, adjust_type)
            if not result.empty:
                return result
        except Exception as e:
            print(f"  [DEBUG] tushare adj_factor 计算失败: {e}")

        # 方案A：pro_bar 直接获取
        try:
            result = self._tushare_pro_bar(ts_code, start_fmt, end_fmt, adjust_type)
            if not result.empty:
                return result
        except Exception as e:
            print(f"  [DEBUG] tushare pro_bar 也失败: {e}")

        return pd.DataFrame()

    def _tushare_adj_factor_calc(self,
                                 ts_code: str,
                                 start_date: str,
                                 end_date: str,
                                 adjust_type: AdjustType) -> pd.DataFrame:
        """
        方案B：用 tushare adj_factor + daily 自行计算复权价格

        后复权公式: adj_price = raw_price × (factor_today / factor_latest)
        前复权公式: adj_price = raw_price × (factor_today / factor_earliest)
        """
        import tushare as ts
        pro = ts.pro_api()

        # 获取不复权行情
        df_daily = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df_daily is None or df_daily.empty:
            return pd.DataFrame()

        # 获取复权因子
        df_adj = pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df_adj is None or df_adj.empty:
            return pd.DataFrame()

        # 合并
        df = df_daily.merge(df_adj[['trade_date', 'adj_factor']], on='trade_date', how='left')
        if df['adj_factor'].isna().all():
            return pd.DataFrame()

        df['adj_factor'] = df['adj_factor'].ffill()

        # 计算复权价格
        if adjust_type in ('back', 'geometric_back'):
            # 后复权：以最新因子为基准
            base_factor = df['adj_factor'].iloc[-1]
        else:
            # 前复权：以最早因子为基准
            base_factor = df['adj_factor'].iloc[0]

        if base_factor <= 0:
            return pd.DataFrame()

        ratio = df['adj_factor'] / base_factor
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col] * ratio

        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        df['stock_code'] = ts_code
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df.index.name = 'date'

        print(f"  [OK] tushare adj_factor 计算复权成功 {len(df)} 条 [股票:{ts_code}]")
        return df[['stock_code', 'open', 'high', 'low', 'close', 'volume', 'amount']]

    def _tushare_pro_bar(self,
                         ts_code: str,
                         start_date: str,
                         end_date: str,
                         adjust_type: AdjustType) -> pd.DataFrame:
        """
        方案A：用 tushare pro_bar 直接获取复权数据（最后兜底）
        """
        import tushare as ts

        # 映射复权类型到 pro_bar 的 adj 参数
        adj_map = {
            'front': 'qfq',
            'back': 'hfq',
            'geometric_front': 'qfq',   # pro_bar 不支持等比，用普通前复权替代
            'geometric_back': 'hfq',
        }
        adj = adj_map.get(adjust_type, 'hfq')

        df = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj=adj)
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        df['stock_code'] = ts_code
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df.index.name = 'date'

        print(f"  [OK] tushare pro_bar({adj}) 获取复权成功 {len(df)} 条 [股票:{ts_code}]")
        return df[['stock_code', 'open', 'high', 'low', 'close', 'volume', 'amount']]

    @staticmethod
    def _convert_to_ts_code(stock_code: str) -> str:
        """
        转换股票代码格式为 tushare 的 ts_code

        Examples:
            '600519.SH' → '600519.SH'  (已正确)
            '600519'    → '600519.SH'  (根据号段判断)
            '000001.SZ' → '000001.SZ'
        """
        stock_code = stock_code.strip().upper()
        if '.' in stock_code:
            # 把 .SS 转为 .SH（GUI 用的 .SS 后缀，tushare 用 .SH）
            return stock_code.replace('.SS', '.SH')
        # 无后缀，根据号段判断
        if stock_code.startswith(('6', '9')):
            return f"{stock_code}.SH"
        elif stock_code.startswith(('0', '3', '2')):
            return f"{stock_code}.SZ"
        elif stock_code.startswith(('4', '8')):
            return f"{stock_code}.BJ"
        return f"{stock_code}.SH"

    def _format_qmt_data(self, data: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        格式化QMT返回的数据

        QMT返回的数据格式需要转换为我们统一的格式
        """
        if data.empty:
            return pd.DataFrame()

        # 重置索引（如果有多级索引）
        if isinstance(data.index, pd.MultiIndex):
            data = data.reset_index()

        # 确保列名统一
        column_mapping = {
            'time': 'date',
            'trade_time': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
            'code': 'stock_code'
        }

        # 重命名列
        data = data.rename(columns=column_mapping)

        # 转换时间戳为日期格式
        if 'date' in data.columns:
            # 检查date列是否为时间戳（大整数）
            if data['date'].dtype in ['int64', 'int32']:
                # 将毫秒时间戳转换为datetime（修复时区问题）
                # 关键：先转换为UTC时间戳，再转为本地时间，避免时区偏移导致的日期错误
                data['date'] = pd.to_datetime(data['date'], unit='ms', utc=True)
                # 转换为本地时区（中国时区UTC+8）
                data['date'] = data['date'].dt.tz_convert('Asia/Shanghai')
                # 转换为日期格式（去掉时分秒）
                data['date'] = data['date'].dt.date

        # 确保有stock_code列（强制覆盖，防止QMT返回错误的数据）
        data['stock_code'] = stock_code
        print(f"  [DEBUG] _format_qmt_data: 设置stock_code={stock_code}, 行数={len(data)}")

        # 确保有period列
        if 'period' not in data.columns:
            data['period'] = '1d'

        # 选择需要的列
        required_columns = [
            'stock_code', 'date', 'period',
            'open', 'high', 'low', 'close', 'volume', 'amount'
        ]

        # 只保留存在的列
        available_columns = [col for col in required_columns if col in data.columns]
        data = data[available_columns]

        # 输出数据样本用于调试
        if not data.empty and 'close' in data.columns:
            sample_close = data['close'].iloc[0] if len(data) > 0 else 'N/A'
            print(f"  [DEBUG] _format_qmt_data: 股票={stock_code}, 行数={len(data)}, 首日收盘={sample_close:.2f}")

        # 设置date为索引（确保索引类型一致）
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            data = data.set_index('date')
            data.index.name = 'date'  # 明确命名索引，确保reset_index()后能正确生成列

        return data

    def invalidate_cache(self, stock_code: str, con: duckdb.DuckDBPyConnection):
        """
        缓存失效（API方案无需实现）

        API方案每次都从QMT获取最新数据，无需本地缓存管理
        """
        pass


def test_adjustment_cache():
    """测试复权查询（QMT API方案）"""
    print("=" * 60)
    print("复权查询测试（QMT API方案）")
    print("=" * 60)

    db_path = get_default_db_path()
    cache = AdjustmentCache(db_path)

    con = duckdb.connect(db_path)

    test_stock = '511380.SH'
    start_date = '2024-01-01'
    end_date = '2024-01-31'

    # 测试1: 不复权
    print("\n[1] 查询不复权数据（从DuckDB）...")
    df_none = cache.get_adjusted_data(test_stock, start_date, end_date, 'none', con)
    print(f"  返回 {len(df_none)} 条数据")
    if not df_none.empty:
        print(f"  列: {list(df_none.columns)}")

    # 测试2: 前复权
    print("\n[2] 查询前复权数据（从QMT API）...")
    df_front = cache.get_adjusted_data(test_stock, start_date, end_date, 'front', con)
    print(f"  返回 {len(df_front)} 条数据")
    if not df_front.empty:
        print(f"  列: {list(df_front.columns)}")
        # 验证价格是否被复权
        if 'close' in df_front.columns:
            print(f"  最新收盘价: {df_front['close'].iloc[-1]:.3f}")

    # 测试3: 后复权
    print("\n[3] 查询后复权数据（从QMT API）...")
    df_back = cache.get_adjusted_data(test_stock, start_date, end_date, 'back', con)
    print(f"  返回 {len(df_back)} 条数据")

    con.close()
    print("\n[OK] 测试完成")
    print("\n核心优势:")
    print("  - 无需本地计算复权")
    print("  - 使用QMT官方算法")
    print("  - 代码简洁易维护")


if __name__ == "__main__":
    test_adjustment_cache()
