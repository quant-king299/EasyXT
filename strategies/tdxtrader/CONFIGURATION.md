# TDX与EasyXT集成配置说明

本集成方案使用项目根目录下的统一配置文件来管理账户ID和QMT路径，避免在多个地方重复配置。

## 配置文件位置

配置文件位于项目根目录的 `config/unified_config.json` 文件中。

## 账户ID配置

在统一配置文件中找到 `settings.account.account_id` 字段并设置您的账户ID：

```json
{
  "settings": {
    "account": {
      "account_id": "39020958",
      "account_id_comment": "交易账户ID（模拟或实盘账户）"
    }
  }
}
```

## QMT路径配置

在统一配置文件中找到 `settings.account.qmt_path` 字段并设置您的QMT安装路径：

```json
{
  "settings": {
    "account": {
      "qmt_path": "D:\\国金QMT交易端模拟\\userdata_mini",
      "qmt_path_comment": "QMT交易端的安装/数据路径（用于连接本地交易端）"
    }
  }
}
```

注意：路径应指向 `userdata_mini` 目录，而不是QMT的根安装目录。

## 其他配置

其他与通达信预警相关的配置保存在 `strategies/tdxtrader` 目录下的配置文件中，可以通过运行以下命令创建配置模板：

```bash
python strategies/tdxtrader/test_integration.py
```

生成的配置文件 `test_config.json` 包含以下配置项：

- `tdx_file_path`: 通达信预警文件路径
- `interval`: 轮询间隔（秒）
- `buy_signals`: 买入信号名称列表
- `sell_signals`: 卖出信号名称列表
- `cancel_after`: 未成交撤单时间（秒）
- `default_volume`: 默认交易数量
- `price_type`: 价格类型（limit或market）

## 验证配置

运行测试脚本验证配置是否正确加载：

```bash
python strategies/tdxtrader/test_integration.py
```

如果配置正确，您应该看到类似以下的输出：

```
统一配置中的账户ID: 39020958
统一配置中的QMT路径: D:\国金QMT交易端模拟\userdata_mini
```