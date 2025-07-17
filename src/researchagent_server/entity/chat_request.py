from typing import Optional, List
from pydantic import BaseModel, Field

"""
ChatRequest模型，用于定义聊天补全请求的结构。
"""
class ChatRequest(BaseModel):
    conversation_id: str | None = Field(None, description="会话ID")
    model_provider: str | None = Field("deepseek", description="模型提供商")
    model_name: str | None = Field("deepseek-chat", description="模型名称")
    streaming: bool | None = Field(True, description="是否流式传输")
    input: str = Field(..., description="用户输入")