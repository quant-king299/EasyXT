"""
EasyXT学习实例 02 - 交易基础
学习目标：掌握基础的交易功能，包括下单、撤单、查询等
注意：本示例包含实际交易代码，请在模拟环境中运行！
"""

import sys
import os
import pandas as pd
import time
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import easy_xt

# 加载模拟数据生成器和交易功能
try:
    exec(open(os.path.join(parent_dir, 'generate_mock_data.py')).read())
    exec(open(os.path.join(parent_dir, 'mock_trade_functions.py')).read())
    mock_mode = True
    print("🔄 模拟数据和交易模式已启用")
except:
    mock_mode = False

# 配置信息（请根据实际情况修改）
USERDATA_PATH = r'D:\国金QMT交易端模拟\userdata_mini' #修改为实际的路径
ACCOUNT_ID = "39020958"  # 修改为实际账号
TEST_CODE = "000001.SZ"  # 测试用股票代码

def lesson_01_trade_setup():
    """第1课：交易服务初始化"""
    print("=" * 60)
    print("第1课：交易服务初始化")
    print("=" * 60)
    
    # 1. 创建API实例
    print("1. 创建API实例")
    api = easy_xt.get_api()
    print("✓ API实例创建成功")
    
    # 2. 初始化数据服务
    print("\n2. 初始化数据服务")
    try:
        success = api.init_data()
        if success:
            print("✓ 数据服务初始化成功")
        else:
            if mock_mode:
                print("⚠️ 数据服务初始化失败，切换到模拟模式")
                success = True
            else:
                print("✗ 数据服务初始化失败")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 数据服务初始化异常: {e}")
            print("🔄 切换到模拟模式继续学习")
            success = True
        else:
            print(f"✗ 数据服务初始化异常: {e}")
            return None
    
    # 3. 初始化交易服务
    print("\n3. 初始化交易服务")
    print(f"使用路径: {USERDATA_PATH}")
    try:
        success = api.init_trade(USERDATA_PATH, 'learning_session')
        if success:
            print("✓ 交易服务初始化成功")
        else:
            if mock_mode:
                print("⚠️ 交易服务初始化失败，切换到模拟模式")
                success = api.mock_init_trade(USERDATA_PATH, 'learning_session')
                print("✓ 模拟交易服务初始化成功")
            else:
                print("✗ 交易服务初始化失败")
                print("请检查：")
                print("- 迅投客户端是否启动并登录")
                print("- userdata路径是否正确")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 交易服务初始化异常: {e}")
            print("🔄 切换到模拟交易模式")
            success = api.mock_init_trade(USERDATA_PATH, 'learning_session')
            print("✓ 模拟交易服务初始化成功")
        else:
            print(f"✗ 交易服务初始化异常: {e}")
            return None
    
    # 4. 添加交易账户
    print(f"\n4. 添加交易账户: {ACCOUNT_ID}")
    try:
        success = api.add_account(ACCOUNT_ID, 'STOCK')
        if success:
            print("✓ 交易账户添加成功")
        else:
            if mock_mode:
                print("⚠️ 交易账户添加失败，切换到模拟模式")
                success = api.mock_add_account(ACCOUNT_ID, 'STOCK')
                print("✓ 模拟交易账户添加成功")
            else:
                print("✗ 交易账户添加失败")
                print("请检查账户信息是否正确")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 添加交易账户异常: {e}")
            print("🔄 切换到模拟账户模式")
            success = api.mock_add_account(ACCOUNT_ID, 'STOCK')
            print("✓ 模拟交易账户添加成功")
        else:
            print(f"✗ 添加交易账户异常: {e}")
            return None
    
    return api

def lesson_02_account_info(api):
    """第2课：查询账户信息"""
    print("\n" + "=" * 60)
    print("第2课：查询账户信息")
    print("=" * 60)
    
    # 1. 查询账户资产
    print("1. 查询账户资产")
    try:
        asset = api.get_account_asset(ACCOUNT_ID)
        if asset:
            print("✓ 账户资产查询成功")
            print(f"总资产: {asset.get('total_asset', 0):,.2f}")
            print(f"可用资金: {asset.get('cash', 0):,.2f}")
            print(f"冻结资金: {asset.get('frozen_cash', 0):,.2f}")
            print(f"持仓市值: {asset.get('market_value', 0):,.2f}")
        else:
            print("✗ 账户资产查询失败")
    except Exception as e:
        print(f"✗ 查询账户资产异常: {e}")
    
    # 2. 查询持仓信息
    print("\n2. 查询持仓信息")
    try:
        positions = api.get_positions(ACCOUNT_ID)
        if not positions.empty:
            print("✓ 持仓信息查询成功")
            print(f"持仓股票数量: {len(positions)}")
            print("持仓详情:")
            print(positions[['code', 'volume', 'can_use_volume', 'market_value']].to_string())
        else:
            print("✓ 持仓信息查询成功（无持仓）")
    except Exception as e:
        print(f"✗ 查询持仓信息异常: {e}")
    
    # 3. 查询当日委托
    print("\n3. 查询当日委托")
    try:
        orders = api.get_orders(ACCOUNT_ID)
        if not orders.empty:
            print("✓ 委托信息查询成功")
            print(f"当日委托数量: {len(orders)}")
            print("委托详情:")
            # 检查实际可用的字段
            available_columns = ['code', 'order_type', 'volume', 'status']
            display_columns = [col for col in available_columns if col in orders.columns]
            if display_columns:
                print(orders[display_columns].to_string())
            else:
                print("委托信息字段:")
                print(orders.columns.tolist())
                print(orders.to_string())
        else:
            print("✓ 委托信息查询成功（无委托）")
    except Exception as e:
        print(f"✗ 查询委托信息异常: {e}")
    
    print("第3课委托查询完成，准备进入第4课...")
    print("\n准备查询当日成交...")
    # 4. 查询当日成交
    print("\n4. 查询当日成交")
    try:
        print("正在查询成交信息...")
        trades = api.get_trades(ACCOUNT_ID)
        print("成交信息查询完成")
        
        if not trades.empty:
            print("✓ 成交信息查询成功")
            print(f"当日成交数量: {len(trades)}")
            print("成交详情:")
            # 检查实际可用的字段
            available_columns = ['code', 'volume', 'price', 'time']
            display_columns = [col for col in available_columns if col in trades.columns]
            if display_columns:
                print(trades[display_columns].to_string())
            else:
                print("成交信息字段:")
                print(trades.columns.tolist())
                print(trades.to_string())
        else:
            print("✓ 成交信息查询成功（无成交）")
    except Exception as e:
        print(f"✗ 查询成交信息异常: {e}")
        import traceback
        traceback.print_exc()

