import uuid
import asyncio

from fastapi import APIRouter, Request, Response, Body
from fastapi.responses import StreamingResponse

from agent_server.app.service.agent_service import async_chat
# from agent_server.app.agent.basic_agent import async_chat, async_chat_agent
from agent_server.schemas.chat.chat_request import ChatRequest
from agent_server.utils.id_util import id_generator
from agent_server.utils.log_util import build_logger

logger = build_logger("chat-routes")

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
    
    result_generator = async_chat(data)
    
    if streaming:
        # 流式输出
        # 创建自定义的流式响应生成器
        # async def streaming_generator():
        #     async for chunk in result_generator:
        #         yield chunk
        #         # 强制立即刷新
        #         await asyncio.sleep(0)
        
        return StreamingResponse(
            result_generator,
            media_type="text/event-stream",
            headers=headers,
            background=None  # 禁用缓冲，防止后台任务缓冲数据
        )
    else:
        # 非流式，获取结果
        result = await anext(result_generator)
        logger.debug(f"Non-Streaming response result:{result}")
        return result