# EasyXT策略开发文件夹

这个文件夹包含了EasyXT量化交易系统的所有策略开发相关文件和工具。

## 📁 目录结构

```
strategies/
├── README.md                           # 本文件
├── base/                              # 基础策略框架
│   └── strategy_template.py           # 策略基类模板
├── trend_following/                   # 趋势跟踪策略
│   └── 双均线策略.py                  # 双均线策略实现
├── mean_reversion/                    # 均值回归策略
├── arbitrage/                         # 套利策略
├── grid_trading/                      # 网格交易策略
│   └── 固定网格.py                    # 固定网格策略实现
├── conditional_orders/                # 条件单策略
│   └── 止损止盈.py                    # 止损止盈策略实现
├── custom/                           # 自定义策略
├── adapters/                         # 外部系统适配器
│   ├── __init__.py
│   ├── jq2qmt_adapter.py            # JQ2QMT集成适配器
│   └── data_converter.py            # 数据格式转换器
├── examples/                         # 示例代码
│   └── jq2qmt_integration_example.py # JQ2QMT集成示例
├── jq2qmt/                          # JQ2QMT项目（克隆）
│   ├── src/                         # JQ2QMT源代码
│   ├── README.md                    # JQ2QMT项目说明
│   └── ...                          # 其他JQ2QMT文件
├── tdxtrader/                       # 通达信预警交易系统
│   ├── README.md                    # tdxtrader项目说明
│   ├── BLOCK_TRADING_FEATURES.md    # 板块交易功能详解
│   └── ...                          # 其他tdxtrader文件
├── jq2qmt_analysis_report.md        # JQ2QMT项目深度分析报告
└── JQ2QMT_Integration_Guide.md      # JQ2QMT集成指南
```

## 🎯 策略开发指南

### 1. 基础策略开发

#### 使用策略基类
所有策略都应该继承自 `BaseStrategy` 基类：

```python
from base.strategy_template import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        # 策略特定的初始化
    
    def calculate_signals(self):
        # 实现你的策略逻辑
        pass
    
    def on_market_data(self, data):
        # 处理市场数据
        pass
```

#### 策略配置
每个策略都需要一个配置字典：

```python
config = {
    'strategy_name': '我的策略',
    'symbol_list': ['000001.SZ', '000002.SZ'],
    'initial_capital': 1000000,
    'risk_management': {
        'max_position_ratio': 0.1,
        'stop_loss_ratio': 0.05
    }
}
```

### 2. 策略类型说明

#### 趋势跟踪策略 (`trend_following/`)
- **双均线策略**: 基于快慢均线交叉的经典策略
- **动量策略**: 基于价格动量的趋势跟踪
- **突破策略**: 基于价格突破的交易策略

#### 均值回归策略 (`mean_reversion/`)
- **布林带策略**: 基于布林带的均值回归
- **RSI策略**: 基于相对强弱指数的反转策略
- **配对交易**: 基于股票对的统计套利

#### 网格交易策略 (`grid_trading/`)
- **固定网格**: 固定价格间隔的网格交易
- **高频分时网格**: 基于相对涨跌幅的高频网格交易（推荐）
- **动态网格**: 根据波动率调整的动态网格（待实现）
- **多层网格**: 多个价格层级的复合网格（待实现）

> 📖 详细对比和使用指南请查看：`strategies/grid_trading/README.md`

#### 条件单策略 (`conditional_orders/`)
- **止损止盈**: 自动止损止盈策略
- **追踪止损**: 动态调整的追踪止损
- **时间条件单**: 基于时间条件的交易

#### 通达信预警交易策略 (`tdxtrader/`)
- **预警文件触发**: 基于通达信技术指标预警的自动化交易
- **板块文件触发**: 基于通达信自定义板块的实时交易触发
- **双重保险机制**: EasyXT与xt_trader双通道下单保障

查看详细文档：[tdxtrader板块交易功能详解](tdxtrader/BLOCK_TRADING_FEATURES.md)

### 3. 外部系统集成

#### JQ2QMT集成
支持将聚宽策略迁移到QMT交易终端：

```python
from examples.jq2qmt_integration_example import JQ2QMTIntegratedStrategy

class MyJQStrategy(JQ2QMTIntegratedStrategy):
    def __init__(self, config):
        # 启用JQ2QMT集成
        config['jq2qmt_config'] = {
            'enabled': True,
            'auto_sync': True
        }
        super().__init__(config)
```

