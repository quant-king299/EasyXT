import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
"""

通达信条件选股 + EasyXT批量下单实战示例



使用方法：

1. 在通达信中使用条件选股选出股票

2. 手动复制股票代码

3. 修改下面的stock_list变量

4. 运行脚本自动下单



作者：EasyXT团队

日期：2025-01-30

"""



import sys

from pathlib import Path

import time



# 添加项目路径

project_root = Path(__file__).parent.parent

sys.path.insert(0, str(project_root))

sys.path.insert(0, str(project_root / "easy_xt"))



from datetime import datetime



# ==================== 配置参数 ====================

# 交易配置

TRADING_CONFIG = {

    'userdata_path': r'D:\国金QMT交易端模拟\userdata_mini',

    'account_id': '39020958',

    'single_stock_amount': 5000,  # 每只股票买入金额

    'max_stocks': 3,               # 最多同时买入几只股票

}



# ==================== 股票池配置 ====================

# 方式1: 从通达信自选股文件读取（推荐）

# 使用说明：

#   1. 先运行 python tools/parse_tdx_zixg.py 提取自选股

#   2. 自选股会保存到 my_favorites.txt

#   3. 脚本自动从该文件读取



FALLBACK_STOCKS = []



# 尝试从文件读取自选股

STOCK_FILE = 'my_favorites.txt'

try:

    with open(STOCK_FILE, 'r', encoding='utf-8') as f:

        FALLBACK_STOCKS = [line.strip() for line in f if line.strip()]

    logger.info(f"[OK] 从文件读取自选股: {len(FALLBACK_STOCKS)} 只")
except FileNotFoundError:

    logger.warning(f"[WARN] 未找到自选股文件: {STOCK_FILE}")
    logger.info(f"[TIP] 运行 python tools/parse_tdx_zixg.py 提取自选股")
    logger.info(f"[INFO] 使用演示股票列表")
    FALLBACK_STOCKS = [

        '605168.SH',  # 明阳智能

        '000333.SZ',  # 美的集团

        '600519.SH',  # 贵州茅台

    ]



# 方式2: 手动设置股票列表（备选）

# 如果不使用文件，直接在这里设置：

# FALLBACK_STOCKS = [

#     '605168.SH',  # 明阳智能

#     '000333.SZ',  # 美的集团

#     '600519.SH',  # 贵州茅台

# ]



