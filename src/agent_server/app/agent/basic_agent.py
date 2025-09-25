
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

from langchain.agents import create_agent, AgentState, ToolNode
from langgraph.runtime import Runtime
from langchain_tavily import TavilySearch

from langchain_core.tools import tool
from langchain_core.callbacks import UsageMetadataCallbackHandler, usage
from langchain_core.runnables import RunnableConfig

from langchain_core.messages import RemoveMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES, MessagesState, add_messages 
from langgraph.checkpoint.memory import InMemorySaver
# from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.memory import InMemoryStore
from langgraph.config import get_store
from langgraph.graph import StateGraph, START, END

#表示基本的聊天历史记录和内存存储的聊天历史记录
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
#该类用于将聊天模型与聊天历史记录结合在一起
from langchain_core.runnables import RunnableWithMessageHistory,ConfigurableFieldSpec

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger
from agent_server.utils.id_util import id_generator
from agent_server.schemas.chat.chat_request import ChatRequest
# from agent_server.app.rag.vector_store.base import VsServiceFactory, SupportedVSType

from agent_server.schemas.chat.chat_conversation_schema import ChatConversationCreate
from agent_server.db.models.chat_conversation_model import ChatConversation
from agent_server.db.repository.chat_conversation_repository import chat_conversation_repository
from agent_server.db.base import get_async_db, _AsyncSessionFactory
from agent_server.core.exceptions import NotFoundException, UnauthorizedException

logger = build_logger("basic-agent")

SYSTEM_PROMPT = """
    你是一位乐于助人的 AI问答助手, 请根据用户的问题以及上下文信息回答问题。
    如果匹配到合适的工具则调用工具获取信息, 并将工具返回的信息作为回答的一部分。
    如果没有匹配到合适的工具, 则直接根据已有信息回答问题。
    如果你不确定答案, 请说你不知道, 不要编造信息。
    请使用简体中文回答。
    """

