"""
股票类型预设配置 - 动态从QMT获取真实数据
"""
from typing import List, Dict, Any, Optional
import sys
import os

# 添加项目路径（尝试多个可能的路径）
current_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(current_dir, '..', '..', '..'),  # 从src/workflow向上三级
    os.path.abspath('../..'),  # 从当前目录向上两级
    os.path.abspath('.'),  # 当前目录
    os.path.dirname(current_dir),  # 从src/workflow到src
]

for path in possible_paths:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# 导入 EasyXT - 添加详细的错误信息
EASYXT_AVAILABLE = False
EasyXT = None

try:
    from easy_xt import EasyXT
    EASYXT_AVAILABLE = True
    print("[INFO] EasyXT模块导入成功")
except ImportError as e:
    print(f"[DEBUG] EasyXT导入失败 (ImportError): {e}")
    # 尝试从其他路径导入
    try:
        import importlib.util
        # 尝试从父目录导入
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        easyxt_path = os.path.join(parent_dir, 'easy_xt')
        if os.path.exists(easyxt_path):
            spec = importlib.util.spec_from_file_location("easy_xt", os.path.join(easyxt_path, '__init__.py'))
            easyxt_module = importlib.util.module_from_spec(spec)
            sys.modules['easy_xt'] = easyxt_module
            spec.loader.exec_module(easyxt_module)
            from easy_xt import EasyXT
            EASYXT_AVAILABLE = True
            print("[INFO] EasyXT从备用路径导入成功")
    except Exception as e2:
        print(f"[DEBUG] 备用导入也失败: {e2}")
        EASYXT_AVAILABLE = False
except Exception as e:
    print(f"[DEBUG] EasyXT导入失败 (其他错误): {e}")
    EASYXT_AVAILABLE = False


def _get_real_stock_list(sector: Optional[str], fallback: List[str], limit: int = None) -> List[str]:
    """
    从EasyXT获取真实股票列表

    Args:
        sector: 板块名称，如'沪深300', '中证500'等；None表示获取所有A股（沪A+深A）
        fallback: 获取失败时的备用列表
        limit: 限制返回的股票数量，None表示不限制

    Returns:
        List[str]: 股票代码列表
    """
    if not EASYXT_AVAILABLE:
        print(f"[DEBUG] EasyXT不可用，使用备用列表（{len(fallback)}只）")
        return fallback[:limit] if limit else fallback

    try:
        print(f"[DEBUG] 尝试从EasyXT获取板块: {sector if sector else '所有A股'}")

        # 创建EasyXT实例（只创建一次）
        if not hasattr(_get_real_stock_list, '_easyxt_instance'):
            _get_real_stock_list._easyxt_instance = EasyXT()
            # 初始化数据服务
            result = _get_real_stock_list._easyxt_instance.init_data()
            print(f"[DEBUG] EasyXT初始化{'成功' if result else '失败'}")

        easyxt = _get_real_stock_list._easyxt_instance

        # 获取股票列表
        stock_list = easyxt.get_stock_list(sector)

        if stock_list:
            print(f"[DEBUG] 从EasyXT获取到 {len(stock_list)} 只股票")
            if limit:
                return stock_list[:limit]
            return stock_list
        else:
            print(f"[WARNING] EasyXT返回空列表，使用备用列表")
            return fallback[:limit] if limit else fallback

    except Exception as e:
        print(f"[WARNING] 从EasyXT获取股票列表失败: {e}")
        print(f"[DEBUG] 使用备用列表（{len(fallback)}只）")
        return fallback[:limit] if limit else fallback