logger.info("="*70)
logger.info("  通达信条件选股 + EasyXT批量下单")
logger.info("="*70)
logger.info(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


# ==================== 股票列表确认 ====================

logger.info("[股票池] 股票列表")
logger.info("-"*70)
stock_list = FALLBACK_STOCKS

logger.info(f"  股票数量: {len(stock_list)} 只")
if len(stock_list) > 0:

    logger.info(f"  示例股票: {stock_list[:5]}")
print()



# ==================== 步骤1: 显示交易参数 ====================

logger.info("[步骤1] 交易参数确认")
logger.info("-"*70)
logger.info(f"  账户ID: {TRADING_CONFIG['account_id']}")
logger.info(f"  每股买入金额: {TRADING_CONFIG['single_stock_amount']:,.0f} 元")
logger.info(f"  最大买入数量: {TRADING_CONFIG['max_stocks']} 只")
logger.info(f"  股票池数量: {len(stock_list)} 只")
logger.info(f"  股票列表: {stock_list}")


# ==================== 步骤2: 获取实时行情 ====================

logger.info("\n[步骤2] 获取实时行情")
logger.info("-"*70)


try:

    from easy_xt.tdx_client import TdxClient



    with TdxClient() as client:

        market_data = client.get_market_data(

            stock_list=stock_list,

            start_time='20250130',

            period='1d'

        )



        if not market_data.empty:

            logger.info(f"\n  实时行情:")
            logger.info(f"  {'股票代码':12} {'收盘价':>10} {'涨跌幅':>10} {'成交量':>15}")
            logger.info(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*15}")


            for _, row in market_data.iterrows():

                symbol = row['Symbol']

                close = row['Close']

                open_price = row['Open']

                volume = row['Volume']

                change_pct = ((close - open_price) / open_price) * 100



                logger.info(f"  {symbol:12} {close:>10.2f} {change_pct:>9.2f}% {volume:>15,.0f}")
        else:

            logger.error("  [ERROR] 无法获取行情数据")


except Exception as e:

    logger.error(f"  [ERROR] 获取行情失败: {e}")
    logger.info("  [演示] 使用模拟价格")
    market_data = None



# ==================== 步骤3: 条件筛选 ====================

logger.info("\n[步骤3] 条件筛选")
logger.info("-"*70)


logger.info("\n  筛选条件:")
logger.info("    1. 收盘价 > 开盘价（阳线）")
logger.info("    2. 成交量 > 100万")
logger.info("    3. 涨跌幅 < 5% (避免追高)")


selected_stocks = []



if market_data is not None:

    for _, row in market_data.iterrows():

        symbol = row['Symbol']

        close = row['Close']

        open_price = row['Open']

        volume = row['Volume']

        high = row['High']

        low = row['Low']



        # 条件1: 阳线

        is_red = close > open_price



        # 条件2: 成交量放大

        volume_ok = volume > 1000000



        # 条件3: 涨幅不超过5%

        change_pct = ((close - open_price) / open_price) * 100

        not_limit_up = change_pct < 5



        if is_red and volume_ok and not_limit_up:

            selected_stocks.append({

                'symbol': symbol,

                'close': close,

                'volume': volume,

                'change_pct': change_pct,

                'reasons': f'阳线, 放量, 涨幅{change_pct:.2f}%'

            })



if selected_stocks:

    logger.info(f"\n  [筛选结果] 符合条件的股票: {len(selected_stocks)} 只")
    for stock in selected_stocks:

        logger.info(f"    - {stock['symbol']}: {stock['close']:.2f} ({stock['reasons']})")
else:

    logger.info("\n  [演示] 使用所有股票进行演示")
    # 创建模拟数据

    selected_stocks = [

        {'symbol': '605168.SH', 'close': 42.00, 'volume': 1500000, 'change_pct': 1.5},

        {'symbol': '000333.SZ', 'close': 78.50, 'volume': 5000000, 'change_pct': 1.2},

    ]



# ==================== 步骤4: 下单确认 ====================

logger.info("\n" + "="*70)
logger.info("  【重要提示】即将执行真实下单")
logger.info("="*70)


logger.info("\n  ⚠️  即将使用真实资金交易！")
logger.info(f"  ⚠️  账户ID: {TRADING_CONFIG['account_id']}")
logger.info(f"  ⚠️  将买入 {len(selected_stocks)} 只股票")


logger.info("\n  如需取消，请按 Ctrl+C")


try:

    # 倒计时

    for i in range(5, 0, -1):

        logger.info(f"    倒计时: {i} 秒...")
        time.sleep(1)



    logger.info("    继续执行下单...")


except KeyboardInterrupt:

    logger.info("\n\n[INFO] 用户取消操作")
    sys.exit(0)



# ==================== 步骤5: 初始化交易模块 ====================

logger.info("\n[步骤5] 初始化交易模块")
logger.info("-"*70)


try:

    from easy_xt.api import EasyXT



    trader = EasyXT()



    # 初始化交易服务

    init_result = trader.init_trade(

        userdata_path=TRADING_CONFIG['userdata_path'],

        session_id=TRADING_CONFIG['account_id']

    )



    if not init_result:

        logger.error("[ERROR] 交易服务初始化失败")
        logger.info("  请检查:")
        logger.info("    1. QMT是否已启动")
        logger.info("    2. userdata_path路径是否正确")
        sys.exit(1)



    # 添加账户

    trader.add_account(TRADING_CONFIG['account_id'])



    logger.info("[OK] 交易模块初始化成功")


    # 获取账户信息

    account = trader.get_account_asset(TRADING_CONFIG['account_id'])

    logger.info(f"\n  账户信息:")
    logger.info(f"    总资产: {account.get('total_asset', 0):,.2f}")
    logger.info(f"    可用资金: {account.get('cash', 0):,.2f}")


    available_cash = account.get('cash', 0)



    if available_cash < 10000:

        logger.warning(f"\n  [WARN] 可用资金不足: {available_cash:,.2f}")
        logger.info("  建议入金或减少交易数量")
        sys.exit(1)



except Exception as e:

    logger.error(f"[ERROR] 交易模块初始化失败: {e}")
    import traceback

    traceback.print_exc()

    sys.exit(1)



# ==================== 步骤6: 批量下单 ====================

logger.info("\n[步骤6] 批量下单执行")
logger.info("-"*70)


orders_submitted = []

single_amount = TRADING_CONFIG['single_stock_amount']

max_stocks = TRADING_CONFIG['max_stocks']



for i, stock in enumerate(selected_stocks[:max_stocks], 1):

    symbol = stock['symbol']

    price = stock['close']



    # 计算买入数量

    quantity = int(single_amount / price) // 100 * 100



    if quantity < 100:

        logger.info(f"\n  [{i}/{len(selected_stocks)}] {symbol}")
        logger.info(f"    [SKIP] 金额不足，无法购买100股")
        continue



    amount = quantity * price



    logger.info(f"\n  [{i}/{len(selected_stocks)}] {symbol}")
    logger.info(f"    操作: 买入")
    logger.info(f"    数量: {quantity} 股")
    logger.info(f"    价格: {price:.2f}")
    logger.info(f"    金额: {amount:,.2f}")
    logger.info(f"    原因: {stock.get('reasons', '条件筛选')}")


    # 执行下单

    try:

        order_id = trader.trade.buy(

            account_id=TRADING_CONFIG['account_id'],

            code=symbol,

            volume=quantity,

            price=price,

            price_type='limit'

        )



        if order_id:

            logger.info(f"    [OK] 下单成功！")
            logger.info(f"    委托编号: {order_id}")
            orders_submitted.append({

                'symbol': symbol,

                'quantity': quantity,

                'price': price,

                'amount': amount,

                'order_id': order_id

            })

        else:

            logger.info(f"    [FAIL] 下单失败")


    except Exception as e:

        logger.error(f"    [ERROR] 下单异常: {e}")
        import traceback

        traceback.print_exc()



# ==================== 步骤7: 订单汇总 ====================

logger.info("\n" + "="*70)
logger.info("  [订单汇总]")
logger.info("="*70)


if orders_submitted:

    total_quantity = sum(o['quantity'] for o in orders_submitted)

    total_amount = sum(o['amount'] for o in orders_submitted)



    logger.info(f"\n  成功下单: {len(orders_submitted)} 笔")
    logger.info(f"  总数量: {total_quantity} 股")
    logger.info(f"  总金额: {total_amount:,.2f} 元")


    logger.info(f"\n  订单明细:")
    for order in orders_submitted:

        print(f"    - {order['symbol']}: "

              f"{order['quantity']}股 × {order['price']:.2f} = "

              f"{order['amount']:,.2f} 元 "

              f"(委托号: {order['order_id']})")



    logger.info(f"\n  [重要提醒]")
    logger.info(f"    1. 已提交 {len(orders_submitted)} 个买入委托")
    logger.info(f"    2. 请在QMT的'委托查询'中查看订单状态")
    logger.info(f"    3. 建议设置止损止盈")
    logger.info(f"    4. 控制仓位，不要满仓操作")


else:

    logger.info("\n  [INFO] 没有订单提交成功")


# ==================== 使用说明 ====================

logger.info("\n" + "="*70)
logger.info("  【使用说明】")
logger.info("="*70)


print("""

完整操作流程:



方法1: 使用通达信板块（推荐）



1. 在通达信中创建自定义板块:

   - 打开通达信

   - 按F6或点击: 功能 -> 自选股设置

   - 点击"新建板块"

   - 输入板块名称（例如: '量化选股'）

   - 点击确定



2. 使用条件选股将结果导出到板块:

   - 打开通达信 -> 工具 -> 条件选股 (Ctrl+T)

   - 设置选股条件并执行

   - 在选股结果窗口，全选股票

   - 右键 -> 加入自选股 -> 选择刚创建的板块



3. 配置脚本参数:

   SECTOR_CONFIG = {

       'use_sector': True,

       'sector_name': '量化选股',  # 修改为你的板块名称

       'block_type': 1,

   }



4. 运行脚本:

   python tools/tdx_condition_stock_trading.py



方法2: 手动设置股票列表



1. 在通达信中使用条件选股:

   - 打开通达信 -> 工具 -> 条件选股 (Ctrl+T)

   - 设置选股条件并执行

   - 查看选股结果



2. 复制股票代码:

   - 在选股结果窗口，全选股票

   - 复制股票代码

   - 粘贴到本脚本的FALLBACK_STOCKS变量中



3. 配置脚本参数:

   SECTOR_CONFIG = {

       'use_sector': False,  # 禁用板块模式

   }



4. 运行脚本:

   python tools/tdx_condition_stock_trading.py



通用配置:



修改交易参数:

   TRADING_CONFIG = {

       'account_id': '你的账户ID',

       'single_stock_amount': 5000,  # 每股买入金额

       'max_stocks': 3,               # 最多买入几只

   }



查看订单:

   - 在QMT中查看"委托查询"

   - 确认订单状态

   - 可在"成交查询"中查看成交情况



常见条件选股公式:



1. MACD金叉:

   CROSS(MACD.DIF, MACD.DEA)



2. KDJ金叉:

   CROSS(KDJ.K(9,3,3), 20)



3. RSI超卖:

   RSI.RSI1(6,12,24) < 20



4. 均线多头排列:

   MA5 > MA10 > MA20 > MA60



5. 放量上涨:

   CLOSE/REF(CLOSE,1) > 1.03 AND VOL/REF(VOL,1) > 1.5



6. 横盘突破:

   CLOSE > MA(CLOSE, 60) * 1.03



风险提示:

- 建议先用模拟账号测试

- 设置合理的止损止盈

- 控制单股和总仓位

- 避免全仓追涨

- 注意交易费用

""")



logger.info(f"\n{'='*70}")
logger.info("  通达信条件选股 + EasyXT = 智能量化交易！")
logger.info('='*70)
