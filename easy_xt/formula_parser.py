"""
TDX 公式解析器
=============

将通达信 (TDX) 公式文件 (.txt) 转换为可运行的 Python 代码，
对接 `easy_xt.indicators` 技术指标模块。

支持的语法:
  - 赋值:    MA5:=MA(C,5);
  - 输出:    OUTPUT:MA5;
  - 运算符:  + - * / > < = != >= <= && || NOT
  - 条件:    IF(COND, A, B)
  - 注释:    { 这是注释 }
  - 修饰符:  DRAWNULL, NODRAW, COLORxxxx, LINETHICKn

数据变量映射:
  C=close, O=open, H=high, L=low, V=volume, AMO=amount
  REFX 在计算时等同于 ref; 实际公式中 REFX 极少使用

使用方式:
    from easy_xt.formula_parser import TdxFormulaParser

    parser = TdxFormulaParser()

    # 方式1: 生成 Python 代码
    code = parser.parse_file('my_formula.txt')
    exec(code)

    # 方式2: 直接应用于 DataFrame
    result = parser.apply(df, 'my_formula.txt')
"""

import re
import ast as py_ast
from typing import Dict, List, Tuple, Optional, Callable, Any
import numpy as np
import pandas as pd


# ============================================================================
# 词法规则定义
# ============================================================================

# 数据变量映射: TDX 变量名 → Python 变量名
DATA_VAR_MAP: Dict[str, str] = {
    'C': 'close',
    'O': 'open',
    'H': 'high',
    'L': 'low',
    'V': 'volume',
    'VOL': 'volume',
    'VOLUME': 'volume',
    'AMO': 'amount',
    'AMOUNT': 'amount',
    'CLOSE': 'close',
    'OPEN': 'open',
    'HIGH': 'high',
    'LOW': 'low',
    'AMOUNT': 'amount',
    # 扩展的别名
    '收盘': 'close',
    '开盘': 'open',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',
    '成交额': 'amount',
}

# 函数名映射: TDX 函数名 → (Python 函数名, 是否在 indicators 模块中)
FUNCTION_MAP: Dict[str, Tuple[str, bool]] = {
    # 简单移动平均线
    'MA': ('ma', True),
    'EMA': ('ema', True),
    'SMA': ('sma', True),
    'WMA': ('wma', True),
    'DMA': ('dma', True),
    'EXPMA': ('expma', True),

    # 引用与变换
    'REF': ('ref', True),
    'REFX': ('ref', True),
    'DIFF': ('diff', True),
    'HHV': ('hhv', True),
    'LLV': ('llv', True),
    'STD': ('std', True),
    'SUM': ('rolling_sum', True),
    'AVEDEV': ('avedev', True),
    'SLOPE': ('slope', True),
    'FORCAST': ('forecast', True),

    # 交叉与条件
    'CROSS': ('cross', True),
    'LONGCROSS': ('_long_cross', False),
    'COUNT': ('count_true', True),
    'EVERY': ('every_true', True),
    'EXIST': ('exist_true', True),
    'BARSLAST': ('bars_last', True),
    'BARSLASTCOUNT': ('bars_last_count', True),
    'IF': ('np.where', False),
    'IFS': ('np.select', False),
    'VALUEWHEN': ('_value_when', False),

    # 摆动指标
    'CCI': ('cci', True),
    'KDJ': ('kdj', True),
    'MACD': ('macd', True),
    'RSI': ('rsi', True),
    'WR': ('wr', True),
    'MFI': ('mfi', True),
    'MTM': ('mtm', True),
    'ROC': ('roc', True),
    'TRIX': ('trix', True),
    'UOS': ('uos', True),

    # 趋势指标
    'BOLL': ('boll', True),
    'BBI': ('bbi', True),
    'DMI': ('dmi', True),
    'SAR': ('sar', True),
    'DKX': ('dkx', True),
    'ATR': ('atr', True),

    # 量价指标
    'OBV': ('obv', True),
    'VPT': ('vpt', True),
    'VR': ('vr', True),
    'PSY': ('psy', True),

    # 数学函数
    'ABS': ('np.abs', False),
    'MAX': ('np.maximum', False),
    'MIN': ('np.minimum', False),
    'ROUND': ('np.round', False),
    'CONST': ('_const', False),
    'SQRT': ('np.sqrt', False),
    'LOG': ('np.log', False),
    'EXP': ('np.exp', False),
    'POW': ('np.power', False),
    'MOD': ('np.mod', False),
    'INTPART': ('np.floor', False),
    'CEILING': ('np.ceil', False),
    'FLOOR': ('np.floor', False),
    'HHVBARS': ('_hhv_bars', False),
    'LLVBARS': ('_llv_bars', False),
    'FILTER': ('_filter', False),
    'BARSSINCEN': ('_bars_since_n', False),
}

