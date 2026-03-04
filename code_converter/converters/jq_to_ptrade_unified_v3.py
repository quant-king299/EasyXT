"""
聚宽到Ptrade统一转换器 v3.10 (修复get_Ashares返回值处理)
更新说明:
- ✅ 修复get_Ashares().index.tolist()错误（改为list(get_Ashares())）
- ✅ 证券代码后缀可选转换（默认不转换，Ptrade支持.XSHG/.XSHE）
- ✅ 新增get_factor_values兼容函数（基于get_fundamentals封装）
- ✅ 完善get_fundamentals转换（支持fields字符串/列表、is_dataframe）
- ✅ 基于实际Ptrade Demo策略验证

所有已知问题已修复！
"""
import re
import ast
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum


class StrategyType(Enum):
    """策略类型枚举"""
    BACKTEST = "backtest"
    LIVE = "live"
    HYBRID = "hybrid"


class APIUsage(Enum):
    """API使用情况"""
    FUNDAMENTALS = "fundamentals"
    FACTORS = "factors"
    TECHNICAL = "technical"
    BASIC = "basic"
    REALTIME = "realtime"


class JQToPtradeUnifiedConverter:
    """聚宽到Ptrade统一转换器 v3.10

    基于实际Ptrade运行验证和Demo策略分析
    修复: get_Ashares返回值处理、get_factor_values兼容、完善get_fundamentals转换
    """

    def __init__(self, verbose: bool = True, convert_security_codes: bool = False):
        """
        初始化转换器

        Args:
            verbose: 是否显示详细转换信息
            convert_security_codes: 是否转换证券代码后缀（.XSHG->.SS, .XSHE->.SZ）
                                     默认False，因为Ptrade向后兼容.XSHG/.XSHE格式
        """
        self.verbose = verbose
        self.convert_security_codes = convert_security_codes
        self.conversion_report = {
            'warnings': [],
            'errors': [],
            'changes': [],
            'api_mappings': [],
            'added_functions': []
        }

        # API映射规则 (基于实际Ptrade运行验证)
        self.api_mapping = {
            'get_price': 'get_price',
            'get_history': 'get_history',
            'get_bars': 'get_history',
            'history': 'get_history',  # 聚宽的history()函数
            'get_current_data': 'get_snapshot',
            'get_all_securities': 'get_Ashares',
            'get_security_info': 'get_stock_info',
            'get_index_stocks': 'get_index_stocks',
            'get_industry_stocks': 'get_industry_stocks',
            'get_portfolio': 'get_portfolio',
            'get_positions': 'get_positions',
            'get_orders': 'get_orders',
            'order': 'order',
            'order_value': 'order_value',
            'order_target': 'order_target',
            'order_target_value': 'order_target_value',
            'cancel_order': 'cancel_order',
            'log': 'log',
            'record': 'record',
            'set_benchmark': 'set_benchmark',
            # 注意：定时函数不添加context前缀，保持全局函数调用
            # run_daily, run_weekly, run_monthly 在_convert_timing_functions中单独处理
        }

        # 特殊处理函数
        self.special_apis = {
            'get_current_data': self._handle_get_current_data,
            'get_factor_values': self._handle_get_factor_values,
            'get_fundamentals': self._handle_get_fundamentals,
            'query': self._handle_query,
            'get_Ashares': self._handle_get_Ashares,
        }

        # 不支持的API
        self.unsupported_apis = {
            'log.set_level',
            'set_commission',
            'set_price_limit',
            'set_order_cost',
            'set_option',  # 添加set_option到不支持列表
        }

    def convert(self, jq_code: str, strategy_type: Optional[StrategyType] = None) -> str:
        """转换聚宽代码为Ptrade代码"""
        self.conversion_report = {
            'warnings': [],
            'errors': [],
            'changes': [],
            'api_mappings': [],
            'added_functions': []
        }

        if self.verbose:
            print("=" * 60)
            print("聚宽到Ptrade统一转换器 v3.4 (修复datetime导入)")
            print("智能添加辅助函数 + 精简注释 + 修复导入问题")
            print("=" * 60)

        # 1. 分析代码
        code_analysis = self._analyze_code(jq_code)

        # 2. 确定策略类型
        if strategy_type is None:
            strategy_type = self._detect_strategy_type(code_analysis)

        if self.verbose:
            print(f"\n[OK] 检测到策略类型: {strategy_type.value}")
            print(f"[OK] 使用的API类型: {', '.join([api.value for api in code_analysis['api_usage']])}")

        # 3. 执行转换
        converted_code = self._perform_conversion(jq_code, code_analysis, strategy_type)

        # 4. 后处理
        converted_code = self._post_process(converted_code, strategy_type)

        # 5. 添加辅助函数
        converted_code = self._add_helper_functions(converted_code, code_analysis)

        # 6. 生成报告
        if self.verbose:
            self._print_report()

        return converted_code

    def _analyze_code(self, code: str) -> Dict:
        """分析代码特征"""
        analysis = {
            'api_usage': set(),
            'functions': [],
            'uses_realtime_data': False,
            'uses_historical_data': False,
            'uses_fundamentals': False,
            'uses_factors': False,
            'uses_monthly_timing': False,
            'uses_current_data': False,
        }

        # 检测API使用
        api_patterns = {
            APIUsage.FUNDAMENTALS: [
                r'get_fundamentals\s*\(',
                r'query\s*\(',
            ],
            APIUsage.FACTORS: [
                r'get_factor_values\s*\(',
                r'from\s+jqfactor\s+import',
            ],
            APIUsage.TECHNICAL: [
                r'MACD\s*\(',
                r'RSI\s*\(',
            ],
            APIUsage.BASIC: [
                r'get_price\s*\(',
                r'get_history\s*\(',
                r'attribute_history\s*\(',
            ],
            APIUsage.REALTIME: [
                r'get_current_data\s*\(',
            ],
        }

        for api_type, patterns in api_patterns.items():
            for pattern in patterns:
                if re.search(pattern, code):
                    analysis['api_usage'].add(api_type)
                    if api_type == APIUsage.FUNDAMENTALS:
                        analysis['uses_fundamentals'] = True
                    elif api_type == APIUsage.FACTORS:
                        analysis['uses_factors'] = True
                    elif api_type == APIUsage.REALTIME:
                        analysis['uses_realtime_data'] = True
                        analysis['uses_current_data'] = True
                    elif api_type == APIUsage.BASIC:
                        analysis['uses_historical_data'] = True

        # 检测run_monthly使用
        if re.search(r'run_monthly\s*\(', code):
            analysis['uses_monthly_timing'] = True

        # 提取函数定义
        function_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*:'
        analysis['functions'] = re.findall(function_pattern, code)

        return analysis

    def _detect_strategy_type(self, code_analysis: Dict) -> StrategyType:
        """检测策略类型"""
        if code_analysis['uses_realtime_data']:
            if code_analysis['uses_historical_data']:
                return StrategyType.HYBRID
            return StrategyType.LIVE

        function_names = ' '.join(code_analysis['functions'])
        if any(keyword in function_names for keyword in ['check_limit_up', 'realtime', 'live']):
            return StrategyType.LIVE

        return StrategyType.BACKTEST

    def _perform_conversion(self, code: str, analysis: Dict, strategy_type: StrategyType) -> str:
        """执行转换"""
        result = code

        # 1. 处理定时任务（必须在常规API映射之前，因为run_monthly需要特殊处理）
        result = self._convert_timing_functions(result, analysis)

        # 2. 处理特殊API（注意：get_Ashares处理在API映射之后进行）
        for api_name, handler in self.special_apis.items():
            # 跳过get_Ashares，在API映射之后再处理
            if api_name == 'get_Ashares':
                continue
            if re.search(rf'{api_name}\s*\(', result):
                result = handler(result, strategy_type)
        # 3. 常规API映射（排除已经处理的定时任务API）
        for jq_api, ptrade_api in self.api_mapping.items():
            # 跳过定时任务API，已经在_convert_timing_functions中处理
            if jq_api in ['run_daily', 'run_weekly', 'run_monthly']:
                continue

            pattern = rf'\b{re.escape(jq_api)}\b'
            if re.search(pattern, result):
                result = re.sub(pattern, ptrade_api, result)
                self.conversion_report['api_mappings'].append(f'{jq_api} → {ptrade_api}')

        # 3.5. 处理get_Ashares的日期格式（必须在get_all_securities→get_Ashares映射之后）
        result = self._handle_get_Ashares(result, strategy_type)

        # 4. 处理全局变量
        result = self._convert_global_variable(result)

        # 5. 标准化证券代码
        result = self._standardize_security_codes(result)

        # 6. 移除不支持的API
        result = self._remove_unsupported_apis(result)

        # 7. 转换技术指标
        result = self._convert_technical_indicators(result)

        # 8. 转换其他杂项
        result = self._convert_misc_issues(result)

        return result

    def _handle_get_current_data(self, code: str, strategy_type: StrategyType) -> str:
        """
        智能处理get_current_data调用
        聚宽的get_current_data()返回当前快照数据，Ptrade用get_snapshot()
        但需要根据使用方式提供不同的替代方案
        """
        # 检测get_current_data的使用模式
        usage_patterns = [
            (r'get_current_data\(\)\[([^\]]+)\]\.last_price', 'last_price'),
            (r'get_current_data\(\)\[([^\]]+)\]\.paused', 'paused'),
            (r'get_current_data\(\)\[([^\]]+)\]\.is_st', 'is_st'),
            (r'get_current_data\(\)', 'general'),
        ]

        has_get_current_data = False
        for pattern, usage_type in usage_patterns:
            if re.search(pattern, code):
                has_get_current_data = True
                break

        if not has_get_current_data:
            return code

        self.conversion_report['warnings'].append(
            "检测到get_current_data使用。已转换为get_snapshot并添加兼容函数。"
        )

        # 替换get_current_data为get_snapshot
        code = re.sub(r'\bget_current_data\s*\(\)', 'get_snapshot()', code)

        # 添加get_current_data兼容函数（如果不存在）
        if 'def get_current_data_compat' not in code:
            # 简化注释，保留必要信息
            compat_function = '''
# get_current_data兼容函数 - 替代聚宽的get_current_data()
def get_current_data_compat(security_list=None):
    """模拟聚宽get_current_data()功能，使用get_price()实现"""
    import pandas as pd

    try:
        if security_list is None:
            # 返回空字典，需要用户传入具体的security_list
            # 或者可以从context.portfolio.positions获取
            return {}

        # 使用get_price获取最近一天的数据
        df = get_price(security_list, count=1, fields=['close', 'high', 'low', 'volume', 'paused', 'name'])

        # 构造返回数据，模拟聚宽的get_current_data()返回格式
        result = {}
        for stock in security_list:
            if stock in df.index:
                row = df.loc[stock]
                # 估算涨跌停价格
                close_price = row['close'] if 'close' in row else 0
                result[stock] = type('obj', (), {
                    'last_price': close_price,
                    'high_limit': close_price * 1.1 if close_price > 0 else 0,  # 估算涨停价
                    'low_limit': close_price * 0.9 if close_price > 0 else 0,   # 估算跌停价
                    'paused': row.get('paused', False),                        # 停牌状态
                    'is_st': 'ST' in stock or '*' in stock,                     # ST状态
                    'name': row.get('name', stock),                             # 股票名称
                })()

        return result
    except Exception as e:
        # 出错时返回空字典
        return {}

# ========================================

'''
            # 在文件开头添加
            if compat_function not in code:
                code = compat_function + code

            # 替换get_snapshot()调用为get_current_data_compat()
            # 只替换用户代码区域，不替换compat_function内部
            lines = code.split('\n')
            compat_function_end = -1

            # 找到compat_function的结束位置
            for i, line in enumerate(lines):
                if line.strip() == '# ========================================' and i > 10:
                    compat_function_end = i
                    break

            if compat_function_end > 0:
                # 只替换用户代码部分
                user_code = '\n'.join(lines[compat_function_end+1:])
                user_code = re.sub(r'\bget_snapshot\s*\(\)', 'get_current_data_compat()', user_code)
                code = '\n'.join(lines[:compat_function_end+1]) + '\n' + user_code
            else:
                # 没有找到，直接替换
                code = re.sub(r'\bget_snapshot\s*\(\)', 'get_current_data_compat()', code)

        return code

    def _handle_get_factor_values(self, code: str, strategy_type: StrategyType) -> str:
        """处理get_factor_values - 添加Ptrade兼容实现

        聚宽: from jqfactor import get_factor_values (内置函数)
        Ptrade: 需要自己实现（基于get_fundamentals封装）
        """
        if not re.search(r'get_factor_values\s*\(', code):
            return code

        # 检测是否导入了jqfactor
        has_jqfactor_import = 'from jqfactor import' in code or 'import jqfactor' in code

        if has_jqfactor_import:
            # 添加Ptrade版本的get_factor_values实现
            compat_function = '''
# ======================================================================
# get_factor_values 兼容函数（Ptrade版本）
# ======================================================================
# 聚宽的get_factor_values是内置函数，Ptrade需要自己实现
# 这里基于get_fundamentals封装，提供基本的因子数据获取功能
#
# 使用方法:
#   df = get_factor_values(stocks, 'sales_growth', end_date=date, count=1)
#
# 注意: 因子名称需要映射到Ptrade的表和字段
# ======================================================================

def get_factor_values(stock_list, factor, end_date=None, count=1, **kwargs):
    """
    获取因子值（Ptrade兼容版本）

    参数:
        stock_list: 股票列表
        factor: 因子名称或因子列表
        end_date: 结束日期
        count: 数据条数（暂未实现，默认为1）
        **kwargs: 其他参数

    返回:
        DataFrame格式的因子数据
    """
    import pandas as pd

    # 因子名称映射：聚宽因子名 -> (Ptrade表名, Ptrade字段名)
    factor_mapping = {
        # 估值因子
        'market_cap': ('valuation', 'total_value'),
        'circulating_market_cap': ('valuation', 'a_floats'),
        'pe_ratio': ('valuation', 'pe_ratio'),
        'pb_ratio': ('valuation', 'pb_ratio'),
        'ps_ratio': ('valuation', 'ps_ratio'),

        # 财务指标因子
        'roe': ('indicator', 'roe'),
        'roa': ('indicator', 'roa'),
        'eps': ('indicator', 'eps'),
        'inc_revenue_year_on_year': ('indicator', 'operating_revenue_grow_rate'),
        'inc_net_profit_year_on_year': ('indicator', 'np_parent_company_cut_yoy'),
        'operating_revenue_grow_rate': ('indicator', 'operating_revenue_grow_rate'),

        # 增长因子
        'sales_growth': ('indicator', 'operating_revenue_grow_rate'),
        'net_profit_growth_rate': ('indicator', 'net_profit_growth_rate'),
        'total_profit_growth_rate': ('indicator', 'total_profit_growth_rate'),

        # 质量因子
        'total_shareholder_equity': ('balance_statement', 'total_shareholder_equity'),
    }

    # 处理单个因子
    if isinstance(factor, str):
        if factor not in factor_mapping:
            # 未映射的因子，尝试直接使用
            table = 'valuation'
            field = factor
        else:
            table, field = factor_mapping[factor]

        # 获取数据
        try:
            df = get_fundamentals(
                stock_list,
                table,
                fields=field,
                date=end_date,
                is_dataframe=True
            )

            if df is not None and not df.empty:
                # 重命名列
                df = df.rename(columns={field: factor})
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            print(f"获取因子{factor}失败: {e}")
            return pd.DataFrame()

    # 处理多个因子
    elif isinstance(factor, list):
        dfs = []
        for f in factor:
            df_f = get_factor_values(stock_list, f, end_date=end_date, count=count, **kwargs)
            if not df_f.empty:
                dfs.append(df_f)

        if dfs:
            # 合并所有因子的DataFrame
            result = pd.concat(dfs, axis=1)
            return result
        else:
            return pd.DataFrame()

    return pd.DataFrame()

'''

            # 移除jqfactor导入
            code = re.sub(r'from jqfactor import.*\n?', '', code)
            code = re.sub(r'import jqfactor.*\n?', '', code)

            # 添加兼容函数
            code = compat_function + '\n' + code

            self.conversion_report['changes'].append(
                'get_factor_values: 已添加Ptrade兼容实现（基于get_fundamentals封装）'
            )

            self.conversion_report['warnings'].append(
                "get_factor_values已添加兼容实现，但因子名称可能需要手动调整映射关系"
            )
        else:
            # 没有导入jqfactor，可能只是调用
            self.conversion_report['warnings'].append(
                "检测到get_factor_values使用，但未发现jqfactor导入。请确认是否需要添加兼容实现。"
            )

        return code

    def _handle_get_fundamentals(self, code: str, strategy_type: StrategyType) -> str:
        """处理get_fundamentals - 智能转换或添加转换指南

        聚宽: get_fundamentals(query_object)
        Ptrade: get_fundamentals(stock_list, "table", fields=[...], date=..., is_dataframe=False)
        """
        if not re.search(r'get_fundamentals\s*\(', code):
            return code

        conversion_guide = '''
# ======================================================================
# ⚠️ get_fundamentals API转换说明 ⚠️
# ======================================================================
# Ptrade的get_fundamentals API与聚宽完全不同：
#
# 【聚宽】: get_fundamentals(query_object) - 使用query对象
# 【Ptrade】: get_fundamentals(stock_list, "table", fields=[...], date=..., is_dataframe=False)
#
# 【Ptrade支持的表名】:
#   - "valuation": 估值数据（市值、PE、PB等）
#   - "indicator": 财务指标（EPS、ROE、营收增长率等）
#   - "balance_statement": 资产负债表
#   - "profit_ability": 利润表数据
#   - "growth_ability": 增长能力数据
#   - "cash_flow_statement": 现金流量表
#
# 【fields参数】:
#   - 单字段: fields='total_value'
#   - 多字段: fields=['code', 'total_value']
#
# 【is_dataframe参数】:
#   - True: 返回DataFrame格式
#   - False或省略: 返回dict格式
#
# 转换器已尝试自动转换，请检查结果是否正确！
# ======================================================================

'''

        lines = code.split('\n')
        result = []
        converted_count = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # 尝试自动转换get_fundamentals调用
            # 模式1: get_fundamentals(query_var)
            match = re.search(r'get_fundamentals\s*\(\s*(\w+)\s*\)', line)
            if match:
                query_var = match.group(1)

                # 向上查找query定义
                query_info = self._find_and_analyze_query(lines, i, query_var)

                if query_info and self._is_simple_query(query_info):
                    # 可以自动转换
                    ptrade_call = self._build_ptrade_fundamentals_call(query_info)
                    # 替换原调用
                    new_line = re.sub(
                        r'get_fundamentals\s*\([^)]*\)',
                        ptrade_call,
                        line
                    )
                    result.append(new_line + '  # [已转换为Ptrade格式]')
                    converted_count += 1
                    self.conversion_report['changes'].append(
                        f"自动转换get_fundamentals: table={query_info['table']}, fields={query_info['fields']}"
                    )
                else:
                    # 复杂query，无法自动转换
                    result.append(line)
                    if query_info:
                        result.append(f'    # ⚠️ 复杂query无法自动转换，需要手动调整')
                        result.append(f'    # 检测到表: {query_info.get("table", "?")}, 字段: {query_info.get("fields", "?")}')
                    else:
                        result.append(f'    # ⚠️ 无法分析query对象，请手动转换为Ptrade格式')
            else:
                result.append(line)

            i += 1

        # 添加转换信息
        if converted_count > 0:
            self.conversion_report['changes'].append(
                f"get_fundamentals: 已自动转换{converted_count}处简单调用"
            )
            code = conversion_guide + '\n'.join(result)
        else:
            # 没有自动转换，添加警告
            self.conversion_report['warnings'].append(
                "检测到get_fundamentals使用，但无法自动转换复杂query，请手动调整"
            )
            code = conversion_guide + code

        return code

    def _find_and_analyze_query(self, lines: list, current_idx: int, query_var: str) -> dict:
        """查找并分析query对象定义"""
        # 向上查找query定义
        for i in range(current_idx - 1, max(0, current_idx - 50), -1):
            line = lines[i]

            # 匹配 query_var = query(
            match = re.match(rf'{query_var}\s*=\s*query\s*\(', line)
            if match:
                # 收集完整query定义
                query_lines = [line]
                j = i + 1
                bracket_count = line.count('(') - line.count(')')

                while j < len(lines) and bracket_count > 0:
                    query_lines.append(lines[j])
                    bracket_count += lines[j].count('(') - lines[j].count(')')
                    j += 1

                query_code = '\n'.join(query_lines)
                return self._parse_simple_query(query_code)

        return None

    def _parse_simple_query(self, query_code: str) -> dict:
        """解析简单query对象

        返回: {
            'table': 'valuation',
            'fields': ['code', 'market_cap'],
            'stock_list_var': 'stock_list',
            'is_simple': bool
        }
        """
        info = {
            'table': None,
            'fields': [],
            'stock_list_var': None,
            'filters': [],
            'order_by': None,
            'limit': None,
            'is_simple': False
        }

        # 提取表和字段
        # 模式: query(valuation.code, valuation.field)
        table_field_pattern = r'query\s*\(\s*([a-z_]+)\.([a-z_]+)(?:\s*,\s*([a-z_]+)\.([a-z_]+))*'
        match = re.search(table_field_pattern, query_code)
        if match:
            info['table'] = match.group(1)
            info['fields'].append(match.group(2))
            # 检查是否有更多字段
            for m in re.finditer(r'([a-z_]+)\.([a-z_]+)', query_code):
                if m.group(1) == info['table']:
                    field = m.group(2)
                    if field not in info['fields']:
                        info['fields'].append(field)

        # 提取filter中的stock_list
        # 模式: valuation.code.in_(stock_list)
        stock_pattern = r'valuation\.code\.in_\s*\(\s*(\w+)'
        stock_match = re.search(stock_pattern, query_code)
        if stock_match:
            info['stock_list_var'] = stock_match.group(1)
        else:
            # 尝试其他模式
            stock_pattern2 = r'\.in_\s*\(\s*(\w+)'
            stock_match2 = re.search(stock_pattern2, query_code)
            if stock_match2:
                info['stock_list_var'] = stock_match2.group(1)

        # 检测复杂特性
        if '.order_by(' in query_code:
            info['order_by'] = True
        if '.limit(' in query_code:
            info['limit'] = True
        if '>.<' in query_code or '<.>' in query_code or '==' in query_code:
            info['filters'].append('complex')

        # 判断是否简单（只有基本字段查询和stock_list过滤）
        info['is_simple'] = (
            info['table'] is not None and
            len(info['fields']) > 0 and
            info['order_by'] is None and
            info['limit'] is None and
            len(info['filters']) == 0
        )

        return info

    def _is_simple_query(self, query_info: dict) -> bool:
        """判断是否是简单query（可以自动转换）"""
        return query_info and query_info.get('is_simple', False)

    def _build_ptrade_fundamentals_call(self, query_info: dict) -> str:
        """构建Ptrade格式的get_fundamentals调用

        Ptrade格式: get_fundamentals(stock_list, "table", fields=..., date=..., is_dataframe=False)
        """
        table = query_info.get('table', 'valuation')
        fields = query_info.get('fields', ['code'])
        stock_list_var = query_info.get('stock_list_var', 'stock_list')

        # 如果没有找到stock_list，使用context.portfolio.positions或提示
        if not stock_list_var:
            stock_list_var = 'context.portfolio.positions.keys()'

        # 构建fields参数
        # 单字段用字符串，多字段用列表
        if len(fields) == 1:
            fields_str = f"'{fields[0]}'"
        else:
            fields_str = str(fields)

        # 构建完整调用
        # 默认添加is_dataframe=True（因为大多数情况下需要DataFrame格式）
        return f'get_fundamentals(list({stock_list_var}), "{table}", fields={fields_str}, date=context.previous_date, is_dataframe=True)'


    def _handle_query(self, code: str, strategy_type: StrategyType) -> str:
        """处理query对象"""
        if not re.search(r'\bquery\s*\(', code):
            return code
        return code

    def _handle_get_Ashares(self, code: str, strategy_type: StrategyType) -> str:
        """处理get_all_securities/get_Ashares - 移除date参数和.index.tolist()

        聚宽: get_all_securities(date=xxx).index.tolist()
        Ptrade: get_Ashares() 或 list(get_Ashares())
        """
        # 注意：此函数在API映射之前被调用，所以代码中还是get_all_securities
        # 需要同时处理get_all_securities和get_Ashares两种情况

        # Ptrade的get_Ashares()不接受任何参数，直接返回所有A股列表
        # 返回值可能是列表或DataFrame，需要处理.index.tolist()

        # 第一步：移除date参数
        # 处理get_all_securities(date=xxx) → get_all_securities()
        pattern_all = r'get_all_securities\s*\(\s*date\s*=\s*[^)]*\)'
        code = re.sub(pattern_all, 'get_all_securities()', code)

        # 处理get_Ashares(date=xxx) → get_Ashares()
        pattern_ashares = r'get_Ashares\s*\(\s*date\s*=\s*[^)]*\)'
        code = re.sub(pattern_ashares, 'get_Ashares()', code)

        # 处理get_Ashares(_format_date(xxx)) → get_Ashares()
        pattern_ashares_format = r'get_Ashares\s*\(\s*_format_date\s*\([^)]*\)\s*\)'
        code = re.sub(pattern_ashares_format, 'get_Ashares()', code)

        # 第二步：处理.index.tolist()
        # Ptrade的get_Ashares()可能返回列表，不需要.index.tolist()
        # 模式1: get_all_securities().index.tolist() → list(get_all_securities())
        pattern_all_index = r'get_all_securities\(\)\.index\.tolist\(\)'
        code = re.sub(pattern_all_index, 'list(get_all_securities())', code)

        # 模式2: get_Ashares().index.tolist() → list(get_Ashares())
        pattern_ashares_index = r'get_Ashares\(\)\.index\.tolist\(\)'
        code = re.sub(pattern_ashares_index, 'list(get_Ashares())', code)

        # 模式3: xxx = get_Ashares().index → xxx = list(get_Ashares())
        pattern_index = r'(\w+)\s*=\s*get_(?:all_securities|Ashares)\(\)\.index'
        code = re.sub(pattern_index, r'\1 = list(get_Ashares())', code)

        if re.search(r'get_all_securities\(\)|get_Ashares\(\)', code):
            self.conversion_report['changes'].append(
                "get_all_securities()已转换为get_Ashares()，移除date参数，处理.index.tolist()为list()包装"
            )

        return code

    def _convert_timing_functions(self, code: str, analysis: Dict) -> str:
        """转换定时任务函数

        基于实际Ptrade运行验证(2026-03-02 12:00):
        - Ptrade只支持 run_daily(context, func, time='...')
        - 不支持 run_weekly() 和 run_monthly()
        - 必须将所有定时函数转换为run_daily()
        - 在函数内部添加日期检查逻辑
        """

        # 收集需要特殊处理的函数（用于添加日期检查）
        weekly_functions = []
        monthly_functions = []

        # 处理run_weekly - 转换为run_daily
        def replace_run_weekly(match):
            func_name = match.group(1)
            weekday = match.group(2) if match.group(2) else '1'
            time_str = match.group(3) if match.group(3) else "'09:30'"

            # 记录需要添加星期检查的函数
            weekly_functions.append({'name': func_name, 'weekday': weekday})

            # 转换为run_daily
            return f'run_daily(context, {func_name}, time={time_str})'

        run_weekly_pattern = r'run_weekly\s*\(\s*([^,]+),\s*weekday\s*=\s*(\d+)(?:,\s*time\s*=\s*([^,\)]+))?(?:,\s*reference_security\s*=\s*[^)]+)?\s*\)'

        if re.search(run_weekly_pattern, code):
            code = re.sub(run_weekly_pattern, replace_run_weekly, code)
            self.conversion_report['changes'].append(
                "run_weekly → run_daily (需要在函数内检查weekday)"
            )

        # 处理run_monthly - 转换为run_daily
        def replace_run_monthly(match):
            func_name = match.group(1).strip() if match.group(1) else ""
            monthday = match.group(2) if match.group(2) else "1"
            time_str = match.group(3) if match.group(3) else "'09:30'"

            # 记录需要添加月份检查的函数
            if func_name:
                monthly_functions.append({'name': func_name, 'day': monthday})

            # 转换为run_daily
            return f'run_daily(context, {func_name}, time={time_str})'

        run_monthly_pattern = r'run_monthly\s*\(\s*([^,\s]+)\s*(?:,\s*monthday\s*=\s*(\d+))?(?:,\s*time\s*=\s*([^,\)]+))?(?:,\s*reference_security\s*=\s*[^)]+)?\s*\)'

        if re.search(run_monthly_pattern, code):
            code = re.sub(run_monthly_pattern, replace_run_monthly, code)
            self.conversion_report['changes'].append(
                "run_monthly → run_daily (需要在函数内检查day of month)"
            )

        # 处理run_daily - 添加context参数
        def replace_run_daily(match):
            func_name = match.group(1)
            time_str = match.group(2) if match.group(2) else "'9:30'"

            # 添加context作为第一个参数
            return f'run_daily(context, {func_name}, time={time_str})'

        run_daily_pattern = r'run_daily\s*\(\s*([^,\s]+)\s*(?:,\s*time\s*=\s*([^,\)]+))?(?:,\s*reference_security\s*=\s*[^)]+)?\s*\)'

        if re.search(run_daily_pattern, code):
            code = re.sub(run_daily_pattern, replace_run_daily, code)
            self.conversion_report['changes'].append(
                "run_daily - 添加context参数，移除reference_security"
            )

        # 为需要星期/月份检查的函数添加检查逻辑
        code = self._add_timing_checks(code, weekly_functions, monthly_functions)

        return code

    def _add_timing_checks(self, code: str, weekly_functions: list, monthly_functions: list) -> str:
        """为函数添加日期检查逻辑"""
        if not weekly_functions and not monthly_functions:
            return code

        lines = code.split('\n')
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            result_lines.append(line)

            # 检查是否是需要添加检查的函数定义
            for func_info in weekly_functions:
                func_name = func_info['name']
                weekday = func_info['weekday']

                # 匹配函数定义行
                if re.match(rf'\s*def\s+{re.escape(func_name)}\s*\(', line):
                    # 在函数定义后添加星期检查
                    result_lines.append('')
                    result_lines.append('    # ========== run_weekly转换 ==========')
                    result_lines.append(f'    # 只在星期{weekday}执行')
                    result_lines.append(f"    if context.current_dt.weekday() + 1 != {weekday}:")
                    result_lines.append('        return  # 今天不是目标星期，直接返回')
                    result_lines.append('    # =====================================')
                    result_lines.append('')
                    break

            for func_info in monthly_functions:
                func_name = func_info['name']
                day = func_info['day']

                # 匹配函数定义行
                if re.match(rf'\s*def\s+{re.escape(func_name)}\s*\(', line):
                    # 在函数定义后添加月份检查
                    result_lines.append('')
                    result_lines.append('    # ========== run_monthly转换 ==========')
                    result_lines.append(f'    # 只在每月第{day}日执行')
                    result_lines.append(f'    if context.current_dt.day != {day}:')
                    result_lines.append('        return  # 今天不是目标日期，直接返回')
                    result_lines.append('    # =====================================')
                    result_lines.append('')
                    break

            i += 1

        return '\n'.join(result_lines)


    def _convert_global_variable(self, code: str) -> str:
        """转换全局变量"""
        code = re.sub(r'\bg\.', 'context.', code)
        code = re.sub(r'context\.(info|debug|warn|error)\s*\(', r'log.\1(', code)
        return code

    def _standardize_security_codes(self, code: str) -> str:
        """标准化证券代码（可选转换）

        基于Ptrade Demo分析：
        - Ptrade同时支持.XSHG/.XSHE（聚宽格式）和.SS/.SZ（新版格式）
        - 默认不转换，保持聚宽格式
        - 用户可以通过convert_security_codes=True参数启用转换
        """
        if self.convert_security_codes:
            # 转换为.SS/.SZ格式
            code = re.sub(r'\.XSHG\b', '.SS', code)
            code = re.sub(r'\.XSHE\b', '.SZ', code)
            if 'security_codes' not in self.conversion_report['changes']:
                self.conversion_report['changes'].append('证券代码后缀: .XSHG->.SS, .XSHE->.SZ')
        else:
            # 不转换，保持聚宽格式
            if 'security_codes' not in self.conversion_report['changes']:
                self.conversion_report['changes'].append('证券代码后缀: 保持原样（.XSHG/.XSHE）')
        return code

    def _remove_unsupported_apis(self, code: str) -> str:
        """移除不支持的API"""
        for api in self.unsupported_apis:
            pattern = rf'{re.escape(api)}\s*\([^)]*\)\s*(?=#|\n|$)'
            if re.search(pattern, code):
                code = re.sub(
                    pattern,
                    f'# [已移除] {api}()  # Ptrade不支持此API\n',
                    code
                )
                self.conversion_report['warnings'].append(f'已移除不支持的API: {api}')

        return code

    def _convert_technical_indicators(self, code: str) -> str:
        """转换技术指标，并记录使用了哪些指标"""
        macd_converted = False
        rsi_converted = False

        # MACD
        def convert_macd_call(match):
            nonlocal macd_converted
            stock = match.group(1)
            macd_converted = True
            return f'get_macd_value(context, {stock})'

        if re.search(r'MACD\s*\(', code):
            code = re.sub(
                r'MACD\s*\(\s*([^,)]+)\s*,[^)]*\)',
                convert_macd_call,
                code
            )

        # RSI
        def convert_rsi_call(match):
            nonlocal rsi_converted
            stock = match.group(1)
            rsi_converted = True
            return f'get_rsi_value(context, {stock})'

        if re.search(r'RSI\s*\(', code):
            code = re.sub(
                r'RSI\s*\(\s*([^,)]+)\s*(?:,[^)]*)?\)',
                convert_rsi_call,
                code
            )

        # 记录到分析结果
        if macd_converted:
            self.conversion_report['changes'].append("MACD指标已转换为get_macd_value()")
        if rsi_converted:
            self.conversion_report['changes'].append("RSI指标已转换为get_rsi_value()")

        # 将使用信息存储在conversion_report中
        if macd_converted:
            self.conversion_report['uses_macd'] = True
        if rsi_converted:
            self.conversion_report['uses_rsi'] = True

        return code

    def _convert_misc_issues(self, code: str) -> str:
        """转换其他杂项问题"""
        # 处理OrderStatus - Ptrade可能使用不同的常量名
        code = re.sub(
            r'\bOrderStatus\.held\b',
            "'held'",  # 使用字符串常量
            code
        )

        return code

    def _add_helper_functions(self, code: str, analysis: Dict) -> str:
        """添加辅助函数 - 只在代码中实际使用时才添加"""
        # 检查转换过程中是否实际使用了MACD/RSI
        uses_macd = self.conversion_report.get('uses_macd', False)
        uses_rsi = self.conversion_report.get('uses_rsi', False)
        has_get_current_data = 'get_current_data_compat' in code

        # 检查是否已经有函数定义（避免重复添加）
        has_macd_func = 'def get_macd_value' in code
        has_rsi_func = 'def get_rsi_value' in code
        has_compat_func = 'def get_current_data_compat' in code

        # 只有在代码中实际使用且没有定义时才添加
        if not (uses_macd or uses_rsi or has_get_current_data):
            return code

        helper_functions = []
        added_funcs = []

        # MACD函数
        if uses_macd and not has_macd_func:
            helper_functions.append('''
def get_macd_value(context, security, short_period=12, long_period=26, signal_period=9):
    """
    获取MACD指标值（兼容聚宽的MACD函数）

    Args:
        context: 上下文
        security: 证券代码
        short_period: 短周期
        long_period: 长周期
        signal_period: 信号周期

    Returns:
        float: MACD柱状图值
    """
    try:
        # 获取历史数据
        h = get_history(50, '1d', ['close'], stock_list=[security], end_date=context.current_dt)
        close_data = h['close'].values

        # 计算MACD
        import pandas as pd
        import numpy as np
        ema_short = pd.Series(close_data).ewm(span=short_period).mean()
        ema_long = pd.Series(close_data).ewm(span=long_period).mean()
        dif = ema_short - ema_long
        dea = dif.ewm(span=signal_period).mean()
        macd_bar = (dif - dea) * 2

        return macd_bar[-1]  # 返回最新的MACD柱状图值
    except Exception as e:
        log.warning(f"计算MACD失败: {e}")
        return 0.0
''')
            added_funcs.append('get_macd_value')

        # RSI函数
        if uses_rsi and not has_rsi_func:
            helper_functions.append('''
def get_rsi_value(context, security, period=14):
    """
    获取RSI指标值（兼容聚宽的RSI函数）

    Args:
        context: 上下文
        security: 证券代码
        period: 周期

    Returns:
        float: RSI值
    """
    try:
        # 获取历史数据
        h = get_history(period + 10, '1d', ['close'], stock_list=[security], end_date=context.current_dt)
        close_data = h['close'].values

        # 计算RSI
        import pandas as pd
        import numpy as np
        delta = pd.Series(close_data).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.values[-1]  # 返回最新的RSI值
    except Exception as e:
        log.warning(f"计算RSI失败: {e}")
        return 50.0
''')
            added_funcs.append('get_rsi_value')

        if helper_functions:
            # 合并所有辅助函数
            all_helpers = ''.join(helper_functions)

            # 在第一个def之前插入
            lines = code.split('\n')
            insert_index = 0
            for i, line in enumerate(lines):
                if line.startswith('def '):
                    insert_index = i
                    break
                elif not line.strip().startswith('#') and line.strip():
                    insert_index = i
                    break

            lines.insert(insert_index, all_helpers)
            code = '\n'.join(lines)

            self.conversion_report['added_functions'].extend(added_funcs)

        return code

    def _post_process(self, code: str, strategy_type: StrategyType) -> str:
        """后处理"""
        # 清理导入语句
        lines = code.split('\n')
        cleaned_lines = []

        for line in lines:
            if line.startswith('import jqdata') or line.startswith('from jqdata import'):
                cleaned_lines.append(f'# {line}  # 聚宽数据模块已移除')
            elif line.startswith('from jqfactor import') or line.startswith('import jqfactor'):
                cleaned_lines.append(f'# {line}  # 聚宽因子库需要手动处理')
            else:
                cleaned_lines.append(line)

        code = '\n'.join(cleaned_lines)

        # 检查代码中是否使用了datetime，确保导入
        uses_datetime = 'datetime.' in code or 'context.current_dt' in code or 'context.previous_date' in code
        has_datetime_import = 'import datetime' in code

        if uses_datetime and not has_datetime_import:
            # 在第一个import之前添加datetime导入
            lines = code.split('\n')
            import_index = -1
            for i, line in enumerate(lines):
                if line.startswith('import ') and 'import datetime' not in line:
                    import_index = i
                    break
                elif line.strip() and not line.startswith('#'):
                    import_index = i
                    break

            if import_index >= 0:
                lines.insert(import_index, 'import datetime  # 添加datetime导入\n')
                code = '\n'.join(lines)

        # 添加头部说明
        header = f'''# 聚宽策略转Ptrade - {strategy_type.value.upper()}版本
# 转换时间: {self._get_timestamp()}
# 转换器版本: v3.4 - 修复datetime导入，智能添加辅助函数

'''

        if not code.startswith('# 聚宽策略转Ptrade'):
            code = header + code

        if not code.endswith('\n'):
            code += '\n'

        return code

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _print_report(self):
        """打印转换报告"""
        print("\n" + "=" * 60)
        print("转换报告")
        print("=" * 60)

        if self.conversion_report['api_mappings']:
            print("\n[OK] API映射:")
            for mapping in self.conversion_report['api_mappings']:
                print(f"  - {mapping}")

        if self.conversion_report['changes']:
            print("\n[OK] 代码改动:")
            for change in self.conversion_report['changes']:
                print(f"  - {change}")

        if self.conversion_report['added_functions']:
            print("\n[OK] 添加的辅助函数:")
            for func in self.conversion_report['added_functions']:
                print(f"  - {func}")

        if self.conversion_report['warnings']:
            print("\n[WARNING] 警告:")
            for warning in self.conversion_report['warnings']:
                print(f"  - {warning}")

        if self.conversion_report['errors']:
            print("\n[ERROR] 错误:")
            for error in self.conversion_report['errors']:
                print(f"  - {error}")

        print("\n" + "=" * 60)
        print("转换完成！请检查生成的代码并根据警告信息手动调整。")
        print("=" * 60 + "\n")

    def get_conversion_report(self) -> Dict:
        """获取转换报告"""
        return self.conversion_report


