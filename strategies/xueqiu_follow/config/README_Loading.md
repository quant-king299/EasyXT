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