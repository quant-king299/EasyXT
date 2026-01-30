"""
直接解析通达信自选股文件
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "easy_xt"))


def parse_zxg_blk(zxg_file):
    """
    解析通达信自选股文件 zxg.blk

    通达信的.blk文件格式：
    - 文件头：固定格式
    - 每个股票：6位代码 + 后缀
    """
    stocks = []

    try:
        with open(zxg_file, 'rb') as f:
            # 读取文件内容
            content = f.read()

            # 通达信.blk文件通常是二进制格式
            # 股票代码格式：市场代码(1字节) + 股票代码(6字节)
            # 市场代码：1=上海，0=深圳

            # 尝试解析（简化版）
            i = 0
            while i < len(content) - 7:
                market = content[i]
                code_bytes = content[i+1:i+7]

                # 尝试解码股票代码
                try:
                    code = code_bytes.decode('ascii').strip()
                    if code.isdigit() and len(code) == 6:
                        # 组合市场代码和股票代码
                        if market == 1:  # 上海
                            stock_code = f"{code}.SH"
                        elif market == 0:  # 深圳
                            stock_code = f"{code}.SZ"
                        else:
                            i += 1
                            continue

                        stocks.append(stock_code)
                        i += 7
                    else:
                        i += 1
                except:
                    i += 1

    except Exception as e:
        print(f"  [错误] 解析失败: {e}")

    return stocks


def read_tdx_zixg():
    """读取通达信自选股"""
    print("="*70)
    print("  读取通达信自选股")
    print("="*70)
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 通达信路径
    tdx_path = Path(r"D:\new_tdx64.2")
    zxg_file = tdx_path / "T0002" / "blocknew" / "zxg.blk"

    print(f"[步骤1] 定位自选股文件")
    print("-"*70)
    print(f"  通达信路径: {tdx_path}")
    print(f"  自选股文件: {zxg_file}")

    if not zxg_file.exists():
        print(f"\n  [错误] 文件不存在: {zxg_file}")
        return

    file_size = zxg_file.stat().st_size
    print(f"  文件大小: {file_size} 字节")
    print(f"  [OK] 文件存在\n")

    # 方法1: 尝试二进制解析
    print("[方法1] 二进制解析")
    print("-"*70)

    stocks = parse_zxg_blk(zxg_file)

    if stocks:
        print(f"\n  [成功] 找到 {len(stocks)} 只股票:")
        for i, stock in enumerate(stocks, 1):
            print(f"    {i:2d}. {stock}")
    else:
        print(f"\n  [失败] 未能解析出股票")

    # 方法2: 尝试文本读取
    print("\n[方法2] 文本读取")
    print("-"*70)

    try:
        with open(zxg_file, 'r', encoding='gbk', errors='ignore') as f:
            lines = f.readlines()

        print(f"  文件行数: {len(lines)}")

        # 解析每行的股票代码
        text_stocks = []
        for line in lines:
            # 去除空白和换行符
            code = line.strip()
            # 提取7位数字（通达信格式：市场代码(1位)+股票代码(6位)）
            import re
            match = re.search(r'\d{7}', code)
            if match:
                code7 = match.group()

                # 判断市场：第1位是市场代码
                market_code = code7[0]
                stock_code = code7[1:]  # 后6位是股票代码

                # 市场代码：1=上海，0=深圳（但在文件中可能不同）
                # 根据股票代码前缀判断更准确
                if stock_code.startswith('6') or stock_code.startswith('5'):
                    # 上海：600xxx, 601xxx, 603xxx, 688xxx, 5xx.xxx
                    stock_code_full = f"{stock_code}.SH"
                elif stock_code.startswith('8') or stock_code.startswith('4'):
                    # 北交所：8xxxxx, 4xxxxx
                    stock_code_full = f"{stock_code}.BJ"
                elif stock_code.startswith('3'):
                    # 创业板：300xxx, 301xxx
                    stock_code_full = f"{stock_code}.SZ"
                else:
                    # 深圳：000xxx, 001xxx, 002xxx
                    stock_code_full = f"{stock_code}.SZ"

                text_stocks.append(stock_code_full)

        if text_stocks:
            print(f"\n  [成功] 解析到 {len(text_stocks)} 只股票:")
            for i, stock in enumerate(text_stocks, 1):
                print(f"    {i:2d}. {stock}")

            # 保存到文件
            output_file = Path(__file__).parent.parent / "my_favorites.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                for stock in text_stocks:
                    f.write(f"{stock}\n")

            print(f"\n  [保存] 已保存到: {output_file}")

    except Exception as e:
        print(f"  [错误] 文本读取失败: {e}")
        import traceback
        traceback.print_exc()

    # 方法3: 十六进制查看
    print("\n[方法3] 文件内容预览（十六进制）")
    print("-"*70)

    try:
        with open(zxg_file, 'rb') as f:
            header = f.read(200)

        print(f"  前200字节（十六进制）:")
        for i in range(0, min(len(header), 200), 16):
            hex_str = ' '.join(f'{b:02x}' for b in header[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in header[i:i+16])
            print(f"  {i:04x}: {hex_str:48} {ascii_str}")

    except Exception as e:
        print(f"  [错误] {e}")

    print("\n" + "="*70)
    print("  使用建议")
    print("="*70)

    if stocks:
        print(f"""
成功解析自选股文件，找到 {len(stocks)} 只股票！

在交易脚本中使用:

    # 您的自选股列表
    MY_FAVORITES = {stocks[:10]}{'...' if len(stocks) > 10 else ''}

    # 完整列表
    MY_FAVORITES = {stocks}

    # 在交易脚本中
    for stock in MY_FAVORITES:
        trader.trade.buy(
            account_id='账户ID',
            code=stock,
            volume=100,
            price=10.0,
            price_type='limit'
        )
        """)
    else:
        print("""
未能自动解析自选股文件。

建议方案：
1. 在通达信中手动查看自选股（F6）
2. 将股票代码复制到代码中
3. 或者创建一个新的自定义板块

示例：
    MY_FAVORITES = [
        '605168.SH',  # 明阳智能
        '000333.SZ',  # 美的集团
        '600519.SH',  # 贵州茅台
        # 添加您的自选股...
    ]
        """)


if __name__ == "__main__":
    read_tdx_zixg()
