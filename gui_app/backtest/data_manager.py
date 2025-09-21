# -*- coding: utf-8 -*-
"""
数据管理器
负责获取、清洗和转换回测所需的历史数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings

class DataManager:
    """
    数据管理器
    
    功能特性：
    1. 通过xtquant获取真实历史数据
    2. 数据清洗和质量检查
    3. 格式转换和标准化
    4. 多数据源支持和备用方案
    """
    
    def __init__(self):
        """初始化数据管理器"""
        self.xt_available = self._check_xtquant_availability()
        self.qmt_connected = self._check_qmt_connection()
        
        # 显示连接状态
        print("📊 数据管理器初始化完成")
        print(f"   - xtquant模块: {'✅ 可用' if self.xt_available else '❌ 不可用'}")
        print(f"   - QMT连接状态: {'✅ 已连接' if self.qmt_connected else '❌ 未连接'}")
        
        if not self.qmt_connected:
            print("💡 提示: 请确保MiniQMT已启动并登录，否则将使用模拟数据")
        
    def _check_xtquant_availability(self) -> bool:
        """检查xtquant是否可用"""
        try:
            import xtquant.xtdata as xt_data
            return True
        except ImportError:
            print("⚠️ xtquant未安装，将使用模拟数据")
            return False
    
    def _check_qmt_connection(self) -> bool:
        """检查QMT连接状态"""
        if not self.xt_available:
            return False
            
        try:
            import xtquant.xtdata as xt_data
            
            print("🔍 正在检测QMT连接状态...")
            
            # 使用快速检测方法 - 直接尝试获取单个股票信息
            try:
                # 设置较短的超时时间，避免长时间阻塞
                import threading
                import time
                
                result = {'connected': False}
                
                def quick_check():
                    try:
                        # 尝试获取单个股票的基本信息，这个调用通常很快
                        info = xt_data.get_instrument_detail('000001.SZ')
                        if info and len(info) > 0:
                            result['connected'] = True
                    except:
                        result['connected'] = False
                
                # 创建检测线程，设置2秒超时
                check_thread = threading.Thread(target=quick_check)
                check_thread.daemon = True
                check_thread.start()
                check_thread.join(timeout=2.0)  # 2秒超时
                
                if result['connected']:
                    print("✅ QMT连接检测成功")
                    return True
                else:
                    print("⚠️ QMT未连接或检测超时")
                    return False
                    
            except Exception as inner_e:
                print(f"⚠️ QMT连接检测失败: {inner_e}")
                return False
                
        except Exception as e:
            print(f"⚠️ QMT连接检测失败: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, any]:
        """获取连接状态信息"""
        return {
            'xt_available': self.xt_available,
            'qmt_connected': self.qmt_connected,
            'data_source': 'real' if self.qmt_connected else 'mock',
            'status_message': self._get_status_message()
        }
    
    def _get_status_message(self) -> str:
        """获取状态消息"""
        if self.qmt_connected:
            return "✅ 已连接到QMT，使用真实市场数据"
        elif self.xt_available:
            return "⚠️ xtquant可用但QMT未连接，使用模拟数据"
        else:
            return "❌ xtquant不可用，使用模拟数据"
    
    def get_stock_data(self, 
                      stock_code: str, 
                      start_date: str, 
                      end_date: str,
                      period: str = '1d') -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码 (如 '000001.SZ')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD')
            period: 数据周期 ('1d', '1h', '5m' 等)
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        print(f"📊 获取股票数据: {stock_code} ({start_date} ~ {end_date})")
        
        if self.qmt_connected:
            print("🔗 数据源: QMT真实市场数据")
            return self._get_real_data(stock_code, start_date, end_date, period)
        else:
            print("🎲 数据源: 模拟数据 (QMT未连接)")
            return self._generate_mock_data(stock_code, start_date, end_date)
    
    def _get_real_data(self, stock_code: str, start_date: str, end_date: str, period: str) -> pd.DataFrame:
        """通过xtquant获取真实数据"""
        try:
            import xtquant.xtdata as xt_data
            
            # 转换日期格式
            start_time = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
            end_time = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
            
            # 获取历史数据
            data = xt_data.get_market_data_ex(
                stock_list=[stock_code],
                period=period,
                start_time=start_time,
                end_time=end_time,
                fill_data=True
            )
            
            if data and stock_code in data:
                df = data[stock_code]
                
                # 标准化列名
                df = self._standardize_columns(df)
                
                # 数据清洗
                df = self._clean_data(df)
                
                print(f"✅ 成功获取 {len(df)} 条真实数据")
                return df
            else:
                print("⚠️ 未获取到数据，使用模拟数据")
                return self._generate_mock_data(stock_code, start_date, end_date)
                
        except Exception as e:
            print(f"⚠️ 获取真实数据失败: {e}，使用模拟数据")
            return self._generate_mock_data(stock_code, start_date, end_date)
    
    def _generate_mock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟数据"""
        print(f"🎲 生成模拟数据: {stock_code}")
        
        # 创建日期范围
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = dates[dates.weekday < 5]  # 只保留工作日
        
        # 生成价格数据
        np.random.seed(hash(stock_code) % 2**32)  # 基于股票代码的固定种子
        
        # 基础价格
        base_price = 10.0 + (hash(stock_code) % 100)
        
        # 生成收盘价（随机游走）
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
        close_prices = [base_price]
        
        for ret in returns[1:]:
            new_price = close_prices[-1] * (1 + ret)
            close_prices.append(max(new_price, 0.1))  # 防止价格为负
        
        close_prices = np.array(close_prices)
        
        # 生成其他价格数据
        high_prices = close_prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates))))
        low_prices = close_prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates))))
        
        # 开盘价基于前一日收盘价
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = base_price
        open_prices = open_prices * (1 + np.random.normal(0, 0.005, len(dates)))
        
        # 确保价格关系合理 (low <= open,close <= high)
        for i in range(len(dates)):
            low_prices[i] = min(low_prices[i], open_prices[i], close_prices[i])
            high_prices[i] = max(high_prices[i], open_prices[i], close_prices[i])
        
        # 生成成交量
        volumes = np.random.lognormal(10, 1, len(dates)).astype(int) * 100
        
        # 创建DataFrame
        df = pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        }, index=dates)
        
        print(f"✅ 生成 {len(df)} 条模拟数据")
        return df
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 确保必要列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                if col == 'volume':
                    df[col] = 0
                else:
                    # 如果缺少价格列，用close价格填充
                    df[col] = df.get('close', 0)
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        print("🧹 开始数据清洗...")
        
        original_length = len(df)
        
        # 1. 删除空值
        df = df.dropna()
        
        # 2. 删除价格为0或负数的数据
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                df = df[df[col] > 0]
        
        # 3. 检查价格关系的合理性
        if all(col in df.columns for col in price_columns):
            # high >= max(open, close) and low <= min(open, close)
            valid_mask = (
                (df['high'] >= df[['open', 'close']].max(axis=1)) &
                (df['low'] <= df[['open', 'close']].min(axis=1))
            )
            df = df[valid_mask]
        
        # 4. 删除异常波动的数据（日涨跌幅超过20%）
        if 'close' in df.columns and len(df) > 1:
            returns = df['close'].pct_change()
            normal_mask = (returns.abs() <= 0.2) | returns.isna()
            df = df[normal_mask]
        
        # 5. 确保成交量为正数
        if 'volume' in df.columns:
            df = df[df['volume'] >= 0]
        
        cleaned_length = len(df)
        removed_count = original_length - cleaned_length
        
        if removed_count > 0:
            print(f"🧹 数据清洗完成，删除 {removed_count} 条异常数据")
        
        return df
    
    def get_multiple_stocks_data(self, 
                               stock_codes: List[str], 
                               start_date: str, 
                               end_date: str) -> Dict[str, pd.DataFrame]:
        """
        获取多只股票的数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            股票代码到DataFrame的字典
        """
        print(f"📊 批量获取 {len(stock_codes)} 只股票数据...")
        
        results = {}
        for stock_code in stock_codes:
            try:
                data = self.get_stock_data(stock_code, start_date, end_date)
                if not data.empty:
                    results[stock_code] = data
                else:
                    print(f"⚠️ {stock_code} 数据为空")
            except Exception as e:
                print(f"⚠️ 获取 {stock_code} 数据失败: {e}")
        
        print(f"✅ 成功获取 {len(results)} 只股票数据")
        return results
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        验证数据质量
        
        Args:
            df: 待验证的数据
            
        Returns:
            数据质量报告
        """
        report = {
            'total_records': len(df),
            'date_range': {
                'start': self._safe_format_date(df.index.min() if not df.empty else None),
                'end': self._safe_format_date(df.index.max() if not df.empty else None)
            },
            'missing_values': df.isnull().sum().to_dict(),
            'data_completeness': (1 - df.isnull().sum() / len(df)).to_dict() if not df.empty else {},
            'price_statistics': {},
            'issues': []
        }
        
        if df.empty:
            report['issues'].append('数据为空')
            return report
        
        # 价格统计
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                report['price_statistics'][col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std())
                }
        
        # 检查数据问题
        if df.isnull().any().any():
            report['issues'].append('存在缺失值')
        
        if 'close' in df.columns:
            returns = df['close'].pct_change().dropna()
            if (returns.abs() > 0.2).any():
                report['issues'].append('存在异常波动（单日涨跌幅>20%）')
        
        # 检查价格关系
        if all(col in df.columns for col in price_columns):
            invalid_high = (df['high'] < df[['open', 'close']].max(axis=1)).any()
            invalid_low = (df['low'] > df[['open', 'close']].min(axis=1)).any()
            
            if invalid_high or invalid_low:
                report['issues'].append('存在不合理的价格关系')
        
        return report
    
    def resample_data(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        重采样数据到不同频率
        
        Args:
            df: 原始数据
            freq: 目标频率 ('1H', '4H', '1D', '1W', '1M')
            
        Returns:
            重采样后的数据
        """
        if df.empty:
            return df
        
        # OHLCV数据的重采样规则
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min', 
            'close': 'last',
            'volume': 'sum'
        }
        
        # 只对存在的列进行重采样
        available_agg = {k: v for k, v in agg_dict.items() if k in df.columns}
        
        resampled = df.resample(freq).agg(available_agg)
        
        # 删除空值行
        resampled = resampled.dropna()
        
        print(f"📊 数据重采样完成: {len(df)} -> {len(resampled)} 条记录 (频率: {freq})")
        
        return resampled
    
    def _safe_format_date(self, date_obj) -> Optional[str]:
        """安全地格式化日期对象"""
        if date_obj is None:
            return None
        
        try:
            # 如果是pandas Timestamp对象
            if hasattr(date_obj, 'strftime'):
                return date_obj.strftime('%Y-%m-%d')
            # 如果是datetime对象
            elif hasattr(date_obj, 'date'):
                return date_obj.date().strftime('%Y-%m-%d')
            # 尝试转换为pandas Timestamp
            else:
                return pd.to_datetime(date_obj).strftime('%Y-%m-%d')
        except Exception as e:
            print(f"⚠️ 日期格式化失败: {e}")
            return None


if __name__ == "__main__":
    # 测试数据管理器
    dm = DataManager()
    
    # 测试单只股票数据获取
    data = dm.get_stock_data('000001.SZ', '2023-01-01', '2023-12-31')
    print(f"📊 获取数据形状: {data.shape}")
    print(f"📊 数据列: {list(data.columns)}")
    
    # 测试数据质量验证
    quality_report = dm.validate_data_quality(data)
    print(f"📊 数据质量报告: {quality_report}")
    
    # 测试数据重采样
    weekly_data = dm.resample_data(data, '1W')
    print(f"📊 周线数据形状: {weekly_data.shape}")