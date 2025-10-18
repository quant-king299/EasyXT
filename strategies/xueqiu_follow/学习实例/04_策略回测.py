# -*- coding: utf-8 -*-
"""
策略开发学习实例 - 回测系统专版
本文件专注于回测系统的学习和使用
高级多因子策略演示已移至05_实盘策略开发.py

作者: CodeBuddy
版本: 4.0 (回测系统专版)
"""

import sys
import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easy_xt.api import EasyXT

# Backtrader相关导入
try:
    import backtrader as bt
    import backtrader.analyzers as btanalyzers
    import backtrader.feeds as btfeeds
    import backtrader.indicators as btind
    BACKTRADER_AVAILABLE = True
    print("✅ Backtrader库已导入")
except ImportError:
    BACKTRADER_AVAILABLE = False
    print("⚠️ Backtrader库未安装，请运行: pip install backtrader")

def print_section_header(lesson_num, title, description):
    """打印课程标题"""
    print("\n" + "=" * 70)
    print(f"第{lesson_num}课: {title}")
    print("=" * 70)
    print(f"📖 学习目标: {description}")
    print("-" * 70)

def wait_for_user_input(message="按回车键继续..."):
    """等待用户输入"""
    input(f"\n💡 {message}")

def display_backtest_interface_info():
    """显示回测界面信息（基于提供的图片）"""
    print("\n🖼️ EasyXT回测系统界面详解：")
    print("=" * 60)
    
    print("📊 【左侧参数配置区】")
    print("┌─ 回测参数设置 ─────────────────────┐")
    print("│ 股票代码: 000001.SZ (平安银行)      │")
    print("│ 开始日期: 2024/9/21 星期六          │")
    print("│ 结束日期: 2025/9/21 星期日          │")
    print("│ 初始资金: 1000000.00 元            │")
    print("│ 手续费率: 0.0001%                  │")
    print("│ ✅ QMT连接 (自动连接)              │")
    print("└────────────────────────────────────┘")
    
    print("\n📈 【策略参数配置】")
    print("┌─ 双均线策略 ───────────────────────┐")
    print("│ 短期均线: 5  (日均线)              │")
    print("│ 长期均线: 20 (日均线)              │")
    print("│ RSI周期:  14 (日)                  │")
    print("└────────────────────────────────────┘")
    
    print("\n⚙️ 【高级选项】")
    print("☑️ 启用参数优化")
    print("☑️ 基准比较")
    print("☑️ 详细回测分析")
    
    print("\n🎛️ 【操作按钮】")
    print("🟢 开始回测  📊 导出回测  📋 导出HTML报告")
    
    print("\n📊 【右侧结果展示区】")
    print("┌─ 回测结果分析 ─────────────────────┐")
    print("│                                    │")
    print("│  💚 总收益率     💙 年化收益率      │")
    print("│    4.7713%        5.1476%         │")
    print("│                                    │")
    print("│  🟡 夏普比率     🔴 最大回撤       │")
    print("│    0.253          7.1999%         │")
    print("│                                    │")
    print("└────────────────────────────────────┘")
    
    print("\n📈 【投资组合净值曲线】")
    print("图表显示：")
    print("• 蓝色实线：策略净值曲线 (从0.95上升至1.10)")
    print("• 红色虚线：基准线 (1.0基准)")
    print("• 时间轴：09-08 至 07-31")
    print("• 特征：前期调整，后期显著上涨")

