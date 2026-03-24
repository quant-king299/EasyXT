"""
实盘代码生成器

根据YAML策略配置自动生成EasyXT实盘交易代码。
"""

import os
from typing import Dict, List
from pathlib import Path
from datetime import datetime

# 导入配置
try:
    from ..config import StrategyConfig
except ImportError:
    from easyxt_backtest.config import StrategyConfig


class LiveCodeGenerator:
    """
    实盘代码生成器

    功能：
    1. 根据YAML配置生成实盘交易代码
    2. 生成策略逻辑模块
    3. 生成订单管理模块
    4. 生成风控模块
    5. 生成主程序
    """

    def __init__(self):
        """初始化代码生成器"""
        pass

    def generate_live_strategy(self,
                               config: StrategyConfig,
                               output_dir: str) -> Dict[str, str]:
        """
        生成完整的实盘策略代码

        Args:
            config: 策略配置
            output_dir: 输出目录

        Returns:
            Dict[str, str]: 生成的文件路径字典
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files_created = {}

        # 1. 生成策略配置文件
        config_file = output_path / 'strategy_config.py'
        self._generate_config_file(config, config_file)
        files_created['config'] = str(config_file)

        # 2. 生成策略逻辑模块
        strategy_file = output_path / 'strategy_logic.py'
        self._generate_strategy_logic(config, strategy_file)
        files_created['strategy'] = str(strategy_file)

        # 3. 生成订单管理模块
        order_file = output_path / 'order_manager.py'
        self._generate_order_manager(order_file)
        files_created['order_manager'] = str(order_file)

        # 4. 生成风控模块
        risk_file = output_path / 'risk_control.py'
        self._generate_risk_control(risk_file)
        files_created['risk_control'] = str(risk_file)

        # 5. 生成主程序
        main_file = output_path / 'main.py'
        self._generate_main(config, main_file)
        files_created['main'] = str(main_file)

        # 6. 生成README
        readme_file = output_path / 'README.md'
        self._generate_readme(config, readme_file)
        files_created['readme'] = str(readme_file)

        return files_created

    def _generate_config_file(self, config: StrategyConfig, file_path: Path):
        """生成策略配置文件"""
        content = f'''"""
策略配置文件

从YAML配置自动生成
"""

# 回测参数
BACKTEST_CONFIG = {config.backtest_config}

# 股票池配置
UNIVERSE_CONFIG = {config.universe_config}

# 打分因子配置
SCORING_FACTORS_CONFIG = [
'''

        for i, f in enumerate(config.scoring_factors):
            content += f"""    {{
        'name': '{f.name}',
        'factor_type': '{f.factor_type}',
        'field': '{f.field}',
        'direction': {f.direction},
        'weight': {f.weight},
        'normalize': {f.normalize},
        'neutralize': {f.neutralize}
    }}"""
            if i < len(config.scoring_factors) - 1:
                content += ","

        content += "\n]\n\n# 组合构建配置\nPORTFOLIO_CONFIG = " + str(config.portfolio_config) + "\n\n# 调仓配置\nREBALANCE_CONFIG = " + str(config.rebalance_config)

        file_path.write_text(content, encoding='utf-8')

    def _generate_strategy_logic(self, config: StrategyConfig, file_path: Path):
        """生成策略逻辑模块"""
        class_name = config.name.replace(' ', '').replace('-', '_') + 'Strategy'

        content = f'''# -*- coding: utf-8 -*-
"""
策略逻辑模块

自动生成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

from typing import List, Dict
from datetime import datetime


