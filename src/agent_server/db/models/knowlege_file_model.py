from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, BigInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseEntity
from .mixin import DateTimeMixin


class KnowledgeFile(BaseEntity, DateTimeMixin):
    """
    知识文件模型
    """

    __tablename__ = "knowledge_file"
    file_name: Mapped[str] = mapped_column(String(255), comment="文件名")
    file_ext: Mapped[str] = mapped_column(String(10), comment="文件扩展名")
    kb_id: Mapped[int] = mapped_column(BigInteger, index=True, comment="所属知识库ID")
    kb_name: Mapped[str] = mapped_column(String(50), comment="所属知识库名称")
    document_loader_name: Mapped[str] = mapped_column(String(50), comment="文档加载器名称")
    text_splitter_name: Mapped[str] = mapped_column(String(50), comment="文本分割器名称")
    file_version: Mapped[int] = mapped_column(Integer, default=1, comment="文件版本")
    file_mtime: Mapped[float] = mapped_column(Float, default=0.0, comment="文件修改时间")
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="文件大小")
    custom_docs: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否自定义docs")
    docs_count: Mapped[int] = mapped_column(Integer, default=0, comment="切分文档数量")

    def __repr__(self):
        return f"<KnowledgeFile(id='{self.id}', file_name='{self.file_name}', file_ext='{self.file_ext}', kb_id='{self.kb_id}', kb_name='{self.kb_name}', \
            document_loader_name='{self.document_loader_name}', text_splitter_name='{self.text_splitter_name}', file_version='{self.file_version}', \
            created_time='{self.created_time}', updated_time='{self.updated_time}')>"



class FileDoc(BaseEntity):
    """
    文件-向量库文档模型
    """

    __tablename__ = "file_doc"
    kb_id: Mapped[int] = mapped_column(BigInteger, index=True, comment="知识库ID")
    kb_name: Mapped[str] = mapped_column(String(50), comment="知识库名称")
    file_id: Mapped[int] = mapped_column(BigInteger, index=True, comment="文件ID")
    file_name: Mapped[str] = mapped_column(String(255), comment="文件名称")
    doc_id: Mapped[str] = mapped_column(String(50), comment="向量库文档ID")
    meta_data: Mapped[dict] = mapped_column(JSON, default={})

    def __repr__(self):
        return f"<FileDoc(id='{self.id}', kb_id='{self.kb_id}', kb_name='{self.kb_name}', file_id='{self.file_id}', file_name='{self.file_name}', \
            doc_id='{self.doc_id}', metadata='{self.meta_data}')>"
