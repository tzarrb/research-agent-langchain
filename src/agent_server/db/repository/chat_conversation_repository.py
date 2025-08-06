
from .base import BaseRepository
from ...db.models.chat_conversation_model import ChatConversation
from ...schemas.chat.chat_conversation_schema import ChatConversationCreate, ChatConversationUpdate

class ChatConversationRepository(BaseRepository[ChatConversation, ChatConversationCreate, ChatConversationUpdate]):
    # 这里是空的！因为所有基础方法都已自动获得。
    # 我们只需要在这里添加ChatConversation专属的查询，比如按名称查找。
    pass

chat_conversation_repository = ChatConversationRepository(ChatConversation)


if __name__ == "__main__":
    
    import os
    import sys
    
    # 把 src 加入 sys.path
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "...."))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    print("Current sys.path = ", sys.path)


    # 测试代码示例
    async def test_repository():
        # async with async_session() as session:
        #     repo = ChatConversationRepository(ChatConversation)
        #     new_conversation = ChatConversationCreate(name="Test Conversation", chat_type="general")
        #     created_conversation = await repo.create(session, obj_in=new_conversation)
        #     chat_conversation_repository.create(new_conversation)
        #     print(f"Created Conversation: {created_conversation}")
    
        new_conversation = ChatConversationCreate(name="Test Conversation", chat_type="general")
        created_conversation = chat_conversation_repository.create(new_conversation)
        print(f"Created Conversation: {created_conversation}")

    import asyncio
    asyncio.run(test_repository())
