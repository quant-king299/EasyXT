# 101因子分析平台

基于EasyXT构建的完整101因子分析平台，提供从因子计算、分析、回测到策略构建的一站式量化研究解决方案。

## ✨ 核心特性

- 🎯 **完整因子库**：实现 WorldQuant Alpha101 全部101个因子 + Alpha191扩展因子
- 📊 **可视化工作流**：拖拽式界面，零代码构建量化策略
- 🚀 **高性能计算**：基于pandas向量化计算，支持大规模数据
- 📈 **完整分析工具**：IC分析、分层回测、绩效评估
- 🔌 **EasyXT集成**：无缝对接EasyXT数据接口

## 🚀 快速启动

### 方式1：启动增强版UI（推荐）

```bash
cd c:\Users\Administrator\Desktop\miniqmt扩展\101因子\101因子分析平台
python 启动增强版.py
```

或手动启动：

```bash
streamlit run src/workflow/ui_enhanced.py --server.port=8510 --server.address=127.0.0.1
```

访问：http://127.0.0.1:8510

### 方式2：使用代码调用

```python
from src.factor_engine.calculator import FactorCalculator

# 初始化计算器
calculator = FactorCalculator()

# 加载数据
symbols = ['000001.SZ', '000002.SZ', '600000.SH']
calculator.load_data(symbols, '2023-01-01', '2023-12-31')

# 计算因子
factor = calculator.calculate_single_factor(data, 'alpha078')
```

## 📚 项目结构

```
101因子分析平台/
├── src/                          # 源代码
│   ├── easyxt_adapter/          # EasyXT数据适配器
│   ├── factor_engine/           # 因子计算引擎
│   │   ├── alpha101.py         # ✅ Alpha101因子(101个)
│   │   ├── alpha191.py         # ✅ Alpha191因子(90个)
│   │   └── calculator.py       # 统一计算接口
│   ├── workflow/                # 可视化工作流
│   │   ├── ui_enhanced.py      # ✅ 增强版UI
│   │   └── engine.py           # 工作流引擎
│   └── analysis/                # 分析模块
├── config/                      # 配置文件
├── README.md                    # 本文件
├── USER_GUIDE.md               # 📖 详细使用指南
├── IMPLEMENTATION_GUIDE.md     # 🔧 实现细节文档
└── requirements.txt            # 依赖包
```

## 🎯 支持的因子

### Alpha101 因子 (alpha001-alpha101)
- ✅ 已完整实现全部101个因子
- 基于WorldQuant Alpha101公式
- 支持自定义参数调整

### Alpha191 扩展因子 (alpha102-alpha191)
- ✅ 已实现90个扩展因子
- 包含动量、反转、波动率等类型

**总计：191个Alpha因子**

## 📊 功能模块

### 1. 因子计算引擎
- 支持191个Alpha因子计算
- 40+基础操作符（ts_sum, sma, stddev等）
- 自动数据预处理和清洗

### 2. 可视化工作流
- 拖拽式策略构建
- 实时结果展示
- 支持保存/加载工作流

### 3. 因子分析工具
- IC/IR分析
- 分层回测
- 绩效评估（夏普比率、最大回撤等）

### 4. EasyXT集成
- 自动数据格式转换
- 实时行情支持
- 历史数据回测

## 💻 核心API

### 因子计算

```python
from src.factor_engine.calculator import FactorCalculator

calculator = FactorCalculator()

# 加载数据
data = calculator.load_data(
    symbols=['000001.SZ', '600000.SH'],
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 计算单个因子
factor = calculator.calculate_single_factor(data, 'alpha001')

# 计算多个因子
factors = calculator.calculate_factors(['alpha001', 'alpha002', 'alpha078'])
```

### 因子分析

```python
from src.workflow.engine import WorkflowEngine

# 创建工作流引擎
engine = WorkflowEngine()

# 添加节点
engine.add_data_node(symbols=['000001.SZ'], start='2023-01-01', end='2023-12-31')
engine.add_factor_node('alpha078')
engine.add_ic_analysis_node(periods=1)

# 执行工作流
results = engine.execute()
```

## 📖 详细文档

- **[USER_GUIDE.md](USER_GUIDE.md)** - 详细使用指南
  - 界面操作说明
  - 节点配置方法
  - 常见问题解答

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - 技术实现文档
  - 架构设计说明
  - 扩展开发指南
  - API参考文档

## 🔧 开发指南

### 添加自定义因子

在 `src/factor_engine/alpha101.py` 中添加：

```python
def alpha_custom(self) -> pd.DataFrame:
    """
    自定义因子
    公式：...
    """
    # 使用基础操作符
    close = self.data['close']
    volume = self.data['volume']

    # 计算因子值
    factor = self.rank(close / self.delay(close, 5))

    return factor
```

### 扩展工作流节点

参考 `src/workflow/nodes/` 中的节点实现：

```python
from src.workflow.nodes.base_node import BaseNode

class CustomNode(BaseNode):
    def execute(self, data):
        # 实现自定义逻辑
        return result
```

## 🛠️ 技术栈

- **数据处理**: pandas, numpy
- **科学计算**: scipy
- **可视化**: matplotlib, seaborn, plotly
- **UI框架**: streamlit
- **配置管理**: yaml, json

## ⚠️ 注意事项

1. **数据质量**：确保输入数据无过多缺失值
2. **内存管理**：大数据集注意内存使用
3. **因子选择**：建议先进行IC分析筛选有效因子
4. **参数调优**：根据实际情况调整回测参数

## 🚀 性能优化建议

- 使用缓存机制避免重复计算
- 批量计算因子提高效率
- 合理设置数据时间范围
- 定期清理临时文件

## 📝 更新日志

### v2.0.0 (2025-01-21)
- ✅ 完整实现Alpha101全部101个因子
- ✅ 新增Alpha191扩展因子（90个）
- ✅ 修复因子计算器支持alpha001-alpha191
- ✅ 优化UI界面，新增增强版工作流
- ✅ 清理临时文件，项目结构优化

### v1.0.0 (2024-12-XX)
- 初始版本发布
- 实现基础工作流功能
- 支持因子计算和分析

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📮 联系方式

- **微信公众号**: 王者quant
- **微信号**: www_ptqmt_com
- **GitHub**: [项目地址]

## 📄 许可证

MIT License

---

**🎉 祝您因子研究顺利！**
