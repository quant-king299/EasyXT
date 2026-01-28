# -*- coding: utf-8 -*-
"""
在GUI中添加复权选项的代码片段
将此代码添加到 local_data_manager_widget.py 的适当位置
"""

# ========== 在数据操作组中添加复权选项 ==========

# 在 init_ui 方法中，找到"下载数据类型选择"部分
# 在 data_type_combo 旁边添加复权选项

# 原有代码（约578行附近）：
# data_type_layout = QHBoxLayout()
# self.data_type_combo = QComboBox()
# self.data_type_combo.addItems(["日线数据", "1分钟数据", "5分钟数据", "15分钟数据", "30分钟数据", "60分钟数据"])
# data_type_layout.addWidget(QLabel("数据类型:"))
# data_type_layout.addWidget(self.data_type_combo)
# data_type_layout.addStretch()
# action_layout.addLayout(data_type_layout, 1, 0, 1, 4)

# 替换为：
# 数据类型和复权选项（一行）
data_type_layout = QHBoxLayout()
self.data_type_combo = QComboBox()
self.data_type_combo.addItems(["日线数据", "1分钟数据", "5分钟数据", "15分钟数据", "30分钟数据", "60分钟数据"])
data_type_layout.addWidget(QLabel("数据类型:"))
data_type_layout.addWidget(self.data_type_combo)

# 复权选项
self.adjust_combo = QComboBox()
self.adjust_combo.addItems(["不复权", "前复权", "后复权"])
self.adjust_combo.setCurrentIndex(0)  # 默认不复权
self.adjust_combo.setToolTip(
    "不复权：原始价格，适合短期分析\n"
    "前复权：当前价真实，适合短期回测\n"
    "后复权：历史价真实，适合长期回测"
)
data_type_layout.addWidget(QLabel("  复权:"))
data_type_layout.addWidget(self.adjust_combo)

data_type_layout.addStretch()
action_layout.addLayout(data_type_layout, 1, 0, 1, 4)


# ========== 修改 download_single_stock 方法 ==========

def download_single_stock(self):
    """下载单个标的的数据（支持复权）"""
    # 获取输入的股票代码
    stock_code = self.stock_code_input.text().strip()

    if not stock_code:
        QMessageBox.warning(self, "提示", "请输入股票/ETF代码")
        return

    # 标准化代码格式
    stock_code = stock_code.upper()

    # 验证代码格式
    if not ('.' in stock_code):
        # 如果没有后缀，尝试自动添加
        if stock_code.startswith('6') or stock_code.startswith('5'):
            stock_code = stock_code + '.SH'
        elif stock_code.startswith('0') or stock_code.startswith('3') or stock_code.startswith('1'):
            stock_code = stock_code + '.SZ'

    # 获取日期范围
    start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
    end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

    # 获取数据类型
    data_type_text = self.data_type_combo.currentText()
    period_map = {
        "日线数据": "1d",
        "1分钟数据": "1m",
        "5分钟数据": "5m",
        "15分钟数据": "15m",
        "30分钟数据": "30m",
        "60分钟数据": "60m"
    }
    period = period_map.get(data_type_text, "1d")

    # 获取复权类型
    adjust_text = self.adjust_combo.currentText()
    adjust_map = {
        "不复权": "none",
        "前复权": "qfq",
        "后复权": "hfq"
    }
    adjust = adjust_map.get(adjust_text, "none")

    self.log(f"🎯 开始下载单个标的: {stock_code}")
    self.log(f"   数据类型: {data_type_text}")
    self.log(f"   复权方式: {adjust_text}")
    self.log(f"   日期范围: {start_date} ~ {end_date}")

    # 禁用按钮
    self.manual_download_btn.setEnabled(False)

    # 创建下载线程
    self.download_thread = SingleStockDownloadThread(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        period=period,
        adjust=adjust  # 新增：复权参数
    )
    self.download_thread.log_signal.connect(self.log)
    self.download_thread.finished_signal.connect(self.on_single_download_finished)
    self.download_thread.error_signal.connect(self.on_single_download_error)
    self.download_thread.start()


# ========== 修改 SingleStockDownloadThread 类 ==========

