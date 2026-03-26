#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据下载GUI组件
集成到本地数据管理界面中
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QDateEdit, QScrollArea, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QTextCursor

import pandas as pd
import numpy as np

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TushareDownloadThread(QThread):
    """Tushare下载线程"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, task_type, **kwargs):
        super().__init__()
        self.task_type = task_type  # 'financial', 'dividend', 'moneyflow', 'holders', etc.
        self.kwargs = kwargs
        self._is_running = True

        # 导入下载器
        try:
            from tushare_manager.tushare_downloader import TushareDownloader
            from tushare_manager.tushare_config import TushareConfig
            self.TushareDownloader = TushareDownloader
            self.TushareConfig = TushareConfig
        except ImportError as e:
            self.log_signal.emit(f"[ERROR] 导入Tushare模块失败: {e}")
            self.TushareDownloader = None

    def _get_db_path(self):
        """获取DuckDB数据库路径（自动检测）"""
        common_paths = [
            'D:/StockData/stock_data.ddb',
            'C:/StockData/stock_data.ddb',
            'E:/StockData/stock_data.ddb',
            './data/stock_data.ddb',
        ]
        for path in common_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path
        return 'D:/StockData/stock_data.ddb'

    def run(self):
        """运行下载任务"""
        if self.TushareDownloader is None:
            self.error_signal.emit("Tushare模块未安装")
            return

        try:
            if self.task_type == 'financial':
                self._download_financial()
            elif self.task_type == 'dividend':
                self._download_dividend()
            elif self.task_type == 'moneyflow':
                self._download_moneyflow()
            elif self.task_type == 'holders':
                self._download_holders()
            elif self.task_type == 'all':
                self._download_all()
            else:
                self.error_signal.emit(f"未知任务类型: {self.task_type}")

        except Exception as e:
            import traceback
            error_msg = f"下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _get_stock_list(self):
        """获取股票列表"""
        # 如果用户指定了股票列表
        stock_list = self.kwargs.get('stock_list', [])
        if stock_list:
            return stock_list

        # 否则从数据库获取
        try:
            import duckdb
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            con = duckdb.connect(db_path, read_only=True)

            # 获取所有股票代码
            result = con.execute("""
                SELECT DISTINCT stock_code
                FROM stock_daily
                WHERE symbol_type = 'stock'
                ORDER BY stock_code
            """).fetchdf()

            con.close()
            return result['stock_code'].tolist()

        except Exception as e:
            self.log_signal.emit(f"[WARN] 从数据库获取股票列表失败: {e}，使用默认股票")
            return ['000001.SZ', '600000.SH', '600519.SH']

    def _download_financial(self):
        """下载财务数据"""
        try:
            downloader = self.TushareDownloader()

            self.log_signal.emit("=" * 70)
            self.log_signal.emit("  【Tushare财务数据下载】")
            self.log_signal.emit("=" * 70)

            # 获取股票列表
            stock_list = self._get_stock_list()
            years = self.kwargs.get('years', 5)

            self.log_signal.emit(f"股票数量: {len(stock_list)}")
            self.log_signal.emit(f"时间范围: 最近{years}年")
            self.log_signal.emit("")

            # 批量下载
            result = downloader.batch_download_financial(
                stock_list=stock_list,
                years=years,
                progress_callback=lambda curr, total, msg: self._on_progress(curr, total, msg)
            )

            self.finished_signal.emit(result)
            self.log_signal.emit("")
            self.log_signal.emit(f"✅ 完成! 成功: {result['success']}, 失败: {result['failed']}")

        except Exception as e:
            import traceback
            self.log_signal.emit(f"[ERROR] 下载财务数据失败: {e}\n{traceback.format_exc()}")

    def _download_dividend(self):
        """下载分红数据"""
        try:
            downloader = self.TushareDownloader()

            self.log_signal.emit("=" * 70)
            self.log_signal.emit("  【Tushare分红数据下载】")
            self.log_signal.emit("=" * 70)

            # 获取股票列表
            stock_list = self._get_stock_list()

            self.log_signal.emit(f"股票数量: {len(stock_list)}")
            self.log_signal.emit("")

            # 批量下载
            result = downloader.batch_download_dividend(
                stock_list=stock_list,
                progress_callback=lambda curr, total, msg: self._on_progress(curr, total, msg)
            )

            self.finished_signal.emit(result)
            self.log_signal.emit("")
            self.log_signal.emit(f"✅ 完成! 成功: {result['success']}, 失败: {result['failed']}")

        except Exception as e:
            import traceback
            self.log_signal.emit(f"[ERROR] 下载分红数据失败: {e}\n{traceback.format_exc()}")

    def _download_moneyflow(self):
        """下载资金流向数据"""
        try:
            downloader = self.TushareDownloader()
            import duckdb

            self.log_signal.emit("=" * 70)
            self.log_signal.emit("  【Tushare资金流向数据下载】")
            self.log_signal.emit("=" * 70)

            # 获取股票列表
            stock_list = self._get_stock_list()

            # 获取日期范围
            start_date = self.kwargs.get('start_date')
            end_date = self.kwargs.get('end_date')

            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            self.log_signal.emit(f"股票数量: {len(stock_list)}")
            self.log_signal.emit(f"时间范围: {start_date} ~ {end_date}")
            self.log_signal.emit("")

            success_count = 0
            failed_count = 0

            # 生成日期列表
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            trade_dates = [d.strftime('%Y%m%d') for d in date_range]

            for i, stock_code in enumerate(stock_list[:100]):  # 限制100只股票测试
                if not self._is_running:
                    break

                self._on_progress(i + 1, min(len(stock_list), 100), f"{stock_code}")

                try:
                    df = downloader.download_moneyflow(ts_code=stock_code)
                    if df is not None and not df.empty:
                        downloader.save_to_duckdb(df, 'tushare_moneyflow',
                                                  primary_keys=['ts_code', 'trade_date'])
                        success_count += 1
                except Exception as e:
                    failed_count += 1
                    self.log_signal.emit(f"[WARN] {stock_code}: {e}")

            result = {
                'total': i + 1,
                'success': success_count,
                'failed': failed_count,
                'task_type': 'moneyflow'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 完成! 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            import traceback
            self.log_signal.emit(f"[ERROR] 下载资金流向失败: {e}\n{traceback.format_exc()}")

    def _download_holders(self):
        """下载股东数据"""
        try:
            downloader = self.TushareDownloader()

            self.log_signal.emit("=" * 70)
            self.log_signal.emit("  【Tushare股东数据下载】")
            self.log_signal.emit("=" * 70)

            stock_list = self._get_stock_list()[:50]  # 限制50只测试

            self.log_signal.emit(f"股票数量: {len(stock_list)}")
            self.log_signal.emit("")

            success_count = 0
            failed_count = 0

            for i, stock_code in enumerate(stock_list):
                if not self._is_running:
                    break

                self._on_progress(i + 1, len(stock_list), f"{stock_code}")

                try:
                    # 下载前十大股东
                    df = downloader.download_top10_holders(ts_code=stock_code)
                    if df is not None and not df.empty:
                        downloader.save_to_duckdb(df, 'tushare_top10_holders',
                                                  primary_keys=['ts_code', 'end_date'])
                        success_count += 1
                except Exception as e:
                    failed_count += 1

            result = {
                'total': len(stock_list),
                'success': success_count,
                'failed': failed_count,
                'task_type': 'holders'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 完成! 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            import traceback
            self.log_signal.emit(f"[ERROR] 下载股东数据失败: {e}\n{traceback.format_exc()}")

    def _download_all(self):
        """下载所有推荐数据"""
        self.log_signal.emit("开始批量下载所有Tushare数据...")

        # 按顺序下载各类数据
        tasks = ['dividend', 'financial', 'moneyflow', 'holders']

        for task in tasks:
            if not self._is_running:
                break

            self.log_signal.emit(f"\n开始下载: {task}")
            self.task_type = task
            if task == 'financial':
                self._download_financial()
            elif task == 'dividend':
                self._download_dividend()
            elif task == 'moneyflow':
                self._download_moneyflow()
            elif task == 'holders':
                self._download_holders()

    def _on_progress(self, current: int, total: int, message: str):
        """进度回调"""
        self.progress_signal.emit(current, total)
        self.log_signal.emit(f"[{current}/{total}] {message}")

    def stop(self):
        """停止下载"""
        self._is_running = False
        self.quit()
        self.wait()


class TushareDownloadWidget(QWidget):
    """Tushare数据下载组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_thread = None
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ============== Tushare配置区域 ==============
        config_group = QGroupBox("🔑 Tushare配置")
        config_layout = QGridLayout()

        # Token输入
        config_layout.addWidget(QLabel("Token:"), 0, 0)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("请输入Tushare Token（首次使用需要）")
        # 从环境变量读取 Token
        try:
            from config import get_env_config
            env_config = get_env_config()
            token = env_config.tushare_token
            if token:
                self.token_input.setText(token)
                self.token_input.setReadOnly(True)
                self.token_input.setStyleSheet("background-color: #f0f0f0;")
        except:
            pass
        config_layout.addWidget(self.token_input, 0, 1)

        # 测试连接按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        config_layout.addWidget(self.test_btn, 0, 2)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # ============== 数据类型选择 ==============
        data_group = QGroupBox("📊 数据类型选择")
        data_layout = QVBoxLayout()

        # 数据类型选择
        type_layout = QGridLayout()

        self.chk_financial = QCheckBox("💰 财务数据（利润表、资产负债表、现金流量表）")
        self.chk_financial.setChecked(True)
        type_layout.addWidget(self.chk_financial, 0, 0)

        self.chk_dividend = QCheckBox("🎁 分红送股数据")
        self.chk_dividend.setChecked(True)
        type_layout.addWidget(self.chk_dividend, 0, 1)

        self.chk_moneyflow = QCheckBox("💵 资金流向数据")
        self.chk_moneyflow.setChecked(False)
        type_layout.addWidget(self.chk_moneyflow, 1, 0)

        self.chk_holders = QCheckBox("👥 股东数据（前十大股东）")
        self.chk_holders.setChecked(False)
        type_layout.addWidget(self.chk_holders, 1, 1)

        self.chk_all = QCheckBox("📦 下载所有推荐数据")
        self.chk_all.setChecked(False)
        type_layout.addWidget(self.chk_all, 2, 0, 1, 2)

        data_layout.addLayout(type_layout)

        # 数据范围设置
        range_layout = QGridLayout()

        range_layout.addWidget(QLabel("数据年份:"), 0, 0)
        self.years_spinbox = QSpinBox()
        self.years_spinbox.setRange(1, 20)
        self.years_spinbox.setValue(5)
        range_layout.addWidget(self.years_spinbox, 0, 1)
        range_layout.addWidget(QLabel("年"), 0, 2)

        # 股票范围
        range_layout.addWidget(QLabel("股票范围:"), 1, 0)
        self.stock_range_combo = QComboBox()
        self.stock_range_combo.addItems(["全部A股", "指定股票", "沪深300", "中证500"])
        range_layout.addWidget(self.stock_range_combo, 1, 1)

        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("输入股票代码，逗号分隔（如：000001.SZ,600000.SH）")
        range_layout.addWidget(self.stock_input, 2, 0, 1, 3)

        data_layout.addLayout(range_layout)

        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # ============== 操作按钮 ==============
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton("🚀 开始下载")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        btn_layout.addWidget(self.download_btn)

        self.stop_btn = QPushButton("⏹ 停止下载")
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # ============== 进度条 ==============
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # ============== 日志输出 ==============
        log_group = QGroupBox("📝 下载日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(300)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)

        # 清空日志按钮
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_log_btn)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()

    def test_connection(self):
        """测试Tushare连接"""
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        self.log("正在测试Tushare连接...")

        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()

            # 测试API调用
            df = pro.trade_cal(exchange='SSE', start_date='20240101', end_date='20240110')

            if df is not None and len(df) > 0:
                QMessageBox.information(self, "成功", f"✅ Tushare连接成功！\n\n获取到 {len(df)} 条交易日历数据")
                self.log("✅ Tushare连接测试成功")
            else:
                QMessageBox.warning(self, "警告", "连接失败，请检查Token是否正确")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接失败：\n{str(e)}")
            self.log(f"❌ 连接测试失败: {e}")

    def start_download(self):
        """开始下载"""
        # 检查Token
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        # 保存Token配置
        try:
            from tushare_manager.tushare_config import TushareConfig
            config = TushareConfig()
            config.token = token
        except:
            pass

        # 确定下载类型
        if self.chk_all.isChecked():
            task_type = 'all'
        elif self.chk_financial.isChecked():
            task_type = 'financial'
        elif self.chk_dividend.isChecked():
            task_type = 'dividend'
        elif self.chk_moneyflow.isChecked():
            task_type = 'moneyflow'
        elif self.chk_holders.isChecked():
            task_type = 'holders'
        else:
            QMessageBox.warning(self, "警告", "请选择至少一种数据类型")
            return

        # 获取参数
        years = self.years_spinbox.value()
        stock_range = self.stock_range_combo.currentText()
        stock_list = []

        if stock_range == "指定股票":
            stock_input = self.stock_input.text().strip()
            if stock_input:
                stock_list = [s.strip() for s in stock_input.split(',')]
            else:
                QMessageBox.warning(self, "警告", "请输入股票代码")
                return

        # 清空日志
        self.log_text.clear()
        self.log("开始下载...")

        # 禁用下载按钮，启用停止按钮
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        # 创建并启动下载线程
        self.download_thread = TushareDownloadThread(
            task_type=task_type,
            stock_list=stock_list,
            years=years,
            db_path=None  # 自动检测
        )

        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.on_download_error)

        self.download_thread.start()

    def stop_download(self):
        """停止下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.log("正在停止下载...")
            self.download_thread.stop()
            self.log("已停止")

    def on_download_finished(self, result: dict):
        """下载完成"""
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        total = result.get('total', 0)
        success = result.get('success', 0)
        failed = result.get('failed', 0)

        QMessageBox.information(
            self, "完成",
            f"下载完成！\n\n总数: {total}\n成功: {success}\n失败: {failed}"
        )

        # 输出失败清单
        failed_list = result.get('failed_list', [])
        if failed_list:
            self.log("\n" + "=" * 70)
            self.log("失败清单:")
            for item in failed_list[:20]:  # 只显示前20条
                self.log(f"  ✗ {item}")
            if len(failed_list) > 20:
                self.log(f"  ... 还有 {len(failed_list) - 20} 条")
            self.log("=" * 70)

    def on_download_error(self, error: str):
        """下载错误"""
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        QMessageBox.critical(self, "错误", error)

    def update_progress(self, current: int, total: int):
        """更新进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"进度: {current}/{total} ({current*100//total if total > 0 else 0}%)")

    def log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    widget = TushareDownloadWidget()
    widget.setWindowTitle("Tushare数据下载")
    widget.resize(800, 700)
    widget.show()
    sys.exit(app.exec_())
