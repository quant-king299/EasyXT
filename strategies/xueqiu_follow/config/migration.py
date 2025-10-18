#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件迁移脚本
将多个配置文件整合到统一的配置文件中
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigMigration:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.unified_config = {}
    
    def load_existing_configs(self) -> Dict[str, Any]:
        """加载所有现有的配置文件"""
        configs = {}
        
        # 加载default.json
        default_path = self.config_dir / "default.json"
        if default_path.exists():
            with open(default_path, 'r', encoding='utf-8') as f:
                configs['default'] = json.load(f)
        
        # 加载settings.json
        settings_path = self.config_dir / "settings.json"
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                configs['settings'] = json.load(f)
        
        # 加载portfolios.json
        portfolios_path = self.config_dir / "portfolios.json"
        if portfolios_path.exists():
            with open(portfolios_path, 'r', encoding='utf-8') as f:
                configs['portfolios'] = json.load(f)
        
        # 加载xueqiu_config.json
        xueqiu_path = self.config_dir / "xueqiu_config.json"
        if xueqiu_path.exists():
            with open(xueqiu_path, 'r', encoding='utf-8') as f:
                configs['xueqiu'] = json.load(f)
        
        # 加载real_trading.json
        real_trading_path = self.config_dir / "real_trading.json"
        if real_trading_path.exists():
            with open(real_trading_path, 'r', encoding='utf-8') as f:
                configs['real_trading'] = json.load(f)
        
        return configs
    
    def merge_configs(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """合并所有配置文件到统一格式"""
        unified = {
            "version": "3.0",
            "description": "雪球跟单系统统一配置文件",
            "last_updated": "2025-10-02",
            "config_source": "migrated_from_multiple_files"
        }
        
        # 合并主设置
        if 'default' in configs:
            unified.update(configs['default'])
        elif 'settings' in configs:
            unified.update(configs['settings'])
        
        # 合并组合配置
        if 'portfolios' in configs:
            unified['portfolios'] = configs['portfolios']
        
        # 合并雪球配置
        if 'xueqiu' in configs:
            unified['xueqiu_settings'] = configs['xueqiu']
        
        # 合并实盘交易配置
        if 'real_trading' in configs:
            unified['trading_settings'] = configs['real_trading']
        
        return unified
    
    def backup_old_configs(self):
        """备份旧的配置文件"""
        backup_dir = self.config_dir / "backup"
        backup_dir.mkdir(exist_ok=True)
        
        config_files = [
            "default.json", "settings.json", "portfolios.json",
            "xueqiu_config.json", "real_trading.json", "production_template.json"
        ]
        
        for config_file in config_files:
            source_path = self.config_dir / config_file
            if source_path.exists():
                backup_path = backup_dir / f"{config_file}.backup"
                shutil.copy2(source_path, backup_path)
                print(f"已备份: {config_file} -> {backup_path}")
    
    def create_unified_config(self):
        """创建统一配置文件"""
        print("开始迁移配置文件...")
        
        # 加载现有配置
        existing_configs = self.load_existing_configs()
        print(f"找到 {len(existing_configs)} 个配置文件")
        
        # 合并配置
        unified_config = self.merge_configs(existing_configs)
        
        # 保存统一配置文件
        unified_path = self.config_dir / "unified_config.json"
        with open(unified_path, 'w', encoding='utf-8') as f:
            json.dump(unified_config, f, ensure_ascii=False, indent=2)
        
        print(f"统一配置文件已创建: {unified_path}")
        
        # 备份旧配置文件
        self.backup_old_configs()
        
        print("配置文件迁移完成！")
        
        return unified_config


def main():
    """主函数"""
    config_dir = Path(__file__).parent
    migrator = ConfigMigration(config_dir)
    
    try:
        migrator.create_unified_config()
        print("\n迁移成功！系统现在使用统一配置文件。")
        print("旧的配置文件已备份到 backup/ 目录。")
    except Exception as e:
        print(f"迁移失败: {e}")


if __name__ == "__main__":
    main()