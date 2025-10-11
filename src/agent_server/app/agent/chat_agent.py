
import json
import os
import sys
import operator
import requests

from agent_server.config import settings
# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Literal, TypedDict, Annotated, AsyncGenerator
from pydantic import BaseModel, Field

# from langchain.agents import create_agent, AgentState, ToolNode
from langgraph.prebuilt import create_react_agent, ToolNode

from langchain_core.callbacks import UsageMetadataCallbackHandler, usage
from langchain_core.runnables import RunnableConfig

from langchain_core.messages import RemoveMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES, MessagesState, add_messages 
from langgraph.checkpoint.memory import InMemorySaver
# from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.memory import InMemoryStore
from langgraph.config import get_store
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

#表示基本的聊天历史记录和内存存储的聊天历史记录
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
#该类用于将聊天模型与聊天历史记录结合在一起
from langchain_core.runnables import RunnableWithMessageHistory,ConfigurableFieldSpec
from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)
from langmem.short_term import SummarizationNode, RunningSummary

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from langgraph.store.base import BaseStore

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger
from agent_server.utils.id_util import id_generator
from agent_server.schemas.chat.chat_request import ChatRequest

from agent_server.core.exceptions import NotFoundException, UnauthorizedException
from agent_server.schemas.chat.chat_conversation_schema import ChatConversationCreate
from agent_server.db.models.chat_conversation_model import ChatConversation
from agent_server.db.repository.chat_conversation_repository import chat_conversation_repository
from agent_server.db.base import get_async_db, _AsyncSessionFactory

from agent_server.app.tool.datetime_tool import current_datetime
from agent_server.app.tool.weather_tool import weather_tool
from agent_server.app.tool.search_tool import search_tool
from agent_server.app.tool.retriever_tool import retriever_tool

logger = build_logger("basic-agent")

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
    
