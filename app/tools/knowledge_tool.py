"""知识检索工具"""

from typing import List, Tuple
from langchain_core.documents import Document
from langchain_core.tools import tool
from loguru import logger
from app.config import config
from app.services.vector_store_manager import vector_store_manager


@tool(response_format="content_and_artifact")
def retrieve_knowledge(query: str) -> Tuple[str, List[Document]]:
    """从知识库中检索相关信息来回答问题"""
    try:
        logger.info(f"知识检索: query='{query}'")
        vector_store = vector_store_manager.get_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": config.rag_top_k})
        docs = retriever.invoke(query)

        if not docs:
            return "没有找到相关信息。", []

        context = _format_docs(docs)
        logger.info(f"检索到 {len(docs)} 个相关文档")
        return context, docs
    except Exception as e:
        logger.error(f"知识检索失败: {e}")
        return f"检索错误: {str(e)}", []


def _format_docs(docs: List[Document]) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("_file_name", "未知来源")
        headers = []
        for key in ["h1", "h2"]:
            if key in doc.metadata and doc.metadata[key]:
                headers.append(doc.metadata[key])
        header_str = " > ".join(headers) if headers else ""
        formatted = f"【参考资料 {i}】"
        if header_str:
            formatted += f"\n标题: {header_str}"
        formatted += f"\n来源: {source}"
        formatted += f"\n内容:\n{doc.page_content}\n"
        parts.append(formatted)
    return "\n".join(parts)
