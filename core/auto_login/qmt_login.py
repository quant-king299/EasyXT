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
    from dotenv import load_dotenv
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

try:
    import pywinauto
    from pywinauto.application import Application, ProcessNotFoundError
except ImportError:
    raise ImportError(
        "请先安装 pywinauto: pip install pywinauto\n"
        "或者在安装时使用: pip install -e .[auto_login]"
    )


class QMTAutoLogin:
    """QMT 自动登录类"""

    def __init__(
        self,
        exe_path: Optional[str] = None,
        password: Optional[str] = None,
        data_dir: Optional[str] = None
    ):
        """
        初始化自动登录

        Args:
            exe_path: QMT可执行文件路径，默认从配置读取
            password: QMT密码，默认从配置读取
            data_dir: QMT数据目录，默认从配置读取

        注意：用户ID会自动显示，无需配置
        """
        self.logger = self._setup_logger()

        # 从环境变量或参数获取
        self.exe_path = exe_path or os.getenv('QMT_EXE_PATH')
        self.password = password or os.getenv('QMT_PASSWORD')
        self.data_dir = data_dir or os.getenv('QMT_DATA_DIR')

        # 验证必要参数
        if not all([self.exe_path, self.password]):
            missing = []
            if not self.exe_path:
                missing.append('QMT_EXE_PATH')
            if not self.password:
                missing.append('QMT_PASSWORD')

            raise ValueError(
                f"缺少必要配置，请在 .env 文件中设置：\n"
                f"{', '.join(missing)}\n\n"
                f"参考 .env.example 文件进行配置"
            )

        self.logger.info(f"QMT路径: {self.exe_path}")

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
                        self.logger.info("用户已登录")
                        return True
                    self.logger.info("未登录，准备登录...")

            # 启动QMT
            self.logger.info("正在启动QMT...")
            app = Application(backend="uia").start(self.exe_path, timeout=10)
            time.sleep(5)  # 增加等待时间，确保窗口完全加载

            # 检查是否已登录
            if self._check_logged_in(app):
                self.logger.info("检测到QMT已登录")
                return True

            # 未登录，执行登录流程
            self.logger.info("检测到登录界面，准备登录...")
            return self._do_login(app, timeout)

        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False

    def _get_user_id(self, app: Application) -> Optional[str]:
        """从QMT窗口获取自动显示的用户ID"""
        try:
            win = app.top_window()
            # 尝试从窗口标题或其他控件获取用户ID
            # 有些QMT版本会在登录窗口显示用户ID
            window_text = win.window_text()

            # 尝试从窗口文本中提取数字（可能是用户ID）
            import re
            numbers = re.findall(r'\d{8,12}', window_text)
            if numbers:
                return numbers[0]

            # 如果窗口标题包含用户ID
            if any(keyword in window_text for keyword in ["资金账号", "用户名", "UserID"]):
                # 尝试提取ID
                for num in numbers:
                    if 8 <= len(num) <= 12:  # QMT用户ID通常是8-12位数字
                        return num

            return None
        except Exception as e:
            self.logger.debug(f"获取用户ID失败: {e}")
            return None

    def _get_captcha_from_window(self, app: Application) -> Optional[str]:
        """从QMT窗口获取自动显示的验证码"""
        try:
            win = app.top_window()
            window_text = str(win.window_text())

            self.logger.debug(f"窗口文本: {window_text[:200]}...")  # 打印前200个字符

            # 尝试从窗口文本中提取验证码
            # QMT验证码通常是字母数字组合，如：598hi
            import re
            # 匹配 3-5位数字 + 2-3位字母 的模式（如：598hi, 123ab）
            captcha_pattern = re.compile(r'(\d{3,5}[a-zA-Z]{2,3})')
            captcha = captcha_pattern.search(window_text)

            if captcha:
                captcha_code = captcha.group(1)
                self.logger.info(f"从窗口获取到验证码: {captcha_code}")
                return captcha_code

            # 如果没有找到，尝试其他模式
            # 可能是纯数字或者纯字母
            alt_pattern = re.compile(r'(\d{4,6})')
            alt_captcha = alt_pattern.search(window_text)
            if alt_captcha:
                captcha_code = alt_captcha.group(1)
                self.logger.info(f"从窗口获取到验证码（纯数字）: {captcha_code}")
                return captcha_code

            self.logger.debug("未找到验证码")
            return None
        except Exception as e:
            self.logger.debug(f"获取验证码失败: {e}")
            return None

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

            self.logger.debug(f"窗口标题: {window_text}")

            # 检查是否有登录窗口的特征
            # 登录窗口通常包含"登录"、"密码"、"账号"等关键词
            login_keywords = ["登录", "密码", "账号", "用户", "Login", "Password", "User"]
            if any(keyword in window_text for keyword in login_keywords):
                self.logger.debug("检测到登录窗口特征")
                return False

            # 检查是否有已登录窗口的特征
            # 已登录窗口通常包含"委托"、"持仓"、"交易"等关键词
            logged_in_keywords = ["委托", "持仓", "交易", "行情", "资产", "策略"]
            if any(keyword in window_text for keyword in logged_in_keywords):
                self.logger.debug("检测到已登录窗口特征")
                return True

            # 如果窗口标题是"miniQMT"或"QMT"，可能已经登录
            if "QMT" in window_text or "mini" in window_text.lower():
                self.logger.debug("检测到QMT主窗口")
                # 进一步检查：尝试找密码输入框，如果有说明在登录界面
                if self._has_password_field(top_window):
                    self.logger.debug("发现密码输入框，判断为登录界面")
                    return False
                return True

            # 默认情况下，认为未登录
            self.logger.debug("无法确定登录状态，默认为未登录")
            return False

        except Exception as e:
            self.logger.debug(f"检查登录状态异常: {e}")
            return False

    def _has_password_field(self, window) -> bool:
        """检查窗口是否有密码输入框"""
        try:
            # 检查是否有密码相关的Edit控件
            # 通常密码输入框是Edit2或包含"密码"的控件
            if hasattr(window, 'Edit2') and window.Edit2.Exists():
                return True
            if hasattr(window, 'Edit'):
                for edit in window.children(class_name='Edit'):
                    if '密码' in str(edit.window_text()) or 'password' in str(edit.window_text()).lower():
                        return True
            return False
        except Exception:
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
            # 重新连接到窗口（防止窗口句柄失效）
            try:
                win = app.top_window()
            except Exception as e:
                self.logger.warning(f"无法获取窗口，尝试重新连接: {e}")
                time.sleep(2)
                try:
                    app = Application(backend="uia").connect(path=self.exe_path, timeout=10)
                    win = app.top_window()
                except Exception as e2:
                    self.logger.error(f"重新连接失败: {e2}")
                    return False

            win.set_focus()
            time.sleep(1)  # 等待窗口激活

            # 获取自动显示的用户ID（用于验证）
            user_id = self._get_user_id(app)
            if user_id:
                self.logger.info(f"检测到用户ID: {user_id}")

            # 获取自动显示的验证码
            captcha = self._get_captcha_from_window(app)

            self.logger.info("正在填写密码...")
            # 使用pyautogui模拟键盘操作（更可靠）
            try:
                import pyautogui

                # 方法1：尝试使用Tab键导航到密码框
                self.logger.debug("使用Tab键导航到密码框...")
                pyautogui.press('tab')  # 从用户ID框跳到密码框
                time.sleep(0.5)

                # 清空密码框
                pyautogui.hotkey('ctrl', 'a')  # 全选
                time.sleep(0.2)

                # 如果有验证码，先输入验证码
                if captcha:
                    self.logger.info(f"输入验证码: {captcha}")
                    pyautogui.typewrite(captcha, interval=0.05)
                    time.sleep(0.3)

                # 输入密码
                self.logger.info("输入密码...")
                pyautogui.typewrite(self.password, interval=0.05)
                time.sleep(0.5)

                self.logger.info("密码填写完成")
            except Exception as e:
                self.logger.error(f"填写密码失败: {e}")
                # 给用户手动输入的机会
                self.logger.info("请手动输入密码...")
                time.sleep(10)  # 给用户10秒时间手动输入

            # 点击登录按钮或按回车
            self.logger.info("正在登录（按回车键）...")
            try:
                import pyautogui
                # 使用回车键登录（最可靠的方法）
                pyautogui.press('enter')
                self.logger.info("已按回车键，等待登录...")
                time.sleep(3)  # 等待登录处理
            except Exception as e:
                self.logger.error(f"按回车键失败: {e}")
                return False

            # 点击登录按钮或按回车
            self.logger.info("正在登录（按回车键）...")
            try:
                import pyautogui
                # 使用回车键登录（最可靠的方法）
                pyautogui.press('enter')
                self.logger.info("已按回车键")
            except Exception as e:
                self.logger.error(f"按回车键失败: {e}")
                return False

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

    def _has_captcha(self, app: Application) -> bool:
        """检查是否有验证码"""
        try:
            win = app.top_window()

            # 方法1：检查窗口文本是否包含"验证码"关键词
            window_text = str(win.window_text())
            if '验证码' in window_text or 'captcha' in window_text.lower():
                self.logger.debug("窗口文本包含验证码关键词")
                return True

            # 方法2：检查是否有多个Edit框（通常登录界面有2个Edit：用户名+密码，有验证码时会有3个）
            edit_count = 0
            if hasattr(win, 'children'):
                for child in win.children():
                    if 'Edit' in str(child.class_name()):
                        edit_count += 1

            if edit_count >= 3:
                self.logger.debug(f"检测到{edit_count}个Edit框，可能需要验证码")
                return True

            return False
        except Exception as e:
            self.logger.debug(f"检查验证码异常: {e}")
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
