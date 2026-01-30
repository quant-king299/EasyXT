import json
import ctypes
import numpy as np
import pandas as pd
import weakref
import sys
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Union
from collections import defaultdict
from datetime import datetime, timedelta
import re
import atexit
import inspect

from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 优先从通达信安装目录加载DLL
_tdx_install_paths = [
    Path(r"D:/new_tdx64.2/PYPlugins/TPythClient.dll"),  # 用户当前使用的通达信
    Path(r"D:/new_tdx64/PYPlugins/TPythClient.dll"),        # 备选路径
    Path(__file__).resolve().parents[1] / 'TPythClient.dll',  # 项目本地（原逻辑）
]

global_dll_path = None
for dll_path in _tdx_install_paths:
    if dll_path.exists():
        global_dll_path = dll_path
        break

if global_dll_path:
    dll = ctypes.CDLL(str(global_dll_path))

# 设置DLL函数的返回类型
dll.InitConnect.restype = ctypes.c_char_p       # 初始化 获取id
dll.GetStockListInStr.restype = ctypes.c_char_p  # 获取股票列表
dll.GetHISDATsInStr.restype = ctypes.c_char_p   # K线数据
dll.GetCWDATAInStr.restype = ctypes.c_char_p    # 复权数据
dll.Register_DataTransferFunc.restype=None      # 注册外套回调函数
dll.SubscribeGPData.restype=ctypes.c_char_p     # 订阅单股数据
dll.SubscribeHQDUpdate.restype=ctypes.c_char_p     # 订阅单股行情更新
dll.SetNewOrder.restype=ctypes.c_char_p         # 下单接口 
dll.GetSTOCKInStr.restype=ctypes.c_char_p       # 获取股票详细信息
dll.GetREPORTInStr.restype=ctypes.c_char_p      # 获取行情数据
dll.SetResToMain.restype=ctypes.c_char_p        # 获取行情数据
dll.GetBlockListInStr.restype=ctypes.c_char_p           # 获取板块列表
dll.GetBlockStocksInStr.restype=ctypes.c_char_p         # 获取板块成分股
dll.GetTradeCalendarInStr.restype=ctypes.c_char_p    # 获取交易日历数据
dll.ReFreshCacheAll.restype=ctypes.c_char_p    # 刷新缓存行情
dll.ReFreshCacheKLine.restype=ctypes.c_char_p    # 刷新缓存数据
dll.DownLoadFiles.restype=ctypes.c_char_p    # 下载文件
dll.UserBlockControl.restype=ctypes.c_char_p    # 自定义板块操作
dll.GetProDataInStr.restype=ctypes.c_char_p         # 获取专业数据
dll.GetCBINFOInStr.restype=ctypes.c_char_p         # 可转债基础信息
dll.GetIPOINFOInStr.restype=ctypes.c_char_p         # 新股申购信息
dll.GetUserBlockInStr.restype=ctypes.c_char_p         # 获取自定义板块

def _convert_time_format(start_time):
    """
    将起始时间转换为标准格式

    Args:
        start_time (str): 起始时间，格式为 YYYYMMDD 或 YYYYMMDDHHMMSS

    Returns:
        str: 格式化后的时间，格式为 YYYY-MM-DD HH:MM:SS

    Raises:
        ValueError: 当输入格式不正确时
    """
    if not start_time:
        return ''
    # 根据输入长度判断时间格式
    if len(start_time) == 8:  # YYYYMMDD
        dt = datetime.strptime(start_time, '%Y%m%d')
    elif len(start_time) == 14:  # YYYYMMDDHHMMSS
        dt = datetime.strptime(start_time, '%Y%m%d%H%M%S')
    else:
        tq.close()
        raise ValueError("时间格式不正确，应为 YYYYMMDD 或 YYYYMMDDHHMMSS")

    # 转换为目标格式
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def convert_or_validate(data):
    """
    如果输入是list，则根据后缀(SZ=0, SH=1, BJ=2)转换为“0#600000|1#600001|2#600002”格式的字符串
    如果输入是字符串，则验证是否符合指定格式
    
    Args:
        data: list或str类型的数据
        
    Returns:
        str: 转换后的字符串或验证结果
    """
    # 定义后缀到编号的映射
    suffix_map = {
        'SZ': '0',
        'SH': '1', 
        'BJ': '2',
        '0': '0',
        '1': '1',
        '2': '2'
    }
    
    if isinstance(data, list):
        # 处理列表转换
        result = []
        for item in data:
            # 分割代码和后缀
            if '.' not in item:
                print(f"无效的格式: {item}，需要包含后缀(.SZ/.SH/.BJ)")
                return ""
            
            code, suffix = item.split('.', 1)
            
            if suffix not in suffix_map:
                print(f"不支持的后缀: {suffix}, 只支持SZ/SH/BJ")
                return ""
            
            # 根据后缀获取对应的编号
            num = suffix_map[suffix]
            result.append(f"{num}#{code}")
        
        return "|".join(result)
    
    elif isinstance(data, str):
        # 验证字符串格式
        parts = data.split("|")
        
        # 检查是否包含所有必要的部分
        if len(parts) < 1:
            return ""
        
        # 检查每个部分的格式
        for part in parts:
            if '#' not in part:
                return ""
            
            num, code = part.split('#', 1)
            
            # 检查编号是否有效
            if num not in ['0', '1', '2']:
                return ""
            
            # 检查代码是否为6位数字
            if not code.isdigit() or len(code) != 6:
                return ""
        
        return data
    
    else:
        # 不支持的类型
        print("输入必须是list或str类型")
        return ""
    
def get_python_version_number() -> int:
    """
    获取当前Python版本号，提取主、次版本拼接为数字（如3.13.7返回313）
    
    Returns:
        int: 主+次版本拼接的数字
    """
    version_info = sys.version_info
    major = version_info.major  # 主版本（如3）
    minor = version_info.minor  # 次版本（如13）
    version_num = major * 100 + minor  # 拼接为数字（3*100+13=313）
    
    return version_num

def get_warn_struct_str(stock_list:        List[str] = [],
                  time_list:         List[str] = [],
                  price_list:        List[str] = [],
                  close_list:        List[str] = [],
                  volum_list:        List[str] = [],
                  bs_flag_list:      List[str] = [],
                  warn_type_list:    List[str] = [],
                  reason_list:       List[str] = [],
                  count:        int  = 1) -> str:
    """
    获取预警结构字符串
    """
    # 1. 校验stock_list格式
    stock_pattern = re.compile(r'^\d{6}\.[A-Z]+$')
    for stock in stock_list:
        if not stock_pattern.match(stock):
            tq.close()
            raise ValueError(f"股票代码格式错误: {stock}（需6位数字+市场后缀，如688318.SH）")

    # 2. 校验必须满足count长度的列表
    required_lists = {
        "stock_list": stock_list,
        "price_list": price_list,
        "close_list": close_list,
        "volum_list": volum_list
    }
    for name, lst in required_lists.items():
        if len(lst) < count:
            tq.close()
            raise ValueError(f"{name}元素数量不足（当前{len(lst)}，需要{count}）")
        
    time_list = [_convert_time_format(time_str) for time_str in time_list]
    # 3. 补全其他列表
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 补全warn_time（缺则补当前时间）
    filled_warn_time = time_list[:count] + [current_time] * max(0, count - len(time_list))
    # 补全bs_flag（缺则补2）
    filled_bs_flag = bs_flag_list[:count] + ["2"] * max(0, count - len(bs_flag_list))
    # 补全warn_type（缺则补-1）
    filled_warn_type = warn_type_list[:count] + ["-1"] * max(0, count - len(warn_type_list))
    # 补全reason（缺则补空字符串）
    filled_reason = reason_list[:count] + [""] * max(0, count - len(reason_list))

    # 4. 截取每个列表的前count个元素
    parts = [
        ",".join(stock_list[:count]),
        ",".join(filled_warn_time),
        ",".join(price_list[:count]),
        ",".join(close_list[:count]),
        ",".join(volum_list[:count]),
        ",".join(filled_bs_flag),
        ",".join(filled_warn_type),
        ",".join(filled_reason)
    ]

    # 5. 拼接结果（不同元素用||分隔）
    return "|".join(parts)
        
def get_bt_struct_str(time_list:         List[str] = [],
                      data_list:       List[List[str]] = [],
                      count:        int  = 1) -> str:
    """
    获取回测结构字符串
    """
    # 1. 校验time_list长度
    if len(time_list) < count:
        raise ValueError(f"time_list长度不足（当前{len(time_list)}，需至少{count}）")

    time_list = [_convert_time_format(time_str) for time_str in time_list]
    # 2. 处理data_list：补全、截取、格式校验
    filled_data = data_list[:count] + ['0'] * max(0, count - len(data_list))  # 不足补0
    num_pattern = re.compile(r'^-?[0-9.]+$')  # 匹配纯数字（含整数/浮点数）
    processed_data = []
    
    for item in filled_data:
        truncated = item[:16]  # 取前16位
        for item2 in truncated:
            if not num_pattern.match(item2):
                raise ValueError(f"data_list元素非法：{truncated}（需为纯数字字符串）")
        processed_data.append(",".join(truncated))  # 重新拼接（保证格式统一）

    # 3. 按新格式拼接最终字符串
    time_part = ",".join(time_list[:count])  # time_list元素用","拼接
    data_part = ",,".join(processed_data)   # data_list元素整体用",,"拼接
    final_str = f"{time_part}|{data_part}"  # 最终time和data用||分隔

    return final_str

def check_stock_code_format(input_data):
    """
    校验输入的字符串/字符串列表是否符合「6位数字+市场后缀」的标准格式
    :param input_data: str | list[str]，待校验的单个股票代码或代码列表
    """
    if not input_data:
        print("入参不能为空")
        return False

    # 正则表达式：6位数字 + . + 2-3位大写字母（匹配.SH/.SZ/.JJ等）
    pattern = re.compile(r'^\d{6}\.[A-Z]{2,3}$')
    
    # 统一转为列表处理（兼容单个字符串/列表入参）
    if isinstance(input_data, str):
        check_list = [input_data]
    elif isinstance(input_data, list):
        # 过滤非字符串元素（避免类型错误）
        check_list = [item for item in input_data if isinstance(item, str)]
    else:
        print("入参仅支持字符串或字符串列表")
        return False
    
    for code in check_list:
        if not bool(pattern.match(code)):
            print(f"股票代码格式错误: {code}（需6位数字+市场后缀，如688318.SH）")
            return False
    
    return True

