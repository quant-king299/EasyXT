# 统一配置管理器

## 概述

`core/config` 模块提供了项目级的统一配置管理功能，解决了之前配置分散、路径硬编码的问题。

## 特性

1. **配置层级** - 支持系统级、用户级、运行时配置
2. **嵌套访问** - 支持点号分隔的嵌套键访问（如 `data_providers.tdx.timeout`）
3. **线程安全** - 所有操作都是线程安全的
4. **自动保存** - 用户级配置修改自动保存到文件
5. **配置验证** - 内置配置验证功能
6. **导入导出** - 支持配置的导入和导出

## 快速开始

### 基本使用

```python
from core.config import get_config, set_config

# 获取配置
timeout = get_config("data_providers.tdx.timeout", 30)
log_level = get_config("logging.level", "INFO")

# 设置配置
set_config("logging.level", "DEBUG")
set_config("data_providers.tdx.timeout", 60)
```

### 使用配置管理器

```python
from core.config import UnifiedConfigManager

# 创建配置管理器
config = UnifiedConfigManager()

# 获取配置
timeout = config.get("data_providers.tdx.timeout")

# 设置配置
config.set("logging.level", "DEBUG")

# 获取配置段
data_providers = config.get_section("data_providers")

# 批量更新
config.update({
    "logging": {"level": "WARNING"},
    "custom": {"key": "value"}
})
```

### 配置层级

```python
from core.config import UnifiedConfigManager, ConfigLevel

config = UnifiedConfigManager()

# 系统级配置（默认值）
system_timeout = config.get("timeout", level=ConfigLevel.SYSTEM)

# 用户级配置（来自配置文件）
user_timeout = config.get("timeout", level=ConfigLevel.USER)

# 运行时配置（临时修改，优先级最高）
config.set("timeout", 999, level=ConfigLevel.RUNTIME)
runtime_timeout = config.get("timeout")  # 返回 999

# 重置运行时配置
config.reset_runtime()
```

## 配置文件位置

配置文件查找优先级：

1. 环境变量 `EASYXT_CONFIG_PATH`
2. 项目根目录 `/config/`
3. 当前工作目录 `/config/`
4. 用户主目录 `~/.miniqmt/`

## 配置文件格式

配置文件使用 JSON 格式：

```json
{
  "data_providers": {
    "tdx": {
      "enabled": true,
      "timeout": 30,
      "retry_count": 3
    },
    "eastmoney": {
      "enabled": true,
      "timeout": 25
    }
  },
  "logging": {
    "level": "INFO",
    "file_path": "logs/app.log"
  },
  "trading": {
    "dry_run": true,
    "commission": 0.0003
  }
}
```

## API 参考

### UnifiedConfigManager

#### `__init__(config_file='unified_config.json', auto_save=True, env_var='EASYXT_CONFIG_PATH')`

初始化配置管理器。

#### `get(key, default=None, level=None)`

获取配置值。

- `key`: 配置键，支持点号分隔的嵌套键
- `default`: 默认值
- `level`: 配置级别（ConfigLevel.SYSTEM/USER/RUNTIME）

#### `set(key, value, level=ConfigLevel.USER, save=None)`

设置配置值。

- `key`: 配置键
- `value`: 配置值
- `level`: 配置级别
- `save`: 是否立即保存

#### `get_all()`

获取所有配置（合并后的结果）。

#### `get_section(section)`

获取配置段。

#### `update(config, level=ConfigLevel.USER)`

批量更新配置。

#### `reload()`

重新加载配置文件。

#### `save()`

保存配置到文件。

#### `reset_runtime()`

重置运行时配置。

#### `validate()`

验证配置，返回包含 `valid`, `errors`, `warnings` 的字典。

#### `export(file_path)`

导出配置到指定文件。

#### `import_config(file_path, level=ConfigLevel.USER)`

从指定文件导入配置。

### 便捷函数

#### `get_config(key, default=None)`

获取配置值的便捷函数。

#### `set_config(key, value)`

设置配置值的便捷函数。

#### `get_config_dir(env_var='EASYXT_CONFIG_PATH')`

获取配置目录路径。

#### `get_config_path(filename='unified_config.json', env_var='EASYXT_CONFIG_PATH')`

获取配置文件完整路径。

## 使用示例

### 示例1：在策略中使用配置

```python
# strategies/my_strategy/main.py
from core.config import get_config

class MyStrategy:
    def __init__(self):
        # 从配置读取参数
        self.timeout = get_config("data_providers.tdx.timeout", 30)
        self.dry_run = get_config("trading.dry_run", True)
        self.log_level = get_config("logging.level", "INFO")
```

### 示例2：在数据管理器中使用配置

```python
# core/data_manager/manager.py
from core.config import get_config

class DataManager:
    def __init__(self):
        # 获取缓存配置
        cache_enabled = get_config("cache.enabled", True)
        cache_ttl = get_config("cache.ttl", 300)

        # 获取数据源配置
        tdx_config = get_config("data_providers.tdx", {})
        self.timeout = tdx_config.get("timeout", 30)
```

### 示例3：运行时修改配置

```python
from core.config import UnifiedConfigManager, ConfigLevel

config = UnifiedConfigManager()

# 临时修改配置（不保存到文件）
config.set("logging.level", "DEBUG", level=ConfigLevel.RUNTIME)

# 执行某些操作...

# 重置运行时配置
config.reset_runtime()
```

### 示例4：配置验证

```python
from core.config import UnifiedConfigManager

config = UnifiedConfigManager()

# 验证配置
result = config.validate()

if not result['valid']:
    print("配置错误:")
    for error in result['errors']:
        print(f"  - {error}")
else:
    print("配置有效")
```

## 迁移指南

### 从旧的配置系统迁移

**之前（硬编码路径）：**
```python
import json
config_path = "strategies/xueqiu_follow/config/unified_config.json"
with open(config_path) as f:
    config = json.load(f)
```

**之后（统一配置管理）：**
```python
from core.config import get_config
timeout = get_config("data_providers.tdx.timeout", 30)
```

### 从环境变量迁移

**之前：**
```python
import os
config_path = os.getenv('MY_CONFIG_PATH', 'config.json')
```

**之后：**
```python
from core.config import get_config_path
config_path = get_config_path()
```

## 注意事项

1. **线程安全** - 配置管理器是线程安全的，可以在多线程环境中使用
2. **自动保存** - 默认情况下，用户级配置会自动保存，可以通过 `auto_save=False` 禁用
3. **运行时配置** - 运行时配置优先级最高，但不会保存到文件，重启后丢失
4. **配置验证** - 建议在应用启动时调用 `validate()` 检查配置

## 测试

运行测试：

```bash
python core/config/test_config_manager.py
```

## 相关文档

- `REFACTOR_PROGRESS.md` - 重构进度报告
- `docs/CONFIG_MIGRATION_GUIDE.md` - 配置迁移指南
- `TASK4_COMPLETE_REPORT.md` - Task 4 完成报告
