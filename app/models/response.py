"""响应数据模型"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class SessionInfoResponse(BaseModel):
    session_id: str
    message_count: int
    history: List[Dict[str, str]]


class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None
