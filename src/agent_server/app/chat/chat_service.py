import json
import os
import sys
import asyncio
import random
import redis
from calendar import c

from fastapi import Body
from fastapi.responses import StreamingResponse, JSONResponse

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks import StdOutCallbackHandler
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler

# 输出解析
from langchain_core.output_parsers import StrOutputParser

#表示基本的聊天历史记录和内存存储的聊天历史记录
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
#该类用于将聊天模型与聊天历史记录结合在一起
from langchain_core.runnables import RunnableWithMessageHistory,ConfigurableFieldSpec
from langchain_core.messages import HumanMessage

# 历史会话记忆
from langchain_community.chat_message_histories import RedisChatMessageHistory

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.utils.log_util import build_logger
from agent_server.schemas.chat.chat_request import ChatRequest

logger = build_logger("chat-service")

# 初始化会话历史
messages_list: dict[str, BaseChatMessageHistory] = {}
    
def chat(model_name: str, model_provider: str = "deepseek", input: str = ""):
    chat_model = ModelFactory.get_model(model_provider, model_name)
    message = chat_model.invoke(input)
    return message

async def chat_async(data: ChatRequest):
    model_provider = data.model_provider
    model_name = data.model_name
    streaming = data.streaming or True
    
    input = data.input
    conversation_id = data.conversation_id

    # 定义 Prompt 模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位乐于助人的 AI 助手,请根据用户的问题给出回答"),
        MessagesPlaceholder(variable_name="history"),
        ("human",  "{input}")
    ])

    std_handler = StdOutCallbackHandler()
    asynchandler = AsyncIteratorCallbackHandler()
    callbacks = [std_handler]
    if streaming:
        # 将异步回调处理器添加到回调列表中
        callbacks = [std_handler, asynchandler]
    
    chat_model = ModelFactory.get_model(model_provider, model_name, streaming, callbacks)
    parser = StrOutputParser()
    
    # 链式组合：Prompt → ChatModel
    chain = prompt | chat_model | parser
    chain_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",    
        history_messages_key="history",
        history_factory_config=[        
            ConfigurableFieldSpec(            
                id="conversation_id",            
                annotation=str,            
                name="Conversation ID",            
                default="",            
                is_shared=True,        
                ),    
            ],
    )
    
    try:
        if streaming:
            #  异步流式输出（建议放在 async 函数中调用）:RunnableConfig
            async for chunk in chain_history.astream(
                {"input": input},
                config={"configurable": {"conversation_id": conversation_id}}
            ):
                logger.info(f"conversation_id: {conversation_id}, chat stream: {chunk}")
                print(chunk, end="", flush=True)
                response={"content":chunk, "conversation_id": conversation_id}
                yield json.dumps(response)

            # async for event in chain_history.astream_events(
            #     {"input": input},
            #     config=config
            # ):
            #     logger.info(f"conversation_id: {conversation_id}, chat stream: {event}")
            #     print(event, end="", flush=True)
            #     yield event.values
        else:
            # Use async invocation with proper configuration
            result = await chain_history.ainvoke(
                {"input": input},
                config={"configurable": {"conversation_id": conversation_id}}
            )
            response={"content":result, "conversation_id": conversation_id}
            logger.info(f"conversation_id: {conversation_id}, chat result: {result}")
            yield json.dumps(response)
    except Exception as e:
        # Handle errors appropriately
        logger.error(f"Error in chat processing: {str(e)}")
        raise  # Or return a custom error response

 
def get_session_history(conversation_id: str) -> BaseChatMessageHistory:    
    return RedisChatMessageHistory(
        session_id=conversation_id, 
        url="redis://localhost:6379/0", #密码redis://:123456@localhost:6379/0
        key_prefix = "researchagent-lang:chat:memory:", 
        ttl=600)           

def get_redis_client():    
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        password="",
        db=0
    )       
    redis_client.ping()
    return redis_client

if __name__ == "__main__":
    # message = chat("deepseek-chat", "deepseek", "请介绍下杭州的著名旅游景点")
    # print(message.content)
    # message = asyncio.run(async_chat("请介绍下杭州的著名旅游景点"))
    # print(message.content)
    pass
