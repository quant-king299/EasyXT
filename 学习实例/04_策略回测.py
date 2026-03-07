# -*- coding: utf-8 -*-
"""
策略开发学习实例 - 回测系统（新版）

本教程使用最新的 easyxt_backtest 回测框架
展示从策略开发到回测验证的完整流程

作者: 王者quant
版本: 5.0 (基于 easyxt_backtest 框架)
更新: 2025-03-06
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("🎓 量化策略回测系统学习（基于 easyxt_backtest 框架）")
print("=" * 70)
print()

# 检查 easyxt_backtest 是否可用
try:
    from easyxt_backtest import DataManager, BacktestEngine
    from easyxt_backtest.strategies import SmallCapStrategy
    print("✅ easyxt_backtest 框架加载成功！")
    EASYXT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ easyxt_backtest 框架加载失败: {e}")
    print("💡 请确保已安装所有依赖：pip install -r requirements.txt")
    EASYXT_AVAILABLE = False


def print_section_header(num, title, description=""):
    """打印章节标题"""
    print("\n" + "=" * 70)
    print(f"第{num}课: {title}")
    if description:
        print(f"📖 {description}")
    print("=" * 70)


def wait_for_user(message="按回车键继续..."):
    """等待用户输入"""
    input(f"\n💡 {message}")


# ============================================================================
# 第1课：回测框架介绍
# ============================================================================

def lesson_1_framework_intro():
    """第1课：回测框架介绍"""
    print_section_header(1, "easyxt_backtest 回测框架介绍",
                         "了解新回测框架的核心组件")

    print("\n🏗️ 框架架构：")
    print("""
    ┌─────────────────────────────────────────────────┐
    │                  easyxt_backtest                 │
    ├─────────────────────────────────────────────────┤
    │                                                 │
    │  📊 DataManager (数据管理器)                     │
    │    ├── DuckDB (本地数据库，最快)                │
    │    ├── QMT (迅投终端数据)                       │
    │    └── Tushare (在线API)                        │
    │                                                 │
    │  🎯 BacktestEngine (回测引擎)                   │
    │    ├── 交易模拟（买入、卖出、持仓）              │
    │    ├── 绩效计算（收益率、回撤、夏普）            │
    │    └── 风险控制（止损、止盈）                   │
    │                                                 │
    │  📈 Strategy (策略基类)                          │
    │    ├── SmallCapStrategy (小市值策略)            │
    │    ├── 自定义策略...                            │
    │    └── 继承 StrategyBase 即可                   │
    │                                                 │
    │  📊 PerformanceAnalyzer (绩效分析)              │
    │    ├── 收益率计算                               │
    │    ├── 风险指标                                 │
    │    └── 绘图功能                                 │
    │                                                 │
    └─────────────────────────────────────────────────┘
    """)

    print("\n🎯 框架优势：")
    print("  ✅ 模块化设计，易于扩展")
    print("  ✅ 多数据源支持，自动切换")
    print("  ✅ 完整的绩效分析")
    print("  ✅ 灵活的策略定义")
    print("  ✅ 开箱即用的小市值策略")

    print("\n📖 使用方式：")
    print("  方式1：通过101因子平台（图形界面，推荐）")
    print("  方式2：直接调用框架（代码方式）")

    wait_for_user()


# ============================================================================
# 第2课：回测指标详解
# ============================================================================

def lesson_2_metrics_explanation():
    """第2课：回测指标详解"""
    print_section_header(2, "核心回测指标详解",
                         "理解每个指标的含义和计算方法")

    metrics = {
        "总收益率": {
            "含义": "策略在回测期间的总收益",
            "计算": "(期末净值 - 期初净值) / 期初净值",
            "评价": "正收益表明策略盈利",
            "示例": "15.92% 表示投入100万，赚了15.92万"
        },
        "年化收益率": {
            "含义": "按年化计算的收益率",
            "计算": "考虑复利效应的年化收益",
            "评价": ">15%为优秀，8-15%为良好",
            "示例": "15.92% 年化收益超过银行理财"
        },
        "最大回撤": {
            "含义": "从峰值到谷值的最大跌幅",
            "计算": "max((峰值 - 当前值) / 峰值)",
            "评价": "<10%为良好，10-20%可接受",
            "示例": "-25.33% 表示最大亏损25.33%"
        },
        "夏普比率": {
            "含义": "单位风险下的超额收益",
            "计算": "(策略收益 - 无风险收益) / 策略波动率",
            "评价": ">1为优秀，0.5-1为良好",
            "示例": "0.68 表示每承担1单位风险获得0.68单位收益"
        },
        "波动率": {
            "含义": "收益率的标准差",
            "计算": "std(日收益率) * sqrt(252)",
            "评价": "越小越好，表示策略稳定",
            "示例": "20% 表示中等波动"
        },
        "卡玛比率": {
            "含义": "单位回撤下的收益",
            "计算": "年化收益 / |最大回撤|",
            "评价": ">1为优秀，>0.5为良好",
            "示例": "0.63 表示回撤1%可获得0.63%收益"
        }
    }

    for metric_name, info in metrics.items():
        print(f"\n💎 {metric_name}")
        print(f"  • 含义：{info['含义']}")
        print(f"  • 计算：{info['计算']}")
        print(f"  • 评价：{info['评价']}")
        print(f"  • 示例：{info['示例']}")

    print("\n📊 指标评估标准：")
    print("""
    ┌──────────────┬────────┬────────┬────────┬────────┐
    │   指标        │  优秀  │  良好  │  一般  │  较差  │
    ├──────────────┼────────┼────────┼────────┼────────┤
    │ 年化收益率    │ >15%   │ 8-15%  │ 3-8%   │ <3%    │
    │ 最大回撤      │ <5%    │ 5-10%  │ 10-20% │ >20%   │
    │ 夏普比率      │ >1.0   │ 0.5-1.0│ 0.2-0.5│ <0.2   │
    │ 卡玛比率      │ >1.0   │ 0.5-1.0│ 0.3-0.5│ <0.3   │
    └──────────────┴────────┴────────┴────────┴────────┘
    """)

    wait_for_user()


# ============================================================================
# 第3课：小市值策略实战
# ============================================================================

def lesson_3_practical_demo():
    """第3课：小市值策略实战演示"""
    print_section_header(3, "小市值策略实战演示",
                         "使用 easyxt_backtest 运行完整的回测")

    if not EASYXT_AVAILABLE:
        print("\n⚠️ 框架未加载，无法运行演示")
        print("💡 请参考源代码了解使用方法")
        return

    print("\n📝 策略说明：")
    print("  • 策略名称：小市值策略")
    print("  • 选股逻辑：每月选择流通市值最小的N只股票")
    print("  • 调仓频率：每月第一个交易日")
    print("  • 权重分配：等权重配置")
    print("  • 适用市场：A股市场")

    print("\n⚙️ 回测参数：")
    start_date = "20240101"
    end_date = "20241231"
    initial_cash = 1000000
    select_num = 5
    universe_size = 500

    print(f"  • 回测时间：{start_date} ~ {end_date}")
    print(f"  • 初始资金：{initial_cash:,} 元")
    print(f"  • 选股数量：{select_num} 只")
    print(f"  • 股票池：{universe_size} 只小市值股票")

    wait_for_user("准备开始回测...")

    # 创建数据管理器
    print("\n📊 步骤1：创建数据管理器...")
    dm = DataManager()
    print("  ✅ 数据管理器创建成功")

    # 创建策略
    print("\n🎯 步骤2：创建小市值策略...")
    strategy = SmallCapStrategy(
        index_code='399101.SZ',  # 中小板综指
        select_num=select_num,
        rebalance_freq='monthly'
    )
    strategy.data_manager = dm
    print(f"  ✅ 策略创建成功（选股数：{select_num}）")

    # 创建回测引擎
    print("\n🚀 步骤3：创建回测引擎...")
    engine = BacktestEngine(
        data_manager=dm,
        initial_cash=initial_cash,
        commission=0.001  # 0.1% 佣金
    )
    print(f"  ✅ 回测引擎创建成功（初始资金：{initial_cash:,} 元）")

    # 运行回测
    print(f"\n⏱️ 步骤4：运行回测（{start_date} ~ {end_date}）...")
    print("  正在执行回测，请稍候...")

    try:
        results = engine.run_backtest(strategy, start_date, end_date)
        print("  ✅ 回测完成！")

        # 显示结果
        display_backtest_results(results, initial_cash)

    except Exception as e:
        print(f"  ❌ 回测失败：{e}")
        print("\n💡 可能的原因：")
        print("  1. 市值数据未下载（首次使用需要下载）")
        print("  2. 日期范围内无交易日")
        print("  3. 数据源连接失败")

        print("\n📥 解决方案：")
        print("  启动主GUI下载市值数据：")
        print("  cd \"C:\\Users\\Administrator\\Desktop\\miniqmt扩展\"")
        print("  python run_gui.py")
        print("  然后进入 '📥 Tushare数据下载' → '💰 市值数据'")


def display_backtest_results(results, initial_cash):
    """显示回测结果"""
    print("\n" + "=" * 70)
    print("📊 回测结果")
    print("=" * 70)

    # 核心指标
    perf = results.performance
    print(f"\n💰 收益指标：")
    print(f"  • 总收益率：{perf['total_return'] * 100:.2f}%")
    print(f"  • 年化收益率：{perf['annual_return'] * 100:.2f}%")
    print(f"  • 最终资金：{initial_cash * (1 + perf['total_return']):,.2f} 元")

    print(f"\n⚠️ 风险指标：")
    print(f"  • 最大回撤：{perf['max_drawdown'] * 100:.2f}%")
    print(f"  • 波动率：{perf['volatility'] * 100:.2f}%")
    print(f"  • 夏普比率：{perf['sharpe_ratio']:.2f}")
    print(f"  • 卡玛比率：{perf.get('calmar_ratio', 0):.2f}")

    print(f"\n📈 交易统计：")
    print(f"  • 总交易次数：{len(results.trades)} 笔")
    print(f"  • 交易天数：{len(results.returns)} 天")

    if len(results.trades) > 0:
        buy_count = len(results.trades[results.trades['direction'] == 'buy'])
        sell_count = len(results.trades[results.trades['direction'] == 'sell'])
        print(f"  • 买入次数：{buy_count} 笔")
        print(f"  • 卖出次数：{sell_count} 笔")

    # 交易记录示例
    if len(results.trades) > 0:
        print(f"\n📋 交易记录示例（前5笔）：")
        print(results.trades.head().to_string())


# ============================================================================
# 第4课：自定义策略开发
# ============================================================================

def lesson_4_custom_strategy():
    """第4课：自定义策略开发"""
    print_section_header(4, "自定义策略开发指南",
                         "学习如何开发自己的量化策略")

    print("\n📝 策略开发模板：")
    print("""
