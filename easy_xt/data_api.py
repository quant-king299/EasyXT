"""
数据API封装模块
简化xtquant数据接口的调用

⚠️ 线程安全说明：
xtdata.download_history_data2() 和 download_history_data() 方法在并发调用时可能导致卡死。
为了解决这个问题，我们在 DataAPI 类中添加了类级别的线程锁 (_download_lock)，
确保同一时间只有一个线程执行下载操作。

锁保护的方法包括：
- get_price() - 获取价格数据时的下载操作
- get_price_robust() - 健壮获取价格数据时的下载操作
- download_data() - 下载历史数据
- download_history_data_batch() - 批量下载历史数据
- 任何内部调用 download_history_data 或 download_history_data2 的方法

这样可以确保即使在并发场景下，也能正常工作，不会导致卡死。
"""
import pandas as pd
from typing import Union, List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os
import threading  # 添加线程锁支持

# 添加xtquant路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
xtquant_path = os.path.join(project_root, 'xtquant')

if xtquant_path not in sys.path:
    sys.path.insert(0, xtquant_path)

# 尝试导入 xtquant（QMT数据源）
xt_available = False
xt = None
try:
    import xtquant.xtdata as xt
    xt_available = True
    print("[OK] QMT (xtquant.xtdata) imported successfully")
except ImportError:
    # QMT不可用是正常的，继续尝试其他数据源
    pass

# 尝试导入 xqshare（远程xtquant代理）- 仅当配置了环境变量时
XQSHARE_AVAILABLE = False
xqshare_client = None
if os.environ.get('XQSHARE_REMOTE_HOST'):
    try:
        from xqshare.client import connect as xqshare_connect
        # 尝试连接
        xqshare_client = xqshare_connect()
        if xqshare_client.is_connected():
            XQSHARE_AVAILABLE = True
            print("[OK] xqshare (远程xtquant) 连接成功")
        else:
            print("[INFO] xqshare 连接失败")
    except ImportError:
        print("[INFO] xqshare 未安装")
    except Exception as e:
        print(f"[INFO] xqshare 不可用: {e}")

# 尝试导入多数据源
TDX_AVAILABLE = False
try:
    from .realtime_data.providers.tdx_provider import TdxDataProvider
    TDX_AVAILABLE = True
    print("[OK] TDX (通达信) provider available")
except ImportError:
    print("[INFO] TDX provider not available")

EASTMONEY_AVAILABLE = False
try:
    from .realtime_data.providers.eastmoney_provider import EastmoneyDataProvider
    EASTMONEY_AVAILABLE = True
    print("[OK] Eastmoney (东方财富) provider available")
except ImportError:
    print("[INFO] Eastmoney provider not available")

# 打印数据源状态总结
if not (xt_available or TDX_AVAILABLE or EASTMONEY_AVAILABLE):
    print("\n[WARN] 所有数据源都不可用，请至少安装一个：")
    print("  - QMT (推荐用于实盘)")
    print("  - 或使用 TDX/Eastmoney (可用于回测)")

from .utils import StockCodeUtils, TimeUtils, DataUtils, ErrorHandler
from .config import config
from .data_types import ConnectionError, DataError
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time
import pandas as pd


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

            # 检查 stock_daily 表是否存在
            self._check_tables()

        except ImportError:
            print("[ERROR] duckdb未安装，请运行: pip install duckdb")
            raise
        except Exception as e:
            print(f"[ERROR] DuckDB连接失败: {e}")
            raise

    def _check_tables(self):
        """检查必要的数据表是否存在"""
        try:
            tables = self.conn.execute("SHOW TABLES").fetchall()
            table_names = {t[0] for t in tables}

            if 'stock_daily' not in table_names:
                print()
                print("=" * 60)
                print("[WARN] 数据库中缺少 stock_daily 表（日线行情数据）")
                print("=" * 60)
                print()
                print("当前数据库中只有以下表:", ', '.join(sorted(table_names)) if table_names else '（空）')
                print()
                print("你需要先下载日线数据，以下任选一种方式：")
                print()
                print("  方式1（推荐，不需要QMT）：")
                print("    python run_gui.py")
                print("    → 切换到「Tushare下载」标签页")
                print("    → 勾选「日线行情」→ 设置股票数量和年份 → 点击下载")
                print()
                print("  方式2（命令行，需要Tushare Token）：")
                print("    python tools/setup_duckdb.py")
                print()
                print("  方式3（需要QMT）：")
                print("    python run_gui.py")
                print("    → 切换到「数据管理」标签页 → 下载股票数据")
                print()
                print("=" * 60)
                return

            # 检查数据量
            count = self.conn.execute("SELECT COUNT(*) FROM stock_daily").fetchone()[0]
            if count == 0:
                print(f"[WARN] stock_daily 表存在但数据为空（0 条记录），请先下载日线数据")
            else:
                date_range = self.conn.execute(
                    "SELECT MIN(date), MAX(date), COUNT(DISTINCT stock_code) FROM stock_daily"
                ).fetchone()
                print(f"[OK] stock_daily: {date_range[2]} 只股票, {date_range[0]} ~ {date_range[1]}")

        except Exception as e:
            print(f"[WARN] 检查数据表失败: {e}")

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
            err_msg = str(e)
            if 'stock_daily' in err_msg and 'does not exist' in err_msg:
                print(f"[ERROR] 数据查询失败: stock_daily 表不存在")
                print("        请先下载日线数据: python run_gui.py → Tushare下载 → 勾选「日线行情」")
            else:
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


# QMT支持的数据周期 - 基于xtdata官方文档v2023-01-31
SUPPORTED_PERIODS = {
    # Level1数据周期 (标准行情数据)
    'tick': '分笔数据',
    '1m': '1分钟线',
    '5m': '5分钟线', 
    '15m': '15分钟线',
    '30m': '30分钟线',
    '1h': '1小时线',
    '1d': '日线',
    
    # Level2数据周期 (需要Level2权限)
    'l2quote': 'Level2实时行情快照',
    'l2order': 'Level2逐笔委托',
    'l2transaction': 'Level2逐笔成交',
    'l2quoteaux': 'Level2实时行情补充',
    'l2orderqueue': 'Level2委买委卖一档委托队列',
    'l2thousand': 'Level2千档盘口'
}

def validate_period(period: str) -> bool:
    """验证数据周期是否支持"""
    return period in SUPPORTED_PERIODS

def get_supported_periods() -> Dict[str, str]:
    """获取支持的数据周期"""
    return SUPPORTED_PERIODS.copy()

# 推荐的测试股票代码
RECOMMENDED_STOCKS = [
    '000001.SZ',  # 平安银行
    '600000.SH',  # 浦发银行  
    '000002.SZ',  # 万科A
    '600036.SH',  # 招商银行
    '000858.SZ',  # 五粮液
]

def get_recommended_stocks(count: int = 5) -> List[str]:
    """获取推荐的测试股票代码"""
    return RECOMMENDED_STOCKS[:count]

