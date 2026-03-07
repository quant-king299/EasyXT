"""
股票量化交易学习案例 - 第一步：数据获取模块 (使用akshare)
使用akshare库获取股票数据的完整示例

功能包括：
1. 获取股票基本信息
2. 获取实时行情数据
3. 获取历史K线数据
4. 数据预处理和存储
5. 数据可视化展示

作者：王者quant
日期：2025-01-09
"""

import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class StockDataFetcher:
    """股票数据获取器 - 使用akshare"""
    
    def __init__(self):
        """初始化数据获取器"""
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        print("📊 股票数据获取器初始化完成 (使用akshare)")
    
    def get_stock_info(self, stock_code):
        """
        获取股票基本信息
        
        Args:
            stock_code (str): 股票代码，如 '000001' 或 '600000'
            
        Returns:
            dict: 股票基本信息
        """
        try:
            print(f"🔍 正在获取股票 {stock_code} 的基本信息...")
            
            # 获取股票实时行情
            stock_info = ak.stock_zh_a_spot_em()
            stock_data = stock_info[stock_info['代码'] == stock_code]
            
            if not stock_data.empty:
                data = stock_data.iloc[0]
                
                info = {
                    'stock_code': stock_code,
                    'name': data['名称'],
                    'latest_price': data['最新价'],
                    'change_pct': data['涨跌幅'],
                    'change_amount': data['涨跌额'],
                    'volume': data['成交量'],
                    'amount': data['成交额'],
                    'amplitude': data['振幅'],
                    'high': data['最高'],
                    'low': data['最低'],
                    'open': data['今开'],
                    'prev_close': data['昨收']
                }
                
                print(f"✅ 成功获取股票 {stock_code} ({data['名称']}) 基本信息")
                return info
            else:
                print(f"❌ 无法获取股票 {stock_code} 的信息")
                return None
                
        except Exception as e:
            print(f"❌ 获取股票信息时发生错误: {str(e)}")
            return None
    
    def get_realtime_data(self, stock_codes):
        """
        获取实时行情数据
        
        Args:
            stock_codes (list): 股票代码列表
            
        Returns:
            pd.DataFrame: 实时行情数据
        """
        try:
            print(f"📈 正在获取 {len(stock_codes)} 只股票的实时行情...")
            
            # 获取所有A股实时行情
            all_stocks = ak.stock_zh_a_spot_em()
            
            # 筛选指定股票
            selected_stocks = all_stocks[all_stocks['代码'].isin(stock_codes)]
            
            if not selected_stocks.empty:
                realtime_data = []
                
                for _, row in selected_stocks.iterrows():
                    realtime_data.append({
                        'stock_code': row['代码'],
                        'name': row['名称'],
                        'latest_price': row['最新价'],
                        'change_pct': row['涨跌幅'],
                        'change_amount': row['涨跌额'],
                        'volume': row['成交量'],
                        'amount': row['成交额'],
                        'high': row['最高'],
                        'low': row['最低'],
                        'open': row['今开'],
                        'prev_close': row['昨收']
                    })
                    print(f"  ✅ {row['代码']} {row['名称']}: {row['最新价']:.2f} ({row['涨跌幅']:+.2f}%)")
                
                df = pd.DataFrame(realtime_data)
                print(f"✅ 成功获取 {len(realtime_data)} 只股票的实时行情")
                return df
            else:
                print("❌ 未找到指定股票的实时行情数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取实时行情时发生错误: {str(e)}")
            return pd.DataFrame()
    
    def get_historical_data(self, stock_code, period="daily", adjust="qfq", start_date=None, end_date=None):
        """
        获取历史K线数据
        
        Args:
            stock_code (str): 股票代码
            period (str): 周期，默认"daily"
            adjust (str): 复权类型，默认"qfq"前复权
            start_date (str): 开始日期，格式"20240101"
            end_date (str): 结束日期，格式"20241231"
            
        Returns:
            pd.DataFrame: 历史K线数据
        """
        try:
            # 如果没有指定日期，默认获取最近30天
            if not start_date:
                start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            
            print(f"📊 正在获取股票 {stock_code} 从 {start_date} 到 {end_date} 的历史数据...")
            
            # 获取历史数据
            hist_data = ak.stock_zh_a_hist(symbol=stock_code, period=period, 
                                         start_date=start_date, end_date=end_date, adjust=adjust)
            
            if hist_data is not None and not hist_data.empty:
                # 重命名列名为英文
                hist_data.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'change_pct', 'change_amount', 'turnover']
                
                # 设置日期为索引
                hist_data['date'] = pd.to_datetime(hist_data['date'])
                hist_data.set_index('date', inplace=True)
                
                # 添加技术指标计算
                hist_data = self._add_technical_indicators(hist_data)
                
                # 保存数据到文件
                filename = f"{self.data_dir}/{stock_code}_historical.csv"
                hist_data.to_csv(filename)
                
                print(f"✅ 成功获取 {len(hist_data)} 条历史数据，已保存到 {filename}")
                return hist_data
            else:
                print(f"❌ 无法获取股票 {stock_code} 的历史数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取历史数据时发生错误: {str(e)}")
            return pd.DataFrame()
    
    def _add_technical_indicators(self, data):
        """
        添加基础技术指标
        
        Args:
            data (pd.DataFrame): 原始K线数据
            
        Returns:
            pd.DataFrame: 添加技术指标后的数据
        """
        try:
            # 计算移动平均线
            data['MA5'] = data['close'].rolling(window=5).mean()
            data['MA10'] = data['close'].rolling(window=10).mean()
            data['MA20'] = data['close'].rolling(window=20).mean()
            
            # 计算成交量移动平均
            data['VOL_MA5'] = data['volume'].rolling(window=5).mean()
            
            # 计算RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # 计算MACD
            exp1 = data['close'].ewm(span=12).mean()
            exp2 = data['close'].ewm(span=26).mean()
            data['MACD'] = exp1 - exp2
            data['MACD_signal'] = data['MACD'].ewm(span=9).mean()
            data['MACD_hist'] = data['MACD'] - data['MACD_signal']
            
            # 计算布林带
            data['BB_middle'] = data['close'].rolling(window=20).mean()
            bb_std = data['close'].rolling(window=20).std()
            data['BB_upper'] = data['BB_middle'] + (bb_std * 2)
            data['BB_lower'] = data['BB_middle'] - (bb_std * 2)
            
            return data
            
        except Exception as e:
            print(f"❌ 计算技术指标时发生错误: {str(e)}")
            return data
    
    def visualize_data(self, data, stock_code, title="股票K线图"):
        """
        可视化股票数据
        
        Args:
            data (pd.DataFrame): 股票数据
            stock_code (str): 股票代码
            title (str): 图表标题
        """
        try:
            if data.empty:
                print("❌ 数据为空，无法绘制图表")
                return
            
            print(f"📈 正在绘制股票 {stock_code} 的K线图...")
            
            # 创建子图
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
            
            # 1. 绘制K线图和移动平均线
            ax1.plot(data.index, data['close'], label='收盘价', linewidth=2, color='blue')
            
            if 'MA5' in data.columns:
                ax1.plot(data.index, data['MA5'], label='MA5', alpha=0.7, color='orange')
            if 'MA10' in data.columns:
                ax1.plot(data.index, data['MA10'], label='MA10', alpha=0.7, color='green')
            if 'MA20' in data.columns:
                ax1.plot(data.index, data['MA20'], label='MA20', alpha=0.7, color='red')
            
            # 添加布林带
            if 'BB_upper' in data.columns:
                ax1.fill_between(data.index, data['BB_upper'], data['BB_lower'], 
                               alpha=0.2, color='gray', label='布林带')
            
            ax1.set_title(f'{title} - {stock_code}', fontsize=14, fontweight='bold')
            ax1.set_ylabel('价格 (元)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 2. 绘制成交量
            ax2.bar(data.index, data['volume'], alpha=0.6, color='gray', label='成交量')
            if 'VOL_MA5' in data.columns:
                ax2.plot(data.index, data['VOL_MA5'], color='red', label='成交量MA5')
            
            ax2.set_title('成交量', fontsize=12)
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 3. 绘制RSI
            if 'RSI' in data.columns:
                ax3.plot(data.index, data['RSI'], color='purple', label='RSI')
                ax3.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='超买线(70)')
                ax3.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='超卖线(30)')
                ax3.set_title('RSI指标', fontsize=12)
                ax3.set_ylabel('RSI', fontsize=12)
                ax3.set_ylim(0, 100)
                ax3.legend()
                ax3.grid(True, alpha=0.3)
            
            # 4. 绘制MACD
            if 'MACD' in data.columns:
                ax4.plot(data.index, data['MACD'], color='blue', label='MACD')
                ax4.plot(data.index, data['MACD_signal'], color='red', label='Signal')
                ax4.bar(data.index, data['MACD_hist'], alpha=0.6, color='green', label='Histogram')
                ax4.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                ax4.set_title('MACD指标', fontsize=12)
                ax4.set_ylabel('MACD', fontsize=12)
                ax4.legend()
                ax4.grid(True, alpha=0.3)
            
            # 格式化x轴日期
            for ax in [ax1, ax2, ax3, ax4]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # 保存图表
            chart_filename = f"{self.data_dir}/{stock_code}_chart.png"
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            
            plt.show()
            print(f"✅ 图表已保存到 {chart_filename}")
            
        except Exception as e:
            print(f"❌ 绘制图表时发生错误: {str(e)}")
    
    def get_market_summary(self, stock_codes):
        """
        获取市场概览
        
        Args:
            stock_codes (list): 股票代码列表
            
        Returns:
            pd.DataFrame: 市场概览数据
        """
        try:
            print(f"📊 正在获取 {len(stock_codes)} 只股票的市场概览...")
            
            # 获取所有A股实时行情
            all_stocks = ak.stock_zh_a_spot_em()
            
            # 筛选指定股票
            selected_stocks = all_stocks[all_stocks['代码'].isin(stock_codes)]
            
            if not selected_stocks.empty:
                summary_data = []
                
                for _, row in selected_stocks.iterrows():
                    summary_data.append({
                        'stock_code': row['代码'],
                        'name': row['名称'],
                        'latest_price': row['最新价'],
                        'change_pct': row['涨跌幅'],
                        'change_amount': row['涨跌额'],
                        'volume': row['成交量'],
                        'amount': row['成交额'],
                        'amplitude': row['振幅'],
                        'high': row['最高'],
                        'low': row['最低'],
                        'turnover': row['换手率']
                    })
                
                df = pd.DataFrame(summary_data)
                print(f"✅ 成功获取 {len(summary_data)} 只股票的市场概览")
                return df
            else:
                print("❌ 未获取到任何市场概览数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取市场概览时发生错误: {str(e)}")
            return pd.DataFrame()