# 使用示例
if __name__ == "__main__":
    # 测试代码
    sample_jq_code = '''
import jqdata
from jqfactor import MACD

def initialize(context):
    g.stock_num = 10
    g.hold_list = []
    set_benchmark('000300.XSHG')

    # 测试定时函数
    run_monthly(monthly_adjustment, monthday=1, time='9:30', reference_security='000300.XSHG')
    run_weekly(weekly_rebalance, weekday=1, time='10:00', reference_security='000300.XSHG')
    run_daily(daily_check, time='14:00', reference_security='000300.XSHG')

def monthly_adjustment(context):
    """月度调整"""
    # 获取当前数据
    current_data = get_current_data()
    for stock in context.hold_list:
        if current_data[stock].last_price > current_data[stock].high_limit:
            log.info(f'{stock} 涨停')

    # 使用MACD指标
    macd_value = MACD('000001.XSHE', check_date=context.previous_date)
    if macd_value > 0:
        order_target_value('000001.XSHE', 100000)

def weekly_rebalance(context):
    """周度调整 - 使用Ptrade原生run_weekly"""
    pass

def daily_check(context):
    """每日检查"""
    pass
'''

    converter = JQToPtradeUnifiedConverter(verbose=True)
    converted_code = converter.convert(sample_jq_code)

    # 保存
    with open('ptrade_strategy_v3_test.py', 'w', encoding='utf-8') as f:
        f.write(converted_code)

    print("[OK] 测试代码已保存到: ptrade_strategy_v3_test.py")
    print("\nv3.4改进内容:")
    print("  - 修复datetime模块导入缺失问题")
    print("  - 智能添加辅助函数(MACD/RSI只在需要时)")
    print("  - 精简注释，减少冗余说明")
    print("  - run_weekly/monthly转换为run_daily+日期检查")
    print("  - 基于实际Ptrade运行验证")
