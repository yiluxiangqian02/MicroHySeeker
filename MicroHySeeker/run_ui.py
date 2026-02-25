#!/usr/bin/env python
"""
运行 MicroHySeeker 界面应用
"""
import sys
import os
from pathlib import Path

# PyInstaller 打包检测
if getattr(sys, 'frozen', False):
    # 打包模式：exe 所在目录
    project_root = Path(sys.executable).parent
    # PyInstaller 解压的临时目录（含 _internal 数据）
    bundle_dir = Path(sys._MEIPASS)
    sys.path.insert(0, str(bundle_dir))
    # 设置工作目录为 exe 所在目录（确保配置文件可访问）
    os.chdir(str(project_root))
else:
    # 开发模式
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "src"))

# 设置环境变量
os.environ["QT_LOGGING_RULES"] = "qt.qpa.plugin=false"
# 确保 stdout/stderr 编码为 UTF-8（避免 GBK 编码错误）
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    from PySide6.QtWidgets import QApplication
    from src.ui.main_window import MainWindow
    from src.services.app_logger import init_app_logging, shutdown_logging
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保已安装所有依赖:")
    print("  方式1 (推荐): 双击 start.bat 启动")
    print("  方式2: .venv\\Scripts\\python.exe run_ui.py")
    print("  安装依赖: uv pip install -r requirements.txt --python .venv\\Scripts\\python.exe")
    sys.exit(1)


def main():
    # 初始化日志系统（应用级，按天轮换到 logs/ 目录，永久保留）
    init_app_logging(log_dir="./logs")

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()

    exit_code = app.exec()

    # 清理日志
    shutdown_logging()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
