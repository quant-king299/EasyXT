# Git 常用命令速查表

## 🚀 日常开发流程

### 1. 查看状态和历史
```bash
git status                    # 查看工作区状态
git log --oneline            # 简洁查看提交历史
git log --graph --oneline    # 图形化查看分支历史
git diff                     # 查看工作区变更
git diff --staged            # 查看暂存区变更
```

### 2. 添加和提交
```bash
git add .                    # 添加所有文件
git add -p                   # 交互式添加（选择代码块）
git commit -m "消息"         # 提交并添加消息
git commit --amend           # 修改最后一次提交
```

### 3. 分支操作
```bash
git branch                   # 查看本地分支
git branch -a               # 查看所有分支
git checkout -b feature/新功能  # 创建并切换到新分支
git merge feature/新功能      # 合并分支
git branch -d feature/新功能  # 删除分支
```

### 4. 远程操作
```bash
git remote -v               # 查看远程仓库
git fetch                   # 获取远程更新
git pull                    # 拉取并合并
git push origin main        # 推送到远程
```

## 📋 针对您项目的实际示例

### 功能开发示例
```bash
# 1. 创建功能分支
git checkout -b feature/add-macd-strategy

# 2. 开发过程中的提交
git add easy_xt/indicators.py
git commit -m "feat(indicators): 添加MACD技术指标计算

- 实现MACD指标的DIF、DEA、MACD计算
- 支持自定义快慢均线周期参数
- 添加单元测试验证计算准确性"

# 3. 添加文档
git add 学习实例/11_MACD策略示例.py
git commit -m "docs: 添加MACD策略学习示例

- 演示MACD金叉死叉交易信号
- 包含完整的回测代码
- 添加详细的策略说明注释"

# 4. 合并到主分支
git checkout main
git merge feature/add-macd-strategy
git push origin main
```

### Bug修复示例
```bash
# 1. 创建修复分支
git checkout -b hotfix/fix-price-precision

# 2. 修复提交
git add easy_xt/trade_api.py
git commit -m "fix(trade): 修复股价精度处理问题

修复当股价包含超过2位小数时，交易下单失败的问题。
现在正确处理最多4位小数的价格精度。

- 更新价格格式化函数
- 添加价格精度验证
- 修复相关单元测试

Fixes #123"

# 3. 推送修复
git push origin hotfix/fix-price-precision
```

## 🛠️ 高级技巧

### 1. 交互式rebase（整理提交历史）
```bash
git rebase -i HEAD~3         # 整理最近3次提交
# 可以选择：pick, reword, edit, squash, drop
```

### 2. 暂存工作进度
```bash
git stash                    # 暂存当前工作
git stash pop               # 恢复暂存的工作
git stash list              # 查看暂存列表
```

### 3. 撤销操作
```bash
git reset --soft HEAD~1     # 撤销提交，保留更改
git reset --hard HEAD~1     # 撤销提交，丢弃更改
git checkout -- 文件名      # 撤销文件的工作区更改
```

### 4. 查找和定位
```bash
git blame 文件名            # 查看文件每行的修改者
git grep "搜索内容"         # 在代码中搜索
git log --grep="关键词"     # 在提交消息中搜索
```

## 🎯 项目维护最佳实践

### 1. 发布版本
```bash
# 创建标签
git tag -a v1.0.0 -m "发布版本1.0.0

主要功能：
- 完整的EasyXT API封装
- 10个学习实例
- GUI交易界面
- 完善的文档"

# 推送标签
git push origin v1.0.0
```

### 2. 代码审查流程
```bash
# 创建Pull Request分支
git checkout -b feature/new-feature
# ... 开发和提交 ...
git push origin feature/new-feature
# 在GitHub上创建Pull Request
```

### 3. 紧急修复流程
```bash
# 从主分支创建热修复
git checkout main
git checkout -b hotfix/urgent-fix
# ... 修复和测试 ...
git checkout main
git merge hotfix/urgent-fix
git tag -a v1.0.1 -m "紧急修复版本"
git push origin main --tags
```

---

记住：好的Git习惯是团队协作的基础！