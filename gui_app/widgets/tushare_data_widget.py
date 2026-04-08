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
                self._download_holders()
            elif self.task_type == 'test_connection':
                self._test_connection()
            elif self.task_type == 'batch_download':
                self._batch_download()
            elif self.task_type == 'daily':
                self._download_daily()
            elif self.task_type == 'index_data':
                self._download_index_data()
            elif self.task_type == 'stock_basic':
                self._download_stock_basic()
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

    def _get_db_path(self):
        """获取DuckDB数据库路径（自动检测）"""
        import os
        # 优先使用环境变量
        env_path = os.environ.get('DUCKDB_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        # 常见路径自动检测
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
        # 默认路径（会自动创建目录）
        return 'D:/StockData/stock_data.ddb'

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
        """下载市值数据（全市场，按日期范围）"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            start_date = self.kwargs.get('start_date', '20240101')
            end_date = self.kwargs.get('end_date', '20241231')

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载全A股市值数据")
            self.log_signal.emit("=" * 60)

            # 连接数据库
            conn = duckdb.connect(db_path)
            self.log_signal.emit("✅ 数据库连接成功")

            # 检查表是否存在，获取现有结构
            try:
                # 尝试查询表
                conn.execute("SELECT COUNT(*) FROM stock_market_cap LIMIT 1")
                self.log_signal.emit("✅ stock_market_cap 表已存在")

                # 检查是否有必要的字段
                required_columns = ['stock_code', 'date', 'circ_mv', 'total_mv', 'close', 'pe', 'pb', 'turnover_rate']
                existing_columns = conn.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'stock_market_cap'
                """).fetchdf()['column_name'].tolist()

                # 找出缺失的字段
                missing_columns = [col for col in required_columns if col.lower() not in [c.lower() for c in existing_columns]]

                if missing_columns:
                    self.log_signal.emit(f"📝 检测到缺失字段: {', '.join(missing_columns)}")
                    self.log_signal.emit("📝 正在添加缺失字段...")

                    # 添加缺失字段
                    if 'close' in missing_columns:
                        conn.execute("ALTER TABLE stock_market_cap ADD COLUMN close DECIMAL(10,2)")
                        self.log_signal.emit("  ✅ 已添加 close 字段")
                    if 'pe' in missing_columns:
                        conn.execute("ALTER TABLE stock_market_cap ADD COLUMN pe DECIMAL(10,2)")
                        self.log_signal.emit("  ✅ 已添加 pe 字段")
                    if 'pb' in missing_columns:
                        conn.execute("ALTER TABLE stock_market_cap ADD COLUMN pb DECIMAL(10,2)")
                        self.log_signal.emit("  ✅ 已添加 pb 字段")
                    if 'turnover_rate' in missing_columns:
                        conn.execute("ALTER TABLE stock_market_cap ADD COLUMN turnover_rate DECIMAL(10,4)")
                        self.log_signal.emit("  ✅ 已添加 turnover_rate 字段")

                    self.log_signal.emit("✅ 表结构更新完成")

            except Exception as e:
                # 表不存在，创建新表
                self.log_signal.emit(f"📝 创建新表: {e}")
                conn.execute("""
                    CREATE TABLE stock_market_cap (
                        stock_code VARCHAR,
                        date DATE,
                        circ_mv DECIMAL(18,2),
                        total_mv DECIMAL(18,2),
                        close DECIMAL(10,2),
                        pe DECIMAL(10,2),
                        pb DECIMAL(10,2),
                        turnover_rate DECIMAL(10,4),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (stock_code, date)
                    )
                """)
                self.log_signal.emit("✅ stock_market_cap 表创建成功")

            # 获取交易日历
            self.log_signal.emit(f"📅 获取交易日历: {start_date} ~ {end_date}")
            trade_cal = pro.trade_cal(
                exchange='SSE',
                start_date=start_date,
                end_date=end_date,
                is_open=1
            )

            if trade_cal is None or trade_cal.empty:
                self.log_signal.emit("❌ 未获取到交易日历")
                return

            all_trade_dates = trade_cal['cal_date'].tolist()
            self.log_signal.emit(f"✅ 共 {len(all_trade_dates)} 个交易日")

            # ✨ 智能检查：找出缺失数据的日期
            self.log_signal.emit("\n🔍 检查已有数据...")
            existing_dates = set()

            try:
                # 转换日期格式为YYYY-MM-DD用于数据库查询
                start_date_db = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                end_date_db = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

                # 查询数据库中已有的日期
                existing_result = conn.execute("""
                    SELECT DISTINCT date
                    FROM stock_market_cap
                    WHERE date BETWEEN ? AND ?
                    ORDER BY date
                """, [start_date_db, end_date_db]).fetchall()

                if existing_result:
                    existing_dates = {row[0] for row in existing_result}

                self.log_signal.emit(f"  已有数据: {len(existing_dates)} 个交易日")

                # 找出缺失的日期（all_trade_dates是YYYYMMDD格式，需要转换比较）
                # 注意：DuckDB返回的是datetime.date对象，需要先转换为字符串
                existing_dates_db = {d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
                                    for d in existing_dates}
                missing_dates = [d for d in all_trade_dates if f"{d[:4]}-{d[4:6]}-{d[6:]}" not in existing_dates_db]

                if len(existing_dates) > 0:
                    # 显示已有数据的日期范围
                    sorted_dates = sorted(list(existing_dates))
                    if sorted_dates:
                        self.log_signal.emit(f"  日期范围: {sorted_dates[0]} ~ {sorted_dates[-1]}")

            except Exception as e:
                # 查询失败，下载所有数据
                self.log_signal.emit(f"  ⚠️  检查失败: {e}")
                self.log_signal.emit("  将下载所有数据...")
                missing_dates = all_trade_dates

            if missing_dates:
                self.log_signal.emit(f"\n✨ 需要下载: {len(missing_dates)} 个交易日")
                if len(existing_dates) > 0:
                    self.log_signal.emit(f"✅ 跳过已有: {len(existing_dates)} 个交易日")
                    self.log_signal.emit(f"💾 节省时间: 约 {len(existing_dates) * 0.3:.0f} 秒")
            else:
                self.log_signal.emit(f"\n✅ 所有数据已存在！无需下载")
                self.finished_signal.emit({
                    'success': True,
                    'total_records': 0,
                    'total_stocks': 0,
                    'skipped': True
                })
                return

            # 只下载缺失的日期
            trade_dates = missing_dates

            # 逐日下载全市场数据（超高速模式）
            total_inserted = 0
            all_stocks = set()
            start_time = time.time()

            for date_idx, trade_date in enumerate(trade_dates, 1):
                if not self._is_running:
                    self.log_signal.emit("\n⚠️  下载已取消")
                    break

                try:
                    # 获取当日全市场数据（不指定股票代码）
                    df = pro.daily_basic(
                        trade_date=trade_date,
                        fields='ts_code,trade_date,close,pe,pb,total_mv,circ_mv,turnover_rate'
                    )

                    if df is not None and not df.empty:
                        # 统计股票数量
                        all_stocks.update(df['ts_code'].tolist())

                        # 转换日期格式 YYYYMMDD -> YYYY-MM-DD
                        df['date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

                        # 重命名列
                        df.rename(columns={'ts_code': 'stock_code'}, inplace=True)

                        # 选择需要的列
                        df_insert = df[['stock_code', 'date', 'circ_mv', 'total_mv', 'close', 'pe', 'pb', 'turnover_rate']].copy()
                        df_insert = df_insert.fillna(0)

                        # ✨ 使用to_sql的APPEND模式（最快的方法！）
                        try:
                            df_insert.to_sql(
                                'stock_market_cap',
                                conn,
                                if_exists='append',
                                index=False,
                                method='multi'  # 多行插入，速度最快
                            )
                            insert_count = len(df_insert)
                        except Exception as sql_error:
                            # to_sql失败，回退到executemany
                            insert_data = [tuple(row) for row in df_insert.itertuples(index=False, name=None)]
                            conn.executemany("""
                                INSERT OR REPLACE INTO stock_market_cap
                                (stock_code, date, circ_mv, total_mv, close, pe, pb, turnover_rate)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, insert_data)
                            insert_count = len(insert_data)

                        total_inserted += insert_count

                        # 每20个交易日显示一次进度（减少日志开销）
                        if date_idx % 20 == 0 or date_idx == len(trade_dates):
                            elapsed = time.time() - start_time
                            # 确保至少运行了1秒再计算速度
                            if elapsed > 0:
                                speed = date_idx / elapsed
                                eta = (len(trade_dates) - date_idx) / speed if speed > 0 else 0

                                self.log_signal.emit(
                                    f"[{date_idx}/{len(trade_dates)}] {trade_date} | "
                                    f"已插入: {total_inserted:,}条 | "
                                    f"速度: {speed:.2f}天/秒 | "
                                    f"预计剩余: {eta/60:.1f}分钟"
                                )

                    else:
                        # 无数据，每20个交易日显示一次
                        if date_idx % 20 == 0 or date_idx == len(trade_dates):
                            self.log_signal.emit(f"[{date_idx}/{len(trade_dates)}] {trade_date} | ⚠️ 无数据")

                except Exception as e:
                    # 错误，每20个交易日显示一次
                    if date_idx % 20 == 0 or date_idx == len(trade_dates):
                        self.log_signal.emit(f"[{date_idx}/{len(trade_dates)}] {trade_date} | ❌ 失败: {str(e)[:50]}")

                # 更新进度
                progress = int(date_idx / len(trade_dates) * 100)
                self.progress_signal.emit(progress, len(trade_dates))

                # ✨ 添加适当延迟避免IP限流（0.15秒 = 每秒约6-7次请求）
                time.sleep(0.15)
                # time.sleep(0)

            # 完成统计
            self.log_signal.emit("\n" + "=" * 60)
            if len(existing_dates) > 0:
                self.log_signal.emit("✅ 下载完成！（增量更新）")
                self.log_signal.emit(f"  本次新增: {total_inserted:,} 条记录")
                self.log_signal.emit(f"  跳过已有: {len(existing_dates)} 个交易日")
                total_records = len(existing_dates) + len(trade_dates)
                self.log_signal.emit(f"  总覆盖范围: {total_records} 个交易日")
            else:
                self.log_signal.emit("✅ 下载完成！（首次下载）")
                self.log_signal.emit(f"  总记录数: {total_inserted:,}")
                self.log_signal.emit(f"  涉及股票: {len(all_stocks)} 只")
                self.log_signal.emit(f"  日期范围: {start_date} ~ {end_date}")
            self.log_signal.emit("=" * 60)

            # 验证数据
            # 转换日期格式：20240101 -> 2024-01-01
            start_date_db = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end_date_db = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            stats = conn.execute("""
                SELECT
                    COUNT(DISTINCT stock_code) as total_stocks,
                    COUNT(DISTINCT date) as total_dates
                FROM stock_market_cap
                WHERE date BETWEEN ? AND ?
            """, [start_date_db, end_date_db]).fetchone()

            self.log_signal.emit(f"\n📊 验证结果:")
            self.log_signal.emit(f"  数据库中股票数: {stats[0]}")
            self.log_signal.emit(f"  数据库中日期数: {stats[1]}")

            conn.close()

            self.finished_signal.emit({
                'success': True,
                'total_records': total_inserted,
                'total_stocks': len(all_stocks)
            })

        except Exception as e:
            import traceback
            error_msg = f"下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

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
            db_path = self.kwargs.get('db_path') or self._get_db_path()
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
            db_path = self.kwargs.get('db_path') or self._get_db_path()
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
            db_path = self.kwargs.get('db_path') or self._get_db_path()
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
            db_path = self.kwargs.get('db_path') or self._get_db_path()
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
                elif task_type == 'daily':
                    self._download_daily()

                self.progress_signal.emit(i + 1, total_tasks)

            self.finished_signal.emit({'success': True})
            self.log_signal.emit("\n✅ 批量下载完成！")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"批量下载失败: {str(e)}\n{traceback.format_exc()}")

    def stop(self):
        """停止下载"""
        self._is_running = False

    def _download_daily(self):
        """下载日线行情数据（使用Tushare，无需QMT）"""
        import os
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            start_date = self.kwargs.get('start_date', '20230101')
            end_date = self.kwargs.get('end_date', '20241231')
            symbols = self.kwargs.get('symbols', [])

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载日线行情数据（Tushare）")
            self.log_signal.emit("=" * 60)

            # 确保目录存在
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

            # 连接数据库
            conn = duckdb.connect(db_path)
            self.log_signal.emit(f"数据库: {db_path}")

            # 确保表存在
            try:
                conn.execute("SELECT COUNT(*) FROM stock_daily LIMIT 1")
            except:
                conn.execute("""
                    CREATE TABLE stock_daily (
                        stock_code VARCHAR,
                        symbol_type VARCHAR DEFAULT 'stock',
                        date DATE,
                        period VARCHAR DEFAULT '1d',
                        open DOUBLE,
                        high DOUBLE,
                        low DOUBLE,
                        close DOUBLE,
                        volume BIGINT,
                        amount DOUBLE,
                        adjust_type VARCHAR DEFAULT 'none',
                        factor DOUBLE DEFAULT 1.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (stock_code, date, period, adjust_type)
                    )
                """)
                self.log_signal.emit("已创建 stock_daily 表")

            # 如果没有指定股票列表，获取全部A股
            if not symbols:
                self.log_signal.emit("获取A股列表...")
                stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
                symbols = stock_list['ts_code'].tolist()

            # 限制下载数量
            max_count = self.kwargs.get('max_count', 500)
            symbols = symbols[:max_count]

            self.log_signal.emit(f"股票数量: {len(symbols)}")
            self.log_signal.emit(f"日期范围: {start_date} ~ {end_date}")

            # 获取交易日历
            trade_cal = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open=1)
            trade_dates = sorted(trade_cal['cal_date'].tolist())
            self.log_signal.emit(f"交易日数: {len(trade_dates)}")

            total_inserted = 0
            success_count = 0
            failed_count = 0

            for i, ts_code in enumerate(symbols, 1):
                if not self._is_running:
                    break

                try:
                    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                                   fields='ts_code,trade_date,open,high,low,close,vol,amount')

                    if df is not None and not df.empty:
                        df['date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                        df.rename(columns={'ts_code': 'stock_code', 'vol': 'volume'}, inplace=True)
                        df['symbol_type'] = 'stock'
                        df['period'] = '1d'
                        df['adjust_type'] = 'none'
                        df['factor'] = 1.0
                        df['created_at'] = pd.Timestamp.now()
                        df['updated_at'] = pd.Timestamp.now()

                        cols = ['stock_code', 'symbol_type', 'date', 'period',
                                'open', 'high', 'low', 'close', 'volume', 'amount',
                                'adjust_type', 'factor', 'created_at', 'updated_at']
                        df = df[cols]

                        # 删除可能已存在的数据，重新插入
                        conn.execute(f"DELETE FROM stock_daily WHERE stock_code = '{ts_code}' AND period = '1d' AND adjust_type = 'none'")
                        df.to_sql('stock_daily', conn, if_exists='append', index=False, method='multi')

                        total_inserted += len(df)
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    failed_count += 1
                    if failed_count <= 5:
                        self.log_signal.emit(f"  {ts_code} 失败: {str(e)[:40]}")

                # 进度
                if i % 50 == 0 or i == len(symbols):
                    self.progress_signal.emit(i, len(symbols))
                    self.log_signal.emit(f"[{i}/{len(symbols)}] 成功: {success_count} | 失败: {failed_count} | 记录: {total_inserted:,}")

            conn.close()

            self.log_signal.emit(f"\n日线数据下载完成！成功: {success_count}, 失败: {failed_count}, 总记录: {total_inserted:,}")
            self.finished_signal.emit({
                'success': True,
                'total': len(symbols),
                'success_count': success_count,
                'failed_count': failed_count,
                'total_inserted': total_inserted
            })

        except Exception as e:
            import traceback
            self.error_signal.emit(f"日线数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_index_data(self):
        """下载指数数据"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            index_codes = self.kwargs.get('index_codes', [
                '000300.SH',  # 沪深300
                '000905.SH',  # 中证500
                '000906.SH',  # 中证800
                '000852.SH',  # 中证1000
                '399303.SZ'   # 国证2000
            ])
            start_date = self.kwargs.get('start_date', '20200101')
            end_date = self.kwargs.get('end_date', datetime.now().strftime('%Y%m%d'))

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载指数数据")
            self.log_signal.emit("=" * 60)
            self.log_signal.emit(f"指数数量: {len(index_codes)}")
            self.log_signal.emit(f"日期范围: {start_date} - {end_date}")

            # 连接数据库
            conn = duckdb.connect(db_path)

            # 创建指数数据表（包含所有字段）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS index_data (
                    ts_code VARCHAR,
                    trade_date DATE,
                    open DECIMAL(10,2),
                    high DECIMAL(10,2),
                    low DECIMAL(10,2),
                    close DECIMAL(10,2),
                    pre_close DECIMAL(10,2),
                    change DECIMAL(10,2),
                    pct_chg DECIMAL(10,4),
                    vol DECIMAL(18,2),
                    amount DECIMAL(18,2),
                    PRIMARY KEY (ts_code, trade_date)
                )
            """)

            total_count = 0
            success_count = 0

            for i, index_code in enumerate(index_codes, 1):
                if not self._is_running:
                    break

                try:
                    self.log_signal.emit(f"\n[{i}/{len(index_codes)}] 下载 {index_code}...")

                    df = pro.index_daily(
                        ts_code=index_code,
                        start_date=start_date,
                        end_date=end_date
                    )

                    if df is not None and not df.empty:
                        # 保存到数据库 - 使用DuckDB原生方法
                        try:
                            # 保留所有11个字段
                            df_insert = df[[
                                'ts_code', 'trade_date', 'open', 'high', 'low', 'close',
                                'pre_close', 'change', 'pct_chg', 'vol', 'amount'
                            ]].copy()

                            # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
                            df_insert['trade_date'] = pd.to_datetime(
                                df_insert['trade_date'], format='%Y%m%d'
                            ).dt.strftime('%Y-%m-%d')

                            # 准备数据：将DataFrame转换为元组列表
                            insert_data = [tuple(row) for row in df_insert.itertuples(index=False, name=None)]

                            # 执行批量插入（11个字段）
                            conn.executemany("""
                                INSERT OR REPLACE INTO index_data
                                (ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, insert_data)

                            total_count += len(df)
                            success_count += 1
                            self.log_signal.emit(f"  ✅ 成功: {len(df)} 条记录")
                        except Exception as e:
                            self.log_signal.emit(f"  ❌ 保存失败: {e}")
                    else:
                        self.log_signal.emit(f"  ❌ 无数据")

                    self.progress_signal.emit(i, len(index_codes))

                except Exception as e:
                    self.log_signal.emit(f"  ❌ {index_code} 下载失败: {e}")
                    continue

                time.sleep(0.5)  # 避免请求过快

            conn.close()
            self.finished_signal.emit({'success': True, 'total': total_count})
            self.log_signal.emit(f"\n✅ 指数数据下载完成！总计: {total_count:,} 条记录")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"指数数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_stock_basic(self):
        """下载股票基本信息"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载股票基本信息")
            self.log_signal.emit("=" * 60)

            # 连接数据库
            conn = duckdb.connect(db_path)

            # 创建stock_basic表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_basic (
                    ts_code VARCHAR PRIMARY KEY,
                    symbol VARCHAR,
                    name VARCHAR,
                    area VARCHAR,
                    industry VARCHAR,
                    market VARCHAR,
                    list_date DATE,
                    is_hs VARCHAR,
                    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.log_signal.emit("✅ 数据库连接成功")
            self.log_signal.emit("正在获取股票列表...")

            # 获取股票列表
            df = pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,market,list_date,is_hs'
            )

            if df is None or df.empty:
                self.error_signal.emit("获取股票列表失败")
                return

            self.log_signal.emit(f"✅ 获取到 {len(df)} 只股票")

            # 转换日期格式
            df['list_date'] = pd.to_datetime(df['list_date'], format='%Y%m%d', errors='coerce')

            # 删除旧数据
            conn.execute("DELETE FROM stock_basic")

            # 插入新数据
            insert_count = 0
            for _, row in df.iterrows():
                try:
                    conn.execute("""
                        INSERT INTO stock_basic
                        (ts_code, symbol, name, area, industry, market, list_date, is_hs)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        row['ts_code'],
                        row['symbol'],
                        row['name'],
                        row['area'],
                        row['industry'],
                        row['market'],
                        row['list_date'],
                        row['is_hs']
                    ])
                    insert_count += 1
                except Exception as e:
                    self.log_signal.emit(f"  ⚠️  {row['ts_code']} 插入失败: {e}")
                    continue

            conn.close()

            self.finished_signal.emit({'success': True, 'total': insert_count})
            self.log_signal.emit(f"\n✅ 股票基本信息下载完成！")
            self.log_signal.emit(f"   总计: {insert_count} 只股票")
            self.log_signal.emit(f"   用于：过滤ST股票、新股、停牌股票")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"股票基本信息下载失败: {str(e)}\n{traceback.format_exc()}")

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

        # 指数数据标签页
        index_data_tab = self._create_index_data_tab()
        tab_widget.addTab(index_data_tab, "📊 指数数据")

        # 股票基本信息标签页
        stock_basic_tab = self._create_stock_basic_tab()
        tab_widget.addTab(stock_basic_tab, "📝 股票信息")

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
            "快速下载说明\n\n"
            "快速下载模块提供了一键下载常用数据的功能，包括：\n"
            "- 日线行情：股票每日OHLCV数据（回测必需）\n"
            "- 市值数据：用于回测和选股（小市值策略必需）\n"
            "- 财务数据：包括利润表、资产负债表、现金流量表\n"
            "- 分红数据：历史分红送股数据\n\n"
            "选择要下载的数据类型，设置参数后点击开始下载。\n"
            "所有数据保存到 DuckDB 数据库（默认 D:/StockData/stock_data.ddb）"
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

        self.chk_daily = QCheckBox("📈 日线行情（OHLCV，回测必需）")
        self.chk_daily.setChecked(True)
        type_layout.addWidget(self.chk_daily, 0, 0)

        self.chk_market_cap = QCheckBox("💰 市值数据（小市值策略必需）")
        self.chk_market_cap.setChecked(True)
        type_layout.addWidget(self.chk_market_cap, 0, 1)

        self.chk_financial = QCheckBox("📊 财务数据")
        self.chk_financial.setChecked(True)
        type_layout.addWidget(self.chk_financial, 1, 0)

        self.chk_dividend = QCheckBox("💸 分红数据")
        self.chk_dividend.setChecked(False)
        type_layout.addWidget(self.chk_dividend, 1, 1)

        self.chk_moneyflow = QCheckBox("💱 资金流向")
        self.chk_moneyflow.setChecked(False)
        type_layout.addWidget(self.chk_moneyflow, 2, 0)

        self.chk_holders = QCheckBox("👥 股东数据（小市值策略必需）")
        self.chk_holders.setChecked(False)
        type_layout.addWidget(self.chk_holders, 2, 1)

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

        config_group = QGroupBox("📅 下载配置")
        config_layout = QFormLayout(config_group)

        # 开始日期
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate(2024, 1, 1))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        config_layout.addRow("开始日期:", self.start_date_edit)

        # 结束日期
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        config_layout.addRow("结束日期:", self.end_date_edit)

        layout.addWidget(config_group)

        # 快速选择按钮
        quick_group = QGroupBox("⚡ 快速选择")
        quick_layout = QHBoxLayout(quick_group)

        btn_2024 = QPushButton("2024年全年")
        btn_2024.clicked.connect(lambda: self._set_date_range("2024-01-01", "2024-12-31"))
        quick_layout.addWidget(btn_2024)

        btn_2023 = QPushButton("2023年全年")
        btn_2023.clicked.connect(lambda: self._set_date_range("2023-01-01", "2023-12-31"))
        quick_layout.addWidget(btn_2023)

        btn_2years = QPushButton("近2年")
        btn_2years.clicked.connect(lambda: self._set_date_range("2023-01-01", "2024-12-31"))
        quick_layout.addWidget(btn_2years)

        layout.addWidget(quick_group)

        # 说明文字
        info_label = QLabel(
            "📌 <b>说明：</b><br>"
            "• 下载全A股市值数据（不指定股票代码）<br>"
            "• 自动下载所有A股（主板+创业板+科创板）<br>"
            "• 一次下载，永久支持任意回测参数<br>"
            "• 预计时间：5-10分钟/年"
        )
        info_label.setStyleSheet("color: #666; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载全A股市值数据")
        download_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        download_btn.clicked.connect(self.start_download_market_cap)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _set_date_range(self, start_str: str, end_str: str):
        """设置日期范围"""
        start_date = QDate.fromString(start_str, "yyyy-MM-dd")
        end_date = QDate.fromString(end_str, "yyyy-MM-dd")
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)

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

    def _create_index_data_tab(self):
        """创建指数数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.index_years_spin = QSpinBox()
        self.index_years_spin.setRange(1, 20)
        self.index_years_spin.setValue(5)
        self.index_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.index_years_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 说明：指数数据包括沪深300、中证500、中证800、中证1000、国证2000等主要指数，"
            "用于计算定价因子（MKT、SMB、HML、UMD）和作为回测基准。"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载指数数据")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_index_data)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_stock_basic_tab(self):
        """创建股票基本信息标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 说明
        info_label = QLabel(
            "📌 说明：股票基本信息包括股票代码、名称、行业、上市日期等，"
            "用于101因子平台的样本筛选和过滤。\n\n"
            "主要用途：\n"
            "• 过滤ST股票（*ST, ST等）\n"
            "• 过滤新股（上市不足60天）\n"
            "• 过滤停牌股票\n"
            "• 按行业分类进行分组回测"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载股票信息")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_stock_basic)
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

        if self.chk_daily.isChecked():
            # 计算日期范围
            years_back = self.quick_years_spin.value()
            end_date = datetime.now().strftime('%Y%m%d')
            start_year = datetime.now().year - years_back
            start_date = f"{start_year}0101"
            task_list.append({
                'name': '日线行情',
                'type': 'daily',
                'params': {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date,
                    'max_count': self.quick_stock_spin.value()
                }
            })

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

        # 获取日期范围
        start_date = self.start_date_edit.date().toString("yyyyMMdd")
        end_date = self.end_date_edit.date().toString("yyyyMMdd")

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认下载",
            f"即将下载全A股市值数据：\n\n"
            f"📅 日期范围：{start_date} ~ {end_date}\n"
            f"⏱️  预计时间：5-10分钟\n"
            f"💾 数据量：约100-200MB\n\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        os.environ['TUSHARE_TOKEN'] = token

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载全A股市值数据...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'market_cap',
            token=token,
            start_date=start_date,
            end_date=end_date
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

    def start_download_index_data(self):
        """开始下载指数数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载指数数据...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.index_years_spin.value() * 365)

        self.download_thread = TushareDownloadThread(
            'index_data',
            token=token,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.start()

    def start_download_stock_basic(self):
        """开始下载股票基本信息"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载股票基本信息...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = TushareDownloadThread(
            'stock_basic',
            token=token
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
