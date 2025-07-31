# 导入 Base，它是所有模型的基础
from .base import BaseModel

# 导入你所有的模型，确保它们被 Base.metadata 识别
from .chat_conversation_model import ChatConversationModel
from .chat_message_model import ChatMessageModel
from .knowledge_base_model import KnowledgeBaseModel
from .knowlege_file_model import KnowledgeFileModel
from .knowlege_metadata_model import SummaryChunkModel


# 可选：使用 __all__ 来明确声明这个包对外暴露的接口
__all__ = ["BaseModel", "ChatConversationModel", "ChatMessageModel",
           "KnowledgeBaseModel", "KnowledgeFileModel", "SummaryChunkModel" ]