# 沪深300成分股（前100只权重股，按权重排序）
HS300_FALLBACK = [
    '600519.SH', '000858.SZ', '600036.SH', '000002.SZ', '601318.SH',
    '600030.SH', '000333.SZ', '600276.SH', '000001.SZ', '600000.SH',
    '601166.SH', '600900.SH', '000725.SZ', '600009.SH', '601888.SH',
    '002594.SZ', '600031.SH', '000651.SZ', '601012.SH', '300750.SZ',
    '600887.SH', '002475.SZ', '601390.SH', '000063.SZ', '600585.SH',
    '601668.SH', '600029.SH', '601111.SH', '000100.SZ', '601888.SH',
    '600309.SH', '600036.SH', '000333.SZ', '601318.SH', '000858.SZ',
    '600519.SH', '601012.SH', '300750.SZ', '002594.SZ', '600030.SH',
    '600276.SH', '000001.SZ', '000002.SZ', '600000.SH', '601166.SH',
    '600900.SH', '000725.SZ', '600009.SH', '600031.SH', '000651.SZ',
    '600887.SH', '002475.SZ', '601390.SH', '000063.SZ', '600585.SH',
    '601668.SH', '600029.SH', '601111.SH', '000100.SZ', '600309.SH',
    '601628.SH', '600837.SH', '002304.SZ', '601601.SH', '600104.SH',
    '601988.SH', '601398.SH', '601288.SH', '600000.SH', '601328.SH',
    '601857.SH', '601088.SH', '600547.SH', '600570.SH', '002352.SZ',
    '600016.SH', '600048.SH', '000568.SZ', '601888.SH', '601138.SH',
    '002415.SZ', '600015.SH', '600690.SH', '000651.SZ', '601888.SH',
    '601766.SH', '601788.SH', '600398.SH', '002142.SZ', '601985.SH',
    '601818.SH', '601939.SH', '601658.SH', '601688.SH', '601998.SH'
]

# 中证500成分股（前100只）
ZZ500_FALLBACK = [
    '600585.SH', '601668.SH', '600029.SH', '601111.SH', '000063.SZ',
    '002475.SZ', '300014.SZ', '601888.SH', '600309.SH', '000100.SZ',
    '002304.SZ', '601601.SH', '600104.SH', '601988.SH', '601398.SH',
    '601288.SH', '600690.SH', '000568.SZ', '601138.SH', '002415.SZ',
    '600015.SH', '601766.SH', '601788.SH', '600398.SH', '002142.SZ',
    '601985.SH', '601818.SH', '601939.SH', '601658.SH', '601688.SH',
    '601998.SH', '601816.SH', '601727.SH', '002459.SZ', '600048.SH',
    '600406.SH', '601877.SH', '601018.SH', '601928.SH', '600104.SH',
    '000778.SZ', '600875.SH', '002459.SZ', '601888.SH', '600011.SH',
    '600048.SH', '000063.SZ', '002475.SZ', '601601.SH', '601668.SH'
]

# 创业板成分股（前100只）
CYB_FALLBACK = [
    '300750.SZ', '300059.SZ', '300015.SZ', '300142.SZ', '300413.SZ',
    '300274.SZ', '300760.SZ', '300124.SZ', '300003.SZ', '300002.SZ',
    '300014.SZ', '300017.SZ', '300033.SZ', '300037.SZ', '300042.SZ',
    '300058.SZ', '300059.SZ', '300070.SZ', '300072.SZ', '300073.SZ',
    '300095.SZ', '300103.SZ', '300113.SZ', '300122.SZ', '300124.SZ',
    '300133.SZ', '300142.SZ', '300144.SZ', '300146.SZ', '300159.SZ',
    '300166.SZ', '300168.SZ', '300177.SZ', '300182.SZ', '300188.SZ',
    '300197.SZ', '300207.SZ', '300209.SZ', '300212.SZ', '300223.SZ',
    '300233.SZ', '300244.SZ', '300251.SZ', '300253.SZ', '300257.SZ',
    '300267.SZ', '300274.SZ', '300285.SZ', '300296.SZ', '300298.SZ',
    '300302.SZ', '300308.SZ', '310259.SZ', '300272.SZ', '300284.SZ',
    '300295.SZ', '300303.SZ', '300315.SZ', '300316.SZ', '300318.SZ',
    '300326.SZ', '300327.SZ', '300331.SZ', '300347.SZ', '300363.SZ',
    '300367.SZ', '300368.SZ', '300373.SZ', '300376.SZ', '300377.SZ',
    '300394.SZ', '300395.SZ', '300398.SZ', '300408.SZ', '300413.SZ',
    '300415.SZ', '300418.SZ', '300433.SZ', '300450.SZ', '300454.SZ',
    '300457.SZ', '300462.SZ', '300463.SZ', '300475.SZ', '300474.SZ',
    '300482.SZ', '300485.SZ', '300487.SZ', '300496.SZ', '300498.SZ',
    '300502.SZ', '300511.SZ', '300517.SZ', '300521.SZ', '300529.SZ',
    '300540.SZ', '300568.SZ', '300570.SZ', '300576.SZ', '300595.SZ'
]

