"""
聚宽到Ptrade实时数据转换器
处理get_current_data()转换为自定义实现
"""
import re
from typing import Dict, List

class JQToPtradeCurrentDataConverter:
    """处理实时数据转换的转换器"""
    
    def __init__(self):
        pass
    
    def convert(self, jq_code: str) -> str:
        """
        转换聚宽代码为Ptrade回测版代码，特别处理实时数据获取
        
        Args:
            jq_code: 聚宽策略代码
            
        Returns:
            str: 转换后的Ptrade回测版代码
        """
        # 使用模板方法进行转换
        template = self._get_template()
        
        # 提取关键函数和逻辑
        functions = self._extract_functions(jq_code)
        
        # 将提取的函数合并到模板中
        result = self._merge_functions_to_template(template, functions)
        
        # 替换全局变量引用
        result = result.replace('g.', 'context.')
        
        # 修复log替换错误
        result = result.replace('locontext.', 'log.')
        
        # 标准化证券代码后缀
        result = self._standardize_security_code(result)
        
        # 处理API转换
        result = self._convert_apis(result)
        
        return result
    
    def _get_template(self) -> str:
        """获取Ptrade回测模板"""
        return '''# 自动生成的Ptrade策略代码 - 回测版本
# 原始代码来自聚宽策略
# 注意：本版本为回测环境优化，去除了所有实时数据API

import datetime
import pandas as pd
import numpy as np
import statsmodels.api as sm

def initialize(context):
    # [回测版本提示] log.set_level不被支持
    # 使用log时直接调用 log.info(), log.debug(), log.warning() 等方法
    # [回测版本提示] set_option等配置函数不被支持，已在转换时移除
    context.stock_num = 10
    context.limit_days = 20
    context.hold_list = []
    context.history_hold_list = []
    context.not_buy_again_list = []
    context.high_limit_list = []
    run_daily(context, prepare_stock_list, time='9:05')
    run_daily(context, daily_check, time='9:30')  # 原run_daily已适配

def before_trading_start(context, data):
    # 盘前处理
    pass

def get_last_trading_day_data(context, security_list):
    """
    获取上一交易日的数据
    替代聚宽的get_current_data()函数
    """
    result = {}
    
    # 1. 获取当前日期的上一交易日
    # 格式化日期为API可用格式
    last_trading_day = context.previous_date
    last_trading_day_str = last_trading_day.strftime('%Y-%m-%d')
    
    # 2. 调用get_price获取上一交易日的行情数据
    # 注意: get_price按日期查询时，start_date和end_date需一致(单交易日)，且返回数据不包含当天(需用end_date=上一交易日)
    try:
        price_data = get_price(
            security_list, 
            start_date=last_trading_day_str, 
            end_date=last_trading_day_str, 
            fields=['open', 'close', 'high', 'low'],  # 目标字段
            is_dict=False  # 非dict格式，便于DataFrame处理
        )
        
        # 3. 按要求格式整理数据
        # 遍历目标股票
        for stock in security_list:
            # 筛选当前股票的数据(Python3.11多股票返回格式:行索引为时间，列索引为code+字段)
            stock_data = price_data[price_data['code'] == stock]
            if not stock_data.empty:
                # 保留原始精度，API返回为float类型
                open_price = stock_data['open'].iloc[0]
                close_price = stock_data['close'].iloc[0]
                high_price = stock_data['high'].iloc[0]
                low_price = stock_data['low'].iloc[0]
                # 存入结果字典
                result[stock] = {
                    'open': open_price,
                    'close': close_price,
                    'high': high_price,
                    'low': low_price
                }
    except Exception as e:
        log.warning(f"获取上一交易日数据失败: {str(e)}")
        # 返回空结果
        for stock in security_list:
            result[stock] = {
                'open': 0,
                'close': 0,
                'high': 0,
                'low': 0
            }
    
    return result

def get_current_data(context, security_list=None):
    """
    获取当前数据 - 回测版本
    替代聚宽的get_current_data()函数
    在回测环境中，当前数据即为上一交易日的数据
    """
    if security_list is None:
        # 如果没有指定股票列表，使用持仓股票
        security_list = list(context.portfolio.positions.keys())
    
    if not security_list:
        return {}
    
    # 调用获取上一交易日数据的函数
    return get_last_trading_day_data(context, security_list)

def prepare_stock_list(context):
    """准备股票池"""
    try:
        context.hold_list = list(context.portfolio.positions)
        context.history_hold_list.append(context.hold_list)
        if len(context.history_hold_list) >= context.limit_days:
            context.history_hold_list = context.history_hold_list[-context.limit_days:]
        
        temp_set = set()
        for hold_list in context.history_hold_list:
            temp_set = temp_set.union(set(hold_list))
        context.not_buy_again_list = list(temp_set)
        
        context.high_limit_list = []
        if context.hold_list:
            try:
                df = get_price(context.hold_list, end_date=context.previous_date, fields=['close', 'high_limit', 'paused'], count=1)
                context.high_limit_list = df.query('close==high_limit and paused==0')['code'].tolist()
            except:
                context.high_limit_list = []
    except Exception as e:
        log.error(f"[prepare_stock_list] 异常: {str(e)}")

def daily_check(context):
    """每日检查函数"""
    # 获取当前数据示例
    current_data = get_current_data(context)
    
    for stock, data in current_data.items():
        open_price = data['open']
        close_price = data['close']
        high_price = data['high']
        low_price = data['low']
        
        log.info(f'{stock}: 开盘价={open_price}, 收盘价={close_price}, 最高价={high_price}, 最低价={low_price}')

def handle_data(context, data):
    # 盘中处理
    pass

def after_trading_end(context, data):
    # 收盘后处理
    pass
'''
    
    def _extract_functions(self, jq_code: str) -> Dict[str, str]:
        """从聚宽代码中提取函数"""
        functions = {}
        
        # 定义需要提取的关键函数
        key_functions = [
            'initialize', 'before_trading_start', 'handle_data', 'after_trading_end',
            'daily_check', 'prepare_stock_list', 'get_current_data', 'get_last_trading_day_data'
        ]
        
        lines = jq_code.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('def '):
                # 提取函数名
                func_name = line.split('(')[0].replace('def ', '').strip()
                # 提取所有自定义函数
                func_lines = [lines[i]]
                i += 1
                indent_level = None
                while i < len(lines):
                    next_line = lines[i]
                    stripped = next_line.lstrip()
                    if stripped == '':
                        func_lines.append(next_line)
                        i += 1
                        continue
                    if next_line.strip().startswith('def '):
                        break
                    current_indent = len(next_line) - len(stripped)
                    if indent_level is None:
                        if current_indent > 0:
                            indent_level = current_indent
                        func_lines.append(next_line)
                    elif current_indent < indent_level:
                        break
                    else:
                        func_lines.append(next_line)
                    i += 1
                functions[func_name] = '\n'.join(func_lines)
            else:
                i += 1
        
        return functions
    
    def _merge_functions_to_template(self, template: str, functions: Dict[str, str]) -> str:
        """将提取的函数合并到模板中"""
        result = template
        
        # 替换模板中的函数
        for func_name, func_code in functions.items():
            # 查找模板中的函数定义，使用re.escape确保安全
            escaped_func_name = re.escape(func_name)
            pattern = 'def ' + escaped_func_name + r'\(.*?\):.*?(?=\n\ndef|\Z)'
            try:
                if re.search(pattern, result, re.DOTALL):
                    # 替换函数实现
                    result = re.sub(pattern, func_code, result, flags=re.DOTALL)
                else:
                    # 如果模板中没有该函数，添加到末尾
                    result = result.rstrip() + '\n\n' + func_code
            except re.error:
                # 如果正则表达式出错，直接添加函数到末尾
                result = result.rstrip() + '\n\n' + func_code
        
        return result
    
    def _standardize_security_code(self, code: str) -> str:
        """标准化证券代码后缀"""
        try:
            # 将 .XSHG 替换为 .SS
            code = re.sub(r'\.XSHG(?![a-zA-Z0-9])', '.SS', code)
            # 将 .XSHE 替换为 .SZ
            code = re.sub(r'\.XSHE(?![a-zA-Z0-9])', '.SZ', code)
        except re.error:
            # 如果正则表达式出错，跳过处理
            pass
        return code
    
    def _convert_apis(self, code: str) -> str:
        """处理API转换"""
        lines = code.split('\n')
        new_lines = []
        
        for line in lines:
            original_line = line
            
            # 处理get_current_data调用
            if 'get_current_data(' in line or 'get_current_data()' in line:
                # 检查是否有参数
                if 'get_current_data()' in line:
                    # 无参数调用，添加context参数
                    line = line.replace('get_current_data()', 'get_current_data(context)')
                    line = '# [已转换] ' + line + '  # 原聚宽get_current_data()已转换为自定义函数'
                else:
                    # 有参数调用，添加context参数，避免重复替换
                    if 'get_current_data(context' not in line:
                        line = re.sub(r'get_current_data\(([^)]+)\)', r'get_current_data(context, \1)', line)
                        line = '# [已转换] ' + line + '  # 原聚宽get_current_data()已转换为自定义函数'
            
            # 处理set_option函数
            if 'set_option(' in line:
                # 检查是否是order_volume_ratio参数
                if 'order_volume_ratio' in line:
                    # 可以转换的set_option
                    line = line.replace('set_option(', '# [已转换] set_option(')
                    line = line.replace(')', ')  # PTrade使用其他方式设置')
                else:
                    # 无法转换的set_option，添加注释
                    line = '# [无法转换] ' + line + '  # PTrade不支持此set_option参数'
            
            # 处理set_order_cost函数 - 用set_commission替代
            if 'set_order_cost(' in line:
                # 添加注释说明替代方案
                line = '# [已替换] ' + line + '  # PTrade建议使用set_commission替代'
            
            # 处理set_slippage函数 - 转换为set_fixed_slippage
            if 'set_slippage(' in line:
                line = line.replace('set_slippage(', 'set_fixed_slippage(')
                line = '# [已转换] ' + line + '  # 参数可能需要调整'
            
            # 处理get_trade_days函数 - 注意日期格式
            if 'get_trade_days(' in line:
                line = '# [注意日期格式] ' + line + '  # PTrade要求start_date、end_date必须是YYYY-MM-DD格式'
            
            # 处理run_weekly和run_monthly函数 - 转换为run_daily
            if 'run_weekly(' in line and 'context,' not in line:
                # 将run_weekly转换为run_daily，因为Ptrade不支持run_weekly
                line = line.replace('run_weekly(', 'run_daily(context, ')
                line = '# [已转换] ' + line + '  # 原run_weekly已转换为run_daily'
            elif 'run_monthly(' in line and 'context,' not in line:
                # 将run_monthly转换为run_daily，因为Ptrade可能不支持run_monthly
                line = line.replace('run_monthly(', 'run_daily(context, ')
                line = '# [已转换] ' + line + '  # 原run_monthly已转换为run_daily'
            
            # 处理run_daily函数
            if 'run_daily(' in line and 'context,' not in line:
                line = line.replace('run_daily(', 'run_daily(context, ')
            
            # 移除weekday参数
            line = re.sub(r",\s*weekday\s*=\s*\d+", "", line)
            
            # 移除reference_security参数
            line = re.sub(r",\s*reference_security\s*=\s*'[^']+'", "", line)
            line = re.sub(r",\s*reference_security\s*=\s*\"[^\"]+\"", "", line)
            line = re.sub(r"reference_security\s*=\s*'[^']+'", "", line)
            line = re.sub(r"reference_security\s*=\s*\"[^\"]+\"", "", line)
            
            # 清理可能的多余逗号和空格
            line = re.sub(r"\(\s*,", "(", line)
            line = re.sub(r",\s*\)", ")", line)
            line = re.sub(r",\s*,", ", ", line)
            
            # 移除不支持的API调用
            unsupported_apis = [
                'log.set_level(',
                'set_commission(',
                'set_price_limit(',
            ]
            
            should_remove = False
            for api in unsupported_apis:
                if api in line:
                    should_remove = True
                    break
            
            if should_remove:
                line = '# [已移除] ' + line + '  # PTrade不支持此API'
            
            new_lines.append(line)
        
        code = '\n'.join(new_lines)
        
        # 移除聚宽特定的导入
        code = self._remove_jq_imports(code)
        
        return code
    
    def _remove_jq_imports(self, code: str) -> str:
        """移除聚宽特定的导入"""
        lines = code.split('\n')
        filtered_lines = []
        for line in lines:
            # 移除聚宽特定的导入语句
            if not (line.startswith('import jqdata') or 
                   line.startswith('from jqdata import') or
                   line.startswith('import jqfactor') or
                   line.startswith('from jqfactor import')):
                filtered_lines.append(line)
        return '\n'.join(filtered_lines)

# 使用示例
if __name__ == "__main__":
    # 示例聚宽代码，包含get_current_data调用
    sample_jq_code = '''
import jqdata
from jqdata import *

def initialize(context):
    g.security = '000001.XSHE'
    set_benchmark('000300.XSHG')
    run_daily(daily_check, time='9:30', reference_security='000300.XSHG')

def daily_check(context):
    # 获取当前数据 - 聚宽可以直接调用
    current_data = get_current_data()
    
    for stock in g.security:
        if stock in current_data:
            data = current_data[stock]
            print(f"{stock}: 开盘价={data.open}, 收盘价={data.close}")
    
    # 带参数调用
    specific_data = get_current_data(['000001.XSHE', '000002.XSHE'])
    print(specific_data)

def handle_data(context, data):
    pass
'''
    
    # 创建转换器
    converter = JQToPtradeCurrentDataConverter()
    
    # 转换代码
    try:
        ptrade_code = converter.convert(sample_jq_code)
        print("转换后的Ptrade回测版代码:")
        print("=" * 50)
        print(ptrade_code)
        print("=" * 50)
    except Exception as e:
        print(f"转换失败: {e}")
        import traceback
        traceback.print_exc()