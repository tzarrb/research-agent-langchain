
from fastapi import APIRouter, Depends, Request, Response, Body
from fastapi.responses import Response

from agent_server.app.chat.chat_conversation_service import ChatConversationService

router = APIRouter(prefix="/conversation", tags=["Chat会话消息"])

@router.get("/list", summary="聊天会话列表")
async def chat_completions(pageIndex: int = Body(1),
                           pageSize: int = Body(10), 
                           service: ChatConversationService = Depends()):
    return await service.list_conversation(page_size=pageSize, page_num=pageIndex)


@router.post("/add", summary="创建聊天会话")
async def create_chat_conversation(name: str, service: ChatConversationService = Depends()):
    return await service.create_chat_conversation(name=name)