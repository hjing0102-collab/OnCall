"""向量检索服务模块"""

from typing import Any, Dict, List
from loguru import logger
from app.services.vector_store_manager import vector_store_manager


class SearchResult:
    def __init__(self, id: str, content: str, score: float, metadata: Dict[str, Any]):
        self.id = id
        self.content = content
        self.score = score
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "content": self.content, "score": self.score, "metadata": self.metadata}


class VectorSearchService:
    def search_similar_documents(self, query: str, top_k: int = 3) -> List[SearchResult]:
        try:
            logger.info(f"搜索相似文档: {query}, topK: {top_k}")
            docs = vector_store_manager.similarity_search(query, k=top_k)
            results = []
            for doc in docs:
                results.append(SearchResult(
                    id=doc.metadata.get("id", ""),
                    content=doc.page_content,
                    score=doc.metadata.get("score", 0.0),
                    metadata=doc.metadata,
                ))
            logger.info(f"搜索完成, 找到 {len(results)} 个相似文档")
            return results
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []


vector_search_service = VectorSearchService()
