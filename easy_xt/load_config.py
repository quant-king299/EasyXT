"""
配置加载模块
提供从统一配置文件加载配置的功能
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

def load_unified_config() -> Optional[Dict[str, Any]]:
    """
    加载统一配置文件
    
    Returns:
        Optional[Dict[str, Any]]: 配置字典，如果加载失败则返回None
    """
    # 定义可能的配置文件路径
    possible_paths = [
        # 项目根目录下的config目录
        Path(__file__).parent.parent / "config" / "unified_config.json",
        # 当前工作目录下的config目录
        Path.cwd() / "config" / "unified_config.json",
        # 策略目录下的config目录
        Path(__file__).parent.parent / "strategies" / "xueqiu_follow" / "config" / "unified_config.json"
    ]
    
    # 尝试加载配置文件
    for config_path in possible_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                print(f"✅ 成功加载统一配置文件: {config_path}")
                return config_data
            except Exception as e:
                print(f"⚠️ 配置文件加载失败 {config_path}: {e}")
    
    print("❌ 未找到统一配置文件")
    return None

def update_config_with_unified_settings(config_instance) -> bool:
    """
    使用统一配置文件更新配置实例
    
    Args:
        config_instance: EasyXT配置实例
        
    Returns:
        bool: 是否成功更新配置
    """
    # 加载统一配置
    unified_config = load_unified_config()
    if not unified_config:
        return False
    
    # 更新账户配置
    account_config = unified_config.get('settings', {}).get('account', {})
    if account_config:
        # 更新账户ID
        account_id = account_config.get('account_id')
        if account_id:
            config_instance.set('settings.account.account_id', account_id)
        
        # 更新QMT路径
        qmt_path = account_config.get('qmt_path')
        if qmt_path:
            # 检查路径是否已经包含userdata_mini子目录
            if 'userdata_mini' in qmt_path or 'userdata' in qmt_path:
                # 如果已经包含userdata路径，直接设置
                if os.path.exists(qmt_path):
                    config_instance.settings['trade']['userdata_path'] = qmt_path
                    config_instance.settings['qmt']['detected_path'] = os.path.dirname(qmt_path)
            else:
                # 否则使用原始逻辑设置QMT路径
                config_instance.set_qmt_path(qmt_path)
    
    return True