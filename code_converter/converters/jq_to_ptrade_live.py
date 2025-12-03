"""
聚宽到Ptrade代码转换器 - 实盘版本
用于Ptrade实盘交易环境，充分利用实时数据API
"""
import re
from typing import Dict, List

class JQToPtradeLiveConverter:
    """实盘版本转换器 - 针对Ptrade实盘环境优化"""
    
    def __init__(self):
        # API映射规则（聚宽 → Ptrade）
        self.api_mapping = {
            # 数据API
            'get_current_data': 'get_snapshot',
            'get_all_securities': 'get_Ashares',
            'get_security_info': 'get_stock_info',
            'attribute_history': 'get_history',
            'get_bars': 'get_history',
        }
        
        # 保留的实盘API（不删除）
        self.keep_live_apis = {
            'get_snapshot',
            'get_real_time_data',
            'set_option',
            'set_commission',
            'set_slippage',
            'set_price_limit',
        }
        
        # 特殊处理函数
        self.special_handlers = {
            'filter_paused_stock': self._optimize_filter_paused_stock_live,
            'filter_st_stock': self._optimize_filter_st_stock_live,
            'filter_limit_stock': self._optimize_filter_limit_stock_live,
            'check_limit_up': self._optimize_check_limit_up_live,
        }
    
    def convert(self, jq_code: str) -> str:
        """
        转换聚宽代码为Ptrade实盘版本
        
        Args:
            jq_code: 聚宽策略代码
            
        Returns:
            str: 转换后的Ptrade实盘版本代码
        """
        code = jq_code
        
        # 1. 替换API映射
        code = self._replace_apis(code)
        
        # 2. 添加实盘配置
        code = self._add_live_configs(code)
        
        # 3. 优化实时数据使用
        code = self._optimize_for_live_data(code)
        
        # 4. 整理代码格式
        code = self._cleanup_code(code)
        
        return code
    
    def _replace_apis(self, code: str) -> str:
        """替换API映射"""
        for jq_api, ptrade_api in self.api_mapping.items():
            code = re.sub(rf'\b{jq_api}\b', ptrade_api, code)
        
        return code
    
    def _add_live_configs(self, code: str) -> str:
        """添加实盘配置"""
        # 检查initialize函数
        if 'def initialize(context):' in code:
            # 提供配置示例（注释形式）
            config_hint = '''    # ========== Ptrade实盘配置 ==========
    # 设置手续费（可选）
    # set_commission(CommissionSpec(...))
    
    # 设置滑点（可选）
    # set_slippage(SlippageSpec(...))
    
    # 设置价格限制（可选）
    # set_price_limit(limit_value)
    
    # 使用实时价格（推荐）
    # set_option('use_real_price', True)
    # =======================================
'''
            
            # 在initialize函数的最后一行插入配置提示
            lines = code.split('\n')
            result = []
            in_init = False
            init_end_index = -1
            
            for i, line in enumerate(lines):
                result.append(line)
                if 'def initialize(context):' in line:
                    in_init = True
                elif in_init and line.strip() and not line.startswith(' ' * 4):
                    # 找到initialize函数的结束
                    init_end_index = i - 1
                    in_init = False
            
            if init_end_index > 0:
                result.insert(init_end_index + 1, config_hint)
        
            code = '\n'.join(result)
        
        return code
    
    def _optimize_for_live_data(self, code: str) -> str:
        """优化实时数据使用"""
        # 替换函数实现为实盘优化版本
        
        # filter_paused_stock
        if 'def filter_paused_stock(stock_list):' in code:
            old_pattern = r'def filter_paused_stock\(stock_list\):.*?(?=\ndef|\Z)'
            replacement = '''def filter_paused_stock(stock_list):
    # 实盘版本：使用实时行情检查停牌
    current_data = get_snapshot(stock_list)
    if current_data is None:
        return stock_list
    return [stock for stock in stock_list if not current_data[stock].paused]'''
            code = re.sub(old_pattern, replacement, code, flags=re.DOTALL)
        
        # filter_st_stock
        if 'def filter_st_stock(stock_list):' in code:
            old_pattern = r'def filter_st_stock\(stock_list\):.*?(?=\ndef|\Z)'
            replacement = '''def filter_st_stock(stock_list):
    # 实盘版本：使用实时行情检查ST状态
    current_data = get_snapshot(stock_list)
    if current_data is None:
        return stock_list
    return [stock for stock in stock_list if not (
        current_data[stock].is_st or 
        'ST' in current_data[stock].name or
        '*' in current_data[stock].name
    )]'''
            code = re.sub(old_pattern, replacement, code, flags=re.DOTALL)
        
        # filter_limit_stock
        if 'def filter_limit_stock(context, stock_list):' in code:
            old_pattern = r'def filter_limit_stock\(context, stock_list\):.*?(?=\ndef|\Z)'
            replacement = '''def filter_limit_stock(context, stock_list):
    # 实盘版本：使用实时行情检查涨跌停
    current_data = get_snapshot(stock_list)
    if current_data is None:
        return stock_list
    holdings = list(context.portfolio.positions)
    return [stock for stock in stock_list if stock in holdings or (
        current_data[stock].low_limit < current_data[stock].last_price < current_data[stock].high_limit
    )]'''
            code = re.sub(old_pattern, replacement, code, flags=re.DOTALL)
        
        # check_limit_up
        if 'def check_limit_up(context):' in code:
            old_pattern = r'def check_limit_up\(context\):.*?(?=\ndef|\Z)'
            replacement = '''def check_limit_up(context):
    # 实盘版本：实时检查涨停状态
    current_data = get_snapshot()
    if current_data is None:
        return
    
    if context.high_limit_list:
        for stock in context.high_limit_list:
            snapshot = current_data[stock]
            
            # 检查涨停是否打开
            if snapshot.last_price < snapshot.high_limit:
                log.info('[%s]涨停打开，卖出' % stock)
                position = context.portfolio.positions[stock]
                close_position(position)
            else:
                log.info('[%s]仍在涨停' % stock)'''
            code = re.sub(old_pattern, replacement, code, flags=re.DOTALL)
        
        return code
    
    def _optimize_filter_paused_stock_live(self, code: str) -> str:
        """优化filter_paused_stock函数"""
        return '''def filter_paused_stock(stock_list):
    # 实盘：直接使用实时行情
    current_data = get_snapshot(stock_list)
    return [s for s in stock_list if not current_data[s].paused]'''
    
    def _optimize_filter_st_stock_live(self, code: str) -> str:
        """优化filter_st_stock函数"""
        return '''def filter_st_stock(stock_list):
    # 实盘：直接使用实时行情
    current_data = get_snapshot(stock_list)
    return [s for s in stock_list if not current_data[s].is_st]'''
    
    def _optimize_filter_limit_stock_live(self, code: str) -> str:
        """优化filter_limit_stock函数"""
        return '''def filter_limit_stock(context, stock_list):
    # 实盘：直接使用实时行情检查涨跌停
    current_data = get_snapshot(stock_list)
    holdings = list(context.portfolio.positions)
    return [s for s in stock_list if s in holdings or (
        current_data[s].low_limit < current_data[s].last_price < current_data[s].high_limit
    )]'''
    
    def _optimize_check_limit_up_live(self, code: str) -> str:
        """优化check_limit_up函数"""
        return '''def check_limit_up(context):
    # 实盘：实时检查涨停
    current_data = get_snapshot()
    if not current_data:
        return
    
    for stock in context.high_limit_list:
        if current_data[stock].last_price < current_data[stock].high_limit:
            position = context.portfolio.positions.get(stock)
            if position:
                close_position(position)'''
    
    def _cleanup_code(self, code: str) -> str:
        """整理代码格式"""
        # 移除过度空行
        lines = code.split('\n')
        result = []
        consecutive_blank = 0
        
        for line in lines:
            if line.strip() == '':
                consecutive_blank += 1
                if consecutive_blank <= 2:
                    result.append(line)
            else:
                consecutive_blank = 0
                result.append(line)
        
        return '\n'.join(result)


# 使用示例
if __name__ == "__main__":
    converter = JQToPtradeLiveConverter()
    
    # 测试转换
    jq_code = '''
def initialize(context):
    run_daily(check_limit_up, time='14:00')

def filter_paused_stock(stock_list):
    current_data = get_snapshot()
    return [s for s in stock_list if not current_data[s].paused]

def check_limit_up(context):
    current_data = get_snapshot()
    pass
'''
    
    ptrade_code = converter.convert(jq_code)
    print(ptrade_code)