def lesson_03_market_order(api):
    """第3课：市价单交易"""
    print("\n" + "=" * 60)
    print("第3课：市价单交易")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    print("请确保在模拟环境中运行，或者注释掉实际交易代码")
    
    confirm = input("是否继续执行市价单交易？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过市价单交易")
        return
    
    # 1. 获取当前价格
    print(f"\n1. 获取 {TEST_CODE} 当前价格")
    try:
        current = api.get_current_price(TEST_CODE)
        if not current.empty:
            current_price = current.iloc[0]['price']
            print(f"✓ 当前价格: {current_price:.2f}")
        else:
            print("✗ 无法获取当前价格")
            return
    except Exception as e:
        print(f"✗ 获取当前价格异常: {e}")
        return
    
    # 2. 市价买入
    print(f"\n2. 市价买入 {TEST_CODE} 100股")
    try:
        order_id = api.buy(
            account_id=ACCOUNT_ID,
            code=TEST_CODE,
            volume=100,
            price=0,  # 市价单价格为0
            price_type='market'
        )
        
        if order_id:
            print(f"✓ 市价买入委托成功，委托编号: {order_id}")
            
            # 等待一段时间查看委托状态
            print("等待3秒查看委托状态...")
            time.sleep(3)
            
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                order_info = orders[orders['order_id'] == order_id]
                if not order_info.empty:
                    status = order_info.iloc[0]['status']
                    print(f"委托状态: {status}")
        else:
            print("✗ 市价买入委托失败")
    except Exception as e:
        print(f"✗ 市价买入异常: {e}")
    
    # 3. 检查持仓情况（T+1交易制度说明）
    print(f"\n3. 检查是否有 {TEST_CODE} 持仓")
    try:
        positions = api.get_positions(ACCOUNT_ID, TEST_CODE)
        if not positions.empty:
            total_volume = positions.iloc[0]['volume']  # 总持仓
            available_volume = positions.iloc[0]['can_use_volume']  # 可用持仓
            
            print(f"总持仓: {total_volume}股")
            print(f"可用持仓: {available_volume}股")
            
            if available_volume >= 100:
                print("可用持仓充足，尝试市价卖出100股")
                order_id = api.sell(
                    account_id=ACCOUNT_ID,
                    code=TEST_CODE,
                    volume=100,
                    price=0,
                    price_type='market'
                )
                
                if order_id:
                    print(f"✓ 市价卖出委托成功，委托编号: {order_id}")
                else:
                    print("✗ 市价卖出委托失败")
            else:
                print("💡 T+1交易制度说明：")
                print("   - 当天买入的股票需要第二天才能卖出")
                print("   - 可用持仓为0是正常现象")
                print("   - 总持仓显示实际拥有的股票数量")
                print("   跳过卖出操作")
        else:
            print("无持仓，跳过卖出")
    except Exception as e:
        print(f"✗ 查询持仓异常: {e}")

def lesson_04_limit_order(api):
    """第4课：限价单交易"""
    print("\n" + "=" * 60)
    print("第4课：限价单交易")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行限价单交易？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过限价单交易")
        return
    
    # 1. 获取当前价格
    print(f"\n1. 获取 {TEST_CODE} 当前价格")
    try:
        current = api.get_current_price(TEST_CODE)
        if not current.empty:
            current_price = current.iloc[0]['price']
            print(f"✓ 当前价格: {current_price:.2f}")
        else:
            print("✗ 无法获取当前价格")
            return
    except Exception as e:
        print(f"✗ 获取当前价格异常: {e}")
        return
    
    # 2. 限价买入（价格略低于当前价）
    buy_price = round(current_price * 0.99, 2)  # 比当前价低1%
    print(f"\n2. 限价买入 {TEST_CODE} 100股，价格: {buy_price}")
    
    try:
        order_id = api.buy(
            account_id=ACCOUNT_ID,
            code=TEST_CODE,
            volume=100,
            price=buy_price,
            price_type='limit'
        )
        
        if order_id:
            print(f"✓ 限价买入委托成功，委托编号: {order_id}")
            
            # 等待查看委托状态
            time.sleep(2)
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                order_info = orders[orders['order_id'] == order_id]
                if not order_info.empty:
                    status = order_info.iloc[0]['status']
                    print(f"委托状态: {status}")
            
            # 演示撤单
            print(f"\n3. 撤销委托 {order_id}")
            cancel_result = api.cancel_order(ACCOUNT_ID, order_id)
            if cancel_result:
                print("✓ 撤单成功")
            else:
                print("✗ 撤单失败（可能已成交或已撤销）")
        else:
            print("✗ 限价买入委托失败")
    except Exception as e:
        print(f"✗ 限价买入异常: {e}")
    
    # 4. 限价卖出（如果有持仓）
    print(f"\n4. 检查持仓并尝试限价卖出")
    try:
        positions = api.get_positions(ACCOUNT_ID, TEST_CODE)
        if not positions.empty:
            available_volume = positions.iloc[0]['can_use_volume']
            if available_volume >= 100:
                sell_price = round(current_price * 1.01, 2)  # 比当前价高1%
                print(f"限价卖出100股，价格: {sell_price}")
                
                order_id = api.sell(
                    account_id=ACCOUNT_ID,
                    code=TEST_CODE,
                    volume=100,
                    price=sell_price,
                    price_type='limit'
                )
                
                if order_id:
                    print(f"✓ 限价卖出委托成功，委托编号: {order_id}")
                    
                    # 立即撤单（演示用）
                    time.sleep(1)
                    print("立即撤销该委托（演示用）")
                    cancel_result = api.cancel_order(ACCOUNT_ID, order_id)
                    if cancel_result:
                        print("✓ 撤单成功")
                else:
                    print("✗ 限价卖出委托失败")
            else:
                print(f"可用持仓不足: {available_volume}股")
        else:
            print("无持仓，跳过卖出")
    except Exception as e:
        print(f"✗ 限价卖出异常: {e}")

def lesson_05_quick_buy(api):
    """第5课：便捷买入功能"""
    print("\n" + "=" * 60)
    print("第5课：便捷买入功能")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行便捷买入？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过便捷买入")
        return
    
    # 1. 按金额买入
    buy_amount = 10000  # 买入10000元
    print(f"\n1. 按金额买入 {TEST_CODE}，金额: {buy_amount}元")
