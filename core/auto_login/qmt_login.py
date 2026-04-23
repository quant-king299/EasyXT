"""
QMT 自动登录模块

使用 pywinauto 实现 QMT/miniQMT 的自动登录
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

try:
    import pywinauto
    from pywinauto.application import Application, ProcessNotFoundError
except ImportError:
    raise ImportError(
        "请先安装 pywinauto: pip install pywinauto\n"
        "或者在安装时使用: pip install -e .[auto_login]"
    )

from core.config.config_manager import ConfigManager


class QMTAutoLogin:
    """QMT 自动登录类"""

    def __init__(
        self,
        exe_path: Optional[str] = None,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
        data_dir: Optional[str] = None
    ):
        """
        初始化自动登录

        Args:
            exe_path: QMT可执行文件路径，默认从配置读取
            user_id: QMT用户ID，默认从配置读取
            password: QMT密码，默认从配置读取
            data_dir: QMT数据目录，默认从配置读取
        """
        self.logger = self._setup_logger()

        # 从配置或参数获取
        config = ConfigManager.get_config()

        self.exe_path = exe_path or config.get('QMT_EXE_PATH')
        self.user_id = user_id or config.get('QMT_USER_ID')
        self.password = password or config.get('QMT_PASSWORD')
        self.data_dir = data_dir or config.get('QMT_DATA_DIR')

        # 验证必要参数
        if not all([self.exe_path, self.user_id, self.password]):
            missing = []
            if not self.exe_path:
                missing.append('QMT_EXE_PATH')
            if not self.user_id:
                missing.append('QMT_USER_ID')
            if not self.password:
                missing.append('QMT_PASSWORD')

            raise ValueError(
                f"缺少必要配置，请在 .env 文件中设置：\n"
                f"{', '.join(missing)}\n\n"
                f"参考 .env.example 文件进行配置"
            )

        self.logger.info(f"QMT路径: {self.exe_path}")
        self.logger.info(f"用户ID: {self.user_id}")

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('QMTAutoLogin')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def login(self, restart: bool = False, timeout: int = 60) -> bool:
        """
        执行自动登录

        Args:
            restart: 如果QMT已运行，是否重启
            timeout: 登录超时时间（秒）

        Returns:
            bool: 登录是否成功
        """
        try:
            # 检查是否已运行
            app = self._is_running()
            if app:
                if restart:
                    self.logger.info("QMT正在运行，准备重启...")
                    app.kill()
                    self._clean_temp_files()
                    time.sleep(3)
                else:
                    self.logger.info("QMT已在运行中")
                    if self._check_logged_in(app):
                        self.logger.info(f"用户 {self.user_id} 已登录")
                        return True
                    self.logger.info("未登录，准备登录...")

            # 启动QMT
            self.logger.info("正在启动QMT...")
            app = Application(backend="uia").start(self.exe_path, timeout=10)
            time.sleep(3)

            # 检查是否已登录
            if self._check_logged_in(app):
                self.logger.info("已经登录，跳过")
                return True

            # 执行登录流程
            return self._do_login(app, timeout)

        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False

    def _is_running(self) -> Optional[Application]:
        """检查QMT是否正在运行"""
        try:
            return Application(backend="uia").connect(
                path=self.exe_path,
                timeout=2
            )
        except (ProcessNotFoundError, Exception):
            return None

    def _check_logged_in(self, app: Application) -> bool:
        """检查是否已登录"""
        try:
            top_window = app.top_window()
            window_text = top_window.window_text()

            # 如果窗口标题包含用户ID，说明已登录
            if self.user_id in window_text:
                return True

            # 检查是否有登录窗口的特征
            # 登录窗口通常包含"登录"、"密码"等关键词
            if any(keyword in window_text for keyword in ["登录", "密码"]):
                return False

            # 如果没有登录窗口，可能已经登录
            return True

        except Exception as e:
            self.logger.debug(f"检查登录状态异常: {e}")
            return False

    def _do_login(self, app: Application, timeout: int) -> bool:
        """
        执行登录流程

        Args:
            app: pywinauto Application对象
            timeout: 超时时间

        Returns:
            bool: 是否登录成功
        """
        try:
            win = app.top_window()
            win.set_focus()

            self.logger.info("正在填写用户名...")
            # 尝试找到用户名输入框并填写
            # 常见的定位方式：ComboBox.Edit 或 Edit1
            try:
                edit = win.ComboBox.Edit if win.ComboBox.Exists() else win.Edit1
                edit.click_input()
                edit.type_keys("^a" + self.user_id)
                time.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"填写用户名失败（尝试备用方案）: {e}")
                # 备用方案：使用Tab键导航
                import pyautogui
                pyautogui.press('tab')
                time.sleep(0.3)
                import pyautogui
                pyautogui.typewrite(self.user_id)
                time.sleep(0.5)

            self.logger.info("正在填写密码...")
            # 填写密码
            try:
                password_edit = win.Edit2 if win.Edit2.Exists() else win.Edit if len(win.children()) > 1 else None
                if password_edit:
                    password_edit.click_input()
                    password_edit.type_keys(self.password)
                else:
                    # 备用方案
                    import pyautogui
                    pyautogui.press('tab')
                    time.sleep(0.3)
                    import pyautogui
                    pyautogui.typewrite(self.password)
                time.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"填写密码失败（尝试备用方案）: {e}")

            # 处理验证码（如果有）
            if self._has_captcha(win):
                self.logger.info("检测到验证码，尝试处理...")
                if not self._handle_captcha(win):
                    self.logger.warning("验证码处理失败，请手动输入")
                    # 给用户30秒时间手动输入
                    self.logger.info("等待30秒手动输入...")
                    time.sleep(30)

            # 点击登录按钮或按回车
            self.logger.info("正在登录...")
            try:
                # 尝试找到登录按钮
                login_btn = win.Button3 if win.Button3.Exists() else win.Button if len(win.buttons()) > 0 else None
                if login_btn:
                    login_btn.click()
                else:
                    # 按回车键
                    import pyautogui
                    pyautogui.press('enter')
            except Exception:
                import pyautogui
                pyautogui.press('enter')

            # 等待登录完成
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(2)
                if self._check_logged_in(app):
                    self.logger.info("✓ 登录成功！")
                    return True

            self.logger.error("登录超时")
            return False

        except Exception as e:
            self.logger.error(f"登录流程异常: {e}")
            return False

    def _has_captcha(self, window) -> bool:
        """检查是否有验证码"""
        try:
            # 检查是否有验证码相关的控件
            # 通常验证码是一个Custom控件或者Edit控件
            if hasattr(window, 'Custom') and window.Custom.Exists():
                return True
            if hasattr(window, 'Edit3') and window.Edit3.Exists():
                return True
            return False
        except Exception:
            return False

    def _handle_captcha(self, window) -> bool:
        """
        处理验证码

        QMT的验证码通常是简单的数学计算题，如：3+4=?
        """
        try:
            # 尝试使用OCR识别验证码（如果安装了pytesseract）
            try:
                import cv2
                import numpy as np
                import pytesseract

                # 截取验证码图片
                if hasattr(window, 'Custom') and window.Custom.Exists():
                    captcha_img = window.Custom.capture_as_image()

                    # 转换为OpenCV格式
                    img = cv2.cvtColor(np.array(captcha_img), cv2.COLOR_RGB2BGR)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                    # OCR识别
                    code = pytesseract.image_to_string(img)
                    self.logger.info(f"识别验证码: {code}")

                    # 计算数学表达式
                    code = code.strip().replace('=', '').replace(' ', '')
                    if code and any(c in code for c in '+-*/'):
                        result = str(eval(code))
                        self.logger.info(f"计算结果: {result}")

                        # 填写结果
                        if hasattr(window, 'Edit3') and window.Edit3.Exists():
                            window.Edit3.click_input()
                            window.Edit3.type_keys(result)
                        return True

            except ImportError:
                self.logger.warning("未安装pytesseract/opencv-python，跳过自动识别")

            return False

        except Exception as e:
            self.logger.debug(f"处理验证码异常: {e}")
            return False

    def _clean_temp_files(self):
        """清理临时文件"""
        if not self.data_dir:
            return

        try:
            data_dir = Path(self.data_dir)
            if not data_dir.exists():
                return

            # 清理 down_queue_ 开头的临时文件（除了包含 xtmodel 的）
            temp_files = list(data_dir.glob("down_queue_*"))
            for f in temp_files:
                if "xtmodel" not in f.name:
                    self.logger.info(f"删除临时文件: {f.name}")
                    try:
                        f.unlink()
                    except PermissionError:
                        pass

        except Exception as e:
            self.logger.debug(f"清理临时文件异常: {e}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='miniQMT 自动登录工具')
    parser.add_argument('--restart', action='store_true', help='如果QMT已运行，先关闭再启动')
    parser.add_argument('--timeout', type=int, default=60, help='登录超时时间（秒）')

    args = parser.parse_args()

    try:
        auto_login = QMTAutoLogin()
        success = auto_login.login(restart=args.restart, timeout=args.timeout)

        if success:
            print("\n✓ 登录成功！")
            return 0
        else:
            print("\n✗ 登录失败，请检查配置或手动操作")
            return 1

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
