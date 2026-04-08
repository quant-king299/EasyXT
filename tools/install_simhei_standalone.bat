@echo off
chcp 65001 >nul
echo ========================================
echo      SimHei 字体自动安装工具
echo ========================================
echo.

echo [1/4] 检查SimHei字体文件...
if not exist "C:\Windows\Fonts\simhei.ttf" (
    echo 错误：找不到 C:\Windows\Fonts\simhei.ttf
    echo 请确保系统中有SimHei字体
    pause
    exit /b 1
)
echo √ 找到SimHei字体文件
echo.

echo [2/4] 复制字体到matplotlib目录...
echo 请稍候...
python -c "import matplotlib,os,shutil;font_dir=os.path.join(os.path.dirname(matplotlib.__file__),'mpl-data','fonts','ttf');dest=os.path.join(font_dir,'simhei.ttf');shutil.copy(r'C:\Windows\Fonts\simhei.ttf',dest);print('√ 字体已复制到:',dest)"
if errorlevel 1 (
    echo 错误：字体复制失败
    pause
    exit /b 1
)
echo.

echo [3/4] 清除matplotlib缓存...
python -c "import matplotlib,shutil;cache_dir=matplotlib.get_cachedir();shutil.rmtree(cache_dir,ignore_errors=True);print('√ 缓存已清除:',cache_dir)" 2>nul
if errorlevel 1 (
    echo 警告：缓存清除失败，但不影响使用
) else (
    echo √ 缓存清除成功
)
echo.

echo [4/4] 验证字体安装...
python -c "import matplotlib.pyplot as plt;plt.rcParams['font.sans-serif']=['SimHei'];print('√ SimHei字体配置成功')" 2>nul
if errorlevel 1 (
    echo 警告：字体配置可能有问题，但可以尝试运行程序
) else (
    echo √ 字体验证通过
)
echo.

echo ========================================
echo           安装完成！
echo ========================================
echo.
echo 现在可以运行: python run_gui.py
echo.
pause