"""
EasyXT学习实例 02 - 交易基础
学习目标：掌握基础的交易功能，包括下单、撤单、查询等
注意：本示例包含实际交易代码，请在模拟环境中运行！
"""

import sys
import os
import pandas as pd
import time
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import easy_xt

# 加载模拟数据生成器和交易功能
try:
    exec(open(os.path.join(parent_dir, 'generate_mock_data.py')).read())
    exec(open(os.path.join(parent_dir, 'mock_trade_functions.py')).read())
    mock_mode = True
    print("🔄 模拟数据和交易模式已启用")
except:
    mock_mode = False

# 配置信息（请根据实际情况修改）
USERDATA_PATH = r'D:\国金QMT交易端模拟\userdata_mini' #修改为实际的路径
ACCOUNT_ID = "39020958"  # 修改为实际账号
TEST_CODE = "000001.SZ"  # 测试用股票代码

def lesson_01_trade_setup():
    """第1课：交易服务初始化"""
    print("=" * 60)
    print("第1课：交易服务初始化")
    print("=" * 60)
    
    # 1. 创建API实例
    print("1. 创建API实例")
    api = easy_xt.get_api()
    print("✓ API实例创建成功")
    
    # 2. 初始化数据服务
    print("\n2. 初始化数据服务")
    try:
        success = api.init_data()
        if success:
            print("✓ 数据服务初始化成功")
        else:
            if mock_mode:
                print("⚠️ 数据服务初始化失败，切换到模拟模式")
                success = True
            else:
                print("✗ 数据服务初始化失败")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 数据服务初始化异常: {e}")
            print("🔄 切换到模拟模式继续学习")
            success = True
        else:
            print(f"✗ 数据服务初始化异常: {e}")
            return None
    
    # 3. 初始化交易服务
    print("\n3. 初始化交易服务")
    print(f"使用路径: {USERDATA_PATH}")
    try:
        success = api.init_trade(USERDATA_PATH, 'learning_session')
        if success:
            print("✓ 交易服务初始化成功")
        else:
            if mock_mode:
                print("⚠️ 交易服务初始化失败，切换到模拟模式")
                success = api.mock_init_trade(USERDATA_PATH, 'learning_session')
                print("✓ 模拟交易服务初始化成功")
            else:
                print("✗ 交易服务初始化失败")
                print("请检查：")
                print("- 迅投客户端是否启动并登录")
                print("- userdata路径是否正确")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 交易服务初始化异常: {e}")
            print("🔄 切换到模拟交易模式")
            success = api.mock_init_trade(USERDATA_PATH, 'learning_session')
            print("✓ 模拟交易服务初始化成功")
        else:
            print(f"✗ 交易服务初始化异常: {e}")
            return None
    
    # 4. 添加交易账户
    print(f"\n4. 添加交易账户: {ACCOUNT_ID}")
    try:
        success = api.add_account(ACCOUNT_ID, 'STOCK')
        if success:
            print("✓ 交易账户添加成功")
        else:
            if mock_mode:
                print("⚠️ 交易账户添加失败，切换到模拟模式")
                success = api.mock_add_account(ACCOUNT_ID, 'STOCK')
                print("✓ 模拟交易账户添加成功")
            else:
                print("✗ 交易账户添加失败")
                print("请检查账户信息是否正确")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 添加交易账户异常: {e}")
            print("🔄 切换到模拟账户模式")
            success = api.mock_add_account(ACCOUNT_ID, 'STOCK')
            print("✓ 模拟交易账户添加成功")
        else:
            print(f"✗ 添加交易账户异常: {e}")
            return None
    
    return api

def lesson_02_account_info(api):
    """第2课：查询账户信息"""
    print("\n" + "=" * 60)
    print("第2课：查询账户信息")
    print("=" * 60)
    
    # 1. 查询账户资产
    print("1. 查询账户资产")
    try:
        asset = api.get_account_asset(ACCOUNT_ID)
        if asset:
            print("✓ 账户资产查询成功")
            print(f"总资产: {asset.get('total_asset', 0):,.2f}")
            print(f"可用资金: {asset.get('cash', 0):,.2f}")
            print(f"冻结资金: {asset.get('frozen_cash', 0):,.2f}")
            print(f"持仓市值: {asset.get('market_value', 0):,.2f}")
        else:
            print("✗ 账户资产查询失败")
    except Exception as e:
        print(f"✗ 查询账户资产异常: {e}")
    
    # 2. 查询持仓信息
    print("\n2. 查询持仓信息")
    try:
        positions = api.get_positions(ACCOUNT_ID)
        if not positions.empty:
            print("✓ 持仓信息查询成功")
            print(f"持仓股票数量: {len(positions)}")
            print("持仓详情:")
            print(positions[['code', 'volume', 'can_use_volume', 'market_value']].to_string())
        else:
            print("✓ 持仓信息查询成功（无持仓）")
    except Exception as e:
        print(f"✗ 查询持仓信息异常: {e}")
    
    # 3. 查询当日委托
    print("\n3. 查询当日委托")
    try:
        orders = api.get_orders(ACCOUNT_ID)
        if not orders.empty:
            print("✓ 委托信息查询成功")
            print(f"当日委托数量: {len(orders)}")
            print("委托详情:")
            # 检查实际可用的字段
            available_columns = ['code', 'order_type', 'volume', 'status']
            display_columns = [col for col in available_columns if col in orders.columns]
            if display_columns:
                print(orders[display_columns].to_string())
            else:
                print("委托信息字段:")
                print(orders.columns.tolist())
                print(orders.to_string())
        else:
            print("✓ 委托信息查询成功（无委托）")
    except Exception as e:
        print(f"✗ 查询委托信息异常: {e}")
    
    # 4. 查询当日成交
    print("\n4. 查询当日成交")
    try:
        trades = api.get_trades(ACCOUNT_ID)
        if not trades.empty:
            print("✓ 成交信息查询成功")
            print(f"当日成交数量: {len(trades)}")
            print("成交详情:")
            # 显示成交记录，使用您提供的字段格式
            print("code      order_type  volume status")
            for i, trade in trades.iterrows():
                code = trade.get('code', trade.get('stock_code', 'N/A'))
                order_type = trade.get('order_type', '买入')  # 默认显示买入
                volume = trade.get('volume', trade.get('traded_volume', 0))
                status = trade.get('status', '已成')  # 成交记录默认为已成
                print(f"{i}  {code:<12} {order_type:<8} {volume:<6} {status}")
        else:
            print("✓ 查询当日成交：查不到成交记录，跳出查询")
            return  # 查不到就跳出查询
    except Exception as e:
        print(f"✗ 查询成交信息异常: {e}")
        print("查询失败，跳出查询")
        return  # 异常时也跳出查询

