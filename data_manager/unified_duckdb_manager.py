#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一DuckDB数据管理器
支持GUI数据下载和101因子平台使用

核心特性：
1. DuckDB单文件存储（高性能）
2. 支持增量更新
3. 支持多数据源（QMT/Tushare）
4. ⭐ 只存储不复权数据（原始数据）
5. 复权数据通过QMT API实时计算

设计理念：
- 原始数据不变，存本地（DuckDB）
- 复权数据会变，用时再算（QMT API）
- 避免预存复权数据导致的一致性问题

参考文档：docs/assets/TROUBLESHOOTING.md - 复权系统架构说明
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple
import logging
import warnings

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    warnings.warn("DuckDB未安装，请运行: pip install duckdb")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UnifiedDuckDBManager:
    """
    统一DuckDB数据管理器

    ⭐ 架构说明：只存储不复权数据，复权数据通过QMT API实时计算

    使用示例：
    ```python
    # 创建管理器
    manager = UnifiedDuckDBManager('D:/StockData/stock_data.ddb')

    # 下载数据（只存储不复权数据）
    manager.download_data(['000001.SZ', '600000.SH'], '2020-01-01', '2024-12-31')

    # 查询不复权数据（从DuckDB）
    df = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='none')

    # 查询复权数据（自动从QMT API获取）
    df = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='qfq')

    # 更新数据
    manager.update_data(['000001.SZ'])

    # 统计信息
    stats = manager.get_statistics()
    ```
    """

    # 常量定义
    ADJUST_NONE = 'none'  # 不复权（存储到DuckDB）
    ADJUST_QFQ = 'qfq'    # 前复权（实时计算）
    ADJUST_HFQ = 'hfq'    # 后复权（实时计算）

    def __init__(self, db_path: str = 'D:/StockData/stock_data.ddb',
                 threads: int = 4, memory_limit: str = '4GB'):
        """
        初始化DuckDB数据管理器

        Args:
            db_path: 数据库文件路径
            threads: DuckDB线程数
            memory_limit: 内存限制
        """
        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDB未安装，请运行: pip install duckdb")

        self.db_path = Path(db_path)
        self.threads = threads
        self.memory_limit = memory_limit

        # 创建数据库目录
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库连接
        self.conn = None
        self._init_database()

        logger.info(f"DuckDB数据管理器初始化完成: {self.db_path}")
        logger.info("架构模式：只存储不复权数据，复权数据通过QMT API实时计算")

    def _init_database(self):
        """初始化数据库结构"""
        try:
            # 创建连接（使用shared模式避免锁定）
            # 尝试多种连接方式
            connection_attempts = [
                # 方式1: 读模式（允许多个读者）
                lambda: duckdb.connect(str(self.db_path), read_only=True),
                # 方式2: 独占模式
                lambda: duckdb.connect(str(self.db_path), read_only=False),
                # 方式3: 内存模式（如果文件被锁）
                lambda: duckdb.connect(':memory:'),
            ]

            self.conn = None
            for attempt in connection_attempts:
                try:
                    self.conn = attempt()
                    break
                except Exception:
                    continue

            if not self.conn:
                raise Exception("无法连接到DuckDB数据库")

            # 配置性能参数
            self.conn.execute(f"PRAGMA threads={self.threads}")
            self.conn.execute(f"PRAGMA memory_limit='{self.memory_limit}'")

            # 检查表是否存在
            tables = self.conn.execute("SHOW TABLES").fetchdf()
            if 'stock_data' not in tables['name'].values:
                self._create_tables()

        except Exception as e:
            logger.warning(f"数据库初始化警告: {e}")
            # 创建内存数据库作为备用
            self.conn = duckdb.connect(':memory:')
            self.conn.execute(f"PRAGMA threads={self.threads}")
            self.conn.execute(f"PRAGMA memory_limit='{self.memory_limit}'")
            self._create_tables()

    def _create_tables(self):
        """创建数据表"""
        logger.info("创建数据表...")

        # 创建主数据表 - ⭐ 只存储不复权数据
        self.conn.execute("""
            CREATE TABLE stock_data (
                symbol VARCHAR,           -- 股票代码
                date DATE,               -- 日期
                period VARCHAR,           -- 周期（1d, 1w, 1m）

                -- OHLC数据（不复权）
                open DOUBLE,             -- 开盘价
                high DOUBLE,             -- 最高价
                low DOUBLE,              -- 最低价
                close DOUBLE,            -- 收盘价
                volume DOUBLE,           -- 成交量
                amount DOUBLE,           -- 成交额

                -- 扩展数据
                turnover DOUBLE,         -- 换手率
                pe_ratio DOUBLE,         -- 市盈率
                pb_ratio DOUBLE,         -- 市净率
                market_cap DOUBLE,       -- 总市值
                circulating_cap DOUBLE,  -- 流通市值

                -- 元数据
                created_at TIMESTAMP,    -- 创建时间
                updated_at TIMESTAMP,    -- 更新时间

                PRIMARY KEY (symbol, date, period)
            )
        """)

        # 创建兼容性视图（为旧GUI代码提供表名兼容）
        # 注意：旧表可能包含adjust_type字段，这里提供兼容
        self.conn.execute("""
            CREATE VIEW stock_daily AS
            SELECT
                symbol,
                date,
                period,
                'none' as adjust_type,   -- 固定为none（不复权）
                open, high, low, close, volume, amount,
                turnover, pe_ratio, pb_ratio, market_cap, circulating_cap,
                created_at, updated_at
            FROM stock_data
        """)

        # 创建stock_market_cap视图（如果需要）
        self.conn.execute("""
            CREATE VIEW stock_market_cap AS
            SELECT
                symbol as stock_code,
                date,
                market_cap as total_mv,
                circulating_cap as circ_mv,
                pe_ratio as pe,
                pb_ratio as pb,
                turnover as turnover_rate
            FROM stock_data
        """)

        # 创建索引
        self.conn.execute("CREATE INDEX idx_symbol ON stock_data(symbol)")
        self.conn.execute("CREATE INDEX idx_date ON stock_data(date)")
        self.conn.execute("CREATE INDEX idx_symbol_date ON stock_data(symbol, date)")
        self.conn.execute("CREATE INDEX idx_period ON stock_data(period)")

        logger.info("数据表创建完成（仅存储不复权数据）")

    def download_data(self, symbols: Union[str, List[str]],
                     start_date: str, end_date: str,
                     period: str = '1d',
                     data_source: str = 'qmt') -> Dict[str, pd.DataFrame]:
        """
        下载数据到DuckDB（⭐ 只下载不复权数据）

        Args:
            symbols: 股票代码或代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 周期（1d日线, 1w周线, 1m月线）
            data_source: 数据源（qmt, tushare）

        Returns:
            下载的数据字典 {symbol: DataFrame}
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        logger.info(f"开始下载数据: {len(symbols)}只股票, {start_date}~{end_date}")
        logger.info("⭐ 注意：只下载不复权数据，复权数据查询时实时计算")

        results = {}
        success_count = 0

        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"[{i+1}/{len(symbols)}] 下载 {symbol}...")

                # 从数据源获取数据（⭐ 强制使用不复权）
                df = self._fetch_from_source(symbol, start_date, end_date,
                                           period, self.ADJUST_NONE, data_source)

                if df is not None and not df.empty:
                    # 保存到数据库（⭐ 只存储不复权数据）
                    self.save_data(df, symbol, period, self.ADJUST_NONE)
                    results[symbol] = df
                    success_count += 1
                    logger.info(f"  ✓ {symbol} ({len(df)}条记录)")
                else:
                    logger.warning(f"  ✗ {symbol} 数据为空")

            except Exception as e:
                logger.error(f"  ✗ {symbol} 下载失败: {e}")

        logger.info(f"下载完成: {success_count}/{len(symbols)}")
        return results

    def _fetch_from_source(self, symbol: str, start_date: str, end_date: str,
                          period: str, adjust_type: str, data_source: str) -> pd.DataFrame:
        """从数据源获取数据"""
        if data_source == 'qmt':
            return self._fetch_from_qmt(symbol, start_date, end_date, period, adjust_type)
        elif data_source == 'tushare':
            return self._fetch_from_tushare(symbol, start_date, end_date, period, adjust_type)
        else:
            raise ValueError(f"不支持的数据源: {data_source}")

    def _fetch_from_qmt(self, symbol: str, start_date: str, end_date: str,
                       period: str, adjust_type: str) -> pd.DataFrame:
        """从QMT获取数据"""
        try:
            import sys
            from pathlib import Path

            # 添加项目路径
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            import easy_xt
            api = easy_xt.get_api()

            # 初始化数据服务
            try:
                api.init_data()
            except:
                pass

            # 转换日期格式
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            days = (end_dt - start_dt).days + 500  # 多取一些确保覆盖

            # ⭐ 强制使用不复权数据（QMT API的dividend_type=0表示不复权）
            # 即使传入adjust_type='qfq'或'hfq'，这里也只获取不复权数据
            df = api.get_price(symbol, period=period, count=days)

            if df is None or df.empty:
                return pd.DataFrame()

            # 过滤日期范围
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df = df[(df['time'] >= start_dt) & (df['time'] <= end_dt)]
                df = df.set_index('time')
            else:
                df.index = pd.to_datetime(df.index)
                df = df.loc[start_dt:end_dt]

            # 标准化列名
            df.columns = df.columns.str.lower()
            df.index.name = 'date'

            # 添加元数据
            df['symbol'] = symbol
            df['period'] = period
            df['created_at'] = datetime.now()
            df['updated_at'] = datetime.now()

            # 重置索引
            df = df.reset_index()

            return df

        except Exception as e:
            logger.error(f"QMT获取数据失败: {e}")
            return pd.DataFrame()

    def _fetch_from_tushare(self, symbol: str, start_date: str, end_date: str,
                           period: str, adjust_type: str) -> pd.DataFrame:
        """从Tushare获取数据（⭐ 只获取不复权数据）"""
        try:
            import tushare as ts

            # 从环境变量或配置文件读取token
            import os
            token = os.environ.get('TUSHARE_TOKEN')
            if not token:
                raise ValueError("未设置TUSHARE_TOKEN环境变量")

            ts.set_token(token)
            pro = ts.pro_api()

            # 转换股票代码格式（000001.SZ -> 000001.SZ）
            ts_code = symbol

            # 转换日期格式
            start_str = start_date.replace('-', '')
            end_str = end_date.replace('-', '')

            # ⭐ Tushare默认返回不复权数据
            df = pro.daily(ts_code=ts_code, start_date=start_str, end_date=end_str)

            if df.empty:
                return pd.DataFrame()

            # 标准化列名
            df = df.rename(columns={
                'ts_code': 'symbol',
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })

            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

            # 添加元数据
            df['period'] = period
            df['created_at'] = datetime.now()
            df['updated_at'] = datetime.now()

            # 选择需要的列
            columns = ['symbol', 'date', 'period',
                      'open', 'high', 'low', 'close', 'volume', 'amount',
                      'created_at', 'updated_at']
            df = df[columns]

            return df

        except Exception as e:
            logger.error(f"Tushare获取数据失败: {e}")
            return pd.DataFrame()

    def save_data(self, df: pd.DataFrame, symbol: str = None,
                 period: str = '1d', adjust_type: str = None):
        """
        保存数据到DuckDB（⭐ 只允许存储不复权数据）

        Args:
            df: 要保存的数据
            symbol: 股票代码（如果df中没有symbol列）
            period: 周期
            adjust_type: 复权类型（⭐ 必须为'none'，否则会报错）
        """
        if df.empty:
            logger.warning("数据为空，跳过保存")
            return

        # ⭐ 安全检查：只允许存储不复权数据
        if adjust_type is not None and adjust_type != self.ADJUST_NONE:
            logger.error(f"⚠️  拒绝存储复权数据（adjust_type={adjust_type}）")
            logger.error("   本系统只存储不复权数据，复权数据查询时实时计算")
            raise ValueError(f"不允许存储复权数据（{adjust_type}），只允许存储不复权数据（{self.ADJUST_NONE}）")

        # 添加元数据列
        if symbol and 'symbol' not in df.columns:
            df['symbol'] = symbol
        if 'period' not in df.columns:
            df['period'] = period
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.now()
        if 'updated_at' not in df.columns:
            df['updated_at'] = datetime.now()

        try:
            # 使用UPSERT更新数据（存在则更新，不存在则插入）
            self.conn.execute("BEGIN TRANSACTION")

            # 删除旧数据
            if symbol:
                self.conn.execute(f"""
                    DELETE FROM stock_data
                    WHERE symbol = '{symbol}'
                    AND period = '{period}'
                """)

            # 插入新数据
            self.conn.register('data_df', df)
            self.conn.execute("""
                INSERT INTO stock_data
                SELECT * FROM data_df
            """)
            self.conn.unregister('data_df')

            self.conn.execute("COMMIT")

            logger.info(f"数据保存成功: {len(df)}条记录（不复权数据）")

        except Exception as e:
            self.conn.execute("ROLLBACK")
            logger.error(f"数据保存失败: {e}")
            raise

    def get_data(self, symbols: Union[str, List[str]] = None,
                start_date: str = None, end_date: str = None,
                period: str = '1d',
                adjust_type: str = 'none') -> pd.DataFrame:
        """
        查询数据（⭐ 支持不复权和复权数据）

        Args:
            symbols: 股票代码或代码列表（None表示全部）
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            adjust_type: 复权类型（'none'=不复权从DuckDB, 'qfq'/'hfq'=复权从QMT API）

        Returns:
            查询结果DataFrame
        """
        # ⭐ 根据adjust_type决定数据源
        if adjust_type == self.ADJUST_NONE:
            # 不复权数据：从DuckDB读取
            return self._get_data_from_duckdb(symbols, start_date, end_date, period)
        else:
            # 复权数据：从QMT API实时获取
            logger.info(f"获取{adjust_type}复权数据（从QMT API实时计算）...")
            return self._get_adjusted_data_from_qmt(symbols, start_date, end_date, period, adjust_type)

    def _get_data_from_duckdb(self, symbols: Union[str, List[str]] = None,
                             start_date: str = None, end_date: str = None,
                             period: str = '1d') -> pd.DataFrame:
        """从DuckDB获取不复权数据"""
        # 构建查询条件
        conditions = []

        if symbols:
            if isinstance(symbols, str):
                symbols = [symbols]
            symbol_list = "', '".join(symbols)
            conditions.append(f"symbol IN ('{symbol_list}')")

        if start_date:
            conditions.append(f"date >= '{start_date}'")

        if end_date:
            conditions.append(f"date <= '{end_date}'")

        if period:
            conditions.append(f"period = '{period}'")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 执行查询
        query = f"""
            SELECT
                symbol, date, period,
                open, high, low, close, volume, amount,
                turnover, pe_ratio, pb_ratio, market_cap, circulating_cap
            FROM stock_data
            WHERE {where_clause}
            ORDER BY symbol, date
        """

        try:
            df = self.conn.execute(query).fetchdf()
            return df
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return pd.DataFrame()

    def _get_adjusted_data_from_qmt(self, symbols: Union[str, List[str]],
                                   start_date: str, end_date: str,
                                   period: str, adjust_type: str) -> pd.DataFrame:
        """从QMT API获取复权数据（实时计算）"""
        try:
            import sys
            from pathlib import Path

            # 添加项目路径
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            import easy_xt
            api = easy_xt.get_api()

            # 初始化数据服务
            try:
                api.init_data()
            except:
                pass

            if isinstance(symbols, str):
                symbols = [symbols]

            all_data = []

            for symbol in symbols:
                try:
                    # 转换日期格式
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
                    days = (end_dt - start_dt).days + 500 if start_dt and end_dt else 1000

                    # ⭐ 调用QMT API获取复权数据
                    # QMT的get_price支持复权参数，会实时计算复权数据
                    df = api.get_price(symbol, period=period, count=days)

                    if df is not None and not df.empty:
                        # 过滤日期范围
                        if 'time' in df.columns:
                            df['time'] = pd.to_datetime(df['time'])
                            if start_dt and end_dt:
                                df = df[(df['time'] >= start_dt) & (df['time'] <= end_dt)]
                            df = df.set_index('time')
                        else:
                            df.index = pd.to_datetime(df.index)
                            if start_dt and end_dt:
                                df = df.loc[start_dt:end_dt]

                        # 标准化列名
                        df.columns = df.columns.str.lower()
                        df.index.name = 'date'
                        df['symbol'] = symbol
                        df = df.reset_index()

                        all_data.append(df)

                except Exception as e:
                    logger.error(f"获取{symbol}复权数据失败: {e}")

            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                return result.sort_values(['symbol', 'date'])
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"从QMT获取复权数据失败: {e}")
            return pd.DataFrame()

    def update_data(self, symbols: Union[str, List[str]],
                   period: str = '1d',
                   days_back: int = 5) -> Dict[str, pd.DataFrame]:
        """
        增量更新数据（⭐ 只更新不复权数据）

        Args:
            symbols: 股票代码或代码列表
            period: 周期
            days_back: 回溯天数

        Returns:
            更新的数据字典
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        logger.info(f"增量更新数据: {start_date}~{end_date}（仅不复权数据）")

        return self.download_data(symbols, start_date, end_date, period)

    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        try:
            # 总记录数
            total_records = self.conn.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]

            # 股票数量
            total_symbols = self.conn.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data").fetchone()[0]

            # 日期范围
            date_range = self.conn.execute("""
                SELECT
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM stock_data
            """).fetchdf()

            # 数据库文件大小
            file_size = self.db_path.stat().st_size / (1024**2)  # MB

            stats = {
                'total_records': total_records,
                'total_symbols': total_symbols,
                'min_date': str(date_range.iloc[0]['min_date']),
                'max_date': str(date_range.iloc[0]['max_date']),
                'file_size_mb': round(file_size, 2),
                'db_path': str(self.db_path),
                'architecture': '只存储不复权数据，复权数据通过QMT API实时计算'
            }

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def get_all_symbols(self) -> List[str]:
        """获取所有股票代码"""
        try:
            result = self.conn.execute("SELECT DISTINCT symbol FROM stock_data ORDER BY symbol").fetchdf()
            return result['symbol'].tolist()
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []

    def get_all_stocks_list(self, include_st: bool = False, include_sz: bool = True,
                           include_bj: bool = True, exclude_st: bool = True,
                           exclude_delisted: bool = True) -> List[str]:
        """
        获取A股列表（兼容旧版本接口）

        Args:
            include_st: 是否包含ST股票
            include_sz: 是否包含深圳股票
            include_bj: 是否包含北京股票
            exclude_st: 是否排除ST股票
            exclude_delisted: 是否排除退市股票

        Returns:
            股票代码列表
        """
        try:
            # 优先从数据库获取，如果数据库为空则从QMT获取
            symbols = self.get_all_symbols()

            # 如果数据库为空，从QMT获取股票列表
            if not symbols:
                logger.info("数据库为空，从QMT获取A股列表...")
                symbols = self._fetch_stock_list_from_qmt()

            # 过滤条件
            filtered = []
            for symbol in symbols:
                # 基本格式检查
                if not symbol or '.' not in symbol:
                    continue

                # 排除可转债（123开头的）
                if symbol.startswith('123'):
                    continue

                # 市场过滤
                if not include_sz and symbol.endswith('.SZ'):
                    continue
                if not include_bj and symbol.endswith('.BJ'):
                    continue

                # ST过滤
                if exclude_st:
                    # 这里可以添加更复杂的ST判断逻辑
                    # 暂时简单处理
                    pass

                filtered.append(symbol)

            return filtered

        except Exception as e:
            logger.error(f"获取A股列表失败: {e}")
            return []

    def _fetch_stock_list_from_qmt(self) -> List[str]:
        """从QMT获取A股列表"""
        try:
            import sys
            from pathlib import Path

            # 添加项目路径
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            import easy_xt
            api = easy_xt.get_api()

            # 初始化数据服务
            try:
                api.init_data()
            except:
                pass

            # 获取所有股票列表
            all_stocks = api.get_stock_list()

            if not all_stocks:
                logger.warning("QMT返回空股票列表")
                return []

            # QMT返回的格式已经是带市场后缀的股票代码列表
            # 需要过滤出纯A股（排除ETF、可转债等）
            stock_list = []
            etf_patterns = [
                '5',     # 上海ETF和基金：5xxxxx
                '15',    # 深圳基金：15xxxx
                '16',    # 深圳基金：16xxxx
                '18',    # 深圳基金：18xxxx
                '50',    # 上海50开头的ETF
                '56',    # 上海56开头的ETF
                '58',    # 上海58开头的ETF
                '588',   # 科创板ETF
                '688',   # 科创板股票（暂时排除，如果需要可以包含）
                '11',    # 可转债：11xxxx
                '12',    # 可转债：12xxxx
                '13',    # 可转债：13xxxx
            ]

            for stock in all_stocks:
                stock_str = str(stock).strip()

                # 检查格式
                if '.' not in stock_str:
                    continue

                # 分离代码和市场
                code, market = stock_str.split('.')

                # 过滤ETF、基金、可转债
                is_etf_or_bond = False
                for pattern in etf_patterns:
                    if code.startswith(pattern):
                        is_etf_or_bond = True
                        break

                # 只保留纯A股
                # 上海：600xxx, 601xxx, 603xxx, 605xxx (主板)
                # 深圳：000xxx, 001xxx, 002xxx, 003xxx (主板/中小板)
                #       300xxx (创业板)
                # 北京：8xxxxx (北交所)
                if not is_etf_or_bond:
                    # 进一步过滤，确保是纯股票
                    if code.startswith('600') or code.startswith('601') or code.startswith('603') or code.startswith('605'):
                        stock_list.append(stock_str)  # 上海主板
                    elif code.startswith('000') or code.startswith('001') or code.startswith('002') or code.startswith('003'):
                        stock_list.append(stock_str)  # 深圳主板/中小板
                    elif code.startswith('300'):
                        stock_list.append(stock_str)  # 创业板
                    elif code.startswith('8') and len(code) == 6:
                        stock_list.append(stock_str)  # 北交所

            logger.info(f"从QMT获取到 {len(stock_list)} 只A股（已过滤ETF和可转债）")
            return stock_list

        except Exception as e:
            logger.error(f"从QMT获取股票列表失败: {e}")
            # 返回一些常见股票作为备用
            return [
                '000001.SZ',  # 平安银行
                '000002.SZ',  # 万科A
                '600000.SH',  # 浦发银行
                '600036.SH',  # 招商银行
                '600519.SH',  # 贵州茅台
            ]

    def check_data_integrity(self) -> Dict:
        """检查数据完整性"""
        try:
            # 检查缺失数据
            missing = self.conn.execute("""
                SELECT
                    symbol,
                    COUNT(*) as record_count,
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM stock_data
                GROUP BY symbol
                HAVING record_count < 200
            """).fetchdf()

            # 检查异常数据
            abnormal = self.conn.execute("""
                SELECT COUNT(*) as count
                FROM stock_data
                WHERE high < low
                   OR close > high
                   OR close < low
            """).fetchone()[0]

            return {
                'missing_symbols': len(missing),
                'missing_detail': missing.to_dict('records') if not missing.empty else [],
                'abnormal_records': abnormal
            }

        except Exception as e:
            logger.error(f"数据完整性检查失败: {e}")
            return {}

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")