# 装饰性/输出关键词，需从公式中移除
STRIP_KEYWORDS = [
    'DRAWNULL', 'NODRAW', 'NOTEXT',
    'COLORRED', 'COLORGREEN', 'COLORBLUE', 'COLORWHITE', 'COLORYELLOW',
    'COLORMAGENTA', 'COLORCYAN', 'COLORBLACK', 'COLORGRAY', 'COLORLIGHTRED',
    'COLORLIGHTGREEN', 'COLORLIGHTBLUE', 'COLORLIGHTGRAY',
    'LINETHICK1', 'LINETHICK2', 'LINETHICK3', 'LINETHICK4', 'LINETHICK5',
    'LINETHICK6', 'LINETHICK7', 'LINETHICK8', 'LINETHICK9',
    'LINEDASH', 'LINEDOT', 'LINEDASHDOT',
    'CIRCLEDOT', 'POINTDOT', 'STICK',
    'DOTLINE', 'DOTTED', 'CROSSDOT',
    'ALIGN', 'LAYER0', 'LAYER1', 'LAYER2', 'LAYER3', 'LAYER4',
    'NOFRAME', 'NODRAWLINE', 'NOAXIS',
    'COLORSTICK', 'VOLSTICK', 'LINESTICK',
    'DRAWTEXT', 'DRAWICON', 'DRAWLINE', 'DRAWBAND',
    'PLOYLINE', 'DRAWNUMBER', 'DRAWKLINE',
    'STICKLINE', 'FILLRGN',
]


# ============================================================================
# 辅助函数（公式引擎内部使用）
# ============================================================================

def _long_cross(s1: np.ndarray, s2: np.ndarray, n: int) -> np.ndarray:
    """两条线维持一定周期后交叉"""
    from easy_xt.indicators import every_true, cross_up
    condition = every_true(s1 < s2, n)
    return np.logical_and(condition, cross_up(s1, s2))


def _value_when(condition: np.ndarray, value: np.ndarray) -> np.ndarray:
    """当条件成立时取当前值，否则取上一次成立时的值"""
    result = np.where(condition, value, np.nan)
    mask = np.isnan(result)
    idx = np.where(~mask, np.arange(len(mask)), 0)
    np.maximum.accumulate(idx, out=idx)
    return result[idx]


def _const(series: np.ndarray) -> np.ndarray:
    """返回序列最后值组成的常量序列"""
    if len(series) == 0:
        return np.array([], dtype=float)
    return np.full(len(series), float(series[-1]))