def demo_backtest_system():
    """演示回测系统 - 从回测到实盘的完整流程"""
    print("\n" + "=" * 80)
    print("📊 量化策略回测系统演示")
    print("=" * 80)
    print("本课程展示从策略回测到实盘部署的完整流程")
    print("🎯 学习目标：掌握专业的量化回测方法和工具")
    
    print("\n📋 回测系统核心功能：")
    print("  • 📊 策略参数配置与优化")
    print("  • 📈 历史数据回测验证")
    print("  • 📉 风险指标分析")
    print("  • 💰 收益曲线展示")
    print("  • 📋 详细回测报告")
    
    wait_for_user_input("准备开始回测系统学习？")
    
    print_section_header(1, "回测系统界面介绍", "了解专业回测工具的使用方法")
    
    # 显示回测界面详细信息
    display_backtest_interface_info()
    
    wait_for_user_input("界面介绍完成！按回车键继续...")
    
    print_section_header(2, "回测结果分析", "解读专业回测报告的关键指标")
    
    print("📊 核心回测指标解析：")
    print("=" * 50)
    
    print("💚 总收益率：4.7713%")
    print("  • 含义：策略在回测期间的总收益")
    print("  • 计算：(期末净值 - 期初净值) / 期初净值")
    print("  • 评价：正收益表明策略有效性")
    print("  • 实际表现：在一年期间获得4.77%的正收益")
    
    print("\n💙 年化收益率：5.1476%")
    print("  • 含义：策略年化后的收益水平")
    print("  • 计算：考虑复利效应的年化收益")
    print("  • 评价：与无风险收益率(约3%)对比，有一定优势")
    print("  • 实际表现：年化收益超过银行定期存款")
    
    print("\n🟡 夏普比率：0.253")
    print("  • 含义：单位风险下的超额收益")
    print("  • 计算：(策略收益 - 无风险收益) / 策略波动率")
    print("  • 评价：>1为优秀，>0.5为良好，0.253为一般")
    print("  • 改进方向：可通过降低波动率或提高收益来优化")
    
    print("\n🔴 最大回撤：7.1999%")
    print("  • 含义：策略净值的最大跌幅")
    print("  • 计算：从峰值到谷值的最大跌幅")
    print("  • 评价：<10%为良好，7.2%属于可接受范围")
    print("  • 风险控制：需要关注回撤控制机制")
    
    wait_for_user_input("指标解析完成！按回车键继续...")
    
    print_section_header(3, "净值曲线分析", "理解策略表现的可视化展示")
    
    print("📈 投资组合净值曲线分析：")
    print("=" * 50)
    print("🔵 蓝色实线 - 策略净值曲线：")
    print("  • 显示策略净值的历史走势")
    print("  • 反映策略的收益波动特征")
    print("  • 可观察策略的稳定性和风险")
    
    print("\n🔴 红色虚线 - 基准线：")
    print("  • 通常为1.0基准线或市场指数")
    print("  • 用于对比策略相对表现")
    print("  • 评估策略的超额收益能力")
    
    print("\n📊 曲线特征分析：")
    print("  • 时间范围：09-08至07-31期间表现")
    print("  • 前期阶段：策略经历调整期（0.95-1.0区间）")
    print("  • 中期阶段：策略表现平稳（小幅波动）")
    print("  • 后期阶段：策略显著上涨（突破1.05）")
    print("  • 整体趋势：呈现上升趋势，符合预期")
    print("  • 波动特征：存在一定回撤，但整体向上")
    
    wait_for_user_input("净值分析完成！按回车键继续...")
    
    print_section_header(4, "回测系统操作流程", "掌握完整的回测操作步骤")
    
    print("🔧 标准回测操作流程：")
    print("=" * 50)
    
    print("1️⃣ 策略准备阶段：")
    print("  • 确定策略逻辑和参数")
    print("  • 选择回测标的和时间范围")
    print("  • 设置初始资金和交易成本")
    print("  • 准备策略代码和配置文件")
    
    print("\n2️⃣ 参数配置阶段：")
    print("  • 输入股票代码（支持模糊搜索）")
    print("  • 设置回测时间区间（建议1-3年）")
    print("  • 配置策略参数（均线周期、RSI等）")
    print("  • 选择高级选项（参数优化、基准对比）")
    
    print("\n3️⃣ 回测执行阶段：")
    print("  • 点击'开始回测'按钮")
    print("  • 系统自动下载历史数据")
    print("  • 执行策略逻辑计算")
    print("  • 生成回测结果和图表")
    
    print("\n4️⃣ 结果分析阶段：")
    print("  • 查看核心指标（收益率、夏普比率、回撤）")
    print("  • 分析净值曲线走势")
    print("  • 导出详细HTML报告")
    print("  • 评估策略可行性")
    
    print("\n5️⃣ 策略优化阶段：")
    print("  • 根据回测结果调整参数")
    print("  • 进行参数敏感性分析")
    print("  • 多周期验证策略稳定性")
    print("  • 准备实盘部署")
    
    wait_for_user_input("操作流程学习完成！按回车键继续...")
    
    print_section_header(5, "从回测到实盘", "理解实盘部署的关键要素")
    
    print("🚀 实盘部署关键步骤：")
    print("=" * 50)
    
    print("📋 实盘前检查清单：")
    print("  ✅ 回测结果稳定且符合预期")
    print("  ✅ 多周期验证策略有效性")
    print("  ✅ 风险控制机制完善")
    print("  ✅ 交易执行逻辑正确")
    print("  ✅ 异常处理机制健全")
    
    print("\n🔧 技术准备要素：")
    print("  • 实时数据接口稳定连接")
    print("  • 交易接口权限和配置")
    print("  • 监控和报警系统")
    print("  • 日志记录和分析系统")
    print("  • 资金管理和风控系统")
    
    print("\n⚠️ 风险控制要点：")
    print("  • 设置合理的止损止盈")
    print("  • 控制单笔交易仓位")
    print("  • 监控策略运行状态")
    print("  • 建立应急处理机制")
    print("  • 定期评估策略表现")
    
    # 尝试调用回测组件（如果可用）
    try:
        print("\n🚀 启动回测系统演示...")
        print("正在加载回测组件...")
        
        # 检查是否有回测组件可用
        try:
            from gui_app.backtest import backtest_widget
            print("✅ 回测组件加载成功")
            print("💡 提示：您可以通过以下方式启动完整回测界面：")
            print("   python -m gui_app.backtest.backtest_widget")
            print("   或者运行：python gui_app/backtest/backtest_widget.py")
        except ImportError:
            print("⚠️ 回测组件未找到，请确保gui_app模块已正确安装")
            print("💡 您可以手动启动回测界面进行实际操作")
            
    except Exception as e:
        print(f"⚠️ 回测组件加载失败: {e}")
    
    print("\n📚 回测系统学习要点总结：")
    print("=" * 50)
    print("✅ 掌握了回测系统的界面和功能")
    print("✅ 理解了关键回测指标的含义")
    print("✅ 学会了净值曲线的分析方法")
    print("✅ 熟悉了完整的回测操作流程")
    print("✅ 了解了从回测到实盘的路径")
    print("✅ 掌握了实盘部署的关键要素")
    
    wait_for_user_input("回测系统学习完成！")

