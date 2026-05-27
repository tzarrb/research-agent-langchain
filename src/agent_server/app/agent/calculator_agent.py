
import os
import sys
# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import json
import html
from typing import Any, AsyncGenerator
from functools import wraps

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool # 用于@tool装饰器
from langchain.agents import AgentExecutor # 核心的Agent执行器
from langchain.agents.format_scratchpad import format_to_openai_function_messages # 格式化中间步骤
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser # 解析LLM输出
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory,ConfigurableFieldSpec

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.schemas.chat.chat_request import ChatRequest
from agent_server.app.service.chat_service import get_message_history
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger

logger = build_logger("calculator-agent")

def parse_tool_input(func):
    """
    装饰器：自动解析工具输入参数
    处理ReAct模式下LLM传递的JSON字符串参数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 检查是否有参数
            if len(args) == 0:
                logger.warning("没有传入参数，使用默认值")
                raise ValueError(f"没有传入参数: {args}")
            
            first_arg = args[0]
            
            # 如果第一个参数是字符串，尝试解析为JSON
            if isinstance(first_arg, str):
                try:
                    # 尝试解析JSON字符串
                    parsed_data = json.loads(first_arg)
                    if isinstance(parsed_data, dict):
                        # 如果解析成功且是字典，使用字典中的值
                        logger.info(f"解析JSON参数: {parsed_data}")
                        a = float(parsed_data.get('a', 0))
                        b = float(parsed_data.get('b', args[1] if len(args) > 1 else 0))
                        return func(a, b)
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning(f"JSON解析失败，尝试直接转换: {e}")
                    # JSON解析失败，尝试直接转换为数值
                    try:
                        a = float(first_arg)
                        b = float(args[1]) if len(args) > 1 else 0
                        return func(a, b)
                    except (ValueError, IndexError) as convert_error:
                        logger.error(f"参数转换失败: args={args}, error={convert_error}")
                        raise ValueError(f"无法解析参数: {first_arg}")
            
            # 正常的数值参数调用
            return func(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"工具调用错误 {func.__name__}: {e}, args={args}, kwargs={kwargs}")
            raise
    
    return wrapper

# 定义工具函数
@tool(description="将两个数字相加并返回结果。")
@parse_tool_input
def add(a: float, b: float):
    """
    将两个数字相加并返回结果。
    
    参数:
    a (float): 第一个数字
    b (float): 第二个数字（默认为0）
    
    示例:
    - add(2, 3) 返回 5
    - add('{"a": 2, "b": 3}') 返回 5 (ReAct模式)
    """
    result = a + b
    logger.info(f"执行加法: {a} + {b} = {result}")
    return result

@tool(description="将两个数字相减并返回结果。")
@parse_tool_input
def subtract(a: float, b: float):
    """
    将两个数字相减并返回结果。
    
    参数:
    a (float): 被减数
    b (float): 减数（默认为0）
    
    示例:
    - subtract(5, 2) 返回 3
    - subtract('{"a": 5, "b": 2}') 返回 3 (ReAct模式)
    """
    result = a - b
    logger.info(f"执行减法: {a} - {b} = {result}")
    return result

@tool(description="将两个数字相乘并返回结果。")
@parse_tool_input
def multiply(a: float, b: float):
    """
    将两个数字相乘并返回结果。
    
    参数:
    a (float): 第一个数字
    b (float): 第二个数字（默认为1）
    
    示例:
    - multiply(2, 3) 返回 6
    - multiply('{"a": 2, "b": 3}') 返回 6 (ReAct模式)
    """
    result = a * b
    logger.info(f"执行乘法: {a} × {b} = {result}")
    return result

@tool(description="将两个数字相除并返回结果。")
@parse_tool_input
def divide(a: float, b: float) -> float:
    """
    将两个数字相除并返回结果。
    
    参数:
    a (float): 被除数
    b (float): 除数（默认为1）
    
    示例:
    - divide(6, 3) 返回 2.0
    - divide('{"a": 6, "b": 3}') 返回 2.0 (ReAct模式)
    """
    if b == 0:
        logger.error("除零错误")
        raise ValueError("除数不能为零")
    result = a / b
    logger.info(f"执行除法: {a} ÷ {b} = {result}")
    return result

# 定义工具列表
tools = [add, subtract, multiply, divide] # 将工具列表传入

# 定义 Agent 的提示模板
# MessagesPlaceholder("agent_scratchpad") 是关键，它会插入LLM的思考过程和工具执行结果
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个数学助手，可以使用工具进行加法和乘法运算。"),
    MessagesPlaceholder(variable_name="chat_history"), # 可以选择性加入聊天历史
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"), # LLM的思考过程和工具输出会填充这里
])

async def calculator_run(data: ChatRequest):
    """
    执行计算 Agent
    :param input: 用户输入的数学表达式
    :param chat_history: 聊天历史记录
    :return: Agent 的响应结果
    """
    streaming = data.streaming
    thinking = data.enableThink
    
    input = data.input
    conversation_id = data.conversation_id

    # 获取模型提供商和模型名称
    model_provider = data.model_provider or Settings.model_settings.DEFAULT_LLM_PLATFORM
    model_name = data.model_name or Settings.model_settings.DEFAULT_LLM_MODEL

    llm = ModelFactory.get_model(model_provider, model_name, streaming)

    # 检查模型是否支持工具绑定（主要是 OpenAI 兼容的模型）
    if thinking and hasattr(llm, "bind_tools"):
        system_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个数学助手，专门用于进行数学计算。你有以下工具可以使用：
            
            可用工具：
            {tools}
            
            严格安全规则：
            调用工具时，请确保参数是独立的数字，不要将多个参数组合成字符串。如：正确的调用是 add(2, 3)，错误的调用是 add("a=2, b=3")

            当用户提出数学问题时，你必须使用这些工具来计算，而不是直接给出答案。
            请一步一步地使用工具完成计算。"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 将LLM绑定到工具 (这是 OpenAI Function Calling 的核心)
        llm_with_tools = llm.bind_tools(                               
            tools,
            tool_choice="auto",  # 让模型自动选择工具
            strict=True  # 如果模型支持，启用严格模式
        )

        # 构建 Agent 核心逻辑 (LCEL 链)
        step_runnable = RunnablePassthrough.assign(
            agent_scratchpad=lambda x: format_to_openai_function_messages(x["intermediate_steps"]),
            tools=lambda x: "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        )
        agent_runnable = step_runnable | system_prompt | llm_with_tools | OpenAIFunctionsAgentOutputParser()

    else:
        # 对于不支持函数调用的模型，使用传统的 Agent 方式
        from langchain.agents import create_react_agent,create_structured_chat_agent
        
        # 修改 prompt 以适应 ReAct 格式
        react_template = """
            你是一个计算器助手，必须使用工具来进行计算。

            可用工具：
            {tools}
            
            请严格按照以下格式回答：
            Question: 用户的问题
            Thought: 我需要分析这个问题并决定使用哪个工具
            Action: 要使用的工具名称，必须是 [{tool_names}] 中的一个
            Action Input: 工具的输入参数
            Observation: 工具执行的结果
            ... (可以重复 Thought/Action/Action Input/Observation)
            Thought: 我现在知道最终答案了
            Final Answer: 最终答案

            严格安全规则 - 必须遵守:
            - 对于数学计算，你必须使用工具，不能直接计算！
            - Action Input 必须是有效的JSON格式，例如 {{"a": 数字, "b": 数字}}，不要使用字符串格式如 "a=数字, b=数字"
            - 数字参数不要加引号
            - 对于多步骤问题，你必须完成所有步骤才能给出Final Answer
            - 每次使用工具后，检查是否还有未完成的计算步骤
            - 只有当所有计算都完成后，才能给出Final Answer

            示例：
            示例1：
            Question: 2加3等于多少？
            Thought: 我需要使用add工具
            Action: add
            Action Input: {{"a": 2, "b": 3}}
            Observation: 5
            Thought: 我现在知道最终答案了，2加3等于5
            Final Answer: 2加3等于5
            
            示例2：
            Question: 2加3，再乘以4等于多少？
            Thought: 这是一个多步骤问题。首先，我需要计算2加3，使用add工具。然后，将结果乘以4，使用multiply工具。
            Action: add
            Action Input: {{"a": 2, "b": 3}}
            Observation: 5
            Action: multiply
            Action Input: {{"a": 5, "b": 4}}
            Observation: 20
            Thought: 我现在知道最终答案了，结果等于20
            Final Answer: 20
    
            开始!
            
            Question: {input}
            Thought: {agent_scratchpad}
        """
        react_prompt = ChatPromptTemplate.from_messages([
            ("system", react_template),
            MessagesPlaceholder(variable_name="chat_history"),
        ])
        
        # 创建 ReAct Agent
        agent_runnable = create_react_agent(llm, tools, react_prompt)
        
        # # 提示词，直接从langchain hub上下载，因为写这个ReAct机制的prompt比较复杂，直接用现成的。
        # prompt = hub.pull("hwchase17/structured-chat-agent")
        # # 定义AI Agent
        # agent = create_structured_chat_agent(
        #     llm=llm,
        #     tools=tools,
        #     prompt=prompt
        # )

        # # 使用Memory记录上下文
        # memory = ConversationBufferMemory(
        #     memory_key='chat_history',
        #     return_messages=True
        # )

        # # 定义AgentExecutor，必须使用AgentExecutor，才能执行代理定义的工具
        # agent_executor = AgentExecutor.from_agent_and_tools(
        #     agent=agent, tools=tools, memory=memory, verbose=True, handle_parsing_errors=True
        # )
        
    # 创建 AgentExecutor 
    base_agent_executor = AgentExecutor(
        agent=agent_runnable, 
        tools=tools, 
        verbose=True,
        max_iterations=10,  # 增加最大迭代次数
        early_stopping_method="generate",  # 设置早停策略
        handle_parsing_errors=True  # 处理解析错误
    )

    # 用 RunnableWithMessageHistory 包装整个 AgentExecutor
    # 这样可以确保 conversation_id 配置正确传递到所有组件
    agent_executor = RunnableWithMessageHistory(
            base_agent_executor,
            get_message_history,
            input_messages_key="input",
            history_messages_key="chat_history",  # 与 Prompt 中的 placeholder 对应
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
    
    from langchain_core.runnables import RunnableConfig
    config = RunnableConfig(configurable={"conversation_id": conversation_id})

    try:
        if streaming:
            #  异步流式输出（建议放在 async 函数中调用）:RunnableConfig
            async for chunk in agent_executor.astream(
                {"input": input},
                config=config
            ):
                # logger.info(f"conversation_id: {conversation_id}, chat stream: {html.escape(str(chunk))}")
                # print(chunk, end="", flush=True)
                # response={"content":chunk, "conversation_id": conversation_id}    
    
                # 普通对话链返回的是字符串
                response = chunk if isinstance(chunk, str) else str(chunk)
                response = json.dumps(response, ensure_ascii=False)
                
                logger.info(f"\n conversation_id: {conversation_id}, chat response: {response}")
                yield response
        else:
            # Use async invocation with proper configuration
            response = await agent_executor.ainvoke(
                {"input": input},
                config=config
            )
            logger.info(f"conversation_id: {conversation_id}, chat result: {response}")
            # response={"content":result, "conversation_id": conversation_id}
            yield json.dumps(response, ensure_ascii=False)

        # await save_chat_conversation(input, int(conversation_id))
    except Exception as e:
        # Handle errors appropriately
        logger.error(f"Error in chat processing: {html.escape(str(e))}")
        raise  # Or return a custom error response



if __name__ == "__main__":
    import asyncio
    
    async def test_calculator():
        # 测试 Agent
        input = "2加3 等于多少，再将结果乘以4?"
        conversation_id = "test_conversation_123"
        
        data = ChatRequest(
            input=input,
            conversation_id=conversation_id,
            streaming=False,
            model_provider="deepseek",  # 使用支持工具的模型
            model_name="deepseek-reasoner",
            enableLocal=False,
            enableWeb=False,
            enableThink=False
        )
        # 执行 Agent
        async for response in calculator_run(data):
            # 打印结果
            print("Agent Response:", response)
    
    # 运行异步测试函数
    asyncio.run(test_calculator())