# 网络搜索工具
search_tool = TavilySearch(
    max_results=5,
    topic="general",
    tavily_api_key=Settings.basic_settings.TAVILY_API_KEY
)


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
    try:
        logger.info("Starting async_chat_agent...")
        async for chunk in async_chat_agent(data):
            yield chunk
        logger.info("async_chat_agent completed successfully")
    except NotFoundException as e:
        logger.error(f"Model not found: {str(e)}")
        error_result = {
            "error": "Model not found",
            "message": str(e),
            "conversation_id": data.conversation_id
        }
        yield json.dumps(error_result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Unexpected error in chat_async: {str(e)}", exc_info=True)
        error_result = {
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "conversation_id": data.conversation_id
        }
        yield json.dumps(error_result, ensure_ascii=False)

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

async def async_chat_agent(data: ChatRequest):
    model_provider = data.model_provider
    model_name = data.model_name
    streaming = data.streaming or True
    
    input = data.input
    conversation_id = data.conversation_id

    system_prompt = data.system or SYSTEM_PROMPT
    
    # 聊天模型
    chat_model = ModelFactory.get_model(model_provider, model_name, streaming, [])
    
    # 工具
    tools = [get_weather]
    if data.enableWeb:
        tools.append(search_tool)

    # 工具节点
    tool_node = ToolNode(
        tools=tools,
        handle_tool_errors="Please check your input and try again."
    )

    usage_callback = UsageMetadataCallbackHandler()

    human_messages = HumanMessage(content=[
        {"type": "text", "text": "Hello, how are you?"},
        {"type": "image_url", "image_url": {"url": "https://avatars.githubusercontent.com/u/7997078?v=4"}}
    ])
    
    human_message = HumanMessage(content=input)
    system_message = SystemMessage(content=system_prompt)

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

    # 创建智能体 
    agent = create_agent(
        chat_model,
        tools=tools,
        prompt=system_message,
        pre_model_hook=trim_messages,
        checkpointer=InMemorySaver(),
    )
    
    if streaming:
        # stream_mode : values:以完整响应块流式输出，updates:分步骤输出, messages:以token流式输出
        async for chunk in agent.astream(
            input={"messages": [human_message]},
            config=runnable_config,
            stream_mode="values" # values:以完整响应块流式传输
        ):
            logger.info(f"Agent response chunk: {chunk}")
            
            content = ""
            # Each chunk contains the full state at that point
            latest_message = chunk["messages"][-1]
            logger.info(f"Agent response message: {latest_message}")
            if latest_message.content:
                content = latest_message.content
                logger.info(f"Agent response content: {content}")
            elif latest_message.tool_calls:
                logger.info(f"Agent calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")

            # token 使用量
            # usage_callback.usage_metadata
        
            result = {"content": content, "conversation_id": conversation_id}
            # yield json.dumps(result, ensure_ascii=False)
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n".encode('utf-8')
            
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
        # async for token, metadata in agent.astream(
        #     input={"messages": [human_message]},
        #     config=runnable_config,
        #     stream_mode="messages", # messages:以token流式传输
        # ):
        #     logger.info(f"Agent response token: {token}")
        #     logger.info(f"Agent response metadata: {metadata}")
            
        #     node = metadata.get("langgraph_node", "unknown")
        #     logger.debug(f"node: {node}")
        #     # logger.debug(f"content: {token.content_blocks}")
            
        #     content = ""
        #     if node == "agent":
        #         content = token.content
        #         logger.debug(f"Agent response content: {content}")
        #         if hasattr(token, 'tool_call_chunks') and token.tool_call_chunks:
        #             tool_call = token.tool_call_chunks[-1]
        #             if tool_call.get('name'):
        #                 logger.debug(f"Agent calling tool: {tool_call.get('name')}")
        #             elif tool_call.get('args'):
        #                 logger.debug(f"Agent calling tool with args: {tool_call.get('args')}")
        #     elif node == "tools":
        #         logger.debug(f"Tool response content: {token.content}")

        #     result = {"content": content, "conversation_id": conversation_id}
        #     logger.debug(f"Agent stream response result: {result}")
        #     # yield json.dumps(result, ensure_ascii=False)
        #     yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n".encode('utf-8')
            
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

    system_prompt = data.system or SYSTEM_PROMPT
    
    # 工具
    tools = [get_weather]
    if data.enableWeb:
        tools.append(search_tool)
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
            "conversation_id": conversation_id,
            # "rsa_model": "gpt-5-nano",
            # "rsa_model_provider": "openai",
            # "rsa_api_key": "sk-xxxxxx",
            # "rsa_base_url": "",
        },
    }

    class MessagesState(TypedDict):
        messages: Annotated[list[AnyMessage], operator.add]
        llm_calls: int
    
    def llm_node(state: MessagesState):
        """LLM decides whether to call a tool or not"""

        messages = state["messages"]
        llm_calls = state.get("llm_calls", 0)
        logger.info(f"LLM call with {len(messages)} messages, last_message: {messages[-1] if messages else None}, llm_calls so far: {llm_calls}")
        
        ai_message = llm_with_tools.invoke(
                    input=[system_message] + messages,
                    config=runnable_config
                )
        logger.info(f"LLM generated message: {ai_message}")
        
        return {
            "messages": [
                ai_message
            ],
            "llm_calls": llm_calls + 1
        }


    def tool_node(state: dict):
        """Performs the tool call"""

        result = []
        tool_calls = state["messages"][-1].tool_calls
        logger.info(f"Tool calls: {tool_calls}")
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool = tools_by_name[tool_name]
            observation = tool.invoke(tool_call["args"])
            result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
            logger.info(f"{tool_name} call result: {observation}")
        return {"messages": result}


    # Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
    def should_continue(state: MessagesState) -> Literal["tool_node", END]:
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
    agent = agent_builder.compile()

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
def trim_messages(state):
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 20:
        return {"messages": messages}

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

@tool(description="Search for information")
def search_info(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

class WeatherQuery(BaseModel):
    city: str = Field(description="城市名称")
    start: int = Field(description="起始时间(-1:昨天, 0:今天, 1:明天)", default=0)
    days: int = Field(description="查询天数", default=1)

@tool(description="Get the current weather in a given city", args_schema=WeatherQuery)
def get_weather(city: str, start: int, days: int, config: RunnableConfig) -> str:
    """
       查询城市天气实时或预报函数
       :param city: 必要参数，字符串类型，用于表示查询天气的具体城市名称，start:起始时间(-1:昨天, 0:今天, 1:明天), days:查询天数
       :return：心知天气 API查询即时天气的结果
       返回结果对象类型为解析之后的JSON格式对象，并用字符串形式进行表示，其中包含了全部重要的天气信息
       示例：
       北京实时天气预报
       https://api.seniverse.com/v3/weather/now.json?key=your_api_key&location=beijing&language=zh-Hans&unit=c
       北京今天和未来 4 天的预报
       https://api.seniverse.com/v3/weather/daily.json?key=your_api_key&location=beijing&language=zh-Hans&unit=c&start=0&days=5
    """
    
    conversation_id = config["configurable"].get("conversation_id")
    logger.info(f"get_weather called for conversation_id: {conversation_id}, city: {city}, start:{start}, days:{days}")
    
    # return f"It's sunny in {city}."
    
    url = Settings.basic_settings.WEATHER_SENIVERSE_URL
    params = {
        "key": Settings.basic_settings.WEATHER_SENIVERSE_KEY,
        "location": city,
        "start": start,
        "days": days,
        "language": "zh-Hans",
        "unit": "c",
    }
    response = requests.get(url, params=params)
    temperature = response.json()
    return temperature['results'][0]['daily']
