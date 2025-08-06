from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseEntity
from .mixin import DateTimeMixin


class ChatMessage(BaseEntity, DateTimeMixin):
    """
    聊天记录模型
    """

    __tablename__ = "chat_message"
    conversation_id: Mapped[int] = mapped_column(Integer, index=True, comment="对话框ID")
    chat_type: Mapped[str] = mapped_column(String(50), default="", comment="聊天类型")
    question: Mapped[str] = mapped_column(String(4096), comment="用户问题")
    answer: Mapped[str] = mapped_column(String(4096), comment="模型回答")
    # 记录知识库id等，以便后续扩展
    meta_data: Mapped[dict] = mapped_column(JSON, default={})
    # 满分100 越高表示评价越好
    feedback_score: Mapped[int] = mapped_column(Integer, default=-1, comment="用户评分")
    feedback_reason: Mapped[str] = mapped_column(String(255), default="", comment="用户评分理由")

    def __repr__(self):
        return f"<message(id='{self.id}', conversation_id='{self.conversation_id}', chat_type='{self.chat_type}', question='{self.question}', answer='{self.answer}', meta_data='{self.meta_data}', feedback_score='{self.feedback_score}', feedback_reason='{self.feedback_reason}', updated_time='{self.updated_time}', created_time='{self.created_time}')>"
