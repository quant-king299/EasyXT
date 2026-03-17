"""
配置管理器模块
负责配置文件的加载、保存、验证和运行时修改
"""

import json
import os
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
# from ..utils.crypto_utils import encrypt_password, decrypt_password

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: str = "config/default.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 主配置文件路径
        """
        # 使用绝对路径，基于当前文件位置
        # 获取当前文件所在目录（config_manager.py所在目录）
        current_file_dir = Path(__file__).parent
        # 正确的配置目录路径（上一级目录的config文件夹）
        self.config_dir = current_file_dir.parent / "config"
        
        # 调试信息：显示实际路径
        logger.debug(f"当前文件目录: {current_file_dir}")
        logger.debug(f"配置目录路径: {self.config_dir}")
        
        # 处理传入的配置文件路径
        if config_file and config_file != "config/default.json":
            # 如果是相对路径，转换为绝对路径
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = self.config_dir.parent / config_path
            self.settings_file = config_path
        else:
            self.settings_file = self.config_dir / "default.json"
            
        self.portfolios_file = self.config_dir / "portfolios.json"
        
        # 调试信息：显示实际路径
        logger.debug(f"配置文件路径: {self.settings_file}")
        logger.debug(f"组合文件路径: {self.portfolios_file}")
        
        # 确保配置目录存在（使用parents=True创建父目录）
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置缓存
        self._settings = {}
        self._portfolios = {}
        
        # 线程锁，确保配置修改的线程安全
        self._lock = threading.RLock()
        
        # 加载配置
        self.load_all_configs()
    
    def load_all_configs(self):
        """加载所有配置文件"""
        with self._lock:
            self._load_settings()
            self._load_portfolios()
    
    def _load_settings(self):
        """加载主配置文件"""
        try:
            # 首先尝试加载统一配置文件
            unified_config_path = self.config_dir / "unified_config.json"
            if unified_config_path.exists():
                with open(unified_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 加载完整的统一配置，包括settings、xueqiu_settings、xueqiu等所有部分
                self._settings = config_data
                
                logger.info("统一配置文件加载成功")
                
                # 然后尝试加载雪球专用配置文件并合并配置
                xueqiu_config_path = self.config_dir / "xueqiu_config.json"
                if xueqiu_config_path.exists():
                    with open(xueqiu_config_path, 'r', encoding='utf-8') as f:
                        xueqiu_config_data = json.load(f)
                    
                    # 深度合并雪球配置到主配置中
                    self._merge_configs(self._settings, xueqiu_config_data)
                    logger.info("雪球专用配置文件加载并合并成功")
            elif self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 从default.json中提取settings部分
                if 'settings' in config_data:
                    self._settings = config_data['settings']
                else:
                    self._settings = config_data
                
                logger.info("默认配置文件加载成功")
                
                # 解密密码
                if 'account' in self._settings and 'password' in self._settings['account']:
                    encrypted_password = self._settings['account']['password']
                    if encrypted_password and len(encrypted_password) > 10:  # 只有加密的密码才解密
                        try:
                            self._settings['account']['password'] = decrypt_password(encrypted_password)
                        except Exception as e:
                            logger.warning(f"密码解密失败: {e}")
                            # 如果解密失败，可能是明文密码，保持原样
                
                logger.info("主配置文件加载成功")
            else:
                self._settings = self._get_default_settings()
                self.save_settings()
                logger.info("创建默认主配置文件")
                
        except Exception as e:
            logger.error(f"加载主配置文件失败: {e}")
            self._settings = self._get_default_settings()
    
    def _merge_configs(self, base_config: Dict[str, Any], new_config: Dict[str, Any]):
        """
        深度合并两个配置字典
        
        Args:
            base_config: 基础配置（会被修改）
            new_config: 要合并的新配置
        """
        for key, value in new_config.items():
            if key in base_config:
                # 如果两个值都是字典，递归合并
                if isinstance(base_config[key], dict) and isinstance(value, dict):
                    self._merge_configs(base_config[key], value)
                else:
                    # 否则用新值覆盖旧值
                    base_config[key] = value
            else:
                # 如果键不存在，直接添加
                base_config[key] = value
    
    def _load_portfolios(self):
        """加载组合配置文件"""
        try:
            # 优先尝试从统一配置文件加载
            unified_config_path = self.config_dir / "unified_config.json"
            if unified_config_path.exists():
                with open(unified_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if 'portfolios' in config_data:
                    # 直接使用字典格式，不转换为列表
                    self._portfolios = config_data['portfolios']
                    logger.info("从统一配置文件加载组合配置成功")
                    
                    # 然后尝试从雪球专用配置文件加载组合配置并合并
                    xueqiu_config_path = self.config_dir / "xueqiu_config.json"
                    if xueqiu_config_path.exists():
                        with open(xueqiu_config_path, 'r', encoding='utf-8') as f:
                            xueqiu_config_data = json.load(f)
                        
                        if 'portfolios' in xueqiu_config_data:
                            self._merge_configs(self._portfolios, xueqiu_config_data['portfolios'])
                            logger.info("从雪球专用配置文件加载组合配置并合并成功")
                    return
            
            # 其次加载单独的portfolios.json文件
            if self.portfolios_file.exists():
                with open(self.portfolios_file, 'r', encoding='utf-8') as f:
                    self._portfolios = json.load(f)
                logger.info("组合配置文件加载成功")
                return
            
            # 最后尝试从default.json加载组合配置
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if 'portfolios' in config_data:
                    # 直接使用字典格式，不转换为列表
                    self._portfolios = config_data['portfolios']
                    logger.info("从主配置文件加载组合配置成功")
                    return
            
            # 如果都没有，创建默认配置
            self._portfolios = self._get_default_portfolios()
            self.save_portfolios()
            logger.info("创建默认组合配置文件")
                
        except Exception as e:
            logger.error(f"加载组合配置文件失败: {e}")
            self._portfolios = self._get_default_portfolios()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """获取默认主配置"""
        return {
            "account": {
                "qmt_path": "C:/QMT/",
                "account_id": "",
                "password": "",
                "auto_detect_qmt": True
            },
            "risk": {
                "max_position_ratio": 0.1,
                "stop_loss_ratio": 0.05,
                "max_total_exposure": 0.8,
                "blacklist": ["ST*", "*ST"],
                "emergency_stop": False
            },
            "monitoring": {
                "check_interval": 30,
                "retry_times": 3,
                "timeout": 10,
                "max_delay": 3,
                "health_check_interval": 300
            },
            "logging": {
                "level": "INFO",
                "file": "logs/xueqiu_follow.log",
                "max_size": "10MB",
                "backup_count": 5,
                "enable_console": True
            },
            "trading": {
                "trade_mode": "paper_trading",
                "auto_confirm": True,
                "price_tolerance": 0.02,
                "min_trade_amount": 100
            }
        }
    
    def _get_default_portfolios(self) -> Dict[str, Any]:
        """获取默认组合配置"""
        return {
            "portfolios": [
                {
                    "name": "示例组合",
                    "code": "ZH000000",
                    "follow_ratio": 0.4,
                    "enabled": False,
                    "description": "这是一个示例配置，请修改为实际的雪球组合代码"
                }
            ],
            "global_settings": {
                "total_follow_ratio": 0.4,
                "auto_start": False,
                "emergency_stop": False
            }
        }
    
    def get_setting(self, key_path: str, default=None):
        """
        获取配置项
        
        Args:
            key_path: 配置项路径，如 'account.qmt_path'
            default: 默认值
            
        Returns:
            配置项值
        """
        with self._lock:
            keys = key_path.split('.')
            value = self._settings
            
            try:
                for key in keys:
                    value = value[key]
                # 确保返回正确的类型
                if value is None:
                    return default
                return value
            except (KeyError, TypeError):
                return default
    
    def set_setting(self, key_path: str, value: Any, save: bool = True):
        """
        设置配置项
        
        Args:
            key_path: 配置项路径，如 'account.qmt_path'
            value: 配置项值
            save: 是否立即保存到文件
        """
        with self._lock:
            keys = key_path.split('.')
            config = self._settings
            
            # 导航到目标位置
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 设置值
            config[keys[-1]] = value
            
            if save:
                self.save_settings()
    
    def get_portfolios(self) -> List[Dict[str, Any]]:
        """获取所有组合配置"""
        with self._lock:
            return self._portfolios.get('portfolios', []).copy()
    
    def get_enabled_portfolios(self) -> List[Dict[str, Any]]:
        """获取启用的组合配置"""
        with self._lock:
            # 处理两种格式：字典格式和列表格式
            # 首先检查是否是portfolios.json格式：{"portfolios": [...], "global_settings": {...}}
            if isinstance(self._portfolios, dict) and 'portfolios' in self._portfolios:
                # portfolios.json 格式
                return [p for p in self._portfolios['portfolios'] if p.get('enabled', False)]
            elif isinstance(self._portfolios, dict):
                # 如果是字典格式（从default.json加载的组合配置）
                enabled_portfolios = []
                for code, portfolio_config in self._portfolios.items():
                    if isinstance(portfolio_config, dict) and portfolio_config.get('enabled', False):
                        # 添加code字段
                        portfolio_with_code = portfolio_config.copy()
                        portfolio_with_code['code'] = code
                        enabled_portfolios.append(portfolio_with_code)
                return enabled_portfolios
            else:
                # 如果是列表格式
                return [p for p in self._portfolios if p.get('enabled', False)]
    
    def add_portfolio(self, portfolio: Dict[str, Any], save: bool = True):
        """
        添加组合配置
        
        Args:
            portfolio: 组合配置字典
            save: 是否立即保存
        """
        with self._lock:
            if 'portfolios' not in self._portfolios:
                self._portfolios['portfolios'] = []
            
            # 验证组合配置
            if self._validate_portfolio(portfolio):
                self._portfolios['portfolios'].append(portfolio)
                
                if save:
                    self.save_portfolios()
                
                logger.info(f"添加组合配置: {portfolio.get('name', 'Unknown')}")
            else:
                raise ValueError("组合配置验证失败")
    
    def update_portfolio(self, index: int, portfolio: Dict[str, Any], save: bool = True):
        """
        更新组合配置
        
        Args:
            index: 组合索引
            portfolio: 新的组合配置
            save: 是否立即保存
        """
        with self._lock:
            portfolios = self._portfolios.get('portfolios', [])
            
            if 0 <= index < len(portfolios):
                if self._validate_portfolio(portfolio):
                    portfolios[index] = portfolio
                    
                    if save:
                        self.save_portfolios()
                    
                    logger.info(f"更新组合配置: {portfolio.get('name', 'Unknown')}")
                else:
                    raise ValueError("组合配置验证失败")
            else:
                raise IndexError("组合索引超出范围")
    
    def remove_portfolio(self, index: int, save: bool = True):
        """
        删除组合配置
        
        Args:
            index: 组合索引
            save: 是否立即保存
        """
        with self._lock:
            portfolios = self._portfolios.get('portfolios', [])
            
            if 0 <= index < len(portfolios):
                removed = portfolios.pop(index)
                
                if save:
                    self.save_portfolios()
                
                logger.info(f"删除组合配置: {removed.get('name', 'Unknown')}")
            else:
                raise IndexError("组合索引超出范围")
    
    def get_global_setting(self, key: str, default=None):
        """获取全局设置"""
        with self._lock:
            return self._portfolios.get('global_settings', {}).get(key, default)
    
    def set_global_setting(self, key: str, value: Any, save: bool = True):
        """设置全局设置"""
        with self._lock:
            if 'global_settings' not in self._portfolios:
                self._portfolios['global_settings'] = {}
            
            self._portfolios['global_settings'][key] = value
            
            if save:
                self.save_portfolios()
    
    def save_settings(self):
        """保存主配置到文件"""
        with self._lock:
            try:
                # 确保配置目录存在
                self.config_dir.mkdir(parents=True, exist_ok=True)
                
                # 复制配置用于保存（避免修改原配置）
                settings_to_save = self._settings.copy()
                
                # 加密密码
                if 'account' in settings_to_save and 'password' in settings_to_save['account']:
                    password = settings_to_save['account']['password']
                    if password:
                        # 临时注释加密功能，避免导入错误
                        # settings_to_save['account']['password'] = encrypt_password(password)
                        pass
                
                # 使用临时文件避免文件锁定问题
                temp_file = str(self.settings_file) + '.tmp'
                
                # 确保临时文件目录存在
                temp_dir = Path(temp_file).parent
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(settings_to_save, f, indent=2, ensure_ascii=False)
                
                # 原子性替换文件
                if self.settings_file.exists():
                    self.settings_file.unlink()
                Path(temp_file).rename(self.settings_file)
                
                logger.info("主配置文件保存成功")
                
            except Exception as e:
                logger.error(f"保存主配置文件失败: {e}")
                # 清理临时文件
                temp_file = str(self.settings_file) + '.tmp'
                if Path(temp_file).exists():
                    try:
                        Path(temp_file).unlink()
                    except:
                        pass
                raise
    
    def save_portfolios(self):
        """保存组合配置到文件"""
        with self._lock:
            try:
                # 创建配置目录
                self.config_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存到文件
                with open(self.portfolios_file, 'w', encoding='utf-8') as f:
                    json.dump(self._portfolios, f, indent=2, ensure_ascii=False)
                
                logger.info("组合配置文件保存成功")
                
            except Exception as e:
                logger.error(f"保存组合配置文件失败: {e}")
                raise
    
    def save_configs(self):
        """保存主配置到文件（兼容性方法）"""
        self.save_settings()
    
    def load_configs(self):
        """加载主配置文件（兼容性方法）"""
        self._load_settings()
    
    def save_all(self):
        """保存所有配置"""
        self.save_settings()
        self.save_portfolios()
    
    def _validate_portfolio(self, portfolio: Dict[str, Any]) -> bool:
        """
        验证组合配置
        
        Args:
            portfolio: 组合配置字典
            
        Returns:
            验证是否通过
        """
        required_fields = ['name', 'code', 'follow_ratio']
        
        # 检查必需字段
        for field in required_fields:
            if field not in portfolio:
                logger.error(f"组合配置缺少必需字段: {field}")
                return False
        
        # 验证跟单比例
        follow_ratio = portfolio.get('follow_ratio', 0)
        if not isinstance(follow_ratio, (int, float)) or follow_ratio < 0 or follow_ratio > 1:
            logger.error(f"跟单比例无效: {follow_ratio}")
            return False
        
        # 验证组合代码格式
        code = portfolio.get('code', '')
        if not isinstance(code, str) or len(code) < 6:
            logger.error(f"组合代码格式无效: {code}")
            return False
        
        return True
    
    def validate_settings(self) -> List[str]:
        """
        验证主配置
        
        Returns:
            验证错误列表
        """
        errors = []
        
        # 验证账户配置
        qmt_path = self.get_setting('account.qmt_path', '')
        
        if not qmt_path or not os.path.exists(qmt_path):
            errors.append(f"QMT路径不存在: {qmt_path}")
        
        account_id = self.get_setting('account.account_id', '')
        if not account_id:
            errors.append("账户ID不能为空")
        
        # 验证风险配置
        max_position_ratio = self.get_setting('risk.max_position_ratio', 0)
        if not isinstance(max_position_ratio, (int, float)) or max_position_ratio <= 0 or max_position_ratio > 1:
            errors.append(f"最大仓位比例无效: {max_position_ratio}")
        
        stop_loss_ratio = self.get_setting('risk.stop_loss_ratio', 0)
        if not isinstance(stop_loss_ratio, (int, float)) or stop_loss_ratio <= 0 or stop_loss_ratio > 1:
            errors.append(f"止损比例无效: {stop_loss_ratio}")
        
        max_total_exposure = self.get_setting('risk.max_total_exposure', 0)
        if not isinstance(max_total_exposure, (int, float)) or max_total_exposure <= 0 or max_total_exposure > 1:
            errors.append(f"最大总仓位无效: {max_total_exposure}")
        
        # 验证监控配置
        check_interval = self.get_setting('monitoring.check_interval', 0)
        if not isinstance(check_interval, int) or check_interval <= 0:
            errors.append(f"检查间隔无效: {check_interval}")
        
        return errors
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        with self._lock:
            self._settings = self._get_default_settings()
            self._portfolios = self._get_default_portfolios()
            self.save_all()
            logger.info("配置已重置为默认值")
    

    
    def export_config(self, export_path: str):
        """
        导出配置到指定路径
        
        Args:
            export_path: 导出路径
        """
        export_data = {
            'settings': self._settings,
            'portfolios': self._portfolios
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"配置已导出到: {export_path}")
    
    def import_config(self, import_path: str):
        """
        从指定路径导入配置
        
        Args:
            import_path: 导入路径
        """
        with open(import_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        with self._lock:
            if 'settings' in import_data:
                self._settings = import_data['settings']
            
            if 'portfolios' in import_data:
                self._portfolios = import_data['portfolios']
            
            self.save_all()
        
        logger.info(f"配置已从 {import_path} 导入")

    # 便捷方法
    def get_qmt_path(self) -> str:
        """获取QMT路径"""
        path = self.get_setting('account.qmt_path', '')
        return str(path) if path else ''
    
    def get_account_id(self) -> str:
        """获取账户ID"""
        account_id = self.get_setting('account.account_id', '')
        return str(account_id) if account_id else ''
    
    def get_trade_mode(self) -> str:
        """获取交易模式"""
        mode = self.get_setting('trading.trade_mode', 'paper_trading')
        return str(mode) if mode else 'paper_trading'
    
    def get_max_position_ratio(self) -> float:
        """获取最大持仓比例"""
        ratio = self.get_setting('risk.max_position_ratio', 0.1)
        try:
            return float(ratio)
        except (ValueError, TypeError):
            return 0.1
    
    def get_config_version(self) -> str:
        """获取配置版本"""
        # 尝试从统一配置文件中获取版本信息
        unified_config_path = self.config_dir / "unified_config.json"
        if unified_config_path.exists():
            try:
                with open(unified_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                return config_data.get('version', 'unknown')
            except:
                pass
        return 'unknown'
    
    def get_all_portfolios(self) -> List[Dict[str, Any]]:
        """获取所有组合配置（包括未启用的）"""
        return self.get_portfolios()
    
    def is_config_valid(self) -> bool:
        """检查配置是否有效"""
        errors = self.validate_settings()
        return len(errors) == 0
    
    def get_config_errors(self) -> List[str]:
        """获取配置错误信息"""
        return self.validate_settings()


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager