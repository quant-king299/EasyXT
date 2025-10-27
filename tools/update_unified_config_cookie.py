# -*- coding: utf-8 -*-
import json
import os
import shutil

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'strategies', 'xueqiu_follow', 'config', 'unified_config.json'
)


def main():
    if not os.path.exists(CONFIG_PATH):
        print(f'未找到配置文件: {CONFIG_PATH}')
        return 2

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 备份
    backup_path = CONFIG_PATH + '.bak'
    shutil.copyfile(CONFIG_PATH, backup_path)

    # 仅清空 xueqiu.cookie
    xq = data.get('xueqiu')
    if isinstance(xq, dict):
        before = xq.get('cookie')
        xq['cookie'] = ''
        after = xq.get('cookie')
    else:
        print('未找到 xueqiu 节点，跳过修改')
        return 3

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print('已清空 xueqiu.cookie')
    print(f'备份文件: {backup_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
