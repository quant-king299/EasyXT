#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件验证脚本
验证统一配置文件的完整性和正确性
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List


class ConfigValidator:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.errors = []
        self.warnings = []
    
    def validate_unified_config(self) -> bool:
        """验证统一配置文件"""
        unified_path = self.config_dir / "unified_config.json"
        
        if not unified_path.exists():
            self.errors.append("统一配置文件不存在")
            return False
        
        try:
            with open(unified_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            self.errors.append(f"配置文件格式错误: {e}")
            return False
        
        # 验证必需字段
        required_fields = ['version', 'settings']
        for field in required_fields:
            if field not in config:
                self.errors.append(f"缺少必需字段: {field}")
        
        # 验证设置配置
        if 'settings' in config:
            settings = config['settings']
            
            # 验证账户配置
            if 'account' in settings:
                account_config = settings['account']
                if 'qmt_path' not in account_config or not account_config['qmt_path']:
                    self.warnings.append("QMT路径未设置，系统将尝试自动检测")
                
                if 'account_id' not in account_config or not account_config['account_id']:
                    self.warnings.append("账户ID未设置")
            else:
                self.errors.append("缺少账户配置")
            
            # 验证风险配置
            if 'risk' in settings:
                risk_config = settings['risk']
                if 'max_position_ratio' in risk_config:
                    ratio = risk_config['max_position_ratio']
                    if not (0 < ratio <= 1):
                        self.errors.append("最大持仓比例必须在0-1之间")
                
                if 'stop_loss_ratio' in risk_config:
                    ratio = risk_config['stop_loss_ratio']
                    if not (0 <= ratio <= 1):
                        self.errors.append("止损比例必须在0-1之间")
            else:
                self.warnings.append("缺少风险配置")
            
            # 验证监控配置
            if 'monitoring' in settings:
                monitoring_config = settings['monitoring']
                if 'check_interval' in monitoring_config:
                    interval = monitoring_config['check_interval']
                    if interval < 10:
                        self.warnings.append("检查间隔过短，建议至少10秒")
            else:
                self.warnings.append("缺少监控配置")
        
        # 验证组合配置
        if 'portfolios' in config:
            portfolios = config['portfolios']
            if not isinstance(portfolios, dict):
                self.errors.append("组合配置格式错误，应为字典格式")
            elif not portfolios:
                self.warnings.append("组合配置为空")
        
        # 验证QMT路径
        if 'settings' in config and 'account' in config['settings']:
            account_config = config['settings']['account']
            if 'qmt_path' in account_config:
                qmt_path = account_config['qmt_path']
                if qmt_path and not os.path.exists(qmt_path):
                    self.warnings.append(f"QMT路径不存在: {qmt_path}")
        
        return len(self.errors) == 0
    
    def auto_fix_qmt_path(self) -> bool:
        """自动修复QMT路径"""
        unified_path = self.config_dir / "unified_config.json"
        
        if not unified_path.exists():
            return False
        
        try:
            with open(unified_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            return False
        
        # 检查是否需要修复QMT路径
        if 'settings' not in config or 'account' not in config['settings']:
            return False
        
        account_config = config['settings']['account']
        qmt_path = account_config.get('qmt_path', '')
        
        # 如果QMT路径不存在，尝试自动检测
        if not qmt_path or not os.path.exists(qmt_path):
            detected_path = self._detect_qmt_path()
            if detected_path:
                account_config['qmt_path'] = detected_path
                config['account'] = account_config
                
                # 保存修复后的配置
                with open(unified_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                print(f"已自动修复QMT路径: {detected_path}")
                return True
        
        return False
    
    def _detect_qmt_path(self) -> str:
        """自动检测QMT路径"""
        common_paths = [
            "C:/QMT/",
            "D:/QMT/",
            "E:/QMT/",
            "C:/Program Files/QMT/",
            "D:/Program Files/QMT/",
            "C:/迅投/QMT/",
            "D:/迅投/QMT/"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                # 检查是否是有效的QMT目录
                exe_files = ["QMT.exe", "QMTClient.exe", "bin/QMT.exe"]
                if any(os.path.exists(os.path.join(path, exe)) for exe in exe_files):
                    return path
        
        # 检查环境变量
        env_vars = ['QMT_HOME', 'QMT_PATH', 'QMT_DIR']
        for env_var in env_vars:
            path = os.environ.get(env_var, '')
            if path and os.path.exists(path):
                return path
        
        return ""
    
    def print_report(self):
        """打印验证报告"""
        print("=" * 50)
        print("配置文件验证报告")
        print("=" * 50)
        
        if self.errors:
            print("❌ 错误:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("⚠️  警告:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ 配置文件验证通过")
        
        print("=" * 50)


def main():
    """主函数"""
    config_dir = Path(__file__).parent
    validator = ConfigValidator(config_dir)
    
    print("开始验证配置文件...")
    
    # 验证配置文件
    is_valid = validator.validate_unified_config()
    
    # 尝试自动修复QMT路径
    if any("QMT路径" in warning for warning in validator.warnings):
        print("尝试自动修复QMT路径...")
        validator.auto_fix_qmt_path()
    
    # 打印验证报告
    validator.print_report()
    
    if not is_valid:
        print("\n❌ 配置文件存在错误，请修复后重试")
        sys.exit(1)
    else:
        print("\n✅ 配置文件验证完成")


if __name__ == "__main__":
    main()