# 1. 导入基类
from easyxt_backtest.strategy_base import StrategyBase

# 2. 定义策略类
class MyCustomStrategy(StrategyBase):
    \"\"\"自定义策略模板\"\"\"

    def __init__(self, param1, param2, **kwargs):
        super().__init__(**kwargs)
        self.param1 = param1
        self.param2 = param2

    def generate_signals(self, date):
        \"\"\"
        生成交易信号

        参数:
            date: 当前日期 (YYYYMMDD)

        返回:
            list: 交易信号列表
                [{'symbol': '000001.SZ', 'action': 'buy', 'weight': 0.5},
                 {'symbol': '000002.SZ', 'action': 'sell', 'weight': 0.5}]
        \"\"\"
        signals = []

        # 获取历史数据
        symbols = self.get_universe(date)  # 获取股票池
        for symbol in symbols:
            # 获取价格数据
            data = self.data_manager.get_price_data(
                symbol,
                start_date=date,
                end_date=date,
                fields=['open', 'close', 'volume']
            )

            # 策略逻辑示例：均线金叉
            if self._check_golden_cross(symbol):
                signals.append({
                    'symbol': symbol,
                    'action': 'buy',
                    'weight': 1.0 / len(symbols)  # 等权重
                })

        return signals

    def _check_golden_cross(self, symbol):
        \"\"\"检查均线金叉\"\"\"
        # 获取历史数据
        data = self.data_manager.get_price_data(
            symbol,
            start_date='20230101',
            end_date=datetime.now().strftime('%Y%m%d'),
            fields=['close']
        )

        if data is None or len(data) < 20:
            return False

        # 计算均线
        ma5 = data['close'].rolling(5).mean()
        ma20 = data['close'].rolling(20).mean()

        # 金叉判断
        return ma5.iloc[-1] > ma20.iloc[-1] and ma5.iloc[-2] <= ma20.iloc[-2]


