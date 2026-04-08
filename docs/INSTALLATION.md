# EasyXT 安装指南

## 基础安装（推荐）

EasyXT 核心功能只需要基础依赖：

```bash
pip install -r requirements.txt
```

### 基础依赖包含：
- pandas - 数据处理
- numpy - 数值计算
- matplotlib - 图表绘制
- requests - 网络请求
- psutil - 系统工具

**默认存储方式：CSV格式**
- ✅ 无额外依赖
- ✅ 兼容性好
- ✅ 适合大多数场景

## 可选依赖（提升性能）

### 1. 启用高性能Parquet存储

如果你需要处理大量数据或追求更好的性能，可以安装pyarrow：

```bash
pip install pyarrow>=10.0.0
```

**安装后效果：**
- 🚀 数据读写速度提升3-5倍
- 📦 文件大小减少50-70%
- 💾 支持压缩和列式存储

系统会自动检测并启用Parquet存储。

### 2. 启用DuckDB数据库

DuckDB提供强大的SQL查询能力：

```bash
pip install duckdb
```

**适用场景：**
- 大规模数据分析
- 复杂SQL查询
- 数据仓库需求

### 3. 安装所有可选依赖

如果你想要最佳性能：

```bash
pip install pyarrow duckdb fastparquet
```

## 常见问题

### Q: 我该选择哪种安装方式？

**A:**
- **新手用户**：只需基础安装即可
- **量化开发者**：建议安装pyarrow
- **专业用户**：安装所有可选依赖

### Q: 如何检查当前使用的存储方式？

**A:** 启动GUI时会显示：
```
✅ 使用Parquet存储（高性能）  # 已安装pyarrow
ℹ️  使用CSV存储（无需额外依赖）  # 未安装pyarrow
```

### Q: 可以在已安装pyarrow后降级到CSV吗？

**A:** 可以，只需：
```bash
pip uninstall pyarrow
```
重启GUI后自动切换到CSV存储。

### Q: CSV和Parquet的数据可以互相转换吗？

**A:** 可以，但需要手动操作。建议：
- 新用户直接使用目标存储方式
- 老用户可以继续使用现有数据
- 系统会自动识别文件格式

## 系统要求

- Python 3.8+
- Windows 10+ / Linux / macOS
- 至少2GB可用内存

## 故障排除

### 安装失败

如果遇到安装问题，尝试：

```bash
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 导入错误

如果遇到模块导入错误：

```bash
# 重新安装依赖
pip install --force-reinstall -r requirements.txt

# 检查Python版本
python --version  # 确保 >= 3.8
```

## 获取帮助

- 📧 Email: support@example.com
- 💬 QQ群: 1018087929
- 📱 微信: www_ptqmt_com
- 🌐 GitHub: https://github.com/quant-king299/EasyXT/issues
