"""系统监控接口 — 实时告警 SSE + 即时检测"""

import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from loguru import logger
from app.services.monitor_service import check_system_now, get_alert_stream

router = APIRouter()


@router.get("/monitor/stream")
async def monitor_stream():
    """SSE 实时告警流 — 系统有异常时自动推送"""
    async def event_generator():
        try:
            async for alert in get_alert_stream():
                yield {"event": "message", "data": json.dumps(alert, ensure_ascii=False)}
        except Exception as e:
            logger.error(f"监控流异常: {e}")
            yield {"event": "message", "data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}
    return EventSourceResponse(event_generator())


@router.get("/monitor/now")
async def monitor_now():
    """即时获取当前系统状态"""
    try:
        result = check_system_now()
        return JSONResponse(status_code=200, content={
            "code": 200, "message": "success", "data": result
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "code": 500, "message": str(e), "data": None
        })
