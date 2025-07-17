import uuid
from google.ai.generativelanguage_v1beta.types import content
from nltk import pr

from fastapi import APIRouter, Request, Response, Body
from fastapi.responses import StreamingResponse

from researchagent_server.chat.chat_service import chat, chat_async
from entity.chat_request import ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat对话"])

@router.post("/completions", summary="兼容 openai 的统一 chat 接口")
async def chat_completions(request: Request, response: Response, data: ChatRequest):
    conversation_id = request.headers.get("conversation_id", "")
    if conversation_id == "" or conversation_id is None:
        conversation_id = data.conversation_id
        if conversation_id == "" or conversation_id is None:
            conversation_id = str(uuid.uuid4())
            print(f"新增会话：{conversation_id}")
            data.conversation_id = conversation_id
    
    streaming = data.streaming
    
    headers = {"conversation_id": str(conversation_id)}
    response.headers.update(headers)
    
    result_generator = chat_async(data)
    
    if streaming:
        # 流式输出

        return StreamingResponse(result_generator, media_type="text/event-stream", headers=headers)
    else:
        # 非流式，获取结果
        # 获取异步迭代器的第一个结果
        # result = await anext(result_generator)
        # return {"result": result, "conversation_id": conversation_id}
        pass