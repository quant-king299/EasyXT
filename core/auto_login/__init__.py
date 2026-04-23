"""
miniQMT 自动登录模块

提供 QMT/miniQMT 的自动登录功能，支持：
- 自动填写用户名和密码
- 验证码识别（数学计算题）
- 登录状态检测
- 临时文件清理

依赖安装：
pip install pywinauto

使用示例：
from core.auto_login import QMTAutoLogin

auto_login = QMTAutoLogin()
auto_login.login()
"""

from .qmt_login import QMTAutoLogin

__all__ = ['QMTAutoLogin']
