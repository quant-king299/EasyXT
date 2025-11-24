from xtquant import xtconstant
import time
import math
import inspect
from tdxtrader.file import read_file, read_block_file
from tdxtrader.utils import add_stock_suffix, timestamp_to_datetime_string, convert_to_current_date
from tdxtrader.anis import RED, GREEN, YELLOW, BLUE, RESET
from tdxtrader.logger import logger
from tdxtrader.trader import error_orders
import os
from datetime import datetime

# 存储上一次板块文件的内容，用于检测变化
previous_block_contents = {}

def get_volume(paload, row):
    if paload.get('size') is not None:
        return paload.get('size')
    elif paload.get('amount') is not None:
        if paload.get('price') > 0:
            return math.floor(paload.get('amount') / paload.get('price') / 100) * 100
        else:
            return math.floor(paload.get('amount') / row.get('price') / 100) * 100
    else:
        return 100
    

def get_position(positions, stock_code):
    for position in (positions or []):
        if position.stock_code == stock_code:
            return position
    return None

def create_order(xt_trader, account, file_path, previous_df, buy_sign, sell_sign, buy_event, sell_event, block_files=None):
    current_df = read_file(file_path)
    if current_df is not None:
        if previous_df is not None:
            # 比较前后两次读取的 DataFrame，找出新增的行
            new_rows = current_df[~current_df.index.isin(previous_df.index)]
            if not new_rows.empty:
                for index, row in new_rows.iterrows():

                    stock_code = add_stock_suffix(row['code'])

                    price_type_map = {
                        '市价': xtconstant.LATEST_PRICE,
                        '限价': xtconstant.FIX_PRICE
                    }

                    positions = xt_trader.query_stock_positions(account)

                    position = get_position(positions, stock_code)

                    params = {
                        'xt_trader': xt_trader,
                        'account': account,
                        'stock': row,
                        'position': position
                    }
                    
                    # Convert buy_sign and sell_sign to lists if they are strings
                    buy_signs = buy_sign if isinstance(buy_sign, list) else [buy_sign]
                    sell_signs = sell_sign if isinstance(sell_sign, list) else [sell_sign]
                    
                    if row['sign'] in buy_signs:
                        if len(inspect.signature(buy_event).parameters) > 1: # 检查 buy_event 是否需要额外的参数
                            buy_paload = buy_event(row, position, xt_trader)
                        else:
                            buy_paload = buy_event(params)
                        if buy_paload is not None:
                            xt_trader.order_stock_async(
                                account=account, 
                                stock_code=stock_code, 
                                order_type=xtconstant.STOCK_BUY, 
                                order_volume=get_volume(buy_paload, row), 
                                price_type=price_type_map.get(buy_paload.get('type')) or xtconstant.LATEST_PRICE,
                                price=buy_paload.get('price') or -1,
                                order_remark=row.get('name')
                            )
                    elif row['sign'] in sell_signs:
                        if position is not None:
                            if len(inspect.signature(sell_event).parameters) > 1: # 检查 sell_event 是否需要额外的参数
                                sell_paload = sell_event(row, position, xt_trader)
                            else:
                                sell_paload = sell_event(params)
                                
                            if sell_paload is not None:
                                xt_trader.order_stock_async(
                                    account=account, 
                                    stock_code=stock_code, 
                                    order_type=xtconstant.STOCK_SELL, 
                                    order_volume=get_volume(sell_paload, row),
                                    price_type=price_type_map.get(sell_paload.get('type')) or xtconstant.LATEST_PRICE,
                                    price=sell_paload.get('price') or -1,
                                    order_remark=row.get('name')
                                )
                        else:
                            logger.warning(f"{YELLOW}【无持仓】{RESET}没有查询到持仓信息，不执行卖出操作。股票代码：{stock_code}, 名称：{row['name']}")
                
        # 处理板块文件
        if block_files:
            process_block_files(xt_trader, account, block_files, buy_event, sell_event)
        
        return current_df
    
    return None

