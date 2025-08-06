from sqlalchemy.orm.properties import MappedColumn


from sqlalchemy.orm.properties import MappedColumn


from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseEntity
from .mixin import DateTimeMixin

class KnowledgeBase(BaseEntity, DateTimeMixin):
    """
    知识库模型
    """

    __tablename__ = "knowledge_base"
    kb_name: MappedColumn[str] = mapped_column(String(50), comment="知识库名称")
    kb_info: MappedColumn[str | None] = mapped_column(String(200), comment="知识库简介(用于Agent)")
    vs_type: MappedColumn[str | None] = mapped_column(String(50), comment="向量库类型")
    embed_model: MappedColumn[str | None] = mapped_column(String(50), comment="嵌入模型名称")
    file_count: MappedColumn[int] = mapped_column(Integer, default=0, comment="文件数量")

    def __repr__(self):
        return f"<KnowledgeBase(id='{self.id}', kb_name='{self.kb_name}',kb_intro='{self.kb_info}', vs_type='{self.vs_type}', embed_model='{self.embed_model}', file_count='{self.file_count}', updated_time='{self.updated_time}', created_time='{self.created_time}')>"

