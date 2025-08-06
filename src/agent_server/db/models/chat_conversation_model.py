from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseEntity
from .mixin import DateTimeMixin


class ChatConversation(BaseEntity, DateTimeMixin):
    """
    对话记录模型
    """

    __tablename__ = "chat_conversation"
    name: Mapped[str] = mapped_column(String(50), comment="对话框名称")
    chat_type: Mapped[str] = mapped_column(String(50), default="", comment="聊天类型")

    def __repr__(self):
        return f"<Conversation(id='{self.id}', name='{self.name}', chat_type='{self.chat_type}', updated_time='{self.updated_time}', created_time='{self.created_time}')>"
