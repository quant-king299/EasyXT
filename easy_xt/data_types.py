"""
EasyXT类型定义模块
定义所有API接口的类型注解和数据结构
"""
from typing import Union, List, Optional, Dict, Any, Literal, TypedDict, Protocol
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from datetime import datetime

# ==================== 基础类型定义 ====================

StockCode = str  # 股票代码类型
AccountId = str  # 账户ID类型
OrderId = int    # 委托ID类型
TradeId = int    # 成交ID类型

# 时间周期类型
PeriodType = Literal['1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M']

# 复权类型
AdjustType = Literal['front', 'back', 'none']

# 价格类型
PriceType = Literal['market', 'limit']

# 订单类型
OrderType = Literal['buy', 'sell']

# 订单状态
OrderStatus = Literal['pending', 'partial', 'filled', 'cancelled', 'rejected']

# 账户类型
AccountType = Literal['STOCK', 'CREDIT', 'OPTION']

# 市场类型
MarketType = Literal['SH', 'SZ', 'BJ']

# ==================== 数据结构定义 ====================

class PriceFields(TypedDict, total=False):
    """价格数据字段"""
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    turnover: float

class QuoteData(TypedDict):
    """实时行情数据"""
    code: StockCode
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    amount: float
    bid1: float
    ask1: float
    bid1_volume: int
    ask1_volume: int
    timestamp: datetime

class AccountAsset(TypedDict):
    """账户资产信息"""
    account_id: AccountId
    cash: float
    frozen_cash: float
    market_value: float
    total_asset: float
    available_cash: float
    profit_loss: float

class Position(TypedDict):
    """持仓信息"""
    code: StockCode
    name: str
    volume: int
    available_volume: int
    frozen_volume: int
    cost_price: float
    current_price: float
    market_value: float
    profit_loss: float
    profit_loss_pct: float

class OrderInfo(TypedDict):
    """委托信息"""
    order_id: OrderId
    account_id: AccountId
    code: StockCode
    name: str
    order_type: OrderType
    volume: int
    price: float
    traded_volume: int
    status: OrderStatus
    order_time: datetime
    remark: str

class TradeInfo(TypedDict):
    """成交信息"""
    trade_id: TradeId
    order_id: OrderId
    account_id: AccountId
    code: StockCode
    name: str
    order_type: OrderType
    volume: int
    price: float
    amount: float
    trade_time: datetime

# ==================== 枚举类定义 ====================

class Period(Enum):
    """时间周期枚举"""
    MIN1 = '1m'
    MIN5 = '5m'
    MIN15 = '15m'
    MIN30 = '30m'
    HOUR1 = '1h'
    DAY1 = '1d'
    WEEK1 = '1w'
    MONTH1 = '1M'

class AdjustMethod(Enum):
    """复权方式枚举"""
    FRONT = 'front'  # 前复权
    BACK = 'back'    # 后复权
    NONE = 'none'    # 不复权

class TradeDirection(Enum):
    """交易方向枚举"""
    BUY = 'buy'
    SELL = 'sell'

class PriceMode(Enum):
    """价格模式枚举"""
    MARKET = 'market'  # 市价
    LIMIT = 'limit'    # 限价

class OrderState(Enum):
    """订单状态枚举"""
    PENDING = 'pending'      # 待成交
    PARTIAL = 'partial'      # 部分成交
    FILLED = 'filled'        # 全部成交
    CANCELLED = 'cancelled'  # 已撤销
    REJECTED = 'rejected'    # 已拒绝

# ==================== 协议接口定义 ====================

class DataProvider(Protocol):
    """数据提供者协议"""
    
    def get_price_data(
        self, 
        codes: Union[StockCode, List[StockCode]], 
        period: PeriodType,
        start: Optional[str] = None,
        end: Optional[str] = None,
        count: Optional[int] = None
    ) -> pd.DataFrame:
        """获取价格数据"""
        ...
    
    def get_realtime_quote(
        self, 
        codes: Union[StockCode, List[StockCode]]
    ) -> List[QuoteData]:
        """获取实时行情"""
        ...

