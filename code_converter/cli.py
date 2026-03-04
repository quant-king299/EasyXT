#!/usr/bin/env python3
"""
聚宽到Ptrade代码转换器命令行工具
"""
import argparse
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from converters.jq_to_ptrade_unified_v2 import JQToPtradeUnifiedConverter, StrategyType

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='聚宽到Ptrade代码转换器')
    parser.add_argument('input_file', help='输入的聚宽策略文件路径')
    parser.add_argument('-o', '--output', help='输出的Ptrade策略文件路径')
    parser.add_argument('-m', '--mapping', help='API映射文件路径 (已弃用，保留用于兼容性)')
    parser.add_argument('-t', '--type', choices=['backtest', 'live', 'auto'],
                       default='auto', help='策略类型: backtest(回测), live(实盘), auto(自动检测)')
    parser.add_argument('-q', '--quiet', action='store_true', help='静默模式，减少输出信息')
    parser.add_argument('--version', action='version', version='%(prog)s 2.1 (统一转换器完善版)')
    
    args = parser.parse_args()
    
    # 读取输入文件
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            jq_code = f.read()
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {args.input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取输入文件失败: {e}")
        sys.exit(1)
    
    # 确定API映射文件路径
    api_mapping_file = args.mapping
    if not api_mapping_file:
        # 默认使用项目中的映射文件
        default_mapping = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_mapping.json')
        if os.path.exists(default_mapping):
            api_mapping_file = default_mapping
    
    # 确定策略类型
    strategy_type_map = {
        'backtest': StrategyType.BACKTEST,
        'live': StrategyType.LIVE,
        'auto': None,
    }
    strategy_type = strategy_type_map[args.type]

    # 创建统一转换器
    converter = JQToPtradeUnifiedConverter(verbose=not args.quiet)
    
    # 转换代码
    try:
        ptrade_code = converter.convert(jq_code, strategy_type=strategy_type)
    except Exception as e:
        print(f"错误: 代码转换失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 输出结果
    if args.output:
        # 写入输出文件
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(ptrade_code)
            print(f"转换完成，结果已保存到 {args.output}")
        except Exception as e:
            print(f"错误: 写入输出文件失败: {e}")
            sys.exit(1)
    else:
        # 输出到标准输出
        print(ptrade_code)

if __name__ == "__main__":
    main()