class {class_name}:
    """
    {config.description}

    核心逻辑：
    1. 获取股票池
    2. 应用排除条件
    3. 计算因子得分
    4. 构建投资组合
    """

    def __init__(self, data_manager):
        """
        初始化策略

        Args:
            data_manager: 数据管理器
        """
        self.data_manager = data_manager
        self.name = "{config.name}"
        self.current_portfolio = {{}}

        # 配置
        self.universe_config = {config.universe_config}
        self.portfolio_config = {config.portfolio_config}

    def get_stock_pool(self, date: str) -> List[str]:
        """
        获取股票池

        Args:
            date: 日期 (YYYYMMDD)

        Returns:
            股票列表
        """
        universe_config = self.universe_config

        if universe_config['type'] == 'index':
            index_code = universe_config['index_code']
            if hasattr(self.data_manager, 'get_index_components'):
                return self.data_manager.get_index_components(index_code, date)
            else:
                raise ValueError(f"无法获取指数成分股: {{index_code}}")

        return universe_config.get('codes', [])

    def apply_filters(self, stock_pool: List[str], date: str) -> List[str]:
        """
        应用排除条件

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            过滤后的股票列表
        """
        # TODO: 实现过滤逻辑
        return stock_pool

    def calculate_scores(self, stock_pool: List[str], date: str) -> Dict[str, float]:
        """
        计算因子得分

        根据配置的打分因子计算股票得分

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            股票得分字典
        """
        scores = {{}}

        if self.data_manager is not None:
            try:
                # 获取所有需要的因子字段
                factor_fields = []
                for factor in {config.scoring_factors}:
                    factor_fields.append(factor['field'])

                # 获取基本面数据
                fundamentals = self.data_manager.get_fundamentals(
                    codes=stock_pool,
                    date=date,
                    fields=factor_fields
                )

                if fundamentals is not None and not fundamentals.empty:
                    # 计算每个股票的综合得分
                    for stock in stock_pool:
                        if stock in fundamentals.index:
                            total_score = 0.0
                            valid_factors = 0

                            for factor in {config.scoring_factors}:
                                field = factor['field']
                                direction = factor['direction']
                                weight = factor['weight']

                                if field in fundamentals.columns:
                                    factor_value = fundamentals.loc[stock, field]
                                    # 根据方向调整因子值
                                    if direction == -1:
                                        # 负相关：值越小越好
                                        factor_score = -factor_value
                                    else:
                                        # 正相关：值越大越好
                                        factor_score = factor_value

                                    total_score += factor_score * weight
                                    valid_factors += 1

                            if valid_factors > 0:
                                scores[stock] = total_score
                            else:
                                scores[stock] = -float('inf')
                        else:
                            # 没有数据的股票，给一个很低的得分
                            scores[stock] = -float('inf')
                else:
                    print("[WARN] 无法获取基本面数据")
                    scores = {{stock: 0.0 for stock in stock_pool}}
            except Exception as e:
                print(f"[WARN] 计算因子得分失败: {{e}}")
                scores = {{stock: 0.0 for stock in stock_pool}}
        else:
            print("[WARN] data_manager未配置")
            scores = {{stock: 0.0 for stock in stock_pool}}

        return scores

    def build_portfolio(self, scores: Dict[str, float], date: str) -> Dict[str, float]:
        """
        构建投资组合

        Args:
            scores: 股票得分
            date: 日期

        Returns:
            持仓权重字典
        """
        portfolio_config = self.portfolio_config

        # 选股
        if portfolio_config['select_method'] == 'top_n':
            top_n = portfolio_config['top_n']
            selected = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        else:
            selected = list(scores.items())

        # 分配权重
        if portfolio_config['weight_method'] == 'equal':
            weights = {{stock: 1.0/len(selected) for stock, _ in selected}}
        else:
            weights = dict(selected)

        return weights

    def run_rebalance(self, date: str) -> Dict[str, float]:
        """
        运行调仓逻辑

        Args:
            date: 日期

        Returns:
            目标持仓
        """
        # 1. 获取股票池
        stock_pool = self.get_stock_pool(date)

        # 2. 应用过滤
        filtered_stocks = self.apply_filters(stock_pool, date)

        # 3. 计算得分
        scores = self.calculate_scores(filtered_stocks, date)

        # 4. 构建组合
        portfolio = self.build_portfolio(scores, date)

        self.current_portfolio = portfolio

        return portfolio
'''

        file_path.write_text(content, encoding='utf-8')

    def _generate_order_manager(self, file_path: Path):
        """生成订单管理模块"""
        content = '''# -*- coding: utf-8 -*-
"""
订单管理模块

提供订单执行和管理功能。
"""

from typing import List, Dict
from datetime import datetime


