"""
通达信量化数据客户端
支持在任意位置调用通达信量化接口，无需将代码放到通达信安装目录

使用方法：
    from easy_xt.tdx_client import TdxClient

    # 初始化客户端
    client = TdxClient()

    # 获取行情数据
    df = client.get_market_data(
        stock_list=['605168.SH', '000333.SZ'],
        start_time='20250101',
        period='1d'
    )

    # 获取财务数据
    df = client.get_financial_data(
        stock_list=['000001.SZ'],
        fields=['净资产收益率', '市盈率']
    )

    # 获取板块成分股
    stocks = client.get_sector_stocks('CSBK')

    # 关闭连接
    client.close()
"""

import sys
import pandas as pd
from pathlib import Path
from typing import List, Optional, Union, Dict


class TdxClient:
    """通达信量化数据客户端"""

    def __init__(self, tdx_user_path: Optional[str] = None):
        """
        初始化通达信客户端

        Args:
            tdx_user_path: 通达信user插件目录路径，如果为None则自动查找
        """
        # 查找通达信user目录
        self.tdx_user_path = self._find_tdx_user_path(tdx_user_path)

        # 添加到sys.path
        if self.tdx_user_path not in sys.path:
            sys.path.insert(0, str(self.tdx_user_path))

        # 导入通达信接口模块
        try:
            from tqcenter import tq
            self.tq = tq
            # 初始化
            tq.initialize(__file__)
            print(f"[OK] 通达信客户端初始化成功")
            print(f"  插件路径: {self.tdx_user_path}")
        except ImportError as e:
            raise ImportError(
                f"无法导入tqcenter模块，请检查通达信安装路径是否正确。\n"
                f"当前路径: {self.tdx_user_path}\n"
                f"错误信息: {e}"
            )

    def _find_tdx_user_path(self, custom_path: Optional[str] = None) -> Path:
        """
        查找通达信user插件目录

        优先级：
        1. 用户指定的路径
        2. 项目根目录下的PYPlugins/user（项目本地插件，推荐）
        3. 通达信安装目录（仅作备用）

        Returns:
            Path: user目录的路径
        """
        if custom_path:
            return Path(custom_path)

        # 当前项目根目录的PYPlugins/user（优先使用项目本地插件）
        # tdx_client.py 位于 easy_xt/tdx_client.py
        # parents[0] = easy_xt
        # parents[1] = 项目根目录
        project_root = Path(__file__).resolve().parents[1]
        project_user_path = project_root / "PYPlugins" / "user"

        print(f"[DEBUG] 项目根目录: {project_root}")
        print(f"[DEBUG] 查找项目插件: {project_user_path}")

        if project_user_path.exists():
            print(f"[OK] 使用项目本地通达信插件: {project_user_path}")
            return project_user_path

        # 常见安装位置（优先使用通达信安装目录）
        print("[INFO] 查找通达信安装目录...")
        common_paths = [
            Path("D:/new_tdx64.2/PYPlugins"),      # 用户当前使用的通达信
            Path("D:/new_tdx64/PYPlugins"),        # 备选通达信路径
            Path("H:/new_tdx64/PYPlugins/user"),
            Path("C:/new_tdx64/PYPlugins/user"),
            Path("E:/new_tdx64/PYPlugins/user"),
        ]

        for path in common_paths:
            if path.exists():
                print(f"[OK] 使用通达信安装目录: {path}")
                return path

        # 如果通达信安装目录不存在，尝试项目本地插件
        print("[INFO] 通达信安装目录不存在，尝试项目本地插件...")
        project_user_path = project_root / "PYPlugins" / "user"

        if project_user_path.exists():
            print(f"[OK] 使用项目本地插件: {project_user_path}")
            return project_user_path

        raise FileNotFoundError(
            "找不到通达信user插件目录！\n"
            f"请确认项目目录 {project_user_path} 存在\n"
            "或者手动指定路径：TdxClient(tdx_user_path='你的路径/PYPlugins/user')"
        )

    def get_market_data(
        self,
        stock_list: List[str],
        start_time: str,
        end_time: str = "",
        count: int = -1,
        dividend_type: str = "front",
        period: str = "1d",
        fill_data: bool = False,
        field_list: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取行情数据

        Args:
            stock_list: 股票列表，如 ['605168.SH', '000333.SZ']
            start_time: 开始时间，格式 '20250101'
            end_time: 结束时间，格式 '20250131'，为空表示到最新
            count: 数据条数，-1表示全部
            dividend_type: 复权类型 'front'=前复权 'none'=不复权 'back'=后复权
            period: 周期 '1d'=日线 '1wk'=周线 '1min'=1分钟 '5min'=5分钟
            fill_data: 是否填充数据
            field_list: 字段列表

        Returns:
            pd.DataFrame: 行情数据
        """
        if field_list is None:
            field_list = []

        data = self.tq.get_market_data(
            field_list=field_list,
            stock_list=stock_list,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type=dividend_type,
            period=period,
            fill_data=fill_data
        )

        # 转换为DataFrame
        return self._data_to_df(data)

    def get_financial_data(
        self,
        stock_list: List[str],
        field_list: List[str],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        report_type: str = "report_time"
    ) -> pd.DataFrame:
        """
        获取财务数据

        Args:
            stock_list: 股票列表
            field_list: 财务指标字段，如 ['净资产收益率', '市盈率', '营业总收入']
            start_time: 开始时间
            end_time: 结束时间
            report_type: 报表类型，默认'report_time'

        Returns:
            pd.DataFrame: 财务数据
        """
        data = self.tq.get_financial_data(
            stock_list=stock_list,
            field_list=field_list,
            start_time=start_time or '',
            end_time=end_time or '',
            report_type=report_type
        )

        return self._data_to_df(data)

    def get_sector_stocks(
        self,
        sector_name: str,
        block_type: int = 1
    ) -> List[str]:
        """
        获取板块成分股

        Args:
            sector_name: 板块名称或代码（如：'880081.SH' 或 '自选股'）
            block_type: 板块类型，1=自定义板块，2=行业板块等（已废弃，保留兼容性）

        Returns:
            List[str]: 股票代码列表

        注意:
            1. 通达信API只需要传入板块代码/名称
            2. 可以通过 get_sector_list() 获取所有可用板块代码
            3. 可以通过 get_user_sector() 获取用户自定义板块
            4. 返回空列表通常表示板块不存在或板块中没有股票
        """
        # API只需要block_code参数，不需要block_type
        result = self.tq.get_stock_list_in_sector(sector_name)

        # 解析返回结果
        if isinstance(result, dict) and 'stocks' in result:
            return result['stocks']
        elif isinstance(result, list):
            return result
        else:
            return []

    def get_stock_info(self, stock_code: str) -> Dict:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码，如 '000001.SZ'

        Returns:
            Dict: 股票信息
        """
        return self.tq.get_stock_info(stock_code)

    def get_block_list(self, block_type: int = 1) -> List[Dict]:
        """
        获取板块列表

        Args:
            block_type: 板块类型（已废弃，API已变更）

        Returns:
            List[Dict]: 板块列表

        注意:
            推荐使用 get_sector_list() 方法替代
        """
        # 新API使用 get_sector_list()
        return self.tq.get_sector_list()

    def get_sector_list(self) -> List[str]:
        """
        获取所有板块列表

        Returns:
            List[str]: 板块代码列表，如 ['880081.SH', '880082.SH', ...]
        """
        result = self.tq.get_sector_list()
        return result if isinstance(result, list) else []

    def get_user_sector(self) -> List[str]:
        """
        获取用户自定义板块列表

        Returns:
            List[str]: 用户自定义板块名称列表

        注意:
            返回用户在通达信中创建的自定义板块
            如果返回空列表，说明用户还没有创建自定义板块
        """
        result = self.tq.get_user_sector()
        return result if isinstance(result, list) else []

    def _data_to_df(self, data: Dict) -> pd.DataFrame:
        """
        将tq.get_market_data返回的dict转换为DataFrame格式

        Args:
            data: 通达信返回的字典数据

        Returns:
            pd.DataFrame: 转换后的数据框
        """
        if not data or not isinstance(data, dict):
            return pd.DataFrame()

        try:
            # 合并所有股票的数据
            combined = pd.concat(data.values(), keys=data.keys(), axis=0)
            # 转换为DataFrame
            df = combined.stack().unstack(level=0).reset_index()
            df.columns.name = None
            df.rename(columns={'level_0': 'Date', 'level_1': 'Symbol'}, inplace=True)
            return df
        except Exception as e:
            print(f"数据转换失败: {e}")
            return pd.DataFrame()

    def close(self):
        """关闭连接"""
        if hasattr(self, 'tq'):
            self.tq.close()
            print("[OK] 通达信客户端已关闭")

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()


# 快捷函数
def get_tdx_data(
    stock_list: List[str],
    start_time: str,
    end_time: str = "",
    period: str = "1d",
    dividend_type: str = "front"
) -> pd.DataFrame:
    """
    快捷函数：获取通达信行情数据

    Args:
        stock_list: 股票列表
        start_time: 开始时间
        end_time: 结束时间
        period: 周期
        dividend_type: 复权类型

    Returns:
        pd.DataFrame: 行情数据
    """
    with TdxClient() as client:
        return client.get_market_data(
            stock_list=stock_list,
            start_time=start_time,
            end_time=end_time,
            period=period,
            dividend_type=dividend_type
        )


if __name__ == "__main__":
    # 测试代码
    print("=== 测试通达信数据客户端 ===\n")

    # 测试1: 初始化客户端
    print("【测试1】初始化客户端")
    client = TdxClient()
    print()

    # 测试2: 获取行情数据
    print("【测试2】获取行情数据")
    df = client.get_market_data(
        stock_list=['605168.SH', '000333.SZ'],
        start_time='20250101',
        period='1d',
        count=10
    )
    print(f"数据形状: {df.shape}")
    print(f"数据列: {df.columns.tolist()}")
    print(f"\n前5行数据:")
    print(df.head())
    print()

    # 测试3: 获取板块成分股
    print("【测试3】获取板块成分股")
    try:
        stocks = client.get_sector_stocks('CSBK', block_type=1)
        print(f"板块股票数量: {len(stocks) if isinstance(stocks, list) else 'N/A'}")
        if isinstance(stocks, list) and len(stocks) > 0:
            print(f"前5只股票: {stocks[:5]}")
    except Exception as e:
        print(f"获取板块数据失败: {e}")
    print()

    # 测试4: 获取财务数据
    print("【测试4】获取财务数据")
    try:
        fin_df = client.get_financial_data(
            stock_list=['000001.SZ'],
            fields=['净资产收益率', '市盈率', '营业总收入'],
            report_type='年报'
        )
        print(f"财务数据形状: {fin_df.shape}")
        if not fin_df.empty:
            print(f"\n财务数据:")
            print(fin_df.head())
    except Exception as e:
        print(f"获取财务数据失败: {e}")
    print()

    # 关闭连接
    client.close()
