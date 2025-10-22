#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单系统健康检查工具
"""

import sys
import os
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from core.config_manager import ConfigManager
from core.strategy_engine import StrategyEngine
from core.xueqiu_collector import XueqiuCollector
from core.trade_executor import TradeExecutor
from core.risk_manager import RiskManager


class SystemHealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self.results = {}
        self.errors = []
        self.warnings = []
        
    async def run_health_check(self):
        """运行完整的健康检查"""
        print("🔍 开始系统健康检查...")
        print("=" * 50)
        
        # 检查各个组件
        await self._check_config_manager()
        await self._check_qmt_connection()
        await self._check_xueqiu_connection()
        await self._check_risk_manager()
        await self._check_strategy_engine()
        await self._check_system_resources()
        await self._check_log_files()
        
        # 生成报告
        self._generate_report()
        
        return len(self.errors) == 0
    
    async def _check_config_manager(self):
        """检查配置管理器"""
        print("📋 检查配置管理器...")
        
        try:
            config = ConfigManager()
            
            # 检查配置文件是否存在
            if not config.settings_file.exists():
                self.warnings.append("配置文件不存在，使用默认配置")
            
            # 验证配置
            errors = config.validate_settings()
            if errors:
                self.warnings.extend([f"配置警告: {error}" for error in errors])
            
            # 检查组合配置
            portfolios = config.get_enabled_portfolios()
            if not portfolios:
                self.warnings.append("没有启用的跟单组合")
            
            self.results['config_manager'] = '✅ 正常'
            print("   ✅ 配置管理器正常")
            
        except Exception as e:
            self.errors.append(f"配置管理器错误: {e}")
            self.results['config_manager'] = f'❌ 错误: {e}'
            print(f"   ❌ 配置管理器错误: {e}")
    
    async def _check_qmt_connection(self):
        """检查QMT连接"""
        print("🔌 检查QMT连接...")
        
        try:
            from xtquant import xtdata
            
            # 测试数据获取
            test_data = xtdata.get_market_data(['000001.SZ'], period='1d', count=1)
            
            if test_data and len(test_data) > 0:
                self.results['qmt_connection'] = '✅ 正常'
                print("   ✅ QMT连接正常")
            else:
                self.warnings.append("QMT数据获取异常")
                self.results['qmt_connection'] = '⚠️ 数据异常'
                print("   ⚠️ QMT数据获取异常")
                
        except ImportError:
            self.errors.append("QMT模块未安装或路径错误")
            self.results['qmt_connection'] = '❌ 模块未找到'
            print("   ❌ QMT模块未安装或路径错误")
        except Exception as e:
            self.errors.append(f"QMT连接错误: {e}")
            self.results['qmt_connection'] = f'❌ 错误: {e}'
            print(f"   ❌ QMT连接错误: {e}")
    
    async def _check_xueqiu_connection(self):
        """检查雪球连接"""
        print("🌐 检查雪球连接...")
        
        try:
            collector = XueqiuCollector()
            await collector.initialize()
            
            # 测试网络连接（不实际请求数据）
            self.results['xueqiu_connection'] = '✅ 正常'
            print("   ✅ 雪球连接初始化正常")
            
        except Exception as e:
            self.warnings.append(f"雪球连接警告: {e}")
            self.results['xueqiu_connection'] = f'⚠️ 警告: {e}'
            print(f"   ⚠️ 雪球连接警告: {e}")
    
    async def _check_risk_manager(self):
        """检查风险管理器"""
        print("🛡️ 检查风险管理器...")
        
        try:
            config = ConfigManager()
            risk_config = config.get_setting('risk', {})
            risk_manager = RiskManager(risk_config)
            
            # 测试风险验证
            test_result = risk_manager.validate_order(
                'buy', '000001', 100, 10.0, {}, {'available_cash': 10000}
            )
            
            if 'allowed' in test_result:
                self.results['risk_manager'] = '✅ 正常'
                print("   ✅ 风险管理器正常")
            else:
                self.warnings.append("风险管理器返回格式异常")
                self.results['risk_manager'] = '⚠️ 格式异常'
                print("   ⚠️ 风险管理器返回格式异常")
                
        except Exception as e:
            self.errors.append(f"风险管理器错误: {e}")
            self.results['risk_manager'] = f'❌ 错误: {e}'
            print(f"   ❌ 风险管理器错误: {e}")
    
    async def _check_strategy_engine(self):
        """检查策略引擎"""
        print("⚙️ 检查策略引擎...")
        
        try:
            config = ConfigManager()
            engine = StrategyEngine(config)
            
            # 检查初始化（不实际连接）
            self.results['strategy_engine'] = '✅ 正常'
            print("   ✅ 策略引擎初始化正常")
            
        except Exception as e:
            self.errors.append(f"策略引擎错误: {e}")
            self.results['strategy_engine'] = f'❌ 错误: {e}'
            print(f"   ❌ 策略引擎错误: {e}")
    
    async def _check_system_resources(self):
        """检查系统资源"""
        print("💻 检查系统资源...")
        
        try:
            import psutil
            
            # 检查CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 检查内存使用
            memory = psutil.virtual_memory()
            
            # 检查磁盘空间
            disk = psutil.disk_usage('.')
            
            resource_info = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_free_gb': disk.free / (1024**3)
            }
            
            # 检查资源是否充足
            warnings = []
            if cpu_percent > 80:
                warnings.append(f"CPU使用率过高: {cpu_percent}%")
            if memory.percent > 85:
                warnings.append(f"内存使用率过高: {memory.percent}%")
            if disk.free / (1024**3) < 1:
                warnings.append(f"磁盘空间不足: {disk.free / (1024**3):.1f}GB")
            
            if warnings:
                self.warnings.extend(warnings)
                self.results['system_resources'] = f'⚠️ 资源紧张'
            else:
                self.results['system_resources'] = '✅ 正常'
            
            print(f"   CPU: {cpu_percent}%, 内存: {memory.percent}%, 可用磁盘: {disk.free / (1024**3):.1f}GB")
            
        except ImportError:
            self.warnings.append("psutil模块未安装，无法检查系统资源")
            self.results['system_resources'] = '⚠️ 无法检查'
            print("   ⚠️ psutil模块未安装，无法检查系统资源")
        except Exception as e:
            self.warnings.append(f"系统资源检查错误: {e}")
            self.results['system_resources'] = f'⚠️ 错误: {e}'
            print(f"   ⚠️ 系统资源检查错误: {e}")
    
    async def _check_log_files(self):
        """检查日志文件"""
        print("📝 检查日志文件...")
        
        try:
            log_dir = Path('logs')
            
            if not log_dir.exists():
                self.warnings.append("日志目录不存在")
                self.results['log_files'] = '⚠️ 目录不存在'
                print("   ⚠️ 日志目录不存在")
                return
            
            # 检查日志文件
            log_files = list(log_dir.glob('*.log'))
            
            if not log_files:
                self.warnings.append("没有找到日志文件")
                self.results['log_files'] = '⚠️ 无日志文件'
                print("   ⚠️ 没有找到日志文件")
                return
            
            # 检查日志文件大小
            large_files = []
            for log_file in log_files:
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > 100:  # 超过100MB
                    large_files.append(f"{log_file.name}: {size_mb:.1f}MB")
            
            if large_files:
                self.warnings.append(f"日志文件过大: {', '.join(large_files)}")
                self.results['log_files'] = '⚠️ 文件过大'
            else:
                self.results['log_files'] = '✅ 正常'
            
            print(f"   找到 {len(log_files)} 个日志文件")
            
        except Exception as e:
            self.warnings.append(f"日志文件检查错误: {e}")
            self.results['log_files'] = f'⚠️ 错误: {e}'
            print(f"   ⚠️ 日志文件检查错误: {e}")
    
    def _generate_report(self):
        """生成健康检查报告"""
        print("\n" + "=" * 50)
        print("📊 健康检查报告")
        print("=" * 50)
        
        # 显示检查结果
        for component, status in self.results.items():
            component_name = {
                'config_manager': '配置管理器',
                'qmt_connection': 'QMT连接',
                'xueqiu_connection': '雪球连接',
                'risk_manager': '风险管理器',
                'strategy_engine': '策略引擎',
                'system_resources': '系统资源',
                'log_files': '日志文件'
            }.get(component, component)
            
            print(f"{component_name}: {status}")
        
        # 显示错误
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
        
        # 显示警告
        if self.warnings:
            print(f"\n⚠️ 发现 {len(self.warnings)} 个警告:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        
        # 总体状态
        print("\n" + "=" * 50)
        if not self.errors and not self.warnings:
            print("🎉 系统状态: 完全正常")
        elif not self.errors:
            print("✅ 系统状态: 正常 (有警告)")
        else:
            print("❌ 系统状态: 有错误需要修复")
        
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)


async def main():
    """主函数"""
    checker = SystemHealthChecker()
    
    try:
        success = await checker.run_health_check()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n检查被用户中断")
        return 1
    except Exception as e:
        print(f"\n健康检查过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.WARNING)
    
    # 运行健康检查
    exit_code = asyncio.run(main())
    sys.exit(exit_code)