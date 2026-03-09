"""
FastAPI 应用定义 + uvicorn 启动入口。

使用方式（在 Qt 主线程中准备好 bridge 后，在 daemon 线程中启动）：

    from src.api.bridge import APIBridge
    from src.api.server import start_api_server

    bridge = APIBridge(self.runner, self.config)   # 主线程创建
    api_thread = threading.Thread(
        target=start_api_server,
        args=(bridge,),
        kwargs={"port": 8100},
        daemon=True,
    )
    api_thread.start()
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from .bridge import APIBridge

logger = logging.getLogger("microhyseeker.api.server")

# 全局 bridge 引用（由 start_api_server 注入）
_bridge: "APIBridge | None" = None


def get_bridge() -> "APIBridge":
    """FastAPI 路由依赖注入用。"""
    if _bridge is None:
        raise RuntimeError("APIBridge not initialised — call start_api_server first")
    return _bridge


def create_app(bridge: "APIBridge") -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    from .routes import experiment as exp_router
    from .routes import system as sys_router
    from .routes import data as data_router

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("MicroHySeeker API server started on port %s", app.state.port)
        yield
        logger.info("MicroHySeeker API server shutting down")

    app = FastAPI(
        title="MicroHySeeker Control API",
        description="AutoHySeeker → MicroHySeeker RESTful 控制接口",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS：允许 AutoHySeeker（本地同机）调用
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # 将 bridge 注入 app state，供路由模块通过依赖获取
    app.state.bridge = bridge
    app.state.port = 0  # 由 start_api_server 覆写

    # 路由注册
    app.include_router(exp_router.router,  prefix="/api/experiment", tags=["experiment"])
    app.include_router(sys_router.router,  prefix="/api/system",     tags=["system"])
    app.include_router(data_router.router, prefix="/api/data",       tags=["data"])

    return app


def start_api_server(bridge: "APIBridge", port: int = 8100) -> None:
    """在调用线程中启动 uvicorn。应在 daemon 线程中调用，永不返回。

    Args:
        bridge: 已在 Qt 主线程中初始化的 APIBridge 实例。
        port:   监听端口，默认 8100。
    """
    global _bridge
    _bridge = bridge

    app = create_app(bridge)
    app.state.port = port

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    logger.info("Starting uvicorn on 0.0.0.0:%d", port)
    server.run()
