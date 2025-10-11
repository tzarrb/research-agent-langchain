import json
import os
import sys
import asyncio
import random
import redis
import html

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from fastapi import Depends
from fastapi.responses import StreamingResponse, JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession

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

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever # 历史感知检索器
from langchain.schema.runnable import RunnablePassthrough

# 历史会话记忆
from langchain_community.chat_message_histories import RedisChatMessageHistory

from langchain_tavily import TavilySearch

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger
from agent_server.utils.id_util import id_generator
from agent_server.schemas.chat.chat_request import ChatRequest
from agent_server.app.rag.vector_store.base import VsServiceFactory, SupportedVSType

from agent_server.schemas.chat.chat_conversation_schema import ChatConversationCreate
from agent_server.db.models.chat_conversation_model import ChatConversation
from agent_server.db.repository.chat_conversation_repository import chat_conversation_repository
from agent_server.db.base import get_async_db, _AsyncSessionFactory

from agent_server.app.tool.datetime_tool import current_datetime
from agent_server.app.tool.weather_tool import weather_tool
from agent_server.app.tool.search_tool import search_tool
from agent_server.app.tool.retriever_tool import retriever_tool

logger = build_logger("chat-service")

SYSTEM_PROMPT = """
    你是一位乐于助人的 AI问答助手, 请根据用户的问题以及上下文信息回答问题。
    如果匹配到合适的工具则调用工具获取信息, 并将工具返回的信息作为回答的一部分。
    如果没有匹配到合适的工具, 或者无法通过工具解决（例如，问事实、聊天、创作、分析等），则**禁止调用任何工具**，直接运用你的知识来回答。
    如果你不确定答案, 请说你不知道, 不要编造信息。
    请使用简体中文回答。
    """

WEB_SYSTEM_PROMPT = """
    你是一位乐于助人的 AI问答助手, 请根据用户的问题以及上下文信息回答问题。
    请优先从网络上搜索用户问题相关的信息, 并将返回的信息作为回答的一部分。如果没有匹配的信息，则直接运用你的知识来回答。
    如果你不确定答案, 请说你不知道, 不要编造信息。
    请使用简体中文回答。
    """

KNOWLEDGE_SYSTEM_PROMPT = """
    你是一位乐于助人的 AI问答助手, 请根据用户的问题以及上下文信息回答问题。
    请优先从知识库中获取信息, 并将返回的信息作为回答的一部分。如果知识库中没有匹配的信息，则直接运用你的知识来回答。
    如果你不确定答案, 请说你不知道, 不要编造信息。
    请使用简体中文回答。
    """

# 初始化会话历史
messages_list: dict[str, BaseChatMessageHistory] = {}

    
def chat(model_name: str, model_provider: str = "deepseek", input: str = ""):
    chat_model = ModelFactory.get_model(model_provider, model_name)
    message = chat_model.invoke(input)
    return message

