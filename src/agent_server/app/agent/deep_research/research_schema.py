from pydantic import BaseModel, Field


# ===== 结构化输出模式 =====

class ClarifyWithUser(BaseModel):
    """范围确定阶段用户澄清决策的模式。"""
    need_clarification: bool = Field(
        description="是否需要向用户询问澄清问题。",
    )
    question: str = Field(
        description="向用户询问以澄清报告范围的问题",
    )
    verification: str = Field(
        description="确认消息，表示在用户提供必要信息后我们将开始研究。",
    )

class ResearchQuestion(BaseModel):
    """研究简报生成的模式。"""
    research_brief: str = Field(
        description="将用于指导研究的研究问题。",
    )

class Summary(BaseModel):
    """网页内容摘要的模式。"""
    summary: str = Field(description="网页内容的简洁摘要")
    key_excerpts: str = Field(description="内容中的重要引用和摘录")