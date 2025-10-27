# Tools (Dev Utilities)

本目录存放开发期诊断与调试脚本以及演示用例。

核心诊断脚本：
- `debug_qmt_api.py`：检查 easy_xt API 结构，枚举 trade/data/account 能力并做基础调用验证
- `debug_data_api.py`：直连 DataAPI 验证 connect/xtquant 可用性及行情、列表获取

演示脚本（tools/demos/）：
- `P1-006_config_demo.py`：配置系统演示
- `P1-009_monitor_demo.py`：监控告警演示
- `P1-010_validator_demo.py`：配置校验器演示
- `P1-011_scheduler_demo.py`：任务调度器功能演示（定时、周期、优先级、并发、重试、统计）
- `P2-011_performance_demo.py`：性能/压测演示
- `P2-012_error_handler_demo.py`：错误处理与恢复机制演示（分级分类、重试/降级/优雅退化、断路器）
- `P2-013_log_manager_demo.py`：日志管理演示（配置、检索/过滤、统计分析、导出）
- `quick_start_monitor.py`：监控告警系统快速启动（修复版），用于快速验证监控核心功能
- `find_current_holdings_api.py`：雪球接口探测脚本，枚举多端点并保存样本，结论用于确定“当前持仓”来源

使用方式（PowerShell）：
```powershell
# 诊断脚本
cd "c:\Users\Administrator\Desktop\miniqmt扩展\tools"
python .\debug_qmt_api.py
python .\debug_data_api.py

# 演示脚本
cd "c:\Users\Administrator\Desktop\miniqmt扩展\tools\demos"
python .\P1-006_config_demo.py
python .\P1-009_monitor_demo.py
python .\P1-010_validator_demo.py
python .\P1-011_scheduler_demo.py
python .\P2-011_performance_demo.py
python .\P2-012_error_handler_demo.py
python .\P2-013_log_manager_demo.py
python .\quick_start_monitor.py
python .\find_current_holdings_api.py
```

注意：
- 需预先安装你的“xtquant 特殊版本”，并按 README 配置（或设置环境变量 XTQUANT_PATH）
- 推荐通过 `pip install -e .\easy_xt` 进行可编辑安装后再运行脚本
- 演示脚本为开发/培训用途，不参与生产流程
