"""
通达信预警与EasyXT集成示例
展示如何将tdxtrader与EasyXT结合使用，实现通达信预警信号的程序化交易
"""

import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from easy_xt import get_api
from easy_xt.config import config

# tdxtrader模块导入
try:
    from strategies.tdxtrader.tdxtrader import start as tdx_start
    TDX_AVAILABLE = True
except ImportError:
    TDX_AVAILABLE = False
    print("⚠️  tdxtrader模块未找到，请确保已正确安装")

# 全局EasyXT实例
easy_xt = get_api()
trade_initialized = False
account_added = False

def initialize_trade_service() -> bool:
    """初始化交易服务"""
    global trade_initialized
    if trade_initialized:
        return True
        
    try:
        # 获取QMT路径
        qmt_path = config.get_userdata_path()
        if not qmt_path:
            print("❌ 未配置QMT路径")
            return False
        
        print(f"🔍 尝试连接交易服务: {qmt_path}")
        # 初始化交易服务
        if easy_xt.init_trade(qmt_path):
            trade_initialized = True
            print("✅ 交易服务初始化成功")
            return True
        else:
            print("❌ 交易服务初始化失败")
            return False
    except Exception as e:
        print(f"❌ 交易服务初始化异常: {e}")
        return False

def add_account_to_service(account_id: str) -> bool:
    """添加账户到交易服务"""
    global account_added
    if account_added:
        return True
        
    try:
        print(f"➕ 添加账户: {account_id}")
        if easy_xt.add_account(account_id):
            account_added = True
            print(f"✅ 账户 {account_id} 添加成功")
            return True
        else:
            print(f"❌ 账户 {account_id} 添加失败")
            return False
    except Exception as e:
        print(f"❌ 账户添加异常: {e}")
        return False

def buy_event(params: Dict[str, Any]):
    """
    买入事件处理函数
    使用EasyXT API执行买入操作
    
    Args:
        params: 包含交易相关信息的字典
            - xt_trader: 交易对象
            - account: 账户对象
            - stock: 股票信息
            - position: 持仓信息
    """
    # 获取股票信息
    stock = params.get('stock')
    position = params.get('position')
    xt_trader = params.get('xt_trader')
    account = params.get('account')
    
    if stock is None:
        print("❌ 股票信息缺失")
        return None
    
    print(f"📈 买入信号触发: {stock.get('name', '未知')} ({stock.get('code', '未知')})")
    print(f"   价格: {stock.get('price', '未知')}, 时间: {stock.get('time', '未知')}")
    
    try:
        # 从统一配置中获取账户ID
        account_id = config.get('settings.account.account_id')
        if not account_id:
            print("❌ 未在统一配置中找到账户ID")
            return None
        
        # 确保交易服务已初始化
        if not trade_initialized:
            if not initialize_trade_service():
                return None
        
        # 确保账户已添加
        if not account_added:
            if not add_account_to_service(account_id):
                return None
        
        # 执行买入操作
        order_id = easy_xt.buy(
            account_id=account_id,
            code=stock.get('code', ''),
            volume=100,  # 买入100股（可根据需要调整）
            price=stock.get('price', 0.0),
            price_type='limit'  # 限价单
        )
        
        if order_id:
            print(f"✅ 买入委托成功，委托号: {order_id}")
            return {'size': 100, 'price': stock.get('price', 0.0), 'type': '限价'}
        else:
            print("❌ 买入委托失败")
            return None
            
    except Exception as e:
        print(f"❌ 买入操作异常: {e}")
        return None