async def async_chat_agent(data: ChatRequest):
    model_provider = data.model_provider
    model_name = data.model_name
    streaming = data.streaming or True
    
    input = data.input
    conversation_id = data.conversation_id

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

    # 工具节点
    tool_node = ToolNode(
        tools=tools,
        handle_tool_errors="Please check your input and try again."
    )

    human_message = HumanMessage(content=input)
    system_message = SystemMessage(content=system_prompt)

    human_messages = HumanMessage(content=[
        {"type": "text", "text": "Hello, how are you?"},
        {"type": "image_url", "image_url": {"url": "https://avatars.githubusercontent.com/u/7997078?v=4"}}
    ])
    
    usage_callback = UsageMetadataCallbackHandler()
    
    # 设置检查点
    # checkpointer = InMemorySaver()

    # 聊天模型
    chat_model = ModelFactory.get_model(model_provider, model_name, streaming, [])
    
    #运行时可配置项
    runnable_config: RunnableConfig = {
        "run_name": "agent_chat",      # 识别日志和跟踪中的特定调用。不会被子调用继承
        "tags": ["chat", "agent"],     # 所有子调用继承的标签，用于调试工具中的过滤和组织
        "metadata": {"conversation_id": conversation_id},     # 自定义键值对，用于跟踪附加上下文，并由所有子调用继承
        "callbacks": [usage_callback], # 用于监控和响应执行过程中事件的处理器
        "configurable": {
            "thread_id": conversation_id,
            "conversation_id": conversation_id,
            # "rsa_model": "gpt-5-nano",
            # "rsa_model_provider": "openai",
            # "rsa_api_key": "sk-xxxxxx",
            # "rsa_base_url": "",
        },
    }

    # async with AsyncRedisSaver.from_conn_string(Settings.db_settings.REDIS_URL) as checkpointer :
    async with AsyncPostgresSaver.from_conn_string(Settings.db_settings.POSTGRES_DATABASE_URI) as checkpointer:
        # 第一次启动初始化检查点
        await checkpointer.setup()
        
        # 创建智能体
        agent = create_react_agent(
            chat_model,
            tools=tools,
            prompt=system_message,
            checkpointer=checkpointer,
            pre_model_hook=pre_model_hook,
            debug=True  # 启用调试模式
        )
        
        if streaming:
            # stream_mode : values:以完整响应块流式输出，updates:分步骤输出, messages:以token流式输出
            # async for chunk in agent.astream(
            #     input={"messages": [human_message]},
            #     config=runnable_config,
            #     stream_mode="values" # values:以完整响应块流式传输
            # ):
            #     logger.info(f"Agent response chunk: {chunk}")
                
            #     content = ""
            #     # Each chunk contains the full state at that point
            #     latest_message = chunk["messages"][-1]
            #     logger.info(f"Agent response message: {latest_message}")
            #     if latest_message.content:
            #         content = latest_message.content
            #         logger.info(f"Agent response content: {content}")
            #     elif latest_message.tool_calls:
            #         logger.info(f"Agent calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")

            #     # token 使用量
            #     # usage_callback.usage_metadata
            
            #     result = {"content": content, "conversation_id": conversation_id}
            #     yield json.dumps(result, ensure_ascii=False)
            #     # yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n".encode('utf-8')
                
            # stream_mode : updates:分步骤输出
            # async for chunk in agent.astream(
            #     input={"messages": [human_message]},
            #     config=runnable_config,
            #     stream_mode="updates" # updates:分步骤输出
            # ):
            #     logger.info(f"Agent response chunk: {chunk}")
                
            #     content = ""
            #     for step, data in chunk.items():
            #         logger.debug(f"step: {step}")
            #         logger.debug(f"data: {data}")
            #         # logger.info(f"content: {data['messages'][-1].content_blocks}")
                    
            #         latest_message = data["messages"][-1]
            #         if step == "agent":
            #             content = latest_message.content
            #             logger.debug(f"Agent response content: {content}")
            #         elif step == "tools":
            #             logger.debug(f"Tool response content: {latest_message.content}, tool name:{latest_message.name}")

            #     result = {"content": content, "conversation_id": conversation_id}
            #     yield json.dumps(result, ensure_ascii=False)
            
            # stream_mode : messages:以token流式输出    
            async for token, metadata in agent.astream(
                input={"messages": [human_message]},
                config=runnable_config,
                stream_mode="messages", # messages:以token流式传输
            ):
                logger.info(f"Agent response token: {token}")
                logger.info(f"Agent response metadata: {metadata}")
                
                node = metadata.get("langgraph_node", "unknown")
                logger.debug(f"node: {node}")
                # logger.debug(f"content: {token.content_blocks}")
                
                content = ""
                if node == "agent":
                    content = token.content
                    logger.debug(f"Agent response content: {content}")
                    if hasattr(token, 'tool_call_chunks') and token.tool_call_chunks:
                        tool_call = token.tool_call_chunks[-1]
                        if tool_call.get('name'):
                            logger.debug(f"Agent calling tool: {tool_call.get('name')}")
                        elif tool_call.get('args'):
                            logger.debug(f"Agent calling tool with args: {tool_call.get('args')}")
                elif node == "tools":
                    logger.debug(f"Tool response content: {token.content}")

                result = {"content": content, "conversation_id": conversation_id}
                logger.debug(f"Agent stream response result: {result}")
                # yield json.dumps(result, ensure_ascii=False)
                yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n".encode('utf-8')
                
        else:
            response = await agent.ainvoke(
                input={"messages": [human_message]},
                config=runnable_config
            )
            # logger.debug(response.content_blocks)

            result = {"content": response.get("content"), "conversation_id": conversation_id}
            yield json.dumps(result, ensure_ascii=False)