class SingleStockDownloadThread(QThread):
    """单个标的下载线程（支持复权）"""

    def __init__(self, stock_code, start_date, end_date, period='1d', adjust='none'):
        super().__init__()
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.period = period  # '1d', '1m', '5m', '15m', '30m', '60m'
        self.adjust = adjust  # 新增：复权类型 'none', 'qfq', 'hfq'
        self._is_running = True

    def run(self):
        """运行下载任务"""
        manager = None
        try:
            # ... (原有的下载逻辑)

            # 在保存数据后，如果需要复权，应用复权
            if self.adjust != 'none':
                # 尝试下载分红数据
                self.log_signal.emit(f"📊 获取 {self.stock_code} 分红数据...")

                try:
                    # 这里可以调用下载分红数据的函数
                    # 或者直接从已有的分红数据中读取
                    # 为了简化，这里先跳过，实际使用时需要补充

                    self.log_signal.emit(f"⚠️ 分红数据暂未集成")
                except Exception as e:
                    self.log_signal.emit(f"  无法加载分红数据: {e}")

        except Exception as e:
            import traceback
            error_msg = f"❌ 下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
        finally:
            # 确保关闭管理器
            if manager is not None:
                try:
                    manager.close()
                except:
                    pass


# ========== 添加复权说明对话框 ==========

def show_adjustment_info(self):
    """显示复权说明对话框"""
    info_text = """
╔═════════════════════════════════════════════════════╗
║                    复权类型说明                           ║
╠═══════════════════════════════════════════════════════╣
║                                                           ║
║ 1️⃣ 不复权                                              ║
║    • 定义：原始价格，不做任何调整                        ║
║    • 优点：所有价格都是真实的，可以直接用于交易           ║
║    • 缺点：有分红除权时价格会跳跃，影响技术分析           ║
║    • 适用：短期分析（日内、几天）、实时交易               ║
║                                                           ║
║ 2️⃣ 前复权                                              ║
║    • 定义：保持当前价格不变，调整历史价格                   ║
║    • 原理：除权日之前的所有价格 × 复权因子                 ║
║    • 优点：当前价格真实，便于与实时行情对比                 ║
║    • 缺点：历史价格可能为负，长期数据失真                   ║
║    • 适用：短期回测（最近1年）、技术分析                     ║
║                                                           ║
║ 3️⃣ 后复权                                              ║
║    • 定义：保持历史价格不变，调整当前价格                   ║
║    • 原理：除权日之后的所有价格 × 复权因子                  ║
║    • 优点：历史价格真实，能反映真实收益                     ║
║    • 缺点：当前价格不真实，无法直接用于交易                   ║
║    • 适用：长期回测（3年以上）、因子分析                       ║
║                                                           ║
║ 💡 建议：                                                ║
║    • 短期交易者（日内、周内）：使用不复权                     ║
║    • 短期回测（1年内）：使用前复权                             ║
║    • 长期回测（3年以上）：使用后复权                             ║
║    • 因子分析：使用后复权                                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════╝
    """

    QMessageBox.information(self, "复权说明", info_text)


# ========== 在 init_ui 中添加帮助按钮 ==========

# 在快速操作区域添加帮助按钮
help_layout = QHBoxLayout()

self.adjust_help_btn = QPushButton("❓ 复权说明")
self.adjust_help_btn.clicked.connect(self.show_adjustment_info)
self.adjust_help_btn.setStyleSheet("""
    QPushButton {
        background-color: #9E9E9E;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 3px;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: #757575;
    }
""")
help_layout.addWidget(self.adjust_help_btn)

help_layout.addStretch()
quick_action_layout.addLayout(help_layout, 2, 0, 1, 4)


# ========== 在数据表格中显示复权信息 ==========

# 修改 _load_data_table 方法，添加复权类型列
def _load_data_table(self, manager):
    """加载数据表格"""
    try:
        # 清空表格
        self.data_table.setRowCount(0)

        # 设置列数（增加复权类型列）
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels([
            "代码", "名称", "类型", "记录数", "日期范围", "复权类型", "大小"
        ])

        # ... (加载数据的逻辑)

        # 在显示每一行时，添加复权类型
        # 例如：
        # for row_data in rows:
        #     ...
        #     # 添加复权类型列
        #     adjust_item = QTableWidgetItem("支持")  # 或根据实际情况
        #     self.data_table.setItem(row, 5, adjust_item)
        #
        #     # 大小列
        #     size_mb = row_data[5] or 0
        #     size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
        #     size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        #     self.data_table.setItem(row, 6, size_item)

        print(f"📊 加载了 {len(rows)} 条数据记录")

    except Exception as e:
        self.log(f"⚠️ 加载数据表格失败: {str(e)}")
