"""FAISS 向量存储客户端管理器"""

import os
from loguru import logger

INDEX_DIR = "./faiss_index"


class FAISSClientManager:
    """FAISS 客户端管理器——纯本地文件存储"""

    def __init__(self):
        self._initialized = False
        self._index_path = os.path.join(INDEX_DIR, "index.faiss")

    def connect(self):
        if self._initialized:
            return
        os.makedirs(INDEX_DIR, exist_ok=True)
        self._initialized = True
        logger.info(f"FAISS 索引目录已就绪: {INDEX_DIR}")

    def health_check(self) -> bool:
        return self._initialized and os.path.isdir(INDEX_DIR)

    def close(self):
        self._initialized = False
        logger.info("已关闭 FAISS 连接")

    def get_index_path(self) -> str:
        return self._index_path


faiss_manager = FAISSClientManager()