# 3. 使用自定义策略
from easyxt_backtest import DataManager, BacktestEngine

dm = DataManager()
strategy = MyCustomStrategy(param1=10, param2=20, data_manager=dm)
engine = BacktestEngine(data_manager=dm, initial_cash=1000000)
results = engine.run_backtest(strategy, '20240101', '20241231')
    """)

    print("\n💡 策略开发要点：")
    print("  1. 继承 StrategyBase 基类")
    print("  2. 实现 generate_signals() 方法")
    print("  3. 返回标准格式的信号列表")
    print("  4. 使用 data_manager 获取数据")
    print("  5. 注意风险控制和异常处理")

    print("\n🎯 常用策略类型：")
    print("  • 均线策略（双均线、多均线）")
    print("  • 动量策略（趋势跟踪）")
    print("  • 反转策略（均值回归）")
    print("  • 因子策略（多因子选股）")
    print("  • 择时策略（市场时机）")

    wait_for_user()


# ============================================================================
# 第5课：101因子平台使用
# ============================================================================

def lesson_5_platform_usage():
    """第5课：101因子平台使用"""
    print_section_header(5, "101因子平台使用指南",
                         "学习使用图形界面进行策略回测")

    print("\n🚀 启动101因子平台：")
    print("""
╔═══════════════════════════════════════════════════════════╗
║          方法1：使用启动脚本（推荐）⭐                   ║
╚═══════════════════════════════════════════════════════════╝

