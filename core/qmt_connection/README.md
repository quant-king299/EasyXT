# QMT连接管理器使用指南

## 🎯 功能介绍

`core.qmt_connection` 模块提供统一的QMT连接检查和自动登录功能，用于：
- ✅ **策略启动前**检查QMT状态
- ✅ **数据获取前**确保QMT已登录
- ✅ 自动处理QMT连接断开重连

## 📖 快速开始

### 方法1：使用便捷函数（推荐）

```python
from core.qmt_connection import ensure_qmt_logged_in, get_qmt_status

# 检查QMT状态
status = get_qmt_status()
print(f"QMT运行: {status['running']}")
print(f"QMT登录: {status['logged_in']}")

# 确保QMT已登录（如果未登录会自动登录）
if ensure_qmt_logged_in(auto_login=True):
    print("QMT已就绪，可以开始操作")
    # 你的代码...
else:
    print("QMT登录失败")
```

### 方法2：使用装饰器（最简洁）

```python
from core.qmt_connection import require_qmt_login

@require_qmt_login(auto_login=True)
def my_strategy():
    """这个函数执行前会自动检查QMT状态"""
    from easy_xt import get_api
    api = get_api()
    # 你的策略代码...
```

### 方法3：使用管理器（高级）

```python
from core.qmt_connection import get_qmt_manager

manager = get_qmt_manager()

# 检查状态
status = manager.get_qmt_status()

# 确保登录
if manager.ensure_qmt_logged_in():
    # 你的代码...
```

## 🔧 集成到策略中

### 示例1：策略启动脚本

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.qmt_connection import ensure_qmt_logged_in

def main():
    """策略主函数"""
    print("策略启动中...")

    # 确保QMT已登录
    if not ensure_qmt_logged_in(auto_login=True):
        print("QMT登录失败，无法启动策略")
        return 1

    # 启动策略
    strategy = MyStrategy()
    strategy.run()

if __name__ == '__main__':
    exit(main())
```

### 示例2：数据获取函数

```python
from core.qmt_connection import require_qmt_login

@require_qmt_login(auto_login=True)
def get_stock_data(symbol):
    """获取股票数据（自动检查QMT）"""
    from easy_xt import get_api
    api = get_api()
    return api.get_stock_data(symbol)
```

### 示例3：101因子平台

```python
from core.qmt_connection import ensure_qmt_logged_in

def load_data_from_qmt():
    """从QMT获取数据"""
    # 确保QMT已登录
    if not ensure_qmt_logged_in():
        raise Exception("QMT未登录，无法获取数据")

    # 获取数据
    from easy_xt import get_api
    api = get_api()
    return api.get_stock_list()
```

## 🎨 API 参考

### `ensure_qmt_logged_in(auto_login=True, timeout=60)`

确保QMT已登录。

**参数：**
- `auto_login` (bool): 如果QMT未登录，是否自动登录（默认：True）
- `timeout` (int): 登录超时时间，秒（默认：60）

**返回：**
- `bool`: QMT是否已登录（或登录成功）

**示例：**
```python
from core.qmt_connection import ensure_qmt_logged_in

# 只检查，不自动登录
if ensure_qmt_logged_in(auto_login=False):
    print("QMT已登录")

# 检查并自动登录
if ensure_qmt_logged_in(auto_login=True, timeout=90):
    print("QMT已就绪")
```

### `get_qmt_status()`

获取QMT状态信息。

**返回：**
```python
{
    'running': bool,    # QMT是否在运行
    'logged_in': bool,  # QMT是否已登录
    'can_login': bool   # 是否可以自动登录
}
```

**示例：**
```python
from core.qmt_connection import get_qmt_status

status = get_qmt_status()
if not status['running']:
    print("QMT未运行")
elif not status['logged_in']:
    print("QMT未登录")
```

### `@require_qmt_login(auto_login=True)`

装饰器：确保QMT已登录再执行函数。

**参数：**
- `auto_login` (bool): 如果QMT未登录，是否自动登录（默认：True）

**示例：**
```python
from core.qmt_connection import require_qmt_login

@require_qmt_login(auto_login=True)
def my_function():
    # 这个函数执行前会自动检查QMT状态
    # 如果QMT未登录，会先自动登录
    pass
```

## ⚙️ 配置要求

使用QMT连接管理器前，需要配置 `.env` 文件：

```env
# QMT可执行文件路径
QMT_EXE_PATH=D:\国金QMT交易端模拟\bin.x64\XtMiniQmt.exe

# QMT登录密码
QMT_PASSWORD=your_password

# QMT数据目录（可选）
QMT_DATA_DIR=D:\国金QMT交易端模拟\userdata_mini
```

## 🚀 已集成的位置

目前QMT连接管理器已集成到以下位置：

1. ✅ `strategies/xueqiu_follow/start_xueqiu_follow_easyxt.py` - 雪球跟单策略
2. ✅ `examples/strategy_with_auto_login.py` - 策略示例
3. ✅ `examples/data_fetch_with_auto_login.py` - 数据获取示例

你可以参考这些示例，将QMT连接检查集成到其他策略中。

## 🐛 注意事项

1. **单例模式**：`QMTConnectionManager` 使用单例模式，全局共享一个实例
2. **缓存机制**：为了避免频繁检查，默认每30秒只检查一次
3. **自动登录**：如果 `auto_login=True`，QMT未登录时会自动调用 `start_qmt.py` 的逻辑
4. **错误处理**：如果QMT连接失败，函数会返回 `False`，需要调用方处理

## 📚 相关文档

- [QMT自动登录模块](../auto_login/README.md)
- [主项目README](../../README.md)
- [.env配置指南](../../.env.example)
