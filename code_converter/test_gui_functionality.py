#!/usr/bin/env python3
"""
测试聚宽到Ptrade转换功能
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'code_converter'))

from converters.jq_to_ptrade import JQToPtradeConverter

def test_conversion():
    """测试代码转换功能"""
    # 示例聚宽代码
    jq_code = '''
def initialize(context):
    # 定义全局变量
    g.security = '000001.XSHE'
    # 设置基准
    set_benchmark('000300.XSHG')
    # 设置选项
    set_option('use_real_price', True)
    # 设置手续费
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))

def handle_data(context, data):
    security = g.security
    # 获取历史数据
    close_data = attribute_history(security, 5, '1d', ['close'])
    # 计算均线
    MA5 = close_data['close'].mean()
    current_price = close_data['close'][-1]
    # 交易逻辑
    if current_price > 1.01 * MA5:
        order_value(security, context.portfolio.cash)
        log.info("买入 %s" % security)
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        order_target(security, 0)
        log.info("卖出 %s" % security)
'''

    print("原始聚宽代码:")
    print(jq_code)
    print("\n" + "="*50 + "\n")
    
    try:
        # 创建转换器
        converter = JQToPtradeConverter()
        
        # 转换代码
        ptrade_code = converter.convert(jq_code)
        
        print("转换后的Ptrade代码:")
        print(ptrade_code)
        
        print("\n转换成功!")
        
    except Exception as e:
        print(f"转换失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_conversion()