步骤：
1️⃣ 打开文件夹
   C:\\Users\\Administrator\\Desktop\\miniqmt扩展\\101因子\\101因子分析平台

2️⃣ 双击运行
   启动主应用.bat

3️⃣ 等待启动
   - 命令行窗口会显示启动信息
   - 浏览器会自动打开

═══════════════════════════════════════════════════════════

╔═══════════════════════════════════════════════════════════╗
║          方法2：命令行启动                               ║
╚═══════════════════════════════════════════════════════════╝

# Windows 命令行
cd "C:\\Users\\Administrator\\Desktop\\miniqmt扩展\\101因子\\101因子分析平台"
python main_app.py

# 或使用 Git Bash
cd /c/Users/Administrator/Desktop/miniqmt扩展/101因子/101因子分析平台
python main_app.py
    """)

    print("\n🌐 浏览器访问：")
    print("""
   自动打开地址：http://127.0.0.1:8510

   如果没有自动打开，手动在浏览器输入：
   http://127.0.0.1:8510
    """)

    print("\n📊 界面布局说明：")
    print("""
┌────────────────────────────────────────────────────────┐
│  🎯 策略回测 - 101因子分析平台                         │
├──────────┬─────────────────────────────────────────────┤
│          │                                              │
│ 📂导航   │         回测配置和结果展示区                │
│          │                                              │
│ • 主页   │   ┌──────────────────────────────────┐      │
│ • 策略   │   │ 📅 回测时间                      │      │
│   回测   │   │ • 开始日期: [2024-01-01]         │      │
│ • 因子   │   │ • 结束日期: [2024-12-31]         │      │
│   工作流 │   └──────────────────────────────────┘      │
│ • 因子   │                                              │
│   分析   │   ┌──────────────────────────────────┐      │
│          │   │ 📊 策略参数                      │      │
│          │   │ • 选股数量: [5只]               │      │
│          │   │ • 股票池: [500只]               │      │
│          │   └──────────────────────────────────┘      │
│          │                                              │
│          │   ┌──────────────────────────────────┐      │
│          │   │ 💰 资金设置                      │      │
│          │   │ • 初始资金: [1000000元]          │      │
│          │   └──────────────────────────────────┘      │
│          │                                              │
│          │   [  🚀 开始回测  ]                         │
│          │                                              │
└──────────┴─────────────────────────────────────────────┘
    """)

    print("\n📝 详细操作步骤：")
    print("""
