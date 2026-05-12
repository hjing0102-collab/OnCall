"""健康检查接口"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.config import config
from app.core.milvus_client import faiss_manager
from app.services.vector_store_manager import vector_store_manager

router = APIRouter()


@router.get("/health")
async def health_check():
    health_data = {"service": config.app_name, "version": config.app_version, "status": "healthy"}
    try:
        faiss_ready = faiss_manager.health_check()
        vs_ready = vector_store_manager.is_ready()
        health_data["vector_store"] = {
            "status": "connected" if (faiss_ready or vs_ready) else "disconnected",
            "message": "FAISS 连接正常" if (faiss_ready or vs_ready) else "FAISS 未就绪"
        }
    except Exception as e:
        health_data["vector_store"] = {"status": "error", "message": str(e)}

    overall_status = "healthy" if health_data.get("vector_store", {}).get("status") == "connected" else "unhealthy"
    health_data["status"] = overall_status
    return JSONResponse(
        status_code=200 if overall_status == "healthy" else 503,
        content={"code": 200, "message": "服务运行正常", "data": health_data}
    )
