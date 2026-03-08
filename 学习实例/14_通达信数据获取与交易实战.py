"""
股票量化交易学习案例 - EasyXT与通达信完美结合
使用通达信量化数据接口 + EasyXT交易执行

功能包括：
1. 通达信行情数据获取（K线、实时行情）
2. 通达信财务数据获取（需购买专业财务数据权限）
3. EasyXT交易信号生成
4. EasyXT订单执行
5. 完整的风控系统
6. 策略回测验证
7. 【新增】通达信跟踪预警 + 全自动交易

作者：王者quant
日期：2025-01-30
更新：2025-02-03（新增示例5：跟踪预警自动交易）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ==================== 加载配置 ====================
try:
    from easy_xt.config import config

    # 获取QMT userdata路径（自动从配置文件加载）
    QMT_PATH = config.get_userdata_path()

    # 获取账户ID（从配置文件）
    ACCOUNT_ID = config.get('settings.account.account_id', default='39020958')

    # 获取风控参数
    MAX_POSITION_RATIO = config.get('settings.risk.max_total_exposure', default=0.8)
    STOP_LOSS_RATIO = config.get('settings.risk.stop_loss_ratio', default=0.05)

    # 如果没有自动检测到QMT路径，尝试手动设置
    if not QMT_PATH:
        qmt_path_from_config = config.get('settings.account.qmt_path')
        if qmt_path_from_config:
            config.set_qmt_path(qmt_path_from_config)
            QMT_PATH = config.get_userdata_path()

    print(f"[OK] 成功加载配置文件")
    print(f"  QMT userdata路径: {QMT_PATH}")
    print(f"  账户ID: {ACCOUNT_ID}")
    print(f"  最大仓位比例: {MAX_POSITION_RATIO}")
    print(f"  止损比例: {STOP_LOSS_RATIO}")
    print()

except Exception as e:
    # 备用配置
    print(f"[WARN] 配置文件加载失败，使用默认配置: {e}")

    QMT_PATH = r'D:\国金QMT交易端模拟\userdata_mini'
    ACCOUNT_ID = '39020958'
    MAX_POSITION_RATIO = 0.8
    STOP_LOSS_RATIO = 0.05

STOCK_POOL = {
    '核心蓝筹': ['605168.SH', '000333.SZ', '600519.SH'],
    '成长股': ['300059.SZ', '300015.SZ', '002475.SZ'],
    '科技股': ['000063.SZ', '002230.SZ', '600036.SH'],
}


# ==================== 类定义 ====================

class TdxEasyXTSystem:
    """通达信数据 + EasyXT交易系统"""

    def __init__(self):
        """初始化系统"""
        print("[OK] 初始化通达信+EasyXT交易系统...")

        # 初始化数据模块
        self.init_tdx_data()

        # 初始化交易模块
        self.init_easyxt_trading()

        # 数据缓存
        self.data_cache = {}
        self.signal_history = []

        print("[OK] 系统初始化完成\n")

    def init_tdx_data(self):
        """初始化通达信数据模块"""
        print("[DATA] 初始化通达信数据模块...")

        try:
            from easy_xt.tdx_client import TdxClient

            # 测试连接
            with TdxClient() as client:
                test_df = client.get_market_data(
                    stock_list=['605168.SH'],
                    start_time='20250101',
                    period='1d',
                    count=5
                )

                if not test_df.empty:
                    print(f"[OK] 通达信数据连接成功")
                    print(f"  测试数据: {len(test_df)} 条记录")
                else:
                    print("[WARN]  通达信数据连接为空")

            self.tdx_available = True

        except Exception as e:
            print(f"[ERROR] 通达信数据模块初始化失败: {e}")
            print("[TIP] 请检查:")
            print("  1. 通达信是否已安装")
            print("  2. PYPlugins/user路径是否正确")
            self.tdx_available = False

    def init_easyxt_trading(self):
        """初始化EasyXT交易模块"""
        print("[TRADE] 初始化EasyXT交易模块...")

        try:
            from easy_xt.api import EasyXT

            # 1. 创建EasyXT实例（无参数）
            self.trader = EasyXT()

            # 2. 初始化交易服务（传入QMT路径）
            success = self.trader.init_trade(
                userdata_path=QMT_PATH,
                session_id=ACCOUNT_ID
            )

            if not success:
                raise Exception("交易服务初始化失败")

            # 3. 添加账户
            self.trader.add_account(ACCOUNT_ID)

            print("[OK] EasyXT交易模块初始化成功")
            self.trading_available = True

        except Exception as e:
            print(f"[ERROR] EasyXT交易模块初始化失败: {e}")
            print("[TIP] 请检查:")
            print("  1. QMT是否已启动")
            print("  2. 配置文件中的qmt_path是否正确")
            self.trading_available = False

    # ==================== 通达信数据获取 ====================

    def get_market_data(self, stock_list, start_time, end_time="", period='1d'):
        """
        获取通达信行情数据

        Args:
            stock_list: 股票代码列表，如 ['605168.SH', '000333.SZ']
            start_time: 开始时间，格式 '20250101'
            end_time: 结束时间，格式 '20250131'
            period: 周期 '1d'=日线 '1wk'=周线 '1min'=分钟

        Returns:
            pd.DataFrame: 行情数据
        """
        if not self.tdx_available:
            print("[ERROR] 通达信数据模块不可用")
            return pd.DataFrame()

        try:
            from easy_xt.tdx_client import TdxClient

            with TdxClient() as client:
                df = client.get_market_data(
                    stock_list=stock_list,
                    start_time=start_time,
                    end_time=end_time,
                    period=period,
                    dividend_type='front'  # 前复权
                )

                return df

        except Exception as e:
            print(f"[ERROR] 获取行情数据失败: {e}")
            return pd.DataFrame()

    def get_financial_data(self, stock_list, field_list, start_time=None, end_time=None):
        """
        获取通达信财务数据
        [WARN] 注意：需要购买通达信专业财务数据权限才能使用

        Args:
            stock_list: 股票代码列表
            field_list: 财务指标字段，如 ['净资产收益率', '市盈率', '营业总收入']
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            pd.DataFrame: 财务数据
        """
        if not self.tdx_available:
            print("[ERROR] 通达信数据模块不可用")
            return pd.DataFrame()

        print("[WARN]  获取财务数据需要通达信专业财务数据权限")
        print("[TIP] 如需使用财务数据，请在通达信中购买专业财务数据功能")

        try:
            from easy_xt.tdx_client import TdxClient

            with TdxClient() as client:
                df = client.get_financial_data(
                    stock_list=stock_list,
                    field_list=field_list,
                    start_time=start_time,
                    end_time=end_time,
                    report_type='report_time'
                )

                return df

        except Exception as e:
            error_msg = str(e)
            if '权限' in error_msg or '授权' in error_msg:
                print("[ERROR] 没有财务数据权限")
                print("[TIP] 解决方案:")
                print("   1. 在通达信中购买专业财务数据权限")
                print("   2. 或使用其他免费财务数据源（如akshare）")
            else:
                print(f"[ERROR] 获取财务数据失败: {e}")

            return pd.DataFrame()

    # ==================== 技术指标计算 ====================

    def calculate_indicators(self, df):
        """
        计算技术指标

        Args:
            df: 行情数据DataFrame

        Returns:
            pd.DataFrame: 带技术指标的数据
        """
        data = df.copy()

        # 移动平均线
        data['MA5'] = data['close'].rolling(window=5).mean()
        data['MA10'] = data['close'].rolling(window=10).mean()
        data['MA20'] = data['close'].rolling(window=20).mean()
        data['MA60'] = data['close'].rolling(window=60).mean()

        # MACD
        exp12 = data['close'].ewm(span=12, adjust=False).mean()
        exp26 = data['close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp12 - exp26
        data['MACD_SIGNAL'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_HIST'] = data['MACD'] - data['MACD_SIGNAL']

        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        data['RSI'] = 100 - (100 / (1 + gain / loss))

        # 布林带
        data['BB_MIDDLE'] = data['close'].rolling(window=20).mean()
        bb_std = data['close'].rolling(window=20).std()
        data['BB_UPPER'] = data['BB_MIDDLE'] + (bb_std * 2)
        data['BB_LOWER'] = data['BB_MIDDLE'] - (bb_std * 2)

        # 成交量均线
        data['VOL_MA5'] = data['volume'].rolling(window=5).mean()
        data['VOL_MA10'] = data['volume'].rolling(window=10).mean()

        return data

    # ==================== 交易信号生成 ====================

    def generate_signal(self, symbol, data):
        """
        生成交易信号

        Args:
            symbol: 股票代码
            data: 带技术指标的数据

        Returns:
            dict: 交易信号
        """
        if len(data) < 20:
            return None

        latest = data.iloc[-1]
        prev = data.iloc[-2]

        signals = []

        # 信号1: MA金叉/死叉
        if latest['MA5'] > latest['MA20'] and prev['MA5'] <= prev['MA20']:
            signals.append(('MA金叉', 0.3))
        elif latest['MA5'] < latest['MA20'] and prev['MA5'] >= prev['MA20']:
            signals.append(('MA死叉', -0.3))

        # 信号2: MACD金叉/死叉
        if latest['MACD'] > latest['MACD_SIGNAL'] and prev['MACD'] <= prev['MACD_SIGNAL']:
            signals.append(('MACD金叉', 0.25))
        elif latest['MACD'] < latest['MACD_SIGNAL'] and prev['MACD'] >= prev['MACD_SIGNAL']:
            signals.append(('MACD死叉', -0.25))

        # 信号3: RSI超买超卖
        if latest['RSI'] < 30:
            signals.append(('RSI超卖', 0.2))
        elif latest['RSI'] > 70:
            signals.append(('RSI超买', -0.2))

        # 信号4: 价格突破布林带
        if latest['close'] < latest['BB_LOWER']:
            signals.append(('跌破布林下轨', 0.15))
        elif latest['close'] > latest['BB_UPPER']:
            signals.append(('突破布林上轨', -0.15))

        # 计算综合信号强度
        strength = sum(s[1] for s in signals) if signals else 0

        # 判断信号类型
        signal_type = 'HOLD'
        if strength > 0.3:
            signal_type = 'BUY'
        elif strength < -0.3:
            signal_type = 'SELL'

        # 计算置信度
        confidence = min(95, max(5, 50 + abs(strength) * 40))

        return {
            'symbol': symbol,
            'signal_type': signal_type,
            'strength': strength,
            'confidence': confidence,
            'reasons': [s[0] for s in signals],
            'price': latest['close'],
            'time': datetime.now()
        }

    # ==================== 交易执行 ====================

    def execute_trade(self, signal):
        """
        执行交易

        Args:
            signal: 交易信号

        Returns:
            dict: 执行结果
        """
        if not self.trading_available:
            print("[ERROR] 交易模块不可用")
            return {'status': 'failed', 'message': '交易模块不可用'}

        if signal['signal_type'] == 'HOLD':
            return {'status': 'skipped', 'message': '无交易信号'}

        # 获取账户信息
        try:
            account = self.trader.get_account_asset(ACCOUNT_ID)

            print(f"\n[TRADE] 账户信息:")
            print(f"  总资产: {account.get('total_asset', 0):,.2f}")
            print(f"  可用资金: {account.get('cash', 0):,.2f}")
            print(f"  持仓市值: {account.get('market_value', 0):,.2f}")

        except Exception as e:
            print(f"[ERROR] 获取账户信息失败: {e}")
            return {'status': 'failed', 'message': '获取账户信息失败'}

        # 执行买入
        if signal['signal_type'] == 'BUY':
            return self._execute_buy(signal)

        # 执行卖出
        elif signal['signal_type'] == 'SELL':
            return self._execute_sell(signal)

    def _execute_buy(self, signal):
        """执行买入"""
        cash = self.trader.get_account_asset(ACCOUNT_ID).get('cash', 0)

        # 计算买入数量（使用30%资金）
        trade_amount = cash * 0.3
        price = signal['price']
        quantity = int(trade_amount / price) // 100 * 100

        if quantity < 100:
            return {'status': 'skipped', 'message': '资金不足'}

        print(f"\n[UP] 买入信号: {signal['symbol']}")
        print(f"  信号强度: {signal['strength']:.2f}")
        print(f"  置信度: {signal['confidence']:.1f}%")
        print(f"  信号原因: {', '.join(signal['reasons'])}")
        print(f"  买入数量: {quantity} 股")
        print(f"  买入价格: {price:.2f}")

        # 实际交易（注释掉，避免误操作）
        # result = self.trader.order_stock(
        #     account_id=ACCOUNT_ID,
        #     stock_code=signal['symbol'],
        #     order_type='buy',
        #     order_volume=quantity,
        #     price_type='limit',
        #     price=price
        # )

        # print(f"[OK] 买入订单已提交")

        return {'status': 'success', 'message': f'模拟买入 {quantity} 股'}

    def _execute_sell(self, signal):
        """执行卖出"""
        try:
            positions = self.trader.get_positions(
                ACCOUNT_ID,
                signal['symbol']
            )

            if positions.empty:
                return {'status': 'skipped', 'message': '无持仓'}

            position = positions.iloc[0]
            can_sell = position.get('can_use_volume', 0)

            if can_sell < 100:
                return {'status': 'skipped', 'message': '可卖数量不足'}

            # 根据信号强度决定卖出比例
            sell_ratio = min(0.5, abs(signal['strength']))
            quantity = int(can_sell * sell_ratio) // 100 * 100

            print(f"\n[DOWN] 卖出信号: {signal['symbol']}")
            print(f"  持仓数量: {can_sell} 股")
            print(f"  卖出数量: {quantity} 股")
            print(f"  信号强度: {signal['strength']:.2f}")
            print(f"  信号原因: {', '.join(signal['reasons'])}")

            # 实际交易（注释掉，避免误操作）
            # result = self.trader.order_stock(
            #     account_id=ACCOUNT_ID,
            #     stock_code=signal['symbol'],
            #     order_type='sell',
            #     order_volume=quantity,
            #     price_type='limit',
            #     price=signal['price']
            # )

            return {'status': 'success', 'message': f'模拟卖出 {quantity} 股'}

        except Exception as e:
            return {'status': 'failed', 'message': f'卖出失败: {e}'}


# ==================== 主程序 ====================

def main():
    """主程序"""
    print("="*70)
    print("  通达信数据 + EasyXT交易系统 实战案例")
    print("="*70)
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 初始化系统
    system = TdxEasyXTSystem()

    # 示例1: 获取行情数据
    print("="*70)
    print("  【示例1】获取通达信行情数据")
    print("="*70)

    stocks = ['605168.SH', '000333.SZ']
    print(f"[UP] 获取股票行情: {stocks}\n")

    market_data = system.get_market_data(
        stock_list=stocks,
        start_time='20250101',
        period='1d'
    )

    if not market_data.empty:
        print(f"[OK] 获取行情数据成功")
        print(f"  数据形状: {market_data.shape}")
        print(f"  数据列: {market_data.columns.tolist()}")
        print(f"\n  最新数据:")
        print(market_data.tail(5).to_string())
    else:
        print("[ERROR] 获取行情数据失败")

    # 示例2: 通达信数据功能全面测试
    print("\n" + "="*70)
    print("  【示例2】通达信数据功能全面测试")
    print("="*70)

    if not market_data.empty:
        # 测试1: 数据基本信息
        print("\n[测试1] 数据基本信息")
        print("-"*70)

        print(f"  获取股票数量: {len(stocks)}")
        print(f"  数据形状: {market_data.shape}")
        print(f"  数据列: {market_data.columns.tolist()}")
        print(f"\n  最新行情:")

        for _, row in market_data.iterrows():
            symbol = row['Symbol']
            close = row['Close']  # 列名是大写的
            high = row['High']
            low = row['Low']
            volume = row['Volume']
            amount = row['Amount']
            print(f"    {symbol}: 收盘 {close:.2f}, 最高 {high:.2f}, 最低 {low:.2f}, 成交量 {volume:,.0f}, 成交额 {amount:,.0f}")

        # 测试2: 获取历史数据
        print("\n\n[测试2] 历史数据获取与统计")
        print("-"*70)

        test_stock = '605168.SH'

        # 获取历史数据
        from easy_xt.tdx_client import TdxClient

        with TdxClient() as client:
            try:
                # 获取历史数据
                historical_data = client.get_market_data(
                    stock_list=[test_stock],
                    start_time='20250101',
                    period='1d'
                )

                if not historical_data.empty:
                    print(f"\n  {test_stock} 历史统计:")
                    print(f"  数据条数: {len(historical_data)}")

                    # 价格统计（使用大写列名）
                    print(f"\n  价格统计:")
                    print(f"    最高价: {historical_data['High'].max():.2f}")
                    print(f"    最低价: {historical_data['Low'].min():.2f}")
                    print(f"    平均收盘: {historical_data['Close'].mean():.2f}")
                    print(f"    最新收盘: {historical_data['Close'].iloc[-1]:.2f}")
                    print(f"    成交量合计: {historical_data['Volume'].sum():,.0f}")

                    # 计算简单技术指标
                    if len(historical_data) >= 3:
                        historical_data['MA3'] = historical_data['Close'].rolling(window=3).mean()
                        latest_ma3 = historical_data['MA3'].iloc[-1]
                        print(f"\n  技术指标:")
                        print(f"    3日均线: {latest_ma3:.2f}")
                        print(f"    价格趋势: {'上涨' if historical_data['Close'].iloc[-1] > historical_data['Close'].iloc[0] else '下跌'}")
                else:
                    print(f"  [空] 历史数据为空")

            except Exception as e:
                print(f"  [ERROR] 历史数据获取失败: {e}")

        # 测试3: 多股票对比
        print("\n\n[测试3] 多股票对比")
        print("-"*70)

        print(f"\n  股票对比:")
        print(f"  {'股票代码':12} {'收盘价':>10} {'涨跌':>10} {'成交额':>15}")
        print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*15}")

        for symbol in stocks:
            symbol_data = market_data[market_data['Symbol'] == symbol]
            if not symbol_data.empty:
                row = symbol_data.iloc[0]
                close = row['Close']
                open_price = row['Open']
                amount = row['Amount']
                change = close - open_price
                change_pct = (change / open_price) * 100

                print(f"  {symbol:12} {close:>10.2f} {change_pct:>9.2f}% {amount:>15,.2f}")

        # 测试4: 通达信数据API特性
        print("\n\n[测试4] 通达信数据API特性")
        print("-"*70)

        with TdxClient() as client:
            print(f"\n  [INFO] 通达信数据API特性:")
            print(f"    - 数据来源: 项目本地PYPlugins/user")
            print(f"    - 支持周期: 日线(1d)、周线(1wk)、月线(1m)")
            print(f"    - 支持复权: 不复权(none)、前复权(front)、后复权(back)")
            print(f"    - 支持字段: Open, High, Low, Close, Volume, Amount")
            print(f"    - 数据格式: 统一的DataFrame格式")
            print(f"\n  [TIP] 获取更多历史数据:")
            print(f"    data = client.get_market_data(")
            print(f"        stock_list=['000001.SZ'],")
            print(f"        start_time='20240101',  # 设置更早的开始时间")
            print(f"        period='1d',")
            print(f"        dividend_type='front'  # 前复权")
            print(f"    )")

        print("\n[INFO] 通达信数据功能测试完成!")
        print("  成功获取实时行情数据")
        print("  支持历史K线数据获取")
        print("  支持多股票同时查询")
        print("  数据格式统一为DataFrame，便于分析")

    # 示例3: 获取财务数据
    print("\n" + "="*70)
    print("  【示例3】获取通达信财务数据")
    print("="*70)

    print("[WARN]  通达信财务数据需要购买专业财务数据权限")
    print("[TIP] 如果有权限，可以使用以下代码获取财务数据:")
    print("""
    financial_data = system.get_financial_data(
        stock_list=['000001.SZ'],
        field_list=['净资产收益率', '市盈率', '营业总收入',
                    '净利润', '资产负债率', '毛利率'],
        start_time='20230101',
        end_time='20241231'
    )
    """)

    # 实际调用（测试是否有权限）
    fin_data = system.get_financial_data(
        stock_list=['000001.SZ'],
        field_list=['净资产收益率', '市盈率'],
    )

    if not fin_data.empty:
        print(f"\n[OK] 财务数据获取成功!")
        print(f"  数据形状: {fin_data.shape}")
        print(f"\n  财务数据:")
        print(fin_data.head())
    else:
        print(f"\n[ERROR] 财务数据为空（需要专业财务数据权限）")

    # 示例4: 通达信条件选股 + EasyXT 批量下单
    print("\n" + "="*70)
    print("  【示例4】通达信自选股 + EasyXT批量下单")
    print("="*70)

    print("\n[应用场景]")
    print("  在通达信中管理自选股，通过程序化方式实现批量自动下单！")
    print("\n[使用方法]")
    print("  1. 在通达信中添加自选股（F6）")
    print("  2. 运行工具提取自选股: python tools/parse_tdx_zixg.py")
    print("  3. 股票列表保存到: my_favorites.txt")
    print("  4. 程序自动读取并执行批量下单")
    print("\n[核心优势]")
    print("  1. 利用通达信管理自选股（习惯的操作方式）")
    print("  2. 自动读取自选股文件")
    print("  3. 程序化批量下单，提高效率")
    print("  4. 可结合多种风控条件")
    print("\n[准备检查]")
    print("  请确认已运行: python tools/parse_tdx_zixg.py")
    print("  生成文件: my_favorites.txt")

    from easy_xt.tdx_client import TdxClient

    with TdxClient() as client:
        # ============================================================
        # 方法1: 通达信条件选股（推荐）
        # ============================================================
        print("\n" + "="*70)
        print("  【方法1】使用通达信条件选股功能")
        print("="*70)

        print("\n[步骤1] 在通达信中设置条件选股")
        print("-"*70)

        print("""
  通达信条件选股使用方法:
  ┌─────────────────────────────────────────────────┐
  │ 1. 打开通达信 -> 工具 -> 条件选股（或按Ctrl+T）  │
  │ 2. 设置选股条件:                               │
  │    - 技术指标: MACD、KDJ、RSI、布林带等         │
  │    - K线形态: 金叉、死叉、阳包阴等              │
  │    - 财务数据: ROE、PE、PB等                    │
  │ 3. 点击"执行选股"                              │
  │ 4. 在结果窗口右键 -> "结果导出" -> "导出到板块"  │
  │ 5. 选择或创建板块（如'自选股'或'CSBK'）         │
  │ 6. 确定保存                                    │
  └─────────────────────────────────────────────────┘

  常用条件选股公式示例:
  - MACD金叉: CROSS(MACD.DIF, MACD.DEA)
  - KDJ金叉: CROSS(KDJ.K, KDJ.D)
  - RSI超卖: RSI.RSI1(6, 12, 24) < 20
  - 均线多头排列: MA5 > MA10 > MA20 > MA60
  - 放量上涨: CLOSE/REF(CLOSE,1) > 1.03 AND VOL/REF(VOL,1) > 1.5
        """)

        print("\n[步骤2] 获取股票列表")
        print("-"*70)

        # 方法A: 读取通达信自选股文件（推荐）
        print("\n  [方法A] 从通达信自选股文件读取（推荐）")
        print("  " + "-"*66)

        stock_list = []
        favorites_file = Path(__file__).parent.parent / "my_favorites.txt"

        if favorites_file.exists():
            try:
                with open(favorites_file, 'r', encoding='utf-8') as f:
                    stock_list = [line.strip() for line in f if line.strip()]

                if stock_list:
                    print(f"\n  [OK] 成功读取自选股文件")
                    print(f"  文件路径: {favorites_file}")
                    print(f"  股票数量: {len(stock_list)}")
                    print(f"  示例股票: {stock_list[:5]}")

                    if len(stock_list) > 5:
                        print(f"             ... 还有 {len(stock_list) - 5} 只股票")
                else:
                    print(f"\n  [WARN] 自选股文件为空")
                    stock_list = []

            except Exception as e:
                print(f"\n  [ERROR] 读取自选股文件失败: {e}")
                stock_list = []
        else:
            print(f"\n  [INFO] 未找到自选股文件: {favorites_file}")
            print(f"  [TIP] 运行以下命令提取通达信自选股:")
            print(f"        python tools/parse_tdx_zixg.py")

        # 方法B: 从通达信板块获取（备选）
        if not stock_list:
            print("\n  [方法B] 从通达信板块获取（备选）")
            print("  " + "-"*66)

            # 常见的板块名称
            sector_examples = {
                '自选股': '用户自定义的自选股板块',
                'CSBK': '测试板块',
                '沪深300': '沪深300成分股',
                '中证500': '中证500成分股',
            }

            print("\n  常见板块名称:")
            for name, desc in sector_examples.items():
                print(f"    - {name:12} : {desc}")

            # 这里使用一个测试板块
            sector_name = '自选股'
            print(f"\n  当前使用板块: {sector_name}")

            try:
                # 获取板块股票
                sector_stocks = client.get_sector_stocks(sector_name, block_type=1)

                if sector_stocks and len(sector_stocks) > 0:
                    print(f"\n  [OK] 成功获取板块 '{sector_name}' 中的股票")
                    print(f"  股票数量: {len(sector_stocks)}")
                    print(f"  股票列表: {sector_stocks}")
                    stock_list = sector_stocks
                else:
                    print(f"\n  [WARN] 板块 '{sector_name}' 中没有股票")

            except Exception as e:
                print(f"\n  [ERROR] 获取板块失败: {e}")

        # 方法C: 使用测试股票列表（最后备选）
        if not stock_list:
            print("\n  [方法C] 使用测试股票列表（演示）")
            print("  " + "-"*66)
            stock_list = ['605168.SH', '000333.SZ', '600519.SH']
            print(f"\n  [INFO] 使用演示股票: {stock_list}")

        print(f"\n  [最终] 股票池数量: {len(stock_list)} 只")

        # ============================================================
        # 方法2: 程序化条件选股（高级）
        # ============================================================
        print("\n" + "="*70)
        print("  【方法2】程序化条件选股（高级）")
        print("="*70)

        print("\n[步骤1] 获取股票池数据")
        print("-"*70)

        # 使用板块股票或全市场股票
        print(f"  股票池: {len(stock_list)} 只股票")

        try:
            # 获取实时行情
            all_stock_data = client.get_market_data(
                stock_list=stock_list,
                start_time='20250101',
                period='1d'
            )

            print(f"  [OK] 获取行情数据: {len(all_stock_data)} 条记录")

        except Exception as e:
            print(f"  [ERROR] 获取行情失败: {e}")
            all_stock_data = None

        # 步骤2: 执行程序化条件筛选
        print("\n[步骤2] 执行程序化条件筛选")
        print("-"*70)

        selected_stocks = []

        if all_stock_data is not None and not all_stock_data.empty:
            print("\n  筛选条件:")
            print("    1. 收盘价 > 开盘价（阳线）")
            print("    2. 成交量 > 100万")
            print("    3. 收盘价 > MA20（上升趋势）")

            for symbol in stock_list:
                try:
                    # 获取该股票的历史数据
                    hist_data = client.get_market_data(
                        stock_list=[symbol],
                        start_time='20240101',  # 获取更多历史数据
                        period='1d'
                    )

                    if hist_data is None or hist_data.empty:
                        continue

                    # 计算技术指标
                    hist_data['MA20'] = hist_data['Close'].rolling(window=20).mean()
                    latest = hist_data.iloc[-1]

                    # 应用筛选条件
                    conditions = []
                    condition_desc = []

                    # 条件1: 阳线
                    is_red = latest['Close'] > latest['Open']
                    conditions.append(is_red)
                    if is_red:
                        condition_desc.append("阳线")

                    # 条件2: 成交量放大
                    volume_ok = latest['Volume'] > 1000000
                    conditions.append(volume_ok)
                    if volume_ok:
                        condition_desc.append("放量")

                    # 条件3: 上升趋势
                    if len(hist_data) >= 20 and not pd.isna(latest['MA20']):
                        trend_up = latest['Close'] > latest['MA20']
                        conditions.append(trend_up)
                        if trend_up:
                            condition_desc.append("趋势向上")

                    # 所有条件都满足
                    if all(conditions) and len(condition_desc) >= 2:
                        selected_stocks.append({
                            'symbol': symbol,
                            'close': latest['Close'],
                            'volume': latest['Volume'],
                            'change': ((latest['Close'] - latest['Open']) / latest['Open']) * 100,
                            'reasons': ', '.join(condition_desc)
                        })

                except Exception as e:
                    print(f"    {symbol}: 分析失败 - {e}")

            # 显示筛选结果
            print(f"\n  [筛选结果]")
            if selected_stocks:
                print(f"    符合条件的股票: {len(selected_stocks)} 只")

                for stock in selected_stocks:
                    print(f"    - {stock['symbol']}: "
                          f"{stock['close']:.2f} ({stock['change']:+.2f}%) - "
                          f"{stock['reasons']}")
            else:
                print(f"    [INFO] 当前没有符合条件的股票")

        # ============================================================
        # 真实批量下单
        # ============================================================
        print("\n" + "="*70)
        print("  【批量下单执行】")
        print("="*70)

        print("\n[警告] 即将执行真实下单操作！")
        print("="*70)
        print(f"  [警告] 这将使用真实资金进行股票交易")
        print(f"  [确认]")
        print(f"    1. QMT已登录且账户可用")
        print(f"    2. 账户ID: {ACCOUNT_ID}")
        print(f"    3. 自选股数量: {len(stock_list)} 只")
        print(f"    4. 符合条件: {len(selected_stocks) if selected_stocks else 0} 只")
        print(f"\n  如需取消，请按 Ctrl+C")

        # 检查交易模块是否可用
        if not system.trading_available:
            print("\n[ERROR] 交易模块未初始化，无法下单")
            print("  请检查:")
            print("    1. QMT是否已启动")
            print("    2. EasyXT交易模块是否初始化成功")
            return

        # 等待用户确认
        import time
        try:
            print(f"\n  倒计时开始...")
            for i in range(5, 0, -1):
                print(f"    {i} 秒...")
                time.sleep(1)
            print(f"  [继续] 开始执行下单...\n")
        except KeyboardInterrupt:
            print("\n[INFO] 用户取消操作")
            return

        # 获取目标股票列表（优先使用筛选后的，否则使用全部自选股）
        target_stocks = selected_stocks if selected_stocks else []

        # 如果没有符合条件的股票，询问是否使用全部自选股
        if not target_stocks:
            print(f"[INFO] 没有符合条件的股票")
            print(f"[提示] 您可以选择:")
            print(f"  1. 从全部自选股中选择（数量较多）")
            print(f"  2. 取消操作，调整筛选条件")

            user_confirm = input(f"\n  是否从全部自选股中随机选择3只进行交易？(yes/no): ").strip().lower()

            if user_confirm != 'yes':
                print("[INFO] 用户取消操作")
                return

            # 获取实时行情后随机选择3只
            print(f"\n[获取行情] 正在获取自选股实时行情...")
            import random
            random_stocks = random.sample(stock_list, min(3, len(stock_list)))

            for symbol in random_stocks:
                try:
                    hist_data = client.get_market_data(
                        stock_list=[symbol],
                        start_time='20250101',
                        period='1d'
                    )

                    if hist_data is not None and not hist_data.empty:
                        latest = hist_data.iloc[-1]
                        target_stocks.append({
                            'symbol': symbol,
                            'close': latest['Close'],
                            'reasons': '随机选择'
                        })
                except Exception as e:
                    print(f"  [WARN] 获取 {symbol} 行情失败: {e}")

            if not target_stocks:
                print(f"[ERROR] 无法获取任何股票行情")
                return

        # 获取账户信息
        print("\n[账户信息]")
        print("-"*70)

        try:
            account = system.trader.get_account_asset(ACCOUNT_ID)
            print(f"  总资产: {account.get('total_asset', 0):,.2f}")
            print(f"  可用资金: {account.get('cash', 0):,.2f}")
            print(f"  持仓市值: {account.get('market_value', 0):,.2f}")

            available_cash = account.get('cash', 0)

            if available_cash < 10000:
                print(f"\n[WARN] 可用资金不足: {available_cash:,.2f}")
                print("  建议入金或减少交易数量")
                return

        except Exception as e:
            print(f"[ERROR] 获取账户信息失败: {e}")
            return

        # 执行批量下单
        print(f"\n[下单执行]")
        print("-"*70)

        # 下单参数
        single_stock_amount = 5000  # 每只股票买入金额
        orders_submitted = []

        for i, stock in enumerate(target_stocks, 1):
            symbol = stock['symbol']
            price = stock['close']

            # 计算买入数量
            quantity = int(single_stock_amount / price) // 100 * 100

            if quantity < 100:
                print(f"\n  [{i}/{len(target_stocks)}] {symbol}")
                print(f"    [SKIP] 金额不足，无法购买")
                continue

            print(f"\n  [{i}/{len(target_stocks)}] {symbol}")
            print(f"    操作: 买入")
            print(f"    数量: {quantity} 股")
            print(f"    价格: {price:.2f}")
            print(f"    金额: {quantity * price:,.2f}")

            # 执行真实下单
            try:
                # 使用EasyXT的buy方法
                result = system.trader.trade.buy(
                    account_id=ACCOUNT_ID,
                    code=symbol,
                    volume=quantity,
                    price=price,
                    price_type='limit'  # 限价单
                )

                if result:
                    print(f"    [OK] 订单已提交")
                    print(f"    委托编号: {result}")
                    orders_submitted.append({
                        'symbol': symbol,
                        'quantity': quantity,
                        'price': price,
                        'amount': quantity * price,
                        'order_id': result
                    })
                else:
                    print(f"    [FAIL] 订单提交失败")

            except Exception as e:
                print(f"    [ERROR] 下单失败: {e}")
                import traceback
                traceback.print_exc()

        # 汇总
        print("\n" + "="*70)
        print("  [下单汇总]")
        print("="*70)

        if orders_submitted:
            total_quantity = sum(o['quantity'] for o in orders_submitted)
            total_amount = sum(o['amount'] for o in orders_submitted)

            print(f"\n  成功提交: {len(orders_submitted)} 笔订单")
            print(f"  总数量: {total_quantity} 股")
            print(f"  总金额: {total_amount:,.2f}")

            print(f"\n  订单明细:")
            for order in orders_submitted:
                print(f"    - {order['symbol']}: "
                      f"{order['quantity']}股 × {order['price']:.2f} = "
                      f"{order['amount']:,.2f}")

            print(f"\n  [重要提醒]")
            print(f"    1. 订单已提交，请在QMT中确认")
            print(f"    2. 可在QMT的委托查询中查看订单状态")
            print(f"    3. 建议设置止损止盈")
            print(f"    4. 控制仓位，不要满仓操作")
        else:
            print(f"\n  [INFO] 没有订单提交成功")

        # ============================================================
        # 完整使用说明
        # ============================================================
        print("\n" + "="*70)
        print("  【完整使用流程】")
        print("="*70)

        print("""
