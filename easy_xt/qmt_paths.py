"""
QMT路径配置常量
统一管理QMT可能的安装路径列表
"""

# QMT可能的安装路径列表 (模拟盘优先)
QMT_POSSIBLE_PATHS = [
    "D:/国金QMT交易端模拟",
    "C:/国金QMT交易端模拟",
    "D:/QMT",
    "C:/QMT",
    "D:/Program Files/QMT",
    "C:/Program Files/QMT",
    "D:/Program Files (x86)/QMT",
    "C:/Program Files (x86)/QMT",
]

# QMT用户数据子目录
QMT_USERDATA_SUBPATH = "userdata_mini"

# 用于识别模拟盘路径的关键词
QMT_SIMULATED_KEYWORDS = ["模拟", "mini"]
