from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from agent_server.schemas.base import BaseSchema


class ChatConversationBase(BaseSchema):
    id: int | None = Field(None, description="会话ID")
    name: str = Field("新会话", description="会话名称")
    chat_type: str | None = Field("", description="聊天类型")
    
class ChatConversationCreate(ChatConversationBase):
    pass

class ChatConversationUpdate(ChatConversationBase):
    id: int = Field(description="会话ID")
