#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽转PTrade 代码转换器 - 交互式启动器
双击 run_converter.bat 或直接运行本文件
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from converters.jq_to_ptrade_unified_v3 import JQToPtradeUnifiedConverter, StrategyType


class ConverterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("聚宽转PTrade 代码转换器")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        # 居中
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        # 标题
        title = tk.Label(self.root, text="聚宽策略 → PTrade 策略", font=("Microsoft YaHei", 16, "bold"))
        title.pack(pady=10)

        # 文件选择区
        file_frame = tk.Frame(self.root)
        file_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(file_frame, text="聚宽策略文件:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.file_path_var = tk.StringVar()
        tk.Entry(file_frame, textvariable=self.file_path_var, font=("Microsoft YaHei", 10), width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(file_frame, text="浏览...", command=self._browse_file, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)

        # 选项区
        opt_frame = tk.Frame(self.root)
        opt_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(opt_frame, text="策略类型:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="auto")
        for text, val in [("自动检测", "auto"), ("回测", "backtest"), ("实盘", "live")]:
            tk.Radiobutton(opt_frame, text=text, variable=self.type_var, value=val, font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Button(btn_frame, text="开始转换", command=self._convert, font=("Microsoft YaHei", 11, "bold"),
                  bg="#4CAF50", fg="white", width=15, height=1).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="保存结果", command=self._save, font=("Microsoft YaHei", 11),
                  width=15, height=1).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="使用说明", command=self._show_help, font=("Microsoft YaHei", 11),
                  width=15, height=1).pack(side=tk.LEFT, padx=5)

        # 结果区
        tk.Label(self.root, text="转换结果:", font=("Microsoft YaHei", 10)).pack(anchor=tk.W, padx=20)
        self.result_text = scrolledtext.ScrolledText(self.root, font=("Consolas", 10), height=15)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        self.converted_code = ""

    def _browse_file(self):
        f = filedialog.askopenfilename(
            title="选择聚宽策略文件",
            filetypes=[("Python文件", "*.py"), ("所有文件", "*.*")]
        )
        if f:
            self.file_path_var.set(f)

    def _convert(self):
        path = self.file_path_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择聚宽策略文件")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                jq_code = f.read()
        except Exception as e:
            messagebox.showerror("错误", f"读取文件失败: {e}")
            return

        if not jq_code.strip():
            messagebox.showwarning("提示", "文件内容为空，请选择包含聚宽策略代码的文件")
            return

        # 确定策略类型
        type_map = {"auto": None, "backtest": StrategyType.BACKTEST, "live": StrategyType.LIVE}
        strategy_type = type_map.get(self.type_var.get())

        # 转换
        try:
            converter = JQToPtradeUnifiedConverter(verbose=False)
            self.converted_code = converter.convert(jq_code, strategy_type=strategy_type)
        except Exception as e:
            messagebox.showerror("转换失败", str(e))
            return

        # 显示结果
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", self.converted_code)

        # 显示报告
        report = converter.get_conversion_report()
        summary = []
        if report['api_mappings']:
            summary.append("API映射: " + ", ".join(report['api_mappings']))
        if report['warnings']:
            summary.append("警告: " + "; ".join(report['warnings']))

        msg = "转换完成！"
        if summary:
            msg += "\n\n" + "\n".join(summary)

        messagebox.showinfo("完成", msg)

    def _save(self):
        if not self.converted_code:
            messagebox.showwarning("提示", "请先转换一个策略")
            return

        input_path = self.file_path_var.get().strip()
        if input_path:
            default_name = Path(input_path).stem + "_ptrade.py"
        else:
            default_name = "ptrade_strategy.py"

        save_path = filedialog.asksaveasfilename(
            title="保存PTrade策略",
            defaultextension=".py",
            initialfile=default_name,
            filetypes=[("Python文件", "*.py")]
        )

        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(self.converted_code)
                messagebox.showinfo("成功", f"已保存到:\n{save_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

    def _show_help(self):
        messagebox.showinfo("使用说明",
            "聚宽转PTrade 代码转换器\n\n"
            "使用步骤:\n"
            "1. 点击「浏览」选择你的聚宽策略 .py 文件\n"
            "2. 选择策略类型（自动检测 / 回测 / 实盘）\n"
            "3. 点击「开始转换」\n"
            "4. 点击「保存结果」保存转换后的代码\n\n"
            "注意事项:\n"
            "- 不需要安装 miniQMT 或 easy_xt\n"
            "- 转换后的代码复制到 PTrade 平台运行\n"
            "- 部分复杂 API 可能需要手动调整"
        )

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ConverterApp()
    app.run()
