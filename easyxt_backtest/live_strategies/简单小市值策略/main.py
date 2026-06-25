import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""

简单小市值策略 - 实盘交易主程序（使用easy_xt）



策略描述: 选择市值最小的10只股票，适合研究小市值效应

"""



import sys

from pathlib import Path

from datetime import datetime



# 添加项目路径

current_dir = Path(__file__).resolve().parent

project_root = current_dir.parent.parent.parent

sys.path.insert(0, str(current_dir))

sys.path.insert(0, str(project_root))



# 导入easy_xt

try:

    import easy_xt

    EASYXT_AVAILABLE = True

except ImportError as e:

    logger.warning(f"[WARN] 无法导入easy_xt: {e}")
    EASYXT_AVAILABLE = False



# 导入数据管理器

try:

    from easyxt_backtest.data import create_data_manager

    DATAMANAGER_AVAILABLE = True

except ImportError:

    DATAMANAGER_AVAILABLE = False

    create_data_manager = None



from strategy_logic import 简单小市值策略Strategy

from risk_control import RiskController





class 简单小市值策略StrategyLive:

    """简单小市值策略实盘交易版"""



    def __init__(self):

        self.api = None

        self.strategy = None

        self.risk_controller = None

        self.data_manager = None



        # 直接配置（不依赖JSON文件）

        self.account_id = ""

        self.qmt_path = r"D:\国金QMT交易端模拟\userdata_mini"

        self.session_id = "mini_qmt"

        self.auto_confirm = True  # ✅ 已启用自动执行，订单会发送到QMT

        self.is_connected = False



    def initialize(self):

        """初始化"""

        logger.info(f"\n{'='*60}")
        logger.info(f"初始化简单小市值策略实盘策略...")
        logger.info(f"{'='*60}\n")


        # 1. 初始化数据管理器

        logger.info("[1/4] 初始化数据管理器...")
        if DATAMANAGER_AVAILABLE:

            try:

                self.data_manager = create_data_manager()

                logger.info("  [OK] 数据管理器初始化成功")
            except Exception as e:

                logger.warning(f"  [WARN] 数据管理器初始化失败: {e}")
                self.data_manager = None

        else:

            logger.info("  [INFO] data_manager模块未安装")


        # 2. 初始化easy_xt交易

        logger.info("\n[2/4] 初始化easy_xt交易...")
        if EASYXT_AVAILABLE:

            try:

                self.api = easy_xt.get_api()



                logger.info(f"  [INFO] 账户ID: {self.account_id}")
                logger.info(f"  [INFO] QMT路径: {self.qmt_path}")
                logger.info(f"  [INFO] Session ID: {self.session_id}")


                # 初始化交易服务

                success = self.api.init_trade(self.qmt_path, self.session_id)

                if success:

                    logger.info("  [OK] 交易服务初始化成功")
                else:

                    logger.warning("  [WARN] 交易服务初始化失败（QMT可能未启动）")
                    logger.info("  [TIPS] 请确保QMT交易端已启动并登录")
                    return False



                # 添加账户

                success = self.api.add_account(self.account_id, 'STOCK')

                if success:

                    logger.info(f"  [OK] 账户添加成功: {self.account_id}")
                    self.is_connected = True

                else:

                    logger.warning(f"  [WARN] 账户添加失败")
                    return False



            except Exception as e:

                logger.warning(f"  [WARN] easy_xt初始化失败: {e}")
                import traceback

                traceback.print_exc()

                self.is_connected = False

        else:

            logger.info("  [INFO] easy_xt模块未安装")


        # 3. 初始化策略逻辑

        logger.info("\n[3/4] 初始化策略逻辑...")
        self.strategy = 简单小市值策略Strategy(self.data_manager)

        logger.info("  [OK] 策略初始化完成")


        # 4. 初始化风控

        logger.info("\n[4/4] 初始化风控模块...")
        risk_config = {}

        self.risk_controller = RiskController(risk_config)

        logger.info("  [OK] 风控模块初始化完成")


        # 5. 查询账户状态

        if self.is_connected and self.api:

            try:

                logger.info(f"\n[INFO] 查询账户资产...")
                asset = self.api.get_account_asset(self.account_id)

                if asset:

                    total_asset = asset.get('total_asset', 0)

                    cash = asset.get('cash', 0)

                    logger.info(f"  总资产: {total_asset:,.2f} 元")
                    logger.info(f"  可用资金: {cash:,.2f} 元")
            except Exception as e:

                logger.warning(f"  [WARN] 查询账户资产失败: {e}")


        mode = "实盘模式" if self.is_connected else "模拟模式"

        logger.info(f"\n[OK] 初始化完成（{mode}）")
        logger.info(f"{'='*60}\n")


        return True



    def get_current_positions(self):

        """获取当前持仓"""

        if not self.is_connected or not self.api:

            return {}



        try:

            positions = self.api.get_positions(self.account_id)

            if positions is None or positions.empty:

                return {}



            pos_dict = {}

            for _, row in positions.iterrows():

                pos_dict[row['code']] = {

                    'volume': row['volume'],

                    'can_use_volume': row['can_use_volume'],

                    'market_value': row.get('market_value', 0)

                }

            return pos_dict

        except Exception as e:

            logger.warning(f"[WARN] 获取持仓失败: {e}")
            return {}



    def execute_orders(self, orders):

        """执行订单"""

        if not self.is_connected or not self.api:

            logger.info("[INFO] 未连接QMT，订单未执行（仅显示）")
            return []



        if not self.auto_confirm:

            logger.info("[INFO] auto_confirm = False，订单未发送到QMT")
            logger.info("[TIPS] 修改 self.auto_confirm = True 可自动执行订单")
            return []



        results = []

        for order in orders:

            try:

                direction = order.get('direction')

                code = order.get('symbol')

                volume = order.get('volume')

                reason = order.get('reason', '')



                logger.info(f"\n  执行订单: [{direction.upper()}] {code} {volume}股")
                logger.info(f"  原因: {reason}")


                order_id = None

                if direction == 'buy':

                    order_id = self.api.buy(

                        account_id=self.account_id,

                        code=code,

                        volume=volume,

                        price=0,  # 市价单

                        price_type='market'

                    )

                elif direction == 'sell':

                    order_id = self.api.sell(

                        account_id=self.account_id,

                        code=code,

                        volume=volume,

                        price=0,

                        price_type='market'

                    )



                if order_id:

                    logger.info(f"  [OK] 委托成功: {order_id}")
                    results.append({

                        'symbol': code,

                        'direction': direction,

                        'volume': volume,

                        'order_id': order_id,

                        'success': True

                    })

                else:

                    logger.info(f"  [FAIL] 委托失败")
                    results.append({

                        'symbol': code,

                        'direction': direction,

                        'volume': volume,

                        'order_id': None,

                        'success': False

                    })



            except Exception as e:

                logger.error(f"  [ERROR] 订单执行异常: {e}")
                results.append({

                    'symbol': order.get('symbol'),

                    'direction': order.get('direction'),

                    'volume': order.get('volume'),

                    'order_id': None,

                    'success': False,

                    'error': str(e)

                })



        return results



    def on_rebalance(self):

        """调仓回调"""

        logger.info(f"\n{'='*60}")
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TRIGGER] 触发调仓")
        logger.info(f"{'='*60}\n")


        # 1. 获取当前持仓

        current_positions = self.get_current_positions()

        logger.info(f"[INFO] 当前持仓: {len(current_positions)} 只股票")


        # 2. 计算目标组合

        date = datetime.now().strftime('%Y%m%d')

        try:

            target_portfolio = self.strategy.run_rebalance(date)

            logger.info(f"[OK] 目标持仓: {len(target_portfolio)} 只股票")


            if len(target_portfolio) > 0:

                logger.info("\n[INFO] 目标持仓明细:")
                for i, (stock, weight) in enumerate(target_portfolio.items(), 1):

                    logger.info(f"  {i}. {stock}: {weight:.2%}")


        except Exception as e:

            logger.error(f"[ERROR] 调仓失败: {e}")
            target_portfolio = {}



        # 3. 生成交易订单

        if target_portfolio:

            logger.info(f"\n[INFO] 生成交易订单...")
            orders = self._generate_orders(current_positions, target_portfolio)



            if orders:

                logger.info(f"[OK] 生成订单: {len(orders)} 笔")


                logger.info(f"\n{'='*60}")
                logger.info(f"委托单明细:")
                logger.info(f"{'='*60}")


                for i, order in enumerate(orders, 1):

                    direction_str = "买入" if order['direction'] == 'buy' else "卖出"

                    logger.info(f"  {i}. [{direction_str}] {order['symbol']}")
                    logger.info(f"     数量: {order['volume']} 股")
                    logger.info(f"     原因: {order['reason']}")
                    if 'amount' in order:

                        logger.info(f"     预计金额: {order['amount']:,.2f} 元")
                    print()



                # 4. 执行订单

                if self.is_connected:

                    logger.info(f"[INFO] QMT连接状态: {'已连接' if self.is_connected else '未连接'}")
                    logger.info(f"[INFO] 自动确认: {self.auto_confirm}")


                    if self.auto_confirm:

                        logger.warning(f"\n[WARN] 自动执行订单到QMT...")
                        results = self.execute_orders(orders)

                        success_count = sum(1 for r in results if r.get('success'))

                        logger.info(f"\n[OK] 订单执行: {success_count}/{len(orders)} 笔成功")
                    else:

                        logger.info(f"\n[INFO] 订单未发送到QMT（auto_confirm=False）")
                        logger.info(f"[TIPS] 在代码中设置 self.auto_confirm = True 可自动执行")
                else:

                    logger.info(f"\n[INFO] 未连接QMT，订单未发送")
            else:

                logger.info(f"[INFO] 无需调仓（当前持仓已是目标组合）")


        logger.info(f"\n{'='*60}")
        logger.info(f"[OK] 调仓完成")
        logger.info(f"{'='*60}\n")


    def _generate_orders(self, current_positions, target_portfolio):

        """生成交易订单"""

        orders = []



        # 获取账户资产

        try:

            asset = self.api.get_account_asset(self.account_id) if self.is_connected else None

            total_asset = asset.get('total_asset', 1000000) if asset else 1000000

        except Exception:

            total_asset = 1000000



        # 1. 卖出不在目标组合中的股票

        for code, pos_info in current_positions.items():

            if code not in target_portfolio:

                volume = pos_info.get('can_use_volume', 0)

                if volume > 0:

                    orders.append({

                        'symbol': code,

                        'direction': 'sell',

                        'volume': volume,

                        'reason': '不在目标组合中',

                        'amount': volume * 10  # 估算

                    })



        # 2. 买入目标组合中的股票

        for code, weight in target_portfolio.items():

            target_value = total_asset * weight



            # 简化计算：假设每股20元

            price = 20

            volume = int(target_value / price / 100) * 100  # 整手



            if volume > 0:

                orders.append({

                    'symbol': code,

                    'direction': 'buy',

                    'volume': volume,

                    'reason': f'目标权重{weight:.2%}',

                    'amount': volume * price

                })



        return orders



    def run(self):

        """运行实盘策略"""

        if not self.initialize():

            return



        logger.info(f"\n开始运行简单小市值策略实盘策略...")
        logger.info(f"{'='*60}")
        logger.info(f"账户ID: {self.account_id}")
        logger.info(f"QMT路径: {self.qmt_path}")
        logger.info(f"自动确认: {self.auto_confirm}")
        logger.info(f"QMT连接: {'已连接' if self.is_connected else '未连接'}")
        logger.info(f"{'='*60}\n")


        # 执行一次调仓测试

        self.on_rebalance()



        logger.info(f"\n{'='*60}")
        logger.info(f"[OK] 测试完成！")
        logger.info(f"{'='*60}")
        logger.info(f"\n[TIPS] 启用真实交易:")
        logger.info(f"  1. 确保QMT交易端已启动并登录")
        logger.info(f"  2. 在代码中设置 self.auto_confirm = True")
        logger.info(f"  3. 重新运行: python main.py")
        logger.info(f"{'='*60}\n")




def main():

    """主函数"""

    # 创建策略实例

    strategy_live = 简单小市值策略StrategyLive()



    # 运行策略

    try:

        strategy_live.run()

    except KeyboardInterrupt:

        logger.info(f"\n[INFO] 用户中断，程序退出")
    except Exception as e:

        logger.error(f"\n[ERROR] 运行出错: {e}")
        import traceback

        traceback.print_exc()





if __name__ == "__main__":

    main()