方式一: 使用通达信自选股（推荐，最简单）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 在通达信中管理自选股:
   - 按F6打开自选股设置
   - 添加股票到自选股
   - 您可以直接在通达信中管理股票池

2. 提取自选股到文件:
   python tools/parse_tdx_zixg.py

   输出示例:
     [成功] 解析到 35 只股票:
        1. 002475.SZ
        2. 002528.SZ
        ...
     [保存] 已保存到: my_favorites.txt

3. 运行自动下单:
   python 学习实例/11_通达信数据获取与交易实战.py

   脚本会自动:
   - 读取 my_favorites.txt
   - 获取实时行情
   - 执行条件筛选（阳线+放量+趋势向上）
   - 批量下单


方式二: 使用通达信条件选股（备选）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 在通达信中设置条件:
   - 打开: 工具 -> 条件选股 (Ctrl+T)
   - 常用条件:
     * MACD金叉: CROSS(MACD.DIF, MACD.DEA)
     * KDJ超卖: CROSS(KDJ.K(9,3,3), 20)
     * RSI超卖: RSI.RSI1(6,12,24) < 20
     * 放量突破: C > REF(C,1) * 1.03 AND V > REF(V,1) * 1.5

2. 执行选股并导出:
   - 点击"执行选股"
   - 等待选股完成
   - 在结果窗口右键 -> "结果导出"
   - 选择"导出到板块"
   - 创建或选择板块
   - 确定保存