def lesson_03_market_order(api):
    """第3课：市价单交易"""
    print("\n" + "=" * 60)
    print("第3课：市价单交易")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    print("请确保在模拟环境中运行，或者注释掉实际交易代码")
    
    confirm = input("是否继续执行市价单交易？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过市价单交易")
        return
    
    # 1. 获取当前价格
    print(f"\n1. 获取 {TEST_CODE} 当前价格")
    try:
        current = api.get_current_price(TEST_CODE)
        if not current.empty:
            current_price = current.iloc[0]['price']
            print(f"✓ 当前价格: {current_price:.2f}")
        else:
            print("✗ 无法获取当前价格")
            return
    except Exception as e:
        print(f"✗ 获取当前价格异常: {e}")
        return
    
    # 2. 市价买入
    print(f"\n2. 市价买入 {TEST_CODE} 100股")
    try:
        order_id = api.buy(
            account_id=ACCOUNT_ID,
            code=TEST_CODE,
            volume=100,
            price=0,  # 市价单价格为0
            price_type='market'
        )
        
        if order_id:
            print(f"✓ 市价买入委托成功，委托编号: {order_id}")
            
            # 等待一段时间查看委托状态
            print("等待3秒查看委托状态...")
            time.sleep(3)
            
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                order_info = orders[orders['order_id'] == order_id]
                if not order_info.empty:
                    status = order_info.iloc[0]['order_status']
                    print(f"委托状态: {status}")
        else:
            print("✗ 市价买入委托失败")
    except Exception as e:
        print(f"✗ 市价买入异常: {e}")
    
    # 3. 检查持仓情况（T+1交易制度说明）
    print(f"\n3. 检查是否有 {TEST_CODE} 持仓")
    try:
        positions = api.get_positions(ACCOUNT_ID, TEST_CODE)
        if not positions.empty:
            total_volume = positions.iloc[0]['volume']  # 总持仓
            available_volume = positions.iloc[0]['can_use_volume']  # 可用持仓
            
            print(f"总持仓: {total_volume}股")
            print(f"可用持仓: {available_volume}股")
            
            if available_volume >= 100:
                print("可用持仓充足，尝试市价卖出100股")
                order_id = api.sell(
                    account_id=ACCOUNT_ID,
                    code=TEST_CODE,
                    volume=100,
                    price=0,
                    price_type='market'
                )
                
                if order_id:
                    print(f"✓ 市价卖出委托成功，委托编号: {order_id}")
                else:
                    print("✗ 市价卖出委托失败")
            else:
                print("💡 T+1交易制度说明：")
                print("   - 当天买入的股票需要第二天才能卖出")
                print("   - 可用持仓为0是正常现象")
                print("   - 总持仓显示实际拥有的股票数量")
                print("   跳过卖出操作")
        else:
            print("无持仓，跳过卖出")
    except Exception as e:
        print(f"✗ 查询持仓异常: {e}")

def lesson_04_limit_order(api):
    """第4课：限价单交易"""
    print("\n" + "=" * 60)
    print("第4课：限价单交易")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行限价单交易？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过限价单交易")
        return
    
    # 1. 获取当前价格
    print(f"\n1. 获取 {TEST_CODE} 当前价格")
    try:
        current = api.get_current_price(TEST_CODE)
        if not current.empty:
            current_price = current.iloc[0]['price']
            print(f"✓ 当前价格: {current_price:.2f}")
        else:
            print("✗ 无法获取当前价格")
            return
    except Exception as e:
        print(f"✗ 获取当前价格异常: {e}")
        return
    
    # 2. 限价买入（价格略低于当前价）
    buy_price = round(current_price * 0.99, 2)  # 比当前价低1%
    print(f"\n2. 限价买入 {TEST_CODE} 100股，价格: {buy_price}")
    
    try:
        order_id = api.buy(
            account_id=ACCOUNT_ID,
            code=TEST_CODE,
            volume=100,
            price=buy_price,
            price_type='limit'
        )
        
        if order_id:
            print(f"✓ 限价买入委托成功，委托编号: {order_id}")
            
            # 等待查看委托状态
            time.sleep(2)
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                order_info = orders[orders['order_id'] == order_id]
                if not order_info.empty:
                    status = order_info.iloc[0]['order_status']
                    print(f"委托状态: {status}")
            
            # 演示撤单
            print(f"\n3. 撤销委托 {order_id}")
            cancel_result = api.cancel_order(ACCOUNT_ID, order_id)
            if cancel_result:
                print("✓ 撤单成功")
            else:
                print("✗ 撤单失败（可能已成交或已撤销）")
        else:
            print("✗ 限价买入委托失败")
    except Exception as e:
        print(f"✗ 限价买入异常: {e}")
    
    # 4. 限价卖出（如果有持仓）
    print(f"\n4. 检查持仓并尝试限价卖出")
    try:
        positions = api.get_positions(ACCOUNT_ID, TEST_CODE)
        if not positions.empty:
            available_volume = positions.iloc[0]['can_use_volume']
            if available_volume >= 100:
                sell_price = round(current_price * 1.01, 2)  # 比当前价高1%
                print(f"限价卖出100股，价格: {sell_price}")
                
                order_id = api.sell(
                    account_id=ACCOUNT_ID,
                    code=TEST_CODE,
                    volume=100,
                    price=sell_price,
                    price_type='limit'
                )
                
                if order_id:
                    print(f"✓ 限价卖出委托成功，委托编号: {order_id}")
                    
                    # 立即撤单（演示用）
                    time.sleep(1)
                    print("立即撤销该委托（演示用）")
                    cancel_result = api.cancel_order(ACCOUNT_ID, order_id)
                    if cancel_result:
                        print("✓ 撤单成功")
                else:
                    print("✗ 限价卖出委托失败")
            else:
                print(f"可用持仓不足: {available_volume}股")
        else:
            print("无持仓，跳过卖出")
    except Exception as e:
        print(f"✗ 限价卖出异常: {e}")

def lesson_05_quick_buy(api):
    """第5课：便捷买入功能"""
    print("\n" + "=" * 60)
    print("第5课：便捷买入功能")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行便捷买入？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过便捷买入")
        return
    
"""
EasyXT学习实例 02 - 交易基础
学习目标：掌握基础的交易功能，包括下单、撤单、查询等
注意：本示例包含实际交易代码，请在模拟环境中运行！
"""

