"""
EasyXT数据验证模块
提供参数验证和数据校验功能
"""
import re
from typing import Union, List, Optional, Any, Dict
from datetime import datetime, date
from .types import (
    StockCode, AccountId, PeriodType, AdjustType, PriceType, 
    OrderType, ValidationError, Constants
)

class StockCodeValidator:
    """股票代码验证器"""
    
    # 股票代码正则表达式
    STOCK_CODE_PATTERN = re.compile(r'^[0-9]{6}\.(SH|SZ|BJ)$')
    
    @classmethod
    def validate(cls, code: str) -> str:
        """
        验证并标准化股票代码
        
        Args:
            code: 股票代码
            
        Returns:
            str: 标准化后的股票代码
            
        Raises:
            ValidationError: 代码格式错误
        """
        if not isinstance(code, str):
            raise ValidationError(f"股票代码必须是字符串类型，当前类型: {type(code)}")
        
        code = code.strip().upper()
        
        # 自动补全后缀
        if len(code) == 6 and code.isdigit():
            if code.startswith(('60', '68', '11', '12', '13')):
                code += '.SH'
            elif code.startswith(('00', '30', '12', '13')):
                code += '.SZ'
            elif code.startswith(('43', '83', '87', '88')):
                code += '.BJ'
            else:
                raise ValidationError(f"无法识别股票代码所属市场: {code}")
        
        if not cls.STOCK_CODE_PATTERN.match(code):
            raise ValidationError(f"股票代码格式错误: {code}，正确格式如: 000001.SZ")
        
        return code
    
    @classmethod
    def validate_list(cls, codes: Union[str, List[str]]) -> List[str]:
        """
        验证股票代码列表
        
        Args:
            codes: 股票代码或代码列表
            
        Returns:
            List[str]: 验证后的代码列表
        """
        if isinstance(codes, str):
            return [cls.validate(codes)]
        
        if not isinstance(codes, list):
            raise ValidationError("股票代码必须是字符串或字符串列表")
        
        if not codes:
            raise ValidationError("股票代码列表不能为空")
        
        return [cls.validate(code) for code in codes]

