"""
财务数据集成模块 - 使用akshare

整合通达信行情数据 + akshare财务数据
"""

import pandas as pd
from typing import List, Optional, Dict
from datetime import datetime


class FinancialDataClient:
    """财务数据客户端 - 使用akshare"""

    def __init__(self):
        """初始化客户端"""
        try:
            import akshare as ak
            self.ak = ak
            self.available = True
        except ImportError:
            self.available = False
            print("[WARNING] 未安装akshare，请运行: pip install akshare")

    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取个股基本信息

        Args:
            symbol: 股票代码，不带后缀，如 '000001'

        Returns:
            Dict: 基本信息
        """
        if not self.available:
            raise ImportError("请先安装akshare: pip install akshare")

        info = self.ak.stock_individual_info_em(symbol=symbol)

        # 转换为字典格式
        result = {}
        for _, row in info.iterrows():
            result[row['item']] = row['value']

        return result

    def get_financial_indicator(self, symbol: str) -> pd.DataFrame:
        """
        获取财务指标

        Args:
            symbol: 股票代码，如 '000001'

        Returns:
            pd.DataFrame: 财务指标数据
        """
        if not self.available:
            raise ImportError("请先安装akshare: pip install akshare")

        df = self.ak.stock_financial_analysis_indicator_em(symbol=symbol)
        return df

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """
        获取资产负债表

        Args:
            symbol: 股票代码

        Returns:
            pd.DataFrame: 资产负债表
        """
        if not self.available:
            raise ImportError("请先安装akshare: pip install akshare")

        df = self.ak.stock_balance_sheet_by_em(symbol=symbol)
        return df

    def get_profit_sheet(self, symbol: str) -> pd.DataFrame:
        """
        获取利润表

        Args:
            symbol: 股票代码

        Returns:
            pd.DataFrame: 利润表
        """
        if not self.available:
            raise ImportError("请先安装akshare: pip install akshare")

        df = self.ak.stock_profit_sheet_by_em(symbol=symbol)
        return df

    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        """
        获取现金流量表

        Args:
            symbol: 股票代码

        Returns:
            pd.DataFrame: 现金流量表
        """
        if not self.available:
            raise ImportError("请先安装akshare: pip install akshare")

        df = self.ak.stock_cash_flow_sheet_by_em(symbol=symbol)
        return df

    def get_financial_abstract(self, symbol: str) -> pd.DataFrame:
        """
        获取财务摘要

        Args:
            symbol: 股票代码

        Returns:
            pd.DataFrame: 财务摘要
        """
        if not self.available:
            raise ImportError("请先安装akshare: pip install akshare")

        df = self.ak.stock_financial_abstract(symbol=symbol)
        return df

    def get_key_ratios(self, symbol: str) -> Dict:
        """
        获取关键财务指标（最新一期）

        Args:
            symbol: 股票代码

        Returns:
            Dict: 关键指标
        """
        if not self.available:
            raise ImportError("请先安装akshare: pip install akshare")

        df = self.get_financial_indicator(symbol)

        if df.empty:
            return {}

        # 获取最新一期数据
        latest = df.iloc[-1]

        # 提取关键指标
        key_fields = {
            '报告期': 'report_date',
            '净资产收益率': 'roe',
            '总资产净利率': 'roa',
            '毛利率': 'gross_margin',
            '净利率': 'net_margin',
            '资产负债率': 'debt_ratio',
            '流动比率': 'current_ratio',
            '速动比率': 'quick_ratio',
        }

        result = {}
        for name, field in key_fields.items():
            if field in latest:
                result[name] = latest[field]

        return result


def convert_tdx_to_akshare_code(tdx_code: str) -> str:
    """
    将通达信代码格式转换为akshare格式

    Examples:
        '000001.SZ' -> '000001'
        '600519.SH' -> '600519'

    Args:
        tdx_code: 通达信格式的代码

    Returns:
        str: akshare格式的代码
    """
    return tdx_code.split('.')[0]


def convert_akshare_to_tdx_code(ak_code: str, market: str = 'SZ') -> str:
    """
    将akshare代码格式转换为通达信格式

    Args:
        ak_code: akshare格式的代码（6位数字）
        market: 市场代码，'SZ' 或 'SH'

    Returns:
        str: 通达信格式的代码
    """
    return f"{ak_code}.{market}"


def get_combined_data(
    tdx_codes: List[str],
    start_time: str,
    include_financial: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    获取综合数据：行情数据 + 财务数据

    Args:
        tdx_codes: 通达信格式的股票代码列表
        start_time: 开始时间
        include_financial: 是否包含财务数据

    Returns:
        Dict: {
            'market_data': 行情DataFrame,
            'financial_data': {股票代码: 财务数据}
        }
    """
    from easy_xt.tdx_client import TdxClient

    result = {
        'market_data': None,
        'financial_data': {}
    }

    # 1. 获取行情数据（通达信）
    with TdxClient() as tdx:
        market_data = tdx.get_market_data(
            stock_list=tdx_codes,
            start_time=start_time,
            period='1d'
        )
        result['market_data'] = market_data

    # 2. 获取财务数据（akshare）
    if include_financial:
        client = FinancialDataClient()

        for tdx_code in tdx_codes:
            try:
                ak_code = convert_tdx_to_akshare_code(tdx_code)
                financial = client.get_key_ratios(ak_code)
                result['financial_data'][tdx_code] = financial
            except Exception as e:
                print(f"获取{tdx_code}财务数据失败: {e}")
                result['financial_data'][tdx_code] = {}

    return result


# 快捷函数
def get_stock_financial_quick(tdx_code: str) -> Dict:
    """
    快捷函数：获取单只股票的财务数据

    Args:
        tdx_code: 通达信格式代码，如 '000001.SZ'

    Returns:
        Dict: 财务数据
    """
    client = FinancialDataClient()
    ak_code = convert_tdx_to_akshare_code(tdx_code)
    return client.get_key_ratios(ak_code)


if __name__ == "__main__":
    """测试代码"""
    print("="*70)
    print("  测试财务数据集成模块")
    print("="*70)

    # 测试1: 获取个股信息
    print("\n[测试1] 获取个股基本信息...")
    try:
        client = FinancialDataClient()

        info = client.get_stock_info('000001')
        print("[OK] 成功!")
        print(f"  股票名称: {info.get('股票名称')}")
        print(f"  总股本: {info.get('总股本')}")
        print(f"  流通股: {info.get('流通股')}")
        print(f"  总市值: {info.get('总市值')}")

    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试2: 获取财务指标
    print("\n[测试2] 获取财务指标...")
    try:
        df = client.get_financial_indicator('000001')
        if not df.empty:
            print("[OK] 成功!")
            print(f"  数据形状: {df.shape}")
            print(f"\n  最新财务指标:")
            print(df.tail(3).to_string(max_cols=10))
        else:
            print("[FAIL] 数据为空")

    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试3: 获取关键指标
    print("\n[测试3] 获取关键财务指标...")
    try:
        ratios = client.get_key_ratios('000001')
        print("[OK] 成功!")
        for key, value in ratios.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试4: 综合数据
    print("\n[测试4] 获取综合数据（行情+财务）...")
    try:
        data = get_combined_data(
            tdx_codes=['000001.SZ', '600519.SH'],
            start_time='20240101',
            include_financial=True
        )

        print("[OK] 成功!")
        print(f"  行情数据形状: {data['market_data'].shape}")
        print(f"  财务数据:")
        for code, financial in data['financial_data'].items():
            print(f"    {code}: {len(financial)} 个指标")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("  测试完成!")
    print("="*70)