import sys
import os
import pandas as pd
import time
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import easy_xt

# 加载模拟数据生成器和交易功能
try:
    exec(open(os.path.join(parent_dir, 'generate_mock_data.py')).read())
    exec(open(os.path.join(parent_dir, 'mock_trade_functions.py')).read())
    mock_mode = True
    print("🔄 模拟数据和交易模式已启用")
except:
    mock_mode = False

# 配置信息（请根据实际情况修改）
USERDATA_PATH = r'D:\国金QMT交易端模拟\userdata_mini' #修改为实际的路径
ACCOUNT_ID = "39020958"  # 修改为实际账号
TEST_CODE = "000001.SZ"  # 测试用股票代码

def lesson_01_trade_setup():
    """第1课：交易服务初始化"""
    print("=" * 60)
    print("第1课：交易服务初始化")
    print("=" * 60)
    
    # 1. 创建API实例
    print("1. 创建API实例")
    api = easy_xt.get_api()
    print("✓ API实例创建成功")
    
    # 2. 初始化数据服务
    print("\n2. 初始化数据服务")
    try:
        success = api.init_data()
        if success:
            print("✓ 数据服务初始化成功")
        else:
            if mock_mode:
                print("⚠️ 数据服务初始化失败，切换到模拟模式")
                success = True
            else:
                print("✗ 数据服务初始化失败")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 数据服务初始化异常: {e}")
            print("🔄 切换到模拟模式继续学习")
            success = True
        else:
            print(f"✗ 数据服务初始化异常: {e}")
            return None
    
    # 3. 初始化交易服务
    print("\n3. 初始化交易服务")
    print(f"使用路径: {USERDATA_PATH}")
    try:
        success = api.init_trade(USERDATA_PATH, 'learning_session')
        if success:
            print("✓ 交易服务初始化成功")
        else:
            if mock_mode:
                print("⚠️ 交易服务初始化失败，切换到模拟模式")
                success = api.mock_init_trade(USERDATA_PATH, 'learning_session')
                print("✓ 模拟交易服务初始化成功")
            else:
                print("✗ 交易服务初始化失败")
                print("请检查：")
                print("- 迅投客户端是否启动并登录")
                print("- userdata路径是否正确")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 交易服务初始化异常: {e}")
            print("🔄 切换到模拟交易模式")
            success = api.mock_init_trade(USERDATA_PATH, 'learning_session')
            print("✓ 模拟交易服务初始化成功")
        else:
            print(f"✗ 交易服务初始化异常: {e}")
            return None
    
    # 4. 添加交易账户
    print(f"\n4. 添加交易账户: {ACCOUNT_ID}")
    try:
        success = api.add_account(ACCOUNT_ID, 'STOCK')
        if success:
            print("✓ 交易账户添加成功")
        else:
            if mock_mode:
                print("⚠️ 交易账户添加失败，切换到模拟模式")
                success = api.mock_add_account(ACCOUNT_ID, 'STOCK')
                print("✓ 模拟交易账户添加成功")
            else:
                print("✗ 交易账户添加失败")
                print("请检查账户信息是否正确")
                return None
    except Exception as e:
        if mock_mode:
            print(f"⚠️ 添加交易账户异常: {e}")
            print("🔄 切换到模拟账户模式")
            success = api.mock_add_account(ACCOUNT_ID, 'STOCK')
            print("✓ 模拟交易账户添加成功")
        else:
            print(f"✗ 添加交易账户异常: {e}")
            return None
    
    return api

def lesson_02_account_info(api):
    """第2课：查询账户信息"""
    print("\n" + "=" * 60)
    print("第2课：查询账户信息")
    print("=" * 60)
    
    # 1. 查询账户资产
    print("1. 查询账户资产")
    try:
        asset = api.get_account_asset(ACCOUNT_ID)
        if asset:
            print("✓ 账户资产查询成功")
            print(f"总资产: {asset.get('total_asset', 0):,.2f}")
            print(f"可用资金: {asset.get('cash', 0):,.2f}")
            print(f"冻结资金: {asset.get('frozen_cash', 0):,.2f}")
            print(f"持仓市值: {asset.get('market_value', 0):,.2f}")
        else:
            print("✗ 账户资产查询失败")
    except Exception as e:
        print(f"✗ 查询账户资产异常: {e}")
    
    # 2. 查询持仓信息
    print("\n2. 查询持仓信息")
    try:
        positions = api.get_positions(ACCOUNT_ID)
        if not positions.empty:
            print("✓ 持仓信息查询成功")
            print(f"持仓股票数量: {len(positions)}")
            print("持仓详情:")
            print(positions[['code', 'volume', 'can_use_volume', 'market_value']].to_string())
        else:
            print("✓ 持仓信息查询成功（无持仓）")
    except Exception as e:
        print(f"✗ 查询持仓信息异常: {e}")
    
    # 3. 查询当日委托
    print("\n3. 查询当日委托")
    try:
        orders = api.get_orders(ACCOUNT_ID)
        if not orders.empty:
            print("✓ 委托信息查询成功")
            print(f"当日委托数量: {len(orders)}")
            print("委托详情:")
            # 检查实际可用的字段
            available_columns = ['code', 'order_type', 'volume', 'status']
            display_columns = [col for col in available_columns if col in orders.columns]
            if display_columns:
                print(orders[display_columns].to_string())
            else:
                print("委托信息字段:")
                print(orders.columns.tolist())
                print(orders.to_string())
        else:
            print("✓ 委托信息查询成功（无委托）")
    except Exception as e:
        print(f"✗ 查询委托信息异常: {e}")
    
    # 4. 查询当日成交
    print("\n4. 查询当日成交")
    try:
        trades = api.get_trades(ACCOUNT_ID)
        if not trades.empty:
            print("✓ 成交信息查询成功")
            print(f"当日成交数量: {len(trades)}")
            print("成交详情:")
            print(trades[['stock_code', 'traded_volume', 'traded_price', 'traded_time']].to_string())
        else:
            print("✓ 成交信息查询成功（无成交）")
    except Exception as e:
        print(f"✗ 查询成交信息异常: {e}")

