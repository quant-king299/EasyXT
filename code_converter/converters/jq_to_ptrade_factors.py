"""
聚宽到Ptrade因子转换器
处理因子库调用转换为自定义计算函数
"""
import re
from typing import Dict, List

class JQToPtradeFactorsConverter:
    """处理因子转换的转换器"""
    
    def __init__(self):
        pass
    
    def convert(self, jq_code: str) -> str:
        """
        转换聚宽代码为Ptrade回测版代码，特别处理因子计算
        
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
        
        # 处理因子转换
        result = self._convert_factors(result)
        
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
    run_daily(context, weekly_adjustment, time='9:30')  # 原run_weekly已转换为run_daily

def before_trading_start(context, data):
    # 盘前处理
    pass
    
    # 注意：不能在before_trading_start中调用run_daily
    # 定时任务应该在initialize中设置

def get_macd_value(context, stock):
    """
    计算MACD指标值
    Ptrade需要自定义实现，聚宽可以直接调用
    """
    # 获取历史数据
    h = get_history(50, '1d', ['close'], stock_list=[stock])
    close_data = h['close'].values
    
    # 计算MACD
    macd_DIF, macd_DEA, macd_hist = get_MACD(close_data, 12, 26, 9)
    macd = macd_hist[-1]
    return macd

def get_MACD(close_prices, short_period=12, long_period=26, signal_period=9):
    """
    计算MACD指标
    """
    # 计算快速EMA
    ema_short = pd.Series(close_prices).ewm(span=short_period).mean()
    # 计算慢速EMA
    ema_long = pd.Series(close_prices).ewm(span=long_period).mean()
    # 计算DIF
    dif = ema_short - ema_long
    # 计算DEA
    dea = dif.ewm(span=signal_period).mean()
    # 计算MACD柱状图
    bar = (dif - dea) * 2
    
    return dif.values, dea.values, bar.values

def get_single_factor_list(context, stock_list, jqfactor, sort, p1, p2):
    """
    获取因子列表 - 回测版本
    [回测版本注意] get_factor_values可能在回测中不完全支持
    如果回测中报错，需要使用get_history或其他替代方法
    """
    try:
        yesterday = context.previous_date
        s_score = get_factor_values(stock_list, jqfactor, end_date=yesterday, count=1)[jqfactor].iloc[0].dropna().sort_values(ascending=sort)
        return s_score.index[int(p1 * len(stock_list)):int(p2 * len(stock_list))].tolist()
    except Exception as e:
        # 回测环境可能不支持此函数，返回空列表
        log.warning(f"[get_single_factor_list] 出错: {str(e)}")
        return []

def sorted_by_circulating_market_cap(stock_list, n_limit_top=5):
    """
    按流通市值排序 - 回测版本
    [回测版本注意] query和get_fundamentals可能在回测中有限制
    """
    try:
        q = query(valuation.code).filter(valuation.code.in_(stock_list), indicator.eps > 0).order_by(valuation.circulating_market_cap.asc()).limit(n_limit_top)
        return get_fundamentals(q)['code'].tolist()
    except Exception as e:
        # 回测环境可能不支持，返回原始列表
        log.warning(f"[sorted_by_circulating_market_cap] 出错: {str(e)}")
        return stock_list[:n_limit_top]

def get_stock_list(context):
    """
    获取股票池 - 回测版本
    [回测版本优化] 使用备选方案避免因基本面数据缺失导致失败
    """
    try:
        by_date = context.previous_date - datetime.timedelta(days=375)
        by_date_str = by_date.strftime('%Y-%m-%d')
        
        try:
            ashare_data = get_Ashares(date=by_date_str)
            if hasattr(ashare_data, 'index'):
                initial_list = ashare_data.index.tolist()
            else:
                initial_list = get_index_stocks('000001.XSHG')
        except:
            initial_list = get_index_stocks('000001.XSHG')
        
        if not initial_list:
            log.warning("[get_stock_list] 无法获取股票列表，返回空列表")
            return []
        
        initial_list = filter_kcb_stock(initial_list)
        initial_list = filter_st_stock(initial_list)
        
        # [回测版本简化] 基本面因子选股
        # 由于回测环境可能不支持所有数据，使用简化版本
        try:
            # 尝试获取销售增长率
            sg_list = get_single_factor_list(context, initial_list, 'sales_growth', False, 0, 0.1)
            if sg_list:
                sg_list = sorted_by_circulating_market_cap(sg_list)
            else:
                sg_list = initial_list[:int(0.1 * len(initial_list))]
        except:
            sg_list = initial_list[:int(0.1 * len(initial_list))]
        
        # [回测版本简化] 利润增长因子
        try:
            factor_list = ['operating_revenue_growth_rate', 'total_profit_growth_rate', 'net_profit_growth_rate', 'earnings_growth']
            factor_values = get_factor_values(initial_list, factor_list, end_date=context.previous_date, count=1)
            df = pd.DataFrame(index=initial_list)
            for factor in factor_list:
                try:
                    df[factor] = factor_values[factor].iloc[0]
                except:
                    df[factor] = 0
            
            df['total_score'] = 0.1 * df['operating_revenue_growth_rate'] + 0.35 * df['total_profit_growth_rate'] + 0.15 * df['net_profit_growth_rate'] + 0.4 * df['earnings_growth']
            ms_list = df.sort_values(by=['total_score'], ascending=False).index[:int(0.1 * len(df))].tolist()
            ms_list = sorted_by_circulating_market_cap(ms_list)
        except:
            ms_list = initial_list[:int(0.1 * len(initial_list))]
        
        # [回测版本简化] PEG和周转率因子
        try:
            peg_list = get_single_factor_list(context, initial_list, 'PEG', True, 0, 0.2)
            if peg_list:
                peg_list = get_single_factor_list(context, peg_list, 'turnover_volatility', True, 0, 0.5)
                peg_list = sorted_by_circulating_market_cap(peg_list)
            else:
                peg_list = initial_list[:int(0.2 * len(initial_list))]
        except:
            peg_list = initial_list[:int(0.2 * len(initial_list))]
        
        # 合并因子选股结果
        union_list = list(set(sg_list).union(set(ms_list)).union(set(peg_list)))
        union_list = sorted_by_circulating_market_cap(union_list, 100)
        
        print('选股结果：', union_list)
        return union_list
        
    except Exception as e:
        log.error(f"[get_stock_list] 异常: {str(e)}")
        return []

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

def weekly_adjustment(context):
    """周度调整 - 回测版本（实际每天运行，但只在特定条件下执行）"""
    # 判断是否为周一或者特定条件
    import datetime
    weekday = context.current_dt.weekday()  # 0是周一，6是周日
    
    # 只在周一执行
    if weekday == 0:
        try:
            target_list = get_stock_list(context)
            if not target_list:
                log.warning("[weekly_adjustment] 无目标股票")
                return
            
            target_list = filter_paused_stock(target_list)
            target_list = filter_limit_stock(context, target_list)
            
            try:
                recent_limit_up_list = get_recent_limit_up_stock(context, target_list, context.limit_days)
                black_list = list(set(context.not_buy_again_list).intersection(set(recent_limit_up_list)))
                target_list = [stock for stock in target_list if stock not in black_list]
            except:
                pass
            
            if len(target_list) > 10:
                target_list = target_list[:10]
            
            # [回测版本简化] 趋势分析
            try:
                h_ma = history(20 + 20, '1d', 'close', target_list).rolling(window=20).mean().iloc[20:]
                X = np.arange(len(h_ma))
                tmp_target_list = []
                
                for stock in target_list:
                    try:
                        MA_N_Arr = h_ma[stock].values
                        MA_N_Arr = MA_N_Arr - MA_N_Arr[0]
                        slope = round(sm.OLS(MA_N_Arr, X).fit().params[0] * 100, 1)
                        if slope < -2:
                            if stock not in context.hold_list:
                                print('{}下降趋势明显，切勿开仓'.format(stock))
                                continue
                        tmp_target_list.append(stock)
                    except:
                        tmp_target_list.append(stock)
                
                target_list = tmp_target_list
            except:
                pass
            
            # 调整持仓
            for stock in context.hold_list:
                if stock not in target_list and stock not in context.high_limit_list:
                    log.info('卖出[%s]' % stock)
                    position = context.portfolio.positions[stock]
                    close_position(position)
                else:
                    log.info('已持有[%s]' % stock)
            
            position_count = len(context.portfolio.positions)
            target_num = min(len(set(target_list).union(set(context.portfolio.positions))), context.stock_num)
            
            if target_num > position_count:
                value = target_num / context.stock_num * context.portfolio.cash / (target_num - position_count)
                for stock in target_list:
                    if stock not in context.portfolio.positions:
                        if open_position(stock, value):
                            if len(context.portfolio.positions) >= context.stock_num:
                                break
        
        except Exception as e:
            log.error(f"[weekly_adjustment] 异常: {str(e)}")

def check_limit_up(context):
    """
    检查涨停状态 - 回测版本已禁用
    [回测版本注意] 此函数需要get_snapshot()，而get_snapshot()在回测中不支持
    因此此函数在回测版本中被禁用
    如需类似功能，可在weekly_adjustment中使用get_price检查
    """
    log.info("[check_limit_up] 回测版本不支持此函数，已禁用")
    pass

def filter_paused_stock(stock_list):
    """过滤停牌股票 - 回测版本"""
    try:
        # 回测版本：使用get_price判断停牌
        if not stock_list:
            return stock_list
        
        try:
            df = get_price(stock_list, count=1, fields=['volume'])
            # 通过成交量判断是否停牌
            return [stock for stock in stock_list if df.loc[stock, 'volume'] > 0]
        except:
            # 无法判断，返回原始列表
            return stock_list
    except Exception as e:
        log.warning(f"[filter_paused_stock] 异常: {str(e)}")
        return stock_list

def filter_st_stock(stock_list):
    """过滤ST股票 - 回测版本"""
    try:
        if not stock_list:
            return stock_list
        
        # 回测版本：简化处理，直接返回
        # 如需过滤，可通过股票名称或其他方式实现
        return stock_list
    except Exception as e:
        log.warning(f"[filter_st_stock] 异常: {str(e)}")
        return stock_list

def get_recent_limit_up_stock(context, stock_list, recent_days):
    """获取近期涨停股票 - 回测版本"""
    try:
        yesterday = context.previous_date
        h = get_price(stock_list, end_date=yesterday, fields=['close', 'high_limit', 'paused'], count=recent_days)
        s_limit = h.query('close==high_limit and paused==0').groupby('code')['high_limit'].count()
        return s_limit.index.tolist()
    except Exception as e:
        log.warning(f"[get_recent_limit_up_stock] 异常: {str(e)}")
        return []

def filter_limit_stock(context, stock_list):
    """过滤涨跌停股票 - 回测版本"""
    try:
        if not stock_list:
            return stock_list
        
        # 回测版本：简化处理
        holdings = list(context.portfolio.positions)
        return stock_list
    except Exception as e:
        log.warning(f"[filter_limit_stock] 异常: {str(e)}")
        return stock_list

def filter_kcb_stock(stock_list):
    """过滤科创板股票"""
    return [stock for stock in stock_list if not stock.startswith('68')]

def order_target_value_(security, value):
    """目标金额下单"""
    if value == 0:
        log.debug('Selling out %s' % security)
    else:
        log.debug('Order %s to value %f' % (security, value))
    return order_target_value(security, value)

def open_position(security, value):
    """开仓"""
    _order = order_target_value_(security, value)
    if _order is not None and _order.filled > 0:
        return True
    return False

def close_position(position):
    """平仓"""
    security = position.security
    _order = order_target_value_(security, 0)
    if _order is not None:
        if _order.status == OrderStatus.held and _order.filled == _order.amount:
            return True
    return False

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
            'get_stock_list', 'prepare_stock_list', 'weekly_adjustment',
            'filter_paused_stock', 'filter_st_stock', 'filter_limit_stock',
            'get_single_factor_list', 'sorted_by_circulating_market_cap',
            'get_recent_limit_up_stock', 'filter_kcb_stock',
            'order_target_value_', 'open_position', 'close_position',
            'get_macd_value', 'get_MACD'  # 特别处理因子计算函数
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
            
            # 处理get_current_data函数 - 无法转换，添加警告注释
            if 'get_current_data(' in line or 'get_current_data()' in line:
                line = '# [警告] ' + line + '  # PTrade无此函数，需要手动调整策略'
            
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
                'get_current_data('
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
    
    def _convert_factors(self, code: str) -> str:
        """处理因子转换"""
        lines = code.split('\n')
        new_lines = []
        
        for line in lines:
            # 处理聚宽因子调用转换为自定义函数
            # 例如: MACD(stock, check_date=check_date) 转换为 get_macd_value(context, stock)
            
            # 处理MACD因子调用
            if 'MACD(' in line and '=' in line:
                # 匹配类似 MACD(stock, check_date=check_date) 的调用
                # 更精确地匹配MACD调用，避免误匹配内部函数
                line = re.sub(r'([^a-zA-Z0-9_])MACD\(([^,]+),[^)]+\)', r'\1get_macd_value(context, \2)', line)
                line = '# [已转换] ' + line + '  # 原聚宽MACD调用已转换为自定义函数'
            
            # 处理其他因子库调用（可以根据需要添加更多）
            # 例如: RSI(stock, N=14) 等
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
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
    # 示例聚宽代码，包含因子调用
    sample_jq_code = '''
import jqdata
from jqfactor import MACD, RSI

def initialize(context):
    g.security = '000001.XSHE'
    set_benchmark('000300.XSHG')
    run_daily(daily_check, time='9:30', reference_security='000300.XSHG')

def daily_check(context):
    # 获取MACD值 - 聚宽可以直接调用
    macd_value = MACD('000001.XSHE', check_date=context.previous_date)
    
    # 获取RSI值
    rsi_value = RSI('000001.XSHE', N=14)
    
    print(f"MACD: {macd_value}, RSI: {rsi_value}")

def handle_data(context, data):
    pass
'''
    
    # 创建转换器
    converter = JQToPtradeFactorsConverter()
    
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