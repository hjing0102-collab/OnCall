"""文档分割服务 - 支持 PDF/MD/TXT"""

from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from loguru import logger
from app.config import config


class DocumentSplitterService:
    """文档分割服务"""

    def __init__(self):
        self.chunk_size = config.chunk_max_size
        self.chunk_overlap = config.chunk_overlap

        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2")],
            strip_headers=False,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        logger.info(f"文档分割服务初始化完成, chunk_size={self.chunk_size}")

    def split_document(self, content: str, file_path: str = "") -> List[Document]:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext == ".md":
            return self._split_markdown(content, file_path)
        return self._split_text(content, file_path)

    def _split_markdown(self, content: str, file_path: str) -> List[Document]:
        if not content or not content.strip():
            return []
        md_docs = self.markdown_splitter.split_text(content)
        docs = self.text_splitter.split_documents(md_docs)
        final_docs = self._merge_small_chunks(docs, min_size=300)
        for doc in final_docs:
            doc.metadata["_source"] = file_path
            doc.metadata["_extension"] = ".md"
            doc.metadata["_file_name"] = Path(file_path).name
        logger.info(f"Markdown 分割: {file_path} -> {len(final_docs)} 个分片")
        return final_docs

    def _split_text(self, content: str, file_path: str) -> List[Document]:
        if not content or not content.strip():
            return []
        docs = self.text_splitter.create_documents(
            texts=[content],
            metadatas=[{
                "_source": file_path,
                "_extension": Path(file_path).suffix,
                "_file_name": Path(file_path).name,
            }],
        )
        logger.info(f"文本分割: {file_path} -> {len(docs)} 个分片")
        return docs

    def _merge_small_chunks(self, documents: List[Document], min_size: int = 300) -> List[Document]:
        if not documents:
            return []
        merged = []
        current = None
        for doc in documents:
            if current is None:
                current = doc
            elif len(doc.page_content) < min_size and len(current.page_content) < self.chunk_size:
                current.page_content += "\n\n" + doc.page_content
            else:
                merged.append(current)
                current = doc
        if current is not None:
            merged.append(current)
        return merged

    def extract_pdf_text(self, file_path: str) -> str:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)


document_splitter_service = DocumentSplitterService()
