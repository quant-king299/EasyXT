# -*- coding: utf-8 -*-
"""
跨平台剪贴板工具

Windows 上使用原生 API（不依赖 OLE），避免 CO_E_NOTINITIALIZED 错误。
非 Windows 平台使用 QApplication.clipboard()。
"""

import sys


def copy_text(text: str) -> bool:
    """将纯文本复制到系统剪贴板。返回 True 表示成功。"""
    if not text:
        return False

    if sys.platform == "win32":
        return _win32_copy_text(text)
    else:
        return _qt_copy_text(text)


def _qt_copy_text(text: str) -> bool:
    """通过 Qt 剪贴板复制（非 Windows 平台）"""
    try:
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        return True
    except Exception:
        return False


def _win32_copy_text(text: str) -> bool:
    """Windows 原生剪贴板 API（绕过 OLE，避免 CO_E_NOTINITIALIZED）"""
    import ctypes

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # 编码为 UTF-16LE（带 null 终止符）
    encoded = text.encode("utf-16-le") + b"\x00\x00"
    buf_len = len(encoded)

    hmem = kernel32.GlobalAlloc(GMEM_MOVEABLE, buf_len)
    if not hmem:
        return _qt_copy_text(text)  # fallback

    ptr = kernel32.GlobalLock(hmem)
    if not ptr:
        kernel32.GlobalFree(hmem)
        return _qt_copy_text(text)

    try:
        ctypes.memmove(ptr, encoded, buf_len)
    finally:
        kernel32.GlobalUnlock(hmem)

    if not user32.OpenClipboard(0):
        kernel32.GlobalFree(hmem)
        return _qt_copy_text(text)

    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, hmem):
            kernel32.GlobalFree(hmem)
            return False
    finally:
        user32.CloseClipboard()

    # hmem 现在由系统管理，不要释放
    return True
