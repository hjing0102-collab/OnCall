"""AIOps 请求和响应模型"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AIOpsRequest(BaseModel):
    session_id: Optional[str] = Field(default="default")


class DiagnosisResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Dict[str, Any]
