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
        self._is_stopped = False

    def stop(self):
        """停止下载"""
        self._is_running = False
        self._is_stopped = True
        self.log_signal.emit("\n⚠️ 正在停止下载...")

    def is_running(self):
        """检查是否正在运行"""
        return self._is_running

    def _check_stop(self):
        """检查是否需要停止（在循环中调用）"""
        if not self._is_running:
            self.log_signal.emit("❌ 下载已被用户停止")
            raise StopIteration("下载已停止")

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
            elif self.task_type == 'financial_indicator':
                self._download_financial_indicator()
            elif self.task_type == 'balancesheet':
                self._download_balancesheet()
            elif self.task_type == 'cashflow_data':
                self._download_cashflow_data()
            elif self.task_type == 'cb_basic':
                self._download_cb_basic()
            elif self.task_type == 'cb_daily':
                self._download_cb_daily()
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

    def _get_existing_stocks(self, conn, table_name, date_col='end_date', code_col='ts_code'):
        """查询表中每个股票的最新日期，用于增量判断"""
        try:
            result = conn.execute(f"""
                SELECT {code_col}, MAX({date_col}) as max_date
                FROM {table_name}
                GROUP BY {code_col}
            """).fetchall()
            return dict(result)
        except Exception:
            return {}

    def _filter_symbols_for_download(self, symbols, existing_map, target_end_date=None):
        """将symbols分为需要下载和跳过两组"""
        need_download = []
        skipped = 0
        for symbol in symbols:
            if symbol in existing_map:
                max_date = existing_map[symbol]
                if target_end_date is None or (max_date and str(max_date) >= str(target_end_date)):
                    skipped += 1
                    continue
            need_download.append(symbol)
        return need_download, skipped

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
                    'skipped': True,
                    'stopped': False
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
                    self._is_stopped = True
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
                'total_stocks': len(all_stocks),
                'stopped': self._is_stopped
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
        """下载财务数据（增量）"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            symbols = self.kwargs.get('symbols', [])
            years = self.kwargs.get('years', 5)
            target_end_date = f"{datetime.now().year}1231"

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载财务数据")
            self.log_signal.emit(f"  股票总数: {len(symbols)}")
            self.log_signal.emit("=" * 60)

            conn = duckdb.connect(db_path)

            # 创建财务数据表（利润表）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profit_statement (
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
                    data_source VARCHAR(20) DEFAULT 'Tushare',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ts_code, end_date, report_type)
                )
            """)

            # 增量检查
            existing_map = self._get_existing_stocks(conn, 'profit_statement')
            need_download, skipped = self._filter_symbols_for_download(symbols, existing_map, target_end_date)
            self.log_signal.emit(f"🔍 已有数据: {skipped} 只 | 需下载: {len(need_download)} 只")

            if not need_download:
                self.log_signal.emit("✅ 所有财务数据已是最新，无需下载")
                conn.close()
                self.finished_signal.emit({'success': True, 'success_count': 0, 'skipped': skipped, 'stopped': False})
                return

            success_count = 0
            for i, symbol in enumerate(need_download):
                if not self._is_running:
                    self._is_stopped = True
                    break

                try:
                    df = pro.income(ts_code=symbol, start_date=f'{datetime.now().year - years}0101')
                    if df is not None and not df.empty:
                        for col in ['ann_date', 'f_ann_date', 'end_date']:
                            if col in df.columns:
                                df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')

                        df = df.replace({np.nan: None})

                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO profit_statement
                                (ts_code, ann_date, f_ann_date, end_date, report_type, comp_type,
                                 basic_eps, diluted_eps, total_revenue, revenue, int_income,
                                 prem_earned, comm_expense, oper_expense, admin_expense, fin_expense,
                                 assets_impair_loss, prem_refund, surrend_refund, reins_cost, oper_tax,
                                 commission_expense, lir_commission_expense, business_tax_surcharges,
                                 operate_profit, nonoper_income, nonoper_expense, nca_disploss,
                                 total_profit, income_tax, net_profit, net_profit_atsopc,
                                 minority_gain, oth_compr_income, t_compr_income, compr_inc,
                                 compr_inc_attr_p, net_profit_atsopc_cut, net_profit_atsopc_org_cut,
                                 net_profit_attr_p_cut, net_profit_attr_p_org_cut, data_source, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Tushare', CURRENT_TIMESTAMP)
                            """, [row.get(k, None) for k in [
                                'ts_code', 'ann_date', 'f_ann_date', 'end_date', 'report_type', 'comp_type',
                                'basic_eps', 'diluted_eps', 'total_revenue', 'revenue', 'int_income',
                                'prem_earned', 'comm_expense', 'oper_expense', 'admin_expense', 'fin_expense',
                                'assets_impair_loss', 'prem_refund', 'surrend_refund', 'reins_cost', 'oper_tax',
                                'commission_expense', 'lir_commission_expense', 'business_tax_surcharges',
                                'operate_profit', 'nonoper_income', 'nonoper_expense', 'nca_disploss',
                                'total_profit', 'income_tax', 'net_profit', 'net_profit_atsopc',
                                'minority_gain', 'oth_compr_income', 't_compr_income', 'compr_inc',
                                'compr_inc_attr_p', 'net_profit_atsopc_cut', 'net_profit_atsopc_org_cut',
                                'net_profit_attr_p_cut', 'net_profit_attr_p_org_cut'
                            ]])
                        success_count += 1

                    self.progress_signal.emit(i + 1, len(need_download))

                except Exception as e:
                    self.log_signal.emit(f"  {symbol} 财务数据下载失败: {e}")
                    continue

                time.sleep(0.1)

            conn.close()
            self.finished_signal.emit({'success': True, 'success_count': success_count, 'skipped': skipped, 'stopped': self._is_stopped})
            self.log_signal.emit(f"✅ 财务数据下载完成！成功: {success_count}")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"财务数据下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_dividend(self):
        """下载分红数据（增量）"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            symbols = self.kwargs.get('symbols', [])
            years = self.kwargs.get('years', 5)

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载分红数据")
            self.log_signal.emit(f"  股票总数: {len(symbols)}")
            self.log_signal.emit("=" * 60)

            conn = duckdb.connect(db_path)
            self.log_signal.emit("✅ 数据库连接成功")

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

            # 增量检查：分红数据是历史累积的，只要有数据就跳过
            existing_map = self._get_existing_stocks(conn, 'dividend_data')
            need_download, skipped = self._filter_symbols_for_download(symbols, existing_map)
            self.log_signal.emit(f"🔍 已有数据: {skipped} 只 | 需下载: {len(need_download)} 只")

            if not need_download:
                self.log_signal.emit("✅ 所有分红数据已存在，无需下载")
                conn.close()
                self.finished_signal.emit({'success': True, 'success_count': 0, 'skipped': skipped, 'stopped': False})
                return

            success_count = 0
            failed_count = 0
            for i, symbol in enumerate(need_download):
                if not self._is_running:
                    self._is_stopped = True
                    break

                try:
                    df = pro.dividend(ts_code=symbol)
                    if df is not None and not df.empty:
                        for col in ['end_date', 'record_date', 'ex_date', 'pay_date']:
                            if col in df.columns:
                                df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')

                        df = df.replace({np.nan: None})

                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO dividend_data
                                (ts_code, end_date, div_proc, stk_div, stk_bo_rate, stk_co_rate,
                                 cash_div, cash_div_tax, record_date, ex_date, pay_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, [row.get(k, None) for k in ['ts_code', 'end_date', 'div_proc', 'stk_div',
                                 'stk_bo_rate', 'stk_co_rate', 'cash_div', 'cash_div_tax',
                                 'record_date', 'ex_date', 'pay_date']])
                        success_count += 1
                    else:
                        failed_count += 1

                    self.progress_signal.emit(i + 1, len(need_download))

                    if (i + 1) % 50 == 0 or (i + 1) == len(need_download):
                        self.log_signal.emit(f"[{i+1}/{len(need_download)}] 成功: {success_count} | 失败: {failed_count}")

                except Exception as e:
                    failed_count += 1
                    if failed_count <= 5:
                        self.log_signal.emit(f"  {symbol} 分红数据下载失败: {e}")
                    continue

                time.sleep(0.1)

            conn.close()
            self.log_signal.emit(f"\n✅ 分红数据下载完成！成功: {success_count}, 失败: {failed_count}")
            self.finished_signal.emit({'success': True, 'success_count': success_count, 'stopped': self._is_stopped})

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
                    self._is_stopped = True
                    break

                try:
                    df = pro.moneyflow(ts_code=symbol, start_date=start_date, end_date=end_date)
                    if df is not None and not df.empty:
                        # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
                        if 'trade_date' in df.columns:
                            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')

                        # 填充NaN值为None（SQL NULL）
                        df = df.replace({np.nan: None})

                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO moneyflow_data
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, [row.get(k, None) for k in ['ts_code', 'trade_date', 'buy_elg_vol', 'buy_elg_amt',
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
            self.finished_signal.emit({'success': True, 'success_count': success_count, 'stopped': self._is_stopped})
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
                    self._is_stopped = True
                    break

                try:
                    df = pro.top10_holders(ts_code=symbol, top10holdrtype='ALL')
                    if df is not None and not df.empty:
                        # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
                        for col in ['ann_date', 'end_date']:
                            if col in df.columns:
                                df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')

                        # 填充NaN值为None（SQL NULL）
                        df = df.replace({np.nan: None})

                        for _, row in df.iterrows():
                            conn.execute("""
                                INSERT OR REPLACE INTO holders_data
                                (ts_code, ann_date, end_date, holder_name, holder_amount, holder_rank)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, [row.get(k, None) for k in ['ts_code', 'ann_date', 'end_date',
                                 'holder_name', 'holder_amount', 'holder_rank']])
                        success_count += 1

                    self.progress_signal.emit(i + 1, len(symbols))

                except Exception as e:
                    self.log_signal.emit(f"  {symbol} 股东数据下载失败: {e}")
                    continue

                time.sleep(0.1)

            conn.close()
            self.finished_signal.emit({'success': True, 'success_count': success_count, 'stopped': self._is_stopped})
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
                    self._is_stopped = True
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
                elif task_type == 'financial_indicator':
                    self._download_financial_indicator()
                elif task_type == 'balancesheet':
                    self._download_balancesheet()
                elif task_type == 'cashflow_data':
                    self._download_cashflow_data()

                self.progress_signal.emit(i + 1, total_tasks)

            self.finished_signal.emit({'success': True, 'stopped': self._is_stopped})
            self.log_signal.emit("\n✅ 批量下载完成！")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"批量下载失败: {str(e)}\n{traceback.format_exc()}")

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

            # 增量检查：查询每只股票的最新日期
            existing_map = self._get_existing_stocks(conn, 'stock_daily', date_col='date', code_col='stock_code')
            self.log_signal.emit(f"🔍 数据库中已有 {len(existing_map)} 只股票的日线数据")

            # 分类：完全跳过 vs 需要增量下载 vs 全新下载
            skip_list = []
            incremental_list = []
            new_list = []
            for ts_code in symbols:
                if ts_code in existing_map:
                    max_date = existing_map[ts_code]
                    if max_date and str(max_date)[:10] >= end_date[:4] + '-' + end_date[4:6] + '-' + end_date[6:]:
                        skip_list.append(ts_code)
                    else:
                        incremental_list.append(ts_code)
                else:
                    new_list.append(ts_code)

            self.log_signal.emit(f"  跳过(已完整): {len(skip_list)} | 增量更新: {len(incremental_list)} | 新下载: {len(new_list)}")

            if not incremental_list and not new_list:
                self.log_signal.emit("✅ 所有日线数据已是最新，无需下载")
                conn.close()
                self.finished_signal.emit({
                    'success': True, 'total': len(symbols), 'success_count': 0,
                    'failed_count': 0, 'total_inserted': 0, 'skipped': len(skip_list), 'stopped': False
                })
                return

            total_inserted = 0
            success_count = 0
            failed_count = 0
            need_download = incremental_list + new_list

            for i, ts_code in enumerate(need_download, 1):
                if not self._is_running:
                    self._is_stopped = True
                    break

                try:
                    # 增量下载：从已有最新日期+1开始
                    if ts_code in existing_map and ts_code not in new_list:
                        stock_start = (existing_map[ts_code] + timedelta(days=1)).strftime('%Y%m%d')
                    else:
                        stock_start = start_date

                    df = pro.daily(ts_code=ts_code, start_date=stock_start, end_date=end_date,
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
                if i % 50 == 0 or i == len(need_download):
                    self.progress_signal.emit(i, len(need_download))
                    self.log_signal.emit(f"[{i}/{len(need_download)}] 成功: {success_count} | 失败: {failed_count} | 记录: {total_inserted:,}")

            conn.close()

            self.log_signal.emit(f"\n日线数据下载完成！跳过: {len(skip_list)}, 下载成功: {success_count}, 失败: {failed_count}, 总记录: {total_inserted:,}")
            self.finished_signal.emit({
                'success': True,
                'total': len(symbols),
                'success_count': success_count,
                'failed_count': failed_count,
                'total_inserted': total_inserted,
                'skipped': len(skip_list),
                'stopped': self._is_stopped
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
                    data_source VARCHAR(20) DEFAULT 'Tushare',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ts_code, trade_date)
                )
            """)

            total_count = 0
            success_count = 0

            for i, index_code in enumerate(index_codes, 1):
                if not self._is_running:
                    self._is_stopped = True
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
                            insert_data = [tuple(row) + ('Tushare', pd.Timestamp.now()) for row in df_insert.itertuples(index=False, name=None)]

                            # 执行批量插入（13个字段）
                            conn.executemany("""
                                INSERT OR REPLACE INTO index_data
                                (ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount, data_source, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            self.finished_signal.emit({'success': True, 'total': total_count, 'stopped': self._is_stopped})
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

            self.finished_signal.emit({'success': True, 'total': insert_count, 'stopped': self._is_stopped})
            self.log_text.append(f"\n✅ 股票基本信息下载完成！")
            self.log_signal.emit(f"   总计: {insert_count} 只股票")
            self.log_signal.emit(f"   用于：过滤ST股票、新股、停牌股票")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"股票基本信息下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_financial_indicator(self):
        """下载财务指标数据（fina_indicator）- ROE/ROA/毛利率等"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            symbols = self.kwargs.get('symbols', [])
            start_date = self.kwargs.get('start_date', '')
            end_date = self.kwargs.get('end_date', '')

            if not start_date:
                years = self.kwargs.get('years', 5)
                start_date = f'{datetime.now().year - years}0101'
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载财务指标数据（fina_indicator）")
            self.log_signal.emit(f"  股票数: {len(symbols)}")
            self.log_signal.emit(f"  日期范围: {start_date} ~ {end_date}")
            self.log_signal.emit("=" * 60)

            conn = duckdb.connect(db_path)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_indicator (
                    ts_code VARCHAR,
                    ann_date DATE,
                    end_date DATE,
                    roe DOUBLE,
                    roa DOUBLE,
                    grossprofit_margin DOUBLE,
                    netprofit_margin DOUBLE,
                    or_yoy DOUBLE,
                    netprofit_yoy DOUBLE,
                    debt_to_assets DOUBLE,
                    current_ratio DOUBLE,
                    quick_ratio DOUBLE,
                    eps DOUBLE,
                    bps DOUBLE,
                    undist_profit_ps DOUBLE,
                    equity_yoy DOUBLE,
                    rd_exp DOUBLE,
                    data_source VARCHAR(20) DEFAULT 'Tushare',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ts_code, end_date)
                )
            """)

            fields = 'ts_code,ann_date,end_date,roe,roa,grossprofit_margin,netprofit_margin,or_yoy,netprofit_yoy,debt_to_assets,current_ratio,quick_ratio,eps,bps,undist_profit_ps,equity_yoy,rd_exp'

            # 增量检查
            existing_map = self._get_existing_stocks(conn, 'financial_indicator')
            need_download, skipped = self._filter_symbols_for_download(symbols, existing_map, end_date)
            self.log_signal.emit(f"🔍 已有数据: {skipped} 只 | 需下载: {len(need_download)} 只")

            if not need_download:
                self.log_signal.emit("✅ 所有财务指标数据已是最新，无需下载")
                conn.close()
                self.finished_signal.emit({'success': True, 'total_inserted': 0, 'success_count': 0, 'skipped': skipped, 'stopped': False})
                return

            total_inserted = 0
            success_count = 0
            failed_count = 0

            for i, ts_code in enumerate(need_download, 1):
                if not self._is_running:
                    self._is_stopped = True
                    break
                # 限流重试：最多重试3次
                api_success = False
                for retry in range(3):
                    try:
                        df = pro.fina_indicator(
                            ts_code=ts_code,
                            start_date=start_date,
                            end_date=end_date,
                            fields=fields
                        )
                        if df is not None and not df.empty:
                            for col in ['ann_date', 'end_date']:
                                if col in df.columns:
                                    df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')
                            numeric_cols = [c for c in df.columns if c not in ['ts_code', 'ann_date', 'end_date']]
                            df[numeric_cols] = df[numeric_cols].apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)

                            insert_data = [tuple(None if pd.isna(v) else v for v in row) + ('Tushare', pd.Timestamp.now()) for row in df.itertuples(index=False, name=None)]
                            conn.executemany(
                                "INSERT OR REPLACE INTO financial_indicator VALUES (" + ",".join(["?"] * (len(df.columns) + 2)) + ")",
                                insert_data
                            )
                            total_inserted += len(df)
                            success_count += 1
                        else:
                            failed_count += 1
                        api_success = True
                        break
                    except Exception as e:
                        if '每分钟最多访问' in str(e) or '200次' in str(e):
                            # 限流：等待60秒后重试
                            if retry < 2:
                                self.log_signal.emit(f"  ⏳ 限流，等待60秒后重试 {ts_code} ({retry+1}/3)")
                                time.sleep(60)
                            else:
                                failed_count += 1
                                self.log_signal.emit(f"  ❌ {ts_code} 限流重试3次仍失败")
                        else:
                            failed_count += 1
                            if failed_count <= 5:
                                self.log_signal.emit(f"  {ts_code} 失败: {str(e)[:50]}")
                            break

                if i % 50 == 0 or i == len(need_download):
                    self.progress_signal.emit(i, len(need_download))
                    self.log_signal.emit(f"[{i}/{len(need_download)}] 成功: {success_count} | 失败: {failed_count} | 记录: {total_inserted:,}")

                time.sleep(0.35)

            conn.close()
            self.log_signal.emit(f"\n✅ 财务指标下载完成！跳过: {skipped}, 下载成功: {success_count}, 失败: {failed_count}, 总记录: {total_inserted:,}")
            self.finished_signal.emit({
                'success': True,
                'total_inserted': total_inserted,
                'success_count': success_count,
                'skipped': skipped,
                'stopped': self._is_stopped
            })

        except Exception as e:
            import traceback
            self.error_signal.emit(f"财务指标下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_balancesheet(self):
        """下载资产负债表数据（balancesheet）"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            symbols = self.kwargs.get('symbols', [])
            start_date = self.kwargs.get('start_date', '')
            end_date = self.kwargs.get('end_date', '')

            if not start_date:
                years = self.kwargs.get('years', 5)
                start_date = f'{datetime.now().year - years}0101'
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载资产负债表数据（balancesheet）")
            self.log_signal.emit(f"  股票数: {len(symbols)}")
            self.log_signal.emit(f"  日期范围: {start_date} ~ {end_date}")
            self.log_signal.emit("=" * 60)

            conn = duckdb.connect(db_path)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS balance_sheet_tushare (
                    ts_code VARCHAR,
                    ann_date DATE,
                    end_date DATE,
                    total_assets DOUBLE,
                    total_liab DOUBLE,
                    total_hld_eqy_exc_min DOUBLE,
                    total_equity DOUBLE,
                    total_cur_assets DOUBLE,
                    total_cur_liab DOUBLE,
                    money_cap DOUBLE,
                    accounts_rece DOUBLE,
                    inventory DOUBLE,
                    total_nca DOUBLE,
                    total_ncl DOUBLE,
                    data_source VARCHAR(20) DEFAULT 'Tushare',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ts_code, end_date)
                )
            """)

            fields = 'ts_code,ann_date,end_date,total_assets,total_liab,total_hld_eqy_exc_min,total_equity,total_cur_assets,total_cur_liab,money_cap,accounts_rece,inventory,total_nca,total_ncl'

            # 增量检查
            existing_map = self._get_existing_stocks(conn, 'balance_sheet_tushare')
            need_download, skipped = self._filter_symbols_for_download(symbols, existing_map, end_date)
            self.log_signal.emit(f"🔍 已有数据: {skipped} 只 | 需下载: {len(need_download)} 只")

            if not need_download:
                self.log_signal.emit("✅ 所有资产负债表数据已是最新，无需下载")
                conn.close()
                self.finished_signal.emit({'success': True, 'total_inserted': 0, 'success_count': 0, 'skipped': skipped, 'stopped': False})
                return

            total_inserted = 0
            success_count = 0
            failed_count = 0

            for i, ts_code in enumerate(need_download, 1):
                if not self._is_running:
                    self._is_stopped = True
                    break
                api_success = False
                for retry in range(3):
                    try:
                        df = pro.balancesheet(
                            ts_code=ts_code,
                            start_date=start_date,
                            end_date=end_date,
                            fields=fields
                        )
                        if df is not None and not df.empty:
                            for col in ['ann_date', 'end_date']:
                                if col in df.columns:
                                    df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')
                            numeric_cols = [c for c in df.columns if c not in ['ts_code', 'ann_date', 'end_date']]
                            df[numeric_cols] = df[numeric_cols].apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)

                            insert_data = [tuple(None if pd.isna(v) else v for v in row) + ('Tushare', pd.Timestamp.now()) for row in df.itertuples(index=False, name=None)]
                            conn.executemany(
                                "INSERT OR REPLACE INTO balance_sheet_tushare VALUES (" + ",".join(["?"] * (len(df.columns) + 2)) + ")",
                                insert_data
                            )
                            total_inserted += len(df)
                            success_count += 1
                        else:
                            failed_count += 1
                        api_success = True
                        break
                    except Exception as e:
                        if '每分钟最多访问' in str(e) or '200次' in str(e):
                            if retry < 2:
                                self.log_signal.emit(f"  ⏳ 限流，等待60秒后重试 {ts_code} ({retry+1}/3)")
                                time.sleep(60)
                            else:
                                failed_count += 1
                                self.log_signal.emit(f"  ❌ {ts_code} 限流重试3次仍失败")
                        else:
                            failed_count += 1
                            if failed_count <= 5:
                                self.log_signal.emit(f"  {ts_code} 失败: {str(e)[:50]}")
                            break

                if i % 50 == 0 or i == len(need_download):
                    self.progress_signal.emit(i, len(need_download))
                    self.log_signal.emit(f"[{i}/{len(need_download)}] 成功: {success_count} | 失败: {failed_count} | 记录: {total_inserted:,}")

                time.sleep(0.35)

            conn.close()
            self.log_signal.emit(f"\n✅ 资产负债表下载完成！跳过: {skipped}, 下载成功: {success_count}, 失败: {failed_count}, 总记录: {total_inserted:,}")
            self.finished_signal.emit({
                'success': True,
                'total_inserted': total_inserted,
                'success_count': success_count,
                'skipped': skipped,
                'stopped': self._is_stopped
            })

        except Exception as e:
            import traceback
            self.error_signal.emit(f"资产负债表下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_cashflow_data(self):
        """下载现金流量表数据（cashflow）"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            symbols = self.kwargs.get('symbols', [])
            start_date = self.kwargs.get('start_date', '')
            end_date = self.kwargs.get('end_date', '')

            if not start_date:
                years = self.kwargs.get('years', 5)
                start_date = f'{datetime.now().year - years}0101'
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载现金流量表数据（cashflow）")
            self.log_signal.emit(f"  股票数: {len(symbols)}")
            self.log_signal.emit(f"  日期范围: {start_date} ~ {end_date}")
            self.log_signal.emit("=" * 60)

            conn = duckdb.connect(db_path)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cash_flow_statement_tushare (
                    ts_code VARCHAR,
                    ann_date DATE,
                    end_date DATE,
                    c_pay_goods DOUBLE,
                    c_pay_for_sv DOUBLE,
                    c_paid_to_for_empl DOUBLE,
                    n_cashflow_act DOUBLE,
                    n_cashflow_inv_act DOUBLE,
                    n_cashflow_fnc_act DOUBLE,
                    c_fr_sale_sg DOUBLE,
                    n_incr_cash_cash_equ DOUBLE,
                    data_source VARCHAR(20) DEFAULT 'Tushare',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ts_code, end_date)
                )
            """)

            fields = 'ts_code,ann_date,end_date,c_pay_goods,c_pay_for_sv,c_paid_to_for_empl,n_cashflow_act,n_cashflow_inv_act,n_cashflow_fnc_act,c_fr_sale_sg,n_incr_cash_cash_equ'

            # 增量检查
            existing_map = self._get_existing_stocks(conn, 'cash_flow_statement_tushare')
            need_download, skipped = self._filter_symbols_for_download(symbols, existing_map, end_date)
            self.log_signal.emit(f"🔍 已有数据: {skipped} 只 | 需下载: {len(need_download)} 只")

            if not need_download:
                self.log_signal.emit("✅ 所有现金流量表数据已是最新，无需下载")
                conn.close()
                self.finished_signal.emit({'success': True, 'total_inserted': 0, 'success_count': 0, 'skipped': skipped, 'stopped': False})
                return

            total_inserted = 0
            success_count = 0
            failed_count = 0

            for i, ts_code in enumerate(need_download, 1):
                if not self._is_running:
                    self._is_stopped = True
                    break
                api_success = False
                for retry in range(3):
                    try:
                        df = pro.cashflow(
                            ts_code=ts_code,
                            start_date=start_date,
                            end_date=end_date,
                            fields=fields
                        )
                        if df is not None and not df.empty:
                            for col in ['ann_date', 'end_date']:
                                if col in df.columns:
                                    df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')
                            numeric_cols = [c for c in df.columns if c not in ['ts_code', 'ann_date', 'end_date']]
                            df[numeric_cols] = df[numeric_cols].apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)

                            insert_data = [tuple(None if pd.isna(v) else v for v in row) + ('Tushare', pd.Timestamp.now()) for row in df.itertuples(index=False, name=None)]
                            conn.executemany(
                                "INSERT OR REPLACE INTO cash_flow_statement_tushare VALUES (" + ",".join(["?"] * (len(df.columns) + 2)) + ")",
                                insert_data
                            )
                            total_inserted += len(df)
                            success_count += 1
                        else:
                            failed_count += 1
                        api_success = True
                        break
                    except Exception as e:
                        if '每分钟最多访问' in str(e) or '200次' in str(e):
                            if retry < 2:
                                self.log_signal.emit(f"  ⏳ 限流，等待60秒后重试 {ts_code} ({retry+1}/3)")
                                time.sleep(60)
                            else:
                                failed_count += 1
                                self.log_signal.emit(f"  ❌ {ts_code} 限流重试3次仍失败")
                        else:
                            failed_count += 1
                            if failed_count <= 5:
                                self.log_signal.emit(f"  {ts_code} 失败: {str(e)[:50]}")
                            break

                if i % 50 == 0 or i == len(need_download):
                    self.progress_signal.emit(i, len(need_download))
                    self.log_signal.emit(f"[{i}/{len(need_download)}] 成功: {success_count} | 失败: {failed_count} | 记录: {total_inserted:,}")

                time.sleep(0.35)

            conn.close()
            self.log_signal.emit(f"\n✅ 现金流量表下载完成！跳过: {skipped}, 下载成功: {success_count}, 失败: {failed_count}, 总记录: {total_inserted:,}")
            self.finished_signal.emit({
                'success': True,
                'total_inserted': total_inserted,
                'success_count': success_count,
                'skipped': skipped,
                'stopped': self._is_stopped
            })

        except Exception as e:
            import traceback
            self.error_signal.emit(f"现金流量表下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_cb_basic(self):
        """下载可转债基本信息（cb_basic）"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载可转债基本信息（cb_basic）")
            self.log_signal.emit("=" * 60)

            conn = duckdb.connect(db_path)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cb_basic (
                    ts_code VARCHAR PRIMARY KEY,
                    bond_full_name VARCHAR,
                    bond_short_name VARCHAR,
                    stk_code VARCHAR,
                    stk_short_name VARCHAR,
                    maturity DOUBLE,
                    par DOUBLE,
                    issue_price DOUBLE,
                    issue_size DOUBLE,
                    remain_size DOUBLE,
                    value_date DATE,
                    maturity_date DATE,
                    coupon_rate DOUBLE,
                    list_date DATE,
                    delist_date DATE,
                    exchange VARCHAR,
                    conv_start_date DATE,
                    conv_end_date DATE,
                    first_conv_price DOUBLE,
                    conv_price DOUBLE,
                    maturity_put_price VARCHAR,
                    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.log_signal.emit("✅ 数据库连接成功，正在获取可转债列表...")

            df = pro.cb_basic(fields=(
                'ts_code,bond_full_name,bond_short_name,stk_code,stk_short_name,'
                'maturity,par,issue_price,issue_size,remain_size,'
                'value_date,maturity_date,coupon_rate,'
                'list_date,delist_date,exchange,'
                'conv_start_date,conv_end_date,first_conv_price,conv_price,'
                'maturity_put_price'
            ))

            if df is None or df.empty:
                self.error_signal.emit("获取可转债列表失败或返回空数据")
                conn.close()
                return

            # 过滤只保留在市 + 近期退市的可转债
            df['delist_date'] = df['delist_date'].replace('', pd.NaT)
            self.log_signal.emit(f"✅ 获取到 {len(df)} 只可转债")

            conn.execute("DELETE FROM cb_basic")

            insert_count = 0
            for _, row in df.iterrows():
                try:
                    def _to_date(val):
                        if pd.isna(val) or val == '' or val is None:
                            return None
                        return pd.to_datetime(str(val), format='%Y%m%d', errors='coerce')

                    conn.execute("""
                        INSERT INTO cb_basic
                        (ts_code,bond_full_name,bond_short_name,stk_code,stk_short_name,
                         maturity,par,issue_price,issue_size,remain_size,
                         value_date,maturity_date,coupon_rate,
                         list_date,delist_date,exchange,
                         conv_start_date,conv_end_date,first_conv_price,conv_price,
                         maturity_put_price)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, [
                        row['ts_code'],
                        row.get('bond_full_name'),
                        row.get('bond_short_name'),
                        row.get('stk_code'),
                        row.get('stk_short_name'),
                        row.get('maturity'),
                        row.get('par'),
                        row.get('issue_price'),
                        row.get('issue_size'),
                        row.get('remain_size'),
                        _to_date(row.get('value_date')),
                        _to_date(row.get('maturity_date')),
                        row.get('coupon_rate'),
                        _to_date(row.get('list_date')),
                        _to_date(row.get('delist_date')),
                        row.get('exchange'),
                        _to_date(row.get('conv_start_date')),
                        _to_date(row.get('conv_end_date')),
                        row.get('first_conv_price'),
                        row.get('conv_price'),
                        str(row.get('maturity_put_price', '')) if row.get('maturity_put_price') else None,
                    ])
                    insert_count += 1
                except Exception as e:
                    self.log_signal.emit(f"  ⚠️  {row.get('ts_code', '?')} 插入失败: {e}")
                    continue

            conn.close()
            self.finished_signal.emit({'success': True, 'total': insert_count, 'success_count': insert_count, 'stopped': self._is_stopped})
            self.log_signal.emit(f"\n✅ 可转债基本信息下载完成！共 {insert_count} 只")

        except Exception as e:
            import traceback
            self.error_signal.emit(f"可转债基本信息下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_cb_daily(self):
        """下载可转债日行情（cb_daily），含转股价值和转股溢价率"""
        try:
            pro = self._get_tushare_pro()
            db_path = self.kwargs.get('db_path') or self._get_db_path()
            start_date = self.kwargs.get('start_date', '')
            end_date = self.kwargs.get('end_date', '')

            if not start_date:
                years = self.kwargs.get('years', 3)
                start_date = f'{datetime.now().year - years}0101'
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            self.log_signal.emit("=" * 60)
            self.log_signal.emit("开始下载可转债日行情（cb_daily）")
            self.log_signal.emit(f"  日期范围: {start_date} ~ {end_date}")
            self.log_signal.emit("=" * 60)

            conn = duckdb.connect(db_path)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cb_daily (
                    ts_code VARCHAR,
                    trade_date DATE,
                    pre_close DOUBLE,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    change DOUBLE,
                    pct_chg DOUBLE,
                    vol DOUBLE,
                    amount DOUBLE,
                    bond_value DOUBLE,
                    bond_over_rate DOUBLE,
                    cb_value DOUBLE,
                    cb_over_rate DOUBLE,
                    PRIMARY KEY (ts_code, trade_date)
                )
            """)

            # 获取可转债列表
            try:
                cb_list = conn.execute("SELECT ts_code FROM cb_basic").fetchall()
                cb_codes = [r[0] for r in cb_list]
            except Exception:
                cb_codes = []

            if not cb_codes:
                self.log_signal.emit("⚠️ cb_basic 表为空，先从 API 获取可转债列表...")
                df_basic = pro.cb_basic(fields='ts_code')
                if df_basic is not None and not df_basic.empty:
                    cb_codes = df_basic['ts_code'].tolist()
                else:
                    self.error_signal.emit("无法获取可转债列表")
                    conn.close()
                    return

            # 增量检查：查每个转债的最新日期
            existing_map = self._get_existing_stocks(conn, 'cb_daily', date_col='trade_date', code_col='ts_code')
            need_download, skipped = self._filter_symbols_for_download(cb_codes, existing_map, end_date)
            self.log_signal.emit(f"🔍 已有数据: {skipped} 只 | 需下载: {len(need_download)} 只")

            if not need_download:
                self.log_signal.emit("✅ 所有可转债日行情已是最新，无需下载")
                conn.close()
                self.finished_signal.emit({'success': True, 'total_inserted': 0, 'success_count': 0, 'skipped': skipped, 'stopped': False})
                return

            total_inserted = 0
            success_count = 0
            failed_count = 0

            for i, ts_code in enumerate(need_download, 1):
                if not self._is_running:
                    self._is_stopped = True
                    break

                # 增量：对有部分数据的转债从最新日期+1开始
                stock_start = start_date
                if ts_code in existing_map and existing_map[ts_code]:
                    next_day = pd.to_datetime(str(existing_map[ts_code])) + timedelta(days=1)
                    stock_start = next_day.strftime('%Y%m%d')

                api_success = False
                for retry in range(3):
                    try:
                        df = pro.cb_daily(
                            ts_code=ts_code,
                            start_date=stock_start,
                            end_date=end_date,
                            fields='ts_code,trade_date,pre_close,open,high,low,close,change,pct_chg,vol,amount,bond_value,bond_over_rate,cb_value,cb_over_rate'
                        )
                        if df is not None and not df.empty:
                            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
                            numeric_cols = [c for c in df.columns if c not in ['ts_code', 'trade_date']]
                            df[numeric_cols] = df[numeric_cols].apply(lambda x: pd.to_numeric(x, errors='coerce'))

                            insert_data = [
                                tuple(None if pd.isna(v) else v for v in row)
                                for row in df.itertuples(index=False, name=None)
                            ]
                            conn.executemany(
                                "INSERT OR REPLACE INTO cb_daily VALUES (" + ",".join(["?"] * len(df.columns)) + ")",
                                insert_data
                            )
                            total_inserted += len(df)
                            success_count += 1
                        else:
                            # 空数据不算失败
                            success_count += 1
                        api_success = True
                        break
                    except Exception as e:
                        if '每分钟最多访问' in str(e) or '200次' in str(e) or '频率' in str(e):
                            if retry < 2:
                                wait = 60 + retry * 30
                                self.log_signal.emit(f"  ⏳ 限流，等待{wait}秒后重试 {ts_code} ({retry+1}/3)")
                                time.sleep(wait)
                            else:
                                failed_count += 1
                                self.log_signal.emit(f"  ❌ {ts_code} 限流重试3次仍失败")
                        else:
                            failed_count += 1
                            if failed_count <= 5:
                                self.log_signal.emit(f"  ❌ {ts_code} 失败: {str(e)[:80]}")
                            break

                if i % 20 == 0 or i == len(need_download):
                    self.progress_signal.emit(i, len(need_download))
                    self.log_signal.emit(f"[{i}/{len(need_download)}] 成功: {success_count} | 失败: {failed_count} | 记录: {total_inserted:,}")

                time.sleep(0.4)

            conn.close()
            self.log_signal.emit(f"\n✅ 可转债日行情下载完成！跳过: {skipped}, 成功: {success_count}, 失败: {failed_count}, 总记录: {total_inserted:,}")
            self.finished_signal.emit({
                'success': True,
                'total_inserted': total_inserted,
                'success_count': success_count,
                'skipped': skipped,
                'stopped': self._is_stopped
            })

        except Exception as e:
            import traceback
            self.error_signal.emit(f"可转债日行情下载失败: {str(e)}\n{traceback.format_exc()}")

class TushareDataWidget(QWidget):
    """Tushare数据下载组件（整合版）"""

    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.stop_btn = None  # 停止按钮
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

        # 控制按钮区域
        control_layout = QHBoxLayout()

        # 停止按钮
        self.stop_btn = QPushButton("🛑 停止下载")
        self.stop_btn.setFont(QFont("Microsoft YaHei", 10))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.stop_btn.setEnabled(False)  # 初始禁用
        self.stop_btn.clicked.connect(self.stop_download)
        control_layout.addWidget(self.stop_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

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

        # 财务指标标签页
        financial_indicator_tab = self._create_financial_indicator_tab()
        tab_widget.addTab(financial_indicator_tab, "📈 财务指标")

        # 资产负债表标签页
        balancesheet_tab = self._create_balancesheet_tab()
        tab_widget.addTab(balancesheet_tab, "📋 资产负债表")

        # 现金流量表标签页
        cashflow_tab = self._create_cashflow_tab()
        tab_widget.addTab(cashflow_tab, "💹 现金流量表")

        # 可转债数据标签页
        cb_data_tab = self._create_cb_data_tab()
        tab_widget.addTab(cb_data_tab, "🔄 可转债数据")

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

        self.chk_financial_indicator = QCheckBox("📈 财务指标（ROE/ROA等，基本面因子必需）")
        self.chk_financial_indicator.setChecked(True)
        type_layout.addWidget(self.chk_financial_indicator, 3, 0)

        self.chk_balancesheet = QCheckBox("📋 资产负债表")
        self.chk_balancesheet.setChecked(True)
        type_layout.addWidget(self.chk_balancesheet, 3, 1)

        self.chk_cashflow = QCheckBox("💹 现金流量表")
        self.chk_cashflow.setChecked(False)
        type_layout.addWidget(self.chk_cashflow, 4, 0)

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

    def _create_financial_indicator_tab(self):
        """创建财务指标数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.fi_years_spin = QSpinBox()
        self.fi_years_spin.setRange(1, 20)
        self.fi_years_spin.setValue(5)
        self.fi_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.fi_years_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 <b>说明：</b>财务指标数据（fina_indicator）包含以下关键指标：<br><br>"
            "• <b>ROE</b> - 净资产收益率（基本面因子必需）<br>"
            "• <b>ROA</b> - 总资产收益率（基本面因子必需）<br>"
            "• <b>毛利率</b> - grossprofit_margin<br>"
            "• <b>净利润率</b> - netprofit_margin<br>"
            "• <b>营收增长率</b> - or_yoy<br>"
            "• <b>净利润增长率</b> - netprofit_yoy<br>"
            "• <b>资产负债率</b> - debt_to_assets<br>"
            "• EPS、BPS、流动比率等<br><br>"
            "⚠️ 这是101因子平台基本面因子的<b>核心数据源</b>，建议优先下载。"
        )
        info_label.setStyleSheet("color: #333; padding: 10px; background: #fff3e0; border-radius: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载财务指标数据")
        download_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        download_btn.clicked.connect(self.start_download_financial_indicator)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_balancesheet_tab(self):
        """创建资产负债表标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.bs_years_spin = QSpinBox()
        self.bs_years_spin.setRange(1, 20)
        self.bs_years_spin.setValue(5)
        self.bs_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.bs_years_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 <b>说明：</b>资产负债表数据（balancesheet）包含：<br><br>"
            "• <b>总资产</b> - total_assets<br>"
            "• <b>总负债</b> - total_liab<br>"
            "• <b>所有者权益</b> - total_equity<br>"
            "• <b>流动资产/负债</b> - current assets/liabilities<br>"
            "• <b>货币资金、应收账款、存货</b>等<br><br>"
            "用于计算资产负债率、流动性指标等基本面因子。"
        )
        info_label.setStyleSheet("color: #666; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载资产负债表数据")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_balancesheet)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_cashflow_tab(self):
        """创建现金流量表标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("下载配置")
        config_layout = QFormLayout(config_group)

        self.cf_years_spin = QSpinBox()
        self.cf_years_spin.setRange(1, 20)
        self.cf_years_spin.setValue(5)
        self.cf_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.cf_years_spin)

        layout.addWidget(config_group)

        info_label = QLabel(
            "📌 <b>说明：</b>现金流量表数据（cashflow）包含：<br><br>"
            "• <b>经营活动现金流</b> - n_cashflow_act<br>"
            "• <b>投资活动现金流</b> - n_cashflow_inv_act<br>"
            "• <b>筹资活动现金流</b> - n_cashflow_fnc_act<br>"
            "• <b>销售收到的现金</b>等<br><br>"
            "用于分析企业现金流健康状况，进阶分析用。"
        )
        info_label.setStyleSheet("color: #666; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        layout.addWidget(info_label)

        download_btn = QPushButton("🚀 开始下载现金流量表数据")
        download_btn.setFont(QFont("Microsoft YaHei", 10))
        download_btn.clicked.connect(self.start_download_cashflow)
        layout.addWidget(download_btn)

        layout.addStretch()
        return tab

    def _create_cb_data_tab(self):
        """创建可转债数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # CB Basic 下载
        basic_group = QGroupBox("可转债基本信息（cb_basic）")
        basic_layout = QVBoxLayout(basic_group)

        basic_info = QLabel(
            "📋 包含：转债代码、正股代码、转股价格、上市日期、到期日期、票面利率等。\n"
            "可转债日行情下载的前置依赖，需先下载基本信息。"
        )
        basic_info.setStyleSheet("color: #666; padding: 5px;")
        basic_layout.addWidget(basic_info)

        cb_basic_btn = QPushButton("🚀 下载可转债基本信息")
        cb_basic_btn.setFont(QFont("Microsoft YaHei", 10))
        cb_basic_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        cb_basic_btn.clicked.connect(self.start_download_cb_basic)
        basic_layout.addWidget(cb_basic_btn)
        layout.addWidget(basic_group)

        # CB Daily 下载
        daily_group = QGroupBox("可转债日行情（cb_daily）")
        daily_layout = QVBoxLayout(daily_group)

        config_layout = QFormLayout()
        self.cb_years_spin = QSpinBox()
        self.cb_years_spin.setRange(1, 10)
        self.cb_years_spin.setValue(3)
        self.cb_years_spin.setSuffix(" 年")
        config_layout.addRow("数据年份:", self.cb_years_spin)
        daily_layout.addLayout(config_layout)

        daily_info = QLabel(
            "📊 包含：OHLCV行情 + <b>转股价值</b>(cb_value) + <b>转股溢价率</b>(cb_over_rate)\n\n"
            "转股溢价率由 Tushare 直接提供，无需手动计算。\n"
            "溢价率 = 转债价格/转股价值 - 1\n\n"
            "⚠️ 需要 2000 积分以上。先下载「可转债基本信息」再下载日行情。"
        )
        daily_info.setStyleSheet("color: #333; padding: 10px; background: #fff3e0; border-radius: 5px;")
        daily_layout.addWidget(daily_info)

        cb_daily_btn = QPushButton("🚀 下载可转债日行情")
        cb_daily_btn.setFont(QFont("Microsoft YaHei", 10))
        cb_daily_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #F57C00; }
        """)
        cb_daily_btn.clicked.connect(self.start_download_cb_daily)
        daily_layout.addWidget(cb_daily_btn)
        layout.addWidget(daily_group)

        layout.addStretch()
        return tab

    def start_download_financial_indicator(self):
        """开始下载财务指标数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            symbols = stock_list['ts_code'].tolist()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
            return

        years = self.fi_years_spin.value()
        start_date = f"{datetime.now().year - years}0101"
        end_date = datetime.now().strftime('%Y%m%d')

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载财务指标数据...")
        self.log_text.append(f"  股票数: {len(symbols)}, 日期: {start_date} ~ {end_date}")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        thread = TushareDownloadThread(
            'financial_indicator',
            token=token,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
        self._start_download_thread(thread)

    def start_download_balancesheet(self):
        """开始下载资产负债表数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            symbols = stock_list['ts_code'].tolist()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
            return

        years = self.bs_years_spin.value()
        start_date = f"{datetime.now().year - years}0101"
        end_date = datetime.now().strftime('%Y%m%d')

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载资产负债表数据...")
        self.log_text.append(f"  股票数: {len(symbols)}, 日期: {start_date} ~ {end_date}")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        thread = TushareDownloadThread(
            'balancesheet',
            token=token,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
        self._start_download_thread(thread)

    def start_download_cashflow(self):
        """开始下载现金流量表数据"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            symbols = stock_list['ts_code'].tolist()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取股票列表失败: {e}")
            return

        years = self.cf_years_spin.value()
        start_date = f"{datetime.now().year - years}0101"
        end_date = datetime.now().strftime('%Y%m%d')

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载现金流量表数据...")
        self.log_text.append(f"  股票数: {len(symbols)}, 日期: {start_date} ~ {end_date}")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        thread = TushareDownloadThread(
            'cashflow_data',
            token=token,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
        self._start_download_thread(thread)

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
        # 测试连接不需要停止按钮
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
            # 计算日期范围（也供后续任务使用）
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

        # 确保日期范围可用（即使日线未勾选）
        if 'start_date' not in dir():
            years_back = self.quick_years_spin.value()
            start_date = f"{datetime.now().year - years_back}0101"
            end_date = datetime.now().strftime('%Y%m%d')

        if self.chk_financial_indicator.isChecked():
            task_list.append({
                'name': '财务指标（ROE/ROA等）',
                'type': 'financial_indicator',
                'params': {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date
                }
            })

        if self.chk_balancesheet.isChecked():
            task_list.append({
                'name': '资产负债表',
                'type': 'balancesheet',
                'params': {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date
                }
            })

        if self.chk_cashflow.isChecked():
            task_list.append({
                'name': '现金流量表',
                'type': 'cashflow_data',
                'params': {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date
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

        thread = TushareDownloadThread(
            'batch_download',
            token=token,
            task_list=task_list
        )
        self._start_download_thread(thread)

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

        thread = TushareDownloadThread(
            'market_cap',
            token=token,
            start_date=start_date,
            end_date=end_date
        )
        self._start_download_thread(thread)

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

        thread = TushareDownloadThread(
            'financial',
            token=token,
            symbols=symbols,
            years=self.financial_years_spin.value()
        )
        self._start_download_thread(thread)

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

        thread = TushareDownloadThread(
            'dividend',
            token=token,
            symbols=symbols,
            years=self.dividend_years_spin.value()
        )
        self._start_download_thread(thread)

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

        thread = TushareDownloadThread(
            'moneyflow',
            token=token,
            symbols=symbols,
            days_back=self.moneyflow_days_spin.value()
        )
        self._start_download_thread(thread)

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

        thread = TushareDownloadThread(
            'holders',
            token=token,
            symbols=symbols,
            years=self.holders_years_spin.value()
        )
        self._start_download_thread(thread)

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

        thread = TushareDownloadThread(
            'index_data',
            token=token,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        self._start_download_thread(thread)

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

        thread = TushareDownloadThread(
            'stock_basic',
            token=token
        )
        self._start_download_thread(thread)

    def start_download_cb_basic(self):
        """开始下载可转债基本信息"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载可转债基本信息...")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        thread = TushareDownloadThread('cb_basic', token=token)
        self._start_download_thread(thread)

    def start_download_cb_daily(self):
        """开始下载可转债日行情"""
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "请输入Tushare Token")
            return

        os.environ['TUSHARE_TOKEN'] = token
        years = self.cb_years_spin.value()
        start_date = f"{datetime.now().year - years}0101"
        end_date = datetime.now().strftime('%Y%m%d')

        self.log_text.append("=" * 60)
        self.log_text.append("🚀 开始下载可转债日行情...")
        self.log_text.append(f"  日期范围: {start_date} ~ {end_date}")
        self.log_text.append("=" * 60)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        thread = TushareDownloadThread(
            'cb_daily',
            token=token,
            start_date=start_date,
            end_date=end_date,
            years=years
        )
        self._start_download_thread(thread)

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
        self.stop_btn.setEnabled(False)

        if result.get('success'):
            total_inserted = result.get('total_inserted', 0)
            success_count = result.get('success_count', 0)

            if result.get('stopped'):
                self.log_text.append("\n⚠️ 下载已被用户停止")
                QMessageBox.information(self, "已停止", "⚠️ 下载已被停止\n已下载的数据已保存")
                return

            if total_inserted > 0:
                QMessageBox.information(self, "完成", f"✅ 下载完成！\n\n新增数据: {total_inserted:,} 条")
            elif success_count > 0:
                QMessageBox.information(self, "完成", f"✅ 下载完成！\n\n成功: {success_count} 只股票")

    def _on_error(self, error_msg):
        """处理错误"""
        self.progress_bar.setVisible(False)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "错误", error_msg)

    def _on_thread_finished(self):
        """QThread内置finished信号：线程真正结束后清理引用"""
        self.download_thread = None

    def stop_download(self):
        """停止下载"""
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认停止",
                "确定要停止当前下载吗？\n\n已下载的数据将保存到数据库。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.download_thread.stop()
                self.stop_btn.setEnabled(False)
                self.log_text.append("\n⚠️ 正在停止下载，请稍候...")
        else:
            QMessageBox.information(self, "提示", "当前没有正在进行的下载任务")

    def _start_download_thread(self, thread):
        """启动下载线程的辅助方法"""
        self.download_thread = thread
        self.download_thread.log_signal.connect(self._on_log)
        self.download_thread.progress_signal.connect(self._on_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.error_signal.connect(self._on_error)
        self.download_thread.finished.connect(self._on_thread_finished)
        self.stop_btn.setEnabled(True)
        self.download_thread.start()


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