═══════════════════════════════════════════════════════════

第1步：找到策略回测页面
───────────────────────────────────
• 在左侧导航栏找到 "🎯 策略回测"
• 点击进入策略回测页面

═══════════════════════════════════════════════════════════

第2步：配置回测参数
───────────────────────────────────

📅 回测时间：
  • 开始日期：点击日期选择器，选择 2024-01-01
  • 结束日期：点击日期选择器，选择 2024-12-31
  💡 建议：首次回测选择较短时间（如3个月）

📊 策略参数：
  • 选股数量：拖动滑块，选择 5（每次持仓5只股票）
  • 股票池大小：拖动滑块，选择 500（从500只小市值中选）
  💡 说明：股票池越大，选股范围越广，但速度越慢

💰 资金设置：
  • 初始资金：输入 1000000（100万）
  💡 可以设置为任意金额，不影响收益率

═══════════════════════════════════════════════════════════

第3步：开始回测
───────────────────────────────────
• 点击 "🚀 开始回测" 按钮
• 等待回测完成（首次可能需要1-3分钟）
• 界面会显示实时进度

═══════════════════════════════════════════════════════════

第4步：查看结果
───────────────────────────────────
回测完成后，会显示5个标签页：

📊 性能指标
  • 总收益率、年化收益率
  • 最大回撤、夏普比率
  • 资金情况、风险指标

📈 净值曲线
  • 策略累计净值走势图
  • 可视化展示收益情况

📉 回撤分析
  • 回撤曲线图
  • 显示最大回撤区间

📋 交易记录
  • 每一笔买卖的详细记录
  • 包括日期、股票、价格、数量

📄 详细报告
  • JSON格式的完整数据
  • 可以复制保存

═══════════════════════════════════════════════════════════
    """)

    print("\n💡 平台优势：")
    print("""
  ✅ 图形界面，操作简单
     • 无需编程知识
     • 点击即可运行
     • 可视化配置参数

  ✅ 实时显示，即时反馈
     • 进度条显示执行状态
     • 错误信息清晰提示
     • 无需等待命令行输出

  ✅ 可视化图表，直观清晰
     • 交互式图表展示
     • 多维度数据分析
     - 美观的界面设计

  ✅ 无需编程，开箱即用
     • 内置小市值策略
     • 一键运行回测
     • 快速验证想法
    """)

    print("\n⚠️ 首次使用注意事项：")
    print("""
1. 数据准备
   • 首次使用需要下载市值数据
   • 或选择"继续回测"使用在线API（速度较慢）

2. 时间选择
   • 建议首次回测选择3-6个月
   • 避免选择过长时间范围

3. 参数调整
   • 可以随时修改参数
   • 修改后重新点击"开始回测"即可

4. 结果保存
   • 可以截图保存图表
   • 可以复制JSON数据
    """)

    print("\n🎯 快速测试建议：")
    print("""
如果你想快速测试平台，建议使用以下参数：

  • 开始日期：2024-01-01
  • 结束日期：2024-03-31
  • 选股数量：3只
  • 股票池大小：100只
  • 初始资金：100000元

