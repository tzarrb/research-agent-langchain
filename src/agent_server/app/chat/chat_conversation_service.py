from agent_server.db.repository.chat_conversation_repository import chat_conversation_repository
from agent_server.schemas.chat.chat_conversation_schema import ChatConversationCreate

class ChatConversationService:
    def __init__(self):
        self.chat_conversation_repository = chat_conversation_repository

    async def list_conversation(self, page_size: int = 10, page_num: int = 1):
        """
        获取聊天会话列表
        """
        order_by: list[dict[str, str]] = [{"field":"updated_time", "direction":"desc"}]
        return await self.chat_conversation_repository.list(page_size=page_size, page_num=page_num, order_by=order_by)

    async def create_chat_conversation(self, name: str):
        """
        创建新的聊天会话
        """
        data = ChatConversationCreate(name=name)
        return await self.chat_conversation_repository.create(obj_in=data)