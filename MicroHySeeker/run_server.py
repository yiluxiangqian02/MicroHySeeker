#!/usr/bin/env python
"""
MicroHySeeker 无头服务模式（Headless Server）

不启动 GUI 窗口，仅启动 Qt 事件循环 + FastAPI 服务。
供 AutoHySeeker 远程调用时使用，适合后台运行。

用法:
    .venv\\Scripts\\python.exe run_server.py
    .venv\\Scripts\\python.exe run_server.py --port 8100
"""
import sys
import os
import signal
import threading
from pathlib import Path

# 开发模式路径设置
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 确保 stdout/stderr 编码为 UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    from PySide6.QtCore import QCoreApplication, QTimer
    from src.models import SystemConfig
    from src.engine.runner import ExperimentRunner
    from src.api.bridge import APIBridge
    from src.api.server import start_api_server
    from src.services.app_logger import init_app_logging, shutdown_logging
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保已安装所有依赖:")
    print("  .venv\\Scripts\\python.exe run_server.py")
    sys.exit(1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MicroHySeeker Headless Server")
    parser.add_argument("--port", type=int, default=8100, help="API 监听端口 (默认 8100)")
    args = parser.parse_args()

    # 初始化日志（写入 logs/YYYY-MM-DD/app_HH-MM-SS.log）
    init_app_logging(log_dir="./logs")
    from src.services.app_logger import get_app_logger
    logger = get_app_logger("SERVER")

    # Qt 无头事件循环
    app = QCoreApplication(sys.argv)

    # 加载系统配置
    config_file = Path("./config/system.json")
    config = SystemConfig.load_from_file(str(config_file))
    config.initialize_default_pumps()
    logger.info("配置加载完成: mock_mode=%s, auto_connect=%s", config.mock_mode, config.auto_connect)

    # 创建实验引擎（会触发 RS485 auto-connect）
    runner = ExperimentRunner(config=config)
    logger.info("ExperimentRunner 已创建")

    # 创建 API 桥接
    bridge = APIBridge(runner, config)

    # 在 daemon 线程中启动 uvicorn
    api_thread = threading.Thread(
        target=start_api_server,
        args=(bridge,),
        kwargs={"port": args.port},
        daemon=True,
        name="MicroHySeeker-API",
    )
    api_thread.start()
    logger.info("API 服务已启动: http://0.0.0.0:%d", args.port)
    print(f"✅ MicroHySeeker 无头服务已启动: http://0.0.0.0:{args.port}")
    print(f"   日志保存位置: logs/ 目录")
    print(f"   按 Ctrl+C 退出")

    # 优雅退出：捕获 SIGINT/SIGTERM
    def _shutdown():
        logger.info("正在关闭无头服务...")
        try:
            from src.services.rs485_wrapper import get_rs485_instance
            rs485 = get_rs485_instance()
            rs485.stop_monitoring()
            if rs485.is_connected():
                rs485.close_port()
                logger.info("RS485 连接已断开")
        except Exception as e:
            logger.warning("关闭 RS485 时出错: %s", e)
        shutdown_logging()
        app.quit()

    # 用 QTimer 把信号处理转到 Qt 主线程
    def _signal_handler(signum, frame):
        QTimer.singleShot(0, _shutdown)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # 启动 Qt 事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
