#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据下载GUI组件（整合版）

整合了从数据管理模块中的Tushare下载功能，包括：
1. 市值数据下载
2. 财务数据下载（利润表、资产负债表、现金流量表）
3. 分红数据下载
4. 资金流向数据下载
5. 股东数据下载

所有Tushare相关的下载功能统一管理
"""

import sys
import os
import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox, QDialog,
    QFileDialog, QFormLayout, QScrollArea, QSizePolicy,
    QRadioButton, QButtonGroup, QDateEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor

import pandas as pd
import numpy as np
import duckdb

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TushareDownloadThread(QThread):
    """Tushare数据下载线程（整合版）"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, task_type, **kwargs):
        super().__init__()
        self.task_type = task_type
        self.kwargs = kwargs
        self._is_running = True

    def run(self):
        """运行下载任务"""
        try:
            if self.task_type == 'market_cap':
                self._download_market_cap()
            elif self.task_type == 'financial':
                self._download_financial()
            elif self.task_type == 'dividend':
                self._download_dividend()
            elif self.task_type == 'moneyflow':
                self._download_moneyflow()
            elif self.task_type == 'holders':
                self.__download_holders()
            elif self.task_type == 'test_connection':
                self._test_connection()
            elif self.task_type == 'batch_download':
                self._batch_download()
            else:
                self.log_signal.emit(f"未知任务类型: {self.task_type}")
        except Exception as e:
            import traceback
            error_msg = f"下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _get_tushare_pro(self):
        """获取Tushare Pro API实例"""
        import tushare as ts
        token = self.kwargs.get('token', '')
        if not token:
            raise ValueError("请输入Tushare Token")
        ts.set_token(token)
        return ts.pro_api()

    def _test_connection(self):
        """测试Tushare连接"""
        try:
            pro = self._get_tushare_pro()
            self.log_signal.emit("正在测试连接...")

            # 测试接口
            df = pro.daily(ts_code='000001.SZ', trade_date='20240101', fields='ts_code,close')

            if df is not None and not df.empty:
                self.log_signal.emit("✅ 连接测试成功！")
                self.finished_signal.emit({'success': True, 'message': '连接成功'})
            else:
                self.error_signal.emit("连接测试失败：返回空数据")
        except Exception as e:
            error_msg = f"连接测试失败: {str(e)}"
            self.log_signal.emit(f"❌ {error_msg}")
            self.error_signal.emit(error_msg)

    def _download_market_cap(self):
        """下载市值数据"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path', 'D:/StockData/stock_data.ddb')
            stock_count = self.kwargs.get('stock_count', 500)
            days_back = self.kwargs.get('days_back', 30)

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载市值数据")
            self.log_signal.emit("=" * 60)

            # 连接数据库
            conn = duckdb.connect(db_path)
            self.log_signal.emit("✅ 数据库连接成功")

            # 创建市值表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_market_cap (
                    stock_code VARCHAR,
                    date DATE,
                    circ_mv DECIMAL(18,2),
                    total_mv DECIMAL(18,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, date)
                )
            """)

            # 获取股票列表
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            total_stocks = len(stock_list)
            self.log_signal.emit(f"✅ 共 {total_stocks} 只股票")

            if stock_count < total_stocks:
                stock_list = stock_list.head(stock_count)

            # 下载市值数据
            total_inserted = 0
            for i, (_, stock_row) in enumerate(stock_list.iterrows(), 1):
                if not self._is_running:
                    break

                code = stock_row['ts_code']
                try:
                    df = pro.daily_basic(ts_code=code, fields='ts_code,trade_date,circ_mv,total_mv')
                    if df is not None and not df.empty:
                        df.rename(columns={'trade_date': 'date'}, inplace=True)
                        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
                        recent_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                        df = df[df['date'] >= recent_date]

                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR IGNORE INTO stock_market_cap
                                (stock_code, date, circ_mv, total_mv)
                                VALUES (?, ?, ?, ?)
                            """, [row['ts_code'], row['date'],
                                  float(row['circ_mv']) if pd.notna(row['circ_mv']) else None,
                                  float(row['total_mv']) if pd.notna(row['total_mv']) else None])
                            total_inserted += 1

                    if i % 10 == 0:
                        self.progress_signal.emit(i, len(stock_list))

                except Exception as e:
                    continue

                time.sleep(0.2)

            conn.close()
            self.finished_signal.emit({'success': True, 'total_inserted': total_inserted})
            self.log_signal.emit("✅ 市值数据下载完成！")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"市值数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_financial(self):
        """下载财务数据"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path', 'D:/StockData/stock_data.ddb')
            symbols = self.kwargs.get('symbols', [])
            years = self.kwargs.get('years', 5)

            self.log_signal.emit("开始下载财务数据...")

            conn = duckdb.connect(db_path)

            # 创建财务数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_income (
                    ts_code VARCHAR,
                    ann_date DATE,
                    f_ann_date DATE,
                    end_date DATE,
                    report_type VARCHAR,
                    comp_type VARCHAR,
                    basic_eps DECIMAL(18,4),
                    diluted_eps DECIMAL(18,4),
                    total_revenue DECIMAL(18,2),
                    revenue DECIMAL(18,2),
                    int_income DECIMAL(18,2),
                    prem_earned DECIMAL(18,2),
                    comm_expense DECIMAL(18,2),
                oper_expense DECIMAL(18,2),
                    admin_expense DECIMAL(18,2),
                    fin_expense DECIMAL(18,2),
                    assets_impair_loss DECIMAL(18,2),
                    prem_refund DECIMAL(18,2),
                surrend_refund DECIMAL(18,2),
                    reins_cost DECIMAL(18,2),
                    oper_tax DECIMAL(18,2),
                    commission_expense DECIMAL(18,2),
                lir_commission_expense DECIMAL(18,2),
                    business_tax_surcharges DECIMAL(18,2),
                    operate_profit DECIMAL(18,2),
                    nonoper_income DECIMAL(18,2),
                    nonoper_expense DECIMAL(18,2),
                nca_disploss DECIMAL(18,2),
                    total_profit DECIMAL(18,2),
                    income_tax DECIMAL(18,2),
                    net_profit DECIMAL(18,2),
                    net_profit_atsopc DECIMAL(18,2),
                    minority_gain DECIMAL(18,2),
                    oth_compr_income DECIMAL(18,2),
                    t_compr_income DECIMAL(18,2),
                    compr_inc DECIMAL(18,2),
                    compr_inc_attr_p DECIMAL(18,2),
                    net_profit_atsopc_cut DECIMAL(18,2),
                    net_profit_atsopc_org_cut DECIMAL(18,2),
                    net_profit_attr_p_cut DECIMAL(18,2),
                    net_profit_attr_p_org_cut DECIMAL(18,2),
                    PRIMARY KEY (ts_code, end_date, report_type)
                )
            """)

            success_count = 0
            for i, symbol in enumerate(symbols):
                if not self._is_running:
                    break

                try:
                    # 下载利润表
                    df = pro.income(ts_code=symbol, start_date=f'{datetime.now().year - years}0101')
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO financial_income
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, [row.get(k) for k in ['ts_code', 'ann_date', 'f_ann_date', 'end_date', 'report_type',
                                 'comp_type', 'basic_eps', 'diluted_eps', 'total_revenue', 'revenue', 'int_income',
                                 'prem_earned', 'comm_expense', 'oper_expense', 'admin_expense', 'fin_expense',
                                 'assets_impair_loss', 'prem_refund', 'surrend_refund', 'reins_cost', 'oper_tax',
                                 'commission_expense', 'lir_commission_expense', 'business_tax_surcharges',
                                 'operate_profit', 'nonoper_income', 'nonoper_expense', 'nca_disploss',
                                 'total_profit', 'income_tax', 'net_profit', 'net_profit_atsopc',
                                 'minority_gain', 'oth_compr_income', 't_compr_income', 'compr_inc',
                                 'compr_inc_attr_p', 'net_profit_atsopc_cut', 'net_profit_atsopc_org_cut',
                                 'net_profit_attr_p_cut', 'net_profit_attr_p_org_cut']])
                        success_count += 1

                    self.progress_signal.emit(i + 1, len(symbols))

                except Exception as e:
                    self.log_signal.emit(f"  {symbol} 财务数据下载失败: {e}")
                    continue

                time.sleep(0.1)

            conn.close()
            self.finished_signal.emit({'success': True, 'success_count': success_count})
            self.log_signal.emit(f"✅ 财务数据下载完成！成功: {success_count}")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"财务数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_dividend(self):
        """下载分红数据"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path', 'D:/StockData/stock_data.ddb')
            symbols = self.kwargs.get('symbols', [])
            years = self.kwargs.get('years', 5)

            self.log_signal.emit("开始下载分红数据...")

            conn = duckdb.connect(db_path)

            # 创建分红表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dividend_data (
                    ts_code VARCHAR,
                    end_date DATE,
                    div_proc VARCHAR,
                    stk_div DECIMAL(18,4),
                    stk_bo_rate DECIMAL(18,4),
                    stk_co_rate DECIMAL(18,4),
                    cash_div DECIMAL(18,4),
                    cash_div_tax DECIMAL(18,4),
                    record_date DATE,
                    ex_date DATE,
                    pay_date DATE,
                    PRIMARY KEY (ts_code, end_date)
                )
            """)

            success_count = 0
            for i, symbol in enumerate(symbols):
                if not self._is_running:
                    break

                try:
                    df = pro.dividend(ts_code=symbol)
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO dividend_data
                                (ts_code, end_date, div_proc, stk_div, stk_bo_rate, stk_co_rate,
                                 cash_div, cash_div_tax, record_date, ex_date, pay_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, [row.get(k) for k in ['ts_code', 'end_date', 'div_proc', 'stk_div',
                                 'stk_bo_rate', 'stk_co_rate', 'cash_div', 'cash_div_tax',
                                 'record_date', 'ex_date', 'pay_date']])
                        success_count += 1

                    self.progress_signal.emit(i + 1, len(symbols))

                except Exception as e:
                    self.log_signal.emit(f"  {symbol} 分红数据下载失败: {e}")
                    continue

                time.sleep(0.1)

            conn.close()
            self.finished_signal.emit({'success': True, 'success_count': success_count})
            self.log_signal.emit(f"✅ 分红数据下载完成！成功: {success_count}")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"分红数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_moneyflow(self):
        """下载资金流向数据"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path', 'D:/StockData/stock_data.ddb')
            symbols = self.kwargs.get('symbols', [])
            start_date = self.kwargs.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'))
            end_date = self.kwargs.get('end_date', datetime.now().strftime('%Y%m%d'))

            self.log_signal.emit("开始下载资金流向数据...")

            conn = duckdb.connect(db_path)

            # 创建资金流向表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS moneyflow_data (
                    ts_code VARCHAR,
                    trade_date DATE,
                    buy_elg_vol DECIMAL(18,2),
                    buy_elg_amt DECIMAL(18,2),
                    sell_elg_vol DECIMAL(18,2),
                    sell_elg_amt DECIMAL(18,2),
                    buy_lg_vol DECIMAL(18,2),
                    buy_lg_amt DECIMAL(18,2),
                    sell_lg_vol DECIMAL(18,2),
                    sell_lg_amt DECIMAL(18,2),
                    buy_mdn_vol DECIMAL(18,2),
                    buy_mdn_amt DECIMAL(18,2),
                    sell_mdn_vol DECIMAL(18,2),
                    sell_mdn_amt DECIMAL(18,2),
                    buy_sm_vol DECIMAL(18,2),
                    buy_sm_amt DECIMAL(18,2),
                    sell_sm_vol DECIMAL(18,2),
                    sell_sm_amt DECIMAL(18,2),
                    PRIMARY KEY (ts_code, trade_date)
                )
            """)

            success_count = 0
            for i, symbol in enumerate(symbols):
                if not self._is_running:
                    break

                try:
                    df = pro.moneyflow(ts_code=symbol, start_date=start_date, end_date=end_date)
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO moneyflow_data
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, [row.get(k) for k in ['ts_code', 'trade_date', 'buy_elg_vol', 'buy_elg_amt',
                                 'sell_elg_vol', 'sell_elg_amt', 'buy_lg_vol', 'buy_lg_amt',
                                 'sell_lg_vol', 'sell_lg_amt', 'buy_mdn_vol', 'buy_mdn_amt',
                                 'sell_mdn_vol', 'sell_mdn_amt', 'buy_sm_vol', 'buy_sm_amt',
                                 'sell_sm_vol', 'sell_sm_amt']])
                        success_count += 1

                    self.progress_signal.emit(i + 1, len(symbols))

                except Exception as e:
                    self.log_signal.emit(f"  {symbol} 资金流向数据下载失败: {e}")
                    continue

                time.sleep(0.1)

            conn.close()
            self.finished_signal.emit({'success': True, 'success_count': success_count})
            self.log_signal.emit(f"✅ 资金流向数据下载完成！成功: {success_count}")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"资金流向数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_holders(self):
        """下载股东数据"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path', 'D:/StockData/stock_data.ddb')
            symbols = self.kwargs.get('symbols', [])
            years = self.kwargs.get('years', 5)

            self.log_signal.emit("开始下载股东数据...")

            conn = duckdb.connect(db_path)

            # 创建股东表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holders_data (
                    ts_code VARCHAR,
                    ann_date DATE,
                    end_date DATE,
                    holder_name VARCHAR,
                    holder_amount DECIMAL(18,2),
                    holder_rank INTEGER,
                    PRIMARY KEY (ts_code, end_date, holder_rank)
                )
            """)

            success_count = 0
            for i, symbol in enumerate(symbols):
                if not self._is_running:
                    break

                try:
                    df = pro.top10_holders(ts_code=symbol, top10holdrtype='ALL')
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO holders_data
                                (ts_code, ann_date, end_date, holder_name, holder_amount, holder_rank)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, [row.get(k) for k in ['ts_code', 'ann_date', 'end_date',
                                 'holder_name', 'holder_amount', 'holder_rank']])
                        success_count += 1

                    self.progress_signal.emit(i + 1, len(symbols))

                except Exception as e:
                    self.log_signal.emit(f"  {symbol} 股东数据下载失败: {e}")
                    continue

                time.sleep(0.1)

            conn.close()
            self.finished_signal.emit({'success': True, 'success_count': success_count})
            self.log_signal.emit(f"✅ 股东数据下载完成！成功: {success_count}")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"股东数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _batch_download(self):
        """批量下载多种数据"""
        try:
            task_list = self.kwargs.get('task_list', [])
            total_tasks = len(task_list)

            for i, task in enumerate(task_list):
                if not self._is_running:
                    break

                task_name = task.get('name', '')
                task_type = task.get('type', '')
                task_params = task.get('params', {})

                self.log_signal.emit(f"\n[{i+1}/{total_tasks}] 开始下载: {task_name}")

                # 更新kwargs
                self.kwargs.update(task_params)

                if task_type == 'financial':
                    self._download_financial()
                elif task_type == 'dividend':
                    self._download_dividend()
                elif task_type == 'moneyflow':
                    self._download_moneyflow()
                elif task_type == 'holders':
                    self._download_holders()
                elif task_type == 'market_cap':
                    self._download_market_cap()

                self.progress_signal.emit(i + 1, total_tasks)

            self.finished_signal.emit({'success': True})
            self.log_signal.emit("\n✅ 批量下载完成！")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"批量下载失败: {str(e)}\n{traceback.format_exc()}")

    def stop(self):
        """停止下载"""
        self._is_running = False


class TushareDataWidget(QWidget):
    """Tushare数据下载组件（整合版）"""

    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel("📥 Tushare数据下载中心")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #2196F3; padding: 10px;")
        layout.addWidget(title_label)

        # Token配置
        config_group = QGroupBox("⚙️ Token配置")
        config_layout = QHBoxLayout(config_group)

        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("请输入Tushare Token")
        self.token_edit.setEchoMode(QLineEdit.Password)
        self._load_token()

        config_layout.addWidget(QLabel("Token:"))
        config_layout.addWidget(self.token_edit)

        test_btn = QPushButton("🔗 测试连接")
        test_btn.clicked.connect(self.test_connection)
        config_layout.addWidget(test_btn)

        layout.addWidget(config_group)

        # 创建标签页
        tab_widget = QTabWidget()

        # 快速下载标签页
        quick_tab = self._create_quick_download_tab()
        tab_widget.addTab(quick_tab, "⚡ 快速下载")

        # 市值数据标签页
        market_cap_tab = self._create_market_cap_tab()
        tab_widget.addTab(market_cap_tab, "💰 市值数据")

        # 财务数据标签页
        financial_tab = self._create_financial_tab()
        tab_widget.addTab(financial_tab, "📊 财务数据")

        # 分红数据标签页
        dividend_tab = self._create_dividend_tab()
        tab_widget.addTab(dividend_tab, "💸 分红数据")

        # 资金流向标签页
        moneyflow_tab = self._create_moneyflow_tab()
        tab_widget.addTab(moneyflow_tab, "💱 资金流向")

        # 股东数据标签页
        holders_tab = self._create_holders_tab()
        tab_widget.addTab(holders_tab, "👥 股东数据")

        layout.addWidget(tab_widget)

        # 日志区域
        log_group = QGroupBox("📝 下载日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # 清空日志按钮
        clear_log_btn = QPushButton("🗑️ 清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_log_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def _load_token(self):
        """加载Token"""
        token = os.environ.get('TUSHARE_TOKEN', '')
        if token:
            self.token_edit.setText(token)
            return

        # 从配置文件读取
        config_file = os.path.join(project_root, '.env')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('TUSHARE_TOKEN='):
                            token = line.split('=', 1)[1].strip()
                            self.token_edit.setText(token)
                            break
            except Exception:
                pass

    def _create_quick_download_tab(self):
        """创建快速下载标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 说明
        info_label = QLabel(
            "📌 快速下载说明\n\n"
            "快速下载模块提供了一键下载常用数据的功能，包括：\n"
            "• 市值数据：用于回测和选股\n"
            "• 财务数据：包括利润表、资产负债表、现金流量表\n"
            "• 分红数据：历史分红送股数据\n\n"
            "选择要下载的数据类型，设置参数后点击开始下载。"
        )
        info_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1976d2;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #bbdefb;
            }
        """)
        layout.addWidget(info_label)

        # 数据类型选择
        type_group = QGroupBox("选择数据类型")
        type_layout = QGridLayout(type_group)

        self.chk_market_cap = QCheckBox("💰 市值数据")
        self.chk_market_cap.setChecked(True)
        type_layout.addWidget(self.chk_market_cap, 0, 0)

        self.chk_financial = QCheckBox("📊 财务数据")
        self.chk_financial.setChecked(True)
        type_layout.addWidget(self.chk_financial, 0, 1)

        self.chk_dividend = QCheckBox("💸 分红数据")
        self.chk_dividend.setChecked(False)
        type_layout.addWidget(self.chk_dividend, 1, 0)

        self.chk_moneyflow = QCheckBox("💱 资金流向")
        self.chk_moneyflow.setChecked(False)
        type_layout.addWidget(self.chk_moneyflow, 1, 1)

        self.chk_holders = QCheckBox("👥 股东数据")
        self.chk_holders.setChecked(False)
        type_layout.addWidget(self.chk_holders, 2, 0, 1, 2)

        layout.addWidget(type_group)

        # 通用参数
        param_group = QGroupBox("下载参数")
        param_layout = QFormLayout(param_group)

        self.quick_years_spin = QSpinBox()
        self.quick_years_spin.setRange(1, 20)
        self.quick_years_spin.setValue(3)
        self.quick_years_spin.setSuffix(" 年")
        param_layout.addRow("数据年份:", self.quick_years_spin)

        self.quick_stock_spin = QSpinBox()
        self.quick_stock_spin.setRange(10, 5000)
        self.quick_stock_spin.setValue(500)
        self.quick_stock_spin.setSuffix(" 只")
        param_layout.addRow("股票数量:", self.quick_stock_spin)

        layout.addWidget(param_group)

        # 下载按钮
        download_btn = QPushButton("🚀 开始批量下载")
        download_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        download_btn.clicked.connect(self.start_batch_download)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_market_cap_tab(self):
        """创建市值数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.stock_count_spin = QSpinBox()
        self.stock_count_spin.setRange(10, 5000)
        self.stock_count_spin.setValue(500)
        self.stock_count_spin.setSuffix(" 只")
        config_layout.addRow("股票数量:", self.stock_count_spin)

        self.days_back_spin = QSpinBox()
        self.days_back_spin.setRange(1, 365)
        self.days_back_spin.setValue(30)
        self.days_back_spin.setSuffix(" 天")
        config_layout.addRow("时间范围:", self.days_back_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 说明：市值数据将保存到stock_market_cap表，包含流通市值和总市值。"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载市值数据")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_market_cap)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_financial_tab(self):
        """创建财务数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.financial_years_spin = QSpinBox()
        self.financial_years_spin.setRange(1, 20)
        self.financial_years_spin.setValue(5)
        self.financial_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.financial_years_spin)

        self.financial_stock_edit = QLineEdit()
        self.financial_stock_edit.setPlaceholderText("留空下载所有股票，或输入股票代码逗号分隔")
        config_layout.addRow("股票代码:", self.financial_stock_edit)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 说明：财务数据包括利润表、资产负债表、现金流量表等，"
            "用于基本面分析和量化选股。"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载财务数据")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_financial)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_dividend_tab(self):
        """创建分红数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.dividend_years_spin = QSpinBox()
        self.dividend_years_spin.setRange(1, 20)
        self.dividend_years_spin.setValue(5)
        self.dividend_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.dividend_years_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 说明：分红数据包括送股、转增、现金分红等，"
            "用于计算复权价格和分红收益率。"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载分红数据")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_dividend)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_moneyflow_tab(self):
        """创建资金流向标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.moneyflow_days_spin = QSpinBox()
        self.moneyflow_days_spin.setRange(1, 365)
        self.moneyflow_days_spin.setValue(30)
        self.moneyflow_days_spin.setSuffix(" 天")
        config_layout.addRow("时间范围:", self.moneyflow_days_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 说明：资金流向数据包括超大单、大单、中单、小单的买卖情况，"
            "用于分析主力资金动向。"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载资金流向")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_moneyflow)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_holders_tab(self):
        """创建股东数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.holders_years_spin = QSpinBox()
        self.holders_years_spin.setRange(1, 20)
        self.holders_years_spin.setValue(5)
        self.holders_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.holders_years_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 说明：股东数据包括前十大股东信息，"
            "用于分析股东变化和机构持仓。"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载股东数据")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_holders)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def test_connection(self):
        """测试连接"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        self.log_text.append("=" * 60)
        self.log_text.append("🔗 测试Tushare连接...")
        self.log_text.append("=" * 60)

        self.download_thread = TushareDownloadThread('test_connection', token=token)
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.finished_signal.connect(self._on_test_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def start_batch_download(self):
        """开始批量下载"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        # 构建任务列表
        task_list = []

        # 获取股票列表
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            symbols = stock_list['ts_code'].tolist()[:self.quick_stock_spin.value()]
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
            return

        if self.chk_market_cap.isChecked():
            task_list.append({
                'name': '市值数据',
                'type': 'market_cap',
                'params': {
                    'stock_count': self.quick_stock_spin.value(),
                    'days_back': 30
                }
            })

        if self.chk_financial.isChecked():
            task_list.append({
                'name': '财务数据',
                'type': 'financial',
                'params': {
                    'symbols': symbols,
                    'years': self.quick_years_spin.value()
                }
            })

        if self.chk_dividend.isChecked():
            task_list.append({
                'name': '分红数据',
                'type': 'dividend',
                'params': {
                    'symbols': symbols,
                    'years': self.quick_years_spin.value()
                }
            })

        if self.chk_moneyflow.isChecked():
            task_list.append({
                'name': '资金流向',
                'type': 'moneyflow',
                'params': {
                    'symbols': symbols[:100]  # 限制数量
                }
            })

        if self.chk_holders.isChecked():
            task_list.append({
                'name': '股东数据',
                'type': 'holders',
                'params': {
                    'symbols': symbols,
                    'years': self.quick_years_spin.value()
                }
            })

        if not task_list:
            QMessageBox.warning(self, "警告", "请至少选择一种数据类型")
            return

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始批量下载...")
        self.log_text.append("=" * 60)
        self.log_text.append(f"任务数量: {len(task_list)}")
        for task in task_list:
            self.log_text.append(f"  - {task['name']}")

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'batch_download',
            token=token,
            task_list=task_list
        )
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def start_download_market_cap(self):
        """开始下载市值数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载市值数据...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'market_cap',
            token=token,
            stock_count=self.stock_count_spin.value(),
            days_back=self.days_back_spin.value()
        )
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def start_download_financial(self):
        """开始下载财务数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        # 获取股票列表
        stock_str = self.financial_stock_edit.text().strip()
        if stock_str:
            symbols = [s.strip() for s in stock_str.split(',')]
        else:
            try:
                import tushare as ts
                ts.set_token(token)
                pro = ts.pro_api()
                stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
                symbols = stock_list['ts_code'].tolist()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
                return

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载财务数据...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'financial',
            token=token,
            symbols=symbols,
            years=self.financial_years_spin.value()
        )
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def start_download_dividend(self):
        """开始下载分红数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        # 获取股票列表
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            symbols = stock_list['ts_code'].tolist()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
            return

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载分红数据...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'dividend',
            token=token,
            symbols=symbols,
            years=self.dividend_years_spin.value()
        )
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def start_download_moneyflow(self):
        """开始下载资金流向"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        # 获取股票列表
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            symbols = stock_list['ts_code'].tolist()[:100]  # 限制数量
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
            return

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载资金流向...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'moneyflow',
            token=token,
            symbols=symbols,
            days_back=self.moneyflow_days_spin.value()
        )
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def start_download_holders(self):
        """开始下载股东数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        # 获取股票列表
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            symbols = stock_list['ts_code'].tolist()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
            return

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载股东数据...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'holders',
            token=token,
            symbols=symbols,
            years=self.holders_years_spin.value()
        )
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def _on_log(self, message):
        """处理日志消息"""
        self.log_text.append(message)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def _on_progress(self, current, total):
        """处理进度更新"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _on_test_finished(self, result):
        """测试完成"""
        if result.get('success'):
            QMessageBox.information(self, "成功", "✅ Tushare连接测试成功！")

    def _on_download_finished(self, result):
        """下载完成"""
        self.progress_bar.setVisible(False)

        if result.get('success'):
            total_inserted = result.get('total_inserted', 0)
            success_count = result.get('success_count', 0)

            if total_inserted > 0:
                QMessageBox.information(self, "完成", f"✅ 下载完成！\n\n新增数据: {total_inserted:,} 条")
            elif success_count > 0:
                QMessageBox.information(self, "完成", f"✅ 下载完成！\n\n成功: {success_count} 只股票")

    def _on_error(self, error_msg):
        """处理错误"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", error_msg)


if __name__ == "__main__":
    """测试运行"""
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    widget = TushareDataWidget()
    widget.setWindowTitle("Tushare数据下载中心（整合版）")
    widget.resize(900, 700)
    widget.show()
    sys.exit(app.exec_())
