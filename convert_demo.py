from code_converter.converters.jq_to_ptrade import JQToPtradeConverter

# 读取聚宽策略代码
with open('jq_demo_strategy.py', 'r', encoding='utf-8') as f:
    jq_code = f.read()

# 创建转换器
converter = JQToPtradeConverter()

# 转换代码
try:
    ptrade_code = converter.convert(jq_code)
    
    # 保存转换后的代码
    with open('ptrade_demo_strategy.py', 'w', encoding='utf-8') as f:
        f.write(ptrade_code)
    
    print('转换完成，结果已保存到 ptrade_demo_strategy.py')
    print('\n转换后的代码:')
    print(ptrade_code)
    
except Exception as e:
    print(f'转换失败: {e}')