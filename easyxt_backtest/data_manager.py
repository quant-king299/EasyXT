# -*- coding: utf-8 -*-
"""
数据管理器 - 向后兼容层

⚠️ 已迁移到 core.data_manager.HybridDataManager

本文件为向后兼容层，现有代码无需修改即可使用新的架构。
建议新项目直接使用 core.data_manager.HybridDataManager

迁移计划：
- v1.5.0: 引入兼容层（当前版本）
- v2.0.0: 移除兼容层
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import warnings

# 添加项目路径以导入core模块
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.data_manager import (
    HybridDataManager,
    DataManagerConfig,
    get_global_config,
    normalize_symbol,
    normalize_symbols,
    validate_date,
)


def convert_date_format(dt_str: str,
                       input_format: str = '%Y%m%d',
                       output_format: str = '%Y-%m-%d') -> str:
    """
    转换日期格式

    Args:
        dt_str: 日期字符串
        input_format: 输入格式
        output_format: 输出格式

    Returns:
        转换后的日期字符串
    """
    try:
        dt = datetime.strptime(dt_str, input_format)
        return dt.strftime(output_format)
    except:
        return dt_str


class DataManager:
    """
    统一数据管理器（向后兼容层）

    ⚠️ 已迁移到 core.data_manager.HybridDataManager

    本类为向后兼容层，内部使用 HybridDataManager 实现。
    现有代码无需修改即可继续使用。

    建议新代码直接使用：
        from core.data_manager import HybridDataManager
        manager = HybridDataManager()
    """

    def __init__(self,
                 duckdb_path: Optional[str] = None,
                 tushare_token: Optional[str] = None):
        """
        初始化数据管理器

        Args:
            duckdb_path: DuckDB数据库路径（已弃用，请使用环境变量）
            tushare_token: Tushare API Token（已弃用，请使用环境变量）
        """
        # 发出弃用警告
        warnings.warn(
            "easyxt_backtest.data_manager.DataManager 已迁移到 "
            "core.data_manager.HybridDataManager。建议更新您的代码。"
            "本兼容层将在 v2.0.0 移除。",
            DeprecationWarning,
            stacklevel=2
        )

        # 创建配置
        config = DataManagerConfig()

        # 如果提供了参数，设置到配置中
        if duckdb_path:
            config.set('duckdb_path', duckdb_path)
        if tushare_token:
            config.set('tushare_token', tushare_token)

        # 创建HybridDataManager实例
        self._manager = HybridDataManager(config)

        # 保留原有的属性以保持兼容性
        self.duckdb_path = config.get('duckdb_path')
        self.tushare_token = config.get('tushare_token')
        self.price_cache = {}
        self.fundamental_cache = {}
        self.trading_days_cache = None

        print("[DataManager] 使用新的 core.data_manager.HybridDataManager")

    def get_price(self,
                  codes: Union[str, List[str]],
                  start_date: str,
                  end_date: str,
                  fields: List[str] = None,
                  fq: str = None) -> pd.DataFrame:
        """
        获取价格数据

        Args:
            codes: 股票代码或代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            fields: 需要的字段列表（已弃用，返回所有字段）
            fq: 复权类型（已弃用，新架构默认不复权）
                - 'qfq': 前复权
                - 'hfq': 后复权
                - 'None' or None: 不复权

        Returns:
            DataFrame: 价格数据
        """
        # 如果提供了fq参数且不是None，发出警告
        if fq is not None and fq != 'None':
            warnings.warn(
                f"get_price()的fq参数('{fq}')在新架构中被忽略。"
                "新数据源默认返回不复权数据。如需复权，请使用数据源的复权功能。",
                DeprecationWarning,
                stacklevel=2
            )

        # 调用新的HybridDataManager
        df = self._manager.get_price(codes, start_date, end_date)

        if df is None or df.empty:
            return pd.DataFrame()

        # 设置MultiIndex以保持与旧版本的兼容性
        if 'date' in df.columns and 'symbol' in df.columns:
            df.set_index(['date', 'symbol'], inplace=True)

        return df

    def get_fundamentals(self,
                         codes: Union[str, List[str]],
                         date: str,
                         fields: List[str] = ['circ_mv']) -> pd.DataFrame:
        """
        获取基本面数据

        Args:
            codes: 股票代码或代码列表
            date: 查询日期 (YYYYMMDD)
            fields: 需要的字段列表

        Returns:
            DataFrame: 基本面数据
        """
        # 调用新的HybridDataManager
        df = self._manager.get_fundamentals(codes, date, fields)

        if df is None or df.empty:
            return pd.DataFrame()

        return df

    def get_trading_dates(self,
                          start_date: str,
                          end_date: str) -> List[str]:
        """
        获取交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            List[str]: 交易日列表 (YYYYMMDD格式)
        """
        # 调用新的HybridDataManager
        dates = self._manager.get_trading_dates(start_date, end_date)

        return dates if dates else []

    def get_nearest_price(self,
                          code: str,
                          date: str,
                          max_days_back: int = 30) -> Optional[float]:
        """
        获取最近交易日的价格

        Args:
            code: 股票代码
            date: 查询日期 (YYYYMMDD)
            max_days_back: 最多向前查找天数

        Returns:
            float: 收盘价，找不到返回None
        """
        # 标准化股票代码
        code = normalize_symbol(code)

        # 向前查找（使用静默模式，避免日志刷屏）
        for i in range(max_days_back + 1):
            try:
                date_obj = datetime.strptime(date, '%Y%m%d')
                prev_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

                # 获取价格数据（关闭详细日志）
                df = self._manager.get_price(code, prev_date, prev_date, verbose=False)

                if df is not None and not df.empty:
                    # 返回收盘价
                    if 'close' in df.columns:
                        return float(df['close'].iloc[-1])
                    else:
                        return None

            except Exception as e:
                continue

        return None

    def check_if_delisted(self,
                         code: str,
                         date: str,
                         check_days: int = 30) -> Optional[tuple]:
        """
        检查股票是否退市（完整版逻辑）

        Args:
            code: 股票代码
            date: 查询日期
            check_days: 检查天数

        Returns:
            None (未退市) 或 (last_trade_date, last_price) (已退市)
        """
        from datetime import datetime, timedelta

        dt_obj = datetime.strptime(date, '%Y%m%d')

        # 向前查找最近的有价格的日期
        last_trade_date = None
        last_price = None
        last_day_offset = None

        for i in range(1, check_days + 1):
            check_date = (dt_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (dt_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:  # 周六、周日
                continue

            # 尝试获取价格（静默模式）
            df = self._manager.get_price(code, check_date, check_date, verbose=False)
            if df is not None and not df.empty and 'close' in df.columns:
                last_trade_date = check_date
                last_price = float(df['close'].iloc[-1])
                last_day_offset = i
                break

        # 如果在check_days内找不到任何价格，判定为退市
        if last_trade_date is None:
            return (None, None)

        # ✅ 关键检查：从最后交易日到今天之间是否有交易日有数据
        # 如果中间有数据，说明只是停牌；如果全无数据，说明已退市
        for j in range(last_day_offset):
            between_date = (dt_obj - timedelta(days=j)).strftime('%Y%m%d')
            day_of_week = (dt_obj - timedelta(days=j)).weekday()
            if day_of_week >= 5:
                continue

            df = self._manager.get_price(code, between_date, between_date, verbose=False)
            if df is not None and not df.empty and 'close' in df.columns:
                # 中间有价格数据，说明未退市（可能只是当天停牌）
                return None

        # 从找到的最近价格日期到现在都没有数据，判定为退市
        return (last_trade_date, last_price)

    def get_last_trade_date_and_price(self,
                                     code: str,
                                     date: str) -> Optional[tuple]:
        """
        获取最后交易日和价格

        Args:
            code: 股票代码
            date: 查询日期

        Returns:
            tuple: (最后交易日, 收盘价)
        """
        # 向前查找（使用静默模式）
        for i in range(30):  # 最多向前30天
            try:
                date_obj = datetime.strptime(date, '%Y%m%d')
                prev_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

                # 关闭详细日志
                df = self._manager.get_price(code, prev_date, prev_date, verbose=False)

                if df is not None and not df.empty:
                    price = float(df['close'].iloc[-1]) if 'close' in df.columns else None
                    return (prev_date, price)

            except Exception:
                continue

        return None

    def get_price_date(self, code: str, query_date: str) -> Optional[str]:
        """
        获取价格对应的日期

        Args:
            code: 股票代码
            query_date: 查询日期

        Returns:
            str: 实际有数据的日期
        """
        result = self.get_last_trade_date_and_price(code, query_date)
        if result:
            return result[0]
        return None

    def is_delisted(self, code: str, date: str, check_days: int = 30) -> tuple:
        """
        检查股票是否已退市（增强版）

        Args:
            code: 股票代码
            date: 当前日期 (YYYYMMDD)
            check_days: 检查天数，默认30天

        Returns:
            (is_delisted: bool, last_trade_date: Optional[str], last_price: Optional[float])
            - is_delisted: True表示已退市，False表示正常
            - last_trade_date: 最后交易日（如果已退市）
            - last_price: 最后价格（如果已退市）
        """
        result = self.check_if_delisted(code, date, check_days)

        if result is None:
            # 未退市（中间有价格数据）
            return (False, None, None)
        else:
            # 已退市（result 格式为 (last_trade_date, last_price)）
            last_trade_date, last_price = result
            return (True, last_trade_date, last_price)

    def check_price_data_valid(self,
                              code: str,
                              date: str,
                              max_days_diff: int = 7) -> tuple:
        """
        综合检查价格数据的有效性（包括是否退市）

        Args:
            code: 股票代码
            date: 查询日期 (YYYYMMDD)
            max_days_diff: 允许的最大天数差异，默认7天

        Returns:
            (is_valid: bool, reason: str, price_date: Optional[str], price: Optional[float])
            - is_valid: True表示数据有效，False表示无效
            - reason: 无效的原因（用于日志输出）
            - price_date: 价格数据的实际日期
            - price: 价格
        """
        from datetime import datetime, timedelta

        # 1. 检查是否退市
        delisted_result = self.check_if_delisted(code, date, check_days=30)
        if delisted_result is not None:
            is_delisted_flag, last_date = delisted_result
            if is_delisted_flag:
                # 尝试获取最后的价格
                last_price = self.get_nearest_price(code, date, max_days_back=30)
                if last_price is not None:
                    return (False, f"已退市({last_date}最后价格{last_price:.2f})", last_date, last_price)
                else:
                    return (False, "已退市且无历史价格数据", None, None)

        # 2. 获取价格
        price = self.get_nearest_price(code, date, max_days_back=max_days_diff)
        if price is None:
            return (False, "无价格数据", None, None)

        # 3. 获取价格日期
        price_date_result = self.get_last_trade_date_and_price(code, date)
        if price_date_result is not None:
            price_date, _ = price_date_result
        else:
            price_date = date

        if price_date is None:
            return (False, "无法确定价格日期", None, None)

        # 4. 检查价格数据是否过期
        try:
            price_dt = datetime.strptime(price_date, '%Y%m%d')
            query_dt = datetime.strptime(date, '%Y%m%d')
            days_diff = (query_dt - price_dt).days

            if days_diff > max_days_diff:
                return (False, f"价格数据过期({price_date}，{days_diff}天前)", price_date, price)
        except ValueError:
            pass

        # 5. 所有检查通过
        return (True, "数据有效", price_date, price)

    def get_index_components(self,
                            index_code: str,
                            date: str) -> List[str]:
        """
        获取指数成分股

        Args:
            index_code: 指数代码
            date: 查询日期

        Returns:
            List[str]: 成分股代码列表
        """
        try:
            # 尝试从DuckDB获取股票列表
            if 'duckdb' in self._manager.sources:
                duckdb_source = self._manager.sources['duckdb']
                stock_list = duckdb_source.get_stock_list('stock')

                if stock_list:
                    return stock_list[:1000]  # 限制返回数量，避免过大

            # 如果DuckDB不可用，返回预定义的常用股票列表
            # 沪深300成分股（示例）
            common_stocks = [
                '000001.SZ', '000002.SZ', '000063.SZ', '000069.SZ', '000100.SZ',
                '000166.SZ', '000333.SZ', '000338.SZ', '000401.SZ', '000402.SZ',
                '000415.SZ', '000425.SZ', '000501.SZ', '000516.SZ', '000527.SZ',
                '000538.SZ', '000547.SZ', '000568.SZ', '000583.SZ', '000596.SZ',
                '000625.SZ', '000627.SZ', '000630.SZ', '000651.SZ', '000652.SZ',
                '000660.SZ', '000663.SZ', '000666.SZ', '000673.SZ', '000677.SZ',
                '000681.SZ', '000686.SZ', '000690.SZ', '000708.SZ', '000709.SZ',
                '000712.SZ', '000717.SZ', '000718.SZ', '000725.SZ', '000728.SZ',
                '000730.SZ', '000732.SZ', '000733.SZ', '000735.SZ', '000737.SZ',
                '000738.SZ', '000739.SZ', '000742.SZ', '000746.SZ', '000748.SZ',
                '000750.SZ', '000751.SZ', '000753.SZ', '000755.SZ', '000758.SZ',
                '000761.SZ', '000763.SZ', '000766.SZ', '000768.SZ', '000769.SZ',
                '000770.SZ', '000772.SZ', '000776.SZ', '000777.SZ', '000778.SZ',
                '000780.SZ', '000782.SZ', '000783.SZ', '000785.SZ', '000786.SZ',
                '000788.SZ', '000789.SZ', '000790.SZ', '000791.SZ', '000792.SZ',
                '000793.SZ', '000795.SZ', '000797.SZ', '000798.SZ', '000799.SZ',
                '000800.SZ', '000801.SZ', '000802.SZ', '000805.SZ', '000806.SZ',
                '000807.SZ', '000809.SZ', '000810.SZ', '000811.SZ', '000812.SZ',
                '000813.SZ', '000815.SZ', '000816.SZ', '000819.SZ', '000820.SZ',
                '000821.SZ', '000822.SZ', '000823.SZ', '000825.SZ', '000826.SZ',
                '000827.SZ', '000828.SZ', '000829.SZ', '000830.SZ', '000831.SZ',
                '600000.SH', '600004.SH', '600009.SH', '600010.SH', '600011.SH',
                '600015.SH', '600016.SH', '600017.SH', '600018.SH', '600019.SH',
                '600025.SH', '600026.SH', '600027.SH', '600028.SH', '600029.SH',
                '600030.SH', '600031.SH', '600032.SH', '600033.SH', '600035.SH',
                '600036.SH', '600037.SH', '600039.SH', '600048.SH', '600050.SH',
                '600104.SH', '600105.SH', '600106.SH', '600107.SH', '600108.SH',
                '600109.SH', '600110.SH', '600111.SH', '600113.SH', '600115.SH',
                '600116.SH', '600117.SH', '600118.SH', '600119.SH', '600120.SH',
                '600123.SH', '600125.SH', '600126.SH', '600127.SH', '600128.SH',
                '600129.SH', '600130.SH', '600131.SH', '600132.SH', '600133.SH',
                '600136.SH', '600138.SH', '600139.SH', '600143.SH', '600144.SH',
                '600150.SH', '600151.SH', '600152.SH', '600153.SH', '600154.SH',
                '600156.SH', '600157.SH', '600158.SH', '600159.SH', '600160.SH',
                '600161.SH', '600162.SH', '600163.SH', '600165.SH', '600166.SH',
                '600167.SH', '600168.SH', '600169.SH', '600170.SH', '600171.SH',
                '600176.SH', '600177.SH', '600178.SH', '600179.SH', '600180.SH',
                '600183.SH', '600184.SH', '600185.SH', '600186.SH', '600187.SH',
                '600188.SH', '600189.SH', '600190.SH', '600191.SH', '600192.SH',
                '600196.SH', '600197.SH', '600198.SH', '600199.SH', '600200.SH'
            ]

            print(f"[DataManager] 使用预定义股票列表（{len(common_stocks)}只股票）")
            return common_stocks

        except Exception as e:
            print(f"[DataManager] 获取股票列表失败: {e}")
            return []

    def close(self):
        """关闭数据管理器"""
        self._manager.close()


# 导出兼容的函数和类
__all__ = ['DataManager', 'convert_date_format']