def _hhv_bars(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期内最高值到当前的周期数"""
    return pd.Series(series).rolling(n, min_periods=1).apply(
        lambda x: np.argmax(x[::-1]), raw=True
    ).values


def _llv_bars(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期内最低值到当前的周期数"""
    return pd.Series(series).rolling(n, min_periods=1).apply(
        lambda x: np.argmin(x[::-1]), raw=True
    ).values


def _filter(condition: np.ndarray, n: int) -> np.ndarray:
    """条件满足后，其后 N 周期内的信号置为 False"""
    result = condition.copy()
    for i in range(len(result)):
        if result[i]:
            end = min(i + n + 1, len(result))
            result[i + 1:end] = False
    return result


def _bars_since_n(condition: np.ndarray, n: int) -> np.ndarray:
    """N 周期内第一次条件成立到现在的周期数"""
    return pd.Series(condition).rolling(n, min_periods=1).apply(
        lambda x: n - 1 - np.argmax(x) if np.argmax(x) or x.iloc[0] else 0,
        raw=False
    ).fillna(0).values.astype(int)


# ============================================================================
# 公式解析器
# ============================================================================

class TdxFormulaParser:
    """
    TDX 公式解析器。

    将通达信公式文件转换为 Python 代码，使用 `easy_xt.indicators` 模块执行。

    使用示例:
        parser = TdxFormulaParser()

        # 从文件解析
        code, outputs = parser.parse_file('my_indicator.txt')

        # 直接应用到数据
        df = parser.apply(df, 'my_indicator.txt')

        # 解析公式字符串
        code = parser.parse_text('MA5:=MA(C,5); OUTPUT:MA5;')
    """

    def __init__(self):
        self._input_vars = list(DATA_VAR_MAP.keys())
        # 构建正则：匹配独立的变量名（前后不能是字母）
        data_var_pattern = '|'.join(
            re.escape(v) for v in sorted(DATA_VAR_MAP.keys(), key=len, reverse=True)
        )
        self._data_var_re = re.compile(
            r'(?<![a-zA-Z_])(' + data_var_pattern + r')(?![a-zA-Z_0-9])'
        )

        # 函数名匹配正则
        func_pattern = '|'.join(
            re.escape(f) for f in sorted(FUNCTION_MAP.keys(), key=len, reverse=True)
        )
        self._func_re = re.compile(
            r'(?<![a-zA-Z_.])(' + func_pattern + r')\s*\('
        )

        # 装饰性关键词正则
        if STRIP_KEYWORDS:
            strip_pattern = '|'.join(
                re.escape(k) for k in sorted(STRIP_KEYWORDS, key=len, reverse=True)
            )
            self._strip_re = re.compile(r'\b(' + strip_pattern + r')\b', re.IGNORECASE)
        else:
            self._strip_re = None

    # ---- 核心解析方法 ----

    def parse_text(self, formula_text: str) -> Tuple[str, List[str]]:
        """
        解析公式文本，返回 Python 代码和输出变量列表。

        Args:
            formula_text: TDX 公式文本

        Returns:
            (python_code, output_names)
            - python_code: 可 exec 的 Python 字符串
            - output_names: 公式输出变量名列表
        """
        # Step 1: 移除注释 { ... }
        text = re.sub(r'\{[^}]*\}', '', formula_text)

        # Step 2: 提取输出变量名
        outputs = self._extract_outputs(text)

        # Step 3: 替换赋值操作符
        # : = → =  (先替换带空格的)
        text = text.replace(':=', '=')
        text = text.replace(':', '=')  # 输出标记也转为赋值

        # Step 4: 移除装饰性关键词
        if self._strip_re:
            text = self._strip_re.sub('', text)

        # Step 5: 替换逻辑运算符
        text = text.replace('&&', ' and ')
        text = text.replace('||', ' or ')
        # 处理关键字 AND/OR/NOT（仅当它们作为独立单词时）
        text = re.sub(r'\bAND\b', 'and', text)
        text = re.sub(r'\bOR\b', 'or', text)
        text = re.sub(r'\bNOT\b', 'not', text)
        text = re.sub(r'\bNOT\(\s*', 'not (', text, flags=re.IGNORECASE)

        # Step 6: 替换数据变量引用
        text = self._replace_data_vars(text)

        # Step 7: 替换函数名
        text = self._replace_functions(text)

        # Step 8: 处理逗号
        text = text.replace(',', ', ')

        # Step 9: 按分号拆分行
        lines = [l.strip() for l in text.split(';') if l.strip()]
        python_lines = []
        for line in lines:
            # 跳过空行
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            # 确保每行以换行结束
            if '=' in line:
                python_lines.append(line)

        # Step 10: 构建完整的 Python 代码
        code = self._build_code(python_lines, outputs)
        return code, outputs

    def parse_file(self, filepath: str) -> Tuple[str, List[str]]:
        """
        解析 .txt 格式的公式文件。

        Args:
            filepath: 公式文件路径

        Returns:
            (python_code, output_names)
        """
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        return self.parse_text(text)

    # ---- 应用到数据 ----

    def apply(self, df: pd.DataFrame, formula: str,
              is_file: bool = True) -> pd.DataFrame:
        """
        对 DataFrame 应用公式，返回添加了指标列的结果。

        Args:
            df: 包含 open/high/low/close/volume 列的 DataFrame
            formula: 公式文件路径或公式文本
            is_file: True 表示 formula 是文件路径

        Returns:
            添加了公式输出列的 DataFrame
        """
        if is_file:
            code, outputs = self.parse_file(formula)
        else:
            code, outputs = self.parse_text(formula)

        # 准备命名空间
        namespace = {
            'np': np,
            'pd': pd,
            'close': df.get('close', df.get('C', pd.Series(dtype=float))).values,
            'open': df.get('open', df.get('O', pd.Series(dtype=float))).values,
            'high': df.get('high', df.get('H', pd.Series(dtype=float))).values,
            'low': df.get('low', df.get('L', pd.Series(dtype=float))).values,
            'volume': df.get('volume', df.get('V', pd.Series(dtype=float))).values,
            'amount': df.get('amount', df.get('AMO', pd.Series(dtype=float))).values,
        }

        # 导入指标模块
        import easy_xt.indicators as _ind
        for name in dir(_ind):
            if not name.startswith('_') and callable(getattr(_ind, name)):
                namespace[name] = getattr(_ind, name)

        # 添加辅助函数
        namespace.update({
            '_long_cross': _long_cross,
            '_value_when': _value_when,
            '_const': _const,
            '_hhv_bars': _hhv_bars,
            '_llv_bars': _llv_bars,
            '_filter': _filter,
            '_bars_since_n': _bars_since_n,
        })

        # 执行代码
        result_df = df.copy()
        exec(code, namespace)

        # 将输出变量写回 DataFrame
        for name in outputs:
            if name in namespace:
                val = namespace[name]
                if isinstance(val, np.ndarray) and len(val) == len(result_df):
                    result_df[name] = val
                elif isinstance(val, (int, float, bool)):
                    result_df[name] = val

        return result_df

    def to_function(self, formula: str, is_file: bool = True
                    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        将公式转换为可调用的 Python 函数。

        Args:
            formula: 公式文件路径或文本
            is_file: True 表示文件路径

        Returns:
            function(df) -> df_with_indicators

        Example:
            my_macd = parser.to_function('macd_formula.txt')
            df = my_macd(df)  # 添加 MACD 相关列
        """
        def apply_func(df: pd.DataFrame) -> pd.DataFrame:
            return self.apply(df, formula, is_file=is_file)
        apply_func.__doc__ = f'Formula: {formula}'
        return apply_func

    # ---- 内部方法 ----

    def _extract_outputs(self, text: str) -> List[str]:
        """提取公式的输出变量名（用 : 标记的变量）"""
        outputs = []
        # 匹配输出定义 — 冒号后不能跟等号（排除赋值 :=）
        # 支持中英文变量名 (Unicode letters)
        for match in re.finditer(r'(?<![:\w一-鿿])([\w一-鿿]+)\s*:(?!\s*=)', text):
            name = match.group(1).strip()
            # 排除保留字和函数名
            upper = name.upper()
            if upper in FUNCTION_MAP or upper in DATA_VAR_MAP:
                continue
            if upper in ('COLOR', 'LINETHICK', 'STICK', 'LINE',
                         'DRAWNULL', 'NODRAW', 'NOTEXT', 'CROSSDOT',
                         'CIRCLEDOT', 'POINTDOT', 'DOTLINE'):
                continue
            if name not in outputs:
                outputs.append(name)
        return outputs

    def _replace_data_vars(self, text: str) -> str:
        """替换数据变量引用 C→close, H→high 等"""

        def _replacer(match):
            var = match.group(1)
            return DATA_VAR_MAP.get(var, var)

        return self._data_var_re.sub(_replacer, text)

    def _replace_functions(self, text: str) -> str:
        """替换 TDX 函数名为 Python 函数名"""

        def _replacer(match):
            func_name = match.group(1)
            py_name, in_indicators = FUNCTION_MAP.get(func_name, (func_name.lower(), False))
            return f'{py_name}('

        return self._func_re.sub(_replacer, text)

    def _build_code(self, lines: List[str], outputs: List[str]) -> str:
        """构建完整的 Python 可执行代码"""
        code_lines = [
            '# Auto-generated from TDX formula by EasyXT FormulaParser',
            '# Dependencies: easy_xt.indicators, numpy, pandas',
            '',
        ]

        for line in lines:
            code_lines.append(line)

        code_lines.append('')

        # 生成 return 或输出元组
        if outputs:
            # 过滤掉内部变量（以 _ 开头的不输出）
            public_outputs = [o for o in outputs if not o.startswith('_')]
            if public_outputs:
                return_str = ', '.join(public_outputs)
                if len(public_outputs) == 1:
                    code_lines.append(f'__formula_result__ = {return_str}')
                else:
                    code_lines.append(f'__formula_result__ = ({return_str})')

        return '\n'.join(code_lines)


# ============================================================================
# 便捷函数
# ============================================================================

def parse_formula(formula_text_or_path: str, is_file: bool = True
                  ) -> Tuple[str, List[str]]:
    """
    便捷函数：解析 TDX 公式并返回 Python 代码。

    Args:
        formula_text_or_path: 公式文本或文件路径
        is_file: True 表示是文件路径

    Returns:
        (python_code, output_names)
    """
    parser = TdxFormulaParser()
    if is_file:
        return parser.parse_file(formula_text_or_path)
    return parser.parse_text(formula_text_or_path)


def apply_formula(df: pd.DataFrame, formula_text_or_path: str,
                  is_file: bool = True) -> pd.DataFrame:
    """
    便捷函数：对 DataFrame 应用公式。

    Args:
        df: 包含 OHLCV 列的 DataFrame
        formula_text_or_path: 公式文本或文件路径
        is_file: True 表示是文件路径

    Returns:
        添加了公式输出的 DataFrame
    """
    parser = TdxFormulaParser()
    return parser.apply(df, formula_text_or_path, is_file)
