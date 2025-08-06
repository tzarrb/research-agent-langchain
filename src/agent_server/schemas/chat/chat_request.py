from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

"""
ChatRequest模型，用于定义聊天补全请求的结构。
"""
class ChatRequest(BaseModel):
    conversation_id: str | None = Field(None, description="会话ID")
    model_provider: str | None = Field(None, description="模型提供商")
    model_name: str | None = Field(None, description="模型名称")
    streaming: bool | None = Field(True, description="是否流式传输")
    enableLocal: bool | None = Field(False, description="是否启用本地知识库")
    enableWeb: bool | None = Field(False, description="是否启用Web搜索")
    enableThink: bool | None = Field(False, description="是否启用思考能力")
    input: str = Field(..., description="用户输入")  # type: ignore
    
