"""
验证数据存储配置
"""
import sys
from pathlib import Path

# 添加src目录到路径
project_root = Path(__file__).parents[1]
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))

from data_manager import LocalDataManager


def verify_config():
    """验证配置是否正确"""
    print("="*70)
    print("数据存储配置验证")
    print("="*70)

    # 创建管理器
    manager = LocalDataManager()

    # 显示配置信息
    print(f"\n[DIR] 数据根目录: {manager.root_dir}")
    print(f"   绝对路径: {manager.root_dir.resolve()}")
    print(f"   是否存在: {'[OK] 是' if manager.root_dir.exists() else '[NO] 否'}")

    print(f"\n[STRUCT] 子目录结构:")
    print(f"   原始数据: {manager.raw_data_dir}")
    print(f"   元数据库: {manager.metadata_path}")

    # 显示存储空间
    import shutil
    total, used, free = shutil.disk_usage(manager.root_dir)
    print(f"\n[DISK] 磁盘空间:")
    print(f"   总空间: {total / (1024**3):.2f} GB")
    print(f"   已用: {used / (1024**3):.2f} GB")
    print(f"   可用: {free / (1024**3):.2f} GB")

    if free < 5 * 1024**3:  # 小于5GB
        print(f"   [WARN] 警告：可用空间不足5GB")
    else:
        print(f"   [OK] 空间充足")

    # 测试创建目录
    print(f"\n[TEST] 测试目录创建...")
    try:
        manager.root_dir.mkdir(parents=True, exist_ok=True)
        print(f"   [OK] 成功创建/访问目录")
    except Exception as e:
        print(f"   [ERROR] 创建目录失败: {e}")

    print(f"\n[SUCCESS] 配置验证完成！")
    print(f"   数据将保存到: {manager.root_dir.resolve()}")

    manager.close()


if __name__ == '__main__':
    verify_config()
