"""
EasyXT配置管理
"""

from typing import Dict, Any, Optional
import os


def deep_update(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
    """深度更新字典"""
    for key, value in update_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            deep_update(base_dict[key], value)
        else:
            base_dict[key] = value


class Config:
    """配置管理类"""
    
    def __init__(self):
        # 默认配置
        self.settings = {
            'data': {
                'fill_data': True,
                'auto_retry': True,
                'retry_count': 3,
                'timeout': 30
            },
            'trade': {
                'session_id': 'default',
                'userdata_path': '',
                'callback_timeout': 10
            },
            'qmt': {
                # QMT可能的安装路径列表
                'possible_paths': [
                    "D:/国金证券QMT交易端",
                    "C:/国金证券QMT交易端", 
                    "D:/QMT",
                    "C:/QMT",
                    "D:/Program Files/QMT",
                    "C:/Program Files/QMT",
                    "D:/Program Files (x86)/QMT",
                    "C:/Program Files (x86)/QMT",
                ],
                'userdata_subpath': 'userdata_mini',
                'detected_path': None
            }
        }
        
        # 自动检测QMT路径
        self._detect_qmt_path()
    
    def _detect_qmt_path(self):
        """自动检测QMT安装路径"""
        for path in self.settings['qmt']['possible_paths']:
            if os.path.exists(path):
                userdata_path = os.path.join(path, self.settings['qmt']['userdata_subpath'])
                if os.path.exists(userdata_path):
                    self.settings['qmt']['detected_path'] = path
                    self.settings['trade']['userdata_path'] = userdata_path
                    print(f"✓ 自动检测到QMT路径: {path}")
                    return path
        
        print("❌ 未能自动检测到QMT路径，请手动配置")
        return None
    
    def get_qmt_path(self) -> Optional[str]:
        """获取QMT安装路径"""
        return self.settings['qmt']['detected_path']
    
    def get_userdata_path(self) -> Optional[str]:
        """获取用户数据路径"""
        return self.settings['trade']['userdata_path']
    
    def set_qmt_path(self, path: str) -> bool:
        """手动设置QMT路径"""
        if not os.path.exists(path):
            print(f"❌ QMT路径不存在: {path}")
            return False
        
        userdata_path = os.path.join(path, self.settings['qmt']['userdata_subpath'])
        if not os.path.exists(userdata_path):
            print(f"❌ 未找到userdata_mini目录: {userdata_path}")
            return False
        
        self.settings['qmt']['detected_path'] = path
        self.settings['trade']['userdata_path'] = userdata_path
        
        # 将新路径添加到可能路径列表的开头
        if path not in self.settings['qmt']['possible_paths']:
            self.settings['qmt']['possible_paths'].insert(0, path)
        
        print(f"✓ QMT路径设置成功: {path}")
        return True
    
    def validate_qmt_setup(self) -> tuple[bool, str]:
        """验证QMT配置"""
        qmt_path = self.get_qmt_path()
        if not qmt_path:
            return False, "未配置QMT路径"
        
        if not os.path.exists(qmt_path):
            return False, f"QMT路径不存在: {qmt_path}"
        
        userdata_path = self.get_userdata_path()
        if not userdata_path or not os.path.exists(userdata_path):
            return False, f"userdata路径不存在: {userdata_path}"
        
        return True, "QMT配置正常"
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split('.')
        target = self.settings
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """批量更新配置"""
        deep_update(self.settings, config_dict)
    
    def print_qmt_status(self):
        """打印QMT配置状态"""
        print("\n" + "="*50)
        print("QMT配置状态")
        print("="*50)
        
        qmt_path = self.get_qmt_path()
        userdata_path = self.get_userdata_path()
        
        if qmt_path:
            print(f"✓ QMT安装路径: {qmt_path}")
            print(f"✓ 用户数据路径: {userdata_path}")
            
            is_valid, msg = self.validate_qmt_setup()
            if is_valid:
                print(f"✓ 配置状态: {msg}")
            else:
                print(f"❌ 配置状态: {msg}")
        else:
            print("❌ 未检测到QMT安装路径")
            print("\n可能的解决方案:")
            print("1. 确保QMT已正确安装")
            print("2. 手动设置QMT路径:")
            print("   from easy_xt.config import config")
            print("   config.set_qmt_path('你的QMT安装路径')")
            print("\n常见QMT安装路径:")
            for path in self.settings['qmt']['possible_paths']:
                print(f"   - {path}")
        
        print("="*50)


# 全局配置实例
config = Config()