async def async_chat(data: ChatRequest):
    model_provider = data.model_provider
    model_name = data.model_name
    streaming = data.streaming or True
    
    input = data.input
    conversation_id = data.conversation_id

    # 定义回调处理器
    std_handler = StdOutCallbackHandler()
    async_handler = AsyncIteratorCallbackHandler()
    callbacks = [std_handler]
    if streaming:
        # 将异步回调处理器添加到回调列表中
        callbacks.append(async_handler)

    # 系统提示词
    system_prompt = SYSTEM_PROMPT
    if data.enableWeb:
        system_prompt = WEB_SYSTEM_PROMPT
    if data.enableLocal:
        system_prompt = KNOWLEDGE_SYSTEM_PROMPT
    system_prompt = data.system or system_prompt
    
    # 工具
    tools = [current_datetime, weather_tool]
    if data.enableWeb:
        tools.append(search_tool)
    if data.enableLocal: 
        tools.append(retriever_tool)

    # 聊天模型
    chat_model = ModelFactory.get_model(model_provider, model_name, streaming, [])
    tool_model = chat_model.bind_tools(tools)
    
    # 输出解析器
    parser = StrOutputParser()

    # Prompt 模板
    history_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human",  "{input}")
    ])

    # 链式组合：Prompt → ChatModel
    conversational_chain = history_prompt | tool_model | parser

    # 本地知识库RAG向量搜索构建 ====================================================================================
    # 本地知识库向量检索器
    vs_service = VsServiceFactory.get_service(vector_store_type=Settings.kn_settings.DEFAULT_VS_TYPE)
    retriever = vs_service.get_vector_store_retriever()

    # 关联问题背景系统提示词模版
    history_aware_template = (
        """
        根据上面的对话历史和用户最新问题，生成一个独立的、用于检索相关文档的问题。
        只返回新的查询，不要添加其他内容。
        """
    )
    history_aware_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", history_aware_template),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]
    )
    # 将 llm 和 history_aware_prompt 组合，用于生成新的查询，然后将查询传给 retriever
    history_aware_retriever = create_history_aware_retriever(
        chat_model,
        retriever=retriever, # 基础检索器
        prompt=history_aware_prompt # 用于生成新的查询的Prompt
    )
    
    # 定义 RAG 提示词模板
    rag_template = (
        """
        你是一个负责问答任务的助手。
        请根据提供的上下文回答以下问题。
        如果上下文没有足够的信息，请说明你不知道。

        上下文:
        {context}
        """
    )
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", rag_template),
        MessagesPlaceholder(variable_name="history"), # 确保Prompt也能看到历史
        ("human", "{input}")
    ])
    # 构建文档合并链
    rag_history_document_chain = create_stuff_documents_chain(
        chat_model, 
        rag_prompt
    )
    
    # 构建最终的 RAG 链 (使用历史感知检索器)
    rag_chain = create_retrieval_chain(
        history_aware_retriever, # 这里使用历史感知检索器
        rag_history_document_chain
    )
    
    # 最终的会话链
    # chain = rag_chain if data.enableLocal else conversational_chain
    chain = conversational_chain

    # 构建包含会话历史的链
    output_messages_key = "answer" if data.enableLocal else "output"
    message_history_chain = RunnableWithMessageHistory(
        chain,
        get_message_history,
        input_messages_key="input",
        history_messages_key="history",  # 与 Prompt 中的 placeholder 对应
        output_messages_key=output_messages_key,  # 与 create_retrieval_chain 的输出字典中的键对应
        history_factory_config=[
            ConfigurableFieldSpec(
                id="conversation_id",
                name="Conversation ID",            
                default="",   
                annotation=str,         
                is_shared=True,        
                ),    
            ],
    )
    
    config = {
        "configurable": {
            "conversation_id": conversation_id
        }
    }

    try:
        if streaming:
            #  异步流式输出（建议放在 async 函数中调用）:RunnableConfig
            async for chunk in message_history_chain.astream(
                {"input": input},
                config=config
            ):
                logger.info(f"conversation_id: {conversation_id}, chat stream: {html.escape(str(chunk))}")
                print(chunk, end="", flush=True)
                # response={"content":chunk, "conversation_id": conversation_id}    

                if data.enableLocal:
                    # RAG链返回的是字典，包含answer和context
                    if isinstance(chunk, dict):
                        content = chunk.get('answer')
                    else:
                        content = str(chunk)
                else:
                    # 普通对话链返回的是字符串
                    content = chunk if isinstance(chunk, str) else str(chunk)

                response = {"content": content, "conversation_id": conversation_id}
                # yield json.dumps(response)
                yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n".encode('utf-8')
        else:
            # Use async invocation with proper configuration
            result = await message_history_chain.ainvoke(
                {"input": input},
                config=config
            )
            logger.info(f"conversation_id: {conversation_id}, chat result: {result}")
            response={"content":result, "conversation_id": conversation_id}
            yield json.dumps(response)

        await save_chat_conversation(input, int(conversation_id))
    except Exception as e:
        # Handle errors appropriately
        logger.error(f"Error in chat processing: {html.escape(str(e))}")
        raise  # Or return a custom error response

async def save_chat_conversation(input: str, conversation_id: int):
    chat_conversation = await chat_conversation_repository.get(id=conversation_id)
    if chat_conversation:
        return
    
    chat_conversation = await chat_conversation_repository.create(
        obj_in = ChatConversationCreate(
            id=conversation_id,
            name=input,
            chat_type="general"
        )
    )
    logger.info(f"新增会话成功：{chat_conversation}")

def get_message_history(conversation_id: str) -> BaseChatMessageHistory:    
    return RedisChatMessageHistory(
        session_id=conversation_id, 
        url=Settings.db_settings.REDIS_URL,
        key_prefix=Settings.db_settings.REDIS_PREFIX_CHAT_MEMORY,
        ttl=60 * 60 * 24 * 7  # 7 days
    )

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