class OrderManager:
    """
    订单管理器

    功能：
    1. 创建订单
    2. 执行订单
    3. 跟踪订单状态
    4. 记录交易历史
    """

    def __init__(self, trader):
        """
        初始化订单管理器

        Args:
            trader: QMT交易接口实例
        """
        self.trader = trader
        self.order_history = []
        self.current_orders = {}

    def create_order(self, symbol: str, direction: str, volume: int, price: float = None):
        """
        创建订单

        Args:
            symbol: 股票代码
            direction: 方向 ('buy'/'sell')
            volume: 数量
            price: 价格 (None=市价单)
        """
        order = {
            'symbol': symbol,
            'direction': direction,
            'volume': volume,
            'price': price,
            'status': 'pending',
            'created_at': datetime.now()
        }

        order_id = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.current_orders[order_id] = order

        return order_id

    def execute_order(self, order_id: str):
        """
        执行订单

        Args:
            order_id: 订单ID
        """
        order = self.current_orders.get(order_id)
        if not order:
            print(f"订单不存在: {order_id}")
            return False

        try:
            # 调用QMT交易接口
            if order['direction'] == 'buy':
                result = self.trader.order_buy(
                    stock_code=order['symbol'],
                    order_type=0,  # 限价单
                    price=order['price'],
                    volume=order['volume']
                )
            else:
                result = self.trader.order_sell(
                    stock_code=order['symbol'],
                    order_type=0,
                    price=order['price'],
                    volume=order['volume']
                )

            order['status'] = 'filled'
            order['filled_at'] = datetime.now()
            self.order_history.append(order)

            return True

        except Exception as e:
            print(f"执行订单失败: {e}")
            order['status'] = 'failed'
            return False

    def cancel_order(self, order_id: str):
        """
        取消订单

        Args:
            order_id: 订单ID
        """
        if order_id in self.current_orders:
            self.current_orders[order_id]['status'] = 'cancelled'
            return True
        return False

    def get_positions(self) -> Dict[str, int]:
        """
        获取当前持仓

        Returns:
            持仓字典 {symbol: volume}
        """
        positions = {}

        try:
            # 从QMT获取持仓
            pos = self.trader.query_stock_positions()
            for p in pos:
                positions[p['stock_code']] = p['volume']
        except Exception as e:
            print(f"获取持仓失败: {e}")

        return positions

    def get_account_info(self) -> Dict:
        """
        获取账户信息

        Returns:
            账户信息字典
        """
        try:
            account = self.trader.query_stock_account()
            return {{
                'cash': account.get('cash', 0),
                'market_value': account.get('market_value', 0),
                'total_asset': account.get('total_asset', 0)
            }}
        except Exception as e:
            print(f"获取账户信息失败: {e}")
            return {}
'''

        file_path.write_text(content, encoding='utf-8')

    def _generate_risk_control(self, file_path: Path):
        """生成风控模块"""
        content = '''# -*- coding: utf-8 -*-
"""
风险控制模块

提供风险监控和控制功能。
"""

from typing import Dict, List


class RiskController:
    """
    风控控制器

    功能：
    1. 持仓检查
    2. 风险指标监控
    3. 止损止盈
    4. 异常告警
    """

    def __init__(self, risk_config: Dict):
        """
        初始化风控

        Args:
            risk_config: 风控配置
        """
        self.config = risk_config
        self.max_drawdown = risk_config.get('max_drawdown', 0.15)
        self.max_single_loss = risk_config.get('max_loss_per_trade', 0.02)

    def check_order(self, order: Dict, account: Dict) -> bool:
        """
        检查订单是否符合风控要求

        Args:
            order: 订单信息
            account: 账户信息

        Returns:
            是否通过风控
        """
        # 1. 检查资金充足性
        if order['direction'] == 'buy':
            required = order['volume'] * order['price']
            if required > account['cash']:
                print(f"资金不足: 需要{{required:.2f}}, 可用{{account['cash']:.2f}}")
                return False

        # 2. 检查单笔亏损限制
        if order['direction'] == 'buy':
            # 可以添加更多风控逻辑
            pass

        return True

    def check_portfolio(self, positions: Dict, account: Dict) -> bool:
        """
        检查组合是否符合风控要求

        Args:
            positions: 持仓
            account: 账户

        Returns:
            是否通过风控
        """
        # 计算组合风险
        # ...

        return True

    def check_drawdown(self, current_value: float, peak_value: float) -> bool:
        """
        检查回撤

        Args:
            current_value: 当前净值
            peak_value: 历史最高净值

        Returns:
            是否超限
        """
        if peak_value > 0:
            drawdown = (peak_value - current_value) / peak_value
            if drawdown > self.max_drawdown:
                print(f"⚠️ 回撤超限: {{drawdown:.2%}} > {{self.max_drawdown:.2%}}")
                return False
        return True
