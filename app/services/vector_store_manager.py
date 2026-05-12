"""向量存储管理器 - 基于 FAISS"""

import os
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from loguru import logger
from app.core.milvus_client import faiss_manager, INDEX_DIR
from app.services.vector_embedding_service import vector_embedding_service

INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
PICKLE_FILE = os.path.join(INDEX_DIR, "index.pkl")


class VectorStoreManager:
    """向量存储管理器（FAISS 后端）"""

    def __init__(self):
        self.vector_store = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized and self.vector_store is not None:
            return
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        try:
            faiss_manager.connect()

            if os.path.exists(INDEX_FILE) and os.path.exists(PICKLE_FILE):
                logger.info(f"从磁盘加载已有 FAISS 索引: {INDEX_FILE}")
                self.vector_store = FAISS.load_local(
                    INDEX_DIR, vector_embedding_service,
                    index_name="index",
                    allow_dangerous_deserialization=True,
                )
                self._initialized = True
            else:
                logger.info("创建新的 FAISS 空索引")
                os.makedirs(INDEX_DIR, exist_ok=True)
                self.vector_store = FAISS.from_texts(["__init__"], vector_embedding_service)
                self._persist()
                self._initialized = True

            logger.info("VectorStore 初始化成功 (FAISS)")

        except Exception as e:
            logger.error(f"VectorStore 初始化失败: {e}")
            self._initialized = False
            self.vector_store = None

    def _persist(self):
        if self.vector_store:
            self.vector_store.save_local(INDEX_DIR, index_name="index")

    def add_documents(self, documents: List[Document]) -> List[str]:
        self._ensure_initialized()
        if self.vector_store is None:
            raise RuntimeError("VectorStore 未初始化，无法添加文档")
        import uuid

        # DashScope embedding API limits batch to 10 texts
        BATCH_SIZE = 6
        all_ids = []

        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            ids = [str(uuid.uuid4()) for _ in batch]
            texts = [doc.page_content for doc in batch]
            metadatas = [doc.metadata for doc in batch]
            self.vector_store.add_texts(texts, metadatas=metadatas, ids=ids)
            all_ids.extend(ids)
            logger.info(f"批次 {i // BATCH_SIZE + 1}: 添加 {len(batch)} 个分片")

        self._persist()
        logger.info(f"添加全部 {len(documents)} 个文档到 VectorStore 完成")
        return all_ids

    def get_vector_store(self):
        self._ensure_initialized()
        return self.vector_store

    def is_ready(self) -> bool:
        return self._initialized and self.vector_store is not None

    def get_all_documents(self) -> List[Document]:
        """获取向量库中所有文档分片"""
        self._ensure_initialized()
        if self.vector_store is None:
            return []
        try:
            docs = []
            store = self.vector_store
            for doc_id in store.index_to_docstore_id.values():
                doc = store.docstore.search(doc_id)
                if doc and doc.page_content != "__init__":
                    docs.append(doc)
            return docs
        except Exception as e:
            logger.error(f"获取全部分片失败: {e}")
            return []

    def get_index_stats(self) -> dict:
        """获取索引统计信息：按文件分组，显示分片数"""
        docs = self.get_all_documents()
        files = {}
        for doc in docs:
            source = doc.metadata.get("_file_name", "unknown")
            if source not in files:
                files[source] = {"file_name": source, "chunk_count": 0, "chunks": []}
            files[source]["chunk_count"] += 1
            files[source]["chunks"].append({
                "content_preview": doc.page_content[:200].replace("\n", " "),
                "content_length": len(doc.page_content),
                "metadata": {k: v for k, v in doc.metadata.items()},
            })
        return {
            "total_documents": len(docs),
            "total_files": len(files),
            "files": list(files.values()),
        }

    def delete_by_file(self, file_name: str) -> int:
        """按文件名删除向量库中的切片，返回删除数量"""
        self._ensure_initialized()
        if self.vector_store is None:
            return 0
        try:
            ids_to_delete = []
            store = self.vector_store
            for doc_id in store.index_to_docstore_id.values():
                doc = store.docstore.search(doc_id)
                if doc and doc.metadata.get("_file_name") == file_name:
                    ids_to_delete.append(doc_id)

            if ids_to_delete:
                store.delete(ids=ids_to_delete)
                self._persist()
                logger.info(f"已从向量库删除: {file_name} ({len(ids_to_delete)} 个切片)")
            else:
                logger.info(f"未找到匹配的切片: {file_name}")
            return len(ids_to_delete)
        except Exception as e:
            logger.error(f"删除切片失败: {e}")
            return 0

    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        try:
            self._ensure_initialized()
            if self.vector_store is None:
                logger.warning("VectorStore 未就绪，返回空结果")
                return []
            docs = self.vector_store.similarity_search(query, k=k)
            docs = [d for d in docs if d.page_content != "__init__"]
            return docs[:k] if len(docs) > k else docs
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []


vector_store_manager = VectorStoreManager()
