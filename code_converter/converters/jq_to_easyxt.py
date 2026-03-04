"""
聚宽转EasyXT智能转换器
将聚宽策略自动转换为可以在miniqmt上运行的EasyXT策略

核心功能：
1. 框架转换：initialize/handle_data → 独立脚本
2. API映射：聚宽API → EasyXT API
3. 数据结构转换：DataFrame格式适配
4. 交易函数转换：order_* → api.buy/sell
5. 定时任务转换：run_daily → 主循环

作者：量化之王
版本：v1.0.0
"""

import re
import ast
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime
from enum import Enum


class ConversionLogLevel(Enum):
    """转换日志级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class JQToEasyXTConverter:
    """
    聚宽到EasyXT转换器

    功能特点：
    1. 自动识别聚宽策略类型
    2. 智能转换API调用
    3. 重构策略框架
    4. 生成完整的EasyXT可运行代码
    5. 提供详细的转换报告
    """

    def __init__(self, verbose: bool = True, account_id: str = "YOUR_ACCOUNT_ID"):
        """
        初始化转换器

        Args:
            verbose: 是否输出详细日志
            account_id: 默认账户ID（可在转换后修改）
        """
        self.verbose = verbose
        self.account_id = account_id

        # 转换报告
        self.conversion_report = {
            'infos': [],
            'warnings': [],
            'errors': [],
            'successes': [],
            'api_mappings': [],
            'manual_fixes': []
        }

        # 聚宽 → EasyXT API映射
        self.api_mapping = {
            # 数据获取API
            'get_price': 'api.get_price',
            'get_history': 'api.get_price',
            'attribute_history': 'api.get_price',
            'get_bars': 'api.get_price',
            'get_current_data': 'api.get_current_price',
            'get_snapshot': 'api.get_current_price',

            # 股票列表API
            'get_all_securities': 'api.get_stock_list',
            'get_index_stocks': 'api.get_stock_list',  # 需要参数调整
            'get_industry_stocks': None,  # 需要手动处理

            # 交易日历API
            'get_trade_days': 'api.get_trading_dates',
            'get_trading_dates': 'api.get_trading_dates',

            # 基本面数据API（需要额外处理）
            'get_fundamentals': None,  # 需要手动处理

            # 交易API（需要复杂转换）
            'order': None,  # 需要根据参数转换为buy/sell
            'order_value': None,
            'order_target': None,
            'order_target_value': None,
            'cancel_order': None,  # EasyXT暂不支持

            # 系统API
            'log.info': 'print',
            'log.warn': 'print',
            'log.error': 'print',
            'log.debug': 'print',
            'set_benchmark': None,  # EasyXT不需要，记录即可
        }

        # 定时任务映射
        self.timing_mapping = {
            'run_daily': 'handle_bar',
            'run_weekly': 'handle_bar_weekly',
            'run_monthly': 'handle_bar_monthly',
            'run_minute': 'handle_tick',
        }

    def convert(self, jq_code: str, output_file: Optional[str] = None) -> str:
        """
        转换聚宽代码为EasyXT代码

        Args:
            jq_code: 聚宽策略代码
            output_file: 输出文件路径（可选）

        Returns:
            str: 转换后的EasyXT代码
        """
        # 重置转换报告
        self._reset_report()

        if self.verbose:
            print("=" * 80)
            print("聚宽转EasyXT智能转换器")
            print("=" * 80)
            print(f"转换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)

        # 1. 分析聚宽代码
        code_analysis = self._analyze_jq_code(jq_code)

        # 2. 提取关键信息
        initialize_code = self._extract_initialize(jq_code)
        handle_data_code = self._extract_handle_data(jq_code)
        scheduled_functions = self._extract_scheduled_functions(jq_code)

        if self.verbose:
            print(f"\n✅ 代码分析完成")
            print(f"   - initialize函数: {'已找到' if initialize_code else '未找到'}")
            print(f"   - handle_data函数: {'已找到' if handle_data_code else '未找到'}")
            print(f"   - 定时任务函数: {len(scheduled_functions)}个")

        # 3. 转换代码
        converted_code = self._convert_code(
            jq_code,
            initialize_code,
            handle_data_code,
            scheduled_functions,
            code_analysis
        )

        # 4. 生成完整脚本
        final_code = self._generate_complete_script(converted_code, code_analysis)

        # 5. 保存文件（如果指定）
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_code)
            self._log_success(f"转换后的代码已保存到: {output_file}")

        # 6. 打印转换报告
        if self.verbose:
            self._print_conversion_report()

        return final_code

    def _reset_report(self):
        """重置转换报告"""
        self.conversion_report = {
            'infos': [],
            'warnings': [],
            'errors': [],
            'successes': [],
            'api_mappings': [],
            'manual_fixes': []
        }

    def _analyze_jq_code(self, code: str) -> Dict:
        """
        分析聚宽代码

        Returns:
            Dict: 代码分析结果
        """
        analysis = {
            'has_initialize': bool(re.search(r'def\s+initialize\s*\(', code)),
            'has_handle_data': bool(re.search(r'def\s+handle_data\s*\(', code)),
            'uses_context': 'context.' in code,
            'uses_data': 'data.' in code,
            'uses_global_g': 'g.' in code,
            'scheduled_functions': [],
            'used_apis': set(),
            'has_trading': False,
            'has_fundamentals': False,
            'has_indicators': False,
        }

        # 检测定时任务
        timing_patterns = {
            'run_daily': r'run_daily\s*\(\s*([^,]+)',
            'run_weekly': r'run_weekly\s*\(\s*([^,]+)',
            'run_monthly': r'run_monthly\s*\(\s*([^,]+)',
            'run_minute': r'run_minute\s*\(\s*([^,]+)',
        }

        for timing_name, pattern in timing_patterns.items():
            matches = re.findall(pattern, code)
            for func_name in matches:
                analysis['scheduled_functions'].append({
                    'type': timing_name,
                    'name': func_name.strip()
                })

        # 检测API使用
        api_patterns = [
            r'\border\s*\(',
            r'\border_value\s*\(',
            r'\border_target\s*\(',
            r'\border_target_value\s*\(',
        ]
        for pattern in api_patterns:
            if re.search(pattern, code):
                analysis['has_trading'] = True
                break

        # 检测基本面数据
        if 'get_fundamentals' in code or 'query(' in code:
            analysis['has_fundamentals'] = True

        # 检测技术指标
        if re.search(r'MACD|RSI|BOLL|KDJ|MACD\s*\(', code):
            analysis['has_indicators'] = True

        return analysis

    def _extract_initialize(self, code: str) -> Optional[str]:
        """提取initialize函数代码"""
        pattern = r'def\s+initialize\s*\([^)]*\)\s*:\s*\n((?:\s+.*\n)+)'
        match = re.search(pattern, code)
        if match:
            return match.group(1)
        return None

    def _extract_handle_data(self, code: str) -> Optional[str]:
        """提取handle_data函数代码"""
        pattern = r'def\s+handle_data\s*\([^)]*\)\s*:\s*\n((?:\s+.*\n)+?)(?=\ndef\s|\Z)'
        match = re.search(pattern, code, re.MULTILINE)
        if match:
            return match.group(1)
        return None

    def _extract_scheduled_functions(self, code: str) -> List[Dict]:
        """提取定时任务函数"""
        functions = []

        # 提取所有函数定义
        function_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*:\s*\n((?:\s+.*\n)+?)(?=\ndef\s|\Z)'
        matches = re.finditer(function_pattern, code, re.MULTILINE)

        for match in matches:
            func_name = match.group(1)
            func_body = match.group(2)

            # 跳过initialize和handle_data
            if func_name in ['initialize', 'handle_data']:
                continue

            functions.append({
                'name': func_name,
                'body': func_body
            })

        return functions

    def _convert_code(self, original_code: str, initialize_code: Optional[str],
                     handle_data_code: Optional[str], scheduled_functions: List[Dict],
                     analysis: Dict) -> Dict:
        """
        执行代码转换

        Returns:
            Dict: 包含转换后各部分的字典
        """
        result = {
            'imports': [],
            'global_vars': [],
            'initialize_logic': '',
            'main_loop_logic': '',
            'helper_functions': []
        }

        # 1. 转换导入语句
        result['imports'] = self._convert_imports(original_code)

        # 2. 转换全局变量
        if initialize_code:
            result['global_vars'], result['initialize_logic'] = self._convert_initialize(initialize_code)

        # 3. 转换主逻辑
        if handle_data_code:
            result['main_loop_logic'] = self._convert_handle_data(handle_data_code)

        # 4. 转换定时任务函数
        for func in scheduled_functions:
            converted_func = self._convert_scheduled_function(func)
            result['helper_functions'].append(converted_func)

        return result

    def _convert_imports(self, code: str) -> List[str]:
        """转换导入语句"""
        imports = []

        # 添加标准导入
        imports.append("import sys")
        imports.append("import os")
        imports.append("from datetime import datetime, timedelta")
        imports.append("import pandas as pd")
        imports.append("import time")

        # 添加项目路径
        imports.append("")
        imports.append("# 添加项目根目录到Python路径")
        imports.append("current_dir = os.path.dirname(os.path.abspath(__file__))")
        imports.append("project_root = os.path.dirname(current_dir)")
        imports.append("sys.path.insert(0, project_root)")
        imports.append("")
        imports.append("# 导入EasyXT")
        imports.append("import easy_xt")

        # 保留原代码中的必要导入
        original_imports = re.findall(r'^(import\s+.*|from\s+.*import\s+.*)$', code, re.MULTILINE)
        for imp in original_imports:
            # 跳过聚宽特定的导入
            if 'jqdata' not in imp and 'jqfactor' not in imp:
                if imp not in imports:
                    imports.append(f"# {imp}  # 保留原导入")

        return imports

    def _convert_initialize(self, initialize_code: str) -> Tuple[List[str], str]:
        """
        转换initialize函数

        Returns:
            Tuple[List[str], str]: (全局变量定义, 初始化逻辑)
        """
        global_vars = []
        init_logic = []

        # 提取g.开头的全局变量
        g_assignments = re.findall(r'(g\.\w+)\s*=\s*(.+)', initialize_code)

        for var_name, var_value in g_assignments:
            # g.xxx → xxx
            new_var_name = var_name.replace('g.', '')
            global_vars.append(f"{new_var_name} = {var_value}")
            self._log_api_mapping(f"g.{new_var_name} → 全局变量")

        # 转换其他初始化逻辑
        lines = initialize_code.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 跳过g.变量赋值（已处理）
            if re.match(r'g\.\w+\s*=', line):
                continue

            # 转换set_benchmark
            if 'set_benchmark' in line:
                init_logic.append(f"# {line}  # EasyXT不需要设置基准")
                self._log_info("set_benchmark已注释（EasyXT不需要）")
                continue

            # 保留其他逻辑
            converted_line = self._convert_line(line)
            if converted_line:
                init_logic.append(converted_line)

        return global_vars, '\n        '.join(init_logic)

    def _convert_handle_data(self, handle_data_code: str) -> str:
        """转换handle_data函数为主循环逻辑"""
        lines = handle_data_code.split('\n')
        converted_lines = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                if line:
                    converted_lines.append(line)
                continue

            converted_line = self._convert_line(line)
            if converted_line:
                converted_lines.append(converted_line)

        return '\n        '.join(converted_lines)

    def _convert_scheduled_function(self, func: Dict) -> Dict:
        """转换定时任务函数"""
        func_name = func['name']
        func_body = func['body']

        converted_body = []
        lines = func_body.split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                if line:
                    converted_body.append(line)
                continue

            converted_line = self._convert_line(line)
            if converted_line:
                converted_body.append(converted_line)

        return {
            'name': func_name,
            'body': '\n    '.join(converted_body)
        }

    def _convert_line(self, line: str) -> Optional[str]:
        """
        转换单行代码

        Args:
            line: 原始代码行

        Returns:
            Optional[str]: 转换后的代码行，如果需要移除则返回None
        """
        # 转换g.变量为全局变量
        if 'g.' in line:
            line = re.sub(r'\bg\.(\w+)', r'\1', line)

        # 转换context对象访问
        if 'context.' in line:
            line = self._convert_context_access(line)

        # 转换API调用
        for jq_api, easyxt_api in self.api_mapping.items():
            if easyxt_api and f'{jq_api}(' in line:
                line = line.replace(f'{jq_api}(', f'{easyxt_api}(')
                self._log_api_mapping(f"{jq_api}() → {easyxt_api}()")

        # 转换交易API
        if any(api in line for api in ['order(', 'order_value(', 'order_target(', 'order_target_value(']):
            line = self._convert_trading_api(line)

        # 转换log.info
        if 'log.info(' in line or 'log.warn(' in line or 'log.error(' in line:
            line = re.sub(r'log\.(info|warn|error|debug)\(', 'print(', line)

        # 转换get_current_data
        if 'get_current_data()' in line:
            self._log_warning("get_current_data()需要手动转换为api.get_current_price()")
            line = line.replace('get_current_data()', 'api.get_current_price()')

        return line

    def _convert_context_access(self, line: str) -> str:
        """
        转换context对象访问

        context.portfolio.available_cash → 可用现金变量
        context.current_date → datetime.now()
        context.previous_date → datetime.now() - timedelta(days=1)
        """
        # context.portfolio.available_cash
        if 'context.portfolio.available_cash' in line:
            self._log_warning("context.portfolio.available_cash需要手动实现账户管理")
            line = line.replace('context.portfolio.available_cash', 'account_cash')

        # context.current_date
        if 'context.current_date' in line:
            line = line.replace('context.current_date', 'datetime.now().date()')

        # context.previous_date
        if 'context.previous_date' in line:
            line = line.replace('context.previous_date', '(datetime.now() - timedelta(days=1)).date()')

        # context.portfolio.positions
        if 'context.portfolio.positions' in line:
            self._log_warning("context.portfolio.positions需要手动实现持仓管理")
            line = line.replace('context.portfolio.positions', 'positions')

        return line

    def _convert_trading_api(self, line: str) -> str:
        """
        转换交易API

        order_target(security, 0) → api.sell(account_id, security, volume)
        order_target_value(security, value) → api.buy(account_id, security, volume)
        """
        # order_target(security, 0) - 卖出
        if 'order_target(' in line and ', 0)' in line:
            match = re.search(r'order_target\s*\(\s*([^,]+),\s*0\s*', line)
            if match:
                security = match.group(1).strip()
                self._log_manual_fix(f"order_target({security}, 0)需要手动转换为api.sell()")
                return f"# TODO: 转换卖出逻辑\n        # api.sell(account_id, {security}, volume=可卖数量)"

        # order_target_value - 按金额买入
        if 'order_target_value(' in line:
            self._log_manual_fix("order_target_value需要手动转换为api.buy()")
            return f"# TODO: 转换按金额买入逻辑\n        # 原代码: {line}"

        # order_value - 按金额买入
        if 'order_value(' in line:
            self._log_manual_fix("order_value需要手动转换为api.buy()")
            return f"# TODO: 转换按金额买入逻辑\n        # 原代码: {line}"

        # order_target - 调整持仓
        if 'order_target(' in line:
            self._log_manual_fix("order_target需要手动转换为api.buy/sell")
            return f"# TODO: 转换调仓逻辑\n        # 原代码: {line}"

        return line

    def _generate_complete_script(self, converted_code: Dict, analysis: Dict) -> str:
        """生成完整的EasyXT脚本"""

        # 使用字符串拼接避免f-string中的转义字符问题
        script_parts = []

        # 文件头
        script_parts.append('"""')
        script_parts.append('聚宽策略转EasyXT - 自动生成的策略脚本')
        script_parts.append(f'转换时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        script_parts.append('')
        script_parts.append('⚠️  重要提示：')
        script_parts.append('1. 请根据实际需求修改账户ID')
        script_parts.append('2. 请手动完善标记为TODO的交易逻辑')
        script_parts.append('3. 请检查并测试数据获取是否正常')
        script_parts.append('4. 建议先在模拟环境验证策略')
        script_parts.append('"""')
        script_parts.append('')

        # 导入模块
        script_parts.append('# ========== 导入模块 ==========')
        script_parts.extend(converted_code['imports'])
        script_parts.append('')

        # 全局配置
        script_parts.append('# ========== 全局配置 ==========')
        script_parts.append(f'ACCOUNT_ID = "{self.account_id}"  # TODO: 修改为实际账户ID')
        script_parts.append('USERDATA_PATH = "D:\\\\你的QMT路径\\\\userdata_mini"  # TODO: 修改为实际路径')
        script_parts.append('')

        # 全局变量
        script_parts.append('# ========== 全局变量 ==========')
        if converted_code['global_vars']:
            script_parts.extend(converted_code['global_vars'])
        else:
            script_parts.append('# 无全局变量')
        script_parts.append('')

        # 初始化函数
        script_parts.append('# ========== 初始化函数 ==========')
        script_parts.append('def initialize():')
        script_parts.append('    """初始化策略"""')
        script_parts.append('    print("=" * 60)')
        script_parts.append('    print("策略初始化开始")')
        script_parts.append('    print("=" * 60)')
        script_parts.append('')
        script_parts.append('    # 创建API实例')
        script_parts.append('    api = easy_xt.get_api()')
        script_parts.append('')
        script_parts.append('    # 初始化数据服务')
        script_parts.append('    print("正在初始化数据服务...")')
        script_parts.append('    success = api.init_data()')
        script_parts.append('    if success:')
        script_parts.append('        print("✓ 数据服务初始化成功")')
        script_parts.append('    else:')
        script_parts.append('        print("✗ 数据服务初始化失败")')
        script_parts.append('        return None')
        script_parts.append('')

        # 交易服务初始化
        if analysis['has_trading']:
            script_parts.append('    # 初始化交易服务')
            script_parts.append('    print("正在初始化交易服务...")')
            script_parts.append('    success = api.init_trade(USERDATA_PATH)')
            script_parts.append('    if success:')
            script_parts.append('        print("✓ 交易服务初始化成功")')
            script_parts.append('    else:')
            script_parts.append('        print("✗ 交易服务初始化失败")')
            script_parts.append('        return None')
            script_parts.append('')
            script_parts.append('    # 添加交易账户')
            script_parts.append('    api.add_account(ACCOUNT_ID)')
            script_parts.append('')

        # 执行初始化逻辑
        script_parts.append('    # 执行初始化逻辑')
        if converted_code['initialize_logic']:
            script_parts.append(converted_code['initialize_logic'])
        else:
            script_parts.append('    pass  # 无初始化逻辑')
        script_parts.append('')
        script_parts.append('    print("=" * 60)')
        script_parts.append('    print("策略初始化完成")')
        script_parts.append('    print("=" * 60)')
        script_parts.append('')
        script_parts.append('    return api')
        script_parts.append('')

        # 主策略逻辑
        script_parts.append('# ========== 主策略逻辑 ==========')
        script_parts.append('def run_strategy(api):')
        script_parts.append('    """')
        script_parts.append('    主策略循环')
        script_parts.append('')
        script_parts.append('    注意：这是简化的单次执行版本')
        script_parts.append('    如果需要定时运行，请使用定时器或外部调度')
        script_parts.append('    """')
        script_parts.append('    print("\\n" + "=" * 60)')
        script_parts.append('    print("开始执行策略")')
        script_parts.append('    print("=" * 60)')
        script_parts.append('')
        script_parts.append('    try:')
        if converted_code['main_loop_logic']:
            script_parts.append(converted_code['main_loop_logic'])
        else:
            script_parts.append('        pass  # 无主策略逻辑')
        script_parts.append('    except Exception as e:')
        script_parts.append('        print("策略执行出错: " + str(e))')
        script_parts.append('')
        script_parts.append('    print("=" * 60)')
        script_parts.append('    print("策略执行完成")')
        script_parts.append('    print("=" * 60)')
        script_parts.append('')

        # 辅助函数
        script_parts.append('# ========== 辅助函数 ==========')
        helper_funcs = self._generate_helper_functions(converted_code['helper_functions'])
        script_parts.append(helper_funcs)
        script_parts.append('')

        # 主程序入口
        script_parts.append('# ========== 主程序入口 ==========')
        script_parts.append('if __name__ == "__main__":')
        script_parts.append('    try:')
        script_parts.append('        # 1. 初始化')
        script_parts.append('        api = initialize()')
        script_parts.append('        if api is None:')
        script_parts.append('            print("\\n✗ 初始化失败，程序退出")')
        script_parts.append('            sys.exit(1)')
        script_parts.append('')
        script_parts.append('        # 2. 运行策略')
        script_parts.append('        run_strategy(api)')
        script_parts.append('')
        script_parts.append('        # 3. 如果需要持续运行，可以使用循环')
        script_parts.append('        # while True:')
        script_parts.append('        #     run_strategy(api)')
        script_parts.append('        #     time.sleep(60)  # 每分钟执行一次')
        script_parts.append('')
        script_parts.append('    except KeyboardInterrupt:')
        script_parts.append('        print("\\n\\n用户中断，程序退出")')
        script_parts.append('    except Exception as e:')
        script_parts.append('        print("\\n✗ 程序异常: " + str(e))')
        script_parts.append('        import traceback')
        script_parts.append('        traceback.print_exc()')

        return '\n'.join(script_parts)

    def _generate_helper_functions(self, helper_functions: List[Dict]) -> str:
        """生成辅助函数代码"""
        if not helper_functions:
            return '# 无辅助函数'

        code_blocks = []
        for func in helper_functions:
            func_name = func['name']
            func_body = func['body']

            code_blocks.append(f"def {func_name}(api):")
            code_blocks.append(f"    {func_body}")
            code_blocks.append("")

        return '\n'.join(code_blocks)

    def _log_info(self, message: str):
        """记录信息日志"""
        self.conversion_report['infos'].append(message)
        if self.verbose:
            print(f"  [INFO] {message}")

    def _log_warning(self, message: str):
        """记录警告日志"""
        self.conversion_report['warnings'].append(message)
        if self.verbose:
            print(f"  [⚠️] {message}")

    def _log_error(self, message: str):
        """记录错误日志"""
        self.conversion_report['errors'].append(message)
        if self.verbose:
            print(f"  [❌] {message}")

    def _log_success(self, message: str):
        """记录成功日志"""
        self.conversion_report['successes'].append(message)
        if self.verbose:
            print(f"  [✅] {message}")

    def _log_api_mapping(self, message: str):
        """记录API映射"""
        self.conversion_report['api_mappings'].append(message)

    def _log_manual_fix(self, message: str):
        """记录需要手动修复的项目"""
        self.conversion_report['manual_fixes'].append(message)
        if self.verbose:
            print(f"  [🔧] {message}")

    def _print_conversion_report(self):
        """打印转换报告"""
        print("\n" + "=" * 80)
        print("📊 转换报告")
        print("=" * 80)

        if self.conversion_report['api_mappings']:
            print("\n✅ API映射:")
            for mapping in self.conversion_report['api_mappings'][:20]:  # 限制显示数量
                print(f"   - {mapping}")
            if len(self.conversion_report['api_mappings']) > 20:
                print(f"   ... 还有 {len(self.conversion_report['api_mappings']) - 20} 个映射")

        if self.conversion_report['warnings']:
            print("\n⚠️  警告:")
            for warning in self.conversion_report['warnings'][:10]:
                print(f"   - {warning}")
            if len(self.conversion_report['warnings']) > 10:
                print(f"   ... 还有 {len(self.conversion_report['warnings']) - 10} 个警告")

        if self.conversion_report['manual_fixes']:
            print("\n🔧 需要手动修复:")
            for fix in self.conversion_report['manual_fixes'][:10]:
                print(f"   - {fix}")
            if len(self.conversion_report['manual_fixes']) > 10:
                print(f"   ... 还有 {len(self.conversion_report['manual_fixes']) - 10} 个需要修复")

        if self.conversion_report['errors']:
            print("\n❌ 错误:")
            for error in self.conversion_report['errors']:
                print(f"   - {error}")

        print("\n" + "=" * 80)
        print("✅ 转换完成！")
        print("=" * 80)
        print("\n📋 后续步骤：")
        print("1. 检查生成的代码，特别是标记为TODO的部分")
        print("2. 修改账户ID和路径配置")
        print("3. 手动完善交易逻辑（buy/sell）")
        print("4. 在模拟环境测试策略")
        print("5. 验证通过后才能用于实盘")
        print("=" * 80 + "\n")

    def get_conversion_report(self) -> Dict:
        """获取转换报告"""
        return self.conversion_report


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 示例聚宽代码
    sample_jq_code = """
import jqdata

def initialize(context):
    # 设置股票池
    g.stock = '000001.XSHE'
    g.buy_threshold = 1.05
    g.sell_threshold = 0.95

    # 设置基准
    set_benchmark('000300.XSHG')

    # 设置定时任务
    run_daily(check_strategy, time='9:30')

def check_strategy(context):
    # 获取历史数据
    hist_data = attribute_history(g.stock, 5, unit='1d',
                                  fields=['close'], df=True)

    # 计算均线
    ma5 = hist_data['close'].mean()

    # 获取当前价格
    current_data = get_current_data()
    current_price = current_data[g.stock].last_price

    # 获取可用资金
    cash = context.portfolio.available_cash

    # 买入逻辑
    if current_price > ma5 * g.buy_threshold and cash > 0:
        order_value(g.stock, cash)
        log.info(f"买入 {g.stock}")

    # 卖出逻辑
    elif current_price < ma5 * g.sell_threshold:
        order_target(g.stock, 0)
        log.info(f"卖出 {g.stock}")

def handle_data(context, data):
    pass
"""

    # 创建转换器
    converter = JQToEasyXTConverter(verbose=True)

    # 转换代码
    converted_code = converter.convert(
        sample_jq_code,
        output_file='easyxt_strategy_converted.py'
    )

    print("\n✅ 转换完成！生成的文件：easyxt_strategy_converted.py")