这样可以在1分钟内完成回测！
    """)

    wait_for_user()


# ============================================================================
# 第6课：数据准备
# ============================================================================

def lesson_6_data_preparation():
    """第6课：数据准备指南"""
    print_section_header(6, "数据准备指南",
                         "了解如何下载和准备回测数据")

    print("\n📥 数据下载方法：")

    print("\n方法1：通过主GUI下载（推荐）⭐")
    print("""
# 1. 启动主GUI
cd "C:\\Users\\Administrator\\Desktop\\miniqmt扩展"
python run_gui.py

# 2. 进入下载页面
点击 "📥 Tushare数据下载" → "💰 市值数据"

# 3. 配置下载参数
Token会自动读取（从 .env 文件）
点击 "2024年全年" 快速按钮

# 4. 开始下载
点击 "🚀 开始下载全A股市值数据"
等待 5-10 分钟完成

# 5. 验证数据
下载完成后会显示数据统计信息
    """)

    print("\n方法2：在线API（无需下载）")
    print("""
如果没有本地数据，系统会自动：
1. 尝试使用 Tushare API 在线获取
2. 速度较慢，但可以使用
3. 需要配置 TUSHARE_TOKEN
    """)

    print("\n📊 数据源优先级：")
    print("""
1. ⭐ DuckDB（本地数据库）
   • 速度最快（秒级响应）
   • 需要先下载
   • 推荐用于多次回测

2. ⚡ Tushare（在线API）
   • 数据准确
   • 速度较慢
   • 适合测试使用

3. ⚠️ QMT（迅投终端）
   • 本地数据
   • 需要启动QMT
   • 可能不准确
    """)

    print("\n💡 数据检查：")
    print("""
# 检查市值数据是否完整
from easyxt_backtest import DataManager

dm = DataManager()
# 系统会自动检查数据完整性
# 如果不完整会提示下载
    """)

    wait_for_user()


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主学习流程"""
    print("\n🎯 学习路径：")
    print("  1️⃣ 框架介绍 - 了解回测系统架构")
    print("  2️⃣ 指标详解 - 理解关键回测指标")
    print("  3️⃣ 实战演示 - 运行完整回测示例")
    print("  4️⃣ 策略开发 - 学习自定义策略")
    print("  5️⃣ 平台使用 - 掌握图形界面操作")
    print("  6️⃣ 数据准备 - 下载和配置数据源")

    wait_for_user("准备开始学习？")

    # 运行各课程
    lesson_1_framework_intro()
    lesson_2_metrics_explanation()

    if EASYXT_AVAILABLE:
        lesson_3_practical_demo()
    else:
        print("\n⚠️ 框架未加载，跳过实战演示")

    lesson_4_custom_strategy()
    lesson_5_platform_usage()
    lesson_6_data_preparation()

    # 总结
    print("\n" + "=" * 70)
    print("🎉 学习完成！")
    print("=" * 70)

    print("\n✅ 你已经掌握：")
    print("  • easyxt_backtest 框架的使用")
    print("  • 核心回测指标的含义")
    print("  • 小市值策略的回测流程")
    print("  • 自定义策略的开发方法")
    print("  • 101因子平台的操作")
    print("  • 数据准备和配置")

    print("\n🚀 下一步建议：")
    print("  1. 运行完整回测：")
    print("     cd \"101因子/101因子分析平台\"")
    print("     python main_app.py")
    print("\n  2. 查看详细文档：")
    print("     - 快速入门-3步开始回测.md")
    print("     - 策略回测使用指南-清晰版.md")
    print("\n  3. 开发自己的策略：")
    print("     参考 easyxt_backtest/examples/")
    print("     继承 StrategyBase 基类")

    print("\n📚 相关资源：")
    print("  • 101因子平台：101因子/101因子分析平台/")
    print("  • 回测框架：easyxt_backtest/")
    print("  • 策略示例：easyxt_backtest/examples/")

    print("\n💡 记住：")
    print("  回测是策略验证的第一步，但不是最后一步。")
    print("  真正的考验在实盘交易中！")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
