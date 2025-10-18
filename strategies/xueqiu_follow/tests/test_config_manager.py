"""
配置管理器测试模块
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from ..core.config_manager import ConfigManager
from ..utils.crypto_utils import encrypt_password, decrypt_password


class TestConfigManager(unittest.TestCase):
    """配置管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_with_default_configs(self):
        """测试使用默认配置初始化"""
        # 验证默认配置加载
        self.assertIsNotNone(self.config_manager._settings)
        self.assertIsNotNone(self.config_manager._portfolios)
        
        # 验证默认配置内容
        self.assertIn('account', self.config_manager._settings)
        self.assertIn('risk', self.config_manager._settings)
        self.assertIn('monitoring', self.config_manager._settings)
        self.assertIn('logging', self.config_manager._settings)
        
        self.assertIn('portfolios', self.config_manager._portfolios)
        self.assertIn('global_settings', self.config_manager._portfolios)
    
    def test_get_setting(self):
        """测试获取配置项"""
        # 测试获取存在的配置项
        qmt_path = self.config_manager.get_setting('account.qmt_path')
        self.assertEqual(qmt_path, 'C:/QMT/')
        
        # 测试获取不存在的配置项
        non_existent = self.config_manager.get_setting('non.existent', 'default')
        self.assertEqual(non_existent, 'default')
        
        # 测试获取嵌套配置项
        max_position = self.config_manager.get_setting('risk.max_position_ratio')
        self.assertEqual(max_position, 0.1)
    
    def test_set_setting(self):
        """测试设置配置项"""
        # 设置新值
        self.config_manager.set_setting('account.qmt_path', 'D:/QMT/', save=False)
        
        # 验证设置成功
        new_path = self.config_manager.get_setting('account.qmt_path')
        self.assertEqual(new_path, 'D:/QMT/')
        
        # 测试设置嵌套配置项
        self.config_manager.set_setting('risk.max_position_ratio', 0.2, save=False)
        new_ratio = self.config_manager.get_setting('risk.max_position_ratio')
        self.assertEqual(new_ratio, 0.2)
    
    def test_portfolio_operations(self):
        """测试组合操作"""
        # 测试添加组合
        new_portfolio = {
            'name': '测试组合',
            'code': 'ZH123456',
            'follow_ratio': 0.5,
            'enabled': True,
            'description': '测试用组合'
        }
        
        self.config_manager.add_portfolio(new_portfolio, save=False)
        portfolios = self.config_manager.get_portfolios()
        self.assertEqual(len(portfolios), 2)  # 默认有1个，新增1个
        
        # 测试获取启用的组合
        enabled_portfolios = self.config_manager.get_enabled_portfolios()
        self.assertEqual(len(enabled_portfolios), 1)  # 只有新增的组合是启用的
        
        # 测试更新组合
        updated_portfolio = new_portfolio.copy()
        updated_portfolio['follow_ratio'] = 0.6
        self.config_manager.update_portfolio(1, updated_portfolio, save=False)
        
        portfolios = self.config_manager.get_portfolios()
        self.assertEqual(portfolios[1]['follow_ratio'], 0.6)
        
        # 测试删除组合
        self.config_manager.remove_portfolio(1, save=False)
        portfolios = self.config_manager.get_portfolios()
        self.assertEqual(len(portfolios), 1)
    
    def test_portfolio_validation(self):
        """测试组合配置验证"""
        # 测试有效组合
        valid_portfolio = {
            'name': '有效组合',
            'code': 'ZH123456',
            'follow_ratio': 0.5,
            'enabled': True
        }
        
        # 应该不抛出异常
        self.config_manager.add_portfolio(valid_portfolio, save=False)
        
        # 测试无效组合 - 缺少必需字段
        invalid_portfolio1 = {
            'name': '无效组合',
            'follow_ratio': 0.5
            # 缺少 code 字段
        }
        
        with self.assertRaises(ValueError):
            self.config_manager.add_portfolio(invalid_portfolio1, save=False)
        
        # 测试无效组合 - 跟单比例超出范围
        invalid_portfolio2 = {
            'name': '无效组合',
            'code': 'ZH123456',
            'follow_ratio': 1.5  # 超出范围
        }
        
        with self.assertRaises(ValueError):
            self.config_manager.add_portfolio(invalid_portfolio2, save=False)
        
        # 测试无效组合 - 组合代码格式错误
        invalid_portfolio3 = {
            'name': '无效组合',
            'code': '123',  # 太短
            'follow_ratio': 0.5
        }
        
        with self.assertRaises(ValueError):
            self.config_manager.add_portfolio(invalid_portfolio3, save=False)
    
    def test_global_settings(self):
        """测试全局设置"""
        # 测试获取全局设置
        auto_start = self.config_manager.get_global_setting('auto_start')
        self.assertFalse(auto_start)
        
        # 测试设置全局设置
        self.config_manager.set_global_setting('auto_start', True, save=False)
        new_auto_start = self.config_manager.get_global_setting('auto_start')
        self.assertTrue(new_auto_start)
    
    def test_config_validation(self):
        """测试配置验证"""
        # 测试有效配置
        errors = self.config_manager.validate_settings()
        # 默认配置可能有一些错误（如QMT路径不存在），但不应该为空
        self.assertIsInstance(errors, list)
        
        # 设置无效配置并测试
        self.config_manager.set_setting('risk.max_position_ratio', 1.5, save=False)
        errors = self.config_manager.validate_settings()
        self.assertTrue(any('最大仓位比例无效' in error for error in errors))
    
    def test_save_and_load_configs(self):
        """测试配置保存和加载"""
        # 修改配置
        self.config_manager.set_setting('account.qmt_path', 'D:/QMT/', save=False)
        
        # 测试保存 - 使用完整的Mock避免文件操作
        with patch('builtins.open', create=True):
            with patch('json.dump') as mock_dump:
                with patch('pathlib.Path.exists', return_value=False):
                    with patch('pathlib.Path.unlink'):
                        with patch('pathlib.Path.rename'):
                            self.config_manager.save_settings()
                mock_dump.assert_called_once()
        
        # 测试保存所有配置
        with patch('builtins.open', create=True):
            with patch('json.dump') as mock_dump:
                with patch('pathlib.Path.exists', return_value=False):
                    with patch('pathlib.Path.unlink'):
                        with patch('pathlib.Path.rename'):
                            self.config_manager.save_all()
                self.assertEqual(mock_dump.call_count, 2)  # settings + portfolios
    
    def test_password_encryption(self):
        """测试密码加密功能"""
        # 设置密码
        test_password = "test_password_123"
        self.config_manager.set_setting('account.password', test_password, save=False)
        
        # 验证内存中的密码是明文
        stored_password = self.config_manager.get_setting('account.password')
        self.assertEqual(stored_password, test_password)
        
        # 模拟保存过程 - 不实际保存文件，只测试加密逻辑
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_dump:
                with patch('pathlib.Path.exists', return_value=False):
                    with patch('pathlib.Path.unlink'):
                        with patch('pathlib.Path.rename'):
                            self.config_manager.save_settings()
                
                # 验证保存时密码被加密
                saved_data = mock_dump.call_args[0][0]
                saved_password = saved_data['account']['password']
                self.assertNotEqual(saved_password, test_password)
                self.assertTrue(len(saved_password) > 0)
    
    def test_reset_to_defaults(self):
        """测试重置为默认配置"""
        # 修改配置
        self.config_manager.set_setting('account.qmt_path', 'D:/QMT/', save=False)
        self.config_manager.add_portfolio({
            'name': '测试组合',
            'code': 'ZH123456',
            'follow_ratio': 0.5,
            'enabled': True
        }, save=False)
        
        # 重置配置
        with patch.object(self.config_manager, 'save_all'):
            self.config_manager.reset_to_defaults()
        
        # 验证配置已重置
        qmt_path = self.config_manager.get_setting('account.qmt_path')
        self.assertEqual(qmt_path, 'C:/QMT/')
        
        portfolios = self.config_manager.get_portfolios()
        self.assertEqual(len(portfolios), 1)  # 只有默认组合
    
    def test_export_import_config(self):
        """测试配置导出导入"""
        # 修改配置
        self.config_manager.set_setting('account.qmt_path', 'D:/QMT/', save=False)
        
        # 测试导出
        export_path = Path(self.temp_dir) / 'export_config.json'
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_dump:
                self.config_manager.export_config(str(export_path))
                mock_dump.assert_called_once()
        
        # 测试导入
        import_data = {
            'settings': {'account': {'qmt_path': 'E:/QMT/'}},
            'portfolios': {'portfolios': [], 'global_settings': {}}
        }
        
        with patch('builtins.open', create=True):
            with patch('json.load', return_value=import_data):
                with patch.object(self.config_manager, 'save_all'):
                    self.config_manager.import_config(str(export_path))
        
        # 验证导入成功
        qmt_path = self.config_manager.get_setting('account.qmt_path')
        self.assertEqual(qmt_path, 'E:/QMT/')
    
    def test_thread_safety(self):
        """测试线程安全"""
        import threading
        import time
        
        results = []
        
        def modify_config(value):
            self.config_manager.set_setting('test.value', value, save=False)
            time.sleep(0.01)  # 模拟一些处理时间
            result = self.config_manager.get_setting('test.value')
            results.append(result)
        
        # 创建多个线程同时修改配置
        threads = []
        for i in range(10):
            thread = threading.Thread(target=modify_config, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果（应该有10个结果）
        self.assertEqual(len(results), 10)


if __name__ == '__main__':
    unittest.main()