class TradeProvider(Protocol):
    """交易提供者协议"""
    
    def place_order(
        self,
        account_id: AccountId,
        code: StockCode,
        direction: OrderType,
        volume: int,
        price: float,
        price_type: PriceType
    ) -> Optional[OrderId]:
        """下单"""
        ...
    
    def cancel_order(
        self,
        account_id: AccountId,
        order_id: OrderId
    ) -> bool:
        """撤单"""
        ...

# ==================== 配置类定义 ====================

@dataclass
class ConnectionConfig:
    """连接配置"""
    host: str = 'localhost'
    port: int = 58610
    username: str = ''
    password: str = ''
    timeout: int = 30
    retry_count: int = 3
    retry_interval: float = 1.0

@dataclass
class TradeConfig:
    """交易配置"""
    userdata_path: str
    session_id: str = 'default'
    auto_retry: bool = True
    max_retry_count: int = 3
    order_timeout: int = 30

@dataclass
class DataConfig:
    """数据配置"""
    cache_enabled: bool = True
    cache_size: int = 1000
    auto_download: bool = False
    data_source: str = 'xtquant'

@dataclass
class RiskConfig:
    """风险控制配置"""
    max_position_ratio: float = 0.95  # 最大仓位比例
    max_single_stock_ratio: float = 0.20  # 单股最大仓位比例
    stop_loss_ratio: float = 0.10  # 止损比例
    take_profit_ratio: float = 0.20  # 止盈比例
    daily_loss_limit: float = 0.05  # 日亏损限制

# ==================== 响应类型定义 ====================

@dataclass
class ApiResponse:
    """API响应基类"""
    success: bool
    message: str
    data: Any = None
    error_code: Optional[str] = None

@dataclass
class OrderResponse(ApiResponse):
    """下单响应"""
    order_id: Optional[OrderId] = None

@dataclass
class QueryResponse(ApiResponse):
    """查询响应"""
    total_count: int = 0
    page_size: int = 100
    current_page: int = 1

# ==================== 异常类型定义 ====================

class EasyXTError(Exception):
    """EasyXT基础异常"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code

class ConnectionError(EasyXTError):
    """连接异常"""
    pass

class AuthenticationError(EasyXTError):
    """认证异常"""
    pass

class DataError(EasyXTError):
    """数据异常"""
    pass

class TradeError(EasyXTError):
    """交易异常"""
    pass

class ValidationError(EasyXTError):
    """验证异常"""
    pass

# ==================== 工具函数类型 ====================

def validate_stock_code(code: str) -> bool:
    """验证股票代码格式"""
    import re
    pattern = r'^[0-9]{6}\.(SH|SZ|BJ)$'
    return bool(re.match(pattern, code))

def normalize_period(period: Union[str, Period]) -> str:
    """标准化周期参数"""
    if isinstance(period, Period):
        return period.value
    return period

def format_price(price: float, precision: int = 2) -> str:
    """格式化价格显示"""
    return f"{price:.{precision}f}"

def calculate_change_pct(current: float, previous: float) -> float:
    """计算涨跌幅"""
    if previous == 0:
        return 0.0
    return (current - previous) / previous * 100

# ==================== 类型检查函数 ====================

def is_valid_account_id(account_id: str) -> bool:
    """检查账户ID是否有效"""
    return isinstance(account_id, str) and len(account_id) > 0

def is_valid_volume(volume: int) -> bool:
    """检查交易数量是否有效"""
    return isinstance(volume, int) and volume > 0 and volume % 100 == 0

def is_valid_price(price: float) -> bool:
    """检查价格是否有效"""
    return isinstance(price, (int, float)) and price >= 0

# ==================== 常量定义 ====================

class Constants:
    """常量定义"""
    
    # 最小交易单位
    MIN_TRADE_UNIT = 100
    
    # 价格精度
    PRICE_PRECISION = 2
    
    # 默认超时时间
    DEFAULT_TIMEOUT = 30
    
    # 最大重试次数
    MAX_RETRY_COUNT = 3
    
    # 支持的市场
    SUPPORTED_MARKETS = ['SH', 'SZ', 'BJ']
    
    # 支持的周期
    SUPPORTED_PERIODS = ['1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M']
    
    # 默认字段
    DEFAULT_PRICE_FIELDS = ['open', 'high', 'low', 'close', 'volume']