#!/usr/bin/env python3
"""
聚宽到Ptrade代码转换器命令行工具
"""
import argparse
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from converters.jq_to_ptrade import JQToPtradeConverter

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='聚宽到Ptrade代码转换器')
    parser.add_argument('input_file', help='输入的聚宽策略文件路径')
    parser.add_argument('-o', '--output', help='输出的Ptrade策略文件路径')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    
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
    
    # 创建转换器
    converter = JQToPtradeConverter()
    
    # 转换代码
    try:
        ptrade_code = converter.convert(jq_code)
    except Exception as e:
        print(f"错误: 代码转换失败: {e}")
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