def lesson_03_market_order(api):
    """第3课：市价单交易"""
    print("\n" + "=" * 60)
    print("第3课：市价单交易")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    print("请确保在模拟环境中运行，或者注释掉实际交易代码")
    
    confirm = input("是否继续执行市价单交易？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过市价单交易")
        return
    
    # 1. 获取当前价格
    print(f"\n1. 获取 {TEST_CODE} 当前价格")
    try:
        current = api.get_current_price(TEST_CODE)
        if not current.empty:
            current_price = current.iloc[0]['price']
            print(f"✓ 当前价格: {current_price:.2f}")
        else:
            print("✗ 无法获取当前价格")
            return
    except Exception as e:
        print(f"✗ 获取当前价格异常: {e}")
        return
    
    # 2. 市价买入
    print(f"\n2. 市价买入 {TEST_CODE} 100股")
    try:
        order_id = api.buy(
            account_id=ACCOUNT_ID,
            code=TEST_CODE,
            volume=100,
            price=0,  # 市价单价格为0
            price_type='market'
        )
        
        if order_id:
            print(f"✓ 市价买入委托成功，委托编号: {order_id}")
            
            # 等待一段时间查看委托状态
            print("等待3秒查看委托状态...")
            time.sleep(3)
            
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                order_info = orders[orders['order_id'] == order_id]
                if not order_info.empty:
                    status = order_info.iloc[0]['order_status']
                    print(f"委托状态: {status}")
        else:
            print("✗ 市价买入委托失败")
    except Exception as e:
        print(f"✗ 市价买入异常: {e}")
    
    # 3. 检查持仓情况（T+1交易制度说明）
    print(f"\n3. 检查是否有 {TEST_CODE} 持仓")
    try:
        positions = api.get_positions(ACCOUNT_ID, TEST_CODE)
        if not positions.empty:
            total_volume = positions.iloc[0]['volume']  # 总持仓
            available_volume = positions.iloc[0]['can_use_volume']  # 可用持仓
            
            print(f"总持仓: {total_volume}股")
            print(f"可用持仓: {available_volume}股")
            
            if available_volume >= 100:
                print("可用持仓充足，尝试市价卖出100股")
                order_id = api.sell(
                    account_id=ACCOUNT_ID,
                    code=TEST_CODE,
                    volume=100,
                    price=0,
                    price_type='market'
                )
                
                if order_id:
                    print(f"✓ 市价卖出委托成功，委托编号: {order_id}")
                else:
                    print("✗ 市价卖出委托失败")
            else:
                print("💡 T+1交易制度说明：")
                print("   - 当天买入的股票需要第二天才能卖出")
                print("   - 可用持仓为0是正常现象")
                print("   - 总持仓显示实际拥有的股票数量")
                print("   跳过卖出操作")
        else:
            print("无持仓，跳过卖出")
    except Exception as e:
        print(f"✗ 查询持仓异常: {e}")

def lesson_04_limit_order(api):
    """第4课：限价单交易"""
    print("\n" + "=" * 60)
    print("第4课：限价单交易")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行限价单交易？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过限价单交易")
        return
    
    # 1. 获取当前价格
    print(f"\n1. 获取 {TEST_CODE} 当前价格")
    try:
        current = api.get_current_price(TEST_CODE)
        if not current.empty:
            current_price = current.iloc[0]['price']
            print(f"✓ 当前价格: {current_price:.2f}")
        else:
            print("✗ 无法获取当前价格")
            return
    except Exception as e:
        print(f"✗ 获取当前价格异常: {e}")
        return
    
    # 2. 限价买入（价格略低于当前价）
    buy_price = round(current_price * 0.99, 2)  # 比当前价低1%
    print(f"\n2. 限价买入 {TEST_CODE} 100股，价格: {buy_price}")
    
    try:
        order_id = api.buy(
            account_id=ACCOUNT_ID,
            code=TEST_CODE,
            volume=100,
            price=buy_price,
            price_type='limit'
        )
        
        if order_id:
            print(f"✓ 限价买入委托成功，委托编号: {order_id}")
            
            # 等待查看委托状态
            time.sleep(2)
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                order_info = orders[orders['order_id'] == order_id]
                if not order_info.empty:
                    status = order_info.iloc[0]['order_status']
                    print(f"委托状态: {status}")
            
            # 演示撤单
            print(f"\n3. 撤销委托 {order_id}")
            cancel_result = api.cancel_order(ACCOUNT_ID, order_id)
            if cancel_result:
                print("✓ 撤单成功")
            else:
                print("✗ 撤单失败（可能已成交或已撤销）")
        else:
            print("✗ 限价买入委托失败")
    except Exception as e:
        print(f"✗ 限价买入异常: {e}")
    
    # 4. 限价卖出（如果有持仓）
    print(f"\n4. 检查持仓并尝试限价卖出")
    try:
        positions = api.get_positions(ACCOUNT_ID, TEST_CODE)
        if not positions.empty:
            available_volume = positions.iloc[0]['can_use_volume']
            if available_volume >= 100:
                sell_price = round(current_price * 1.01, 2)  # 比当前价高1%
                print(f"限价卖出100股，价格: {sell_price}")
                
                order_id = api.sell(
                    account_id=ACCOUNT_ID,
                    code=TEST_CODE,
                    volume=100,
                    price=sell_price,
                    price_type='limit'
                )
                
                if order_id:
                    print(f"✓ 限价卖出委托成功，委托编号: {order_id}")
                    
                    # 立即撤单（演示用）
                    time.sleep(1)
                    print("立即撤销该委托（演示用）")
                    cancel_result = api.cancel_order(ACCOUNT_ID, order_id)
                    if cancel_result:
                        print("✓ 撤单成功")
                else:
                    print("✗ 限价卖出委托失败")
            else:
                print(f"可用持仓不足: {available_volume}股")
        else:
            print("无持仓，跳过卖出")
    except Exception as e:
        print(f"✗ 限价卖出异常: {e}")

