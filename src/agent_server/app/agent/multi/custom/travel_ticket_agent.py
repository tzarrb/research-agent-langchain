from typing import Annotated

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.types import Command
from langchain_deepseek import ChatDeepSeek

from dotenv import load_dotenv  # 用于加载环境变量
load_dotenv()  # 加载 .env 文件中的环境变量

from langchain.globals import set_debug
from langchain.globals import set_verbose

set_debug(True)
set_verbose(False)

# from agent_server.app.llm.mode_factory import ModelFactory
# from agent_server.config.settings import Settings
# from agent_server.utils.log_util import build_logger
# from agent_server.utils.id_util import id_generator
# from agent_server.schemas.chat.chat_request import ChatRequest


# 这里需要选择推理的大模型：如 gpt-4o或deepseek-reasoner，而不是聊天模型如deepseek-chat，聊天模型有时无法理解智能体之间的转移和回答逻辑
model = ChatDeepSeek(
            model="deepseek-chat",
            streaming=True,
            temperature=0.6, # 随机性：0.0（最确定）–1.0（最随机）
            max_tokens=8000, # 最多返回多少 token
            max_retries=2,
            timeout=60,
        )

# 创建一个工具handoff,用于智能体的转移
def create_handoff_tool(*, agent_name: str, description: str | None = None):
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer to {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            goto=agent_name,
            update={"messages": state["messages"] + [tool_message]},
            graph=Command.PARENT,
        )
    return handoff_tool

# 创建Handoffs工具
transfer_to_hotel_assistant = create_handoff_tool(agent_name="hotel_assistant")
transfer_to_flight_assistant = create_handoff_tool(agent_name="flight_assistant")

@tool
def book_hotel(hotel_name: str):
    """Book a hotel"""
    return f"成功预订了酒店： {hotel_name}."
@tool
def book_flight(from_airport: str, to_airport: str):
    """Book a flight"""
    return f"成功预订了机票从 {from_airport} 到 {to_airport}."

# 机票预订智能体
flight_assistant = create_react_agent(
    # parallel_tool_calls = False, 设置大模型不要并发调用工具，并发调用可能会导致以下错误：
    # ValueError: Found AIMessages with tool_calls that do not have a corresponding ToolMessage.
    model=model.bind_tools([book_flight, transfer_to_hotel_assistant],parallel_tool_calls=False),
    # 绑定两个工具，transfer_to_hotel_assistant 决定当前智能体大模型可以根据需要转移到酒店预订智能体
    tools=[book_flight, transfer_to_hotel_assistant],
    prompt="You are a flight booking assistant",
    name="flight_assistant"
)

# 酒店预订智能体
hotel_assistant = create_react_agent(
    model=model.bind_tools([book_hotel, transfer_to_flight_assistant],parallel_tool_calls=False),
    tools=[book_hotel, transfer_to_flight_assistant],
    prompt="You are a hotel booking assistant",
    name="hotel_assistant"
)

# 定义多智能体图流程
multi_agent_graph = (
    StateGraph(MessagesState)
    .add_node(flight_assistant)
    .add_node(hotel_assistant)
    .add_edge(START, "flight_assistant")
    .compile()
)

for chunk in multi_agent_graph.stream({
        "messages": [
            {
                "role": "user",
                "content": "帮我订一张机票从北京到广州，并且要住在香格里拉大酒店"
            }
        ]
    }
):
    print(chunk)
    print("\n")