"""AIOps 智能运维接口"""

import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from loguru import logger
from app.models.aiops import AIOpsRequest
from app.services.aiops_service import aiops_service

router = APIRouter()


@router.post("/aiops")
async def diagnose_stream(request: AIOpsRequest):
    session_id = request.session_id or "default"
    logger.info(f"[会话 {session_id}] 收到 AIOps 诊断请求")

    async def event_generator():
        try:
            async for event in aiops_service.diagnose(session_id=session_id):
                yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}
                if event.get("type") in ["complete", "error"]:
                    break
        except Exception as e:
            logger.error(f"AIOps 异常: {e}")
            yield {"event": "message", "data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