def auto_time_range(days: int = 10) -> tuple[str, str]:
    """自动生成合理的时间范围"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_time = start_date.strftime('%Y%m%d')
    end_time = end_date.strftime('%Y%m%d')
    
    return start_time, end_time

def validate_stock_codes(codes: Union[str, List[str]]) -> tuple[bool, str]:
    """验证股票代码有效性"""
    if isinstance(codes, str):
        codes = [codes]
    
    for code in codes:
        if not isinstance(code, str):
            return False, f"股票代码必须是字符串: {code}"
        
        if '.' not in code:
            return False, f"股票代码格式错误，缺少市场后缀: {code}"
        
        parts = code.split('.')
        if len(parts) != 2:
            return False, f"股票代码格式错误: {code}"
        
        stock_code, market = parts
        if market not in ['SH', 'SZ']:
            return False, f"不支持的市场代码: {market}"
        
        if not stock_code.isdigit() or len(stock_code) != 6:
            return False, f"股票代码必须是6位数字: {stock_code}"
    
    return True, "股票代码验证通过"

class DataAPI:
    """数据API封装类 - 支持多数据源自动降级"""

    # 类级别的线程锁，用于保护 xtdata 的下载操作
    _download_lock = threading.Lock()

    def __init__(self):
        self.xt = xt
        self._connected = False

        # 多数据源支持
        self._active_source = None  # 当前使用的数据源: 'qmt', 'tdx', 'eastmoney'
        self._tdx_provider = None
        self._eastmoney_provider = None

    def connect(self) -> bool:
        """连接数据服务 - 自动选择最佳数据源"""
        print("\n[Connecting to data source...]")

        # 优先级1: 尝试连接 QMT (本地)
        if xt_available:
            print("  Trying QMT (xtquant)...")
            if self._connect_qmt():
                self._active_source = 'qmt'
                print("[OK] Using QMT (xtquant) as data source")
                return True
            print("  [WARN] QMT connection failed")

        # 优先级2: 降级到 xqshare (远程)
        if XQSHARE_AVAILABLE:
            print("  Trying xqshare (远程xtquant)...")
            if self._connect_xqshare():
                self._active_source = 'xqshare'
                print("[OK] Using xqshare (远程xtquant) as data source")
                return True
            print("  [WARN] xqshare connection failed")

        # 优先级3: 降级到 TDX
        if TDX_AVAILABLE:
            print("  Trying TDX (通达信)...")
            if self._connect_tdx():
                self._active_source = 'tdx'
                print("[OK] Using TDX (通达信) as data source")
                return True
            print("  [WARN] TDX connection failed")

        # 优先级4: 降级到 Eastmoney
        if EASTMONEY_AVAILABLE:
            print("  Trying Eastmoney (东方财富)...")
            if self._connect_eastmoney():
                self._active_source = 'eastmoney'
                print("[OK] Using Eastmoney (东方财富) as data source")
                return True
            print("  [WARN] Eastmoney connection failed")

        # 所有数据源都失败
        print("[ERROR] All data sources failed to connect")
        return False

    def _connect_qmt(self) -> bool:
        """连接QMT数据源"""
        if not self.xt:
            return False

        try:
            client = self.xt.get_client()
            connected = client.is_connected() if client else False
            if connected:
                self._connected = True  # ✓ 设置连接状态
            return connected
        except Exception as e:
            print(f"  [INFO] QMT connection failed: {e}")
            return False

    def _connect_xqshare(self) -> bool:
        """连接xqshare数据源（远程xtquant代理）"""
        global xqshare_client
        if not xqshare_client:
            return False
        try:
            if xqshare_client.is_connected():
                self.xt = xqshare_client.xtdata
                self._connected = True
                return True
        except Exception as e:
            print(f"  [INFO] xqshare connection failed: {e}")
        return False

    def _connect_tdx(self) -> bool:
        """连接TDX数据源"""
        try:
            if self._tdx_provider is None:
                self._tdx_provider = TdxDataProvider()
            connected = self._tdx_provider.connect()
            if connected:
                self._connected = True  # ✓ 设置连接状态
            return connected
        except Exception as e:
            print(f"  [INFO] TDX connection failed: {e}")
            return False

    def _connect_eastmoney(self) -> bool:
        """连接东方财富数据源"""
        try:
            if self._eastmoney_provider is None:
                self._eastmoney_provider = EastmoneyDataProvider()
            connected = self._eastmoney_provider.connect()
            if connected:
                self._connected = True  # ✓ 设置连接状态
            return connected
        except Exception as e:
            print(f"  [INFO] Eastmoney connection failed: {e}")
            return False

    def get_active_source(self) -> str:
        """获取当前使用的数据源"""
        return self._active_source if self._active_source else "None"
    
    @ErrorHandler.handle_api_error
    def get_price(self,
                  codes: Union[str, List[str]],
                  start: Optional[str] = None,
                  end: Optional[str] = None,
                  period: str = '1d',
                  count: Optional[int] = None,
                  fields: Optional[List[str]] = None,
                  adjust: str = 'front') -> pd.DataFrame:
        """
        获取股票价格数据 - 支持多数据源自动降级

        Args:
            codes: 股票代码，支持单个或多个
            start: 开始日期，支持多种格式
            end: 结束日期，支持多种格式
            period: 周期，支持的周期类型见SUPPORTED_PERIODS
            count: 数据条数，如果指定则忽略start
            fields: 字段列表，默认['open', 'high', 'low', 'close', 'volume']
            adjust: 复权类型，'front'前复权, 'back'后复权, 'none'不复权

        Returns:
            DataFrame: 价格数据

        Raises:
            ConnectionError: 所有数据源都连接失败
            DataError: 数据获取失败
            ValueError: 不支持的周期类型或股票代码无效
        """
        # 验证周期类型
        if not validate_period(period):
            supported_list = ', '.join(SUPPORTED_PERIODS.keys())
            raise ValueError(f"不支持的数据周期 '{period}'。支持的周期: {supported_list}")

        # 根据当前使用的数据源调用相应方法
        if self._active_source in ('qmt', 'xqshare'):
            return self._get_price_qmt(codes, start, end, period, count, fields, adjust)
        elif self._active_source == 'tdx':
            return self._get_price_tdx(codes, start, end, period, count, fields, adjust)
        elif self._active_source == 'eastmoney':
            return self._get_price_eastmoney(codes, start, end, period, count, fields, adjust)
        else:
            raise ConnectionError("数据服务未连接，请先调用init_data()")

    def _get_price_qmt(self, codes, start, end, period, count, fields, adjust):
        """使用QMT获取价格数据（原有逻辑）"""
        if not self.xt:
            raise ConnectionError("QMT (xtquant) 不可用")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        # 标准化股票代码
        # normalize_codes 已经能够正确处理字符串（包括逗号分隔的字符串）和列表
        codes = StockCodeUtils.normalize_codes(codes)

        # 处理时间参数
        from datetime import datetime
        if count:
            end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            start_date = ''
        else:
            start_date = TimeUtils.normalize_date(start) if start else '20200101'
            end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            count = -1
        
        # 处理字段
        if not fields:
            fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
        # 确保 fields 是列表类型
        elif isinstance(fields, str):
            fields = [fields]
        elif not isinstance(fields, list):
            fields = list(fields)
        
        # 处理复权类型
        dividend_map = {
            'front': 'front',
            'back': 'back', 
            'none': 'none',
            '前复权': 'front',
            '后复权': 'back',
            '不复权': 'none'
        }
        dividend_type = dividend_map.get(adjust, 'front')
        
        try:
            # 先下载历史数据（使用正确的API）
            try:
                print(f"正在下载 {codes} 的历史数据...")
                
                # 对于分钟数据，限制时间范围避免数据量过大
                if period in ['1m', '5m', '15m', '30m']:
                    # 分钟数据只下载最近几天
                    from datetime import timedelta
                    end_dt = datetime.now()
                    start_dt = end_dt - timedelta(days=3)  # 只下载最近3天
                    download_start = start_dt.strftime('%Y%m%d')
                    download_end = end_dt.strftime('%Y%m%d')
                else:
                    download_start = start_date if start_date else '20200101'
                    download_end = end_date if end_date else datetime.now().strftime('%Y%m%d')

                # 使用线程锁保护下载操作，防止并发调用导致卡死
                with DataAPI._download_lock:
                    self.xt.download_history_data2(
                        stock_list=codes,
                        period=period,
                        start_time=download_start,
                        end_time=download_end
                    )
                print("历史数据下载完成")
            except Exception as download_error:
                print(f"数据下载警告: {download_error}")
                # 下载失败不影响后续获取，可能本地已有数据
            
            # 调用xtquant接口获取数据
            # 对于分钟数据，使用count参数限制数据量
            if period in ['1m', '5m', '15m', '30m'] and count is None:
                # 分钟数据默认最多获取100条
                actual_count = 100
            else:
                actual_count = count if count else -1
            
            data = self.xt.get_market_data_ex(
                field_list=fields,
                stock_list=codes,
                period=period,
                start_time=start_date if start_date else '20200101',
                end_time=end_date if end_date else datetime.now().strftime('%Y%m%d'),
                count=actual_count,
                dividend_type=dividend_type,
                fill_data=config.get('data.fill_data', True)
            )
            
            if not data:
                raise DataError("xtquant返回空数据，可能是网络问题或股票代码错误")
            
            # 检查是否所有字段都是空的
            all_empty = True
            for field, field_data in data.items():
                if field_data is not None and hasattr(field_data, 'empty') and not field_data.empty:
                    all_empty = False
                    break
            
            if all_empty:
                raise DataError(
                    f"无法获取股票 {codes} 的数据。\n\n"
                    f"🔧 快速解决方案（推荐）：\n"
                    f"1️⃣ 使用项目提供的一键下载工具：\n"
                    f"   cd tools\n"
                    f"   python download_all_stocks.py\n\n"
                    f"2️⃣ 或安装pytdx自动使用通达信数据：\n"
                    f"   pip install pytdx\n\n"
                    f"3️⃣ 或在QMT客户端手动下载数据\n"
                    f"   （终端 → 品种管理 → 下载历史数据）\n\n"
                    f"详细说明：docs/assets/TROUBLESHOOTING.md 第3节"
                )
            
            # 处理返回数据
            if period == 'tick':
                # 分笔数据处理
                result_list = []
                for code, tick_data in data.items():
                    if tick_data is not None and len(tick_data) > 0:
                        df = pd.DataFrame(tick_data)
                        df['code'] = code
                        
                        # 处理时间字段 - 兼容不同的字段名称
                        time_field = None
                        for field in ['time', 'timestamp', 'datetime', 'ttime']:
                            if field in df.columns:
                                time_field = field
                                break
                        
                        if time_field:
                            # 尝试不同的时间格式转换
                            try:
                                if df[time_field].dtype in ['int64', 'float64']:
                                    # 检查是否是毫秒时间戳
                                    sample_time = df[time_field].iloc[0]
                                    if sample_time > 1000000000000:  # 毫秒时间戳
                                        df['time'] = pd.to_datetime(df[time_field], unit='ms')
                                    else:  # 秒时间戳
                                        df['time'] = pd.to_datetime(df[time_field], unit='s')
                                else:
                                    # 字符串格式直接转换
                                    df['time'] = pd.to_datetime(df[time_field])
                            except Exception as e:
                                print(f"时间字段转换失败: {e}")
                                # 使用当前时间作为默认值
                                df['time'] = pd.Timestamp.now()
                        else:
                            # 如果没有找到时间字段，使用当前时间
                            print("警告: 未找到时间字段，使用当前时间")
                            df['time'] = pd.Timestamp.now()
                        
                        result_list.append(df)
                
                if result_list:
                    return pd.concat(result_list, ignore_index=True)
                else:
                    raise DataError("tick数据为空")
            else:
                # K线数据处理 - 处理get_market_data_ex的返回格式
                # get_market_data_ex返回格式: {股票代码: DataFrame(时间×字段)}
                
                if not data:
                    raise DataError("xtquant返回空数据")
                
                # 检查是否有有效数据
                has_data = False
                for stock_code, stock_data in data.items():
                    if stock_data is not None and hasattr(stock_data, 'empty') and not stock_data.empty:
                        has_data = True
                        break
                
                if not has_data:
                    raise DataError(
                        f"无法获取股票 {codes} 的数据。\n\n"
                        f"🔧 快速解决方案（推荐）：\n"
                        f"1️⃣ 使用项目提供的一键下载工具：\n"
                        f"   cd tools\n"
                        f"   python download_all_stocks.py\n\n"
                        f"2️⃣ 或安装pytdx自动使用通达信数据：\n"
                        f"   pip install pytdx\n\n"
                        f"3️⃣ 或在QMT客户端手动下载数据\n"
                        f"   （终端 → 品种管理 → 下载历史数据）\n\n"
                        f"详细说明：docs/assets/TROUBLESHOOTING.md 第3节"
                    )
                
                # 重构数据格式 - 适配get_market_data_ex新格式
                result_list = []
                
                # 遍历每只股票的数据
                for stock_code, stock_df in data.items():
                    if stock_df is None or stock_df.empty:
                        continue
                    
                    # 为每个时间点创建记录
                    for time_idx in stock_df.index:
                        record = {
                            'time': time_idx,  # 使用索引作为时间
                            'code': stock_code
                        }
                        
                        # 添加各个字段的数据
                        for field in fields:
                            if field == 'time':
                                continue  # 已经处理
                            
                            if field in stock_df.columns:
                                record[field] = stock_df.loc[time_idx, field]
                            else:
                                record[field] = None
                        
                        result_list.append(record)
                
                if result_list:
                    # 创建最终DataFrame
                    final_df = pd.DataFrame(result_list)
                    
                    # 修复时间格式 - 基于调试结果的正确处理方式
                    try:
                        # 索引时间格式处理
                        if final_df['time'].dtype in ['int64', 'float64']:
                            # 检查是否是分钟数据格式 (YYYYMMDDHHMMSS)
                            sample_time = final_df['time'].iloc[0]
                            if sample_time > 20000000000000:  # 分钟数据格式
                                # YYYYMMDDHHMMSS格式
                                final_df['time'] = pd.to_datetime(final_df['time'].astype(str), format='%Y%m%d%H%M%S', errors='coerce')
                            else:
                                # YYYYMMDD格式
                                final_df['time'] = pd.to_datetime(final_df['time'].astype(str), format='%Y%m%d', errors='coerce')
                        elif final_df['time'].dtype == 'object':
                            # 如果是字符串格式，尝试直接转换
                            final_df['time'] = pd.to_datetime(final_df['time'], errors='coerce')
                        
                        # 如果转换失败，尝试其他格式
                        notna_values = final_df['time'].notna()
                        notna_count = notna_values.sum()
                        if notna_count == 0:
                            print("警告: 时间格式转换失败")
                    except Exception as e:
                        print(f"时间格式处理警告: {e}")
                    
                    # 过滤掉无效数据
                    final_df = final_df.dropna(subset=['time'])
                    
                    if final_df.empty:
                        raise DataError("时间格式转换后数据为空")
                    
                    return final_df.sort_values(['code', 'time']).reset_index(drop=True)
                else:
                    raise DataError("未能构建有效的数据结构")
        
        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取价格数据失败: {str(e)}")
            raise DataError(f"获取价格数据失败: {str(e)}")

    def _get_price_tdx(self, codes, start, end, period, count, fields, adjust):
        """使用TDX获取价格数据"""
        if not self._tdx_provider:
            raise ConnectionError("TDX数据源未初始化")

        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用connect()")

        # 标准化股票代码
        codes = StockCodeUtils.normalize_codes(codes)

        # 处理时间参数
        from datetime import datetime
        if count:
            end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            start_date = None
        else:
            start_date = TimeUtils.normalize_date(start) if start else '20200101'
            end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            count = 1000  # TDX使用count参数

        # 处理字段
        if not fields:
            fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
        elif isinstance(fields, str):
            fields = [fields]
        elif not isinstance(fields, list):
            fields = list(fields)

        # 周期映射
        period_map = {
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '1d': 'D',
            '1w': 'W',
            '1M': 'M'
        }
        tdx_period = period_map.get(period, 'D')

        try:
            # 批量获取K线数据
            all_data = []
            for code in codes:
                try:
                    # 移除市场后缀，TDX provider会自动处理
                    clean_code = code.split('.')[0]

                    kline_data = self._tdx_provider.get_kline_data(
                        code=clean_code,
                        period=tdx_period,
                        count=min(count, 1000)  # TDX限制每次最多1000条
                    )

                    if kline_data:
                        for item in kline_data:
                            record = {
                                'time': item.get('datetime', ''),
                                'code': code
                            }

                            # 添加字段
                            if 'open' in fields:
                                record['open'] = item.get('open', 0)
                            if 'high' in fields:
                                record['high'] = item.get('high', 0)
                            if 'low' in fields:
                                record['low'] = item.get('low', 0)
                            if 'close' in fields:
                                record['close'] = item.get('close', 0)
                            if 'volume' in fields:
                                record['volume'] = item.get('volume', 0)
                            if 'amount' in fields:
                                record['amount'] = item.get('amount', 0)

                            all_data.append(record)

                except Exception as e:
                    ErrorHandler.log_error(f"获取TDX数据失败 {code}: {e}")
                    continue

            if not all_data:
                raise DataError(f"无法获取股票 {codes} 的TDX数据")

            # 创建DataFrame
            df = pd.DataFrame(all_data)

            # 处理时间格式
            try:
                df['time'] = pd.to_datetime(df['time'], errors='coerce')
                df = df.dropna(subset=['time'])
            except Exception as e:
                ErrorHandler.log_error(f"时间格式转换失败: {e}")

            # 过滤时间范围
            if start_date:
                df = df[df['time'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['time'] <= pd.to_datetime(end_date)]

            if df.empty:
                raise DataError(f"时间范围内无数据: {start_date} - {end_date}")

            return df.sort_values(['code', 'time']).reset_index(drop=True)

        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取TDX价格数据失败: {str(e)}")
            raise DataError(f"获取TDX价格数据失败: {str(e)}")

    def _get_price_eastmoney(self, codes, start, end, period, count, fields, adjust):
        """使用Eastmoney获取价格数据"""
        if not self._eastmoney_provider:
            raise ConnectionError("Eastmoney数据源未初始化")

        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用connect()")

        # 标准化股票代码
        codes = StockCodeUtils.normalize_codes(codes)

        # 处理时间参数
        from datetime import datetime
        if count:
            end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            start_date = None
        else:
            start_date = TimeUtils.normalize_date(start) if start else '20200101'
            end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            count = 1000  # Eastmoney使用count参数

        # 处理字段
        if not fields:
            fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
        elif isinstance(fields, str):
            fields = [fields]
        elif not isinstance(fields, list):
            fields = list(fields)

        # 周期映射
        period_map = {
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '1d': 'D',
            '1w': 'W',
            '1M': 'M'
        }
        em_period = period_map.get(period, 'D')

        try:
            # 批量获取K线数据
            all_data = []
            for code in codes:
                try:
                    # 移除市场后缀，Eastmoney provider会自动处理
                    clean_code = code.split('.')[0]

                    kline_data = self._eastmoney_provider.get_kline_data(
                        code=clean_code,
                        period=em_period,
                        count=min(count, 1000),
                        start_date=start_date,
                        end_date=end_date
                    )

                    if kline_data:
                        for item in kline_data:
                            record = {
                                'time': item.get('datetime', ''),
                                'code': code
                            }

                            # 添加字段
                            if 'open' in fields:
                                record['open'] = item.get('open', 0)
                            if 'high' in fields:
                                record['high'] = item.get('high', 0)
                            if 'low' in fields:
                                record['low'] = item.get('low', 0)
                            if 'close' in fields:
                                record['close'] = item.get('close', 0)
                            if 'volume' in fields:
                                record['volume'] = item.get('volume', 0)
                            if 'amount' in fields:
                                record['amount'] = item.get('amount', 0)

                            all_data.append(record)

                except Exception as e:
                    ErrorHandler.log_error(f"获取Eastmoney数据失败 {code}: {e}")
                    continue

            if not all_data:
                raise DataError(f"无法获取股票 {codes} 的Eastmoney数据")

            # 创建DataFrame
            df = pd.DataFrame(all_data)

            # 处理时间格式
            try:
                df['time'] = pd.to_datetime(df['time'], errors='coerce')
                df = df.dropna(subset=['time'])
            except Exception as e:
                ErrorHandler.log_error(f"时间格式转换失败: {e}")

            # 过滤时间范围
            if start_date:
                df = df[df['time'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['time'] <= pd.to_datetime(end_date)]

            if df.empty:
                raise DataError(f"时间范围内无数据: {start_date} - {end_date}")

            return df.sort_values(['code', 'time']).reset_index(drop=True)

        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取Eastmoney价格数据失败: {str(e)}")
            raise DataError(f"获取Eastmoney价格数据失败: {str(e)}")

    @ErrorHandler.handle_api_error
    def get_current_price(self, codes: Union[str, List[str]]) -> pd.DataFrame:
        """
        获取当前价格（实时行情）
        
        Args:
            codes: 股票代码
            
        Returns:
            DataFrame: 实时价格数据
            
        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        codes = StockCodeUtils.normalize_codes(codes)
        
        try:
            data = self.xt.get_full_tick(codes)
            if not data:
                raise DataError("无法获取实时行情数据")
            
            result_list = []
            for code, tick_info in data.items():
                if tick_info:
                    result_list.append({
                        'code': code,
                        'price': tick_info.get('lastPrice', 0),
                        'open': tick_info.get('open', 0),
                        'high': tick_info.get('high', 0),
                        'low': tick_info.get('low', 0),
                        'pre_close': tick_info.get('lastClose', 0),
                        'volume': tick_info.get('volume', 0),
                        'amount': tick_info.get('amount', 0),
                        'time': tick_info.get('time', 0)
                    })
            
            if not result_list:
                raise DataError("未获取到有效的实时行情数据")
            
            return pd.DataFrame(result_list)
        
        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取实时价格失败: {str(e)}")
            raise DataError(f"获取实时价格失败: {str(e)}")

    @ErrorHandler.handle_api_error
    def get_order_book(self, codes: Union[str, List[str]]) -> pd.DataFrame:
        """
        获取五档行情数据（买卖盘口）

        注意：直接调用 get_full_tick 获取，无需预先订阅

        Args:
            codes: 股票代码

        Returns:
            DataFrame: 包含五档买卖价和量的数据
            字段包括：
            - code: 股票代码
            - lastPrice: 最新价
            - bid1-bid5: 买一到买五价格
            - ask1-ask5: 卖一到卖五价格
            - bidVol1-bidVol5: 买一到买五量
            - askVol1-askVol5: 卖一到卖五量

        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")

        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")

        codes = StockCodeUtils.normalize_codes(codes)

        try:
            # 直接获取五档tick数据，无需订阅
            tick_data = self.xt.get_full_tick(codes)

            if not tick_data:
                raise DataError("无法获取五档行情数据")

            result_list = []
            for code, tick_info in tick_data.items():
                if tick_info:
                    # 获取askPrice和bidPrice - 根据文档这些可能是数组
                    ask_price = tick_info.get('askPrice', 0)
                    bid_price = tick_info.get('bidPrice', 0)
                    ask_vol = tick_info.get('askVol', 0)
                    bid_vol = tick_info.get('bidVol', 0)

                    # 处理askPrice和bidPrice可能是数组的情况
                    def extract_price_or_vol(value, index=0):
                        """提取价格或量，支持数组或单个值"""
                        if hasattr(value, '__len__') and not isinstance(value, str):
                            # 是数组或列表
                            if len(value) > index:
                                return value[index]
                            return 0
                        # 是单个值
                        if index == 0:
                            return value if value else 0
                        return 0

                    # 提取五档行情数据
                    order_book_data = {
                        'code': code,
                        'lastPrice': tick_info.get('lastPrice', 0),
                        'open': tick_info.get('open', 0),
                        'high': tick_info.get('high', 0),
                        'low': tick_info.get('low', 0),
                        'preClose': tick_info.get('lastClose', 0),
                        'volume': tick_info.get('volume', 0),
                        'amount': tick_info.get('amount', 0),
                        'time': tick_info.get('time', 0),
                        # 五档买价 - 使用askPrice和bidPrice
                        'bid1': extract_price_or_vol(bid_price, 0),
                        'bid2': extract_price_or_vol(bid_price, 1),
                        'bid3': extract_price_or_vol(bid_price, 2),
                        'bid4': extract_price_or_vol(bid_price, 3),
                        'bid5': extract_price_or_vol(bid_price, 4),
                        # 五档卖价
                        'ask1': extract_price_or_vol(ask_price, 0),
                        'ask2': extract_price_or_vol(ask_price, 1),
                        'ask3': extract_price_or_vol(ask_price, 2),
                        'ask4': extract_price_or_vol(ask_price, 3),
                        'ask5': extract_price_or_vol(ask_price, 4),
                        # 五档买量
                        'bidVol1': extract_price_or_vol(bid_vol, 0),
                        'bidVol2': extract_price_or_vol(bid_vol, 1),
                        'bidVol3': extract_price_or_vol(bid_vol, 2),
                        'bidVol4': extract_price_or_vol(bid_vol, 3),
                        'bidVol5': extract_price_or_vol(bid_vol, 4),
                        # 五档卖量
                        'askVol1': extract_price_or_vol(ask_vol, 0),
                        'askVol2': extract_price_or_vol(ask_vol, 1),
                        'askVol3': extract_price_or_vol(ask_vol, 2),
                        'askVol4': extract_price_or_vol(ask_vol, 3),
                        'askVol5': extract_price_or_vol(ask_vol, 4),
                    }
                    result_list.append(order_book_data)

            if not result_list:
                raise DataError("未获取到有效的五档行情数据")

            return pd.DataFrame(result_list)

        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取五档行情失败: {str(e)}")
            raise DataError(f"获取五档行情失败: {str(e)}")

    @ErrorHandler.handle_api_error
    def get_l2_quote(self, codes: Union[str, List[str]]) -> Dict[str, Dict]:
        """
        获取Level2五档行情数据（专用接口）

        Args:
            codes: 股票代码

        Returns:
            Dict: {股票代码: {字段: 值}}
            包含完整的五档买卖价量和逐笔数据

        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")

        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")

        codes = StockCodeUtils.normalize_codes(codes)

        try:
            # 尝试使用get_l2_quote接口
            if hasattr(self.xt, 'get_l2_quote'):
                # Level2行情接口
                l2_data = self.xt.get_l2_quote(codes)
                if l2_data:
                    return l2_data
                else:
                    raise DataError("Level2行情数据为空，可能需要Level2权限")

            # 如果没有get_l2_quote，使用subscribe_quote订阅后获取
            elif hasattr(self.xt, 'subscribe_quote'):
                # 订阅行情
                for code in codes:
                    try:
                        self.xt.subscribe_quote(code, period='tick')
                    except:
                        pass

                # 再次获取完整tick
                tick_data = self.xt.get_full_tick(codes)

                result = {}
                for code, tick_info in tick_data.items():
                    if tick_info:
                        # 检查是否有五档数据
                        has_bid_ask = (
                            tick_info.get('bid1', 0) > 0 or
                            tick_info.get('ask1', 0) > 0
                        )

                        if has_bid_ask:
                            result[code] = tick_info
                        else:
                            # 如果没有五档数据，添加提示
                            result[code] = {
                                **tick_info,
                                '_note': '当前未获取到五档数据，可能需要Level2权限或交易时间内'
                            }

                return result if result else tick_data

            else:
                # 使用get_full_tick作为后备
                tick_data = self.xt.get_full_tick(codes)
                return tick_data if tick_data else {}

        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取Level2行情失败: {str(e)}")
            raise DataError(f"获取Level2行情失败: {str(e)}")

    @ErrorHandler.handle_api_error
    def get_financial_data(self, 
                          codes: Union[str, List[str]], 
                          tables: Optional[List[str]] = None,
                          start: Optional[str] = None, 
                          end: Optional[str] = None,
                          report_type: str = 'report_time') -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        获取财务数据
        
        Args:
            codes: 股票代码
            tables: 财务表类型，如['Balance', 'Income', 'CashFlow']
            start: 开始时间
            end: 结束时间
            report_type: 'report_time'报告期, 'announce_time'公告期
            
        Returns:
            Dict: {股票代码: {表名: DataFrame}}
            
        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        codes = StockCodeUtils.normalize_codes(codes)
        
        if not tables:
            tables = ['Balance', 'Income', 'CashFlow']
        
        start_date = TimeUtils.normalize_date(start) if start else '20200101'
        end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
        
        try:
            data = self.xt.get_financial_data(
                stock_list=codes,
                table_list=tables,
                start_time=start_date,
                end_time=end_date,
                report_type=report_type
            )
            
            if not data:
                raise DataError("未获取到财务数据")
            
            return data
        
        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取财务数据失败: {str(e)}")
            raise DataError(f"获取财务数据失败: {str(e)}")
    
    @ErrorHandler.handle_api_error
    def get_stock_list(self, sector: Optional[str] = None) -> List[str]:
        """
        获取股票列表

        Args:
            sector: 板块名称，如:
                - 'A股' (SH+SZ，所有A股)
                - 'SH' (上海市场)
                - 'SZ' (深圳市场)
                - '沪深300' (沪深300成分股)
                - '中证500' (中证500成分股)
                - 等等...

        Returns:
            List[str]: 股票代码列表

        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败

        Examples:
            >>> # 获取所有A股
            >>> stocks = api.get_stock_list('A股')
            >>> # 获取沪深300
            >>> stocks = api.get_stock_list('沪深300')
            >>> # 获取上海市场
            >>> stocks = api.get_stock_list('SH')
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")

        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")

        try:
            if sector:
                # 特殊处理：A股 = SH + SZ（使用市场代码）
                if sector == 'A股':
                    sh_stocks = self.xt.get_stock_list_in_sector('SH')
                    sz_stocks = self.xt.get_stock_list_in_sector('SZ')
                    stock_list = (sh_stocks or []) + (sz_stocks or [])
                else:
                    stock_list = self.xt.get_stock_list_in_sector(sector)
            else:
                # 默认获取所有A股
                sh_stocks = self.xt.get_stock_list_in_sector('SH')
                sz_stocks = self.xt.get_stock_list_in_sector('SZ')
                stock_list = (sh_stocks or []) + (sz_stocks or [])

            if not stock_list:
                raise DataError(f"未获取到股票列表，板块: {sector}")

            return stock_list
        
        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取股票列表失败: {str(e)}")
            raise DataError(f"获取股票列表失败: {str(e)}")
    
    @ErrorHandler.handle_api_error
    def get_trading_dates(self, 
                         market: str = 'SH', 
                         start: Optional[str] = None, 
                         end: Optional[str] = None,
                         count: int = -1) -> List[str]:
        """
        获取交易日列表
        
        Args:
            market: 市场代码，'SH'或'SZ'
            start: 开始日期
            end: 结束日期
            count: 数据条数
            
        Returns:
            List[str]: 交易日列表
            
        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        start_date = TimeUtils.normalize_date(start) if start else ''
        end_date = TimeUtils.normalize_date(end) if end else ''
        
        try:
            dates = self.xt.get_trading_dates(market, start_date, end_date, count)
            if not dates:
                raise DataError("未获取到交易日数据")
            
            # 转换时间戳为日期字符串
            return [TimeUtils.normalize_date(datetime.fromtimestamp(ts/1000)) for ts in dates]
        
        except Exception as e:
            if isinstance(e, (ConnectionError, DataError)):
                raise
            ErrorHandler.log_error(f"获取交易日失败: {str(e)}")
            raise DataError(f"获取交易日失败: {str(e)}")
    
    def download_data(self, 
                     codes: Union[str, List[str]], 
                     period: str = '1d',
                     start: Optional[str] = None, 
                     end: Optional[str] = None) -> bool:
        """
        下载历史数据到本地
        
        Args:
            codes: 股票代码
            period: 周期
            start: 开始日期
            end: 结束日期
            
        Returns:
            bool: 是否成功
            
        Raises:
            ConnectionError: 连接失败
            DataError: 数据下载失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法下载数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        codes = StockCodeUtils.normalize_codes(codes)
        start_date = TimeUtils.normalize_date(start) if start else '20200101'
        end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
        
        try:
            # 使用线程锁保护下载操作，防止并发调用导致卡死
            with DataAPI._download_lock:
                for code in codes:
                    self.xt.download_history_data(code, period, start_date, end_date)
            return True
        
        except Exception as e:
            ErrorHandler.log_error(f"下载数据失败: {str(e)}")
            raise DataError(f"下载数据失败: {str(e)}")
    
    def download_history_data_batch(self, 
                                  stock_list: Union[str, List[str]], 
                                  period: str = '1d',
                                  start_time: str = '',
                                  end_time: str = '') -> Dict[str, bool]:
        """
        批量下载历史数据（使用xtdata.download_history_data2）
        
        Args:
            stock_list: 股票代码列表
            period: 数据周期，如'1d', '1m', '5m'等
            start_time: 开始时间，格式YYYYMMDD
            end_time: 结束时间，格式YYYYMMDD
            
        Returns:
            Dict[str, bool]: 每只股票的下载结果 {股票代码: 是否成功}
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法下载数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        # 标准化股票代码
        if isinstance(stock_list, str):
            stock_list = [stock_list]
        stock_list = StockCodeUtils.normalize_codes(stock_list)
        
        # 结果字典
        results = {}

        # 批量下载数据（使用线程锁保护，防止并发调用导致卡死）
        with DataAPI._download_lock:  # 获取类级别锁
            try:
                self.xt.download_history_data2(
                    stock_list=stock_list,
                    period=period,
                    start_time=start_time,
                    end_time=end_time
                )

                # 下载完成后，验证每只股票的数据是否真正下载成功
                for stock in stock_list:
                    try:
                        # 尝试获取少量数据来验证下载是否成功
                        test_data = self.xt.get_local_data(
                            field_list=['open', 'close', 'volume'],
                            stock_list=[stock],
                            period=period,
                            start_time=start_time,
                            end_time=end_time,
                            count=1
                        )
                        # 如果能获取到数据且不为空，则认为下载成功
                        if stock in test_data and test_data[stock] is not None and len(test_data[stock]) > 0:
                            results[stock] = True
                        else:
                            results[stock] = False
                    except Exception:
                        results[stock] = False

            except Exception as e:
                # 如果出现异常，尝试逐个下载
                print(f"批量下载失败，尝试逐个下载: {e}")
                for stock in stock_list:
                    try:
                        # 逐个下载时也需要锁保护（已经在with块中）
                        self.xt.download_history_data2(
                            stock_list=[stock],
                            period=period,
                            start_time=start_time,
                            end_time=end_time
                        )

                        # 验证数据是否真正下载成功
                        try:
                            test_data = self.xt.get_local_data(
                                field_list=['open', 'close', 'volume'],
                                stock_list=[stock],
                                period=period,
                                start_time=start_time,
                                end_time=end_time,
                                count=1
                            )
                            if stock in test_data and test_data[stock] is not None and len(test_data[stock]) > 0:
                                results[stock] = True
                                print(f"{stock} 历史数据下载完成并验证成功")
                            else:
                                results[stock] = False
                                print(f"{stock} 历史数据下载完成但验证失败")
                        except Exception:
                            results[stock] = False
                            print(f"{stock} 历史数据下载完成但验证失败")
                    except Exception as e2:
                        results[stock] = False
                        print(f"{stock} 下载失败: {e2}")

        return results
    
    @ErrorHandler.handle_api_error
    def get_price_robust(self, 
                        codes: Union[str, List[str]], 
                        start: Optional[str] = None, 
                        end: Optional[str] = None, 
                        period: str = '1d',
                        count: Optional[int] = None,
                        fields: Optional[List[str]] = None,
                        adjust: str = 'front',
                        max_retries: int = 3) -> pd.DataFrame:
        """
        健壮的股票价格数据获取（改进版）
        
        Args:
            codes: 股票代码，支持单个或多个
            start: 开始日期，支持多种格式
            end: 结束日期，支持多种格式  
            period: 周期，支持的周期类型见SUPPORTED_PERIODS
            count: 数据条数，如果指定则忽略start
            fields: 字段列表，默认['open', 'high', 'low', 'close', 'volume']
            adjust: 复权类型，'front'前复权, 'back'后复权, 'none'不复权
            max_retries: 最大重试次数
            
        Returns:
            DataFrame: 价格数据
            
        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败
            ValueError: 不支持的周期类型或股票代码无效
        """
        # 验证周期类型
        if not validate_period(period):
            supported_list = ', '.join(SUPPORTED_PERIODS.keys())
            raise ValueError(f"不支持的数据周期 '{period}'。支持的周期: {supported_list}")
        
        # 验证股票代码
        is_valid, message = validate_stock_codes(codes)
        if not is_valid:
            raise ValueError(f"股票代码验证失败: {message}")
        
        # 如果xtquant不可用，直接报错
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        # 标准化股票代码
        # normalize_codes 已经能够正确处理字符串（包括逗号分隔的字符串）和列表
        codes = StockCodeUtils.normalize_codes(codes)
        
        # 智能时间范围处理
        if count:
            end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            start_date = ''
        else:
            if not start and not end:
                # 如果没有指定时间范围，使用智能默认值
                start_date, end_date = auto_time_range(10)
            else:
                start_date = TimeUtils.normalize_date(start) if start else '20200101'
                end_date = TimeUtils.normalize_date(end) if end else datetime.now().strftime('%Y%m%d')
            count = -1
        
        # 处理字段
        if not fields:
            fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
        # 确保 fields 是列表类型
        elif isinstance(fields, str):
            fields = [fields]
        elif not isinstance(fields, list):
            fields = list(fields)
        
        # 处理复权类型
        dividend_map = {
            'front': 'front',
            'back': 'back', 
            'none': 'none',
            '前复权': 'front',
            '后复权': 'back',
            '不复权': 'none'
        }
        dividend_type = dividend_map.get(adjust, 'front')
        
        # 多次重试获取数据
        last_error = None
        for attempt in range(max_retries):
            try:
                # 先下载历史数据
                try:
                    print(f"正在下载 {codes} 的历史数据... (第{attempt+1}次尝试)")
                    
                    # 对于分钟数据，限制时间范围避免数据量过大
                    if period in ['1m', '5m', '15m', '30m']:
                        # 分钟数据只下载最近几天
                        download_start, download_end = auto_time_range(3)
                    else:
                        download_start = start_date if start_date else '20200101'
                        download_end = end_date if end_date else datetime.now().strftime('%Y%m%d')

                    # 使用线程锁保护下载操作，防止并发调用导致卡死
                    with DataAPI._download_lock:
                        self.xt.download_history_data2(
                            stock_list=codes,
                            period=period,
                            start_time=download_start,
                            end_time=download_end
                        )
                    print("历史数据下载完成")
                except Exception as download_error:
                    print(f"数据下载警告: {download_error}")
                    # 下载失败不影响后续获取，可能本地已有数据
                
                # 调用xtquant接口获取数据
                # 对于分钟数据，使用count参数限制数据量
                if period in ['1m', '5m', '15m', '30m'] and count is None:
                    # 分钟数据默认最多获取100条
                    actual_count = 100
                else:
                    actual_count = count if count else -1
                
                data = self.xt.get_market_data_ex(
                    field_list=fields,
                    stock_list=codes,
                    period=period,
                    start_time=start_date if start_date else '20200101',
                    end_time=end_date if end_date else datetime.now().strftime('%Y%m%d'),
                    count=actual_count,
                    dividend_type=dividend_type,
                    fill_data=config.get('data.fill_data', True)
                )
                
                if not data:
                    raise DataError("xtquant返回空数据，可能是网络问题或股票代码错误")
                
                # 检查是否所有字段都是空的
                all_empty = True
                for field, field_data in data.items():
                    if field_data is not None and hasattr(field_data, 'empty') and not field_data.empty:
                        all_empty = False
                        break
                
                if all_empty:
                    raise DataError(f"无法获取股票 {codes} 的数据。建议：\n1. 检查股票代码是否正确\n2. 尝试使用推荐的股票代码: {get_recommended_stocks()}\n3. 确保时间范围合理\n4. 在迅投客户端中手动下载相关股票的历史数据")
                
                # 处理返回数据（使用原有的数据处理逻辑）
                if period == 'tick':
                    # 分笔数据处理
                    result_list = []
                    for code, tick_data in data.items():
                        if tick_data is not None and len(tick_data) > 0:
                            df = pd.DataFrame(tick_data)
                            df['code'] = code
                            df['time'] = pd.to_datetime(df['time'], unit='ms')
                            result_list.append(df)
                    
                    if result_list:
                        return pd.concat(result_list, ignore_index=True)
                    else:
                        raise DataError("tick数据为空")
                else:
                    # K线数据处理 - 适配get_market_data_ex新格式
                    if not data:
                        raise DataError("xtquant返回空数据")
                    
                    # 检查是否有有效数据
                    has_data = False
                    for stock_code, stock_data in data.items():
                        if stock_data is not None and hasattr(stock_data, 'empty') and not stock_data.empty:
                            has_data = True
                            break
                    
                    if not has_data:
                        raise DataError(f"无法获取股票 {codes} 的数据。建议使用推荐股票: {get_recommended_stocks()}")
                    
                    # 重构数据格式 - 适配get_market_data_ex新格式
                    result_list = []
                    
                    # 遍历每只股票的数据
                    for stock_code, stock_df in data.items():
                        if stock_df is None or stock_df.empty:
                            continue
                        
                        # 为每个时间点创建记录
                        for time_idx in stock_df.index:
                            record = {
                                'time': time_idx,
                                'code': stock_code
                            }
                            
                            # 添加各个字段的数据
                            for field in fields:
                                if field == 'time':
                                    continue  # 已经处理
                                
                                if field in stock_df.columns:
                                    record[field] = stock_df.loc[time_idx, field]
                                else:
                                    record[field] = None
                            
                            result_list.append(record)
                    
                    if result_list:
                        # 创建最终DataFrame
                        final_df = pd.DataFrame(result_list)
                        
                        # 修复时间格式 - 基于调试结果的正确处理方式
                        try:
                            # 索引时间格式处理
                            if final_df['time'].dtype in ['int64', 'float64']:
                                # 检查是否是分钟数据格式 (YYYYMMDDHHMMSS)
                                sample_time = final_df['time'].iloc[0]
                                if sample_time > 20000000000000:  # 分钟数据格式
                                    # YYYYMMDDHHMMSS格式
                                    final_df['time'] = pd.to_datetime(final_df['time'].astype(str), format='%Y%m%d%H%M%S', errors='coerce')
                                else:
                                    # YYYYMMDD格式
                                    final_df['time'] = pd.to_datetime(final_df['time'].astype(str), format='%Y%m%d', errors='coerce')
                            elif final_df['time'].dtype == 'object':
                                # 如果是字符串格式，尝试直接转换
                                final_df['time'] = pd.to_datetime(final_df['time'], errors='coerce')
                            
                            # 如果转换失败，尝试其他格式
                            # 检查是否所有时间值都是NaT
                            notna_values = final_df['time'].notna()
                            notna_count = notna_values.sum()
                            if notna_count == 0:
                                print("警告: 时间格式转换失败")
                        except Exception as e:
                            print(f"时间格式处理警告: {e}")
                        
                        # 过滤掉无效数据
                        final_df = final_df.dropna(subset=['time'])
                        
                        if final_df.empty:
                            raise DataError("时间格式转换后数据为空")
                        
                        return final_df.sort_values(['code', 'time']).reset_index(drop=True)
                    else:
                        raise DataError("未能构建有效的数据结构")
            
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"第{attempt+1}次尝试失败: {str(e)}")
                    print("等待3秒后重试...")
                    time.sleep(3)
                else:
                    break
        
        # 所有重试都失败了
        if isinstance(last_error, (ConnectionError, DataError)):
            raise last_error
        ErrorHandler.log_error(f"获取价格数据失败: {str(last_error)}")
        raise DataError(f"获取价格数据失败: {str(last_error)}")

    # ==================== 订阅相关方法 ====================

    @ErrorHandler.handle_api_error
    def subscribe_quote(self,
                        codes: Union[str, List[str]],
                        period: str = 'tick',
                        callback: Optional[callable] = None) -> int:
        """
        订阅行情数据

        Args:
            codes: 股票代码
            period: 周期，'tick'分笔, '1m'1分钟, '5m'5分钟, '1d'日线等
            callback: 回调函数，接收推送数据

        Returns:
            int: 订阅号，成功返回>0，失败返回-1

        Raises:
            ConnectionError: 连接失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法订阅数据")

        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用connect()")

        codes = StockCodeUtils.normalize_codes(codes)
        if isinstance(codes, str):
            codes = [codes]

        # xtquant的subscribe_quote只支持单个股票订阅
        # 如果是多个股票，需要逐个订阅，返回第一个订阅号
        first_seq_id = -1
        for code in codes:
            try:
                seq_id = self.xt.subscribe_quote(code, period=period, callback=callback)
                if first_seq_id == -1 and seq_id > 0:
                    first_seq_id = seq_id
                print(f"  {code} 订阅成功，订阅号: {seq_id}")
            except Exception as e:
                print(f"  {code} 订阅失败: {e}")

        return first_seq_id

    @ErrorHandler.handle_api_error
    def subscribe_whole_quote(self,
                             codes: Union[str, List[str]],
                             callback: Optional[callable] = None) -> int:
        """
        订阅全推行情数据

        相比subscribe_quote，这个接口更适合订阅大量股票：
        - 可以一次订阅多个股票
        - 只支持tick周期
        - 返回数据格式为 {stock: data}

        Args:
            codes: 股票代码列表
            callback: 回调函数

        Returns:
            int: 订阅号，成功返回>0，失败返回-1

        Raises:
            ConnectionError: 连接失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法订阅数据")

        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用connect()")

        codes = StockCodeUtils.normalize_codes(codes)
        if isinstance(codes, str):
            codes = [codes]

        try:
            seq_id = self.xt.subscribe_whole_quote(code_list=codes, callback=callback)
            if seq_id > 0:
                print(f"  订阅成功，订阅号: {seq_id}")
            else:
                print(f"  订阅失败")
            return seq_id
        except Exception as e:
            ErrorHandler.log_error(f"订阅全推行情失败: {str(e)}")
            return -1

    @ErrorHandler.handle_api_error
    def unsubscribe_quote(self, seq_id: int) -> bool:
        """
        取消订阅

        Args:
            seq_id: 订阅号

        Returns:
            bool: 是否成功
        """
        if not self.xt:
            return False

        try:
            self.xt.unsubscribe_quote(seq_id)
            print(f"  订阅号 {seq_id} 已取消订阅")
            return True
        except Exception as e:
            ErrorHandler.log_error(f"取消订阅失败: {str(e)}")
            return False

    def run_forever(self, check_interval: float = 1.0):
        """
        阻塞当前线程，持续接收行情推送

        Args:
            check_interval: 检查连接状态的间隔时间（秒）
        """
        if not self.xt:
            print("❌ xtquant未正确导入")
            return

        if not self._connected:
            print("❌ 数据服务未连接")
            return

        print("✓ 开始接收行情推送，按 Ctrl+C 退出...")

        try:
            # 使用xtquant的run()方法来阻塞并处理回调
            # 这个方法会定期检查连接状态
            if hasattr(self.xt, 'run'):
                self.xt.run()
            else:
                # 如果没有run()方法，使用简单的sleep循环
                import time
                print(f"  使用兼容模式，检查间隔: {check_interval}秒")
                while True:
                    time.sleep(check_interval)
        except KeyboardInterrupt:
            print("\n\n✓ 已停止接收行情推送")
        except Exception as e:
            # 连接断开会抛出异常
            if '连接断开' in str(e) or 'is_connected' in str(e):
                print(f"\n❌ 行情服务连接断开")
            else:
                print(f"\n❌ 运行出错: {e}")
