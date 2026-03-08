#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyXT 环境检查工具
快速诊断项目环境和常见问题
"""

import sys
import os
from pathlib import Path

# 获取项目根目录（无论从哪里运行都能找到）
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 确保项目根目录在sys.path中
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows编码兼容处理
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def print_check(name, status, message=""):
    """打印检查结果"""
    icon = "✓" if status else "✗"
    print(f"\n[{icon}] {name}")
    if message:
        print(f"    {message}")

def main():
    print_header("EasyXT 环境检查工具")

    # 1. Python版本检查
    print("\n[1] Python版本检查")
    py_version = sys.version_info
    print(f"    当前版本: Python {py_version.major}.{py_version.minor}.{py_version.micro}")

    if py_version >= (3, 9):
        print("    ✓ 版本符合要求 (>=3.9)")
    else:
        print("    ✗ 版本过低，建议升级到Python 3.9+")

    # 2. xtquant模块检查
    print("\n[2] xtquant模块检查")
    try:
        from xtquant import datacenter
        print("    ✓ xtquant已安装")

        # 检查是否是正确的版本
        try:
            # 尝试导入datacenter，这是特殊版本的特征
            from xtquant import xtdata
            print("    ✓ xtquant版本正确（特殊版本）")
        except ImportError:
            print("    ⚠️ xtquant版本可能不完整")
            print("    建议：下载项目提供的特殊版本")

    except ImportError as e:
        print("    ✗ xtquant未安装或版本错误")
        print("    解决方案：")
        print("    1. 访问：https://github.com/quant-king299/EasyXT/releases/tag/v1.0.0")
        print("    2. 下载：xtquant.rar")
        print("    3. 解压到项目根目录")

    # 3. easy_xt模块检查
    print("\n[3] easy_xt模块检查")
    try:
        from easy_xt import get_api
        print("    ✓ easy_xt已安装")

        # 尝试获取API实例
        try:
            api = get_api()
            print("    ✓ easy_xt可以正常导入")
        except Exception as e:
            print(f"    ⚠️ easy_xt导入警告: {e}")

    except ImportError:
        print("    ✗ easy_xt未安装")
        print("    解决方案：pip install -e ./easy_xt")

    # 4. easyxt_backtest模块检查
    print("\n[4] easyxt_backtest模块检查")
    try:
        import easyxt_backtest
        print("    ✓ easyxt_backtest已安装")
    except ImportError:
        print("    ⚠️ easyxt_backtest未安装（可选）")
        print("    如需回测功能，请运行：pip install -e ./easyxt_backtest")

    # 5. DuckDB数据库检查
    print("\n[5] DuckDB数据库检查")
    duckdb_paths = [
        'D:/StockData/stock_data.ddb',
        'd:/stockdata/stock_data.ddb',
        './data/stock_data.ddb',
        '~/StockData/stock_data.ddb'
    ]

    db_found = False
    for path in duckdb_paths:
        expanded_path = Path(path).expanduser()
        if expanded_path.exists():
            print(f"    ✓ 找到数据库: {expanded_path}")

            # 检查数据库内容
            try:
                import duckdb
                con = duckdb.connect(str(expanded_path), read_only=True)

                # 检查表
                tables = con.execute("SHOW TABLES").fetchall()
                print(f"    ✓ 数据表数量: {len(tables)}")

                # 检查数据量
                if tables:
                    table_names = [t[0] for t in tables]
                    if 'stock_data' in table_names:
                        count = con.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]
                        print(f"    ✓ stock_data表记录数: {count:,}")

                con.close()
                db_found = True
                break
            except Exception as e:
                print(f"    ⚠️ 数据库存在但无法读取: {e}")

    if not db_found:
        print("    ✗ 未找到DuckDB数据库")
        print("    解决方案：")
        print("    1. 运行 python run_gui.py")
        print("    2. 切换到'📥 Tushare下载'标签页")
        print("    3. 下载股票数据（会自动创建数据库）")
        print("    或运行：cd '101因子/101因子分析平台/scripts' && python init_data.py")

    # 6. Tushare配置检查
    print("\n[6] Tushare配置检查")
    try:
        from dotenv import load_dotenv
        load_dotenv()

        token = os.getenv('TUSHARE_TOKEN')
        if token:
            print(f"    ✓ Token已配置: {token[:10]}...")
            print(f"    ✓ Token长度: {len(token)} 字符")

            # 验证Token长度（Tushare Token通常是32字符）
            if len(token) == 32:
                print("    ✓ Token格式正确")
            else:
                print("    ⚠️ Token长度可能不正确（通常为32字符）")
        else:
            print("    ⚠️ Token未配置")
            print("    解决方案：")
            print("    1. 在项目根目录创建 .env 文件")
            print("    2. 添加：TUSHARE_TOKEN=你的Token")
            print("    3. 或者运行 GUI 在'Tushare下载'标签页中输入")
    except ImportError:
        print("    ⚠️ python-dotenv未安装")
        print("    解决方案：pip install python-dotenv")

    # 7. GUI依赖检查
    print("\n[7] GUI依赖检查")
    gui_deps = {
        'PyQt5': 'PyQt5基础库',
        'pandas': 'DataFrame数据处理',
        'numpy': '数值计算库',
    }

    missing_gui_deps = []
    for package, description in gui_deps.items():
        try:
            __import__(package)
            print(f"    ✓ {package:<15} - {description}")
        except ImportError:
            print(f"    ✗ {package:<15} - {description} (未安装)")
            missing_gui_deps.append(package)

    if missing_gui_deps:
        print(f"    解决方案：pip install {' '.join(missing_gui_deps)}")

    # 8. 项目结构检查
    print("\n[8] 项目结构检查")
    required_dirs = [
        'easy_xt',
        'easyxt_backtest',
        '101因子',
        '学习实例',
        'strategies'
    ]

    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"    ✓ {dir_name}/")
        else:
            print(f"    ⚠️ {dir_name}/ 不存在")

    # 9. 配置文件检查
    print("\n[9] 配置文件检查")
    config_files = {
        '.env': '环境变量配置',
        '.env.example': '环境变量模板',
        'requirements.txt': 'Python依赖列表',
    }

    for file_name, description in config_files.items():
        file_path = Path(file_name)
        if file_path.exists():
            print(f"    ✓ {file_name:<20} - {description}")
        else:
            if file_name == '.env':
                print(f"    ⚠️ {file_name:<20} - 建议创建（复制.env.example）")
            else:
                print(f"    ✓ {file_name:<20} - {description}（可选）")

    # 10. 快速修复建议
    print_header("快速修复建议")

    issues = []

    # 检查xtquant
    try:
        from xtquant import datacenter
    except ImportError:
        issues.append("1. xtquant未安装 → 下载特殊版本并解压到项目根目录")

    # 检查easy_xt
    try:
        from easy_xt import get_api
    except ImportError:
        issues.append("2. easy_xt未安装 → 运行：pip install -e ./easy_xt")

    # 检查DuckDB
    if not db_found:
        issues.append("3. DuckDB数据库不存在 → 运行GUI下载数据或执行 init_data.py")

    # 检查Token
    if not os.getenv('TUSHARE_TOKEN'):
        issues.append("4. Tushare Token未配置 → 创建.env文件并添加Token")

    if issues:
        print("\n发现以下问题，建议按顺序修复：\n")
        for issue in issues:
            print(f"  {issue}")
        print("\n详细解决方案请查看：TROUBLESHOOTING.md")
    else:
        print("\n✓ 所有检查通过！你的环境配置正确。")
        print("\n下一步：")
        print("  1. 查看 README.md 了解项目结构")
        print("  2. 从 学习实例/01_基础入门.py 开始学习")
        print("  3. 或运行 python run_gui.py 启动GUI应用")

    print_header("检查完成")

    print("\n💡 提示：")
    print("  - 如果遇到问题，查看 TROUBLESHOOTING.md 获取详细帮助")
    print("  - 或访问：https://github.com/quant-king299/EasyXT/issues")
    print("  - 关注公众号：王者quant")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n检查被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