def process_block_files(xt_trader, account, block_files, buy_event, sell_event):
    """
    处理板块文件，检测股票变化并触发相应操作
    :param xt_trader: 交易对象
    :param account: 账户对象
    :param block_files: 板块文件配置字典，格式 {'板块文件路径': '操作类型(buy/sell)'}
    :param buy_event: 买入事件处理函数
    :param sell_event: 卖出事件处理函数
    """
    global previous_block_contents
    
    logger.info(f"🔍 开始处理板块文件监控，共 {len(block_files)} 个板块文件")
    
    for block_file_path, operation in block_files.items():
        try:
            logger.info(f"🔍 检查板块文件: {block_file_path} (操作类型: {operation})")
            
            # 检查文件是否存在
            if not os.path.exists(block_file_path):
                logger.warning(f"板块文件不存在: {block_file_path}")
                continue
                
            # 获取文件修改时间
            mod_time = os.path.getmtime(block_file_path)
            logger.info(f"📊 板块文件 {os.path.basename(block_file_path)} 最后修改时间: {datetime.fromtimestamp(mod_time)}")
            
            # 读取当前板块内容
            current_stocks = read_block_file(block_file_path)
            logger.info(f"📊 当前板块包含 {len(current_stocks)} 只股票: {current_stocks}")
            
            # 检查是否是第一次读取该文件
            if block_file_path not in previous_block_contents:
                logger.info(f"🆕 首次读取板块文件 {os.path.basename(block_file_path)}，共 {len(current_stocks)} 只股票")
                previous_block_contents[block_file_path] = {
                    'stocks': set(current_stocks),
                    'mod_time': mod_time
                }
                continue
            
            # 检查文件是否被修改
            prev_data = previous_block_contents[block_file_path]
            logger.info(f"🕒 上次检查时间: {datetime.fromtimestamp(prev_data['mod_time'])}")
            
            if prev_data['mod_time'] == mod_time:
                # 文件未被修改，跳过
                logger.info(f"⏭️  板块文件 {os.path.basename(block_file_path)} 未发生变化，跳过处理")
                continue
                
            # 文件被修改，更新时间戳
            logger.info(f"🔄 板块文件 {os.path.basename(block_file_path)} 发生变化，开始处理")
            previous_block_contents[block_file_path]['mod_time'] = mod_time
            
            # 比较股票列表变化
            prev_stocks = prev_data['stocks']
            current_stocks_set = set(current_stocks)
            
            logger.info(f"📊 之前股票列表: {prev_stocks}")
            logger.info(f"📊 当前股票列表: {current_stocks_set}")
            
            # 找出新增的股票（需要买入）
            added_stocks = current_stocks_set - prev_stocks
            # 找出移除的股票（可能需要卖出）
            removed_stocks = prev_stocks - current_stocks_set
            
            logger.info(f"🆕 新增股票: {added_stocks}")
            logger.info(f"❌ 移除股票: {removed_stocks}")
            
            # 更新存储的股票列表
            previous_block_contents[block_file_path]['stocks'] = current_stocks_set
            
            # 处理新增股票（买入）
            if operation == 'buy' and added_stocks:
                logger.info(f"📈 板块 {os.path.basename(block_file_path)} 新增 {len(added_stocks)} 只股票，触发买入操作")
                process_stocks_for_operation(xt_trader, account, added_stocks, 'buy', buy_event)
            
            # 处理移除股票（卖出）
            elif operation == 'sell' and removed_stocks:
                logger.info(f"📉 板块 {os.path.basename(block_file_path)} 移除 {len(removed_stocks)} 只股票，触发卖出操作")
                process_stocks_for_operation(xt_trader, account, removed_stocks, 'sell', sell_event)
            else:
                logger.info(f"⏭️  板块 {os.path.basename(block_file_path)} 无操作需要执行")
                
        except Exception as e:
            logger.error(f"处理板块文件 {block_file_path} 时发生错误: {e}")
            import traceback
            traceback.print_exc()

