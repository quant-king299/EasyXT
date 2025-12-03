#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽到Ptrade代码转换GUI组件
提供聚宽策略代码转换为Ptrade格式的可视化界面
"""

import sys
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QFileDialog, QFormLayout, QScrollArea, QTextBrowser,
    QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'code_converter'))

# 尝试导入转换器
try:
    from code_converter.converters.jq_to_ptrade import JQToPtradeConverter
    from code_converter.converters.jq_to_ptrade_monthly import JQToPtradeMonthlyConverter as JQToPtradeBacktestConverter
    from code_converter.converters.jq_to_ptrade_live import JQToPtradeLiveConverter
    from code_converter.converters.jq_to_ptrade_factors import JQToPtradeFactorsConverter
    from code_converter.converters.jq_to_ptrade_current_data import JQToPtradeCurrentDataConverter
    from code_converter.converters.jq_to_ptrade_enhanced import JQToPtradeEnhancedConverter
    CONVERTER_AVAILABLE = True
except ImportError:
    CONVERTER_AVAILABLE = False
    JQToPtradeConverter = None
    JQToPtradeBacktestConverter = None
    JQToPtradeLiveConverter = None
    JQToPtradeFactorsConverter = None
    JQToPtradeCurrentDataConverter = None
    JQToPtradeEnhancedConverter = None
    print("⚠️ 代码转换器不可用")


class PasteInputDialog(QDialog):
    """粘贴输入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("粘贴聚宽策略代码")
        self.setGeometry(200, 200, 800, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 说明标签
        info_label = QLabel("请在下方文本框中粘贴您的聚宽策略代码：")
        layout.addWidget(info_label)
        
        # 代码输入区域
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setPlaceholderText("在此粘贴您的聚宽策略代码...")
        layout.addWidget(self.code_editor)
        
        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_code_content(self):
        """获取代码内容"""
        return self.code_editor.toPlainText()


class CodeConversionWorker(QThread):
    """代码转换工作线程"""
    conversion_finished = pyqtSignal(bool, str, str)  # success, input_code, output_code
    progress_updated = pyqtSignal(int, str)  # progress, message
    
    def __init__(self, input_code: str, mapping_file: Optional[str] = None, converter_type: str = "default"):
        super().__init__()
        self.input_code = input_code
        self.mapping_file = mapping_file
        self.converter_type = converter_type
        
    def run(self):
        try:
            self.progress_updated.emit(10, "初始化转换器...")
            
            # 创建转换器
            if CONVERTER_AVAILABLE:
                if self.converter_type == "backtest" and JQToPtradeBacktestConverter:
                    converter = JQToPtradeBacktestConverter()
                    self.progress_updated.emit(50, "正在转换为回测版本...")
                elif self.converter_type == "enhanced" and JQToPtradeEnhancedConverter:
                    converter = JQToPtradeEnhancedConverter()
                    self.progress_updated.emit(50, "正在转换为增强回测版本...")
                elif self.converter_type == "live" and JQToPtradeLiveConverter:
                    converter = JQToPtradeLiveConverter()
                    self.progress_updated.emit(50, "正在转换为实盘版本...")
                elif self.converter_type == "factors" and JQToPtradeFactorsConverter:
                    converter = JQToPtradeFactorsConverter()
                    self.progress_updated.emit(50, "正在转换因子调用...")
                elif self.converter_type == "current_data" and JQToPtradeCurrentDataConverter:
                    converter = JQToPtradeCurrentDataConverter()
                    self.progress_updated.emit(50, "正在转换实时数据调用...")
                elif JQToPtradeConverter:
                    converter = JQToPtradeConverter(self.mapping_file)
                    self.progress_updated.emit(50, "正在转换代码...")
                else:
                    raise ImportError("代码转换器不可用")
                
                # 执行转换
                output_code = converter.convert(self.input_code)
                self.progress_updated.emit(90, "转换完成...")
                
                self.conversion_finished.emit(True, self.input_code, output_code)
            else:
                raise ImportError("代码转换器不可用")
        except Exception as e:
            error_msg = f"转换失败: {str(e)}"
            self.conversion_finished.emit(False, self.input_code, error_msg)


class JQToPtradeWidget(QWidget):
    """聚宽到Ptrade代码转换组件"""
    
    def __init__(self):
        super().__init__()
        self.current_input_file = ""
        self.current_output_file = ""
        self.conversion_thread = None
        self.converter_type = "default"  # default, backtest, live
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("聚宽到Ptrade代码转换器")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 版本说明标签
        self.version_info_label = QLabel("标准版本：通用转换版本，适用于大多数场景。")
        self.version_info_label.setWordWrap(True)
        self.version_info_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                border: 1px solid #2196F3;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.version_info_label)
        
        # 主要功能区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧控制面板
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 文件操作组
        file_group = QGroupBox("文件操作")
        file_layout = QFormLayout(file_group)
        
        # 输入文件
        input_file_layout = QHBoxLayout()
        self.input_file_edit = QLineEdit()
        self.input_file_edit.setPlaceholderText("请选择聚宽策略文件...")
        self.browse_input_button = QPushButton("浏览")
        self.browse_input_button.clicked.connect(self.browse_input_file)
        input_file_layout.addWidget(self.input_file_edit)
        input_file_layout.addWidget(self.browse_input_button)
        file_layout.addRow("输入文件:", input_file_layout)
        
        # 粘贴输入按钮
        self.paste_input_button = QPushButton("粘贴代码")
        self.paste_input_button.clicked.connect(self.use_paste_input)
        file_layout.addRow("", self.paste_input_button)
        
        # 输出文件
        output_file_layout = QHBoxLayout()
        self.output_file_edit = QLineEdit()
        self.output_file_edit.setPlaceholderText("请选择输出文件路径...")
        self.browse_output_button = QPushButton("浏览")
        self.browse_output_button.clicked.connect(self.browse_output_file)
        output_file_layout.addWidget(self.output_file_edit)
        output_file_layout.addWidget(self.browse_output_button)
        file_layout.addRow("输出文件:", output_file_layout)
        
        # API映射文件
        mapping_file_layout = QHBoxLayout()
        self.mapping_file_edit = QLineEdit()
        self.mapping_file_edit.setPlaceholderText("可选：自定义API映射文件...")
        self.browse_mapping_button = QPushButton("浏览")
        self.browse_mapping_button.clicked.connect(self.browse_mapping_file)
        mapping_file_layout.addWidget(self.mapping_file_edit)
        mapping_file_layout.addWidget(self.browse_mapping_button)
        file_layout.addRow("映射文件:", mapping_file_layout)
        
        control_layout.addWidget(file_group)
        
        # 转换控制组
        control_group = QGroupBox("转换控制")
        control_layout_main = QVBoxLayout(control_group)
        
        # 转换器类型选择
        converter_type_layout = QHBoxLayout()
        converter_type_label = QLabel("转换版本:")
        self.converter_type_combo = QComboBox()
        self.converter_type_combo.addItem("标准版本", "default")
        self.converter_type_combo.addItem("回测版本", "backtest")
        self.converter_type_combo.addItem("增强回测版本", "enhanced")
        self.converter_type_combo.addItem("实盘版本", "live")
        self.converter_type_combo.addItem("因子转换", "factors")
        self.converter_type_combo.addItem("实时数据转换", "current_data")
        self.converter_type_combo.setCurrentIndex(0)
        self.converter_type_combo.currentIndexChanged.connect(self.on_converter_type_changed)
        converter_type_layout.addWidget(converter_type_label)
        converter_type_layout.addWidget(self.converter_type_combo)
        control_layout_main.addLayout(converter_type_layout)
        
        # 转换按钮
        self.convert_button = QPushButton("开始转换")
        self.convert_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.convert_button.clicked.connect(self.start_conversion)
        control_layout_main.addWidget(self.convert_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout_main.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout_main.addWidget(self.status_label)
        
        control_layout.addWidget(control_group)
        
        # 示例代码组
        example_group = QGroupBox("使用示例")
        example_layout = QVBoxLayout(example_group)
        
        example_text = QTextBrowser()
        example_text.setMaximumHeight(150)
        example_text.setHtml("""
        <h3>使用说明：</h3>
        <ol>
            <li>选择聚宽策略Python文件（.py）</li>
            <li>选择转换后的输出文件路径</li>
            <li>可选择自定义API映射文件（可选）</li>
            <li>点击"开始转换"按钮</li>
            <li>等待转换完成，查看结果</li>
        </ol>
        <p><b>支持的转换：</b></p>
        <ul>
            <li>数据获取API</li>
            <li>交易API</li>
            <li>账户API</li>
            <li>系统API</li>
            <li>风险控制API</li>
            <li>定时任务API</li>
        </ul>
        """)
        example_layout.addWidget(example_text)
        
        control_layout.addWidget(example_group)
        control_layout.addStretch()
        
        # 右侧代码预览区域
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # 代码预览标签页
        self.preview_tabs = QTabWidget()
        preview_layout.addWidget(self.preview_tabs)
        
        # 输入代码预览
        self.input_code_preview = QTextEdit()
        self.input_code_preview.setReadOnly(True)
        self.input_code_preview.setFont(QFont("Consolas", 10))
        self.preview_tabs.addTab(self.input_code_preview, "输入代码（聚宽）")
        
        # 输出代码预览
        self.output_code_preview = QTextEdit()
        self.output_code_preview.setReadOnly(True)
        self.output_code_preview.setFont(QFont("Consolas", 10))
        self.preview_tabs.addTab(self.output_code_preview, "输出代码（Ptrade）")
        
        main_splitter.addWidget(control_widget)
        main_splitter.addWidget(preview_widget)
        main_splitter.setSizes([300, 700])  # 设置初始大小比例
        
        # 底部按钮区域
        bottom_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.clear_all)
        
        self.save_output_button = QPushButton("保存输出")
        self.save_output_button.clicked.connect(self.save_output)
        self.save_output_button.setEnabled(False)
        
        bottom_layout.addWidget(self.clear_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.save_output_button)
        
        layout.addLayout(bottom_layout)
        
        # 设置初始状态
        self.update_ui_state()
    
    def browse_input_file(self):
        """浏览输入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择聚宽策略文件", "", "Python文件 (*.py);;所有文件 (*)"
        )
        if file_path:
            self.input_file_edit.setText(file_path)
            self.current_input_file = file_path
            self.load_input_file()
            
            # 自动设置输出文件名
            if not self.output_file_edit.text():
                output_path = file_path.replace('.py', '_ptrade.py')
                self.output_file_edit.setText(output_path)
                self.current_output_file = output_path
    
    def use_paste_input(self):
        """使用粘贴输入"""
        # 创建一个对话框让用户粘贴代码
        paste_dialog = PasteInputDialog(self)
        if paste_dialog.exec_() == PasteInputDialog.Accepted:
            code_content = paste_dialog.get_code_content()
            if code_content:
                self.input_code_preview.setPlainText(code_content)
                self.current_input_file = ""  # 清空文件路径，表示使用粘贴输入
                self.input_file_edit.clear()
                self.status_label.setText("已加载粘贴的代码")
                self.update_ui_state()
    
    def browse_output_file(self):
        """浏览输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存转换结果", "", "Python文件 (*.py);;所有文件 (*)"
        )
        if file_path:
            self.output_file_edit.setText(file_path)
            self.current_output_file = file_path
    
    def browse_mapping_file(self):
        """浏览API映射文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择API映射文件", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        if file_path:
            self.mapping_file_edit.setText(file_path)
    
    def load_input_file(self):
        """加载输入文件内容"""
        try:
            with open(self.current_input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.input_code_preview.setPlainText(content)
                self.status_label.setText(f"已加载输入文件: {os.path.basename(self.current_input_file)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取输入文件: {str(e)}")
    
    def start_conversion(self):
        """开始转换"""
        input_code = ""
        
        # 如果有文件路径，则从文件读取
        if self.current_input_file:
            try:
                with open(self.current_input_file, 'r', encoding='utf-8') as f:
                    input_code = f.read()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取输入文件: {str(e)}")
                return
        else:
            # 否则从输入预览区域获取代码
            input_code = self.input_code_preview.toPlainText()
            if not input_code.strip():
                QMessageBox.warning(self, "警告", "请输入或粘贴聚宽策略代码")
                return
        
        # 检查转换器是否可用
        if not CONVERTER_AVAILABLE:
            QMessageBox.critical(self, "错误", "代码转换器不可用，请检查安装")
            return
        
        # 获取映射文件路径
        mapping_file = self.mapping_file_edit.text()
        if not mapping_file:
            mapping_file = None
        elif not os.path.exists(mapping_file):
            QMessageBox.warning(self, "警告", "指定的映射文件不存在，将使用默认映射")
            mapping_file = None
        
        # 获取转换器类型
        converter_type = self.converter_type_combo.currentData()
        
        # 获取转换器类型
        converter_type = self.converter_type_combo.currentData()
        
        # 禁用界面
        self.convert_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在转换...")
        
        # 启动转换线程
        self.conversion_thread = CodeConversionWorker(input_code, mapping_file, converter_type)
        self.conversion_thread.conversion_finished.connect(self.on_conversion_finished)
        self.conversion_thread.progress_updated.connect(self.on_progress_updated)
        self.conversion_thread.start()
    
    def on_progress_updated(self, progress: int, message: str):
        """进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def on_conversion_finished(self, success: bool, input_code: str, output_code: str):
        """转换完成"""
        # 恢复界面
        self.convert_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.output_code_preview.setPlainText(output_code)
            self.status_label.setText("转换完成")
            self.save_output_button.setEnabled(True)
            QMessageBox.information(self, "成功", "代码转换完成！")
        else:
            self.output_code_preview.setPlainText(output_code)
            self.status_label.setText("转换失败")
            QMessageBox.critical(self, "错误", output_code)
    
    def save_output(self):
        """保存输出文件"""
        if not self.current_output_file:
            self.browse_output_file()
            if not self.current_output_file:
                return
        
        try:
            output_content = self.output_code_preview.toPlainText()
            with open(self.current_output_file, 'w', encoding='utf-8') as f:
                f.write(output_content)
            QMessageBox.information(self, "成功", f"文件已保存到: {self.current_output_file}")
            self.status_label.setText(f"已保存: {os.path.basename(self.current_output_file)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")
    
    def clear_all(self):
        """清空所有内容"""
        self.input_file_edit.clear()
        self.output_file_edit.clear()
        self.mapping_file_edit.clear()
        self.input_code_preview.clear()
        self.output_code_preview.clear()
        self.status_label.setText("就绪")
        self.current_input_file = ""
        self.current_output_file = ""
        self.save_output_button.setEnabled(False)
    
    def on_converter_type_changed(self, index):
        """转换器类型改变"""
        converter_type = self.converter_type_combo.currentData()
        self.converter_type = converter_type
        
        # 更新版本说明
        info_text = ""
        if converter_type == "backtest":
            info_text = "回测版本：针对Ptrade回测环境优化，删除所有实盘专用API调用（如get_snapshot、set_option等），提供备选实现方案，确保代码能在回测环境中完整运行。"
        elif converter_type == "enhanced":
            info_text = "增强回测版本：修复了所有已知问题的回测版本，包括函数重复定义、缺少导入库等问题，确保生成的代码能在Ptrade回测环境中正常运行。"
        elif converter_type == "live":
            info_text = "实盘版本：充分利用Ptrade实盘环境的实时数据API，保留所有实盘专用功能（如get_snapshot、实时行情检查等），提供最佳的实盘交易体验。"
        elif converter_type == "factors":
            info_text = "因子转换：专门处理聚宽因子库调用转换，将MACD、RSI等因子调用转换为Ptrade自定义计算函数，自动生成必要的因子计算实现。"
        elif converter_type == "current_data":
            info_text = "实时数据转换：处理聚宽get_current_data()调用转换，自动生成Ptrade版本的实时数据获取函数，替代聚宽的实时数据API。"
        else:
            info_text = "标准版本：通用转换版本，适用于大多数场景。"
        
        self.version_info_label.setText(info_text)
    
    def update_ui_state(self):
        """更新UI状态"""
        has_input = bool(self.current_input_file) or bool(self.input_code_preview.toPlainText().strip())
        self.convert_button.setEnabled(has_input and CONVERTER_AVAILABLE)


# 测试代码
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    widget = JQToPtradeWidget()
    widget.show()
    sys.exit(app.exec_())