# 便捷函数
def get_duckdb_manager(db_path: str = 'D:/StockData/stock_data.ddb') -> UnifiedDuckDBManager:
    """
    获取DuckDB数据管理器实例

    Args:
        db_path: 数据库文件路径

    Returns:
        UnifiedDuckDBManager实例
    """
    return UnifiedDuckDBManager(db_path)


if __name__ == '__main__':
    # 测试代码
    import time

    print("="*70)
    print("统一DuckDB数据管理器 - 测试")
    print("="*70)
    print("\n⭐ 架构模式：只存储不复权数据，复权数据通过QMT API实时计算")
    print("="*70)

    # 创建管理器
    manager = UnifiedDuckDBManager('D:/StockData/stock_data.ddb')

    # 测试下载
    print("\n[测试1] 下载不复权数据...")
    manager.download_data(['000001.SZ'], '2024-01-01', '2024-12-31')

    # 测试查询不复权数据
    print("\n[测试2] 查询不复权数据（从DuckDB）...")
    df_none = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='none')
    print(f"查询结果: {len(df_none)}条记录")

    # 测试查询复权数据
    print("\n[测试3] 查询前复权数据（从QMT API实时计算）...")
    df_qfq = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='qfq')
    print(f"查询结果: {len(df_qfq)}条记录")

    # 统计信息
    print("\n[测试4] 统计信息...")
    stats = manager.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 关闭
    manager.close()
    print("\n✅ 测试完成")
