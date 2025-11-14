"""
EasyXT与通达信预警集成模块
提供完整的集成方案，将tdxtrader的预警信号处理与EasyXT的交易功能结合
"""

import sys
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from easy_xt import get_api
from easy_xt.config import config

class TDXEasyXTIntegration:
    """通达信预警与EasyXT集成类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化集成器
        
        Args:
            config_file: 配置文件路径
        """
        self.easy_xt = get_api()
        self.config = self._load_config(config_file)
        self._trade_initialized = False
        self._account_added = False
        
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            Dict: 配置字典
        """
        default_config = {
            "tdx_file_path": r"D:\new_tdx\sign.txt",
            "interval": 1,
            "buy_signals": ["KDJ买入条件选股"],
            "sell_signals": ["KDJ卖出条件选股"],
            "cancel_after": 10,
            "wechat_webhook_url": None,
            "default_volume": 100,
            "price_type": "limit"
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"⚠️  配置文件加载失败: {e}")
        
        return default_config
    
    def initialize_trade_service(self) -> bool:
        """
        初始化交易服务
        
        Returns:
            bool: 是否成功
        """
        if self._trade_initialized:
            return True
            
        try:
            # 从统一配置中获取QMT路径
            qmt_path = config.get_userdata_path()
            if not qmt_path:
                print("❌ 未配置QMT路径")
                return False
            
            # 初始化交易服务
            if self.easy_xt.init_trade(qmt_path):
                self._trade_initialized = True
                print("✅ 交易服务初始化成功")
                return True
            else:
                print("❌ 交易服务初始化失败")
                return False
                
        except Exception as e:
            print(f"❌ 交易服务初始化异常: {e}")
            return False
    
    def add_account(self, account_id: Optional[str] = None) -> bool:
        """
        添加交易账户
        
        Args:
            account_id: 账户ID
            
        Returns:
            bool: 是否成功
        """
        if self._account_added:
            return True
            
        try:
            # 从统一配置中获取账户ID
            if not account_id:
                account_id = config.get('settings.account.account_id')
            if not account_id:
                print("❌ 未配置账户ID")
                return False
            
            if self.easy_xt.add_account(account_id):
                self._account_added = True
                print(f"✅ 账户 {account_id} 添加成功")
                return True
            else:
                print(f"❌ 账户 {account_id} 添加失败")
                return False
                
        except Exception as e:
            print(f"❌ 账户添加异常: {e}")
            return False
    
    def buy_event(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        买入事件处理函数
        
        Args:
            params: 包含交易相关信息的字典
            
        Returns:
            Optional[Dict]: 交易参数字典
        """
        try:
            # 获取股票信息
            stock = params.get('stock')
            position = params.get('position')
            
            # 检查股票信息是否存在
            if not stock:
                print("❌ 股票信息缺失")
                return None
                
            print(f"📈 买入信号触发: {stock.get('name', '未知')} ({stock.get('code', '未知')})")
            print(f"   价格: {stock.get('price', '未知')}, 时间: {stock.get('time', '未知')}")
            
            # 检查交易服务是否已初始化
            if not self._trade_initialized:
                if not self.initialize_trade_service():
                    return None
            
            # 检查账户是否已添加
            if not self._account_added:
                if not self.add_account():
                    return None
            
            # 从统一配置中获取账户ID
            account_id = config.get('settings.account.account_id')
            if not account_id:
                print("❌ 未在统一配置中找到账户ID")
                return None
            volume = self.config.get("default_volume", 100)
            price_type = self.config.get("price_type", "limit")
            
            order_id = self.easy_xt.buy(
                account_id=account_id,
                code=stock.get('code'),
                volume=volume,
                price=stock.get('price') if price_type == "limit" else 0,
                price_type=price_type
            )
            
            if order_id:
                print(f"✅ 买入委托成功，委托号: {order_id}")
                return {
                    'size': volume,
                    'price': stock.get('price') if price_type == "limit" else -1,
                    'type': '限价' if price_type == "limit" else '市价'
                }
            else:
                print("❌ 买入委托失败")
                return None
                
        except Exception as e:
            print(f"❌ 买入操作异常: {e}")
            return None
    
    def sell_event(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        卖出事件处理函数
        
        Args:
            params: 包含交易相关信息的字典
            
        Returns:
            Optional[Dict]: 交易参数字典
        """
        try:
            # 获取股票信息
            stock = params.get('stock')
            position = params.get('position')
            
            # 检查股票信息是否存在
            if not stock:
                print("❌ 股票信息缺失")
                return None
                
            print(f"📉 卖出信号触发: {stock.get('name', '未知')} ({stock.get('code', '未知')})")
            print(f"   价格: {stock.get('price', '未知')}, 时间: {stock.get('time', '未知')}")
            
            # 检查是否有持仓
            if position is None:
                print("⚠️  无持仓，不执行卖出操作")
                return None
            
            # 检查交易服务是否已初始化
            if not self._trade_initialized:
                if not self.initialize_trade_service():
                    return None
            
            # 检查账户是否已添加
            if not self._account_added:
                if not self.add_account():
                    return None
            
            # 从统一配置中获取账户ID
            account_id = config.get('settings.account.account_id')
            if not account_id:
                print("❌ 未在统一配置中找到账户ID")
                return None
            price_type = self.config.get("price_type", "limit")
            
            order_id = self.easy_xt.sell(
                account_id=account_id,
                code=stock.get('code'),
                volume=position.can_use_volume,
                price=stock.get('price') if price_type == "limit" else 0,
                price_type=price_type
            )
            
            if order_id:
                print(f"✅ 卖出委托成功，委托号: {order_id}")
                return {
                    'size': position.can_use_volume,
                    'price': stock.get('price') if price_type == "limit" else -1,
                    'type': '限价' if price_type == "limit" else '市价'
                }
            else:
                print("❌ 卖出委托失败")
                return None
                
        except Exception as e:
            print(f"❌ 卖出操作异常: {e}")
            return None
    
    def start_trading(self):
        """
        启动交易系统
        """
        try:
            # 导入tdxtrader
            from strategies.tdxtrader.tdxtrader import start as tdx_start
            
            # 从统一配置中获取账户ID和QMT路径
            account_id = config.get('settings.account.account_id')
            qmt_path = config.get_userdata_path()
            
            if not account_id:
                print("❌ 未在统一配置中找到账户ID")
                return
            
            if not qmt_path:
                print("❌ 未在统一配置中找到QMT路径")
                return
            
            print("🚀 启动通达信预警交易系统（EasyXT集成版）")
            print(f"   账户ID: {account_id}")
            print(f"   QMT路径: {qmt_path}")
            print(f"   预警文件: {self.config.get('tdx_file_path')}")
            print(f"   轮询间隔: {self.config.get('interval')}秒")
            print(f"   买入信号: {self.config.get('buy_signals')}")
            print(f"   卖出信号: {self.config.get('sell_signals')}")
            
            # 启动tdxtrader
            tdx_start(
                account_id=account_id,
                mini_qmt_path=qmt_path,
                file_path=self.config.get("tdx_file_path"),
                interval=self.config.get("interval", 1),
                buy_sign=self.config.get("buy_signals"),
                sell_sign=self.config.get("sell_signals"),
                buy_event=self.buy_event,
                sell_event=self.sell_event,
                cancel_after=self.config.get("cancel_after", 10),
                wechat_webhook_url=self.config.get("wechat_webhook_url")
            )
            
        except ImportError:
            print("❌ tdxtrader模块未找到，请确保已正确安装")
        except KeyboardInterrupt:
            print("\n⏹️  交易系统已停止")
        except Exception as e:
            print(f"❌ 交易系统启动失败: {e}")

def create_config_template(config_file: str = "tdx_easyxt_config.json"):
    """
    创建配置文件模板
    
    Args:
        config_file: 配置文件路径
    """
    template = {
        "tdx_file_path": "D:/new_tdx/sign.txt",
        "interval": 1,
        "buy_signals": ["KDJ买入条件选股", "MACD买入条件选股"],
        "sell_signals": ["KDJ卖出条件选股", "MACD卖出条件选股"],
        "cancel_after": 10,
        "wechat_webhook_url": None,
        "default_volume": 100,
        "price_type": "limit"
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 配置文件模板已创建: {config_file}")
    print("💡 注意：账户ID和QMT路径配置已移至项目根目录的统一配置文件中")
    print("   请参考 strategies/tdxtrader/CONFIGURATION.md 进行配置")

# 使用示例
if __name__ == "__main__":
    # 创建配置文件模板
    create_config_template()
    
    # 初始化集成器
    integration = TDXEasyXTIntegration("tdx_easyxt_config.json")
    
    # 启动交易系统
    integration.start_trading()