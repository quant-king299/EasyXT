import sys
import os
# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
project_root = os.path.dirname(current_dir)
# 将项目根目录添加到Python路径
sys.path.insert(0, project_root)
# 导入EasyXT模块
import easy_xt

# 创建API实例
api = easy_xt.get_api()

# 初始化数据服务
success = api.init_data()
if success:
    print("数据服务初始化成功")
else:
    print("数据服务初始化失败")

# 获取平安银行最近10天的日线数据
data = api.get_price('000001.SZ', count=10)
print("数据形状:", data.shape)
print("最新5条数据:")
print(data.tail())

# 获取多只股票的最近5天数据
codes = ['000001.SZ', '000002.SZ', '600000.SH']
data = api.get_price(codes, count=5)
print("数据形状:", data.shape)
print("数据预览:")
print(data.head(10))

from datetime import datetime, timedelta

# 获取最近一周的数据
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

data = api.get_price(
    codes='000001.SZ',
    start=start_str,
    end=end_str,
    period='1d'
)
print("数据条数:", len(data))
print("最近一周的数据:")
print(data)

# 获取平安银行实时价格
current = api.get_current_price('000001.SZ')
if current is not None:
    print("实时价格数据:")
    print(current)
else:
    print("未能获取到实时价格数据，可能是因为QMT客户端未运行或未登录")

# 获取多只股票实时价格
codes = ['000001.SZ', '000002.SZ', '600000.SH']
current = api.get_current_price(codes)
if current is not None:
    print("多股票实时价格:")
    print(current[['code', 'price', 'open', 'high', 'low']])
else:
    print("未能获取到多股票实时价格数据")

# 获取所有A股列表
try:
    stock_list = api.get_stock_list('沪深A股')
    if stock_list:
        print(f"A股总数: {len(stock_list)}")
        print("前10只股票:")
        for i, code in enumerate(stock_list[:10]):
            print(f"  {i+1}. {code}")
    else:
        print("未能获取到A股列表数据")
except Exception as e:
    print(f"获取A股列表时出错: {e}")

# 获取沪深300列表
try:
    hs300_list = api.get_stock_list('沪深300')
    if hs300_list:
        print(f"沪深300成分股数量: {len(hs300_list)}")
        print("前10只股票:")
        for i, code in enumerate(hs300_list[:10]):
            print(f"  {i+1}. {code}")
    else:
        print("未能获取到沪深300列表数据")
except Exception as e:
    print(f"获取沪深300列表时出错: {e}")

# 获取最近10个交易日
trading_dates = api.get_trading_dates(market='SH', count=10)
print("最近10个交易日:")
for i, date in enumerate(trading_dates[-10:]):
    print(f"  {i+1}. {date}")

# 获取数据并进行基本统计分析
data = api.get_price('000001.SZ', count=30)

# 计算基本统计指标
print("价格统计:")
print(f"  最高价: {data['high'].max():.2f}")
print(f"  最低价: {data['low'].min():.2f}")
print(f"  平均价: {data['close'].mean():.2f}")
print(f"  价格标准差: {data['close'].std():.2f}")

# 计算涨跌幅
# 由于数据中没有pre_close字段，需要通过shift方法创建
import pandas as pd
data = data.sort_values('time').reset_index(drop=True)
data['pre_close'] = data['close'].shift(1)
data['change'] = data['close'] - data['pre_close']
data['change_pct'] = (data['change'] / data['pre_close']) * 100
print("\\n最近3天涨跌幅:")
print(data[['time', 'pre_close', 'close', 'change', 'change_pct']].tail(3))

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号'-'显示为方块的问题

# 获取数据并绘制价格走势图
data = api.get_price('000001.SZ', count=30)

plt.figure(figsize=(12, 6))
plt.plot(data['time'], data['close'])
plt.title('平安银行最近30天收盘价走势')
plt.xlabel('日期')
plt.ylabel('价格')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()