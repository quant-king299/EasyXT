# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
"""
启动101因子平台Web应用
"""

import subprocess
import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 获取项目路径
project_root = Path(__file__).parent.parent.parent.absolute()
app_path = project_root / 'easyxt_backtest' / 'web_app' / 'streamlit_app.py'

logger.info("=" * 80)
logger.info("🚀 启动101因子平台Web应用")
logger.info("=" * 80)
logger.info(f"\n📁 应用路径: {app_path}")
logger.info(f"\n⏳ 正在启动Streamlit服务器...")
logger.info(f"\n💡 启动后请在浏览器中访问:")
logger.info(f"   - Local URL: http://localhost:8501")
logger.info(f"\n" + "=" * 80 + "\n")

# 启动Streamlit
subprocess.run([
    sys.executable, '-m', 'streamlit', 'run',
    str(app_path),
    '--server.port=8501',
    '--server.address=0.0.0.0',
    '--browser.gatherUsageStats=false'
])
