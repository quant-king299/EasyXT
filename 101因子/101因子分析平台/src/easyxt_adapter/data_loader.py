"""
EasyXT数据适配器
负责将EasyXT的数据格式转换为因子引擎所需的标准格式
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
import sys
import os

# 获取当前文件的目录结构
current_file_dir = os.path.dirname(os.path.abspath(__file__))  # src/easyxt_adapter
src_dir = os.path.dirname(current_file_dir)  # src
project_dir = os.path.dirname(src_dir)  # 101因子分析平台
# 101因子 (注意：项目名称包含中文"101因子")
parent_of_project = os.path.dirname(project_dir)  # 101因子
workspace_dir = os.path.dirname(parent_of_project)  # miniqmt扩展

# 打印路径以便调试
print(f"[DEBUG] current_file_dir: {current_file_dir}")
print(f"[DEBUG] src_dir: {src_dir}")
print(f"[DEBUG] project_dir: {project_dir}")
print(f"[DEBUG] workspace_dir: {workspace_dir}")
print(f"[DEBUG] easy_xt应位于: {os.path.join(workspace_dir, 'easy_xt')}")

# 检查easy_xt模块是否存在
easy_xt_path = os.path.join(workspace_dir, 'easy_xt')
if os.path.exists(easy_xt_path):
    print(f"[DEBUG] [OK] easy_xt目录存在")
else:
    print(f"[DEBUG] [ERROR] easy_xt目录不存在: {easy_xt_path}")

# 添加工作空间目录到Python路径，这样可以直接导入easy_xt
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)
    print(f"[DEBUG] 已将workspace_dir添加到sys.path")

# 尝试导入真实的EasyXT实例
real_easyxt_instance = None
try:
    # 方式1：直接导入EasyXT类（推荐）
    from easy_xt import EasyXT
    real_easyxt_instance = EasyXT()
    print(f"[OK] 成功创建EasyXT实例，类型: {type(real_easyxt_instance)}")
    print(f"[DEBUG] 实例有init_data方法: {hasattr(real_easyxt_instance, 'init_data')}")
    EASYXT_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] EasyXT模块导入失败: {e}")
    print(f"请确保 easy_xt 模块位于: {workspace_dir}")
    raise ImportError(
        f"无法导入 easy_xt 模块。请确保：\n"
        f"1. easy_xt 目录存在于: {workspace_dir}\n"
        f"2. easy_xt/__init__.py 文件存在\n"
        f"3. Python 路径配置正确\n\n"
        f"详细错误: {e}"
    )
except Exception as e:
    print(f"[ERROR] 创建EasyXT实例失败: {e}")
    raise


class EasyXTDataLoader:
    """EasyXT数据加载器"""
    
    def __init__(self):
        # 只使用真实的EasyXT实例
        if not EASYXT_AVAILABLE or not real_easyxt_instance:
            raise ConnectionError("EasyXT模块未正确导入，无法创建数据加载器")

        self.easyxt = real_easyxt_instance
        self.connected = False

        # 初始化数据连接
        try:
            self.connected = self.easyxt.init_data()
            if self.connected:
                print("[OK] EasyXT数据服务连接成功")
            else:
                raise ConnectionError("EasyXT数据服务连接失败，请确保迅投客户端已启动")
        except Exception as e:
            raise ConnectionError(f"初始化EasyXT数据服务时出错: {e}\n请确保迅投客户端已启动")
    
    def load_data(self, symbols: Union[str, List[str]], start_date: str, end_date: str,
                  fields: Optional[List[str]] = None) -> pd.DataFrame:
        """
        从EasyXT加载数据并转换为标准格式

        Args:
            symbols: 股票代码列表或逗号分隔的字符串
            start_date: 开始日期
            end_date: 结束日期
            fields: 字段列表，默认为['open', 'high', 'low', 'close', 'volume']

        Returns:
            DataFrame: 标准格式的数据，索引为[date, symbol]
        """
        print(f"[DEBUG] EasyXTDataLoader.load_data 输入: type(symbols)={type(symbols)}, symbols={symbols}")

        # 第一重保险：入口强制转换
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(',') if s.strip()]
            print(f"[DEBUG] EasyXTDataLoader.load_data 字符串拆分后: {symbols}")

        if fields is None:
            # 默认获取价格、成交量和市值数据
            fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
            # 尝试添加市值字段（如果QMT支持）
            try:
                # 检查是否支持市值字段
                test_fields = fields.copy()
                test_fields.append('total_mv')  # 总市值
                fields = test_fields
            except:
                pass
        
        # 检查连接状态
        if not self.connected:
            raise ConnectionError("EasyXT未连接，请先调用 connect() 方法连接到迅投客户端")
        
        try:
            # 获取价格数据
            df_data = self.easyxt.get_price(
                codes=symbols,
                start=start_date,
                end=end_date,
                period='1d',
                fields=fields
            )

            print(f"[DEBUG] get_price 返回的数据形状: {df_data.shape}")
            print(f"[DEBUG] get_price 返回的列: {list(df_data.columns)}")
            print(f"[DEBUG] get_price 返回的前5行:\n{df_data.head()}")

            if df_data.empty:
                raise ValueError(f"获取的数据为空，请检查股票代码 {symbols} 和日期范围 {start_date} - {end_date}")
            
            # 重命名列以匹配期望的格式
            df_data = df_data.rename(columns={
                'time': 'date',
                'code': 'symbol'
            })
            
            # 确保date列为datetime类型
            df_data['date'] = pd.to_datetime(df_data['date'])
            
            # 设置多级索引 [date, symbol]
            df_data = df_data.set_index(['date', 'symbol']).sort_index()
            
            # 计算额外字段
            df_data = self._calculate_additional_fields(df_data)
            
            print(f"[OK] 成功加载真实数据，形状: {df_data.shape}")
            return df_data
            
        except Exception as e:
            print(f'加载真实数据时出错: {e}')
            import traceback
            traceback.print_exc()
            # 不再使用模拟数据，直接抛出异常
            raise RuntimeError(f"数据加载失败: {str(e)}\n请确保：\n1. 迅投客户端已启动\n2. 已下载相关股票的历史数据\n3. 股票代码正确")
    
    def get_historical_data(self, symbols: List[str], start_date: str, end_date: str,
                           fields: Optional[List[str]] = None, warmup_days: int = 250) -> pd.DataFrame:
        """
        获取历史数据（与旧接口兼容）

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fields: 字段列表，默认为['open', 'high', 'low', 'close', 'volume']
            warmup_days: 预热天数，用于因子计算（默认250天，覆盖alpha019的最大窗口期）

        Returns:
            DataFrame: 标准格式的数据，索引为[date, symbol]。包含预热期数据，供因子计算使用
        """
        # 计算扩展后的开始日期
        if warmup_days > 0:
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            # 预估工作日：交易日数 * 1.4 ≈ 日历天数（考虑周末和节假日）
            # 例如：250个交易日 ≈ 350个日历天
            extended_start = start_dt - timedelta(days=int(warmup_days * 1.5))
            extended_start_date = extended_start.strftime('%Y-%m-%d')

            print(f"[INFO] 因子计算需要{warmup_days}个交易日预热期，自动扩展日期范围：")
            print(f"      用户请求: {start_date} 到 {end_date}")
            print(f"      实际加载: {extended_start_date} 到 {end_date}（包含预热数据）")

            # 加载扩展后的数据（包含预热期）
            df_full = self.load_data(symbols, extended_start_date, end_date, fields)

            # 检查是否加载了足够的交易日
            actual_trading_days = len(df_full.index.get_level_values('date').unique())
            if actual_trading_days < warmup_days + 10:  # 加上10天余量
                print(f"[WARNING] 加载的交易日({actual_trading_days})可能不足{warmup_days}天，")
                print(f"         建议检查数据源或调整start_date更早")

            # 返回完整数据（包括预热期），因子计算器会处理
            print(f"[INFO] 总共加载了{actual_trading_days}个交易日")

            return df_full
        else:
            return self.load_data(symbols, start_date, end_date, fields)

    def _calculate_additional_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算额外字段，如vwap, returns等"""
        df = df.copy()

        # 检查必需的列是否存在
        required_cols = ['high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            print(f"⚠️  缺少必需的列: {missing_cols}")
            print(f"    当前可用的列: {list(df.columns)}")
            # 如果缺少关键列，不计算vwap
            if 'close' in df.columns:
                # 至少计算收益率
                df['returns'] = df.groupby(level=1)['close'].pct_change()
            else:
                # 连 close 都没有，创建空的 returns 列
                df['returns'] = np.nan
            return df

        # 计算vwap（成交量加权平均价）- 这里简化处理
        df['vwap'] = (df['high'] + df['low'] + df['close']) / 3

        # 按股票分组计算returns - 使用更安全的方法避免MultiIndex破坏
        df['returns'] = df.groupby(level=1)['close'].pct_change()

        return df
    
    def _generate_mock_data(self, symbols: Union[str, List[str]], start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟数据"""
        # 第二重保险：模拟数据生成前强制转换
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(',') if s.strip()]
            
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        # 过滤掉非交易日
        dates = [date for date in dates if date.weekday() < 5]  # 简单过滤周末
        
        all_data = []
        for symbol in symbols:
            for date in dates:
                row = {
                    'date': date,
                    'symbol': symbol,
                    'open': np.random.uniform(90, 110),
                    'high': np.random.uniform(100, 120),
                    'low': np.random.uniform(80, 100),
                    'close': np.random.uniform(90, 110),
                    'volume': np.random.randint(1000000, 10000000)
                }
                all_data.append(row)
        
        if all_data:
            df = pd.DataFrame(all_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index(['date', 'symbol']).sort_index()
            
            # 计算额外字段
            df = self._calculate_additional_fields(df)
            
            print(f'[OK] 成功生成模拟数据，形状: {df.shape}')
            return df
        else:
            raise Exception('无法生成模拟数据')


# 测试代码
if __name__ == '__main__':
    loader = EasyXTDataLoader()
    
    # 测试数据加载
    symbols = ['000001.SZ', '600000.SH']
    start_date = '2023-01-01'
    end_date = '2023-01-31'
    
    data = loader.load_data(symbols, start_date, end_date)
    print(f'加载数据形状: {data.shape}')
    print(f'数据列: {list(data.columns)}')
    print(f'股票代码: {data.index.get_level_values("symbol").unique().tolist()}')
    print(f'日期范围: {data.index.get_level_values("date").min()} 到 {data.index.get_level_values("date").max()}')