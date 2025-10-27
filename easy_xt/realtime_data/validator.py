"""
P1-010: 数据验证和清洗模块

实现数据质量检查和清洗，确保数据准确性。
支持股票行情数据、技术指标数据等多种数据类型的验证和清洗。
"""

import re
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别"""
    STRICT = "strict"      # 严格模式，任何异常都拒绝
    NORMAL = "normal"      # 正常模式，修复可修复的异常
    LOOSE = "loose"        # 宽松模式，尽可能保留数据


class DataType(Enum):
    """数据类型"""
    QUOTE = "quote"              # 行情数据
    KLINE = "kline"              # K线数据
    TICK = "tick"                # 逐笔数据
    ORDER_BOOK = "order_book"    # 订单簿数据
    INDICATOR = "indicator"      # 技术指标数据
    NEWS = "news"                # 新闻数据


@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    field: str
    rule_type: str  # range, regex, custom, required, type
    params: Dict[str, Any] = field(default_factory=dict)
    level: ValidationLevel = ValidationLevel.NORMAL
    enabled: bool = True
    description: str = ""


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cleaned_data: Optional[Dict[str, Any]] = None
    original_data: Optional[Dict[str, Any]] = None
    validation_time: datetime = field(default_factory=datetime.now)
    rules_applied: List[str] = field(default_factory=list)


class DataValidator:
    """数据验证器"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.NORMAL):
        """初始化数据验证器
        
        Args:
            validation_level: 验证级别
        """
        self.validation_level = validation_level
        self.rules: Dict[DataType, List[ValidationRule]] = {}
        self.statistics = {
            'total_validated': 0,
            'total_errors': 0,
            'total_warnings': 0,
            'total_cleaned': 0
        }
        
        # 初始化默认验证规则
        self._init_default_rules()
        
        logger.info(f"数据验证器初始化完成，验证级别: {validation_level.value}")
    
    def _init_default_rules(self):
        """初始化默认验证规则"""
        # 行情数据验证规则
        quote_rules = [
            ValidationRule(
                name="code_format",
                field="code",
                rule_type="regex",
                params={"pattern": r"^[0-9]{6}$"},
                description="股票代码格式验证"
            ),
            ValidationRule(
                name="price_range",
                field="price",
                rule_type="range",
                params={"min": 0.01, "max": 10000.0},
                description="价格范围验证"
            ),
            ValidationRule(
                name="volume_range",
                field="volume",
                rule_type="range",
                params={"min": 0, "max": 1e12},
                description="成交量范围验证"
            ),
            ValidationRule(
                name="timestamp_required",
                field="timestamp",
                rule_type="required",
                description="时间戳必填验证"
            ),
            ValidationRule(
                name="price_precision",
                field="price",
                rule_type="custom",
                params={"func": "validate_price_precision"},
                description="价格精度验证"
            )
        ]
        
        # K线数据验证规则
        kline_rules = [
            ValidationRule(
                name="ohlc_relationship",
                field="ohlc",
                rule_type="custom",
                params={"func": "validate_ohlc_relationship"},
                description="OHLC价格关系验证"
            ),
            ValidationRule(
                name="volume_positive",
                field="volume",
                rule_type="range",
                params={"min": 0},
                description="成交量非负验证"
            ),
            ValidationRule(
                name="time_sequence",
                field="timestamp",
                rule_type="custom",
                params={"func": "validate_time_sequence"},
                description="时间序列验证"
            )
        ]
        
        # 技术指标验证规则
        indicator_rules = [
            ValidationRule(
                name="value_finite",
                field="value",
                rule_type="custom",
                params={"func": "validate_finite_value"},
                description="数值有限性验证"
            ),
            ValidationRule(
                name="indicator_range",
                field="value",
                rule_type="custom",
                params={"func": "validate_indicator_range"},
                description="指标值范围验证"
            )
        ]
        
        self.rules[DataType.QUOTE] = quote_rules
        self.rules[DataType.KLINE] = kline_rules
        self.rules[DataType.INDICATOR] = indicator_rules
    
    def add_rule(self, data_type: DataType, rule: ValidationRule):
        """添加验证规则"""
        if data_type not in self.rules:
            self.rules[data_type] = []
        self.rules[data_type].append(rule)
        logger.info(f"添加验证规则: {rule.name} for {data_type.value}")
    
    def remove_rule(self, data_type: DataType, rule_name: str):
        """删除验证规则"""
        if data_type in self.rules:
            self.rules[data_type] = [r for r in self.rules[data_type] if r.name != rule_name]
            logger.info(f"删除验证规则: {rule_name} for {data_type.value}")
    
    def validate_quote_data(self, data: Dict[str, Any]) -> ValidationResult:
        """验证行情数据
        
        Args:
            data: 行情数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        return self._validate_data(data, DataType.QUOTE)
    
    def validate_kline_data(self, data: Dict[str, Any]) -> ValidationResult:
        """验证K线数据"""
        return self._validate_data(data, DataType.KLINE)
    
    def validate_indicator_data(self, data: Dict[str, Any]) -> ValidationResult:
        """验证技术指标数据"""
        return self._validate_data(data, DataType.INDICATOR)
    
    def validate_batch_data(self, data_list: List[Dict[str, Any]], 
                          data_type: DataType) -> List[ValidationResult]:
        """批量验证数据"""
        results = []
        for data in data_list:
            result = self._validate_data(data, data_type)
            results.append(result)
        return results
    
    def _validate_data(self, data: Dict[str, Any], data_type: DataType) -> ValidationResult:
        """验证数据的核心方法"""
        self.statistics['total_validated'] += 1
        
        result = ValidationResult(
            is_valid=True,
            original_data=data.copy(),
            cleaned_data=data.copy()
        )
        
        # 获取对应数据类型的验证规则
        rules = self.rules.get(data_type, [])
        
        for rule in rules:
            if not rule.enabled:
                continue
                
            try:
                rule_result = self._apply_rule(data, rule)
                result.rules_applied.append(rule.name)
                
                if not rule_result['valid']:
                    result.is_valid = False
                    if rule_result.get('error'):
                        result.errors.append(f"{rule.name}: {rule_result['error']}")
                        self.statistics['total_errors'] += 1
                    
                    if rule_result.get('warning'):
                        result.warnings.append(f"{rule.name}: {rule_result['warning']}")
                        self.statistics['total_warnings'] += 1
                
                # 应用数据清洗
                if rule_result.get('cleaned_value') is not None:
                    result.cleaned_data[rule.field] = rule_result['cleaned_value']
                    self.statistics['total_cleaned'] += 1
                    
            except Exception as e:
                logger.error(f"验证规则 {rule.name} 执行失败: {e}")
                result.errors.append(f"{rule.name}: 规则执行异常 - {str(e)}")
                result.is_valid = False
        
        return result
    
    def _apply_rule(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """应用单个验证规则"""
        field_value = data.get(rule.field)
        
        if rule.rule_type == "required":
            return self._validate_required(field_value, rule)
        elif rule.rule_type == "range":
            return self._validate_range(field_value, rule)
        elif rule.rule_type == "regex":
            return self._validate_regex(field_value, rule)
        elif rule.rule_type == "type":
            return self._validate_type(field_value, rule)
        elif rule.rule_type == "custom":
            return self._validate_custom(data, rule)
        else:
            return {"valid": True}
    
    def _validate_required(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """验证必填字段"""
        if value is None or value == "":
            return {
                "valid": False,
                "error": f"字段 {rule.field} 是必填的"
            }
        return {"valid": True}
    
    def _validate_range(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """验证数值范围"""
        if value is None:
            return {"valid": True}
        
        try:
            num_value = float(value)
            min_val = rule.params.get("min")
            max_val = rule.params.get("max")
            
            if min_val is not None and num_value < min_val:
                # 根据验证级别决定处理方式
                if self.validation_level == ValidationLevel.STRICT:
                    return {
                        "valid": False,
                        "error": f"值 {num_value} 小于最小值 {min_val}"
                    }
                else:
                    return {
                        "valid": True,
                        "warning": f"值 {num_value} 小于最小值 {min_val}，已修正",
                        "cleaned_value": min_val
                    }
            
            if max_val is not None and num_value > max_val:
                if self.validation_level == ValidationLevel.STRICT:
                    return {
                        "valid": False,
                        "error": f"值 {num_value} 大于最大值 {max_val}"
                    }
                else:
                    return {
                        "valid": True,
                        "warning": f"值 {num_value} 大于最大值 {max_val}，已修正",
                        "cleaned_value": max_val
                    }
            
            return {"valid": True}
            
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": f"无法将 {value} 转换为数值"
            }
    
    def _validate_regex(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """验证正则表达式"""
        if value is None:
            return {"valid": True}
        
        pattern = rule.params.get("pattern")
        if not pattern:
            return {"valid": True}
        
        if not re.match(pattern, str(value)):
            return {
                "valid": False,
                "error": f"值 {value} 不匹配模式 {pattern}"
            }
        
        return {"valid": True}
    
    def _validate_type(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """验证数据类型"""
        expected_type = rule.params.get("type")
        if not expected_type:
            return {"valid": True}
        
        if not isinstance(value, expected_type):
            return {
                "valid": False,
                "error": f"值 {value} 类型不正确，期望 {expected_type.__name__}"
            }
        
        return {"valid": True}
    
    def _validate_custom(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """验证自定义规则"""
        func_name = rule.params.get("func")
        if not func_name:
            return {"valid": True}
        
        # 调用自定义验证函数
        if hasattr(self, func_name):
            func = getattr(self, func_name)
            return func(data, rule)
        else:
            logger.warning(f"自定义验证函数 {func_name} 不存在")
            return {"valid": True}
    
    # 自定义验证函数
    def validate_price_precision(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """验证价格精度"""
        price = data.get(rule.field)
        if price is None:
            return {"valid": True}
        
        try:
            price_str = str(float(price))
            decimal_places = len(price_str.split('.')[-1]) if '.' in price_str else 0
            
            if decimal_places > 3:  # 最多3位小数
                rounded_price = round(float(price), 3)
                return {
                    "valid": True,
                    "warning": f"价格精度过高，已四舍五入到3位小数",
                    "cleaned_value": rounded_price
                }
            
            return {"valid": True}
            
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": f"价格值 {price} 无效"
            }
    
    def validate_ohlc_relationship(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """验证OHLC价格关系"""
        open_price = data.get('open')
        high_price = data.get('high')
        low_price = data.get('low')
        close_price = data.get('close')
        
        if None in [open_price, high_price, low_price, close_price]:
            return {"valid": True}  # 缺少数据时跳过验证
        
        try:
            o, h, l, c = float(open_price), float(high_price), float(low_price), float(close_price)
            
            # 检查高价是否为最高
            if h < max(o, l, c):
                return {
                    "valid": False,
                    "error": f"高价 {h} 不是OHLC中的最高值"
                }
            
            # 检查低价是否为最低
            if l > min(o, h, c):
                return {
                    "valid": False,
                    "error": f"低价 {l} 不是OHLC中的最低值"
                }
            
            return {"valid": True}
            
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": "OHLC价格数据类型错误"
            }
    
    def validate_time_sequence(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """验证时间序列"""
        timestamp = data.get(rule.field)
        if timestamp is None:
            return {"valid": True}
        
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                return {
                    "valid": False,
                    "error": f"时间戳格式不支持: {type(timestamp)}"
                }
            
            # 检查时间是否在合理范围内
            now = datetime.now()
            if dt > now + timedelta(hours=1):  # 不能超过当前时间1小时
                return {
                    "valid": False,
                    "error": f"时间戳 {dt} 超过当前时间过多"
                }
            
            if dt < datetime(2000, 1, 1):  # 不能早于2000年
                return {
                    "valid": False,
                    "error": f"时间戳 {dt} 过于久远"
                }
            
            return {"valid": True}
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"时间戳解析失败: {str(e)}"
            }
    
    def validate_finite_value(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """验证数值有限性"""
        value = data.get(rule.field)
        if value is None:
            return {"valid": True}
        
        try:
            num_value = float(value)
            if not np.isfinite(num_value):
                return {
                    "valid": False,
                    "error": f"数值 {value} 不是有限数"
                }
            return {"valid": True}
            
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": f"无法将 {value} 转换为数值"
            }
    
    def validate_indicator_range(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """验证技术指标范围"""
        value = data.get(rule.field)
        indicator_type = data.get('type', 'unknown')
        
        if value is None:
            return {"valid": True}
        
        try:
            num_value = float(value)
            
            # 根据指标类型设置合理范围
            if indicator_type.upper() == 'RSI':
                if not (0 <= num_value <= 100):
                    return {
                        "valid": False,
                        "error": f"RSI值 {num_value} 超出范围 [0, 100]"
                    }
            elif indicator_type.upper() in ['KDJ_K', 'KDJ_D', 'KDJ_J']:
                if not (-100 <= num_value <= 200):  # KDJ的J值可能超出0-100
                    return {
                        "valid": False,
                        "error": f"KDJ值 {num_value} 超出合理范围"
                    }
            
            return {"valid": True}
            
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": f"指标值 {value} 无效"
            }
    
    def clean_data(self, data: Dict[str, Any], data_type: DataType) -> Dict[str, Any]:
        """清洗数据
        
        Args:
            data: 原始数据
            data_type: 数据类型
            
        Returns:
            Dict: 清洗后的数据
        """
        validation_result = self._validate_data(data, data_type)
        
        if validation_result.cleaned_data:
            logger.info(f"数据清洗完成，修正了 {len(validation_result.warnings)} 个问题")
            return validation_result.cleaned_data
        else:
            return data
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        return {
            **self.statistics,
            'error_rate': self.statistics['total_errors'] / max(self.statistics['total_validated'], 1),
            'warning_rate': self.statistics['total_warnings'] / max(self.statistics['total_validated'], 1),
            'clean_rate': self.statistics['total_cleaned'] / max(self.statistics['total_validated'], 1)
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.statistics = {
            'total_validated': 0,
            'total_errors': 0,
            'total_warnings': 0,
            'total_cleaned': 0
        }
        logger.info("验证统计信息已重置")


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self):
        """初始化数据清洗器"""
        self.cleaning_strategies = {
            'remove_duplicates': self._remove_duplicates,
            'fill_missing_values': self._fill_missing_values,
            'smooth_outliers': self._smooth_outliers,
            'normalize_timestamps': self._normalize_timestamps,
            'fix_price_gaps': self._fix_price_gaps
        }
        
        logger.info("数据清洗器初始化完成")
    
    def clean_quote_series(self, data_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """清洗行情数据序列"""
        if not data_series:
            return data_series
        
        # 按时间排序
        sorted_data = sorted(data_series, key=lambda x: x.get('timestamp', 0))
        
        # 应用清洗策略
        cleaned_data = self._remove_duplicates(sorted_data)
        cleaned_data = self._fill_missing_values(cleaned_data)
        cleaned_data = self._smooth_outliers(cleaned_data)
        cleaned_data = self._normalize_timestamps(cleaned_data)
        cleaned_data = self._fix_price_gaps(cleaned_data)
        
        logger.info(f"清洗完成，原始数据: {len(data_series)}，清洗后: {len(cleaned_data)}")
        return cleaned_data
    
    def _remove_duplicates(self, data_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复数据"""
        seen = set()
        unique_data = []
        
        for item in data_series:
            # 使用代码和时间戳作为唯一标识
            key = (item.get('code'), item.get('timestamp'))
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        removed_count = len(data_series) - len(unique_data)
        if removed_count > 0:
            logger.info(f"去除重复数据 {removed_count} 条")
        
        return unique_data
    
    def _fill_missing_values(self, data_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """填充缺失值"""
        if len(data_series) < 2:
            return data_series
        
        filled_data = []
        for i, item in enumerate(data_series):
            filled_item = item.copy()
            
            # 填充价格字段的缺失值
            price_fields = ['price', 'open', 'high', 'low', 'close']
            for field in price_fields:
                if field in item and (item[field] is None or item[field] == 0):
                    # 使用前一个有效值填充
                    if i > 0 and field in data_series[i-1]:
                        filled_item[field] = data_series[i-1][field]
                        logger.debug(f"填充缺失值: {field} = {filled_item[field]}")
            
            filled_data.append(filled_item)
        
        return filled_data
    
    def _smooth_outliers(self, data_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """平滑异常值"""
        if len(data_series) < 5:
            return data_series
        
        smoothed_data = []
        price_field = 'price' if 'price' in data_series[0] else 'close'
        
        for i, item in enumerate(data_series):
            smoothed_item = item.copy()
            
            if price_field in item and item[price_field] is not None:
                current_price = float(item[price_field])
                
                # 计算周围价格的中位数
                start_idx = max(0, i - 2)
                end_idx = min(len(data_series), i + 3)
                nearby_prices = []
                
                for j in range(start_idx, end_idx):
                    if j != i and price_field in data_series[j] and data_series[j][price_field] is not None:
                        nearby_prices.append(float(data_series[j][price_field]))
                
                if nearby_prices:
                    median_price = np.median(nearby_prices)
                    
                    # 如果当前价格偏离中位数超过20%，则认为是异常值
                    if abs(current_price - median_price) / median_price > 0.2:
                        smoothed_item[price_field] = median_price
                        logger.debug(f"平滑异常值: {current_price} -> {median_price}")
            
            smoothed_data.append(smoothed_item)
        
        return smoothed_data
    
    def _normalize_timestamps(self, data_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标准化时间戳"""
        normalized_data = []
        
        for item in data_series:
            normalized_item = item.copy()
            
            if 'timestamp' in item:
                timestamp = item['timestamp']
                
                # 统一转换为datetime对象
                if isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        normalized_item['timestamp'] = dt.timestamp()
                    except:
                        logger.warning(f"无法解析时间戳: {timestamp}")
                elif isinstance(timestamp, datetime):
                    normalized_item['timestamp'] = timestamp.timestamp()
                # 如果已经是数字时间戳，保持不变
            
            normalized_data.append(normalized_item)
        
        return normalized_data
    
    def _fix_price_gaps(self, data_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """修复价格跳空"""
        if len(data_series) < 2:
            return data_series
        
        fixed_data = []
        price_field = 'price' if 'price' in data_series[0] else 'close'
        
        for i, item in enumerate(data_series):
            fixed_item = item.copy()
            
            if i > 0 and price_field in item and price_field in data_series[i-1]:
                current_price = item[price_field]
                prev_price = data_series[i-1][price_field]
                
                if current_price is not None and prev_price is not None:
                    current_price = float(current_price)
                    prev_price = float(prev_price)
                    
                    # 如果价格跳空超过10%，可能是数据错误
                    price_change = abs(current_price - prev_price) / prev_price
                    if price_change > 0.1:
                        # 使用线性插值修复
                        fixed_price = (current_price + prev_price) / 2
                        fixed_item[price_field] = fixed_price
                        logger.debug(f"修复价格跳空: {current_price} -> {fixed_price}")
            
            fixed_data.append(fixed_item)
        
        return fixed_data