class DateValidator:
    """日期验证器"""
    
    # 支持的日期格式
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%Y%m%d',
        '%Y/%m/%d',
        '%Y.%m.%d'
    ]
    
    @classmethod
    def validate(cls, date_str: Optional[str]) -> Optional[str]:
        """
        验证并标准化日期字符串
        
        Args:
            date_str: 日期字符串
            
        Returns:
            Optional[str]: 标准化后的日期字符串 (YYYY-MM-DD)
        """
        if date_str is None:
            return None
        
        if isinstance(date_str, (datetime, date)):
            return date_str.strftime('%Y-%m-%d')
        
        if not isinstance(date_str, str):
            raise ValidationError(f"日期必须是字符串类型，当前类型: {type(date_str)}")
        
        date_str = date_str.strip()
        
        for fmt in cls.DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        raise ValidationError(f"日期格式错误: {date_str}，支持格式: {cls.DATE_FORMATS}")
    
    @classmethod
    def validate_range(cls, start: Optional[str], end: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """
        验证日期范围
        
        Args:
            start: 开始日期
            end: 结束日期
            
        Returns:
            tuple: (标准化开始日期, 标准化结束日期)
        """
        start_date = cls.validate(start) if start else None
        end_date = cls.validate(end) if end else None
        
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError(f"开始日期不能晚于结束日期: {start_date} > {end_date}")
        
        return start_date, end_date

class PeriodValidator:
    """周期验证器"""
    
    @classmethod
    def validate(cls, period: str) -> str:
        """
        验证时间周期
        
        Args:
            period: 时间周期
            
        Returns:
            str: 验证后的周期
        """
        if not isinstance(period, str):
            raise ValidationError(f"时间周期必须是字符串类型，当前类型: {type(period)}")
        
        period = period.lower().strip()
        
        # 周期映射
        period_map = {
            '1min': '1m', '1分钟': '1m',
            '5min': '5m', '5分钟': '5m',
            '15min': '15m', '15分钟': '15m',
            '30min': '30m', '30分钟': '30m',
            '1hour': '1h', '1小时': '1h',
            '1day': '1d', '1日': '1d', '日线': '1d',
            '1week': '1w', '1周': '1w', '周线': '1w',
            '1month': '1M', '1月': '1M', '月线': '1M'
        }
        
        period = period_map.get(period, period)
        
        if period not in Constants.SUPPORTED_PERIODS:
            raise ValidationError(f"不支持的时间周期: {period}，支持的周期: {Constants.SUPPORTED_PERIODS}")
        
        return period

class TradeValidator:
    """交易参数验证器"""
    
    @classmethod
    def validate_account_id(cls, account_id: str) -> str:
        """验证账户ID"""
        if not isinstance(account_id, str):
            raise ValidationError(f"账户ID必须是字符串类型，当前类型: {type(account_id)}")
        
        account_id = account_id.strip()
        if not account_id:
            raise ValidationError("账户ID不能为空")
        
        return account_id
    
    @classmethod
    def validate_volume(cls, volume: int) -> int:
        """验证交易数量"""
        if not isinstance(volume, int):
            raise ValidationError(f"交易数量必须是整数类型，当前类型: {type(volume)}")
        
        if volume <= 0:
            raise ValidationError(f"交易数量必须大于0，当前值: {volume}")
        
        if volume % Constants.MIN_TRADE_UNIT != 0:
            raise ValidationError(f"交易数量必须是{Constants.MIN_TRADE_UNIT}的整数倍，当前值: {volume}")
        
        return volume
    
    @classmethod
    def validate_price(cls, price: float, allow_zero: bool = True) -> float:
        """验证价格"""
        if not isinstance(price, (int, float)):
            raise ValidationError(f"价格必须是数字类型，当前类型: {type(price)}")
        
        if price < 0:
            raise ValidationError(f"价格不能为负数，当前值: {price}")
        
        if not allow_zero and price == 0:
            raise ValidationError("价格不能为0")
        
        return float(price)
    
    @classmethod
    def validate_price_type(cls, price_type: str) -> str:
        """验证价格类型"""
        if not isinstance(price_type, str):
            raise ValidationError(f"价格类型必须是字符串，当前类型: {type(price_type)}")
        
        price_type = price_type.lower().strip()
        
        # 价格类型映射
        type_map = {
            'market': 'market',
            'limit': 'limit',
            '市价': 'market',
            '限价': 'limit',
            '市价单': 'market',
            '限价单': 'limit'
        }
        
        price_type = type_map.get(price_type, price_type)
        
        if price_type not in ['market', 'limit']:
            raise ValidationError(f"不支持的价格类型: {price_type}，支持: market, limit")
        
        return price_type
    
    @classmethod
    def validate_order_type(cls, order_type: str) -> str:
        """验证订单类型"""
        if not isinstance(order_type, str):
            raise ValidationError(f"订单类型必须是字符串，当前类型: {type(order_type)}")
        
        order_type = order_type.lower().strip()
        
        # 订单类型映射
        type_map = {
            'buy': 'buy',
            'sell': 'sell',
            '买入': 'buy',
            '卖出': 'sell',
            '买': 'buy',
            '卖': 'sell'
        }
        
        order_type = type_map.get(order_type, order_type)
        
        if order_type not in ['buy', 'sell']:
            raise ValidationError(f"不支持的订单类型: {order_type}，支持: buy, sell")
        
        return order_type

class DataValidator:
    """数据验证器"""
    
    @classmethod
    def validate_count(cls, count: Optional[int]) -> Optional[int]:
        """验证数据条数"""
        if count is None:
            return None
        
        if not isinstance(count, int):
            raise ValidationError(f"数据条数必须是整数类型，当前类型: {type(count)}")
        
        if count <= 0:
            raise ValidationError(f"数据条数必须大于0，当前值: {count}")
        
        if count > 10000:
            raise ValidationError(f"数据条数不能超过10000，当前值: {count}")
        
        return count
    
    @classmethod
    def validate_fields(cls, fields: Optional[List[str]]) -> Optional[List[str]]:
        """验证字段列表"""
        if fields is None:
            return None
        
        if not isinstance(fields, list):
            raise ValidationError(f"字段列表必须是列表类型，当前类型: {type(fields)}")
        
        if not fields:
            raise ValidationError("字段列表不能为空")
        
        valid_fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover']
        invalid_fields = [f for f in fields if f not in valid_fields]
        
        if invalid_fields:
            raise ValidationError(f"无效的字段: {invalid_fields}，有效字段: {valid_fields}")
        
        return fields
    
    @classmethod
    def validate_adjust_type(cls, adjust: str) -> str:
        """验证复权类型"""
        if not isinstance(adjust, str):
            raise ValidationError(f"复权类型必须是字符串，当前类型: {type(adjust)}")
        
        adjust = adjust.lower().strip()
        
        # 复权类型映射
        adjust_map = {
            'front': 'front',
            'back': 'back',
            'none': 'none',
            '前复权': 'front',
            '后复权': 'back',
            '不复权': 'none',
            'qfq': 'front',
            'hfq': 'back'
        }
        
        adjust = adjust_map.get(adjust, adjust)
        
        if adjust not in ['front', 'back', 'none']:
            raise ValidationError(f"不支持的复权类型: {adjust}，支持: front, back, none")
        
        return adjust

# ==================== 综合验证函数 ====================

def validate_trade_params(
    account_id: str,
    code: str,
    volume: int,
    price: float = 0,
    price_type: str = 'market',
    order_type: str = 'buy'
) -> Dict[str, Any]:
    """
    验证交易参数
    
    Returns:
        Dict[str, Any]: 验证后的参数
    """
    return {
        'account_id': TradeValidator.validate_account_id(account_id),
        'code': StockCodeValidator.validate(code),
        'volume': TradeValidator.validate_volume(volume),
        'price': TradeValidator.validate_price(price, allow_zero=(price_type == 'market')),
        'price_type': TradeValidator.validate_price_type(price_type),
        'order_type': TradeValidator.validate_order_type(order_type)
    }

def validate_query_params(
    codes: Union[str, List[str]],
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: str = '1d',
    count: Optional[int] = None,
    fields: Optional[List[str]] = None,
    adjust: str = 'front'
) -> Dict[str, Any]:
    """
    验证查询参数
    
    Returns:
        Dict[str, Any]: 验证后的参数
    """
    validated_codes = StockCodeValidator.validate_list(codes)
    start_date, end_date = DateValidator.validate_range(start, end)
    
    return {
        'codes': validated_codes,
        'start': start_date,
        'end': end_date,
        'period': PeriodValidator.validate(period),
        'count': DataValidator.validate_count(count),
        'fields': DataValidator.validate_fields(fields),
        'adjust': DataValidator.validate_adjust_type(adjust)
    }