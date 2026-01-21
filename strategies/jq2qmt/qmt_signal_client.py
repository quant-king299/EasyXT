#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT信号客户端
用于连接中转服务获取交易信号，并转发到本地QKA服务执行交易
"""

import argparse
import requests
import time
import json
from datetime import datetime
import uuid
import hashlib
from typing import Dict, Any, List

class QMTSignalClient:
    """QMT信号客户端"""
    
    def __init__(self, proxy_url: str = "http://www.ptqmt.com:8080", qka_url: str = "http://127.0.0.1:8000", token: str = "test_token"):
        """
        初始化QMT信号客户端
        
        Args:
            proxy_url: 中转服务地址
            qka_url: 本地QKA服务地址
            token: 访问令牌
        """
        self.proxy_url = proxy_url.rstrip('/')
        self.qka_url = qka_url.rstrip('/')
        self.token = token
        # 中转服务使用 Bearer Token 认证
        self.proxy_headers = {"Authorization": f"Bearer {self.token}"}
        # QKA服务使用 X-Token 认证
        self.qka_headers = {"X-Token": self.token}
        self.session = requests.Session()
        
        print(f"QMT信号客户端初始化完成:")
        print(f"  中转服务地址: {self.proxy_url}")
        print(f"  QKA服务地址: {self.qka_url}")
        print(f"  访问令牌: {self.token}")
    
    def get_pending_signals(self) -> List[Dict]:
        """
        从中转服务获取待处理的交易信号
        
        Returns:
            交易信号列表
        """
        try:
            response = self.session.get(
                f"{self.proxy_url}/api/get_signals",
                headers=self.proxy_headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    signals = result.get('signals', [])
                    print(f"获取到 {len(signals)} 个待处理信号")
                    return signals
                else:
                    print(f"❌ 获取信号失败: {result.get('message')}")
                    return []
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 获取信号异常: {e}")
            return []
    
    def execute_signal(self, signal: Dict) -> Dict:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
            
        Returns:
            执行结果
        """
        try:
            # 提取信号参数
            stock_code = signal.get('stock_code')
            order_type = signal.get('order_type')
            order_volume = signal.get('order_volume')
            price_type = signal.get('price_type')
            price = signal.get('price')
            strategy_name = signal.get('strategy_name')
            signal_id = signal.get('signal_id')
            
            print(f"执行交易信号:")
            print(f"  股票代码: {stock_code}")
            print(f"  订单类型: {'买入' if order_type == 23 else '卖出'} ({order_type})")
            print(f"  订单数量: {order_volume}")
            print(f"  价格类型: {'限价' if price_type == 11 else '市价'} ({price_type})")
            print(f"  价格: {price}")
            print(f"  策略名称: {strategy_name}")
            print(f"  信号ID: {signal_id}")
            
            # 调用QKA服务执行交易
            trade_params = {
                'stock_code': stock_code,
                'order_type': order_type,
                'order_volume': order_volume,
                'price_type': price_type,
                'price': price,
                'strategy_name': strategy_name
            }
            
            response = self.session.post(
                f"{self.qka_url}/api/order_stock",
                json=trade_params,
                headers=self.qka_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 交易执行成功: {result}")
                
                # 返回执行结果
                execution_result = {
                    'signal_id': signal_id,
                    'success': True,
                    'result': result,
                    'timestamp': int(time.time())
                }
                return execution_result
            else:
                print(f"❌ 交易执行失败，HTTP错误: {response.status_code}")
                print(f"响应内容: {response.text}")
                execution_result = {
                    'signal_id': signal_id,
                    'success': False,
                    'error': f"HTTP错误: {response.status_code}",
                    'timestamp': int(time.time())
                }
                return execution_result
        except Exception as e:
            print(f"❌ 交易执行异常: {e}")
            execution_result = {
                'signal_id': signal.get('signal_id'),
                'success': False,
                'error': str(e),
                'timestamp': int(time.time())
            }
            return execution_result
    
    def report_result(self, result: Dict) -> bool:
        """
        向中转服务报告执行结果
        
        Args:
            result: 执行结果
            
        Returns:
            是否报告成功
        """
        try:
            response = self.session.post(
                f"{self.proxy_url}/api/report_result",
                json=result,
                headers=self.proxy_headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get('success'):
                    print(f"✅ 执行结果报告成功")
                    return True
                else:
                    print(f"❌ 执行结果报告失败: {result_data.get('message')}")
                    return False
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 报告结果异常: {e}")
            return False
    
    def run(self, interval: int = 5):
        """
        运行信号客户端
        
        Args:
            interval: 轮询间隔（秒）
        """
        print(f"开始运行QMT信号客户端，轮询间隔: {interval}秒")
        print("=" * 50)
        
        try:
            while True:
                # 获取待处理信号
                signals = self.get_pending_signals()
                
                # 处理每个信号
                for signal in signals:
                    # 执行信号
                    execution_result = self.execute_signal(signal)
                    
                    # 报告执行结果
                    self.report_result(execution_result)
                
                # 等待下一次轮询
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n客户端已停止")
        except Exception as e:
            print(f"客户端运行异常: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="QMT信号客户端")
    parser.add_argument("--proxy-url", default="http://www.ptqmt.com:8080", help="中转服务地址")
    parser.add_argument("--qka-url", default="http://127.0.0.1:8000", help="QKA服务地址")
    parser.add_argument("--token", default="test_token", help="访问令牌")
    parser.add_argument("--interval", type=int, default=5, help="轮询间隔（秒）")
    
    args = parser.parse_args()
    
    # 创建并运行客户端
    client = QMTSignalClient(
        proxy_url=args.proxy_url,
        qka_url=args.qka_url,
        token=args.token
    )
    
    client.run(interval=args.interval)

if __name__ == "__main__":
    main()