def is_callback_func(func):
    """
    判断入参是否为 on_data(datas) 格式的函数
    """
    # 校验是否为可调用对象
    if not callable(func):
        return False
    
    try:
        # 获取函数的参数签名
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        
        # 筛选必填参数（无默认值、非*/*kwargs的参数）
        required_params = []
        for param in params:
            # 排除可变位置参数(*args)、可变关键字参数(**kwargs)
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if param.default is inspect.Parameter.empty:
                required_params.append(param)
        
        # 校验必填参数数量为1（核心规则）
        if len(required_params) != 1:
            return False
        return True
    
    except (ValueError, TypeError):
        return False

class tq:
    """TQ数据访问类，提供市场数据获取接口"""

    # 类变量，存储连接路径和资源
    _connection_path: str = ''
    _initialized = False

    run_id = -1
    run_mode = -1
    file_name = __file__
    dll_path = str(global_dll_path)

    # 添加finalizer相关
    _finalizer = None

    #是否已经将外套回调函数注册
    m_is_init_data_transfer = False
    #外套回调函数
    data_transfer = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
    #订阅回调函数{run_id: {code: callback_func}}
    data_callback_func = defaultdict(dict)
    # 缓存前复权因子
    _forward_factor_cache = {}

    # 订阅股票的列表
    _sub_hq_update = []

    @classmethod
    def _release(cls):
        if cls._initialized:
            dll.CloseConnect(cls.run_id, cls.run_mode)
            cls._initialized = False

    @classmethod
    def initialize(cls, 
                   path:str,
                   dll_path:str=''):
        cls._connection_path = path
        if dll_path: cls.dll_path = dll_path
        cls._auto_initialize()

        # 注册finalizer（如果尚未注册）
        if cls._finalizer is None:
            cls._finalizer = weakref.finalize(cls, cls._auto_close)
            # 同时注册atexit确保程序退出时清理
            atexit.register(cls._auto_close)

    @classmethod
    def _auto_close(cls):
        """关闭连接（线程安全版本）"""
        if cls._initialized:
            try:
                dll.CloseConnect(cls.run_id, cls.run_mode)
                cls._initialized = False
                print("TQ数据连接已关闭")
            except Exception as e:
                print(f"关闭连接时出错: {e}")

    @classmethod
    def close(cls):
        """手动关闭连接"""
        cls._auto_close()
        
        # 清理finalizer
        if cls._finalizer is not None and cls._finalizer.alive:
            cls._finalizer()

    # 析构方法
    def __del__(self):
        """实例析构时检查是否需要关闭类连接"""
        # 确保atexit已注册
        if not hasattr(tq, '_atexit_registered'):
            atexit.register(tq._auto_close)
            tq._atexit_registered = True
    
    @classmethod
    def _ensure_cleanup_registered(cls):
        """确保清理机制已注册"""
        if cls._finalizer is None:
            cls._finalizer = weakref.finalize(cls, cls._auto_close)
            atexit.register(cls._auto_close)
            # 设置标记，避免重复注册
            cls._atexit_registered = True

    @classmethod
    def _get_run_id(cls) -> int:
        """
        获取当前的run_id
        """
        if cls._initialized:
            return cls.run_id
        else:
            cls.close()
            raise RuntimeError("TQ数据接口未正确初始化")

    @classmethod
    def _auto_initialize(cls):
        """初始化连接"""
        if not cls._initialized:
            # 确保清理机制已注册
            cls._ensure_cleanup_registered()

            if len(cls._connection_path) <= 0:
                raise RuntimeError("TQ数据接口初始化失败")
            try:
                arguments = sys.argv[1:]
                if len(arguments) == 2:
                    if arguments[0] == '--run_tdx':
                        cls.run_mode = int(arguments[1])
                cls.file_name = cls._connection_path.encode('utf-8')
                dll_path_str = cls.dll_path.encode('utf-8')
                ptr = dll.InitConnect(cls.file_name, dll_path_str, cls.run_mode, get_python_version_number())
                if len(ptr) <= 0:
                    raise RuntimeError("TQ数据接口初始化失败:启动TPythClient失败")
                else:
                    ptr = ptr.decode('utf-8')
                    ptr_json = json.loads(ptr)
                    if ptr_json.get('ErrorId') == '0' or ptr_json.get('ErrorId') == '12':
                        cls.run_id = int(ptr_json.get('run_id', '-1'))
                        if ptr_json.get('ErrorId') == '12':
                            print(ptr_json.get('Error'))
                    else:
                        cls.run_id = -1
                if cls.run_id < 0:
                    raise RuntimeError("TQ数据接口初始化失败或已有同名策略运行")
                cls._initialized = True
                print(f"TQ数据接口初始化成功，使用路径: {cls._connection_path}")
            except Exception as e:
                raise RuntimeError("TQ数据接口初始化失败")

            if not cls._initialized:
                raise RuntimeError(
                    "TQ数据接口初始化失败。请手动调用 tq.initialize(path) 初始化连接。\n"
                    "可能的路径包括：当前目录、上级目录或空字符串。"
                )

    # ======== 数据提取与准备 ========
    @staticmethod
    def price_df(df, price_col, column_names=None):
        if not isinstance(df, dict) or len(df) == 0:
            tq.close()
            raise ValueError(f"输入数据为空（类型：{type(df)}）")

        if price_col not in df:
            tq.close()
            available_fields = list(df.keys())
            raise ValueError(f"数据中不存在'{price_col}'字段！\n可用字段：{available_fields}")

        # 直接获取对应字段的DataFrame
        df_price = df[price_col].copy()

        # 确保索引是datetime类型
        if not isinstance(df_price.index, pd.DatetimeIndex):
            df_price.index = pd.to_datetime(df_price.index)

        # 排序索引
        df_price = df_price.sort_index()

        # 转换为数值类型
        df_price = df_price.apply(pd.to_numeric, errors='coerce')

        # 填充缺失值
        df_price = df_price.ffill().bfill()

        if df_price.isnull().any().any():
            null_cols = df_price.columns[df_price.isnull().any()].tolist()
            print(f"警告：价格数据存在无法填充的空值（股票：{null_cols}）")

        # 重命名列
        if column_names is not None and len(column_names) == len(df_price.columns):
            df_price.columns = column_names
        elif column_names is not None:
            print(f"警告：自定义列名数量（{len(column_names)}）与数据列数（{len(df_price.columns)}）不匹配")

        return df_price
    
    @staticmethod
    def print_to_tdx(df_list, sp_name="", xml_filename="", jsn_filenames=None, 
                        vertical=None, horizontal=None, height=None, table_names=None):
        """
        将多组因子DataFrame导出为通达信所需的 .xml, .jsn, 和 .sp 文件，并移动到指定目录。
        核心改进：
        1. 每组table对应独立的DataFrame和JSON文件（独立表头+独立数据）
        2. 显示函数调用时的运行时间（格式：YYYY-MM-DD HH:MM:SS）
        
        df_list: DataFrame列表，每组table对应1个DataFrame（必须与组数一致）
                每个DF要求：第一列是日期（datetime64[ns] 类型或字符串），后续列是指标/因子名称
        sp_name: 因子名称，用于生成.sp文件名
        xml_filename: 生成的xml文件名（含后缀）
        jsn_filenames: JSON文件名列表（每组对应1个JSON），数量必须与组数/df_list长度一致
                    例：horizontal=2 → jsn_filenames=["h2_1.jsn", "h2_2.jsn"]（2组→2个JSON）
        vertical: 纵向排列的table组数（int），每组=1个condpanel+1个gridctrl，hdirection="true"
        horizontal: 横向排列的table组数（int），每组=1个condpanel+1个gridctrl，hdirection="false"（优先级更高）
        height: 自定义gridctrl高度列表（可选），长度需等于组数
                例：height=["0.4", "0.6"] → 第1组grid=0.4，第2组grid=0.6；无此参数时自动计算（1/组数，最后一组为0）
        table_names: 列表标题名称列表（可选），长度需等于组数，优先使用该值作为列表标题；
                    若未传入，则使用jsn_filenames的文件名前缀（去掉.jsn后缀）
                    例：table_names=["回测结果统计", "回测交易明细"]
        """
        # ===================== 1. 参数初始化与严格校验 =====================
        # 校验df_list（核心：必须是列表且长度≥1）
        if not isinstance(df_list, list) or len(df_list) == 0:
            raise ValueError("❌ df_list必须是非空列表类型（每组对应1个DataFrame）！")
        for idx, df in enumerate(df_list):
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise ValueError(f"❌ df_list第{idx+1}个元素必须是非空的DataFrame！")
        
        # 校验jsn_filenames
        if jsn_filenames is None:
            jsn_filenames = []
        if not isinstance(jsn_filenames, list) or len(jsn_filenames) == 0:
            raise ValueError("❌ jsn_filenames必须是非空列表类型！")
        
        # 确定排列方向、组数，并校验数量匹配
        if horizontal is not None and isinstance(horizontal, int) and horizontal >= 1:
            hdirection = "false"
            group_count = horizontal
        elif vertical is not None and isinstance(vertical, int) and vertical >= 1:
            hdirection = "true"
            group_count = vertical
        else:
            hdirection = "true"
            group_count = 1  # 默认1组
        
        # 关键校验：df_list长度 ≡ 组数 ≡ jsn_filenames长度
        if len(df_list) != group_count:
            raise ValueError(f"❌ df_list长度({len(df_list)})必须等于组数({group_count})！")
        if len(jsn_filenames) != group_count:
            raise ValueError(f"❌ jsn_filenames长度({len(jsn_filenames)})必须等于组数({group_count})！")
        
        # 校验height参数（长度需等于组数）
        custom_height = []
        if height is not None:
            if not isinstance(height, list) or len(height) != group_count:
                raise ValueError(f"❌ height参数必须是长度为{group_count}的列表（如height=['0.4', '0.6']）！")
            custom_height = [str(h) for h in height]
        
        # 处理table_names参数
        table_title_list = []
        if table_names is not None:
            if not isinstance(table_names, list) or len(table_names) != group_count:
                raise ValueError(f"❌ table_names长度({len(table_names)})必须等于组数({group_count})！")
            table_title_list = [name.strip() if isinstance(name, str) and name.strip() else "" for name in table_names]
        else:
            table_title_list = [""] * group_count
        
        # 生成最终的列表标题：优先用table_names，否则用jsn_filenames前缀
        final_table_titles = []
        for idx in range(group_count):
            if table_title_list[idx]:
                final_title = table_title_list[idx]
            else:
                jsn_name = jsn_filenames[idx]
                final_title = os.path.splitext(jsn_name)[0]
            final_table_titles.append(final_title)
        
        # 获取函数调用时的运行时间（核心新增）
        run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"📌 函数运行时间：{run_time}")
        print(f"📌 列表标题配置：{final_table_titles}")

        # ===================== 2. 通达信路径配置 =====================
        # default_tdx_path = r'D:\new_tdx_test'
        
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.dirname(os.path.dirname(current_dir))  # 等价于 parent.parent
        default_tdx_path=target_dir
        
        tdx_root_path = getattr(tq, 'tdx_path', default_tdx_path) if tq is not None else default_tdx_path
        print(f"ℹ️ 通达信根目录路径: {tdx_root_path}")

        # ===================== 3. 生成XML文件（核心修改：移除日期筛选，显示运行时间） =====================
        xml_content = f'''<?xml version="1.0" encoding="gbk" ?>
    <root>
        <table X="0" Y="0" width="1" height="1" isleaf="false" hdirection="true">
            <table X="0" Y="0" width="1" height="1" isleaf="true" hdirection="true" name="branchpanel">
                <branchpanel hdirection="{hdirection}">

    '''
        
        current_table_id = 1  # table id从1开始递增
        auto_height_base = 1.0 / group_count  # 自动高度基数
        
        for group_idx in range(group_count):
            # 当前组的核心配置
            current_df = df_list[group_idx]
            current_jsn = jsn_filenames[group_idx]
            is_last_group = (group_idx == group_count - 1)
            current_title = final_table_titles[group_idx]  # 当前组的列表标题
            
            # -------- 生成当前组的condpanel（移除日期筛选，显示运行时间） --------
            cond_id = current_table_id
            xml_content += f'''
                        <table X="0" Y="-1" width="1" height="36" isleaf="true" id="{cond_id}" name="condpanel">
                            <condpanel>
                                <ctrls rowcount="1" frameline="10">
                                    <ctrl rowindex="0" index="1" text="{current_title}" type="static" hoffset="10" align="L" width="120" fontsize="-14"></ctrl>	
                                    <ctrl rowindex="0" index="2" text="运行时间：{run_time}" type="static" hoffset="10" align="L" width="200" fontsize="-14"></ctrl>
                                    <ctrl rowindex="0" index="97" text="导出" type="button" hoffset="5" align="R" width="50" bindparam="$M_EXP" fontsize="-14"></ctrl>
                                    <ctrl rowindex="0" index="98" text="刷新" type="button" hoffset="5" align="R" width="50" bindparam="IDOK" fontsize="-14"></ctrl>
                                    <ctrl rowindex="0" index="99" text="" type="statnote" hoffset="5" align="R" width="80" fontsize="-14"><statnote format="共%d条"/></ctrl>
                                </ctrls>
                            </condpanel>
                        </table>

    '''
            # -------- 生成当前组的gridctrl（数据展示面板） --------
            current_table_id += 1
            grid_id = current_table_id
            
            # 计算grid高度
            if custom_height:
                grid_h = custom_height[group_idx]
            else:
                grid_h = 0 if is_last_group else auto_height_base
            
            xml_content += f'''
                        <table X="0" Y="-1" width="1" height="{grid_h}" isleaf="true" id="{grid_id}" name="gridctrl">
                            <gridctrl >
                                <gridcols fixednum="1" rowchgmsg="true" postslave="true" showtip="1" defsort="date" expandfull="1">
                                    
    '''
            # 生成当前组的列头
            sp_names = current_df.columns[1:].tolist()
            for j, fname in enumerate(sp_names, 1):
                col_name = f"code_g{group_idx+1}_t1_{j}"
                xml_content += f'\t\t\t\t\t\t\t\t<gridcol name="{col_name}" caption="{fname}" visible="true" filter="true" align="R" headalign="R" width="120" datatype="S"/>\n'

            xml_content += f'''							</gridcols>
                                <datasource  reqformat="11"  condid="{cond_id}" name="" body="list/{current_jsn}"/>
                            </gridctrl>
                        </table>


    '''
            current_table_id += 1

        # 闭合XML标签
        xml_content += f'''			</branchpanel>
            </table>
        </table>
    </root>'''

        # 写入XML文件
        with open(xml_filename, "w", encoding="gbk") as f:
            f.write(xml_content)
        print(f"✅ XML 文件生成完成：{xml_filename}（列表标题：{final_table_titles}）")

        # ===================== 4. 生成JSON文件（保留原有逻辑） =====================
        json_dir = os.path.join(tdx_root_path, r"T0002\cloud_cache\list")
        os.makedirs(json_dir, exist_ok=True)
        
        for g_idx in range(group_count):
            current_df = df_list[g_idx]
            jsn_file = jsn_filenames[g_idx]
            
            # 生成列头
            col_header = ["date"] + [f"code_g{g_idx+1}_t1_{j}" for j, _ in enumerate(current_df.columns[1:], 1)]
            
            # 生成数据行
            data_rows = []
            for _, row in current_df.iterrows():
                # 日期处理
                date_str = row.iloc[0].strftime("%Y-%m-%d") if pd.api.types.is_datetime64_any_dtype(current_df.iloc[:, 0]) else str(row.iloc[0])
                # 数值处理
                vals = []
                for v in row.iloc[1:]:
                    try:
                        vals.append(float(v))
                    except:
                        vals.append(str(v) if pd.notna(v) else "")
                data_rows.append([date_str] + vals)
            
            # 写入JSON
            with open(jsn_file, "w", encoding="utf-8") as f:
                json.dump([{"colheader": col_header, "data": data_rows}], f, ensure_ascii=False, indent=2)
            
            # 移动到通达信目录
            jsn_target = os.path.join(json_dir, jsn_file)
            if os.path.exists(jsn_target):
                os.remove(jsn_target)
            shutil.move(jsn_file, jsn_target)

        # ===================== 5. 移动XML文件 =====================
        xml_dir = os.path.join(tdx_root_path, r"T0002\cloud_cfg")
        os.makedirs(xml_dir, exist_ok=True)
        xml_target = os.path.join(xml_dir, xml_filename)
        if os.path.exists(xml_target):
            os.remove(xml_target)
        shutil.move(xml_filename, xml_target)
        print(f"✅ XML文件移动完成：{xml_filename} → {xml_target}")

        # ===================== 6. 生成SP文件（新增运行时间记录） =====================
        pad_dir = os.path.join(tdx_root_path, r"T0002\pad")
        os.makedirs(pad_dir, exist_ok=True)
        sp_file = f"{sp_name}.sp" if sp_name else "python.sp"
        sp_path = os.path.join(pad_dir, sp_file)
        sp_content = f'''[DEAFULTGP]
    Name={sp_name}
    ShowName=
    CmdNum=2
    UnitNum=1
    KeyGuyToExtern=0
    ForceUseDS=0
    PadMaxCx=0
    PadMaxCy=0
    PadHelpStr=运行时间：{run_time}  # 记录运行时间
    PadHelpUrl=
    HasProcessBtn=0
    UnSizeMode=0
    HQGridNoCode=0
    crTipWord=0
    FixedSwitchMode=0
    AutoFitMode=0
    UserPadFlag=0
    RelType=0
    RelType2=0
    RelType1For2=0
    RelType2For1=0
    CTPGroupType=0
    AutoSize=0
    HideAreaByUnitStr=
    GPSetCode_Code1=1_688318.SH

    [STEP0]
    SplitWhich=-1
    UnitStr=BigData终端组件
    UnitStr_Long=
    UnitDesc=运行时间：{run_time}
    UnitGlStr=
    UnitInClass1=
    UnitType=ZDBIGDATA_UNIT
    UnitStyle=ZST_BIG
    HowToSplit=0
    SplitRatio=100.0000
    ShowGpNo=1
    IsLocked=0
    Fixed_Width=0
    Fixed_Height=0
    Hided_Width=0
    Hided_Height=0
    IsCurrent=1
    OneCanShowSwitch=0
    ShowRefreshBtn=0
    SwitchBarPos=1
    SwitchBarScheme=2
    CollapseFlag=0
    FoldArrowFlag=0
    CfgName={xml_filename.split('.')[0]}
    '''
        with open(sp_path, "w", encoding="gbk") as f:
            f.write(sp_content)
        print(f"✅ SP文件生成完成：{sp_file} → {sp_path}")

    @classmethod
    def _data_callback_transfer(cls, data_str):
        data_str = data_str.decode('utf-8')
        data_json = json.loads(data_str)
        codes = data_json['Code']

        if cls.data_callback_func.get(cls._get_run_id()) is None:
            print("No callback function registered for run_id:", cls._get_run_id())
            return None
        if cls.data_callback_func[cls._get_run_id()].get(codes) is None:
            print("No callback function registered for code:", codes)
            return None
        return cls.data_callback_func[cls._get_run_id()][codes](data_str)
        
    @classmethod
    def filter_dict_by_fields(cls, data: Dict = {}, field_list: List = []) -> Dict:
        """
        根据指定的字段列表筛选字典中的键值对（不区分大小写）

        Args:
            data: 原始字典数据
            field_list: 需要保留的字段列表（大小写不敏感）
            
        Returns:
            筛选后的新字典（保留原始键名的大小写）
        """
        # 创建小写键到原始键的映射
        key_lower_map = {key.lower(): key for key in data.keys()}

        # 筛选字段（不区分大小写）
        filtered_data = {}
        for field in field_list:
            field_lower = field.lower()
            if field_lower in key_lower_map:
                original_key = key_lower_map[field_lower]
                filtered_data[original_key] = data[original_key]

        return filtered_data    

    @classmethod
    def get_market_data(cls,
                        field_list: List[str] = [],
                        stock_list: List[str] = [],
                        period: str = '',
                        start_time: str = '',
                        end_time: str = '',
                        count: int = -1,
                        dividend_type: Optional[str] = None,
                        fill_data: bool = True) -> Dict:

        # 初始化连接
        cls._auto_initialize()
        # stimeD = time.time()

        # 快速参数验证
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空")

        if not period:
            cls.close()
            raise ValueError("必传参数缺失：period不能为空")

        # 周期校验
        valid_periods = ['5m', '15m', '30m', '1h', '1d', '1w', '1mon', '1m', '10m', '45d', '1q', '1y']
        if period.lower() not in valid_periods:
            return {'error': -5, 'msg': f'周期格式错误：{period}（支持{valid_periods}）'}

        # 除权类型转换
        if dividend_type is None:
            dividend_type = 'none'
        dividend_type_map = {'none': 10, 'front': 1, 'back': 2}
        dividend_type_int = dividend_type_map.get(dividend_type.lower(), 0)

        # 股票代码格式校验
        if not cls._check_stock_code_format_batch(stock_list):
            cls.close()
            raise ValueError(f"{stock_list}异常")

        # 修复时间参数处理逻辑
        if count > 0:
            # count模式：只需要end_time，start_time应该为空
            if not end_time:
                end_time = datetime.now().strftime('%Y%m%d%H%M%S')
            start_time_fmt = ''
            end_time_fmt = _convert_time_format(end_time) if end_time else ''
        else:
            # 如果没有提供end_time，使用当前时间
            if not end_time:
                end_time = datetime.now().strftime('%Y%m%d%H%M%S')
                
            start_time_fmt = _convert_time_format(start_time)
            end_time_fmt = _convert_time_format(end_time)

        # 预编码参数
        period_bytes = period.encode('utf-8')
        start_bytes = start_time_fmt.encode('utf-8') if start_time_fmt else b''
        end_bytes = end_time_fmt.encode('utf-8') if end_time_fmt else b''

        # 获取数据
        all_data = cls._fetch_market_data_batch(
            stock_list, period_bytes, start_bytes, end_bytes, 
            dividend_type_int, count, timeout_ms=60000
        )

        # 快速格式化
        if period == 'tick':
            result_data = cls._fast_format_tick_data(all_data, field_list)
        else:
            result_data = cls._fast_format_kline_data(all_data, stock_list, fill_data)

        # 筛选字段
        if field_list:
            available = set(result_data.keys())
            selected = [f for f in field_list if f in available]
            return {f: result_data[f].copy() for f in selected}
        else:
            return {k: v.copy() for k, v in result_data.items() if k != "ErrorId"}
            

    @classmethod
    def _check_stock_code_format_batch(cls, stock_list):
        """批量验证股票代码格式"""
        pattern = re.compile(r'^\d{6}\.[A-Z]{2,3}$')
        return all(pattern.match(stock) for stock in stock_list)

    @classmethod
    def _fetch_market_data_batch(cls, stock_list, period_bytes, start_bytes, end_bytes, 
                                dividend_type_int, count, timeout_ms=60000):
        """批量获取市场数据"""
        all_data = {}
        
        for stock in stock_list:
            try:
                stock_bytes = stock.encode('utf-8')
                
                ptr = dll.GetHISDATsInStr(
                    cls._get_run_id(),
                    stock_bytes,
                    start_bytes,
                    end_bytes,
                    period_bytes,
                    dividend_type_int,
                    count,
                    timeout_ms
                )
                
                if ptr and len(ptr) > 0:
                    data_dict = json.loads(ptr)
                    if data_dict.get("ErrorId") == "0":
                        all_data[stock] = data_dict
                        
            except Exception:
                continue
                
        return all_data
    
    @classmethod
    def _calculate_forward_factors_from_dividends(cls, df_factors: pd.DataFrame, price_series: pd.Series) -> pd.Series:
        """
        从除权除息数据计算前复权因子的调整系数
        返回的是从旧到新的调整系数，键为事件发生日期
        """
        if df_factors.empty or price_series.empty:
            return pd.Series()

        # 按日期正序排列（从旧到新）
        df_sorted = df_factors.sort_index(ascending=True).copy()

        # 初始化调整系数字典
        adjust_dict = {}

        # 获取价格数据的所有日期
        price_dates = price_series.index

        # 遍历所有除权除息事件
        for date in df_sorted.index:
            if date not in price_dates:
                continue

            row = df_sorted.loc[date]

            # 获取前一日的价格
            prev_date_idx = price_dates.get_loc(date) - 1
            if prev_date_idx < 0:
                continue

            prev_date = price_dates[prev_date_idx]
            prev_close = price_series.iloc[prev_date_idx]

            if prev_close <= 0:
                continue

            # 提取分红送股信息
            bonus_per_10 = row['Bonus']  # 每10股分红
            bonus_per_share = bonus_per_10 / 10.0  # 每股分红
            share_bonus_ratio = row['ShareBonus'] / 10.0  # 送股比例
            allotment_ratio = row['Allotment'] / 10.0  # 配股比例
            allot_price = row['AllotPrice']  # 配股价

            # 计算除权除息价
            # 除权价 = (前收盘价 - 现金分红) / (1 + 送股比例 + 转增比例)
            denominator = 1 + share_bonus_ratio + allotment_ratio
            if denominator <= 0:
                denominator = 1.0

            ex_right_price = (prev_close - bonus_per_share) / denominator

            # 计算调整系数
            # 调整系数 = 除权除息价 / 前收盘价
            adjust_ratio = ex_right_price / prev_close

            # 将调整系数关联到事件发生日期
            adjust_dict[date] = adjust_ratio

        # 创建调整系数序列
        adjust_series = pd.Series(adjust_dict)

        return adjust_series.sort_index()


    @classmethod
    def _fast_format_kline_data(cls, all_data: Dict, stock_list: List[str], fill_data: bool) -> Dict:
        if not all_data:
            return {}

        # 极速构建时间索引
        all_timestamps = set()
        for stock_data in all_data.values():
            dates = stock_data.get('Date', [])
            if dates:
                times = stock_data.get('Time', [])
                for i, date in enumerate(dates):
                    if i < len(times) and times[i] not in ("0", "000000", "0000"):
                        all_timestamps.add(f"{date}{int(times[i]):06d}")
                    else:
                        all_timestamps.add(date)

        if not all_timestamps:
            return {}

        sorted_ts = sorted(all_timestamps)
        time_index = pd.DatetimeIndex([datetime.strptime(ts, '%Y%m%d%H%M%S' if len(ts)>8 else '%Y%m%d') for ts in sorted_ts])
        ts_to_idx = {ts: i for i, ts in enumerate(sorted_ts)}
        n_time = len(time_index)

        # 批量处理字段
        fields = set().union(*(d.keys() for d in all_data.values())) - {'Date', 'Time', 'ErrorId'}
        result = {}
        
        for field in fields:
            # 使用numpy数组直接操作   
            data_arr = np.full((n_time, len(stock_list)), np.nan, dtype=np.float64)
            
            for s_idx, stock in enumerate(stock_list):
                if stock in all_data and field in all_data[stock]:
                    data = all_data[stock]
                    dates = data.get('Date', [])
                    values = data.get(field, [])
                    times = data.get('Time', [])
                    
                    # 极速数据处理
                    indices, vals = [], []
                    for i, date in enumerate(dates):
                        if i < len(values):
                            ts = f"{date}{int(times[i]):06d}" if i<len(times) and times[i] not in ("0", "000000", "0000") else date
                            if ts in ts_to_idx:
                                try:
                                    v = float(values[i]) if values[i] else np.nan
                                    if not np.isnan(v):
                                        indices.append(ts_to_idx[ts])
                                        vals.append(v)
                                except:
                                    pass
                    
                    if indices:
                        data_arr[indices, s_idx] = vals
                        
                        if fill_data:
                            col = data_arr[:, s_idx] 
                            mask = ~np.isnan(col)
                            if mask.any():  # 列中至少有一个非NaN值才执行填充
                                idx_arr = np.where(mask, np.arange(len(col)), 0)
                                np.maximum.accumulate(idx_arr, out=idx_arr)
                                col[:] = col[idx_arr]
            
            result[field] = pd.DataFrame(data_arr, index=time_index, columns=stock_list)
    
        return result





    @classmethod
    def _fast_format_tick_data(cls, all_data: Dict, field_list: List[str]) -> Dict:
        """优化版tick数据格式化"""
        result = {}

        for stock, stock_data in all_data.items():
            if 'Date' in stock_data and 'Time' in stock_data:
                dates = stock_data['Date']
                times = stock_data['Time']
                
                # 批量处理时间戳
                timestamps = []
                for i, date in enumerate(dates):
                    time_val = times[i] if i < len(times) else "0"
                    if time_val not in ["0", "000000"]:
                        timestamps.append(f"{date}{int(time_val):06d}")
                    else:
                        timestamps.append(date)
                
                # 筛选字段
                if field_list:
                    selected_fields = [f for f in field_list if f in stock_data and f not in ['Date', 'Time', 'ErrorId']]
                else:
                    selected_fields = [f for f in stock_data.keys() if f not in ['Date', 'Time', 'ErrorId']]
                
                if selected_fields and timestamps:
                    # 创建结构化数组（优化版）
                    dtype = [('datetime', 'U14')]
                    for field in selected_fields:
                        sample = stock_data[field][0] if stock_data[field] else "0"
                        dtype.append((field, np.float64 if '.' in sample else np.int32))
                    
                    arr = np.zeros(len(timestamps), dtype=dtype)
                    arr['datetime'] = timestamps
                    
                    for field in selected_fields:
                        if field in stock_data:
                            try:
                                arr[field] = pd.to_numeric(stock_data[field], errors='coerce')
                            except:
                                pass
                    
                    result[stock] = arr

        return result
    

    
    
        

    @classmethod
    def get_divid_factors(cls,
                          stock_code: str,
                          start_time: str,
                          end_time: str) -> pd.DataFrame:
        """获取除权除息数据"""
        cls._auto_initialize()

        if not stock_code:
            return pd.DataFrame()

        if not end_time:
            end_time = datetime.now().strftime('%Y%m%d%H%M%S')
        
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

        codestr = stock_code.encode('utf-8')
        startimestr = start_time.encode('utf-8')
        endtimestr = end_time.encode('utf-8')
        timeout_ms = 10000

        result_str = dll.GetCWDATAInStr(cls._get_run_id(), codestr, startimestr, endtimestr, timeout_ms)

        if result_str is None or len(result_str) == 0:
            return pd.DataFrame()

        try:
            result_str = result_str.decode('utf-8')
        except Exception:
            return pd.DataFrame()

        try:
            data_dict = json.loads(result_str)

            if data_dict.get("ErrorId") != "0":
                return pd.DataFrame()

            dates = data_dict.get("Date", [])
            types = data_dict.get("Type", [])
            values = data_dict.get("Value", [])

            if not dates:
                return pd.DataFrame()

            # 创建DataFrame
            bonus_list = []
            allot_price_list = []
            share_bonus_list = []
            allotment_list = []

            for value_item in values:
                if value_item and len(value_item) >= 4:
                    bonus_list.append(float(value_item[0]) if value_item[0] else 0.0)
                    allot_price_list.append(float(value_item[1]) if value_item[1] else 0.0)
                    share_bonus_list.append(float(value_item[2]) if value_item[2] else 0.0)
                    allotment_list.append(float(value_item[3]) if value_item[3] else 0.0)
                else:
                    bonus_list.append(0.0)
                    allot_price_list.append(0.0)
                    share_bonus_list.append(0.0)
                    allotment_list.append(0.0)

            df = pd.DataFrame({
                'Date': dates,
                'Type': types,
                'Bonus': bonus_list,
                'AllotPrice': allot_price_list,
                'ShareBonus': share_bonus_list,
                'Allotment': allotment_list
            })

            # 处理日期和索引
            df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d', errors='coerce')
            df = df.dropna(subset=['Date'])  # 删除无效日期
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)

            # 根据时间区间进行切片 C接口的时间没有实际作用，返回的是所有权息数据
            start_ts = pd.Timestamp(start_time, tz=None)   # 与索引保持 naive 一致
            end_ts = pd.Timestamp(end_time, tz=None)
            if not start_time:
                mask = (df.index <= end_ts)
            else:
                mask = (df.index >= start_ts) & (df.index <= end_ts)
            df = df.loc[mask].copy()

            return df

        except json.JSONDecodeError:
            return pd.DataFrame()
    
    @classmethod
    def get_stock_info(cls,
                        stock_code:str, 
                        field_list: List = []) -> Dict:
        """获取基础财务数据"""
        # 初始化连接
        cls._auto_initialize()

        if not check_stock_code_format(stock_code):
            cls.close()
            raise ValueError(f"{stock_code}异常")
        codestr = stock_code.encode('utf-8')
        timeout_ms = 10000

        try:
            ptr = dll.GetSTOCKInStr(cls._get_run_id(), codestr, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取合约详情失败: 返回空指针")
                return {}
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取合约详情错误: {json_res.get('Error')}")
                return {}
            if field_list:
                json_res = cls.filter_dict_by_fields(json_res, field_list)
            return json_res
        except Exception as e:
            cls.close()
            raise ValueError("获取合约详情异常")
        
    @classmethod
    def get_market_snapshot(cls,
                    stock_code: str) -> Dict:
        """获取报表数据"""
        # 初始化连接
        cls._auto_initialize()
        
        if not check_stock_code_format(stock_code):
            tq.close()
            raise ValueError(f"{stock_code}异常")
        codestr = stock_code.encode('utf-8')
        timeout_ms = 60000

        try:
            ptr = dll.GetREPORTInStr(cls._get_run_id(), codestr, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取报表数据失败: 返回空指针")
                return {}
            print("json:",result_str)
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取报表数据错误: {json_res.get('Error')}")
                return {}
            return json_res
        except Exception as e:
            cls.close()
            raise ValueError("获取报表数据异常")
        
    @classmethod
    def send_message(cls,
                    msg_str: str) -> Dict:
        """策略管理输出字符串"""
        # 初始化连接
        cls._auto_initialize()

        msg_str = 'MSG||' + msg_str
        resultstr = msg_str.encode('utf-8')
        timeout_ms = 5000

        try:
            ptr = dll.SetResToMain(cls._get_run_id(), cls.run_mode, resultstr, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("发送信息到主程序失败: 返回空指针")
                return {}
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"发送信息到主程序错误: {json_res.get('Error')}")
                return {}
            return json_res
        except Exception as e:
            cls.close()
            raise ValueError("发送信息到主程序异常")

    @classmethod
    def send_file(cls,
                    file_path: str) -> Dict:
        """策略管理输出字符串"""
        # 初始化连接
        cls._auto_initialize()

        file_path = 'FILE||' + file_path
        resultstr = file_path.encode('utf-8')
        timeout_ms = 5000

        try:
            ptr = dll.SetResToMain(cls._get_run_id(), cls.run_mode, resultstr, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("发送文件路径到主程序失败: 返回空指针")
                return {}
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"发送文件路径到主程序错误: {json_res.get('Error')}")
                return {}
            return json_res
        except Exception as e:
            cls.close()
            raise ValueError("发送文件路径到主程序异常")

    @classmethod
    def send_warn(cls,
                  stock_list:        List[str] = [],
                  time_list:         List[str] = [],
                  price_list:        List[str] = [],
                  close_list:        List[str] = [],
                  volum_list:        List[str] = [],
                  bs_flag_list:      List[str] = [],
                  warn_type_list:    List[str] = [],
                  reason_list:       List[str] = [],
                  count:        int  = 1) -> Dict:
        """发送预警信息到主程序"""
        if count <= 0:
            cls.close()
            raise ValueError("发送预警参数错误：count必须大于0")

        # 初始化连接
        cls._auto_initialize()

        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        warn_str = get_warn_struct_str(stock_list,
                                       time_list,
                                       price_list,
                                       close_list,
                                       volum_list,
                                       bs_flag_list,
                                       warn_type_list,
                                       reason_list,
                                       count)
        warn_str = 'WARN||' + warn_str
        warn_str = warn_str.encode('utf-8')
        timeout_ms = 5000

        try:
            ptr = dll.SetResToMain(cls._get_run_id(), cls.run_mode, warn_str, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("发送预警信息到主程序失败: 返回空指针")
                return {}
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"发送预警信息到主程序错误: {json_res.get('Error')}")
                return {}
            return json_res
        except Exception as e:
            cls.close()
            raise ValueError("发送预警信息到主程序异常")

    @classmethod
    def send_bt_data(cls,
                     stock_code:          str  = '',
                     time_list:         List[str] = [],
                     data_list:         List[List[str]] = [],
                     count:        int  = 1) -> Dict:
        """策略管理输出回测数据"""
        if count <= 0:
            cls.close()
            raise ValueError("发送回测数据错误：count必须大于0")
        if not check_stock_code_format(stock_code):
            tq.close()
            raise ValueError(f"{stock_code}异常")
        # 初始化连接
        cls._auto_initialize()

        bt_data = get_bt_struct_str(time_list,
                                    data_list,
                                    count)  
        bt_data = 'BTR||' + stock_code + '||' + bt_data
        bt_data = bt_data.encode('utf-8')
        timeout_ms = 5000

        try:
            ptr = dll.SetResToMain(cls._get_run_id(), cls.run_mode, bt_data, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("发送回测数据到主程序失败: 返回空指针")
                return {}
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"发送回测数据到主程序错误: {json_res.get('Error')}")
                return {}
            return json_res
        except Exception as e:
            cls.close()
            raise ValueError("发送回测数据到主程序异常")

    @classmethod
    def send_user_block(cls,
                block_code: str = '',
                stocks: List[str] = [],
                show: bool = False) -> Dict:
        """客户端添加自选股"""
        # 初始化连接
        cls._auto_initialize()

        result_str = convert_or_validate(stocks)

        result_str = 'XG,' + block_code + '||' + result_str + '||' + ('1' if show else '0')
        resultstr = result_str.encode('utf-8')
        timeout_ms = 30000

        try:
            ptr = dll.SetResToMain(cls._get_run_id(), cls.run_mode, resultstr, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("发送自选股到主程序失败: 返回空指针")
                return {}
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"发送自选股到主程序错误: {json_res.get('Error')}")
                return {}
            return json_res
        except Exception as e:
            cls.close()
            raise ValueError("发送自选股到主程序异常")

    @classmethod
    def get_sector_list(cls) -> List:
        """获取板块列表"""
        # 初始化连接
        cls._auto_initialize()

        timeout_ms = 5000

        try:
            ptr = dll.GetBlockListInStr(cls._get_run_id(), timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取板块列表失败: 返回空指针")
                return []
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取板块列表错误: {json_res.get('Error')}")
                return []
            result = [item.replace('.1', '.SH').replace('.0', '.SZ').replace('.2', '.BJ') for item in json_res['Value']]
            return result
        except Exception as e:
            cls.close()
            raise ValueError("获取板块列表异常")
        
    @classmethod
    def get_user_sector(cls) -> List:
        """获取用户自选股板块列表"""
        # 初始化连接
        cls._auto_initialize()

        timeout_ms = 5000

        try:
            ptr = dll.GetUserBlockInStr(cls._get_run_id(), timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取用户自选股板块列表失败: 返回空指针")
                return []
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取用户自选股板块列表错误: {json_res.get('Error')}")
                return []
            return json_res['Value']
        except Exception as e:
            cls.close()
            raise ValueError("获取用户自选股板块列表异常")
        
    @classmethod
    def get_stock_list_in_sector(cls,
                         block_code: str,
                         block_type: int = 0) -> List:
        """获取板块成分股"""
        # 初始化连接
        cls._auto_initialize()

        if block_type == 1:
            block_code  = "BKCODE." + block_code
        codestr = block_code.encode('utf-8')
        timeout_ms = 5000

        try:
            ptr = dll.GetBlockStocksInStr(cls._get_run_id(), codestr, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取板块成分股失败: 返回空指针")
                return []
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取板块成分股错误: {json_res.get('Error')}")
                return []
            
            result = [item.replace('.1', '.SH').replace('.0', '.SZ').replace('.2', '.BJ') for item in json_res['Value']]
            return result
        except Exception as e:
            cls.close()
            raise ValueError("获取板块成分股异常")

    @classmethod
    def get_financial_data(cls,
                            stock_list: List[str] = [], 
                            field_list: List[str] = [], 
                            start_time: str = '', 
                            end_time: str = '', 
                            report_type: str = 'report_time') -> Dict:
        """获取财务数据"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码列表")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        if not end_time:
            end_time = datetime.now().strftime('%Y%m%d%H%M%S')

        # 格式化时间参数
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

        timeout_ms = 10000 # 10秒超时
        result_dict = {}    # 返回结果字典

        for stock in stock_list:
            try:
                stock_json = {  "id" : cls._get_run_id(),
                                "type": "1",
                                "code": stock,
                                "table_list": field_list,
                                "start_time": start_time,
                                "end_time": end_time,
                                "report_type": report_type}
                json_str = json.dumps(stock_json, ensure_ascii=False)
                json_str = json_str.encode('utf-8')
                ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
                # 检查返回的指针
                if ptr is None or len(ptr) == 0:
                    print(f"获取{stock}财务数据失败: 返回空指针")
                    continue

                # 解析JSON数据
                try:
                    data_dict = json.loads(ptr)
                except json.JSONDecodeError as e:
                    print(f"获取{stock}财务数据失败: JSON解析错误 - {e}")
                    print(f"原始返回数据: {ptr}")
                    continue

                # 检查错误代码
                if data_dict.get("ErrorId") != "0":
                    print(f"获取{stock}财务数据错误: {data_dict.get('Error')}")
                    continue

                # 获取所有列表的长度，检查是否一致
                list_lengths = [len(v) for v in data_dict['Data'].values()]
                if len(set(list_lengths)) != 1:
                    print("输入字典中各字段的列表长度不一致，返回当前数据。")
                    return data_dict['Data']
                
                # 2. 转换为DataFrame
                df = pd.DataFrame(data_dict['Data'])
                result_dict[stock] = df

            except Exception as e:
                print(f"获取{stock}财务数据异常: {e}")
                import traceback
                traceback.print_exc()
                continue

        return result_dict
    
    @classmethod
    def get_financial_data_by_date(cls,
                                    stock_list: List[str] = [], 
                                    field_list: List[str] = [],  
                                    year: int = 0,
                                    mmdd: int = 0) -> Dict:
        """获取财务数据"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码列表")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        timeout_ms = 10000 # 10秒超时
        result_dict = {}    # 返回结果字典

        for stock in stock_list:
            try:
                stock_json = {  "id" : cls._get_run_id(),
                                "type": "2",
                                "code": stock,
                                "table_list": field_list,
                                "year": year,
                                "mmdd": mmdd}
                json_str = json.dumps(stock_json, ensure_ascii=False)
                json_str = json_str.encode('utf-8')
                ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
                # 检查返回的指针
                if ptr is None or len(ptr) == 0:
                    print(f"获取{stock}财务数据失败: 返回空指针")
                    continue

                # 解析JSON数据
                try:
                    data_dict = json.loads(ptr)
                except json.JSONDecodeError as e:
                    print(f"获取{stock}财务数据失败: JSON解析错误 - {e}")
                    print(f"原始返回数据: {ptr}")
                    continue

                # 检查错误代码
                if data_dict.get("ErrorId") != "0":
                    print(f"获取{stock}财务数据错误: {data_dict.get('Error')}")
                    continue

                result_dict[stock] = data_dict['Data']

            except Exception as e:
                print(f"获取{stock}财务数据异常: {e}")
                import traceback
                traceback.print_exc()
                continue

        return result_dict
    
    @classmethod
    def get_gpjy_value(cls,
                        stock_list: List[str] = [], 
                        field_list: List[str] = [], 
                        start_time: str = '', 
                        end_time: str = '') -> Dict:
        """获取股票交易数据"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码列表")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        if not end_time:
            end_time = datetime.now().strftime('%Y%m%d%H%M%S')

        # 格式化时间参数
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

        timeout_ms = 10000 # 10秒超时
        result_dict = {}    # 返回结果字典

        for stock in stock_list:
            try:
                stock_json = {  "id" : cls._get_run_id(),
                                "type": "3",
                                "code": stock,
                                "table_list": field_list,
                                "start_time": start_time,
                                "end_time": end_time}
                json_str = json.dumps(stock_json, ensure_ascii=False)
                json_str = json_str.encode('utf-8')
                ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
                # 检查返回的指针
                if ptr is None or len(ptr) == 0:
                    print(f"获取{stock}股票交易数据失败: 返回空指针")
                    continue

                # 解析JSON数据
                try:
                    data_dict = json.loads(ptr)
                except json.JSONDecodeError as e:
                    print(f"获取{stock}股票交易数据失败: JSON解析错误 - {e}")
                    print(f"原始返回数据: {ptr}")
                    continue

                # 检查错误代码
                if data_dict.get("ErrorId") != "0":
                    print(f"获取{stock}股票交易数据错误: {data_dict.get('Error')}")
                    continue

                result_dict[stock] = data_dict['Data']

            except Exception as e:
                print(f"获取{stock}财务数据异常: {e}")
                import traceback
                traceback.print_exc()
                continue

        return result_dict
    
    @classmethod
    def get_gpjy_value_by_date(cls,
                                stock_list: List[str] = [], 
                                field_list: List[str] = [],  
                                year: int = 0,
                                mmdd: int = 0) -> Dict:
        """获取股票交易数据"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码列表")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        timeout_ms = 10000 # 10秒超时
        result_dict = {}    # 返回结果字典

        for stock in stock_list:
            try:
                stock_json = {  "id" : cls._get_run_id(),
                                "type": "4",
                                "code": stock,
                                "table_list": field_list,
                                "year": year,
                                "mmdd": mmdd}
                json_str = json.dumps(stock_json, ensure_ascii=False)
                json_str = json_str.encode('utf-8')
                ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
                # 检查返回的指针
                if ptr is None or len(ptr) == 0:
                    print(f"获取{stock}股票交易数据失败: 返回空指针")
                    continue

                # 解析JSON数据
                try:
                    data_dict = json.loads(ptr)
                except json.JSONDecodeError as e:
                    print(f"获取{stock}股票交易数据失败: JSON解析错误 - {e}")
                    print(f"原始返回数据: {ptr}")
                    continue

                # 检查错误代码
                if data_dict.get("ErrorId") != "0":
                    print(f"获取{stock}股票交易数据错误: {data_dict.get('Error')}")
                    continue

                result_dict[stock] = data_dict['Data']

            except Exception as e:
                print(f"获取{stock}财务数据异常: {e}")
                import traceback
                traceback.print_exc()
                continue

        return result_dict
    
    @classmethod
    def get_bkjy_value(cls,
                        stock_list: List[str] = [], 
                        field_list: List[str] = [], 
                        start_time: str = '', 
                        end_time: str = '') -> Dict:
        """获取板块交易数据"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码列表")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        if not end_time:
            end_time = datetime.now().strftime('%Y%m%d%H%M%S')

        # 格式化时间参数
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

        timeout_ms = 10000 # 10秒超时
        result_dict = {}    # 返回结果字典

        for stock in stock_list:
            try:
                stock_json = {  "id" : cls._get_run_id(),
                                "type": "5",
                                "code": stock,
                                "table_list": field_list,
                                "start_time": start_time,
                                "end_time": end_time}
                json_str = json.dumps(stock_json, ensure_ascii=False)
                json_str = json_str.encode('utf-8')
                ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
                # 检查返回的指针
                if ptr is None or len(ptr) == 0:
                    print(f"获取{stock}股票交易数据失败: 返回空指针")
                    continue

                # 解析JSON数据
                try:
                    data_dict = json.loads(ptr)
                except json.JSONDecodeError as e:
                    print(f"获取{stock}股票交易数据失败: JSON解析错误 - {e}")
                    print(f"原始返回数据: {ptr}")
                    continue

                # 检查错误代码
                if data_dict.get("ErrorId") != "0":
                    print(f"获取{stock}股票交易数据错误: {data_dict.get('Error')}")
                    continue

                result_dict[stock] = data_dict['Data']

            except Exception as e:
                print(f"获取{stock}财务数据异常: {e}")
                import traceback
                traceback.print_exc()
                continue

        return result_dict
    
    @classmethod
    def get_bkjy_value_by_date(cls,
                                stock_list: List[str] = [], 
                                field_list: List[str] = [],  
                                year: int = 0,
                                mmdd: int = 0) -> Dict:
        """获取板块交易数据"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码列表")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        timeout_ms = 10000 # 10秒超时
        result_dict = {}    # 返回结果字典

        for stock in stock_list:
            try:
                stock_json = {  "id" : cls._get_run_id(),
                                "type": "6",
                                "code": stock,
                                "table_list": field_list,
                                "year": year,
                                "mmdd": mmdd}
                json_str = json.dumps(stock_json, ensure_ascii=False)
                json_str = json_str.encode('utf-8')
                ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
                # 检查返回的指针
                if ptr is None or len(ptr) == 0:
                    print(f"获取{stock}股票交易数据失败: 返回空指针")
                    continue

                # 解析JSON数据
                try:
                    data_dict = json.loads(ptr)
                except json.JSONDecodeError as e:
                    print(f"获取{stock}股票交易数据失败: JSON解析错误 - {e}")
                    print(f"原始返回数据: {ptr}")
                    continue

                # 检查错误代码
                if data_dict.get("ErrorId") != "0":
                    print(f"获取{stock}股票交易数据错误: {data_dict.get('Error')}")
                    continue

                result_dict[stock] = data_dict['Data']

            except Exception as e:
                print(f"获取{stock}财务数据异常: {e}")
                import traceback
                traceback.print_exc()
                continue

        return result_dict

    @classmethod
    def get_scjy_value(cls,
                        field_list: List[str] = [], 
                        start_time: str = '', 
                        end_time: str = '') -> Dict:
        """获取市场交易数据"""
        # 初始化连接
        cls._auto_initialize()

        if not end_time:
            end_time = datetime.now().strftime('%Y%m%d%H%M%S')

        # 格式化时间参数
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

        timeout_ms = 10000 # 10秒超时
        try:
            stock_json = {  "id" : cls._get_run_id(),
                            "type": "7",
                            "code": "999999.SH",
                            "table_list": field_list,
                            "start_time": start_time,
                            "end_time": end_time}
            json_str = json.dumps(stock_json, ensure_ascii=False)
            json_str = json_str.encode('utf-8')
            ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
            # 检查返回的指针
            if ptr is None or len(ptr) == 0:
                print(f"获取市场交易数据失败: 返回空指针")
                return {}

            # 解析JSON数据
            try:
                data_dict = json.loads(ptr)
            except json.JSONDecodeError as e:
                print(f"获取市场交易数据失败: JSON解析错误 - {e}")
                return ptr

            # 检查错误代码
            if data_dict.get("ErrorId") != "0":
                print(f"获取市场交易数据错误: {data_dict.get('Error')}")
                return {}

        except Exception as e:
            print(f"获取市场交易数据异常: {e}")
            import traceback
            traceback.print_exc()
        return data_dict['Data']
    
    @classmethod
    def get_scjy_value_by_date(cls,
                                field_list: List[str] = [],  
                                year: int = 0,
                                mmdd: int = 0) -> Dict:
        """获取市场交易数据"""
        # 初始化连接
        cls._auto_initialize()

        timeout_ms = 10000 # 10秒超时
        try:
            stock_json = {  "id" : cls._get_run_id(),
                            "type": "8",
                            "code": "999999.SH",
                            "table_list": field_list,
                            "year": year,
                            "mmdd": mmdd}
            json_str = json.dumps(stock_json, ensure_ascii=False)
            json_str = json_str.encode('utf-8')
            ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
            # 检查返回的指针
            if ptr is None or len(ptr) == 0:
                print(f"获取市场交易数据失败: 返回空指针")
                return {}

            # 解析JSON数据
            try:
                data_dict = json.loads(ptr)
            except json.JSONDecodeError as e:
                print(f"获取市场交易数据失败: JSON解析错误 - {e}")
                return ptr

            # 检查错误代码
            if data_dict.get("ErrorId") != "0":
                print(f"获取市场交易数据错误: {data_dict.get('Error')}")
                return {}

        except Exception as e:
            print(f"获取市场交易数据异常: {e}")
            import traceback
            traceback.print_exc()
        return data_dict['Data']
    
    @classmethod
    def get_gp_one_data(cls,
                        stock_list: List[str] = [], 
                        field_list: List[str] = []) -> Dict:
        """获取股票单个数据"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码列表")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")

        timeout_ms = 10000 # 10秒超时
        result_dict = {}    # 返回结果字典

        for stock in stock_list:
            try:
                stock_json = {  "id" : cls._get_run_id(),
                                "type": "9",
                                "code": stock,
                                "table_list": field_list}
                json_str = json.dumps(stock_json, ensure_ascii=False)
                json_str = json_str.encode('utf-8')
                ptr = dll.GetProDataInStr(cls._get_run_id(),json_str,timeout_ms)
                # 检查返回的指针
                if ptr is None or len(ptr) == 0:
                    print(f"获取{stock}股票交易数据失败: 返回空指针")
                    continue

                # 解析JSON数据
                try:
                    data_dict = json.loads(ptr)
                except json.JSONDecodeError as e:
                    print(f"获取{stock}股票交易数据失败: JSON解析错误 - {e}")
                    print(f"原始返回数据: {ptr}")
                    continue

                # 检查错误代码
                if data_dict.get("ErrorId") != "0":
                    print(f"获取{stock}股票交易数据错误: {data_dict.get('Error')}")
                    continue

                result_dict[stock] = data_dict['Data']

            except Exception as e:
                print(f"获取{stock}财务数据异常: {e}")
                import traceback
                traceback.print_exc()
                continue

        return result_dict
    
    @classmethod
    def get_trading_calendar(cls,
                            market: str,
                            start_time: str,
                            end_time: str) -> List:
        """获取交易日历"""
        # 初始化连接
        cls._auto_initialize()
        
        # 格式化时间参数
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

        marketstr = market.encode('utf-8')
        startimestr = start_time.encode('utf-8')
        endtimestr = end_time.encode('utf-8')
        timeout_ms = 5000
        try:
            ptr = dll.GetTradeCalendarInStr(cls._get_run_id(), marketstr, startimestr, endtimestr, -1, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取交易日历失败: 返回空指针")
                return []
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取交易日历错误: {json_res.get('Error')}")
                return []
            return json_res.get("Date", [])
        except Exception as e:
            print("获取交易日历异常")
            return []
        
    @classmethod
    def get_trading_dates(cls,
                            market: str,
                            start_time: str,
                            end_time: str,
                            count:int = -1) -> List:
        """获取交易日列表"""
        # 初始化连接
        cls._auto_initialize()
        
        # 格式化时间参数
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

        marketstr = market.encode('utf-8')
        startimestr = start_time.encode('utf-8')
        endtimestr = end_time.encode('utf-8')
        timeout_ms = 5000
        try:
            ptr = dll.GetTradeCalendarInStr(cls._get_run_id(), marketstr, startimestr, endtimestr, count, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取交易日历失败: 返回空指针")
                return []
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取交易日历错误: {json_res.get('Error')}")
                return []
            return json_res.get("Date", [])
        except Exception as e:
            print("获取交易日历异常")
            return []

    @classmethod
    def get_stock_list(cls,
                       market = None) -> List:
        """获取股票列表"""
        # 初始化连接
        cls._auto_initialize()

        if not market:
            market = '5'
        marketstr = market.encode('utf-8')
        timeout_ms = 5000

        try:
            ptr = dll.GetStockListInStr(cls._get_run_id(), marketstr, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取股票列表失败: 返回空指针")
                return []
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取股票列表错误: {json_res.get('Error')}")
                return []
            result = [item.replace('.1', '.SH').replace('.0', '.SZ').replace('.2', '.BJ') for item in json_res['Value']]
            return result
        except Exception as e:
            print("获取股票列表异常")
            return []
        

    @classmethod
    def order_stock(cls,
                    account:str, 
                    stock_code:str, 
                    order_type:int, 
                    order_volume:int, 
                    price_type:int, 
                    price:float, 
                    strategy_name:str, 
                    order_remark: str = ''):
        """下单接口 暂无实际功能"""
        # 初始化连接
        cls._auto_initialize()

        # 必填入参检查
        if not account:
            cls.close()
            raise ValueError("必传参数缺失：account不能为空，请提供账户信息")
        if not stock_code:
            cls.close()
            raise ValueError("必传参数缺失：stock_code不能为空，请提供合约代码")
        
        if not check_stock_code_format(stock_code):
            tq.close()
            raise ValueError(f"{stock_code}异常")

        try:
            account_str = account.encode('utf-8') 
            code = stock_code.encode('utf-8')
            if order_remark is not None:
                remark = order_remark.encode('utf-8')

            timeout_ms = 5000
            ptr = dll.SetNewOrder(cls._get_run_id(), account_str, code, order_type, order_volume,
                                price_type, price, remark, timeout_ms)

            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
                data_json = json.loads(result_str)
                if data_json.get("ErrorId") != "0":
                    print(f"下单{stock_code}数据错误: {data_json}")
                    return -1;
                return data_json
            return -1
        except Exception as e:
            print(f"下单{stock_code}数据异常: {e}")
            import traceback
            traceback.print_exc()
            return -1

    @classmethod
    def subscribe_quote(cls, 
                        stock_code: str, 
                        period: str = '1d', 
                        start_time: str = '', 
                        end_time: str = '', 
                        count: int = 0, 
                        dividend_type: Optional[str] = None,  # 改为Optional类型
                        callback = None):
        """订阅单股行情数据回调 暂无实际功能"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_code:
            cls.close()
            raise ValueError("必传参数缺失：stock_code不能为空，请提供合约代码")
        if not period:
            cls.close()
            raise ValueError("必传参数缺失：period不能为空，请指定数据周期（如'1d','1m','tick'等）")
        
        if not check_stock_code_format(stock_code):
            tq.close()
            raise ValueError(f"{stock_code}异常")

        # 时间参数检查：count<0时必须提供起始和结束时间
        if count < 0:
            if not start_time:
                cls.close()
                raise ValueError("必传参数缺失：start_time不能为空，当count<0时必须指定起始时间")
            if not end_time:
                cls.close()
                raise ValueError("必传参数缺失：end_time不能为空，当count<0时必须指定结束时间")

        # 转换时间格式
        if start_time:
            start_time = _convert_time_format(start_time)
        if end_time:
            end_time = _convert_time_format(end_time)

         # 如果未传入dividend_type，默认为'none'
        if dividend_type is None:
            dividend_type = 'none'

        # 转换除权类型
        dividend_type_map = {
            'none': 0,  # 不复权（默认）
            'front': 1,  # 前复权
            'back': 2  # 后复权
        }
        # 统一转为小写处理，增强容错性
        dividend_type_int = dividend_type_map.get(dividend_type.lower(), 0)

        # 判断回调函数是否合法
        if callback is None:
            cls.close()
            raise ValueError("回调函数不能为空，请提供有效的回调函数")

        # 注册外套回调函数
        if cls.m_is_init_data_transfer == False:
            CALLBACK_FUNC_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
            cls.data_transfer = CALLBACK_FUNC_TYPE(cls._data_callback_transfer)
            dll.Register_DataTransferFunc(cls._get_run_id(), cls.data_transfer)
            cls.m_is_init_data_transfer = True

        codestr = stock_code.encode('utf-8')
        startimestr = start_time.encode('utf-8')
        endtimestr = end_time.encode('utf-8')
        periodstr = period.encode('utf-8')

        cls.data_callback_func[cls._get_run_id()][stock_code] = callback
        try:
            timeout_ms = 5000
            ptr = dll.SubscribeGPData(cls._get_run_id(), codestr, startimestr, endtimestr, periodstr, 
            dividend_type_int, count, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                cls.close()
                raise ValueError(f"订阅{stock_code}失败: 返回空指针")
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                cls.close()
                raise ValueError(f"订阅{stock_code}失败: {json_res.get('Error')}")
            return result_str
        except Exception as e:
            cls.close()
            raise ValueError(f"订阅{stock_code}异常")
    
    @classmethod
    def subscribe_hq(cls, 
                     stock_list: List[str] = [], 
                     callback = None):
        """订阅单股行情更新"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")
        
        _sub_hq_update = cls._sub_hq_update
        combined = list(set(cls._sub_hq_update) | set(stock_list))
        cls._sub_hq_update.clear()
        cls._sub_hq_update.extend(combined)
      
        if len( cls._sub_hq_update) > 100:
            cls._sub_hq_update = _sub_hq_update
            tq.close()
            raise ValueError("订阅数大于100")
        
        # 判断回调函数是否合法
        if is_callback_func(callback) == False:
            cls.close()
            raise ValueError("回调函数格式错误，请提供有效的回调函数")

        # 注册外套回调函数
        if cls.m_is_init_data_transfer == False:
            CALLBACK_FUNC_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
            cls.data_transfer = CALLBACK_FUNC_TYPE(cls._data_callback_transfer)
            dll.Register_DataTransferFunc(cls._get_run_id(), cls.data_transfer)
            cls.m_is_init_data_transfer = True

        codestr = ','.join(stock_list)
        codestr = codestr.encode('utf-8')
        try:
            timeout_ms = 5000
            ptr = dll.SubscribeHQDUpdate(cls._get_run_id(), codestr, 0, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print(f"订阅{stock_list}失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"订阅{stock_list}失败: {json_res.get('Error')}")
                return
            # 保存回调函数
            for stock in stock_list:
                cls.data_callback_func[cls._get_run_id()][stock] = callback
            return result_str
        except Exception as e:
            print(f"订阅{stock_list}异常")
            return

    @classmethod
    def unsubscribe_hq(cls, 
                     stock_list: List[str] = []):
        """订阅单股行情更新"""
        # 初始化连接
        cls._auto_initialize()
        # 必填入参检查
        if not stock_list:
            cls.close()
            raise ValueError("必传参数缺失：stock_list不能为空，请提供合约代码")
        
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")
        
        a_set = set(cls._sub_hq_update)
        b_set = set(stock_list)
        _sub_hq_update = cls._sub_hq_update
        cls._sub_hq_update.clear()
        cls._sub_hq_update.extend(a_set - b_set)

        if len( cls._sub_hq_update) > 100:
            cls._sub_hq_update = _sub_hq_update
            tq.close()
            raise ValueError("订阅数大于100")

        
        codestr = ','.join(stock_list)
        codestr = codestr.encode('utf-8')
        try:
            timeout_ms = 5000
            ptr = dll.SubscribeHQDUpdate(cls._get_run_id(), codestr, 1, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print(f"取消订阅{stock_list}失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"取消订阅{stock_list}失败: {json_res.get('Error')}")
                return
            
            #去掉对应保存的回调函数
            for run_id in list(cls.data_callback_func.keys()):  # 用list()避免遍历中修改字典导致的异常
                stock_dict = cls.data_callback_func[run_id]
                # 遍历需要删除的stock，若存在则删除
                for stock in b_set:
                    if stock in stock_dict:
                        del stock_dict[stock]
            return result_str
        except Exception as e:
            return(f"取消订阅{stock_list}异常")
        
    @classmethod
    def get_subscribe_hq_stock_list(cls):
        return cls._sub_hq_update

    @classmethod
    def refresh_cache(cls):
        """刷新缓存行情"""
        # 初始化连接
        cls._auto_initialize()
        try:
            timeout_ms = 60000
            ptr = dll.ReFreshCacheAll(cls._get_run_id(), timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("刷新缓存行情失败: 返回空指针")
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"刷新缓存行情失败: {json_res.get('Error')}")
            return result_str
        except Exception as e:
            return("刷新缓存行情异常")
        
    @classmethod
    def refresh_kline(cls,
                      stock_list: List[str] = [],
                      period: str = ''):
        """刷新K线缓存"""
        if not check_stock_code_format(stock_list):
            tq.close()
            raise ValueError(f"{stock_list}异常")
        cls._auto_initialize()

        # 周期校验
        valid_periods = ['1m', '5m', '1d']
        if period.lower() not in valid_periods:
            tq.close()
            raise ValueError(f'不支持{period},仅支持{valid_periods}')

        code_str = ','.join(stock_list)
        code_str = code_str.encode('utf-8')
        period_str = period.encode('utf-8')
        try:
            timeout_ms = 1000000
            ptr = dll.ReFreshCacheKLine(cls._get_run_id(), code_str, period_str, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("刷新数据缓存失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"刷新K线缓存失败: {json_res.get('Error')}")
                return
            return result_str
        except Exception as e:
            print("刷新数据缓存异常")
        
    @classmethod
    def download_file(cls,
                      stock_code: str = '',
                      down_time:str = '',
                      down_type:int = 1):
        """下载文件（10大股东，ETF申赎数据等）"""
        cls._auto_initialize()

        if not stock_code:
            cls.close()
            raise ValueError("证券代码不能未空")
        if not down_time:
            cls.close()
            raise ValueError("下载日期不能为空")
        
        down_time = _convert_time_format(down_time)
        
        code_str = stock_code.encode('utf-8')
        time_str = down_time.encode('utf-8')
        try:
            timeout_ms = 1000000
            ptr = dll.DownLoadFiles(cls._get_run_id(), code_str, time_str, down_type, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("下载文件失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"下载文件失败: {json_res.get('Error')}")
                return
            return result_str
        except Exception as e:
            print("下载文件异常")
        
    @classmethod
    def create_sector(cls,
                      block_code:str = '',
                      block_name:str = ''):
        '''创建自定义板块'''
        cls._auto_initialize()

        if not block_code:
           print("板块简称不能未空")
           return
        if not block_name:
            print("板块名称不能为空")
            return

        code_str = block_code.encode('utf-8')
        name_str = block_name.encode('utf-8')
        try:
            timeout_ms = 10000
            ptr = dll.UserBlockControl(cls._get_run_id(), 1, code_str, name_str, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("创建板块失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"创建板块失败: {json_res.get('Error')}")
            return result_str
        except Exception as e:
            print("创建板块异常")
        
    @classmethod
    def delete_sector(cls,
                      block_code:str = ''):
        '''删除自定义板块'''
        cls._auto_initialize()

        if not block_code:
            print("板块简称不能未空")
            return
        code_str = block_code.encode('utf-8')
        name_str = 'none'.encode('utf-8')
        try:
            timeout_ms = 10000
            ptr = dll.UserBlockControl(cls._get_run_id(), 2, code_str, name_str, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("删除板块失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"删除板块失败: {json_res.get('Error')}")
            return result_str
        except Exception as e:
            print("删除板块异常")
        
    @classmethod
    def rename_sector(cls,
                      block_code:str = '',
                      block_name:str = ''):
        '''重命名自定义板块'''
        cls._auto_initialize()

        if not block_code:
            print("板块简称不能未空")
            return
        if not block_name:
            print("板块名称不能为空")
            return
        
        code_str = block_code.encode('utf-8')
        name_str = block_name.encode('utf-8')
        try:
            timeout_ms = 10000
            ptr = dll.UserBlockControl(cls._get_run_id(), 3, code_str, name_str, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("重命名板块失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"重命名板块失败: {json_res.get('Error')}")
            return result_str
        except Exception as e:
            print("重命名板块异常")
        
    @classmethod
    def clear_sector(cls,
                      block_code:str = ''):
        '''清空自定义板块'''
        cls._auto_initialize()

        if not block_code:
            print("板块简称不能未空")
            return

        code_str = block_code.encode('utf-8')
        name_str = 'none'.encode('utf-8')
        try:
            timeout_ms = 10000
            ptr = dll.UserBlockControl(cls._get_run_id(), 4, code_str, name_str, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("清空板块失败: 返回空指针")
                return
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"清空板块失败: {json_res.get('Error')}")
            return result_str
        except Exception as e:
            print("清空板块异常")

    @classmethod
    def get_cb_info(cls,
                    stock_code:str = ''):
        '''获取可转债基础信息'''
        cls._auto_initialize()

        if not stock_code:
            cls.close()
            raise ValueError("可转债代码不能为空")

        code_str = stock_code.encode('utf-8')
        try:
            timeout_ms = 10000
            ptr = dll.GetCBINFOInStr(cls._get_run_id(), code_str, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取可转债信息失败: 返回空指针")
                return {}
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取可转债信息失败: {json_res.get('Error')}")
                return {}
            return json_res["Data"][0]
        except Exception as e:
            print("获取可转债信息异常")
            return {}

    @classmethod
    def get_ipo_info(cls,
                    ipo_type:int = 0,
                    ipo_date:int = 0):
        '''获取新股申购信息'''
        cls._auto_initialize()
        try:
            timeout_ms = 10000
            ptr = dll.GetIPOINFOInStr(cls._get_run_id(), ipo_type, ipo_date, timeout_ms)
            if len(ptr) > 0:
                result_str = ptr.decode('utf-8')
            else:
                print("获取新股申购信息失败: 返回空指针")
                return []
            json_res = json.loads(result_str)
            if json_res.get("ErrorId") != "0":
                print(f"获取新股申购信息失败: {json_res.get('Error')}")
                return []
            return json_res["Data"]
        except Exception as e:
            print("获取新股申购信息异常")
            return []
        


