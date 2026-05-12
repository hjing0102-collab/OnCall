"""向量嵌入服务 - DashScope Text Embedding (OpenAI 兼容模式)"""

from typing import List
from langchain_core.embeddings import Embeddings
from openai import OpenAI
from loguru import logger
from app.config import config
from app.utils.http_client import get_http_client


class DashScopeEmbeddings(Embeddings):
    """阿里云 DashScope Text Embedding"""

    def __init__(self, api_key: str = "", model: str = "text-embedding-v4", dimensions: int = 1024):
        api_key = api_key or config.dashscope_api_key
        if not api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            http_client=get_http_client(),
        )
        self.model = model
        self.dimensions = dimensions
        logger.info(f"Embeddings 初始化完成 - 模型: {model}, 维度: {dimensions}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model, input=texts, dimensions=self.dimensions, encoding_format="float"
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("查询文本不能为空")
        response = self.client.embeddings.create(
            model=self.model, input=text, dimensions=self.dimensions, encoding_format="float"
        )
        return response.data[0].embedding


vector_embedding_service = DashScopeEmbeddings(
    api_key=config.dashscope_api_key,
    model=config.dashscope_embedding_model,
    dimensions=1024
)