def lesson_05_quick_buy(api):
    """第5课：便捷买入功能"""
    print("\n" + "=" * 60)
    print("第5课：便捷买入功能")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行便捷买入？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过便捷买入")
        return

    # 先获取当前价格，计算合适的买入金额
    print(f"\n正在获取 {TEST_CODE} 的当前价格...")
    try:
        price_data = api.get_current_price(TEST_CODE)
        if not price_data.empty:
            current_price = price_data.iloc[0]['price']
            print(f"当前价格: {current_price:.2f} 元/股")

            # 计算买入1手（100股）需要的金额
            min_amount = current_price * 100
            print(f"买入1手(100股)最少需要: {min_amount:.2f} 元")

            # 建议金额（向上取整到100的倍数）
            suggested_amount = int(min_amount / 100) * 100 + 200
            print(f"建议买入金额: {suggested_amount} 元（可买{int(suggested_amount/current_price/100)*100}股）")

            # 让用户确认或输入金额
            user_input = input(f"\n请输入买入金额（直接回车使用建议金额 {suggested_amount} 元）: ").strip()
            if user_input:
                buy_amount = float(user_input)
            else:
                buy_amount = suggested_amount

            print(f"使用买入金额: {buy_amount} 元")
        else:
            print("⚠️ 无法获取当前价格，使用默认金额")
            buy_amount = 1000
    except Exception as e:
        print(f"⚠️ 获取价格失败: {e}，使用默认金额")
        buy_amount = 1000

    print(f"\n1. 按金额买入 {TEST_CODE}，金额: {buy_amount}元")
    
    try:
        order_id = api.quick_buy(
            account_id=ACCOUNT_ID,
            code=TEST_CODE,
            amount=buy_amount,
            price_type='market'
        )
        
        if order_id:
            print(f"✓ 按金额买入成功，委托编号: {order_id}")
            
            # 查看委托详情
            time.sleep(2)
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                order_info = orders[orders['order_id'] == order_id]
                if not order_info.empty:
                    volume = order_info.iloc[0]['volume']
                    price = order_info.iloc[0]['price']
                    print(f"委托数量: {volume}股")
                    print(f"委托价格: {price:.2f}")
        else:
            print("✗ 按金额买入失败")
    except Exception as e:
        print(f"✗ 按金额买入异常: {e}")

def lesson_06_split_order(api):
    """第6课：拆单交易实战"""
    print("\n" + "=" * 60)
    print("第6课：拆单交易实战")
    print("=" * 60)

    print("💡 拆单交易：将大额订单拆分成多个小单，降低市场冲击")
    print("适用场景：大额买入/卖出、降低滑点、提高成交概率")

    # 拆单函数（来自01_基础入门 Lesson 8）
    def split_order(volume: int, max_single_volume: int = 10000,
                   split_strategy: str = 'equal') -> list:
        """
        拆单函数

        Args:
            volume: 总数量
            max_single_volume: 单笔最大数量
            split_strategy: 拆单策略
                - 'equal': 平均拆分
                - 'decreasing': 递减拆分（大单在前）
                - 'increasing': 递增拆分（小单在前）

        Returns:
            list: 拆分后的数量列表
        """
        if volume <= max_single_volume:
            return [volume]

        num_splits = (volume + max_single_volume - 1) // max_single_volume

        if split_strategy == 'equal':
            base_volume = volume // num_splits
            remainder = volume % num_splits
            result = [base_volume + 1] * remainder + [base_volume] * (num_splits - remainder)
            return result
        elif split_strategy == 'decreasing':
            result = []
            remaining = volume
            while remaining > 0:
                current = min(max_single_volume, remaining)
                result.append(current)
                remaining -= current
            return result
        elif split_strategy == 'increasing':
            result = []
            remaining = volume
            while remaining > 0:
                current = min(max_single_volume, remaining)
                result.insert(0, current)
                remaining -= current
            return result
        else:
            return split_order(volume, max_single_volume, 'equal')

    # 拆单买入实战
    print("\n1. 拆单买入实战示例")
    print("-" * 40)

    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行拆单买入？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过拆单买入")
        return

    # 示例参数
    total_volume = 30000  # 总数量30000股
    max_single = 5000     # 单笔最大5000股
    strategy = 'equal'    # 平均拆分

    print(f"\n交易参数：")
    print(f"  股票代码: {TEST_CODE}")
    print(f"  总数量: {total_volume} 股")
    print(f"  单笔最大: {max_single} 股")
    print(f"  拆单策略: {strategy}")

    # 执行拆单
    splits = split_order(total_volume, max_single, strategy)
    print(f"\n拆分结果：")
    print(f"  拆分数: {len(splits)} 笔")
    print(f"  拆分明细: {splits}")

    # 逐笔下单
    print(f"\n开始逐笔下单...")
    order_ids = []
    success_count = 0
    fail_count = 0

    for i, volume in enumerate(splits, 1):
        print(f"\n第 {i}/{len(splits)} 笔: {volume} 股")

        try:
            # 调用买入接口
            order_id = api.buy(
                account_id=ACCOUNT_ID,
                code=TEST_CODE,
                volume=volume,
                price=0,  # 市价单
                price_type='market'
            )

            if order_id:
                order_ids.append(order_id)
                success_count += 1
                print(f"  ✓ 下单成功，委托号: {order_id}")
            else:
                fail_count += 1
                print(f"  ✗ 下单失败")

        except Exception as e:
            fail_count += 1
            print(f"  ✗ 下单异常: {e}")

        # 避免下单过快
        if i < len(splits):  # 最后一笔不需要等待
            time.sleep(0.5)

    # 统计结果
    print(f"\n拆单买入完成！")
    print(f"  成功: {success_count} 笔")
    print(f"  失败: {fail_count} 笔")
    print(f"  委托编号: {order_ids}")

    # 查询委托状态
    if order_ids:
        print(f"\n查询委托状态...")
        time.sleep(2)

        try:
            orders = api.get_orders(ACCOUNT_ID)
            if not orders.empty:
                print(f"\n委托详情：")
                for order_id in order_ids:
                    order_info = orders[orders['order_id'] == order_id]
                    if not order_info.empty:
                        status = order_info.iloc[0].get('status', '未知')
                        volume = order_info.iloc[0].get('volume', 0)
                        price = order_info.iloc[0].get('price', 0)
                        print(f"  委托 {order_id}: {status}, {volume}股, {price:.2f}元")
        except Exception as e:
            print(f"查询委托状态异常: {e}")

    # 拆单卖出示例
    print("\n\n2. 拆单卖出示例（参考）")
    print("-" * 40)

    print("拆单卖出代码示例：")
    example_code = '''
def split_and_sell(api, account_id, code, total_volume, max_single=5000):
    """拆单卖出函数"""

    # 1. 拆分订单
    splits = split_order(total_volume, max_single, 'decreasing')  # 递减拆分
    print(f"总数量: {total_volume}, 拆分为 {len(splits)} 笔")

    # 2. 逐笔下单
    order_ids = []
    for i, volume in enumerate(splits, 1):
        print(f"下单第 {i}/{len(splits)} 笔: {volume} 股")

        # 调用卖出接口
        order_id = api.sell(
            account_id=account_id,
            code=code,
            volume=volume,
            price=0,  # 市价单
            price_type='market'
        )

        if order_id:
            order_ids.append(order_id)
            print(f"  ✓ 下单成功，委托号: {order_id}")
        else:
            print(f"  ✗ 下单失败")

        # 避免下单过快
        time.sleep(0.5)

    return order_ids

# 使用示例（需要在有持仓时使用）
# order_ids = split_and_sell(api, ACCOUNT_ID, TEST_CODE, 10000, 5000)
'''
    print(example_code)

    print("\n💡 拆单交易要点：")
    print("  • 根据市场流动性选择合适的单笔数量")
    print("  • 使用市价单可提高成交概率，但可能有滑点")
    print("  • 逐笔下单之间需要适当间隔，避免被认定为异常交易")
    print("  • 建议在模拟环境中充分测试后再用于实盘")