# 常见股票类型预设配置
# 使用动态获取的函数，而不是静态列表
STOCK_PRESETS = {
    '📈 沪深300': {
        'sector': '沪深300',  # 从EasyXT获取的板块名称
        'limit': None,  # 不限制数量，获取全部300只
        'fallback': HS300_FALLBACK,  # 扩展的备用列表（100只）
        'description': '沪深300指数成分股（从QMT动态获取）',
        'tag': 'market_index',
        'dynamic': True  # 标记为动态获取
    },
    '🏭 沪深A股（小）': {
        'sector': None,  # None表示获取所有A股
        'limit': 100,
        'fallback': HS300_FALLBACK[:100],
        'description': '沪深A股市场（前100只，快速测试）',
        'tag': 'market_index',
        'dynamic': True
    },
    '🏭 沪深A股（中）': {
        'sector': None,
        'limit': 500,
        'fallback': HS300_FALLBACK + ZZ500_FALLBACK[:200],
        'description': '沪深A股市场（前500只，常规分析）',
        'tag': 'market_index',
        'dynamic': True
    },
    '🏭 沪深A股（大）': {
        'sector': None,
        'limit': 1000,
        'fallback': HS300_FALLBACK + ZZ500_FALLBACK + CYB_FALLBACK[:300],
        'description': '沪深A股市场（前1000只，深度分析）',
        'tag': 'market_index',
        'dynamic': True
    },
    '🚀 创业板': {
        'sector': '创业板',
        'limit': 100,
        'fallback': CYB_FALLBACK[:100],
        'description': '创业板市场（前100只）',
        'tag': 'growth_market',
        'dynamic': True
    },
    '🏢 科创板': {
        'sector': '科创板',
        'limit': 100,
        'fallback': [
            '688981.SH', '688111.SH', '688036.SH', '688187.SH', '688223.SH',
            '688599.SH', '688363.SH', '688169.SH', '688019.SH', '688012.SH',
            '688981.SH', '688077.SH', '688078.SH', '688099.SH', '688106.SH',
            '688126.SH', '688166.SH', '688168.SH', '688169.SH', '688180.SH',
            '688187.SH', '688192.SH', '688198.SH', '688202.SH', '688208.SH',
            '688223.SH', '688233.SH', '688256.SH', '688258.SH', '688280.SH',
            '688298.SH', '688308.SH', '688328.SH', '688333.SH', '688363.SH',
            '688368.SH', '688396.SH', '688399.SH', '688400.SH', '688408.SH',
            '688410.SH', '688433.SH', '688456.SH', '688466.SH', '688488.SH',
            '688498.SH', '688499.SH', '688500.SH', '688508.SH', '688521.SH',
            '688528.SH', '688533.SH', '688556.SH', '688561.SH', '688568.SH',
            '688575.SH', '688577.SH', '688579.SH', '688588.SH', '688590.SH',
            '688592.SH', '6bb599.SH', '688605.SH', '688616.SH', '688618.SH',
            '688621.SH', '688630.SH', '688639.SH', '688646.SH', '688648.SH',
            '688668.SH', '688680.SH', '688686.SH', '688699.SH', '688702.SH',
            '688708.SH', '688715.SH', '688726.SH', '688728.SH', '688736.SH',
            '688739.SH', '688766.SH', '688767.SH', '688772.SH', '6bb788.SH',
            '688798.SH', '688800.SH', '688811.SH', '688819.SH', '688828.SH',
            '688836.SH', '688846.SH', '688862.SH', '688866.SH', '688868.SH',
            '688880.SH', '688898.SH', '688901.SH', '688911.SH', '688915.SH',
            '688919.SH', '688925.SH', '688928.SH', '688929.SH', '688935.SH',
            '688939.SH', '688945.SH', '688950.SH', '688956.SH', '688958.SH',
            '688961.SH', '688966.SH', '688969.SH', '688977.SH', '688980.SH',
            '688981.SH', '688988.SH', '688987.SH', '688995.SH', '688999.SH'
        ],
        'description': '科创板市场（前100只）',
        'tag': 'growth_market',
        'dynamic': True
    },
    '🔺 中证500': {
        'sector': '中证500',
        'limit': None,  # 获取全部500只
        'fallback': ZZ500_FALLBACK,
        'description': '中证500指数成分股（从QMT动态获取）',
        'tag': 'market_index',
        'dynamic': True
    },
    '📥 中证1000': {
        'sector': '中证1000',
        'limit': 200,  # 限制200只
        'fallback': ZZ500_FALLBACK + HS300_FALLBACK[:100],
        'description': '中证1000指数成分股（前200只）',
        'tag': 'market_index',
        'dynamic': True
    },
    '🏆 新能源精选': {
        'sector': None,  # 不使用动态获取，使用静态列表
        'symbols': [  # 静态列表
            '300750.SZ', '002594.SZ', '601012.SH', '300274.SZ', '688223.SH',
            '688599.SH', '002475.SZ', '300014.SZ', '300124.SZ', '002129.SZ',
        ],
        'description': '新能源精选股票（10只）',
        'tag': 'new_energy',
        'dynamic': False
    },
    '💰 银行板块': {
        'sector': None,
        'symbols': [
            '600036.SH', '600000.SH', '601166.SH', '601398.SH', '601288.SH',
            '600016.SH', '002142.SZ', '601166.SH', '600015.SH', '601988.SH'
        ],
        'description': '银行板块精选（10只）',
        'tag': 'sector',
        'dynamic': False
    },
    '🏥 医药板块': {
        'sector': None,
        'symbols': [
            '000001.SZ', '600276.SH', '000661.SZ', '600521.SH', '603259.SH',
            '300015.SZ', '300003.SZ', '300347.SZ', '002821.SZ', '300760.SZ'
        ],
        'description': '医药板块精选（10只）',
        'tag': 'sector',
        'dynamic': False
    }
}


