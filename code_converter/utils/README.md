# QMT API文档爬取工具

这个工具可以自动爬取QMT的API文档并生成Word和HTML格式的文件。

## 功能特点

- 自动爬取QMT官方API文档
- 生成Word格式文档
- 生成HTML格式文档（PDF生成功能需要额外安装wkhtmltopdf）

## 使用方法

```bash
cd code_converter
python utils/qmt_api_scraper.py
```

## 生成的文件

生成的文档将保存在 `code_converter/api_docs/` 目录下：
- `QMT_API文档.docx` - Word格式
- `QMT_API文档.html` - HTML格式

## 依赖安装

如果需要生成PDF文档，需要安装以下依赖：

```bash
pip install pdfkit
```

并安装wkhtmltopdf工具：
- Windows: 下载并安装 [wkhtmltopdf for Windows](https://wkhtmltopdf.org/downloads.html)
- macOS: `brew install wkhtmltopdf`
- Ubuntu/Debian: `sudo apt-get install wkhtmltopdf`

## 注意事项

1. 爬取过程需要网络连接
2. 为了避免对服务器造成压力，程序会在每次请求之间添加延时
3. 生成的文件较大，请确保有足够的磁盘空间