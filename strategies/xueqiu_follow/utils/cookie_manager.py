import logging

logger = logging.getLogger(__name__)
"""
雪球Cookie管理工具
用于获取和管理雪球网站的Cookie
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

try:
    from .logger import setup_logger
except ImportError:
    def setup_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)


class CookieManager:
    """雪球Cookie管理器"""
    
    def __init__(self):
        self.logger = setup_logger("CookieManager")
        self.config_paths = [
            # 历史配置路径
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '雪球跟单系统', '雪球跟单设置.json'),
            # 当前系统配置路径
            os.path.join(os.path.dirname(__file__), '..', 'config', 'xueqiu_config.json')
        ]
    
    def get_cookie(self) -> Optional[str]:
        """获取有效的Cookie"""
        # 尝试从各个配置文件读取
        for config_path in self.config_paths:
            cookie = self._load_cookie_from_file(config_path)
            if cookie:
                if self._is_cookie_valid(cookie):
                    self.logger.info(f"从 {config_path} 加载有效Cookie")
                    return cookie
                else:
                    self.logger.warning(f"Cookie已过期: {config_path}")
        
        self.logger.error("未找到有效的Cookie")
        return None
    
    def _load_cookie_from_file(self, config_path: str) -> Optional[str]:
        """从配置文件加载Cookie"""
        try:
            if not os.path.exists(config_path):
                return None
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 尝试不同的键名
            cookie_keys = ['雪球cookie', 'cookie', 'xueqiu_cookie']
            for key in cookie_keys:
                if key in config and config[key]:
                    return config[key]
                    
        except Exception as e:
            self.logger.debug(f"读取配置文件失败 {config_path}: {e}")
        
        return None
    
    def _is_cookie_valid(self, cookie: str) -> bool:
        """检查Cookie是否有效（简单检查）"""
        if not cookie or len(cookie) < 50:
            return False
            
        # 检查必要的字段
        required_fields = ['xq_a_token', 'u=', 'xq_is_login=1']
        for field in required_fields:
            if field not in cookie:
                return False
        
        # 检查token是否过期（如果有xq_id_token）
        if 'xq_id_token=' in cookie:
            try:
                # 提取token部分
                token_start = cookie.find('xq_id_token=') + len('xq_id_token=')
                token_end = cookie.find(';', token_start)
                if token_end == -1:
                    token_end = len(cookie)
                
                token = cookie[token_start:token_end]
                
                # 简单的JWT过期检查（这里只是基本检查，实际需要解析JWT）
                if len(token) > 100:  # JWT token通常很长
                    return True
                    
            except Exception:
                pass
        
        return True
    
    def save_cookie(self, cookie: str, config_path: str = None) -> bool:
        """保存Cookie到配置文件"""
        try:
            if not config_path:
                config_path = self.config_paths[1]  # 使用当前系统配置路径
            
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # 读取现有配置或创建新配置
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新Cookie
            config['cookie'] = cookie
            config['update_time'] = datetime.now().isoformat()
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Cookie已保存到: {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存Cookie失败: {e}")
            return False
    
    def get_cookie_info(self, cookie: str) -> Dict[str, Any]:
        """解析Cookie信息"""
        info = {
            'valid': False,
            'user_id': None,
            'login_status': False,
            'token_exists': False,
            'fields': []
        }
        
        try:
            # 解析Cookie字段
            fields = {}
            for item in cookie.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    fields[key] = value
            
            info['fields'] = list(fields.keys())
            
            # 检查用户ID
            if 'u' in fields:
                info['user_id'] = fields['u']
            
            # 检查登录状态
            if 'xq_is_login' in fields:
                info['login_status'] = fields['xq_is_login'] == '1'
            
            # 检查token
            if 'xq_a_token' in fields:
                info['token_exists'] = True
            
            # 综合判断有效性
            info['valid'] = (
                info['user_id'] is not None and
                info['login_status'] and
                info['token_exists']
            )
            
        except Exception as e:
            self.logger.error(f"解析Cookie失败: {e}")
        
        return info


def print_cookie_guide():
    """打印获取Cookie的指南"""
    guide = """
🔧 雪球Cookie获取指南

1. 打开浏览器，访问雪球网站: https://xueqiu.com
2. 登录您的雪球账户
3. 按F12打开开发者工具
4. 切换到"网络"(Network)标签页
5. 刷新页面或访问任意组合页面
6. 在网络请求中找到任意一个对xueqiu.com的请求
7. 点击该请求，在"请求标头"中找到"Cookie"字段
8. 复制完整的Cookie值

Cookie示例格式:
cookiesu=xxx; device_id=xxx; xq_is_login=1; u=xxx; xq_a_token=xxx; ...

⚠️ 注意事项:
- Cookie包含您的登录信息，请妥善保管
- Cookie有时效性，过期后需要重新获取
- 不要在公共场所或不安全的环境中操作

📝 保存Cookie:
将获取的Cookie保存到以下文件中的"雪球cookie"字段:
- 历史配置/雪球跟单设置.json
- strategies/xueqiu_follow/config/xueqiu_config.json
"""
    logger.info(guide)


if __name__ == "__main__":
    # 测试Cookie管理器
    manager = CookieManager()
    
    logger.info("🔧 测试Cookie管理器...")
    
    # 获取Cookie
    cookie = manager.get_cookie()
    if cookie:
        logger.info("✅ 找到Cookie")
        
        # 分析Cookie信息
        info = manager.get_cookie_info(cookie)
        logger.info(f"📊 Cookie信息:")
        logger.info(f"   有效性: {'✅' if info['valid'] else '❌'}")
        logger.info(f"   用户ID: {info['user_id']}")
        logger.info(f"   登录状态: {'✅' if info['login_status'] else '❌'}")
        logger.info(f"   Token存在: {'✅' if info['token_exists'] else '❌'}")
        logger.info(f"   字段数量: {len(info['fields'])}")
    else:
        logger.info("❌ 未找到有效Cookie")
        print_cookie_guide()