def process_stocks_for_operation(xt_trader, account, stocks, operation, event_handler):
    """
    处理股票列表并执行相应操作
    :param xt_trader: 交易对象
    :param account: 账户对象
    :param stocks: 股票代码列表
    :param operation: 操作类型 ('buy' 或 'sell')
    :param event_handler: 事件处理函数
    """
    logger.info(f"🔍 开始处理股票列表操作: {operation}, 股票数量: {len(stocks)}")
    
    try:
        # 获取当前持仓
        positions = xt_trader.query_stock_positions(account)
        logger.info(f"📊 当前持仓数量: {len(positions) if positions else 0}")
        
        for stock_code in stocks:
            try:
                logger.info(f"🔍 处理股票: {stock_code}, 操作类型: {operation}")
                
                # 添加股票后缀
                full_stock_code = add_stock_suffix(stock_code)
                logger.info(f"📊 完整股票代码: {full_stock_code}")
                
                # 查找持仓
                position = get_position(positions, full_stock_code)
                if position:
                    logger.info(f"📊 持仓信息: 可用数量={position.can_use_volume}, 总数量={position.volume}, 成本价={position.cost_price}")
                else:
                    logger.info(f"📊 无持仓记录")
                
                # 获取实时行情价格 - 使用EasyXT获取
                stock_price = 0.0
                try:
                    from easy_xt import get_api
                    easy_xt_api = get_api()
                    # 使用EasyXT获取实时价格
                    try:
                        # 获取最新价格
                        price_df = easy_xt_api.get_current_price(stock_code)
                        if price_df is not None and not price_df.empty:
                            # 获取第一行第一列的价格
                            stock_price = float(price_df.iloc[0, 0])
                            if stock_price > 0:
                                logger.info(f"【EasyXT】获取到 {stock_code} 的最新价格: {stock_price}")
                    except Exception as easyxt_error:
                        logger.debug(f"EasyXT获取 {stock_code} 价格失败: {easyxt_error}")
                        
                except Exception as price_error:
                    logger.warning(f"获取 {stock_code} 实时价格失败: {price_error}，将使用市价委托")
                    stock_price = 0.0  # 如果获取失败，使用市价委托
                
                # 准备参数
                params = {
                    'xt_trader': xt_trader,
                    'account': account,
                    'stock': {
                        'code': stock_code, 
                        'name': f'股票{stock_code}', 
                        'price': stock_price,  # 实时获取的价格
                        'time': datetime.now().strftime('%H:%M:%S')
                    },
                    'position': position
                }
                
                if operation == 'buy':
                    logger.info(f"🔍 调用event_handler处理买入操作: {event_handler.__name__}")
                    # 买入操作 - 通过event_handler执行委托（通常是EasyXT）
                    if len(inspect.signature(event_handler).parameters) > 1:
                        logger.info("🔧 使用多参数调用方式")
                        result = event_handler(params['stock'], position, xt_trader)
                    else:
                        logger.info("🔧 使用参数字典调用方式")
                        result = event_handler(params)
                    
                    logger.info(f"📊 event_handler返回结果: {result}")
                    # event_handler返回None表示已在函数内执行了委托，无需再通过xt_trader执行
                    # 如果返回dict，则需要通过xt_trader再次执行（作为备选方案）
                    if result is not None:
                        logger.info("⚠️  event_handler返回非None值，准备使用xt_trader备选方案")
                        # 如果返回的是空dict，使用默认参数
                        if isinstance(result, dict) and len(result) == 0:
                            logger.info("🔧 使用默认参数")
                            result = {
                                'price': 0.0,  # 市价
                                'size': 100    # 默认100股
                            }
                        
                        final_price = result.get('price', 0.0) if isinstance(result, dict) else 0.0
                        if final_price <= 0:
                            logger.warning(f"【买入】{stock_code} 委托价格无效({final_price})，使用市价委托")
                            final_price = -1
                        
                        volume = get_volume(result, params['stock']) if isinstance(result, dict) else 100
                        
                        logger.info(f"🔍 准备通过xt_trader执行买入委托: 股票={stock_code}, 数量={volume}, 价格={final_price}")
                        seq = xt_trader.order_stock_async(
                            account=account,
                            stock_code=full_stock_code,
                            order_type=xtconstant.STOCK_BUY,
                            order_volume=volume,
                            price_type=xtconstant.LATEST_PRICE,
                            price=final_price,
                            strategy_name='TDXTrader',
                            order_remark=params['stock']['name']
                        )
                        logger.info(f"🚀 异步买入委托已提交，序列号: {seq}")
                        logger.info(f"【买入委托】股票:{stock_code} 数量:{volume} 委托价格:{final_price if final_price > 0 else '市价'}")
                    else:
                        logger.info("✅ event_handler返回None，表示委托已成功提交，无需使用备选方案")
                        
                elif operation == 'sell':
                    logger.info(f"🔍 调用event_handler处理卖出操作: {event_handler.__name__}")
                    if position is not None:
                        logger.info(f"📉 执行卖出操作: {stock_code}")
                        # 卖出操作 - 通过event_handler执行委托（通常是EasyXT）
                        if len(inspect.signature(event_handler).parameters) > 1:
                            logger.info("🔧 使用多参数调用方式")
                            result = event_handler(params['stock'], position, xt_trader)
                        else:
                            logger.info("🔧 使用参数字典调用方式")
                            result = event_handler(params)
                        
                        logger.info(f"📊 event_handler返回结果: {result}")
                        
                        # event_handler返回None表示已在函数内执行了委托，无需再通过xt_trader执行
                        # 如果返回dict，则需要通过xt_trader再次执行（作为备选方案）
                        if result is not None:
                            logger.info("⚠️  event_handler返回非None值，准备使用xt_trader备选方案")
                            # 如果返回的是空dict，使用默认参数
                            if isinstance(result, dict) and len(result) == 0:
                                logger.info("🔧 使用默认参数")
                                result = {
                                    'price': 0.0,  # 市价
                                    'size': position.can_use_volume if position else 100  # 可用持仓数量或默认100股
                                }
                            
                            final_price = result.get('price', 0.0) if isinstance(result, dict) else 0.0
                            if final_price <= 0:
                                logger.warning(f"⚠️  【卖出】{stock_code} 委托价格无效({final_price})，使用市价委托")
                                final_price = -1
                            
                            volume = get_volume(result, params['stock']) if isinstance(result, dict) else (position.can_use_volume if position else 100)
                            
                            logger.info(f"🔍 准备通过xt_trader执行卖出委托: 股票={stock_code}, 数量={volume}, 价格={final_price}")
                            seq = xt_trader.order_stock_async(
                                account=account,
                                stock_code=full_stock_code,
                                order_type=xtconstant.STOCK_SELL,
                                order_volume=volume,
                                price_type=xtconstant.LATEST_PRICE,
                                price=final_price,
                                strategy_name='TDXTrader',
                                order_remark=params['stock']['name']
                            )
                            logger.info(f"🚀 异步卖出委托已提交，序列号: {seq}")
                            logger.info(f"✅ 【卖出委托】股票:{stock_code} 数量:{volume} 委托价格:{final_price if final_price > 0 else '市价'}")
                        else:
                            logger.info("✅ event_handler返回None，表示委托已成功提交，无需使用备选方案")
                    else:
                        logger.warning(f"⚠️  【无持仓】没有查询到持仓信息，不执行卖出操作。股票代码：{stock_code}")
                        
            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时发生错误: {e}")
                
    except Exception as e:
        logger.error(f"处理股票列表时发生错误: {e}")

def cancel_order(xt_trader, account, cancel_after):
    if cancel_after is not None:
        orders = xt_trader.query_stock_orders(account, cancelable_only=True)
        for order in orders:
            if order.order_id in error_orders:
                return
            order_time = convert_to_current_date(order.order_time)
            if time.time() - order_time >= cancel_after:
                xt_trader.cancel_order_stock_async(account, order.order_id)