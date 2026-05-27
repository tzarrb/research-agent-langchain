
import json
import os
import sys
# 将项目根目录添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from agent_server.utils.log_util import build_logger
from agent_server.schemas.chat.chat_request import ChatRequest
from agent_server.core.exceptions import NotFoundException
from app.agent.chat_agent import async_chat_agent, async_chat_graph,async_chat_graph_summary

logger = build_logger("agent-service")


async def async_chat(data: ChatRequest):
    
    """
    聊天服务入口函数 
    
    Args:
        data: 聊天请求数据
        
    Yields:
        str: JSON格式的聊天响应数据
        
    Raises:
        ValueError: 当输入数据无效时
        NotFoundException: 当模型不存在时
        Exception: 其他系统错误
    """
    logger.info(f"chat_async called with conversation_id: {data.conversation_id}")
    
    # 输入验证
    try:
        _validate_chat_request(data)
    except ValueError as e:
        logger.error(f"Input validation failed: {str(e)}")
        error_result = {
            "error": "Invalid input",
            "message": str(e),
            "conversation_id": data.conversation_id
        }
        yield json.dumps(error_result, ensure_ascii=False)
        return
    
    # 执行聊天逻辑
    logger.info("Starting async_chat_agent...")
    async for chunk in async_chat_graph(data):
        yield chunk
    logger.info("async_chat_agent completed successfully")
    
    # try:
    #     logger.info("Starting async_chat_agent...")
    #     async for chunk in async_chat_graph_summary(data):
    #         yield chunk
    #     logger.info("async_chat_agent completed successfully")
    # except NotFoundException as e:
    #     logger.error(f"Model not found: {str(e)}")
    #     error_result = {
    #         "error": "Model not found",
    #         "message": str(e),
    #         "conversation_id": data.conversation_id
    #     }
    #     yield json.dumps(error_result, ensure_ascii=False)
        
    # except Exception as e:
    #     logger.error(f"Unexpected error in chat_async: {str(e)}", exc_info=True)
    #     error_result = {
    #         "error": "Internal server error",
    #         "message": "An unexpected error occurred",
    #         "conversation_id": data.conversation_id
    #     }
    #     yield json.dumps(error_result, ensure_ascii=False)


def _validate_chat_request(data: ChatRequest) -> None:
    """
    验证聊天请求数据
    
    Args:
        data: 聊天请求数据
        
    Raises:
        ValueError: 当数据无效时
    """
    if not data.input or not data.input.strip():
        raise ValueError("Input cannot be empty")
    
    if data.input and len(data.input) > 10000:  # 假设最大长度限制
        raise ValueError("Input text is too long (max 10000 characters)")
