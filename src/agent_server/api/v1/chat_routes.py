import uuid
from nltk import pr

from fastapi import APIRouter, Request, Response, Body
from fastapi.responses import StreamingResponse

from agent_server.app.chat.chat_service import chat, chat_async
from agent_server.schemas.chat.chat_request import ChatRequest
from agent_server.utils.id_util import id_generator

router = APIRouter(prefix="/chat", tags=["Chat对话"])

@router.post("/completions", summary="兼容 openai 的统一 chat 接口")
async def chat_completions(request: Request, response: Response, data: ChatRequest):
    conversation_id = request.headers.get("conversation_id")
    if not conversation_id:
        conversation_id = data.conversation_id
        if not conversation_id:
            conversation_id = str(id_generator.next_id())
            print(f"新增会话：{conversation_id}")
            data.conversation_id = conversation_id       
    
    streaming = data.streaming
    
    headers = {"conversation_id": conversation_id}
    response.headers.update(headers)
    
    result_generator = chat_async(data)
    
    if streaming:
        # 流式输出
        return StreamingResponse(result_generator, media_type="text/event-stream", headers=headers)
    else:
        # 非流式，获取结果
        result = await anext(result_generator)
        return result