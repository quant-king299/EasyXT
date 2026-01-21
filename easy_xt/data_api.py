"""
数据API封装模块
简化xtquant数据接口的调用
"""
import pandas as pd
from typing import Union, List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os

# 添加xtquant路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
xtquant_path = os.path.join(project_root, 'xtquant')

if xtquant_path not in sys.path:
    sys.path.insert(0, xtquant_path)

try:
    import xtquant.xtdata as xt
    print("[OK] xtquant.xtdata imported successfully")
except ImportError as e:
    print(f"[ERROR] xtquant.xtdata import failed: {e}")
    xt = None

from .utils import StockCodeUtils, TimeUtils, DataUtils, ErrorHandler
from .config import config
from .data_types import ConnectionError, DataError
from typing import Dict
from datetime import datetime, timedelta
import time

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
    """数据API封装类"""
    
    def __init__(self):
        self.xt = xt
        self._connected = False
    
    def connect(self) -> bool:
        """连接数据服务"""
        if not self.xt:
            ErrorHandler.log_error("xtquant未正确导入")
            return False
        
        try:
            # 尝试获取客户端连接
            client = self.xt.get_client()
            self._connected = client.is_connected() if client else False
            
            if self._connected:
                print("[OK] Data service connected successfully")
            else:
                print("[ERROR] Cannot connect to Xt client")
                print("[TIPS] Please ensure Xt client is running and logged in")
            
            return self._connected
        except Exception as e:
            ErrorHandler.log_error(f"连接数据服务失败: {str(e)}")
            return False
    
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
        获取股票价格数据
        
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
            ConnectionError: 连接失败
            DataError: 数据获取失败
            ValueError: 不支持的周期类型或股票代码无效
        """
        # 验证周期类型
        if not validate_period(period):
            supported_list = ', '.join(SUPPORTED_PERIODS.keys())
            raise ValueError(f"不支持的数据周期 '{period}'。支持的周期: {supported_list}")
        # 如果xtquant不可用，直接报错
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        # 标准化股票代码
        # normalize_codes 已经能够正确处理字符串（包括逗号分隔的字符串）和列表
        codes = StockCodeUtils.normalize_codes(codes)
        print(f"[DEBUG] data_api.py get_price: codes类型={type(codes)}, 值={codes}")

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
                raise DataError(f"无法获取股票 {codes} 的数据。可能的原因：\n1. 需要先在迅投客户端中下载历史数据\n2. 股票代码错误\n3. 网络连接问题\n4. 迅投服务未正常运行\n\n建议：请在迅投客户端中手动下载相关股票的历史数据后重试")
            
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
                    raise DataError(f"无法获取股票 {codes} 的数据。可能的原因：\n1. 需要先在迅投客户端中下载历史数据\n2. 股票代码错误\n3. 网络连接问题\n4. 迅投服务未正常运行\n\n建议：请在迅投客户端中手动下载相关股票的历史数据后重试")
                
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
            sector: 板块名称，如'沪深300', 'A股'等
            
        Returns:
            List[str]: 股票代码列表
            
        Raises:
            ConnectionError: 连接失败
            DataError: 数据获取失败
        """
        if not self.xt:
            raise ConnectionError("xtquant未正确导入，无法获取数据")
        
        if not self._connected:
            raise ConnectionError("数据服务未连接，请先调用init_data()并确保迅投客户端已启动")
        
        try:
            if sector:
                stock_list = self.xt.get_stock_list_in_sector(sector)
            else:
                # 获取所有A股
                sh_stocks = self.xt.get_stock_list_in_sector('沪A')
                sz_stocks = self.xt.get_stock_list_in_sector('深A')
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
        
        # 批量下载数据
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
                except Exception as stock_error:
                    results[stock] = False
                    print(f"{stock} 历史数据下载失败: {stock_error}")
        
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
