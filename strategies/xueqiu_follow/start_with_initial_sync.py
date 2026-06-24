# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
雪球跟单系统 - 带初始同步的启动脚本
启动时立即根据雪球组合当前持仓进行调仓，然后监控变化
"""

import os
import sys
import json
import time
import asyncio
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"xueqiu_sync_{datetime.now().strftime('%Y%m%d')}.log"
    
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
    logger.info("🚀 雪球跟单系统 - 初始同步版")
    logger.info("🔄 启动时立即根据雪球组合当前持仓进行调仓")
    logger.info("=" * 80)
    
    # 先加载配置获取组合信息
    config = load_config()
    
    # 尝试从配置管理器获取启用的组合
    try:
        from strategies.xueqiu_follow.internal.config_manager import ConfigManager
        config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
        config_manager.load_all_configs()  # 确保加载所有配置
        
        # 调试信息 - 检查_portfolios内容
        logger.info(f"DEBUG: _portfolios类型: {type(config_manager._portfolios)}")
        logger.info(f"DEBUG: _portfolios内容: {config_manager._portfolios}")
        
        # 正确获取组合列表：从_portfolios字典中获取portfolios键的值
        if isinstance(config_manager._portfolios, dict) and 'portfolios' in config_manager._portfolios:
            all_portfolios = config_manager._portfolios['portfolios']
        else:
            all_portfolios = []
        
        # 过滤启用的组合
        enabled_portfolios = [p for p in all_portfolios if p.get('enabled', False)]
        
        # 调试信息
        logger.info(f"DEBUG: 获取到的启用组合数量: {len(enabled_portfolios)}")
        for i, portfolio in enumerate(enabled_portfolios):
            logger.info(f"DEBUG: 组合 {i}: {portfolio}")
        
        if enabled_portfolios:
            portfolio = enabled_portfolios[0]
            portfolio_code = portfolio.get('code', portfolio.get('symbol', '未知'))
            account_id = config.get('settings', {}).get('account', {}).get('account_id', '未配置') if config else '未配置'
            
            logger.info(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"📊 跟单组合: {portfolio_code}")
            logger.info(f"🏦 交易账号: {account_id}")
        else:
            logger.info(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"📊 跟单组合: 未配置")
            logger.info(f"🏦 交易账号: 未配置")
    except Exception as e:
        logger.info(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📊 跟单组合: ZH3368671")
        logger.info(f"🏦 交易账号: 39020958")
        logger.info(f"⚠️ 配置加载警告: {e}")
    
    logger.info(f"💰 交易模式: 真实交易模式")
    logger.info(f"🔧 交易接口: EasyXT (高级封装)")
    logger.info("=" * 80)

def safety_confirmation():
    """安全确认流程"""
    logger.info("\n⚠️" + "⚠️" * 19)
    logger.info("重要安全提醒")
    logger.info("⚠️" + "⚠️" * 19)
    logger.info("此版本将执行真实交易操作！")
    logger.info("- 系统启动时会立即根据雪球组合进行调仓")
    logger.info("- 会使用您的真实资金进行买卖")
    logger.info("- 存在盈亏风险")
    logger.info("- 请确保您了解相关风险")
    logger.info("⚠️" + "⚠️" * 19)
    
    # 第一重确认
    confirm1 = input("\n🔐 第一重确认 - 输入 'YES' 确认启动真实交易: ").strip()
    if confirm1 != "YES":
        logger.info("❌ 用户取消启动")
        return False
    
    # 第二重确认
    confirm2 = input("🔐 第二重确认 - 输入 'SYNC' 确认立即同步调仓: ").strip()
    if confirm2 != "SYNC":
        logger.info("❌ 用户取消启动")
        return False
    
    # 第三重确认
    confirm3 = input("🔐 第三重确认 - 输入 'START' 最终确认: ").strip()
    if confirm3 != "START":
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

def export_holdings_to_excel(holdings, portfolio_code, export_dir=None):
    """导出持仓数据到Excel文件（固定文件名覆盖写，受配置开关控制）"""
    try:
        # 读取统一配置以确定导出开关与目录
        export_enabled = False
        export_dir_name = "reports"
        try:
            cfg_path = Path(__file__).parent / "config" / "unified_config.json"
            if cfg_path.exists():
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                # 尝试两种键路径
                export_enabled = (
                    (cfg.get('settings', {}).get('export_holdings')) or
                    cfg.get('导出持仓') or
                    False
                )
                export_dir_name = (cfg.get('settings', {}).get('export_dir')) or "reports"
        except Exception:
            pass

        if not export_enabled:
            logger.info("ℹ️ 导出开关关闭（settings.export_holdings/导出持仓），跳过Excel导出")
            return None

        # 导出目录
        if export_dir is None:
            export_dir = Path(__file__).parent.parent.parent / export_dir_name
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        # 创建DataFrame（增加类型检查与安全默认）
        df_data = []
        for holding in holdings:
            if not isinstance(holding, dict):
                continue
            weight = holding.get('weight', 0) or 0
            try:
                weight_pct = float(weight) * 100.0
            except Exception:
                weight_pct = 0.0
            df_data.append({
                '股票代码': holding.get('stock_symbol', '') or '',
                '股票名称': holding.get('stock_name', '') or '',
                '持仓比例(%)': weight_pct,
                '持仓市值': holding.get('market_value', 0) or 0,
                '持仓数量': holding.get('quantity', 0) or 0,
                '成本价': holding.get('cost_price', 0) or 0,
                '当前价': holding.get('current_price', 0) or 0
            })
        df = pd.DataFrame(df_data)
        if not df.empty:
            df = df.sort_values('持仓比例(%)', ascending=False)

        # 固定文件名，覆盖写
        filename = f"{portfolio_code}_持仓数据.xlsx"
        filepath = export_path / filename

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='持仓明细', index=False)
            summary_data = {
                '项目': ['组合代码', '持仓数量', '导出时间'],
                '数值': [portfolio_code, len(holdings), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='汇总信息', index=False)

        logger.info(f"✅ 持仓数据已导出到: {filepath}（覆盖写）")
        return filepath

    except Exception as e:
        logger.info(f"❌ Excel导出失败: {e}")
        return None

def test_easyxt_connection(config):
    """测试 easy_xt 连接"""
    try:
        logger.info("\n🔧 测试 EasyXT 交易API连接...")
        
        # 先尝试导入 xtquant
        try:
            # 添加 xtquant 路径
            xtquant_path = project_root / "xtquant"
            if str(xtquant_path) not in sys.path:
                sys.path.insert(0, str(xtquant_path))
            
            import xtquant.xttrader as xt
            logger.info("xtquant高级交易模块导入成功")
        except ImportError as e:
            logger.info(f"⚠️ xtquant高级交易模块导入失败: {e}")
        
        # 导入 easy_xt
        from easy_xt.advanced_trade_api import AdvancedTradeAPI
        
        # 获取配置
        qmt_path = config['settings']['account'].get('qmt_path')
        account_id = config['settings']['account']['account_id']
        
        # 检查QMT路径是否存在
        if not qmt_path:
            logger.info("❌ EasyXT 连接测试失败: 'qmt_path'")
            return False
            
        if not os.path.exists(qmt_path):
            logger.info(f"❌ QMT路径不存在: {qmt_path}")
            logger.info("💡 请检查配置文件中的QMT路径设置")
            return False
        
        logger.info(f"📁 QMT路径: {qmt_path}")
        logger.info(f"🏦 交易账号: {account_id}")
        
        # 创建高级交易API
        session_id = f"xueqiu_test_{int(time.time())}"
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

async def test_portfolio_data():
    """测试模式：直接获取组合持仓数据"""
    logger.info("🔧 测试模式：直接获取组合持仓数据")
    
    # 加载配置
    config = load_config()
    if not config:
        logger.info("❌ 配置加载失败")
        return
    
    # 获取启用组合
    try:
        from strategies.xueqiu_follow.internal.config_manager import ConfigManager
        config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
        config_manager.load_all_configs()
        enabled_portfolios = config_manager.get_enabled_portfolios()
        
        if not enabled_portfolios:
            logger.info("❌ 没有启用的组合")
            return
        
        portfolio = enabled_portfolios[0]
        portfolio_code = portfolio.get('code', portfolio.get('symbol', '未知'))
        logger.info(f"📊 测试组合: {portfolio['name']} ({portfolio_code})")
        
        # 初始化数据采集器
        logger.info("🚀 初始化数据采集器...")
        from strategies.xueqiu_follow.internal.xueqiu_collector_real import XueqiuCollectorReal
        collector = XueqiuCollectorReal()
        
        # 初始化采集器
        logger.info("🔧 初始化HTTP会话...")
        if not await collector.initialize():
            logger.info("❌ 数据采集器初始化失败")
            return
        
        # 测试获取组合持仓
        logger.info("📡 尝试获取组合持仓数据...")
        holdings = await collector.get_portfolio_holdings(portfolio_code)
        
        if holdings:
            logger.info(f"✅ 成功获取到 {len(holdings)} 个持仓")
            for i, holding in enumerate(holdings[:5]):  # 只显示前5个
                stock_name = holding.get('stock_name', 'N/A')
                stock_symbol = holding.get('stock_symbol', 'N/A')
                weight = holding.get('weight', 0)
                logger.info(f"  {i+1}. {stock_name} ({stock_symbol}) - {weight:.2%}")
            if len(holdings) > 5:
                logger.info(f"  ... 还有 {len(holdings) - 5} 个持仓")
        else:
            logger.info("❌ 未能获取到持仓数据")
            
    except Exception as e:
        logger.info(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

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
        account_settings = config['settings'].get('account', {})
        trading_settings = config['settings'].get('trading', {})

        account_id = account_settings.get('account_id', '未配置')
        qmt_path = account_settings.get('qmt_path', '未配置')

        logger.info(f"   🏦 交易账号: {account_id}")
        logger.info(f"   📁 QMT路径: {qmt_path}")

        # 获取启用的组合（使用配置管理器）
        try:
            from strategies.xueqiu_follow.internal.config_manager import ConfigManager
            config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
            config_manager.load_all_configs()  # 确保加载所有配置
            enabled_portfolios = config_manager.get_setting("portfolios", [])
            
            if enabled_portfolios:
                # 过滤启用的组合
                enabled_list = [p for p in enabled_portfolios if p.get('enabled', True)]
                if enabled_list:
                    portfolio = enabled_list[0]
                    portfolio_code = portfolio.get('code', portfolio.get('symbol', '未知'))
                    logger.info(f"   📊 跟单组合: {portfolio.get('url', f'https://xueqiu.com/P/{portfolio_code}')}")
                    follow_ratio = portfolio.get('follow_ratio')
                    if follow_ratio is not None:
                        logger.info(f"   📈 跟随比例: {follow_ratio:.1%}")
                    logger.info(f"   💰 最大仓位: {portfolio.get('max_position', 8000)}元")
        except Exception as e:
            logger.info(f"⚠️ 组合配置加载警告: {e}")
            # 回退到直接读取配置
            enabled_portfolios = []
            for portfolio_code, portfolio_config in config.get('portfolios', {}).items():
                if portfolio_config.get('enabled', False):
                    enabled_portfolios.append((portfolio_code, portfolio_config))
            
            if enabled_portfolios:
                portfolio_code, portfolio = enabled_portfolios[0]
                logger.info(f"   📊 跟单组合: {portfolio.get('url', f'https://xueqiu.com/P/{portfolio_code}')}")
                follow_ratio = portfolio.get('follow_ratio')
                if follow_ratio is not None:
                    logger.info(f"   📈 跟随比例: {follow_ratio:.1%}")
                logger.info(f"   💰 最大仓位: {portfolio.get('max_position', 8000)}元")

        logger.info(f"   💸 最大单笔: {trading_settings.get('max_single_amount', 5000)}元")
        logger.info(f"   💰 最小交易: {trading_settings.get('min_trade_amount', 100)}元")

        
        # 测试 EasyXT 连接
        if not test_easyxt_connection(config):
            logger.info("❌ EasyXT 连接测试失败，无法启动真实交易")
            return
        
        logger.info("\n🚀 启动雪球跟单系统...")

        # 初始化配置管理器，使用真实交易配置
        from strategies.xueqiu_follow.internal.config_manager import ConfigManager
        config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
        
        # 手动设置账户ID到配置管理器
        config_manager.set_setting('settings.account.account_id', config['settings']['account']['account_id'])
        config_manager.set_setting('account.account_id', config['settings']['account']['account_id'])
        
        # 使用统一配置管理器，无需额外加载
        
        # 初始化策略引擎
        from strategies.xueqiu_follow.internal.strategy_engine import StrategyEngine
        strategy_engine = StrategyEngine(config_manager)
        
        # 初始化策略引擎
        logger.info("🔧 初始化策略引擎...")
        if not await strategy_engine.initialize():
            logger.info("❌ 策略引擎初始化失败")
            return
        
        logger.info("✅ 策略引擎初始化成功")
        logger.info("\n🔄 系统将首先执行初始同步调仓，然后开始监控组合变化...")
        # 获取启用的组合代码（使用配置管理器）
        portfolio_code = None
        try:
            # 正确获取组合列表：从_portfolios字典中获取portfolios键的值
            if isinstance(config_manager._portfolios, dict) and 'portfolios' in config_manager._portfolios:
                all_portfolios = config_manager._portfolios['portfolios']
            else:
                all_portfolios = []
            
            # 过滤启用的组合
            enabled_portfolios = [p for p in all_portfolios if p.get('enabled', False)]
            
            if enabled_portfolios:
                portfolio = enabled_portfolios[0]
                portfolio_code = portfolio.get('code', portfolio.get('symbol', None))
                logger.info(f"✅ 使用组合: {portfolio.get('name', '未知')} ({portfolio_code})")
            else:
                portfolio_code = None
                logger.info("❌ 没有启用的组合")
        except Exception as e:
            logger.info(f"⚠️ 组合配置加载警告: {e}")
            # 回退到直接读取配置
            for code, portfolio_config in config.get('portfolios', {}).items():
                if portfolio_config.get('enabled', False):
                    portfolio_code = code
                    break
        
        if not portfolio_code:
            logger.info("❌ 没有启用的组合")
            return
        
        logger.info(f"📊 正在获取雪球组合 {portfolio_code} 的当前持仓...")
        
        # 启动策略（包含初始同步）
        logger.info("\n🎯 开始执行策略...")
        await strategy_engine.start()
        
    except KeyboardInterrupt:
        logger.info(f"\n\n⚠️ 收到停止信号，正在安全关闭系统...")
        if 'strategy_engine' in locals():
            await strategy_engine.stop()
        logger.info("👋 系统已安全关闭")
        
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        logger.info(f"❌ 系统异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_portfolio_data())
    else:
        asyncio.run(main())