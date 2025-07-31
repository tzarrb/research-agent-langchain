from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel
from .mixin import DateTimeMixin


class ChatConversationModel(BaseModel, DateTimeMixin):
    """
    对话记录模型
    """

    __tablename__ = "cht_conversation"
    name: Mapped[str] = mapped_column(String(50), comment="对话框名称")
    chat_type: Mapped[str] = mapped_column(String(50), comment="聊天类型")

    def __repr__(self):
        return f"<Conversation(id='{self.id}', name='{self.name}', chat_type='{self.chat_type}', create_time='{self.create_time}')>"
