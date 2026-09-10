# 大QMT 每日日线 DAT 更新

EasyXT 在“大QMT模式”下读取的是大QMT本机 `datadir` 中已有的日线 DAT；
“一键补全数据”只负责 DAT 导入 DuckDB，不会向券商服务器下载缺失数据。

## 安装一次

1. 从仓库打开 `tools/big_qmt_daily_dat_update.py`，把全部内容复制到大QMT的“量化 → Python编辑器”新建策略中。
2. 将策略设置为收盘后运行一次，建议在 15:20 以后；它会下载最近 21 个自然日的沪深A股日线。
3. 先手工运行一次。日志应显示“仅下载大QMT本地DAT；不下单、不写DuckDB”。
4. 回到 EasyXT，点击“数据管理 → 一键补全数据”，将已更新 DAT 导入 DuckDB。

## 市场范围

默认只更新 `沪深A股`，因为不同券商大QMT的 ETF、北交所板块名称和数据权限并不一致。

- ETF：确认大QMT板块名称后，把它加入 `OPTIONAL_SECTOR_NAMES`；若大QMT没有对应 DAT，改用 Tushare 的基金日线数据。
- 北交所：若大QMT不生成 `.BJ` DAT，不能通过本脚本补齐，应配置 Tushare 等备用源。
- 单个证券：可把代码加入 `EXTRA_CODES`。

脚本只调用大QMT内置的 `download_history_data`，没有账户、委托、成交或 DuckDB 写入逻辑。不要在普通 Windows PowerShell 或 miniQMT环境运行它。

## 首次验收

执行后，在大QMT `datadir` 中抽查原先缺失的 A 股 DAT 最新日期；确认已到最近交易日后，再运行 EasyXT 一键补全。对于 DAT 仍无更新的证券，查看大QMT脚本输出的失败代码，并按证券类型选择大QMT数据管理或备用源。
