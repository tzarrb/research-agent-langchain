# 导入 Base，它是所有模型的基础
from .base import BaseEntity

# 导入你所有的模型，确保它们被 Base.metadata 识别
from .chat_conversation_model import ChatConversation
from .chat_message_model import ChatMessage
from .knowledge_base_model import KnowledgeBase
from .knowlege_file_model import KnowledgeFile
from .knowlege_metadata_model import SummaryChunk


# 可选：使用 __all__ 来明确声明这个包对外暴露的接口
__all__ = ["BaseEntity", "ChatConversation", "ChatMessage",
           "KnowledgeBase", "KnowledgeFile", "SummaryChunk" ]