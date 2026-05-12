"""文档相关数据模型"""

from typing import Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    content: str
    start_index: int
    end_index: int
    chunk_index: int
    title: Optional[str] = None