3. 运行自动下单脚本:
   python 学习实例/11_通达信数据获取与交易实战.py


方式三: 手动维护股票列表（简单灵活）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 编辑 my_favorites.txt 文件:
   002475.SZ
   002528.SZ
   600519.SH
   ...

2. 运行自动下单:
   python 学习实例/11_通达信数据获取与交易实战.py


交易配置说明:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

修改交易参数（在本文件中）:
   ACCOUNT_ID = '39020958'           # 账户ID
   single_stock_amount = 5000       # 每只股票买入金额
   max_stocks = 3                   # 最多买入几只

筛选条件（在代码中）:
   1. 阳线: Close > Open
   2. 放量: Volume > 1000000
   3. 趋势向上: Close > MA20

可根据需要修改这些条件。

3. 对符合条件的股票批量下单


风控建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 先用模拟账号测试
2. 设置单股最大买入金额
3. 设置总交易金额上限
4. 设置单日最大交易次数
5. 避免全仓买入，分批建仓
6. 结合止损止盈策略
        """)

        print("\n[TIP] 快速开始（推荐流程）:")
        print("  1. 在通达信中添加自选股（F6）")
        print("  2. 运行: python tools/parse_tdx_zixg.py")
        print("  3. 检查: my_favorites.txt 文件")
        print("  4. 运行: python 学习实例/11_通达信数据获取与交易实战.py")
        print("  5. 确认后自动批量下单")

        print("\n[TIP] 通达信量化 + EasyXT = 个人量化最优解!")
        print("  - 通达信: 强大的行情数据和分析工具")
        print("  - EasyXT: 便捷的交易执行接口")
        print("  - 优势: 无需编程基础，可视化条件选股 + 自动下单")
        print("  - 自选股: 直接使用通达信自选股，无需重复维护")

    # 示例5: 通达信跟踪预警 + 自动交易（全自动）
    print("\n" + "="*70)
    print("  【示例5】通达信跟踪预警 + 自动交易（全自动）")
    print("="*70)

    print("""