'''

        file_path.write_text(content, encoding='utf-8')

    def _generate_main(self, config: StrategyConfig, file_path: Path):
        """生成主程序"""
        live_config = config.live_trading_config or {}
        class_name = config.name.replace(' ', '').replace('-', '_') + 'Strategy'

        content = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
{config.name} - 实盘交易主程序

自动生成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
策略描述: {config.description}
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from strategy_logic import {class_name}
from order_manager import OrderManager
from risk_control import RiskController


class {class_name}Live:
    """
    {config.description} 实盘交易版
    """

    def __init__(self, account_id: str = "{live_config.get('account_id', 'your_account')}"):
        """
        初始化实盘策略

        Args:
            account_id: QMT账户ID
        """
        self.account_id = account_id
        self.trader = None
        self.strategy = None
        self.order_manager = None
        self.risk_controller = None

        # 策略配置
        self.rebalance_frequency = "{config.rebalance_config.get('frequency', 'monthly')}"
        self.is_running = False

    def initialize(self):
        """初始化"""
        print(f"初始化{config.name}实盘策略...")

        # TODO: 连接QMT
        # self.trader = XtQuantTrader(self.account_id)

        # 初始化策略
        self.strategy = {class_name}(None)

        # 初始化订单管理
        # self.order_manager = OrderManager(self.trader)

        # 初始化风控
        risk_config = {live_config.get('risk_control', dict())}
        self.risk_controller = RiskController(risk_config)

        print("✅ 初始化完成（模拟模式）")
        return True

    def on_rebalance(self):
        """调仓回调"""
        print(f"\\n[{{datetime.now()}}] 🔔 触发调仓")

        # 1. 获取当前持仓
        # current_positions = self.order_manager.get_positions()

        # 2. 计算目标组合
        date = datetime.now().strftime('%Y%m%d')
        target_portfolio = self.strategy.run_rebalance(date)

        print(f"✅ 调仓完成（模拟模式）")
        print(f"   目标持仓: {{len(target_portfolio)}} 只股票")

    def run(self):
        """运行实盘策略"""
        if not self.initialize():
            return

        self.is_running = True

        print(f"\\n开始运行{config.name}实盘策略...")
        print(f"账户ID: {{self.account_id}}")
        print(f"⚠️  模拟模式：不会执行实际交易")

        # 执行一次调仓测试
        self.on_rebalance()

        print(f"\\n✅ 测试完成！")
        print(f"\\n💡 实盘使用时需要:")
        print(f"   1. 配置QMT账户ID")
        print(f"   2. 取消注释QMT相关代码")
        print(f"   3. 运行策略: python main.py")


def main():
    """主函数"""
    # 创建策略实例
    strategy_live = {class_name}Live()

    # 运行策略
    strategy_live.run()


if __name__ == "__main__":
    main()
'''

        file_path.write_text(content, encoding='utf-8')

    def _generate_readme(self, config: StrategyConfig, file_path: Path):
        """生成README文档"""
        content = f'''# {config.name} - 实盘交易策略

## 策略说明

{config.description}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 文件结构

```
{config.name}/
├── main.py                  # 主程序
├── strategy_config.py      # 策略配置
├── strategy_logic.py       # 策略逻辑
├── order_manager.py        # 订单管理
├── risk_control.py         # 风控
└── README.md              # 本文件
```

## 使用方法

### 1. 安装依赖

```bash
pip install easyxt pandas numpy
```

### 2. 配置账户ID

编辑 `main.py`，修改 `account_id` 为你的QMT账户ID。

### 3. 运行策略

```bash
python main.py
```

## 策略配置

### 回测参数
- 开始日期: {config.backtest_config['start_date']}
- 结束日期: {config.backtest_config['end_date']}
- 初始资金: {config.backtest_config['initial_cash']:,}
- 佣金: {config.backtest_config['commission']:.2%}

### 股票池
- 类型: {config.universe_config['type']}
- 指数: {config.universe_config.get('index_code', 'N/A')}

### 因子配置
'''

        for i, factor in enumerate(config.scoring_factors, 1):
            direction = "正相关" if factor.direction == 1 else "负相关"
            content += f"- {factor.name}: {direction}, 权重{factor.weight:.1%}\n"

        content += f'''
### 组合构建
- 选股方式: {config.portfolio_config['select_method']}
- 选择数量: {config.portfolio_config.get('top_n', 'N/A')}
- 权重方式: {config.portfolio_config['weight_method']}

### 调仓配置
- 频率: {config.rebalance_config['frequency']}

## 注意事项

1. 本策略自动生成，请仔细测试后使用
2. 实盘交易有风险，请谨慎使用
3. 建议先在模拟环境中验证
4. 确保QMT账户已正确配置

## 技术支持

- 查看策略逻辑: `strategy_logic.py`
- 查看风控设置: `risk_control.py`
- 查看订单管理: `order_manager.py`

---

由 **101因子平台** 自动生成
'''

        file_path.write_text(content, encoding='utf-8')