def main():
    """主函数 - 回测系统专版学习流程"""
    print("🎓 欢迎来到量化策略开发学习实例！(回测系统专版)")
    print("📚 本教程专注于回测系统的学习和使用")
    print("💡 内容包含：回测系统界面 → 指标分析 → 操作流程 → 实盘准备")
    
    print("\n🎯 学习路径：")
    print("  1️⃣ 回测系统：掌握专业回测工具和方法")
    print("  2️⃣ 指标分析：理解关键回测指标含义")
    print("  3️⃣ 操作流程：熟悉完整回测操作步骤")
    print("  4️⃣ 实盘准备：了解从回测到实盘的路径")
    
    wait_for_user_input("准备开始回测系统学习之旅？")
    
    print_section_header(1, "真实数据的重要性", "理解为什么要使用真实数据进行策略开发")
    print("📖 真实数据 vs 模拟数据：")
    print("🔍 真实数据优势：")
    print("  • 反映真实市场波动特征")
    print("  • 包含实际的市场异常和突发事件")
    print("  • 更准确的回测结果")
    print("  • 更可靠的策略验证")
    
    print("\n⚠️ 模拟数据局限性：")
    print("  • 过于理想化，缺乏市场噪音")
    print("  • 无法反映真实的流动性问题")
    print("  • 可能导致过度拟合")
    print("  • 实盘表现与回测差异较大")
    
    wait_for_user_input("数据重要性学习完成！按回车键继续...")
    
    print_section_header(2, "多数据源策略", "了解如何获取和处理真实市场数据")
    print("🔧 数据获取策略：")
    print("  • 主要数据源：EasyXT API")
    print("  • 备用数据源：xtquant、qstock、akshare")
    print("  • 容错机制：高质量示例数据")
    print("  • 数据验证：格式检查、异常处理")
    print("  • 数据清洗：去除异常值、填补缺失")
    
    wait_for_user_input("数据获取策略学习完成！按回车键继续...")
    
    print_section_header(3, "回测与实盘的关系", "理解回测在量化策略开发中的作用")
    print("🔗 回测与实盘的关系：")
    print("  • 📊 回测是策略验证的第一步")
    print("  • 🔧 回测帮助发现策略的潜在问题")
    print("  • 📈 回测提供策略优化的方向")
    print("  • 🚀 回测为实盘部署提供信心")
    
    print("\n💡 下一步学习建议：")
    print("  • 完成回测系统学习后")
    print("  • 可以继续学习05_实盘策略开发.py")
    print("  • 那里有完整的实盘策略开发流程")
    print("  • 包含高级多因子策略的详细实现")
    
    wait_for_user_input("理论学习完成！按回车键开始回测系统演示...")

if __name__ == "__main__":
    # 运行基础教程
    main()
    
    # 运行回测系统演示
    print("\n" + "🎓" * 20)
    print("准备进入回测系统学习...")
    input("按回车键开始回测系统演示...")
    
    demo_backtest_system()
    
    print("\n" + "=" * 80)
    print("🎉 回测系统学习完成！")
    print("📚 您已掌握专业回测系统的使用方法")
    print("🚀 下一步：学习05_实盘策略开发.py")
    print("💡 那里有完整的实盘策略开发流程和高级多因子策略演示")
    print("🎯 建议：先充分理解回测，再进行实盘策略开发")
    print("=" * 80)