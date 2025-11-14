import pandas as pd
from tdxtrader.logger import logger
from tdxtrader.anis import RED, GREEN, YELLOW, BLUE, RESET

# 定义列名
COLUMNS = ['code', 'name', 'date', 'time', 'price', 'rate', 'value', 'sign']

# 需要修复的股票名称列表
STOCK_LIST = ['新 和 成', '五 粮 液', '农 产 品', '南 玻Ａ', '万 科Ａ', '新 华 都', '奥 特 迅', '三 力 士', '诺 普 信', '达 意 隆', '海 利 得', '全 聚 德', '怡 亚 通', '粤 传 媒', '红 宝 丽', '远 望 谷', '报 喜 鸟', '安 纳 达', '生 意 宝', '金 螳 螂', '兔 宝 宝', '南 京 港', '苏 泊 尔', '七 匹 狼', '新 大 陆', '中 关 村', '新 希 望', '张 裕Ａ', '罗 牛 山', '鲁 泰Ａ', '英 力 特', '柳 工', '渝 开 发', '金 融 街', '盐 田 港', '深 赛 格', '特 力Ａ']

def fix_stock_name(line):
    """
    修复股票名称中的空格。
    """
    for stock in STOCK_LIST:
        fixed_stock = stock.replace(' ', '')  # 去掉空格
        line = line.replace(stock, fixed_stock)  # 替换原始行中的股票名称
    return line

def process_line(line):
    """
    处理每一行数据，确保列数为 8，并将 'price' 转换为 float 并保留两位小数。
    """
    line = line.strip()  # 去掉首尾空白字符
    line = fix_stock_name(line)  # 修复股票名称中的空格
    fields = line.split()  # 按空白字符分割

    # 检查列数是否为 8
    if len(fields) != 8:
        logger.error(f"【错误行】 {line}")
        return None  # 跳过该行

    # 将 'price' 转换为 float 并保留两位小数
    try:
        fields[4] = round(float(fields[4]), 2)  # price
    except ValueError as e:
        logger.error(f"【类型转换错误】 {line}: {e}")
        return None  # 跳过该行

    return fields

def read_file(file_path):
    """
    读取文件并处理错误，支持多种编码格式。
    """
    encodings = ['gbk', 'gb2312', 'utf-8']
    
    for encoding in encodings:
        try:
            # 检查文件是否为空
            with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
                first_line = file.readline()
                if not first_line:  # 文件为空
                    return pd.DataFrame(columns=COLUMNS)

            # 逐行读取文件并处理
            rows = []
            with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
                for line in file:
                    processed_line = process_line(line)  # 处理每一行
                    if processed_line:  # 如果处理成功
                        rows.append(processed_line)

            # 构建 DataFrame
            df = pd.DataFrame(rows, columns=COLUMNS)
            # 只有在成功读取且非空时才记录日志，减少冗余信息
            if not df.empty:
                logger.info(f"读取到 {len(df)} 条新的预警信号")
            return df

        except UnicodeError:
            continue
        except Exception as e:
            logger.error(f"读取文件时发生错误: {e}")
            continue
    
    logger.error("所有编码尝试均失败")
    return None

def clear_file_content(file_path):
    try:
        with open(file_path, 'w', encoding='gbk') as file:
            file.truncate(0)
            # 写入表头
            # header = ' '.join(COLUMNS) + '\n'
            # file.write(header)
        logger.info(f"【重置文件】内容已清空")
    except Exception as e:
        logger.error(f"清空文件内容时发生错误: {e}")