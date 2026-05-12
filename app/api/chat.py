"""对话接口"""

import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from app.models.request import ChatRequest, ClearRequest
from app.models.response import SessionInfoResponse, ApiResponse
from app.services.rag_agent_service import rag_agent_service
from loguru import logger

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        logger.info(f"[会话 {request.id}] 收到: {request.question}")
        answer = await rag_agent_service.query(request.question, session_id=request.id)
        return {"code": 200, "message": "success", "data": {"success": True, "answer": answer, "errorMessage": None}}
    except Exception as e:
        logger.error(f"对话接口错误: {e}")
        return {"code": 500, "message": "error", "data": {"success": False, "answer": None, "errorMessage": str(e)}}


@router.post("/chat_stream")
async def chat_stream(request: ChatRequest):
    logger.info(f"[会话 {request.id}] 收到流式对话: {request.question}")

    async def event_generator():
        try:
            async for chunk in rag_agent_service.query_stream(request.question, session_id=request.id):
                chunk_type = chunk.get("type", "unknown")
                if chunk_type == "content":
                    yield {"event": "message", "data": json.dumps({"type": "content", "data": chunk.get("data")}, ensure_ascii=False)}
                elif chunk_type == "complete":
                    yield {"event": "message", "data": json.dumps({"type": "done", "data": None}, ensure_ascii=False)}
                elif chunk_type == "error":
                    yield {"event": "message", "data": json.dumps({"type": "error", "data": str(chunk.get("data"))}, ensure_ascii=False)}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


@router.post("/chat/clear", response_model=ApiResponse)
async def clear_session(request: ClearRequest):
    try:
        success = rag_agent_service.clear_session(request.session_id)
        return ApiResponse(status="success" if success else "error", message="会话已清空" if success else "清空失败", data=None)
    except Exception as e:
        return ApiResponse(status="error", message=str(e), data=None)


@router.get("/chat/session/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    try:
        history = rag_agent_service.get_session_history(session_id)
        return SessionInfoResponse(session_id=session_id, message_count=len(history), history=history)
    except Exception as e:
        return SessionInfoResponse(session_id=session_id, message_count=0, history=[])