async def async_chat_graph(data: ChatRequest):
    model_provider = data.model_provider
    model_name = data.model_name
    streaming = data.streaming or True
    
    input = data.input
    conversation_id = data.conversation_id

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
    tools_by_name = {tool.name: tool for tool in tools}

    # 聊天模型
    chat_model = ModelFactory.get_model(model_provider, model_name, streaming, [])
    # 绑定工具
    # tool_choice "auto":模型自动决定是否调用工具, "none":不调用工具, "any/required":至少调用一个工具
    llm_with_tools = chat_model.bind_tools(tools, tool_choice="auto")
    
    usage_callback = UsageMetadataCallbackHandler()

    human_message = HumanMessage(content=input)

    #运行时可配置项
    runnable_config: RunnableConfig = {
        "run_name": "graph_chat",      # 识别日志和跟踪中的特定调用。不会被子调用继承
        "tags": ["chat", "graph"],     # 所有子调用继承的标签，用于调试工具中的过滤和组织
        "metadata": {"conversation_id": conversation_id},     # 自定义键值对，用于跟踪附加上下文，并由所有子调用继承
        "callbacks": [usage_callback], # 用于监控和响应执行过程中事件的处理器
        "configurable": {
            "thread_id": conversation_id,
            "conversation_id": conversation_id,
            # "rsa_model": "gpt-5-nano",
            # "rsa_model_provider": "openai",
            # "rsa_api_key": "sk-xxxxxx",
            # "rsa_base_url": "",
        },
    }

    
    async with (
        AsyncPostgresStore.from_conn_string(Settings.db_settings.POSTGRES_DATABASE_URI) as store,
        AsyncPostgresSaver.from_conn_string(Settings.db_settings.POSTGRES_DATABASE_URI) as checkpointer
    ):
        # 第一次启动初始化检查点
        await store.setup()
        await checkpointer.setup()
        
        class MessagesState(TypedDict):
            messages: Annotated[list[AnyMessage], operator.add]
            llm_calls: int
        
        async def llm_node(
            state: MessagesState,
            config: RunnableConfig,
            *,
            store: BaseStore,
        ):
            """LLM decides whether to call a tool or not"""

            messages = state["messages"]
            last_message = messages[-1]
            llm_calls = state.get("llm_calls", 0)
            logger.info(f"LLM call with {len(messages)} messages, last_message: {last_message if messages else None}, llm_calls so far: {llm_calls}")

            # 截断消息历史
            messages = trim_messages(
                state["messages"],
                max_tokens=8000,
                token_counter=count_tokens_approximately,
                strategy="last",
                allow_partial=False,
                start_on="human",
                end_on=("human", "tool"),
            )
            
            conversation_id = config["configurable"]["conversation_id"]
            namespace = ("memories", conversation_id)
            memories = await store.asearch(namespace, query=str(last_message.content), limit=2)
            info = "\n".join([d.value["data"] for d in memories])
            system_msg = f"{system_prompt} \n {info}"
            system_message = SystemMessage(content=system_msg)

            # Store new memories if the user asks the model to remember  
            await store.aput(namespace, str(id_generator.next_id()), {"data": input})

            ai_message = await llm_with_tools.ainvoke(
                input=[system_message] + messages
            )
            logger.info(f"LLM generated message: {ai_message}")
            
            return {
                "messages": [ai_message],
                "llm_calls": llm_calls + 1
            }


        async def tool_node(state: dict):
            """Performs the tool call"""

            result = []
            tool_calls = state["messages"][-1].tool_calls
            logger.info(f"Tool calls: {tool_calls}")
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool = tools_by_name[tool_name]
                observation = await tool.ainvoke(tool_call["args"])
                result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
                logger.info(f"{tool_name} call result: {observation}")
            return {"messages": result}


        # Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
        async def should_continue(state: MessagesState) -> Literal["tool_node", END]:
            """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

            messages = state["messages"]
            last_message = messages[-1]
            # If the LLM makes a tool call, then perform an action
            if last_message.tool_calls:
                return "tool_node"
            # Otherwise, we stop (reply to the user)
            return END


        # Build workflow
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("llm_node", llm_node)
        agent_builder.add_node("tool_node", tool_node)

        # Add edges to connect nodes
        agent_builder.add_edge(START, "llm_node")
        agent_builder.add_conditional_edges(
            "llm_node",
            should_continue,
            ["tool_node", END]
        )
        agent_builder.add_edge("tool_node", "llm_node")

        # Compile the agent
        agent = agent_builder.compile(
            checkpointer=checkpointer,
            store=store,
        )

        # Show the agent
        # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

        
        if streaming:
            # async for chunk in agent.astream(
            #     input={"messages": [human_message]},
            #     config=runnable_config,
            #     stream_mode="values" # values:以完整响应块流式传输, messages:以token流式传输，updates:分步骤输出
            # ):
            #     logger.info(f"Agent response chunk: {chunk}")
                
            #     content = ""
            #     # Each chunk contains the full state at that point
            #     latest_message = chunk["messages"][-1]
            #     logger.info(f"Agent response message: {latest_message}")
            #     if latest_message.content:
            #         content = latest_message.content
            #         logger.info(f"Agent response content: {content}")
            #     elif latest_message.tool_calls:
            #         logger.info(f"Agent calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")

            #     # token 使用量
            #     # usage_callback.usage_metadata
            
            #     result = {"content": content, "conversation_id": conversation_id}
            #     yield json.dumps(result, ensure_ascii=False)
                
                
            # async for chunk in agent.astream(
            #     input={"messages": [human_message]},
            #     config=runnable_config,
            #     stream_mode="updates" # updates:分步骤输出
            # ):
            #     logger.info(f"Agent response chunk: {chunk}")
                
            #     content = ""
            #     for step, data in chunk.items():
            #         logger.debug(f"step: {step}")
            #         logger.debug(f"data: {data}")
            #         # logger.info(f"content: {data['messages'][-1].content_blocks}")
                    
            #         latest_message = data["messages"][-1]
            #         if step == "agent":
            #             content = latest_message.content
            #             logger.debug(f"Agent response content: {content}")
            #         elif step == "tools":
            #             logger.debug(f"Tool response content: {latest_message.content}, tool name:{latest_message.name}")

            #     result = {"content": content, "conversation_id": conversation_id}
            #     yield json.dumps(result, ensure_ascii=False)    
            
            async for token, metadata in agent.astream(
                input={"messages": [human_message]},
                config=runnable_config,
                stream_mode="messages", # messages:以token流式传输
            ):
                logger.info(f"Agent response token: {token}")
                logger.info(f"Agent response metadata: {metadata}")
                
                content = ""
                node = metadata.get("langgraph_node", "unknown")
                logger.debug(f"node: {node}")
                # logger.debug(f"content: {token.content_blocks}")
                
                if node == "llm_node":
                    content = token.content
                    logger.debug(f"Agent response content: {content}")
                    if hasattr(token, 'tool_call_chunks') and token.tool_call_chunks:
                        tool_call = token.tool_call_chunks[-1]
                        if tool_call.get('name'):
                            logger.debug(f"Agent calling tool: {tool_call.get('name')}")
                        elif tool_call.get('args'):
                            logger.debug(f"Agent calling tool with args: {tool_call.get('args')}")
                    if hasattr(token, 'usage_metadata') and token.usage_metadata:
                        logger.debug(f"Token usage metadata: {token.usage_metadata}")
                    if hasattr(token, 'additional_kwargs') and token.additional_kwargs:
                        logger.debug(f"Agent response reasoning content: {token.additional_kwargs.get('reasoning_content')}")
                elif node == "tool_node":
                    logger.debug(f"Tool response content: {token.content}")

                result = {"content": content, "conversation_id": conversation_id}
                logger.debug(f"Graph stream response result: {result}")
                yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n".encode('utf-8')            
        else:
            response = await agent.ainvoke(
                input={"messages": [human_message]},
                config=runnable_config
            )
            # print(response.content_blocks)

            result = {"content": response.get("content"), "conversation_id": conversation_id}
            yield json.dumps(result, ensure_ascii=False)


async def async_chat_graph_summary(data: ChatRequest):
    model_provider = data.model_provider
    model_name = data.model_name
    streaming = data.streaming or True
    
    input = data.input
    conversation_id = data.conversation_id

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
    tools_by_name = {tool.name: tool for tool in tools}

    # 聊天模型
    chat_model = ModelFactory.get_model(model_provider, model_name, streaming, [])
    # 绑定工具
    # tool_choice "auto":模型自动决定是否调用工具, "none":不调用工具, "any/required":至少调用一个工具
    llm_with_tools = chat_model.bind_tools(tools, tool_choice="auto")
    
    usage_callback = UsageMetadataCallbackHandler()

    human_message = HumanMessage(content=input)
    system_message = SystemMessage(content=system_prompt)

    #运行时可配置项
    runnable_config: RunnableConfig = {
        "run_name": "graph_chat",      # 识别日志和跟踪中的特定调用。不会被子调用继承
        "tags": ["chat", "graph"],     # 所有子调用继承的标签，用于调试工具中的过滤和组织
        "metadata": {"conversation_id": conversation_id},     # 自定义键值对，用于跟踪附加上下文，并由所有子调用继承
        "callbacks": [usage_callback], # 用于监控和响应执行过程中事件的处理器
        "configurable": {
            "thread_id": conversation_id,
            "conversation_id": conversation_id,
            # "rsa_model": "gpt-5-nano",
            # "rsa_model_provider": "openai",
            # "rsa_api_key": "sk-xxxxxx",
            # "rsa_base_url": "",
        },
    }
    
    async with (
        AsyncPostgresSaver.from_conn_string(Settings.db_settings.POSTGRES_DATABASE_URI) as checkpointer
    ):
        # 第一次启动初始化检查点
        await checkpointer.setup()
        
        class MessagesState(TypedDict):
            messages: Annotated[list[AnyMessage], operator.add]
            context: dict[str, RunningSummary]
            llm_calls: int
        
        class LLMInputState(TypedDict):  
            summarized_messages: list[AnyMessage]
            context: dict[str, RunningSummary]
            llm_calls: int

        async def llm_node(
            state: LLMInputState
        ):
            """LLM decides whether to call a tool or not"""

            # messages = state["messages"]
            # last_message = messages[-1]
            # llm_calls = state.get("llm_calls", 0)
            # logger.info(f"LLM call with {len(messages)} messages, last_message: {last_message if messages else None}, llm_calls so far: {llm_calls}")

            llm_calls = state.get("llm_calls", 0)
            summarized_messages = state["summarized_messages"]
            logger.info(f"LLM call with summarized messages {summarized_messages} ")

            ai_message = await llm_with_tools.ainvoke(
                input=[system_message] + summarized_messages
            )
            logger.info(f"LLM generated message: {ai_message}")
            
            return {
                "messages": [ai_message],
                "llm_calls": llm_calls + 1
            }

        async def tool_node(state: dict):
            """Performs the tool call"""

            result = []
            tool_calls = state["messages"][-1].tool_calls
            logger.info(f"Tool calls: {tool_calls}")
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool = tools_by_name[tool_name]
                observation = await tool.ainvoke(tool_call["args"])
                result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
                logger.info(f"{tool_name} call result: {observation}")
            return {"messages": result}

        # Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
        async def should_continue(state: MessagesState) -> Literal["tool_node", END]:
            """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

            messages = state["messages"]
            last_message = messages[-1]
            # If the LLM makes a tool call, then perform an action
            if last_message.tool_calls:
                return "tool_node"
            # Otherwise, we stop (reply to the user)
            return END

        async def preprocess_node(state: MessagesState):
            """Preprocess messages to add IDs if they are missing."""
            processed_messages = []
            for msg in state["messages"]:
                if not hasattr(msg, "id") or msg.id is None:
                    msg.id = str(id_generator.next_id())
                processed_messages.append(msg)
            return {"messages": processed_messages}

        summarization_node = SummarizationNode(
            model=chat_model,
            token_counter=count_tokens_approximately,
            max_tokens=2000,
            max_tokens_before_summary=2000,
            max_summary_tokens=500,
        )

        # Build workflow
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("llm_node", llm_node)
        agent_builder.add_node("tool_node", tool_node)
        agent_builder.add_node("preprocess", preprocess_node)
        agent_builder.add_node("summarize", summarization_node)

        # Add edges to connect nodes
        agent_builder.add_edge(START, "preprocess")
        agent_builder.add_edge("preprocess", "summarize")
        agent_builder.add_edge("summarize", "llm_node")
        agent_builder.add_conditional_edges(
            "llm_node",
            should_continue,
            ["tool_node", END]
        )
        agent_builder.add_edge("tool_node", "llm_node")

        # Compile the agent
        agent = agent_builder.compile(
            checkpointer=checkpointer
        )

        # Show the agent
        # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

        
        if streaming:
            # async for chunk in agent.astream(
            #     input={"messages": [human_message]},
            #     config=runnable_config,
            #     stream_mode="values" # values:以完整响应块流式传输, messages:以token流式传输，updates:分步骤输出
            # ):
            #     logger.info(f"Agent response chunk: {chunk}")
                
            #     content = ""
            #     # Each chunk contains the full state at that point
            #     latest_message = chunk["messages"][-1]
            #     logger.info(f"Agent response message: {latest_message}")
            #     if latest_message.content:
            #         content = latest_message.content
            #         logger.info(f"Agent response content: {content}")
            #     elif latest_message.tool_calls:
            #         logger.info(f"Agent calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")

            #     # token 使用量
            #     # usage_callback.usage_metadata
            
            #     result = {"content": content, "conversation_id": conversation_id}
            #     yield json.dumps(result, ensure_ascii=False)
                
                
            # async for chunk in agent.astream(
            #     input={"messages": [human_message]},
            #     config=runnable_config,
            #     stream_mode="updates" # updates:分步骤输出
            # ):
            #     logger.info(f"Agent response chunk: {chunk}")
                
            #     content = ""
            #     for step, data in chunk.items():
            #         logger.debug(f"step: {step}")
            #         logger.debug(f"data: {data}")
            #         # logger.info(f"content: {data['messages'][-1].content_blocks}")
                    
            #         latest_message = data["messages"][-1]
            #         if step == "agent":
            #             content = latest_message.content
            #             logger.debug(f"Agent response content: {content}")
            #         elif step == "tools":
            #             logger.debug(f"Tool response content: {latest_message.content}, tool name:{latest_message.name}")

            #     result = {"content": content, "conversation_id": conversation_id}
            #     yield json.dumps(result, ensure_ascii=False)    
            
            async for token, metadata in agent.astream(
                input={"messages": [human_message]},
                config=runnable_config,
                stream_mode="messages", # messages:以token流式传输
            ):
                logger.info(f"Agent response token: {token}")
                logger.info(f"Agent response metadata: {metadata}")
                
                content = ""
                node = metadata.get("langgraph_node", "unknown")
                logger.debug(f"node: {node}")
                # logger.debug(f"content: {token.content_blocks}")
                
                if node == "llm_node":
                    content = token.content
                    logger.debug(f"Agent response content: {content}")
                    if hasattr(token, 'tool_call_chunks') and token.tool_call_chunks:
                        tool_call = token.tool_call_chunks[-1]
                        if tool_call.get('name'):
                            logger.debug(f"Agent calling tool: {tool_call.get('name')}")
                        elif tool_call.get('args'):
                            logger.debug(f"Agent calling tool with args: {tool_call.get('args')}")
                    if hasattr(token, 'usage_metadata') and token.usage_metadata:
                        logger.debug(f"Token usage metadata: {token.usage_metadata}")
                    if hasattr(token, 'additional_kwargs') and token.additional_kwargs:
                        logger.debug(f"Agent response reasoning content: {token.additional_kwargs.get('reasoning_content')}")
                elif node == "tool_node":
                    logger.debug(f"Tool response content: {token.content}")

                result = {"content": content, "conversation_id": conversation_id}
                logger.debug(f"Graph stream response result: {result}")
                yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n".encode('utf-8')            
        else:
            response = await agent.ainvoke(
                input={"messages": [human_message]},
                config=runnable_config
            )
            # print(response.content_blocks)

            result = {"content": response.get("content"), "conversation_id": conversation_id}
            yield json.dumps(result, ensure_ascii=False)


