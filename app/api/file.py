"""文件上传接口模块 - 支持 PDF/TXT/MD"""

from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from app.services.vector_index_service import vector_index_service
from app.services.vector_store_manager import vector_store_manager
from loguru import logger

router = APIRouter()
UPLOAD_DIR = Path("./uploads")
ALLOWED_EXTENSIONS = ["txt", "md", "pdf"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        safe_filename = _sanitize_filename(file.filename)
        file_extension = _get_file_extension(safe_filename)

        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式，仅支持: {', '.join(ALLOWED_EXTENSIONS)}")

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        file_path = UPLOAD_DIR / safe_filename

        if file_path.exists():
            file_path.unlink()

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"文件大小超过限制")

        file_path.write_bytes(content)
        logger.info(f"文件上传成功: {file_path}")

        try:
            vector_index_service.index_single_file(str(file_path))
            logger.info(f"向量索引创建成功: {file_path}")
        except Exception as e:
            logger.error(f"向量索引创建失败: {e}")

        return JSONResponse(status_code=200, content={
            "code": 200, "message": "success",
            "data": {"filename": safe_filename, "file_path": str(file_path), "size": len(content)}
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {e}")


@router.post("/index_directory")
async def index_directory(directory_path: str = None):
    try:
        result = vector_index_service.index_directory(directory_path)
        return JSONResponse(status_code=200, content={
            "code": 200,
            "message": "success" if result.success else "partial_success",
            "data": result.to_dict()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引目录失败: {e}")


@router.get("/index_status")
async def get_index_status():
    """获取向量数据库状态：已索引的文件、分片数、内容预览"""
    try:
        stats = vector_store_manager.get_index_stats()
        return JSONResponse(status_code=200, content={
            "code": 200, "message": "success", "data": stats
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取索引状态失败: {e}")


@router.delete("/index_file")
async def delete_index_file(file_name: str):
    """从向量库中删除指定文件的所有切片"""
    try:
        deleted = vector_store_manager.delete_by_file(file_name)
        if deleted > 0:
            return JSONResponse(status_code=200, content={
                "code": 200, "message": f"已删除 {deleted} 个切片",
                "data": {"file_name": file_name, "deleted": deleted}
            })
        else:
            return JSONResponse(status_code=404, content={
                "code": 404, "message": "未找到该文件的切片",
                "data": {"file_name": file_name, "deleted": 0}
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


def _get_file_extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[1].lower() if len(parts) == 2 else ""


def _sanitize_filename(filename: str) -> str:
    sanitized = filename.replace(" ", "_")
    for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        sanitized = sanitized.replace(char, "_")
    return sanitized
