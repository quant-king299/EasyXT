# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
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
    logger.info("\n" + "=" * 70)
    logger.info(text)
    logger.info("=" * 70)

def print_check(name, status, message=""):
    """打印检查结果"""
    icon = "✓" if status else "✗"
    logger.info(f"\n[{icon}] {name}")
    if message:
        logger.info(f"    {message}")

def main():
    print_header("EasyXT 环境检查工具")

    # 1. Python版本检查
    logger.info("\n[1] Python版本检查")
    py_version = sys.version_info
    logger.info(f"    当前版本: Python {py_version.major}.{py_version.minor}.{py_version.micro}")

    if py_version >= (3, 9):
        logger.info("    ✓ 版本符合要求 (>=3.9)")
    else:
        logger.info("    ✗ 版本过低，建议升级到Python 3.9+")

    # 2. QMT连接检查（平台自适应）
    is_linux_or_mac = sys.platform.startswith('linux') or sys.platform == 'darwin'

    if is_linux_or_mac:
        # Linux/Mac：检查 xqshare 远程连接配置
        logger.info("\n[2] xqshare远程连接检查（Mac/Linux）")
        xq_host = os.environ.get('XQSHARE_REMOTE_HOST', '')
        xq_port = os.environ.get('XQSHARE_REMOTE_PORT', '18812')

        if xq_host:
            logger.info(f"    ✓ xqshare已配置: {xq_host}:{xq_port}")
            try:
                from xqshare.client import connect
                logger.info("    ✓ xqshare模块已安装")
            except ImportError:
                logger.info("    ⚠️ xqshare模块未安装")
                logger.info("    运行: pip install xqshare")
        else:
            logger.info("    ⚠️ xqshare未配置（非报错，QMT仅在Windows可用）")
            logger.info("    如使用远程QMT，在.env中配置：")
            logger.info("    XQSHARE_REMOTE_HOST=你的Windows机器IP")
            logger.info("    XQSHARE_REMOTE_PORT=18812")
            logger.info("    并运行: pip install xqshare")
            logger.info("")
            logger.info("    如果只用Tushare/TDX数据源（不做交易），忽略此项。")
    else:
        # Windows：检查 xtquant 本地安装
        logger.info("\n[2] xtquant模块检查")
        try:
            from xtquant import datacenter
            logger.info("    ✓ xtquant已安装")

            try:
                from xtquant import xtdata
                logger.info("    ✓ xtquant版本正确（特殊版本）")
            except ImportError:
                logger.info("    ⚠️ xtquant版本可能不完整")
                logger.info("    建议：下载项目提供的特殊版本")

        except ImportError as e:
            logger.info("    ✗ xtquant未安装或版本错误")
            logger.info("    解决方案：")
            logger.info("    1. 访问：https://github.com/quant-king299/EasyXT/releases/tag/v1.0.0")
            logger.info("    2. 下载：xtquant.rar")
            logger.info("    3. 解压到项目根目录")

    # 3. easy_xt模块检查
    logger.info("\n[3] easy_xt模块检查")
    try:
        from easy_xt import get_api
        logger.info("    ✓ easy_xt已安装")

        # 尝试获取API实例
        try:
            api = get_api()
            logger.info("    ✓ easy_xt可以正常导入")
        except Exception as e:
            logger.info(f"    ⚠️ easy_xt导入警告: {e}")

    except ImportError:
        logger.info("    ✗ easy_xt未安装")
        logger.info("    解决方案：pip install -e ./easy_xt")

    # 4. easyxt_backtest模块检查
    logger.info("\n[4] easyxt_backtest模块检查")
    try:
        import easyxt_backtest
        logger.info("    ✓ easyxt_backtest已安装")
    except ImportError:
        logger.info("    ⚠️ easyxt_backtest未安装（可选）")
        logger.info("    如需回测功能，请运行：pip install -e ./easyxt_backtest")

    # 5. DuckDB数据库检查
    logger.info("\n[5] DuckDB数据库检查")
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
            logger.info(f"    ✓ 找到数据库: {expanded_path}")

            # 检查数据库内容
            try:
                import duckdb
                con = duckdb.connect(str(expanded_path), read_only=True)

                # 检查表
                tables = con.execute("SHOW TABLES").fetchall()
                logger.info(f"    ✓ 数据表数量: {len(tables)}")

                # 检查数据量
                if tables:
                    table_names = [t[0] for t in tables]
                    if 'stock_data' in table_names:
                        count = con.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]
                        logger.info(f"    ✓ stock_data表记录数: {count:,}")

                con.close()
                db_found = True
                break
            except Exception as e:
                logger.info(f"    ⚠️ 数据库存在但无法读取: {e}")

    if not db_found:
        logger.info("    ✗ 未找到DuckDB数据库")
        logger.info("    解决方案：")
        logger.info("    1. 运行 python run_gui.py")
        logger.info("    2. 切换到'📥 Tushare下载'标签页")
        logger.info("    3. 下载股票数据（会自动创建数据库）")
        logger.info("    或运行：cd '101因子/101因子分析平台/scripts' && python init_data.py")

    # 6. Tushare配置检查
    logger.info("\n[6] Tushare配置检查")
    try:
        from dotenv import load_dotenv
        load_dotenv()

        token = os.getenv('TUSHARE_TOKEN')
        if token:
            logger.info(f"    ✓ Token已配置: {token[:10]}...")
            logger.info(f"    ✓ Token长度: {len(token)} 字符")

            # 验证Token长度（Tushare Token通常是32字符）
            if len(token) == 32:
                logger.info("    ✓ Token格式正确")
            else:
                logger.info("    ⚠️ Token长度可能不正确（通常为32字符）")
        else:
            logger.info("    ⚠️ Token未配置")
            logger.info("    解决方案：")
            logger.info("    1. 在项目根目录创建 .env 文件")
            logger.info("    2. 添加：TUSHARE_TOKEN=你的Token")
            logger.info("    3. 或者运行 GUI 在'Tushare下载'标签页中输入")
    except ImportError:
        logger.info("    ⚠️ python-dotenv未安装")
        logger.info("    解决方案：pip install python-dotenv")

    # 7. GUI依赖检查
    logger.info("\n[7] GUI依赖检查")
    gui_deps = {
        'PyQt5': 'PyQt5基础库',
        'pandas': 'DataFrame数据处理',
        'numpy': '数值计算库',
    }

    missing_gui_deps = []
    for package, description in gui_deps.items():
        try:
            __import__(package)
            logger.info(f"    ✓ {package:<15} - {description}")
        except ImportError:
            logger.info(f"    ✗ {package:<15} - {description} (未安装)")
            missing_gui_deps.append(package)

    if missing_gui_deps:
        logger.info(f"    解决方案：pip install {' '.join(missing_gui_deps)}")

    # 8. 项目结构检查
    logger.info("\n[8] 项目结构检查")
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
            logger.info(f"    ✓ {dir_name}/")
        else:
            logger.info(f"    ⚠️ {dir_name}/ 不存在")

    # 9. 配置文件检查
    logger.info("\n[9] 配置文件检查")
    config_files = {
        '.env': '环境变量配置',
        '.env.example': '环境变量模板',
        'requirements.txt': 'Python依赖列表',
    }

    for file_name, description in config_files.items():
        file_path = Path(file_name)
        if file_path.exists():
            logger.info(f"    ✓ {file_name:<20} - {description}")
        else:
            if file_name == '.env':
                logger.info(f"    ⚠️ {file_name:<20} - 建议创建（复制.env.example）")
            else:
                logger.info(f"    ✓ {file_name:<20} - {description}（可选）")

    # 10. 快速修复建议
    print_header("快速修复建议")

    issues = []

    # 检查QMT连接（平台自适应）
    if is_linux_or_mac:
        xq_host = os.environ.get('XQSHARE_REMOTE_HOST', '')
        if not xq_host:
            issues.append("1. xqshare未配置 → 如需远程QMT，在.env中设置XQSHARE_REMOTE_HOST")
    else:
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
        logger.info("\n发现以下问题，建议按顺序修复：\n")
        for issue in issues:
            logger.info(f"  {issue}")
        logger.info("\n详细解决方案请查看：TROUBLESHOOTING.md")
    else:
        logger.info("\n✓ 所有检查通过！你的环境配置正确。")
        logger.info("\n下一步：")
        logger.info("  1. 查看 README.md 了解项目结构")
        logger.info("  2. 从 学习实例/01_基础入门.py 开始学习")
        logger.info("  3. 或运行 python run_gui.py 启动GUI应用")

    print_header("检查完成")

    logger.info("\n💡 提示：")
    logger.info("  - 如果遇到问题，查看 TROUBLESHOOTING.md 获取详细帮助")
    logger.info("  - 或访问：https://github.com/quant-king299/EasyXT/issues")
    logger.info("  - 关注公众号：王者quant")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n检查被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n\n错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
