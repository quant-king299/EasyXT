# -*- coding: utf-8 -*-
"""
用户策略自动发现和加载器

将 .py 文件放入 user_strategies/ 目录即可自动注册到回测平台。
每个文件需定义一个 `REGISTRY` 字典或 `STRATEGIES` 列表。

支持格式：

  # 格式1: REGISTRY 字典（推荐）
  REGISTRY = {
      'my_strategy': {
          'name': '我的策略',
          'desc': '策略描述',
          'func': my_func,          # 必需: 策略函数
          'category': 'cb',         # 可选: cb/etf/stock (默认cb)
          'params': {'top_n': 20},  # 可选: 默认参数
      }
  }

  # 格式2: 纯函数（函数名作为策略名）
  def my_strategy(df, **params):
      return df.nsmallest(params.get('top_n', 20), 'close')['ts_code'].tolist()

策略函数签名: func(df: pd.DataFrame, **params) -> List[str]
  - df: 当日行情 DataFrame
  - params: 参数字典
  - 返回: 选中的股票/ETF/可转债代码列表
"""

import importlib.util
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Callable, Optional


def _get_user_strategies_dir() -> Path:
    """获取用户策略目录"""
    return Path(__file__).resolve().parent


def discover_strategies() -> Dict[str, dict]:
    """
    扫描 user_strategies/ 目录，自动发现并加载所有策略。

    Returns:
        合并后的策略注册表 {key: {name, desc, func, category, params}}
    """
    registry = {}
    base_dir = _get_user_strategies_dir()

    if not base_dir.exists():
        return registry

    for py_file in sorted(base_dir.glob("*.py")):
        name = py_file.stem
        if name.startswith('_') or name == 'strategy_loader':
            continue

        try:
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(
                f"user_strategies.{name}", str(py_file)
            )
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 格式1: 查找 REGISTRY 字典（优先）
            registered_funcs = set()
            if hasattr(module, 'REGISTRY'):
                reg = getattr(module, 'REGISTRY')
                if isinstance(reg, dict):
                    for key, info in reg.items():
                        if 'func' in info and callable(info['func']):
                            registry[key] = {
                                'name': info.get('name', key),
                                'desc': info.get('desc', ''),
                                'func': info['func'],
                                'category': info.get('category', 'cb'),
                                'params': info.get('params', {'top_n': 20}),
                                'source': str(py_file),
                            }
                            registered_funcs.add(info['func'])
                    print(f"[策略加载] {py_file.name}: {len(reg)} 个策略 (REGISTRY)")

            # 格式2: 自动发现未注册的函数（排除已在 REGISTRY 中的）
            for attr_name in dir(module):
                if attr_name.startswith('_') or attr_name in registry:
                    continue
                attr = getattr(module, attr_name)
                if callable(attr) and not inspect.isclass(attr) and attr not in registered_funcs:
                    sig = inspect.signature(attr)
                    params = list(sig.parameters.keys())
                    if len(params) >= 1:
                        registry[attr_name] = {
                            'name': attr_name.replace('_', ' ').title(),
                            'desc': f'用户策略: {attr_name} (来自 {py_file.name})',
                            'func': attr,
                            'category': 'cb',
                            'params': {'top_n': 20},
                            'source': str(py_file),
                        }
                        print(f"[策略加载] {py_file.name}: 函数 {attr_name}")

        except Exception as e:
            print(f"[策略加载] {py_file.name}: 加载失败 - {e}")

    return registry


def get_merged_registry(*builtin_registries: Dict[str, dict]) -> Dict[str, dict]:
    """
    合并内置策略和用户策略。

    Args:
        builtin_registries: 内置策略注册表（优先，不可被覆盖）

    Returns:
        合并后的注册表
    """
    merged = {}
    # 先加载内置策略（补齐 category 字段）
    for reg in builtin_registries:
        if reg:
            for key, info in reg.items():
                if 'category' not in info:
                    info['category'] = 'cb'  # 内置策略默认 cb 类别
                merged[key] = info
    # 再加载用户策略（不会覆盖同名内置策略）
    user_reg = discover_strategies()
    for key, info in user_reg.items():
        if key not in merged:
            merged[key] = info
        else:
            print(f"[策略加载] 跳过同名策略: {key} (内置策略优先)")
    return merged


def list_strategies_by_category(registry: Dict[str, dict],
                                category: Optional[str] = None) -> Dict[str, dict]:
    """按类别筛选策略"""
    if category is None:
        return registry
    return {k: v for k, v in registry.items()
            if v.get('category', 'cb') == category}


# 初始化时自动加载用户策略（可导入使用）
try:
    USER_STRATEGIES = discover_strategies()
except Exception:
    USER_STRATEGIES = {}