# def select_model(state: AgentState, runtime: Runtime) -> ChatOpenAI:
#     """Choose model based on conversation complexity."""
#     messages = state["messages"]
#     message_count = len(messages)

#     if message_count < 10:
#         return ChatOpenAI(model="gpt-4.1-mini").bind_tools(tools)
#     else:
#         return ChatOpenAI(model="gpt-5").bind_tools(tools) # Better model for longer conversations

# 动态系统提示
def dynamic_prompt(state):
    user_type = state.get("user_type", "standard")
    system_msg = SystemMessage(
        content="Provide detailed technical responses."
        if user_type == "expert"
        else "Provide simple, clear explanations."
    )
    return [system_msg] + state["messages"]

# 保留最近的消息以适应上下文窗口
def trim_messages_func(state, max_messages: int = 10, max_tokens: int = 8000):
    """智能截断消息历史"""
    messages = state["messages"]
    
    if len(messages) <= max_messages:
        return messages

    # 保留系统消息和最近的对话
    first_msg = messages[0]
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    recent_messages = messages[-max_messages//2:]
    
    # 计算token数量
    total_tokens = sum(len(str(msg.content)) for msg in recent_messages)
    
    # 如果仍然超过限制，进一步截断
    while total_tokens > max_tokens and len(recent_messages) > 2:
        recent_messages = recent_messages[1:]  # 移除最旧的消息
        total_tokens = sum(len(str(msg.content)) for msg in recent_messages)
    
    new_messages = [first_msg] + system_messages + recent_messages

    return new_messages

def smart_trim_messages(state):
    """智能截断消息历史"""
    new_messages = trim_messages_func(state)
    
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

def pre_model_hook(state):
    trimmed_messages = trim_messages(
        state["messages"],
        max_tokens=8000,
        token_counter=count_tokens_approximately,
        strategy="last",
        allow_partial=False,
        start_on="human",
        end_on=("human", "tool"),
    )
    return {"llm_input_messages": trimmed_messages}