┌─────────────────────────────────────────────────────────────┐
│  核心思路：跟踪预警 + 板块导出 = 全自动选股交易              │
│                                                              │
│  优势：                                                      │
│  1. 无需每天手动更新自选股                                    │
│  2. 盘中实时预警，立即触发交易                                │
│  3. 可视化设置条件，无需编程                                  │
│  4. 完全自动运行                                              │
└─────────────────────────────────────────────────────────────┘
    """)

    print("\n[应用场景]")
    print("  从'半自动'升级到'全自动'：")
    print("  - 旧方式：每天手动更新动态自选股 → 导出 → 运行脚本")
    print("  - 新方式：设置一次预警 → 自动监控 → 自动交易")

    print("\n[完整流程]")
    print("="*70)

    print("""
步骤1: 通达信设置跟踪预警
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 打开通达信预警系统:
   - 功能菜单 → 预警系统 (或按 Ctrl+W)
   - 或: 工具 → 条件预警 → 条件预警设置

2. 添加预警条件:
   ┌──────────────────────────────────────────────────┐
   │ 条件示例:                                         │
   │                                                  │
   │ 【价格预警】                                      │
   │  - 价格突破20日新高:                              │
   │    C > HHV(C, 20)                                │
   │                                                  │
   │ 【技术指标预警】                                  │
   │  - MACD金叉:                                      │
   │    CROSS(MACD.DIF, MACD.DEA)                     │
   │  - KDJ金叉:                                       │
   │    CROSS(KDJ.K, KDJ.D)                           │
   │  - RSI超卖:                                       │
   │    RSI.RSI1(6,12,24) < 20                        │
   │                                                  │
   │ 【成交量预警】                                    │
   │  - 放量上涨:                                      │
   │    C/REF(C,1) > 1.03 AND V/REF(V,1) > 2         │
   │  - 突然放量:                                      │
   │    V > MA(V, 5) * 3                              │
   │                                                  │
   │ 【形态预警】                                      │
   │  - 阳包阴:                                        │
   │    O < REF(C, 1) AND C > REF(O, 1)              │
   │  - 穿头破脚:                                      │
   │    C > O AND L < REF(L, 1) AND H > REF(H, 1)    │
   └──────────────────────────────────────────────────┘