#### 适配器使用
```python
from adapters.jq2qmt_adapter import EasyXTJQ2QMTAdapter

# 创建适配器
adapter = EasyXTJQ2QMTAdapter(jq2qmt_config)

# 同步持仓
adapter.sync_positions_to_qmt(strategy_name, positions)
```

## 🔧 开发工具

### 1. 数据转换工具
```python
from adapters.data_converter import DataConverter

# 格式转换
jq2qmt_positions = DataConverter.easyxt_to_jq2qmt(easyxt_positions)

# 数据验证
is_valid = DataConverter.validate_easyxt_position(position)

# 持仓合并
merged = DataConverter.merge_positions(positions_list)
```

### 2. 持仓差异分析
```python
from adapters.data_converter import PositionDiffer

# 比较持仓差异
diff_result = PositionDiffer.compare_positions(current, target)
```

### 3. 策略回测框架
```python
# 使用基类的回测功能
strategy = MyStrategy(config)
backtest_result = strategy.run_backtest(start_date, end_date)
```

## 📊 策略性能评估

### 1. 关键指标
- **总收益率**: 策略的总体收益表现
- **夏普比率**: 风险调整后的收益率
- **最大回撤**: 策略的最大亏损幅度
- **胜率**: 盈利交易占总交易的比例

### 2. 风险控制
- **仓位管理**: 控制单只股票的最大持仓比例
- **止损机制**: 设置合理的止损点位
- **资金管理**: 合理分配资金到不同策略

### 3. 性能监控
```python
# 获取策略性能指标
performance = strategy.get_performance_metrics()
print(f"总收益率: {performance['total_return']:.2%}")
print(f"夏普比率: {performance['sharpe_ratio']:.2f}")
print(f"最大回撤: {performance['max_drawdown']:.2%}")
```

## 🚀 部署运行

### 1. 本地开发
```bash
# 运行单个策略
python trend_following/双均线策略.py

# 运行JQ2QMT集成示例
python examples/jq2qmt_integration_example.py
```

### 2. 生产环境
```bash
# 启动JQ2QMT服务
cd jq2qmt/src
python app.py

# 启动EasyXT主程序
cd ../../gui_app
python main_window.py
```

### 3. 配置管理
- 策略配置文件: `config/strategy_config.json`
- JQ2QMT配置文件: `config/jq2qmt_config.json`
- 日志配置: `config/logging_config.json`

## 📚 学习资源

### 1. 文档资料
- [JQ2QMT项目深度分析报告](jq2qmt_analysis_report.md)
- [JQ2QMT集成指南](JQ2QMT_Integration_Guide.md)
- [策略开发最佳实践](../docs/strategy_development_best_practices.md)

### 2. 示例代码
- [JQ2QMT集成示例](examples/jq2qmt_integration_example.py)
- [双均线策略示例](trend_following/双均线策略.py)
- [网格交易示例](grid_trading/固定网格.py)

### 3. API参考
- [BaseStrategy API](base/strategy_template.py)
- [JQ2QMT适配器API](adapters/jq2qmt_adapter.py)
- [数据转换器API](adapters/data_converter.py)

## 🤝 贡献指南

### 1. 代码规范
- 使用Python PEP 8编码规范
- 添加详细的文档字符串
- 编写单元测试

### 2. 提交流程
1. Fork项目仓库
2. 创建功能分支
3. 提交代码变更
4. 创建Pull Request

### 3. 策略贡献
- 新策略应放在对应的策略类型文件夹中
- 提供完整的策略说明和使用示例
- 包含回测结果和性能分析

## 🔍 故障排除

### 1. 常见问题
- **导入错误**: 检查Python路径配置
- **连接失败**: 验证JQ2QMT服务是否启动
- **认证失败**: 检查RSA密钥配置

### 2. 调试方法
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用策略调试日志
strategy.set_log_level(logging.DEBUG)
```

### 3. 性能优化
- 使用向量化计算提高数据处理速度
- 合理设置数据缓存机制
- 优化策略信号计算逻辑

## 📞 技术支持

如果在策略开发过程中遇到问题，可以通过以下方式获取帮助：

1. **查看文档**: 详细阅读相关文档和示例代码
2. **检查日志**: 查看策略运行日志定位问题
3. **社区讨论**: 在项目社区中提问和讨论
4. **提交Issue**: 在GitHub上提交问题报告

---

**EasyXT策略开发团队**  
*让量化交易更简单，让策略开发更高效*