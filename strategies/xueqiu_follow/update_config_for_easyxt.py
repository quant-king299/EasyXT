# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
配置更新脚本 - 迁移到 EasyXT
将现有的雪球跟单配置更新为使用 easy_xt 模块
"""

import os
import sys
import json
import shutil
from datetime import datetime
from typing import Dict, Any

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from easy_xt.config import config as qmt_config
    easy_xt_available = True
except ImportError:
    easy_xt_available = False

def print_banner():
    """打印横幅"""
    logger.info("=" * 60)
    logger.info("🔧 雪球跟单配置更新工具")
    logger.info("   迁移到 EasyXT 模块")
    logger.info("=" * 60)
    logger.info(f"⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

def backup_config():
    """备份现有配置"""
    try:
        config_path = os.path.join(current_dir, 'config', 'unified_config.json')
        if not os.path.exists(config_path):
            logger.info("⚠️ 未找到现有配置文件")
            return False
        
        # 创建备份
        backup_path = os.path.join(current_dir, 'config', f'default_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        shutil.copy2(config_path, backup_path)
        
        logger.info(f"✅ 配置已备份到: {os.path.basename(backup_path)}")
        return True
        
    except Exception as e:
        logger.info(f"❌ 配置备份失败: {e}")
        return False

def load_current_config() -> Dict[str, Any]:
    """加载当前配置"""
    try:
        config_path = os.path.join(current_dir, 'config', 'unified_config.json')
        
        if not os.path.exists(config_path):
            logger.info("❌ 配置文件不存在")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        logger.info("✅ 当前配置加载成功")
        return config_data
        
    except Exception as e:
        logger.info(f"❌ 配置加载失败: {e}")
        return None

def detect_qmt_config() -> Dict[str, Any]:
    """检测 QMT 配置"""
    qmt_info = {
        'detected': False,
        'qmt_path': None,
        'userdata_path': None,
        'auto_detected': False
    }
    
    if not easy_xt_available:
        logger.info("❌ easy_xt 模块不可用")
        return qmt_info
    
    try:
        logger.info("🔍 检测 QMT 配置...")
        
        # 尝试自动检测
        is_valid, msg = qmt_config.validate_qmt_setup()
        
        if is_valid:
            qmt_info.update({
                'detected': True,
                'qmt_path': qmt_config.get_qmt_path(),
                'userdata_path': qmt_config.get_userdata_path(),
                'auto_detected': True
            })
            logger.info(f"✅ 自动检测成功: {msg}")
        else:
            logger.info(f"⚠️ 自动检测失败: {msg}")
            qmt_info['detected'] = False
        
        return qmt_info
        
    except Exception as e:
        logger.info(f"❌ QMT 检测异常: {e}")
        return qmt_info

def manual_qmt_setup(current_config: Dict[str, Any]) -> Dict[str, Any]:
    """手动设置 QMT 配置"""
    if not easy_xt_available:
        return {'detected': False}
    
    try:
        # 从当前配置获取 QMT 路径
        current_qmt_path = current_config.get('settings', {}).get('account', {}).get('qmt_path', '')
        
        if current_qmt_path:
            logger.info(f"📁 当前配置的 QMT 路径: {current_qmt_path}")
            
            # 提取基础路径
            if current_qmt_path.endswith('/userdata_mini') or current_qmt_path.endswith('\\userdata_mini'):
                base_path = os.path.dirname(current_qmt_path)
            else:
                base_path = current_qmt_path
            
            logger.info(f"🔧 尝试设置 QMT 基础路径: {base_path}")
            
            if qmt_config.set_qmt_path(base_path):
                return {
                    'detected': True,
                    'qmt_path': qmt_config.get_qmt_path(),
                    'userdata_path': qmt_config.get_userdata_path(),
                    'auto_detected': False
                }
            else:
                logger.info("❌ 手动设置失败")
        
        return {'detected': False}
        
    except Exception as e:
        logger.info(f"❌ 手动设置异常: {e}")
        return {'detected': False}

def update_config_structure(config_data: Dict[str, Any], qmt_info: Dict[str, Any]) -> Dict[str, Any]:
    """更新配置结构"""
    try:
        logger.info("🔧 更新配置结构...")
        
        # 确保基础结构存在
        if 'settings' not in config_data:
            config_data['settings'] = {}
        
        # 更新 QMT 配置
        if qmt_info['detected']:
            config_data['settings']['account']['qmt_path'] = qmt_info['userdata_path']
            logger.info(f"✅ 更新 QMT 路径: {qmt_info['userdata_path']}")
        
        # 添加 EasyXT 特定配置
        config_data['settings']['qmt'] = {
            'session_id': 'xueqiu_follow',
            'api_type': 'advanced',
            'auto_retry': True,
            'retry_count': 3,
            'timeout': 30,
            'max_concurrent_orders': 10,
            'order_timeout': 30,
            'retry_delay': 1
        }
        
        # 添加 EasyXT 标识
        config_data['system'] = {
            'version': '1.0',
            'api_provider': 'easy_xt',
            'updated_at': datetime.now().isoformat(),
            'qmt_auto_detected': qmt_info.get('auto_detected', False)
        }
        
        # 确保安全配置存在
        if 'safety' not in config_data:
            config_data['safety'] = {}
        
        config_data['safety'].update({
            'auto_confirm': True,
            'require_manual_confirm': False,
            'max_daily_trades': 50,
            'max_daily_amount': 50000,
            'risk_check': True
        })
        
        logger.info("✅ 配置结构更新完成")
        return config_data
        
    except Exception as e:
        logger.info(f"❌ 配置结构更新失败: {e}")
        return config_data

def save_updated_config(config_data: Dict[str, Any]) -> bool:
    """保存更新后的配置"""
    try:
        config_path = os.path.join(current_dir, 'config', 'unified_config.json')
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        logger.info("✅ 更新后的配置已保存")
        return True
        
    except Exception as e:
        logger.info(f"❌ 配置保存失败: {e}")
        return False

def validate_updated_config(config_data: Dict[str, Any]) -> bool:
    """验证更新后的配置"""
    try:
        logger.info("🔍 验证更新后的配置...")
        
        # 检查必要字段
        required_fields = [
            'settings.account.account_id',
            'settings.account.qmt_path',
            'settings.qmt.session_id',
            'settings.qmt.api_type',
            'portfolios'
        ]
        
        for field in required_fields:
            keys = field.split('.')
            value = config_data
            
            for key in keys:
                if key not in value:
                    logger.info(f"❌ 缺少必要字段: {field}")
                    return False
                value = value[key]
        
        # 检查 QMT 路径
        qmt_path = config_data['settings']['account']['qmt_path']
        if not os.path.exists(qmt_path):
            logger.info(f"❌ QMT 路径不存在: {qmt_path}")
            return False
        
        # 检查组合配置
        portfolios = config_data.get('portfolios', {})
        if not portfolios:
            logger.info("❌ 未配置跟单组合")
            return False
        
        logger.info("✅ 配置验证通过")
        return True
        
    except Exception as e:
        logger.info(f"❌ 配置验证异常: {e}")
        return False

def print_config_summary(config_data: Dict[str, Any]):
    """打印配置摘要"""
    try:
        logger.info("\n" + "=" * 50)
        logger.info("📋 更新后的配置摘要")
        logger.info("=" * 50)
        
        # 基本信息
        account_id = config_data['settings']['account']['account_id']
        qmt_path = config_data['settings']['account']['qmt_path']
        trade_mode = config_data['settings']['trading']['trade_mode']
        
        logger.info(f"🏦 交易账号: {account_id}")
        logger.info(f"📁 QMT 路径: {qmt_path}")
        logger.info(f"💼 交易模式: {trade_mode}")
        
        # QMT 配置
        qmt_config_data = config_data['settings']['qmt']
        logger.info(f"🔧 API 类型: {qmt_config_data['api_type']}")
        logger.info(f"🆔 会话 ID: {qmt_config_data['session_id']}")
        logger.info(f"🔄 自动重试: {qmt_config_data['auto_retry']}")
        
        # 跟单组合
        portfolios = config_data['portfolios']
        logger.info(f"📊 跟单组合: {len(portfolios)} 个")
        for portfolio_id, portfolio_info in portfolios.items():
            logger.info(f"   - {portfolio_id}: {portfolio_info['name']}")
        
        # 系统信息
        system_info = config_data.get('system', {})
        logger.info(f"🏷️ 系统版本: {system_info.get('version', 'unknown')}")
        logger.info(f"🔌 API 提供商: {system_info.get('api_provider', 'unknown')}")
        
        logger.info("=" * 50)
        
    except Exception as e:
        logger.info(f"❌ 配置摘要显示失败: {e}")

def main():
    """主函数"""
    print_banner()
    
    # 1. 检查 easy_xt 可用性
    if not easy_xt_available:
        logger.info("❌ easy_xt 模块不可用")
        logger.info("请确保 easy_xt 模块已正确安装")
        return
    
    logger.info("✅ easy_xt 模块可用")
    
    # 2. 备份现有配置
    if not backup_config():
        return
    
    # 3. 加载当前配置
    current_config = load_current_config()
    if not current_config:
        return
    
    # 4. 检测 QMT 配置
    qmt_info = detect_qmt_config()
    
    if not qmt_info['detected']:
        logger.info("🔧 尝试手动设置 QMT 配置...")
        qmt_info = manual_qmt_setup(current_config)
    
    if not qmt_info['detected']:
        logger.info("❌ 无法检测或设置 QMT 配置")
        logger.info("请手动配置 QMT 路径后重试")
        return
    
    # 5. 更新配置结构
    updated_config = update_config_structure(current_config, qmt_info)
    
    # 6. 验证配置
    if not validate_updated_config(updated_config):
        logger.info("❌ 配置验证失败")
        return
    
    # 7. 保存配置
    if not save_updated_config(updated_config):
        return
    
    # 8. 显示摘要
    print_config_summary(updated_config)
    
    logger.info("\n🎉 配置更新完成！")
    logger.info("\n📝 后续步骤:")
    logger.info("1. 运行测试脚本验证配置:")
    logger.info("   python test_qmt_connection.py")
    logger.info("2. 启动雪球跟单系统:")
    logger.info("   python start_xueqiu_follow_easyxt.py")
    logger.info("   或双击: 启动雪球跟单_EasyXT.bat")

if __name__ == "__main__":
    main()