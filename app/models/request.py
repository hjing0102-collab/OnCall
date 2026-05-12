"""请求数据模型"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求"""
    id: str = Field(..., description="会话 ID", alias="Id")
    question: str = Field(..., description="用户问题", alias="Question")

    class Config:
        populate_by_name = True


class ClearRequest(BaseModel):
    """清空会话请求"""
    session_id: str = Field(..., description="会话 ID")