def get_preset_configs() -> List[Dict[str, Any]]:
    """
    获取所有预设配置

    Returns:
        List[Dict]: [{name, symbols, description}, tag}]
    """
    configs = []
    for name, config in STOCK_PRESETS.items():
        config_dict = {
            'name': name,
            **config
        }
        configs.append(config_dict)
    return configs


def get_preset_symbols(name: str) -> List[str]:
    """
    根据预设名称获取股票代码

    Args:
        name: 预设名称，如 '📈 沪深300'

    Returns:
        List[str]: 股票代码列表
    """
    print(f"[DEBUG] get_preset_symbols 被调用，name={name}")

    if name not in STOCK_PRESETS:
        raise ValueError(f"未知的预设类型: {name}")

    config = STOCK_PRESETS[name]
    print(f"[DEBUG] config={config}")

    # 检查是否是动态配置
    if config.get('dynamic', False):
        print(f"[DEBUG] 使用动态获取模式")
        # 动态获取
        sector = config.get('sector')
        fallback = config.get('fallback', [])
        limit = config.get('limit')

        print(f"[DEBUG] sector={sector}, fallback长度={len(fallback)}, limit={limit}")

        # sector为None时传入None，让EasyXT自动获取沪A+深A
        # sector有值时传入具体的板块名称
        sector_param = sector  # 保持原样，None就传None
        print(f"[DEBUG] 调用 _get_real_stock_list({repr(sector_param)}, fallback, {limit})")
        result = _get_real_stock_list(sector_param, fallback, limit)

        print(f"[DEBUG] 动态获取返回 {len(result)} 只股票")
        return result

    # 静态配置，直接返回 symbols
    print(f"[DEBUG] 使用静态模式")
    if 'symbols' in config:
        result = config['symbols']
        print(f"[DEBUG] 静态symbols返回 {len(result)} 只股票")
        return result
    elif 'symbol_list' in config:
        # 兼容旧格式
        suffix = config.get('symbol_suffix', '')
        result = [f"{s}{suffix}" for s in config['symbol_list']]
        print(f"[DEBUG] 静态symbol_list返回 {len(result)} 只股票")
        return result
    else:
        raise ValueError(f"预设 {name} 不包含股票数据")


# 预设类型列表
PRESET_LIST = list(STOCK_PRESETS.keys())
