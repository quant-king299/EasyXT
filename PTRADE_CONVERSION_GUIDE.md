# 聚宽转Ptrade代码转换工具使用指南与原理介绍

## 1. 概述

聚宽转Ptrade代码转换工具是为量化交易开发者设计的自动化代码转换工具，旨在帮助用户将聚宽（JoinQuant）平台的策略代码快速迁移到Ptrade平台。该工具通过AST（抽象语法树）解析技术，识别聚宽API调用并将其映射到相应的Ptrade API，实现代码的自动化转换。

## 2. 项目结构

```
miniqmt扩展/
├── code_converter/              # 代码转换器主目录
│   ├── converters/              # 各平台转换器实现
│   │   └── jq_to_ptrade.py     # 聚宽到Ptrade转换器核心逻辑
│   ├── samples/                # 示例策略文件
│   ├── utils/                  # 工具函数
│   ├── cli.py                  # 命令行接口
│   └── api_mapping.json        # API映射配置文件
├── gui_app/                    # 图形用户界面
│   ├── widgets/                # UI组件
│   │   └── jq_to_ptrade_widget.py  # 聚宽转Ptrade GUI组件
│   └── main_window.py          # 主窗口文件
├── start_gui.py                # GUI启动脚本
└── PTRADE_CONVERSION_GUIDE.md  # 本使用指南文档
```

## 3. 工具原理

### 3.1 AST解析技术
工具使用Python的ast模块对聚宽策略代码进行解析，将源代码转换为抽象语法树结构，然后通过自定义的转换器遍历和修改AST节点，最终生成Ptrade兼容的代码。

### 3.2 API映射机制
工具内置了聚宽到Ptrade的API映射规则，能够自动识别并转换常见的API调用：

- 数据获取API：`get_price`、`get_current_data`、`get_fundamentals`等
- 交易API：`order`、`order_value`、`order_target`等
- 账户API：`get_portfolio`、`get_positions`、`get_orders`等
- 系统API：`log`、`record`、`set_benchmark`等

### 3.3 导入语句处理
Ptrade平台与聚宽平台不同，不需要显式的导入语句。工具会自动移除所有导入语句，确保生成的代码在Ptrade环境中能够正常运行。

### 3.4 全局变量转换
工具会自动将聚宽中的`g`全局变量转换为Ptrade中的`context`变量，确保代码逻辑的一致性。

## 4. 使用方法

### 4.1 GUI界面使用
1. 启动GUI应用程序：
   ```bash
   python start_gui.py
   ```

2. 在主界面中选择"JQ转Ptrade"标签页

3. 选择输入方式：
   - **文件导入**：点击"浏览"按钮选择聚宽策略文件（.py）
   - **粘贴输入**：点击"粘贴代码"按钮，在弹出对话框中粘贴聚宽策略代码

4. 设置输出文件路径（可选）

5. 点击"开始转换"按钮

6. 转换完成后，可在"输出代码（Ptrade）"标签页中查看转换结果

7. 点击"保存输出"按钮保存转换后的代码

### 4.2 命令行使用
工具还提供了命令行接口，可通过以下方式使用：

```bash
# 基本用法
python code_converter/cli.py jq2ptrade <input_file> <output_file>

# 使用自定义API映射文件
python code_converter/cli.py jq2ptrade <input_file> <output_file> --mapping-file <mapping_file>
```

### 4.3 API映射文件自定义
用户可以通过创建自定义API映射文件来扩展或修改默认的API映射规则。映射文件为JSON格式，示例如下：

```json
{
  "get_price": "get_price",
  "order": "order",
  "log": "log"
}
```

## 5. 支持的转换功能

### 5.1 数据获取API
- `get_price` → `get_price`
- `get_current_data` → `get_current_data`
- `get_fundamentals` → `get_fundamentals`
- `get_index_stocks` → `get_index_stocks`
- `get_industry_stocks` → `get_industry_stocks`

### 5.2 交易API
- `order` → `order`
- `order_value` → `order_value`
- `order_target` → `order_target`
- `order_target_value` → `order_target_value`
- `cancel_order` → `cancel_order`

### 5.3 账户API
- `get_portfolio` → `get_portfolio`
- `get_positions` → `get_positions`
- `get_orders` → `get_orders`
- `get_trades` → `get_trades`

### 5.4 系统API
- `log` → `log`
- `record` → `record`
- `set_benchmark` → `set_benchmark`
- `set_option` → `set_option`

### 5.5 风险控制API
- `set_slippage` → `set_slippage`
- `set_commission` → `set_commission`

### 5.6 定时任务API
- `run_daily` → `run_daily`
- `run_weekly` → `run_weekly`
- `run_monthly` → `run_monthly`

## 6. 注意事项

### 6.1 平台差异
虽然工具能够自动转换大部分API调用，但由于聚宽和Ptrade平台在功能和API设计上存在差异，部分高级功能可能需要手动调整。

### 6.2 代码逻辑
工具主要处理API层面的转换，对于复杂的业务逻辑和算法，用户需要根据Ptrade平台的特性进行适当调整。

### 6.3 测试验证
转换后的代码应在Ptrade平台上进行充分测试，确保功能正确性和交易逻辑的准确性。

### 6.4 错误处理
如果转换过程中出现错误，工具会提供详细的错误信息，帮助用户定位和解决问题。

## 7. 常见问题

### 7.1 转换后代码无法运行
可能原因：
1. 平台API差异导致的功能不兼容
2. 策略中使用了工具不支持的高级功能
3. 代码中包含平台特定的实现

解决方案：
1. 检查转换后的代码，手动调整不兼容的部分
2. 参考Ptrade官方文档，修改相关API调用
3. 联系技术支持获取帮助

### 7.2 转换结果不正确
可能原因：
1. API映射规则不完整
2. 代码结构复杂，工具无法正确解析
3. 使用了动态生成的代码

解决方案：
1. 提供反馈，帮助完善API映射规则
2. 简化代码结构后再进行转换
3. 手动调整转换结果

## 8. 技术支持

如在使用过程中遇到问题，请通过以下方式获取技术支持：
- 查看工具文档和FAQ
- 提交GitHub Issue
- 联系项目维护人员

## 9. 版本更新

工具会持续更新以支持更多的API和功能，请定期检查更新：
```bash
git pull origin main
```

## 10. 贡献指南

欢迎贡献代码和改进意见：
1. Fork项目仓库
2. 创建功能分支
3. 提交Pull Request
4. 等待代码审查和合并

## 11. 许可证

本工具采用MIT许可证，详情请查看LICENSE文件。

---

*作者微信: www_ptqmt_com*  
*欢迎关注微信公众号: 王者quant*