def lesson_07_order_monitoring(api):
    """第7课：委托监控"""
    print("\n" + "=" * 60)
    print("第7课：委托监控")
    print("=" * 60)
    
    print("1. 查看所有当日委托")
    try:
        orders = api.get_orders(ACCOUNT_ID)
        if not orders.empty:
            print(f"✓ 共有 {len(orders)} 笔委托")
            print("\n委托详情:")
            for _, order in orders.iterrows():
                print(f"委托编号: {order['order_id']}")
                print(f"股票代码: {order['code']}")
                print(f"委托类型: {order['order_type']}")
                print(f"委托数量: {order['volume']}")
                print(f"委托价格: {order['price']:.2f}")
                print(f"委托状态: {order['status']}")
                print("-" * 30)
        else:
            print("✓ 当前无委托")
    except Exception as e:
        print(f"✗ 查看委托异常: {e}")
    
    # 2. 查看可撤销委托
    print("\n2. 查看可撤销委托")
    try:
        cancelable_orders = api.get_orders(ACCOUNT_ID, cancelable_only=True)
        if not cancelable_orders.empty:
            print(f"✓ 共有 {len(cancelable_orders)} 笔可撤销委托")
            for _, order in cancelable_orders.iterrows():
                print(f"可撤销委托: {order['order_id']} - {order['stock_code']}")
        else:
            print("✓ 当前无可撤销委托")
    except Exception as e:
        print(f"✗ 查看可撤销委托异常: {e}")
    
    # 3. 查看成交记录
    print("\n3. 查看成交记录")
    try:
        trades = api.get_trades(ACCOUNT_ID)
        if not trades.empty:
            print(f"✓ 共有 {len(trades)} 笔成交")
            print("\n成交详情:")
            for _, trade in trades.iterrows():
                print(f"成交编号: {trade.get('trade_id', 'N/A')}")
                print(f"股票代码: {trade.get('code', trade.get('stock_code', 'N/A'))}")
                print(f"成交数量: {trade.get('volume', trade.get('traded_volume', 'N/A'))}")
                print(f"成交价格: {trade.get('price', trade.get('traded_price', 0)):.2f}")
                print(f"成交时间: {trade.get('time', trade.get('traded_time', 'N/A'))}")
                print("-" * 30)
        else:
            print("✓ 当前无成交记录")
    except Exception as e:
        print(f"✗ 查看成交记录异常: {e}")

def lesson_08_practice_summary(api):
    """第8课：实践总结"""
    print("\n" + "=" * 60)
    print("第8课：实践总结")
    print("=" * 60)

    print("本课程学习了以下交易基础功能：")
    print("1. ✓ 交易服务初始化")
    print("2. ✓ 账户信息查询")
    print("3. ✓ 市价单交易")
    print("4. ✓ 限价单交易")
    print("5. ✓ 便捷买入功能")
    print("6. ✓ 拆单交易实战")
    print("7. ✓ 委托监控")
    
    print("\n交易基础要点总结：")
    print("• 交易前必须先初始化数据和交易服务")
    print("• 必须添加交易账户才能进行交易")
    print("• 市价单：price=0, price_type='market'")
    print("• 限价单：price=具体价格, price_type='limit'")
    print("• 可以通过get_orders()查询委托状态")
    print("• 可以通过cancel_order()撤销委托")
    print("• quick_buy()可以按金额买入股票")
    
    print("\n最终账户状态：")
    try:
        # 最终账户资产
        asset = api.get_account_asset(ACCOUNT_ID)
        if asset:
            print(f"总资产: {asset.get('total_asset', 0):,.2f}")
            print(f"可用资金: {asset.get('cash', 0):,.2f}")
        
        # 最终持仓
        positions = api.get_positions(ACCOUNT_ID)
        if not positions.empty:
            print(f"持仓股票数: {len(positions)}")
        else:
            print("持仓股票数: 0")
        
        # 当日委托统计
        orders = api.get_orders(ACCOUNT_ID)
        if not orders.empty:
            print(f"当日委托数: {len(orders)}")
        else:
            print("当日委托数: 0")
            
    except Exception as e:
        print(f"查询最终状态异常: {e}")

def main():
    """主函数：运行所有交易基础课程"""
    print("🎓 EasyXT交易基础学习课程")
    print("本课程将带您学习EasyXT的基础交易功能")
    print("\n⚠️  重要提醒：")
    print("1. 本课程包含实际交易代码，请在模拟环境中运行")
    print("2. 请修改配置信息（USERDATA_PATH和ACCOUNT_ID）")
    print("3. 确保迅投客户端已启动并登录")
    print("4. 建议先在小金额下测试")
    
    # 确认继续
    confirm = input("\n是否继续学习交易基础课程？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("学习已取消")
        return
    
    # 第1课：初始化
    api = lesson_01_trade_setup()
    if not api:
        print("初始化失败，无法继续")
        return
    
    # 运行其他课程
    lessons = [
        lambda: lesson_02_account_info(api),
        lambda: lesson_03_market_order(api),
        lambda: lesson_04_limit_order(api),
        lambda: lesson_05_quick_buy(api),
        lambda: lesson_06_split_order(api),
        lambda: lesson_07_order_monitoring(api),
        lambda: lesson_08_practice_summary(api)
    ]
    
    for i, lesson in enumerate(lessons, 2):
        try:
            lesson()
            if i < len(lessons) + 1:  # 不是最后一课
                input(f"\n按回车键继续第{i+1}课...")
        except KeyboardInterrupt:
            print("\n\n学习已中断")
            break
        except Exception as e:
            print(f"\n课程执行出错: {e}")
            input("按回车键继续...")
    
    print("\n🎉 交易基础课程完成！")
    print("接下来可以学习：")
    print("- 03_高级交易.py - 学习高级交易功能")
    print("- 04_策略开发.py - 学习策略开发")
    print("- 05_风险管理.py - 学习风险管理")

if __name__ == "__main__":
    main()