def main():
    """主函数 - 演示数据获取功能"""
    print("=" * 60)
    print("🚀 股票量化交易学习案例 - 数据获取模块 (akshare版)")
    print("=" * 60)
    
    # 初始化数据获取器
    fetcher = StockDataFetcher()
    
    # 定义测试股票代码
    test_stocks = ['000001', '600000', '000002', '600036']  # 平安银行、浦发银行、万科A、招商银行
    single_stock = '000001'  # 平安银行
    
    print("\n" + "=" * 40)
    print("📋 第一步：获取股票基本信息")
    print("=" * 40)
    
    # 获取单只股票基本信息
    stock_info = fetcher.get_stock_info(single_stock)
    if stock_info:
        print(f"\n📊 股票 {single_stock} 基本信息：")
        for key, value in stock_info.items():
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 40)
    print("📈 第二步：获取实时行情数据")
    print("=" * 40)
    
    # 获取多只股票实时行情
    realtime_df = fetcher.get_realtime_data(test_stocks)
    if not realtime_df.empty:
        print(f"\n📊 实时行情数据：")
        display_cols = ['stock_code', 'name', 'latest_price', 'change_pct', 'volume']
        print(realtime_df[display_cols].to_string(index=False))
    
    print("\n" + "=" * 40)
    print("📊 第三步：获取历史K线数据")
    print("=" * 40)
    
    # 获取历史数据
    historical_df = fetcher.get_historical_data(single_stock)
    if not historical_df.empty:
        print(f"\n📊 历史数据统计信息：")
        print(f"  数据条数: {len(historical_df)}")
        print(f"  日期范围: {historical_df.index[0].strftime('%Y-%m-%d')} 至 {historical_df.index[-1].strftime('%Y-%m-%d')}")
        print(f"  最高价: {historical_df['high'].max():.2f}")
        print(f"  最低价: {historical_df['low'].min():.2f}")
        print(f"  平均成交量: {historical_df['volume'].mean():.0f}")
        
        # 显示最近5天数据
        print(f"\n📊 最近5天数据：")
        recent_data = historical_df.tail(5)[['open', 'high', 'low', 'close', 'volume', 'MA5', 'RSI']]
        print(recent_data.round(2).to_string())
    
    print("\n" + "=" * 40)
    print("📈 第四步：数据可视化")
    print("=" * 40)
    
    # 绘制K线图
    if not historical_df.empty:
        fetcher.visualize_data(historical_df, single_stock, "历史K线图")
    
    print("\n" + "=" * 40)
    print("📊 第五步：市场概览")
    print("=" * 40)
    
    # 获取市场概览
    market_summary = fetcher.get_market_summary(test_stocks)
    if not market_summary.empty:
        print(f"\n📊 市场概览：")
        display_cols = ['stock_code', 'name', 'latest_price', 'change_pct', 'amplitude', 'turnover']
        print(market_summary[display_cols].to_string(index=False))
    
    print("\n" + "=" * 60)
    print("✅ 数据获取模块演示完成！")
    print("📁 数据文件已保存到 data/ 目录")
    print("📈 图表文件已保存到 data/ 目录")
    print("=" * 60)


if __name__ == "__main__":
    main()