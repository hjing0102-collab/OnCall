"""向量索引服务模块"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger
from app.services.document_splitter_service import document_splitter_service
from app.services.vector_store_manager import vector_store_manager


class IndexingResult:
    def __init__(self):
        self.success = False
        self.directory_path = ""
        self.total_files = 0
        self.success_count = 0
        self.fail_count = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error_message = ""
        self.failed_files: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        duration_ms = 0
        if self.start_time and self.end_time:
            duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        return {
            "success": self.success,
            "directory_path": self.directory_path,
            "total_files": self.total_files,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "duration_ms": duration_ms,
            "error_message": self.error_message,
            "failed_files": self.failed_files,
        }


class VectorIndexService:
    def __init__(self):
        self.upload_path = "./uploads"
        logger.info("向量索引服务初始化完成")

    def index_single_file(self, file_path: str):
        path = Path(file_path).resolve()
        if not path.exists():
            raise ValueError(f"文件不存在: {file_path}")

        logger.info(f"开始索引文件: {path}")
        ext = path.suffix.lower()

        try:
            if ext == ".pdf":
                content = document_splitter_service.extract_pdf_text(str(path))
            else:
                content = path.read_text(encoding="utf-8")

            documents = document_splitter_service.split_document(content, str(path))
            if documents:
                vector_store_manager.add_documents(documents)
                logger.info(f"文件索引完成: {file_path}, 共 {len(documents)} 个分片")
        except Exception as e:
            logger.error(f"索引文件失败: {file_path}, 错误: {e}")
            raise RuntimeError(f"索引文件失败: {e}")

    def index_directory(self, directory_path: Optional[str] = None) -> IndexingResult:
        result = IndexingResult()
        result.start_time = datetime.now()

        try:
            target_path = directory_path or self.upload_path
            dir_path = Path(target_path).resolve()

            if not dir_path.exists():
                raise ValueError(f"目录不存在: {target_path}")

            result.directory_path = str(dir_path)
            files = list(dir_path.glob("*.txt")) + list(dir_path.glob("*.md")) + list(dir_path.glob("*.pdf"))

            if not files:
                result.success = True
                result.end_time = datetime.now()
                return result

            result.total_files = len(files)
            for file_path in files:
                try:
                    self.index_single_file(str(file_path))
                    result.success_count += 1
                except Exception as e:
                    result.fail_count += 1
                    result.failed_files[str(file_path)] = str(e)

            result.success = result.fail_count == 0
            result.end_time = datetime.now()
            return result
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.end_time = datetime.now()
            return result


vector_index_service = VectorIndexService()
