"""
工具函数模块
"""
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Union, List, Optional, Any
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockCodeUtils:
    """股票代码处理工具"""
    
    @staticmethod
    def normalize_code(code: str) -> str:
        """
        标准化股票代码格式
        支持多种输入格式：000001、000001.SZ、SZ000001等
        """
        if not code:
            return ""
        
        code = code.upper().strip()
        
        # 如果已经是标准格式，直接返回
        if re.match(r'^\d{6}\.(SH|SZ)$', code):
            return code
        
        # 处理纯数字代码
        if re.match(r'^\d{6}$', code):
            # 根据代码判断市场
            if code.startswith(('60', '68', '11', '12', '13')):
                return f"{code}.SH"
            elif code.startswith(('00', '30', '12', '15', '16', '18')):
                return f"{code}.SZ"
            else:
                # 默认深圳
                return f"{code}.SZ"
        
        # 处理市场+代码格式
        if re.match(r'^(SH|SZ)\d{6}$', code):
            market = code[:2]
            stock_code = code[2:]
            return f"{stock_code}.{market}"
        
        # 其他格式尝试提取
        numbers = re.findall(r'\d{6}', code)
        if numbers:
            return StockCodeUtils.normalize_code(numbers[0])
        
        return code
    
    @staticmethod
    def normalize_codes(codes: Union[str, List[str]]) -> List[str]:
        """批量标准化股票代码

        Args:
            codes: 股票代码，支持以下格式：
                   - 单个字符串: "000001.SZ"
                   - 逗号分隔的字符串: "000001.SZ,000002.SZ"
                   - 列表: ["000001.SZ", "000002.SZ"]

        Returns:
            List[str]: 标准化后的股票代码列表
        """
        print(f"[DEBUG] normalize_codes 输入: type={type(codes)}, value={codes}")

        # 处理字符串输入
        if isinstance(codes, str):
            # 如果是逗号分隔的字符串，先拆分成列表
            codes = [c.strip() for c in codes.split(',') if c.strip()]
            print(f"[DEBUG] normalize_codes 字符串拆分后: {codes}")
        elif not isinstance(codes, list):
            # 其他类型（如None）转成列表
            codes = [codes] if codes is not None else []
            print(f"[DEBUG] normalize_codes 非字符串非列表转列表: {codes}")

        # 标准化每个代码
        result = [StockCodeUtils.normalize_code(code) for code in codes if code]
        print(f"[DEBUG] normalize_codes 输出: {result}")
        return result
    
    @staticmethod
    def get_market(code: str) -> str:
        """获取股票所属市场"""
        normalized = StockCodeUtils.normalize_code(code)
        if normalized.endswith('.SH'):
            return 'SH'
        elif normalized.endswith('.SZ'):
            return 'SZ'
        return ''

class TimeUtils:
    """时间处理工具"""
    
    @staticmethod
    def normalize_date(date_input: Union[str, datetime, int, None]) -> str:
        """
        标准化日期格式为YYYYMMDD
        支持多种输入格式
        """
        if date_input is None:
            return ''
        
        if isinstance(date_input, str):
            # 移除所有非数字字符
            date_str = re.sub(r'[^\d]', '', date_input)
            
            if len(date_str) == 8:
                return date_str
            elif len(date_str) == 6:
                # YYMMDD格式，假设20XX年
                return f"20{date_str}"
            elif len(date_str) == 4:
                # MMDD格式，使用当前年份
                current_year = datetime.now().year
                return f"{current_year}{date_str}"
            else:
                # 尝试解析其他格式
                try:
                    dt = pd.to_datetime(date_input)
                    return dt.strftime('%Y%m%d')
                except:
                    return ''
        
        elif isinstance(date_input, datetime):
            return date_input.strftime('%Y%m%d')
        
        elif isinstance(date_input, int):
            # 时间戳或YYYYMMDD格式
            if date_input > 99999999:  # 时间戳
                dt = datetime.fromtimestamp(date_input)
                return dt.strftime('%Y%m%d')
            else:  # YYYYMMDD格式
                return str(date_input)
        
        return ''
    
    @staticmethod
    def get_trading_days_range(start_date: str, end_date: str, days: int = None) -> tuple:
        """
        获取交易日期范围
        如果指定了days，则从end_date往前推days个交易日
        """
        if days:
            # 简单估算，实际应该查询交易日历
            end_dt = pd.to_datetime(end_date)
            start_dt = end_dt - timedelta(days=days * 1.5)  # 考虑周末和节假日
            start_date = start_dt.strftime('%Y%m%d')
        
        return TimeUtils.normalize_date(start_date), TimeUtils.normalize_date(end_date)

class DataUtils:
    """数据处理工具"""
    
    @staticmethod
    def safe_convert_numeric(value: Any, default: float = 0.0) -> float:
        """安全转换数值"""
        try:
            if pd.isna(value) or value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_dataframe(df: pd.DataFrame, index_name: str = None) -> pd.DataFrame:
        """格式化DataFrame"""
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 设置索引名称
        if index_name and df.index.name != index_name:
            df.index.name = index_name
        
        # 数值列转换
        numeric_columns = df.select_dtypes(include=['object']).columns
        for col in numeric_columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass
        
        return df
    
    @staticmethod
    def merge_market_data(data_dict: dict) -> pd.DataFrame:
        """合并多只股票的行情数据"""
        if not data_dict:
            return pd.DataFrame()
        
        # 如果只有一只股票，直接返回
        if len(data_dict) == 1:
            stock_code = list(data_dict.keys())[0]
            df = data_dict[stock_code].copy()
            df['code'] = stock_code
            return df
        
        # 多只股票合并
        result_list = []
        for stock_code, df in data_dict.items():
            if df is not None and not df.empty:
                df_copy = df.copy()
                df_copy['code'] = stock_code
                result_list.append(df_copy)
        
        if result_list:
            return pd.concat(result_list, ignore_index=True)
        else:
            return pd.DataFrame()

class ErrorHandler:
    """错误处理工具"""
    
    @staticmethod
    def handle_api_error(func):
        """API错误处理装饰器"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"API调用失败: {func.__name__}, 错误: {str(e)}")
                raise  # 重新抛出异常，而不是返回None
        return wrapper
    
    @staticmethod
    def log_warning(message: str):
        """记录警告信息"""
        logger.warning(message)
    
    @staticmethod
    def log_error(message: str):
        """记录错误信息"""
        logger.error(message)