def sell_event(params: Dict[str, Any]):
    """
    卖出事件处理函数
    使用EasyXT API执行卖出操作
    
    Args:
        params: 包含交易相关信息的字典
            - xt_trader: 交易对象
            - account: 账户对象
            - stock: 股票信息
            - position: 持仓信息
    """
    # 获取股票信息
    stock = params.get('stock')
    position = params.get('position')
    xt_trader = params.get('xt_trader')
    account = params.get('account')
    
    if stock is None:
        print("❌ 股票信息缺失")
        return None
    
    print(f"📉 卖出信号触发: {stock.get('name', '未知')} ({stock.get('code', '未知')})")
    print(f"   价格: {stock.get('price', '未知')}, 时间: {stock.get('time', '未知')}")
    
    # 检查是否有持仓
    if position is None:
        print("⚠️  无持仓，不执行卖出操作")
        return None
    
    try:
        # 从统一配置中获取账户ID
        account_id = config.get('settings.account.account_id')
        if not account_id:
            print("❌ 未在统一配置中找到账户ID")
            return None
        
        # 确保交易服务已初始化
        if not trade_initialized:
            if not initialize_trade_service():
                return None
        
        # 确保账户已添加
        if not account_added:
            if not add_account_to_service(account_id):
                return None
        
        # 卖出全部可用持仓
        order_id = easy_xt.sell(
            account_id=account_id,
            code=stock.get('code', ''),
            volume=position.can_use_volume,
            price=stock.get('price', 0.0),
            price_type='limit'  # 限价单
        )
        
        if order_id:
            print(f"✅ 卖出委托成功，委托号: {order_id}")
            return {'size': position.can_use_volume, 'price': stock.get('price', 0.0), 'type': '限价'}
        else:
            print("❌ 卖出委托失败")
            return None
            
    except Exception as e:
        print(f"❌ 卖出操作异常: {e}")
        return None

def start_tdx_trading_with_easyxt():
    """
    启动通达信预警交易系统（使用EasyXT）
    """
    if not TDX_AVAILABLE:
        print("❌ tdxtrader模块不可用，无法启动交易系统")
        return
    
    # 从统一配置中获取参数
    account_id = config.get('settings.account.account_id')
    mini_qmt_path = config.get_userdata_path() or r"D:\国金证券QMT交易端\userdata_mini"  # QMT路径
    file_path = r"D:\new_tdx\sign.txt"  # 通达信预警文件路径
    interval = 1  # 轮询间隔（秒）
    buy_sign = "KDJ买入条件选股"  # 买入信号名称
    sell_sign = "KDJ卖出条件选股"  # 卖出信号名称
    cancel_after = 10  # 未成交撤单时间（秒）
    wechat_webhook_url = None  # 企业微信机器人webhook url（可选）
    
    if not account_id:
        print("❌ 未在统一配置中找到账户ID，请检查配置文件")
        return
    
    print("🚀 启动通达信预警交易系统（EasyXT版）")
    print(f"   账户ID: {account_id}")
    print(f"   QMT路径: {mini_qmt_path}")
    print(f"   预警文件: {file_path}")
    print(f"   轮询间隔: {interval}秒")
    print(f"   买入信号: {buy_sign}")
    print(f"   卖出信号: {sell_sign}")
    
    # 预先初始化交易服务和账户
    print("🔄 预初始化交易服务...")
    if not initialize_trade_service():
        print("❌ 交易服务初始化失败，无法启动交易系统")
        return
        
    print("🔄 预添加账户...")
    if not add_account_to_service(account_id):
        print("❌ 账户添加失败，无法启动交易系统")
        return
    
    if TDX_AVAILABLE:
        try:
            # 启动tdxtrader
            tdx_start(
                account_id=account_id,
                mini_qmt_path=mini_qmt_path,
                file_path=file_path,
                interval=interval,
                buy_sign=buy_sign,
                sell_sign=sell_sign,
                buy_event=buy_event,
                sell_event=sell_event,
                cancel_after=cancel_after,
                wechat_webhook_url=wechat_webhook_url
            )
        except KeyboardInterrupt:
            print("\n⏹️  交易系统已停止")
        except Exception as e:
            print(f"❌ 交易系统启动失败: {e}")

# 使用示例
if __name__ == "__main__":
    # 启动通达信预警交易系统
    start_tdx_trading_with_easyxt()