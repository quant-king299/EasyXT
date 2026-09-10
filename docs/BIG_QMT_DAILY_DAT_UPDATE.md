# 大QMT 每日日线 DAT 更新

EasyXT 在“大QMT模式”下读取的是大QMT本机 `datadir` 中已有的日线 DAT；
“一键补全数据”只负责 DAT 导入 DuckDB，不会向券商服务器下载缺失数据。

## 安装一次

1. 从仓库打开 `tools/big_qmt_daily_dat_update.py`，把全部内容复制到大QMT的“量化 → Python编辑器”新建策略中。
2. 将策略设置为收盘后运行一次，建议在 15:20 以后；它会下载最近 21 个自然日的沪深A股日线。
3. 先手工运行一次。日志应显示“仅下载大QMT本地DAT；不下单、不写DuckDB”。
4. 回到 EasyXT，点击“数据管理 → 一键补全数据”，将已更新 DAT 导入 DuckDB。

## 精确补数闭环

若导入后仍有 DAT 未补齐，EasyXT 会自动在大QMT `python` 目录写入
`easyxt_qmt_dat_update_manifest.json`。清单为每只证券记录了从 DuckDB 最新日期
的下一天到目标日期的准确范围，并按 A 股、ETF/基金、北交所分类。下次运行本
脚本时只会读取其中的沪深A股任务；ETF、北交所和其他证券保留在清单中作为备用
数据源待办，不能被误当成大QMT沪深A股下载任务。之后再运行 EasyXT“一键补全数据”验证。

若脚本被复制到大QMT编辑器而非以 `.py` 文件运行，请把 `MANIFEST_PATH` 设置为
GUI 日志显示的清单绝对路径。

## 市场范围

默认只更新 `沪深A股`，因为不同券商大QMT的 ETF、北交所板块名称和数据权限并不一致。

- ETF：确认大QMT板块名称后，把它加入 `OPTIONAL_SECTOR_NAMES`；若大QMT没有对应 DAT，改用 Tushare 的基金日线数据。
- 北交所：若大QMT不生成 `.BJ` DAT，不能通过本脚本补齐，应配置 Tushare 等备用源。
- 单个证券：可把代码加入 `EXTRA_CODES`。

脚本只调用大QMT内置的 `download_history_data`，没有账户、委托、成交或 DuckDB 写入逻辑。不要在普通 Windows PowerShell 或 miniQMT环境运行它。

下载任务在大QMT的 `after_init` 生命周期回调中执行，而不是 `init`。这是为了让
行情服务先完成策略初始化；脚本默认再等待 3 秒后才开始提交下载请求。

`download_history_data` 调用不抛异常只表示大QMT接受了下载请求，并不能证明每只
DAT 已经写到 EasyXT 读取的目录。若导入后仍有缺口，运行
`python tools/diagnose_qmt_dat_coverage.py`；它会只读比较大QMT与miniQMT目录中
样本 DAT 的最后日期、修改时间与文件大小，用于判断下载未落盘还是路径不一致。

## 首次验收

执行后，在大QMT `datadir` 中抽查原先缺失的 A 股 DAT 最新日期；确认已到最近交易日后，再运行 EasyXT 一键补全。对于 DAT 仍无更新的证券，查看大QMT脚本输出的失败代码，并按证券类型选择大QMT数据管理或备用源。
