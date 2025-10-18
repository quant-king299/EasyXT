# 配置加载说明（混合层级：框架默认 + 子系统覆盖 + 策略专属）

加载顺序（优先级从高到低）
1. 策略层：strategies/xueqiu_follow/config/unified_config.json
   - 策略专属参数与最终运行时覆盖项都写在此文件
   - 可选叠加：xueqiu_config.json（雪球专用补充），若存在则深度合并到 unified_config.json
2. 子系统层：easy_xt/realtime_data/config（作为默认）
   - realtime_config.json、settings.py、server_config.py 提供实时数据/服务默认配置
3. 框架层：core/config（框架默认）
   - config_template.py 用于生成初始模板

合并与覆盖规则
- 深度合并（dict merge）：当同名键为字典时递归合并；非字典则以高优先级值覆盖低优先级。
- 缺省补齐：低优先级文件仅在高优先级缺失对应键时提供默认值，不覆盖已有值。
- 私密配置：本地私密项放在 local/*.json 或 *.secrets.json（已加入 .gitignore）。

已合并/已清理的历史文件
- strategies/xueqiu_follow/config/realtime_config.json → 内容为空，无需合并
- strategies/xueqiu_follow/config/default.json → 仅含入口说明，已并入统一配置说明
- strategies/xueqiu_follow/config/jq2qmt_config.json → 非本策略直系配置，已移除版本追踪；统一在 unified_config.json 的 integrations.jq2qmt.enabled=false 体现

运行建议
- 修改策略运行参数时，统一在 unified_config.json 的 settings、portfolios、xueqiu 等节点进行。
- 若需要对实时数据子系统进行变更，请在 easy_xt/realtime_data/config\* 中调整，策略层不重复维护。

---

覆盖示例：从根 config 回退到策略 config

背景
- 根目录 config/unified_config.json 提供通用默认值。
- 策略目录 strategies/xueqiu_follow/config/unified_config.json 提供策略专属覆盖项。
- 实际加载顺序：策略 > 子系统 > 框架（根）。

示例
- 根 config（默认）：config/unified_config.json
  {
    "settings": {
      "account": { "qmt_path": "C:/QMT/", "account_id": "" },
      "risk": { "max_position_ratio": 0.15 }
    }
  }

- 策略 config（覆盖）：strategies/xueqiu_follow/config/unified_config.json
  {
    "settings": {
      "account": { "qmt_path": "D:\\\\国金QMT交易端模拟\\\\userdata_mini", "account_id": "39020958" },
      "risk": { "max_position_ratio": 0.10 }
    }
  }

加载结果
- account.qmt_path → 使用策略值 D:\\国金QMT交易端模拟\\userdata_mini
- account.account_id → 使用策略值 39020958
- risk.max_position_ratio → 使用策略值 0.10
- 若策略缺失某键，则回退到根 config 或子系统默认。

操作步骤（如何验证覆盖）
1) 在根 config 设置一个默认值（例如 settings.logging.level = "INFO"）。
2) 在策略 config 将同键设置为 "DEBUG"。
3) 运行程序，检查日志级别；应为策略值 "DEBUG"。
4) 删除策略该键后，重新运行，应自动回退到根默认 "INFO"。

注意
- 敏感字段（cookie/password/token）请置空或存放到 local/*.json（被忽略）。
- 若需启用 jq2qmt，请在 integrations.jq2qmt.enabled 设置为 true 并在对应模块配置。