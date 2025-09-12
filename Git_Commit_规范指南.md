# Git Commit 优雅提交指南

## 🎯 Commit消息规范

### 基本格式
```
<类型>(<范围>): <简短描述>

<详细描述>

<脚注>
```

### 常用类型 (Type)
- `feat`: 新功能 (feature)
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式化，不影响代码运行的变动
- `refactor`: 重构（即不是新增功能，也不是修改bug的代码变动）
- `test`: 增加测试
- `chore`: 构建过程或辅助工具的变动
- `perf`: 性能优化
- `ci`: CI/CD相关变更
- `build`: 影响构建系统或外部依赖的更改
- `revert`: 撤销之前的commit

### 范围 (Scope) - 可选
- `api`: API相关
- `ui`: 用户界面
- `core`: 核心功能
- `config`: 配置相关
- `docs`: 文档
- `test`: 测试相关

## 📋 实际示例

### 好的Commit消息
```bash
# 新功能
git commit -m "feat(api): 添加股票实时价格获取接口

- 支持多只股票同时查询
- 添加价格变动推送功能
- 集成WebSocket实时数据流

Closes #123"

# 修复bug
git commit -m "fix(trade): 修复交易下单时的价格精度问题

修复当股价小数位超过2位时，下单失败的问题。
现在支持最多4位小数的价格精度。

Fixes #456"

# 文档更新
git commit -m "docs: 更新API使用文档和安装指南

- 添加详细的环境配置步骤
- 更新依赖包版本要求
- 增加常见问题解答"

# 重构
git commit -m "refactor(core): 重构数据获取模块

- 提取公共数据处理逻辑
- 优化内存使用
- 提高代码可读性"
```

### 避免的Commit消息
```bash
# ❌ 不好的例子
git commit -m "fix bug"
git commit -m "update"
git commit -m "修改了一些东西"
git commit -m "临时提交"
```

## 🛠️ 实用命令

### 1. 修改最后一次commit消息
```bash
git commit --amend -m "新的commit消息"
```

### 2. 交互式提交（选择性添加文件）
```bash
git add -p  # 选择性添加代码块
git commit -m "feat: 添加新功能"
```

### 3. 查看提交历史
```bash
git log --oneline  # 简洁格式
git log --graph --oneline --all  # 图形化显示
```

### 4. 撤销提交
```bash
git reset --soft HEAD~1  # 撤销最后一次提交，保留更改
git reset --hard HEAD~1  # 撤销最后一次提交，丢弃更改
```

## 📊 针对您项目的Commit示例

### 功能开发
```bash
# 添加新的交易策略
git commit -m "feat(strategy): 添加均线交叉策略

- 实现5日和20日均线交叉买卖信号
- 支持自定义均线周期参数
- 添加回测功能验证策略效果

Closes #001"

# 优化数据获取
git commit -m "perf(data): 优化历史数据获取性能

- 使用多线程并发获取数据
- 添加本地缓存机制
- 减少API调用次数，提升50%性能"
```

### Bug修复
```bash
# 修复交易问题
git commit -m "fix(trade): 修复模拟交易账户余额计算错误

修复在模拟交易模式下，账户余额计算不准确的问题。
现在正确处理手续费和印花税的扣除。

Fixes #002"
```

### 文档和配置
```bash
# 更新文档
git commit -m "docs: 完善学习实例文档

- 为每个学习实例添加详细注释
- 更新README中的快速开始指南
- 添加常见问题解答章节"

# 配置更新
git commit -m "chore: 更新依赖包版本

- 升级pandas到最新版本
- 修复安全漏洞
- 更新requirements.txt"
```

## 🔧 配置Git别名（可选）

在 `~/.gitconfig` 中添加：
```ini
[alias]
    co = checkout
    br = branch
    ci = commit
    st = status
    unstage = reset HEAD --
    last = log -1 HEAD
    visual = !gitk
    lg = log --oneline --graph --all
    amend = commit --amend --no-edit
```

## 📝 Commit前检查清单

- [ ] 代码已经测试通过
- [ ] 遵循项目代码规范
- [ ] 提交消息清晰明确
- [ ] 只包含相关的更改
- [ ] 没有包含敏感信息
- [ ] 文档已更新（如需要）

## 🌟 最佳实践

1. **原子性提交**: 每次提交只做一件事
2. **频繁提交**: 小步快跑，经常提交
3. **清晰描述**: 让别人（包括未来的自己）能理解
4. **使用现在时**: "添加功能" 而不是 "添加了功能"
5. **限制长度**: 首行不超过50字符，详细描述每行不超过72字符

---

遵循这些规范，您的Git历史将变得清晰易读，便于团队协作和项目维护！