3. 设置预警输出:
   - 勾选"输出到预警板块"
   - 选择或创建板块: "预警股票"
   - 勾选"自动刷新" (实时监控)
   - 设置刷新频率: 5秒/次

4. 启动预警:
   - 点击"启动预警系统"
   - 通达信开始自动监控全市场
   - 满足条件的股票自动加入"预警股票"板块


步骤2: Python读取预警板块并自动交易
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

    # 实现：读取预警板块并交易
    print("\n[代码实现]")
    print("-"*70)

    print("""
# ===== 自动监控并交易预警股票 =====

import time
from datetime import datetime
from easy_xt.tdx_client import TdxClient

class AlertTradingBot:
    '''预警交易机器人 - 全自动交易系统'''

    def __init__(self, trader, account_id):
        self.trader = trader
        self.account_id = account_id
        self.alert_block = '预警股票'  # 通达信预警板块名称
        self.processed_alerts = set()  # 已处理的预警，避免重复

    def check_alerts(self):
        '''检查新的预警股票'''
        with TdxClient() as client:
            # 读取预警板块
            alert_stocks = client.get_sector_stocks(
                self.alert_block,
                block_type=1  # 1=自选股板块
            )

            if not alert_stocks:
                print(f"[{datetime.now()}] 暂无新预警")
                return []

            # 过滤掉已处理的
            new_alerts = [s for s in alert_stocks if s not in self.processed_alerts]

            if new_alerts:
                print(f"\\n[{datetime.now()}] 发现 {len(new_alerts)} 个新预警:")
                for stock in new_alerts:
                    print(f"  - {stock}")

            return new_alerts

    def evaluate_and_trade(self, stock_list):
        '''评估并交易预警股票'''
        if not stock_list:
            return

        with TdxClient() as client:
            for stock_code in stock_list:
                try:
                    # 获取实时行情
                    data = client.get_market_data(
                        stock_list=[stock_code],
                        start_time='20250101',
                        period='1d'
                    )

                    if data.empty:
                        continue

                    latest = data.iloc[-1]
                    current_price = latest['Close']

                    # 简单评估：这里可以加入更复杂的策略
                    # 例如：检查是否在交易时段、涨跌幅限制等
                    print(f"\\n  {stock_code}")
                    print(f"    当前价格: {current_price:.2f}")
                    print(f"    决策: 满足预警条件，准备买入")

                    # 自动买入
                    self.auto_buy(stock_code, current_price)

                    # 标记为已处理
                    self.processed_alerts.add(stock_code)

                except Exception as e:
                    print(f"    错误: {e}")

    def auto_buy(self, stock_code, price):
        '''自动买入'''
        try:
            # 获取账户信息
            account = self.trader.get_account_asset(self.account_id)
            cash = account.get('cash', 0)

            # 计算买入数量（使用10%资金）
            trade_amount = cash * 0.1
            quantity = int(trade_amount / price) // 100 * 100

            if quantity < 100:
                print(f"    [跳过] 资金不足")
                return

            # 执行买入
            print(f"    [买入] {quantity}股 @ {price:.2f}元")

            # 实际下单（注释掉，避免误操作）
            # result = self.trader.trade.buy(
            #     account_id=self.account_id,
            #     code=stock_code,
            #     volume=quantity,
            #     price=price,
            #     price_type='limit'
            # )
            # print(f"    [成功] 委托编号: {result}")

        except Exception as e:
            print(f"    [失败] {e}")

    def run(self, duration_hours=4):
        '''运行机器人（持续监控）'''
        print(f"\\n[启动] 预警交易机器人开始运行")
        print(f"  监控时长: {duration_hours}小时")
        print(f"  预警板块: {self.alert_block}")
        print(f"  检查频率: 每30秒")

        start_time = time.time()
        check_interval = 30  # 30秒检查一次

        while True:
            try:
                # 检查是否超时
                if time.time() - start_time > duration_hours * 3600:
                    print(f"\\n[完成] 监控时长已到，退出")
                    break

                # 检查新预警
                new_alerts = self.check_alerts()

                # 如果有新预警，评估并交易
                if new_alerts:
                    self.evaluate_and_trade(new_alerts)

                # 等待下一次检查
                time.sleep(check_interval)

            except KeyboardInterrupt:
                print(f"\\n[中断] 用户手动停止")
                break
            except Exception as e:
                print(f"\\n[错误] {e}")
                time.sleep(check_interval)


# 使用示例
print("\\n" + "="*70)
print("  【实战演示】启动预警交易机器人")
print("="*70)

if system.trading_available:
    # 创建机器人实例
    bot = AlertTradingBot(system.trader, ACCOUNT_ID)

    # 运行机器人（监控4小时，覆盖整个交易时段）
    print("\\n[提示] 按 Ctrl+C 可随时停止")
    print("[模拟] 下面将演示30秒的监控...\\n")

    try:
        # 短时间演示（实际使用时改为4小时）
        bot.run(duration_hours=0.01)  # 约30秒演示

    except KeyboardInterrupt:
        print("\\n[用户中断] 演示结束")
else:
    print("\\n[跳过] 交易模块未初始化，跳过演示")
    """)

    print("\n[定时任务]：每天自动运行")
    print("-"*70)

    print("""
# 方案1: 使用Windows任务计划程序
# ──────────────────────────────────────────────
# 1. 打开"任务计划程序"（taskschd.msc）
# 2. 创建基本任务
# 3. 触发器: 每天 9:25
# 4. 操作: 启动程序 python alert_trading_bot.py
# 5. 完成！每天自动运行

# 方案2: 使用Python定时任务
# ──────────────────────────────────────────────
import schedule
import time

def run_trading_bot():
    bot = AlertTradingBot(trader, ACCOUNT_ID)
    bot.run(duration_hours=4)  # 监控4小时

# 每天9:25运行
schedule.every().day.at("09:25").do(run_trading_bot)

while True:
    schedule.run_pending()
    time.sleep(60)

# 方案3: Docker容器（推荐服务器部署）
# ──────────────────────────────────────────────
# docker-compose.yml
version: '3'
services:
  trading-bot:
    image: python:3.9
    volumes:
      - ./app:/app
    command: python alert_trading_bot.py
    restart: always
    """)

    print("\n[风控建议]")
    print("-"*70)

    print("""
1. 资金管理
   - 单次买入不超过总资金的10%
   - 单日最大买入次数：5次
   - 单只股票最大仓位：20%

2. 价格控制
   - 设置买入价上限：当前价 + 1%
   - 避免追高，防止滑点过大

3. 时间控制
   - 只在交易时段运行：9:30-15:00
   - 开盘30分钟内避免交易（波动大）
   - 尾盘30分钟避免交易（流动性差）

4. 数量控制
   - 每天最多交易3只股票
   - 避免过度交易

5. 仓位管理
   - 总仓位不超过80%
   - 留有现金应对机会
   - 分批建仓，不要一次性满仓
    """)

    print("\n[完整使用流程]")
    print("="*70)

    print("""
第一步: 设置通达信预警（一次性设置）
─────────────────────────────────────────
1. 打开通达信 → 功能 → 预警系统
2. 添加预警条件（如MACD金叉）
3. 设置输出到"预警股票"板块
4. 启动预警系统

第二步: 启动自动交易脚本（每天一次）
─────────────────────────────────────────
python 学习实例/11_通达信数据获取与交易实战.py

第三步: 享受全自动（完全解放双手）
─────────────────────────────────────────
- 通达信实时监控全市场
- 发现符合条件的股票
- 自动加入预警板块
- Python读取并自动下单
- 全程无需人工干预


与自选股方案对比
─────────────────────────────────────────
┌──────────────┬─────────────────┬─────────────────┐
│   功能       │   自选股方案    │   预警方案      │
├──────────────┼─────────────────┼─────────────────┤
│ 更新频率     │ 每天手动        │ 实时自动        │
│ 选股方式     │ 手动添加        │ 条件自动筛选    │
│ 响应速度     │ 慢（一天一次）  │ 快（实时响应）  │
│ 人工操作     │ 需要每天导出    │ 一次设置永久    │
│ 适用场景     │ 中长期投资      │ 短线/波段操作   │
│ 自动化程度   │ 半自动          │ 全自动          │
└──────────────┴─────────────────┴─────────────────┘

推荐组合:
  - 中长期持仓: 用自选股方案（示例4）
  - 短线波段: 用预警方案（示例5）
  - 两者结合: 效果更佳！
    """)

    print("\n[注意事项]")
    print("-"*70)

    print("""
⚠️ 重要提示:
1. 确保通达信保持运行状态
2. 确保QMT已登录并可用
3. 建议先在模拟账号测试
4. 设置合理的止损止盈
5. 监控运行日志，及时发现问题

✅ 优势:
1. 完全自动，无需人工干预
2. 实时响应，不错过机会
3. 可视化设置，无需编程
4. 灵活配置，随时调整条件

❌ 限制:
1. 依赖通达信软件运行
2. 需要稳定的网络环境
3. 预警条件相对简单
4. 无法处理复杂的策略逻辑

💡 进阶技巧:
1. 多条件组合预警（提高准确率）
2. 设置预警时间窗口（避免特定时段）
3. 结合股票池过滤（只在自选股中预警）
4. 设置预警频次限制（避免重复预警）
5. 使用多种预警条件（分散风险）
    """)

    # 总结
    print("\n" + "="*70)
    print("  总结")
    print("="*70)

    print("""
[OK] 通达信 + EasyXT 完整功能:

1. 通达信行情数据获取
   - K线数据（日线、周线、分钟线）
   - 支持前复权、后复权
   - 高速、稳定、可靠

2. 通达信财务数据（需购买专业财务数据权限）
   - 资产负债表
   - 利润表
   - 现金流量表
   - 财务指标（ROE、PE、PB等）

3. 技术指标计算
   - 移动平均线（MA）
   - MACD
   - RSI
   - 布林带
   - 成交量指标

4. 交易信号生成
   - 多指标综合判断
   - 信号强度量化
   - 置信度评估

5. EasyXT交易执行
   - 自动下单
   - 持仓管理
   - 风险控制

6. 【示例4】通达信自选股批量交易（半自动）
   - 自动读取通达信自选股文件
   - 获取实时行情
   - 执行条件筛选
   - 批量自动下单
   - 完整的风控机制

7. 【示例5】通达信跟踪预警自动交易（全自动）⭐新增
   - 设置一次预警条件，永久自动运行
   - 实时监控全市场股票
   - 满足条件自动触发
   - 无需每天手动更新
   - 盘中实时响应，立即交易
   - 完全解放双手


[TIP] 使用建议:

方案一: 中长期投资（推荐自选股方案）
├─ 使用通达信管理自选股
├─ 每天收盘后运行一次脚本
└─ 批量调仓换股

方案二: 短线波段操作（推荐预警方案）⭐新
├─ 设置跟踪预警条件
├─ 自动监控全市场
├─ 实时触发自动交易
└─ 无需人工干预

方案三: 混合策略（最佳）⭐推荐
├─ 核心持仓：用自选股方案（中长期）
├─ 波段操作：用预警方案（短线）
└─ 两者结合，效果更佳！


数据来源选择:
1. 行情数据 -> 直接使用通达信（免费）
2. 财务数据 -> 购买通达信专业财务数据权限（几百块/年）
3. 交易执行 -> 使用EasyXT（免费）
4. 组合使用 -> 最优性价比方案


如需帮助，请访问:
   GitHub: https://github.com/quant-king299/EasyXT

⭐ 新增功能:
   - 通达信跟踪预警 + 自动交易
   - 完全自动运行，无需手动干预
   - 实时响应，不错过任何机会
    """)


if __name__ == "__main__":
    main()
