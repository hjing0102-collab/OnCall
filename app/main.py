"""FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
from app.config import config
from loguru import logger
from app.api import chat, health, file, aiops, monitor
from app.core.milvus_client import faiss_manager
from app.services.monitor_service import start_monitor, stop_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"启动 {config.app_name} v{config.app_version}")
    logger.info(f"监听: http://{config.host}:{config.port}")

    logger.info("正在连接 FAISS...")
    faiss_manager.connect()
    logger.info("FAISS 连接成功")

    logger.info("正在启动系统监控...")
    await start_monitor(interval=10)
    logger.info("系统监控已启动 (间隔 10s, CPU>80% MEM>85% DISK>90%)")
    logger.info("=" * 60)

    yield

    logger.info("正在停止系统监控...")
    await stop_monitor()
    logger.info("正在关闭 FAISS...")
    faiss_manager.close()
    logger.info(f"{config.app_name} 关闭")


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="基于 LangChain 的智能OnCall运维系统（FAISS 嵌入式版本）",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(health.router, tags=["健康检查"])
app.include_router(chat.router, prefix="/api", tags=["对话"])
app.include_router(file.router, prefix="/api", tags=["文件管理"])
app.include_router(aiops.router, prefix="/api", tags=["AIOps智能运维"])
app.include_router(monitor.router, prefix="/api", tags=["系统监控"])

static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"Welcome to {config.app_name} API", "version": config.app_version, "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.host, port=config.port, reload=config.debug)
