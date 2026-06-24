# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
雪球跟单系统 - 真实交易版 (使用 easy_xt)
使用 easy_xt 封装的交易API，解决所有兼容性问题
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"xueqiu_real_trading_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def print_banner():
    """显示启动横幅"""
    logger.info("=" * 80)
    logger.info("🚀 雪球跟单系统 - 真实交易版 (EasyXT)")
    logger.info("⚠️  警告：此版本会执行真实交易操作！")
    logger.info("=" * 80)
    logger.info(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from .internal.config_manager import ConfigManager as _Cfg
        _cfg = _Cfg()
        portfolios = _cfg.get_portfolios()
        enabled_names = [str(p.get('name') or p.get('code')) for p in portfolios if p.get('enabled', False)]
        combo_str = ', '.join(enabled_names) if enabled_names else '未配置'
        account_id = _cfg.get_setting('settings.account.account_id') or '未配置'
    except Exception:
        combo_str = '未配置'
        account_id = '未配置'
    logger.info(f"📊 跟单组合: {combo_str}")
    logger.info(f"🏦 交易账号: {account_id}")
    logger.info(f"💰 交易模式: 真实交易模式")
    logger.info(f"🔧 交易接口: EasyXT (高级封装)")
    logger.info("=" * 80)

def safety_confirmation():
    """安全确认流程"""
    logger.info("\n⚠️" + "⚠️" * 19)
    logger.info("重要安全提醒")
    logger.info("⚠️" + "⚠️" * 19)
    logger.info("此版本将执行真实交易操作！")
    logger.info("- 会使用您的真实资金进行买卖")
    logger.info("- 存在盈亏风险")
    logger.info("- 请确保您了解相关风险")
    logger.info("- 建议先在模拟环境中测试")
    logger.info("⚠️" + "⚠️" * 19)
    
    # 第一重确认
    confirm1 = input("\n🔐 第一重确认 - 输入 'YES' 确认启动真实交易: ").strip()
    if confirm1 != "YES":
        logger.info("❌ 用户取消启动")
        return False
    
    # 第二重确认
    confirm2 = input("🔐 第二重确认 - 输入 'CONFIRM' 再次确认: ").strip()
    if confirm2 != "CONFIRM":
        logger.info("❌ 用户取消启动")
        return False
    
    # 第三重确认
    confirm3 = input("🔐 第三重确认 - 输入 'ENABLE' 最终确认: ").strip()
    if confirm3 != "ENABLE":
        logger.info("❌ 用户取消启动")
        return False
    
    logger.info("✅ 安全确认完成")
    return True

def load_config():
    """加载配置"""
    config_file = Path(__file__).parent / "config" / "real_trading.json"
    
    if not config_file.exists():
        # 如果真实交易配置不存在，使用统一配置
        config_file = Path(__file__).parent / "config" / "unified_config.json"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 确保是真实交易模式
        if 'settings' not in config:
            config['settings'] = {}
        if 'trading' not in config['settings']:
            config['settings']['trading'] = {}
        
        config['settings']['trading']['trade_mode'] = 'real'
        
        logger.info("✅ 真实交易配置加载成功")
        return config
    except Exception as e:
        logger.info(f"❌ 真实交易配置加载失败: {e}")
        return None

def test_easyxt_connection(config):
    """测试 easy_xt 连接"""
    try:
        logger.info("\n🔧 初始化 EasyXT 交易API...")
        
        # 导入 easy_xt
        from easy_xt.advanced_trade_api import AdvancedTradeAPI
        
        # 获取配置
        qmt_path = config['settings']['account']['qmt_path']
        account_id = config['settings']['account']['account_id']
        
        logger.info(f"📁 QMT路径: {qmt_path}")
        logger.info(f"🏦 交易账号: {account_id}")
        
        # 创建高级交易API
        session_id = f"xueqiu_real_{int(time.time())}"
        api = AdvancedTradeAPI()
        
        # 连接交易服务
        logger.info("🚀 连接交易服务...")
        result = api.connect(qmt_path, session_id)
        
        if not result:
            logger.info("❌ EasyXT 连接失败")
            return False
        
        logger.info("✅ EasyXT 连接成功")
        
        # 添加账户
        logger.info("📡 添加交易账户...")
        account_result = api.add_account(account_id)
        
        if not account_result:
            logger.info("❌ 添加账户失败")
            api.disconnect()
            return False
        
        logger.info("✅ 账户添加成功")
        
        # 测试账户查询
        try:
            logger.info("💰 查询账户资产...")
            asset_info = api.get_account_asset_detailed(account_id)
            if asset_info:
                logger.info("✅ 账户查询成功")
                total_asset = getattr(asset_info, 'total_asset', 0)
                cash = getattr(asset_info, 'cash', 0)
                logger.info(f"💰 总资产: {total_asset:.2f}")
                logger.info(f"💵 可用资金: {cash:.2f}")
            else:
                logger.info("⚠️ 账户查询返回空数据")
        except Exception as e:
            logger.info(f"⚠️ 账户查询失败: {e}")
        
        # 断开连接
        api.disconnect()
        return True
        
    except ImportError as e:
        logger.info(f"❌ EasyXT 模块导入失败: {e}")
        return False
    except Exception as e:
        logger.info(f"❌ EasyXT 连接测试失败: {e}")
        return False

class XueqiuRealTrader:
    """雪球真实交易器 (EasyXT版本)"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.session_id = f"xueqiu_real_{int(time.time())}"
        self.account_id = config['settings']['account']['account_id']
        self.qmt_path = config['settings']['account']['qmt_path']
        self.api = None
        self.connected = False
        
    async def initialize(self):
        """初始化交易器"""
        try:
            from easy_xt.advanced_trade_api import AdvancedTradeAPI
            
            # 创建高级交易API
            self.api = AdvancedTradeAPI()
            
            # 连接交易服务
            result = self.api.connect(self.qmt_path, self.session_id)
            if not result:
                self.logger.error("EasyXT 连接失败")
                return False
            
            # 添加账户
            account_result = self.api.add_account(self.account_id)
            if not account_result:
                self.logger.error("添加账户失败")
                return False
            
            self.connected = True
            self.logger.info("EasyXT 交易API初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"交易器初始化失败: {e}")
            return False
    
    async def get_account_info(self):
        """获取账户信息"""
        if not self.connected or not self.api:
            return None
        
        try:
            account_info = self.api.get_account_asset_detailed(self.account_id)
            return account_info
        except Exception as e:
            self.logger.error(f"获取账户信息失败: {e}")
            return None
    
    async def place_order(self, stock_code, price, volume, order_type):
        """下单"""
        if not self.connected or not self.api:
            self.logger.error("交易连接未建立")
            return None
        
        try:
            # 使用 EasyXT 的同步下单方法
            self.logger.info(f"下单: {stock_code}, 价格: {price}, 数量: {volume}, 类型: {order_type}")
            
            # 转换订单类型
            order_type_str = 'buy' if order_type == 23 else 'sell'
            
            # 下单
            order_id = self.api.sync_order(
                account_id=self.account_id,
                code=stock_code,
                order_type=order_type_str,
                volume=volume,
                price=price,
                price_type='limit',
                strategy_name='XueqiuFollow',
                order_remark=f'雪球跟单_{stock_code}'
            )
            
            if order_id and order_id > 0:
                self.logger.info(f"下单成功，订单ID: {order_id}")
                return order_id
            else:
                self.logger.error("下单失败")
                return None
                
        except Exception as e:
            self.logger.error(f"下单异常: {e}")
            return None
    
    def cleanup(self):
        """清理资源"""
        if self.connected and self.api:
            try:
                # 断开连接
                self.logger.info("断开 EasyXT 连接")
                self.api.disconnect()
                self.connected = False
            except Exception as e:
                self.logger.error(f"断开连接失败: {e}")

async def main():
    """主函数"""
    # 设置日志
    logger = setup_logging()
    
    try:
        # 显示启动横幅
        print_banner()
        
        # 安全确认
        if not safety_confirmation():
            return
        
        # 加载配置
        config = load_config()
        if not config:
            return
        
        # 显示配置信息
        logger.info("\n📋 真实交易配置:")
        logger.info(f"   🏦 交易账号: {config['settings']['account']['account_id']}")
        logger.info(f"   📁 QMT路径: {config['settings']['account']['qmt_path']}")
        
        if 'portfolios' in config and 'ZH2863835' in config['portfolios']:
            portfolio = config['portfolios']['ZH2863835']
            logger.info(f"   💰 跟单比例: {portfolio['follow_ratio']*100}%")
            logger.info(f"   💵 最大仓位: {portfolio['max_position']}元")
        
        if 'trading' in config['settings']:
            trading = config['settings']['trading']
            logger.info(f"   💸 最大单笔: {trading.get('max_single_amount', 5000)}元")
            logger.info(f"   💰 最小交易: {trading.get('min_trade_amount', 100)}元")
        
        logger.info(f"   🌐 组合URL: https://xueqiu.com/P/ZH2863835")
        
        # 最终确认
        final_confirm = input("\n🔐 最终确认 - 输入 'START' 开始交易: ").strip()
        if final_confirm != "START":
            logger.info("❌ 用户取消启动")
            return
        
        # 测试 EasyXT 连接
        if not test_easyxt_connection(config):
            logger.info("❌ EasyXT 连接测试失败，无法启动真实交易")
            return
        
        # 创建交易器
        trader = XueqiuRealTrader(config, logger)
        
        # 初始化交易器
        if not await trader.initialize():
            logger.info("❌ 交易器初始化失败")
            return
        
        logger.info("\n🎉 真实交易系统启动成功！")
        logger.info("📊 系统正在运行，监控雪球组合变化...")
        logger.info("⚠️ 按 Ctrl+C 可以安全停止系统")
        
        # 主循环
        order_count = 0
        success_count = 0
        failed_count = 0
        total_amount = 0.0
        
        try:
            while True:
                # 显示实时状态
                current_time = datetime.now().strftime("%H:%M:%S")
                logger.info(f"\r📊 [{current_time}] 实时状态: 📈总订单:{order_count} ✅成功:{success_count} ❌失败:{failed_count} 🔄活跃:0 💰总额:{total_amount:.2f}", end="")
                
                # 这里添加实际的雪球监控和交易逻辑
                await asyncio.sleep(5)  # 每5秒检查一次
                
        except KeyboardInterrupt:
            logger.info(f"\n\n⚠️ 收到停止信号，正在安全关闭系统...")
            
        finally:
            # 清理资源
            trader.cleanup()
            logger.info("👋 系统已安全关闭")
    
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        logger.info(f"❌ 系统异常: {e}")

if __name__ == "__main__":
    asyncio.run(main())