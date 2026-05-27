from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_swarm, create_handoff_tool
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI


from dotenv import load_dotenv  # 用于加载环境变量
load_dotenv()  # 加载 .env 文件中的环境变量


model = ChatDeepSeek(
            model="deepseek-chat",
            streaming=True,
            temperature=0.3, # 随机性：0.0（最确定）–1.0（最随机）
            # max_tokens=8000, # 最多返回多少 token
            max_retries=2,
            timeout=60,
        )


@tool
def book_hotel(hotel_name: str, days: int):
    """Book a hotel"""
    return f"成功预订了酒店：{hotel_name}，入住{days}天。"

@tool
def book_flight(from_airport: str, to_airport: str):
    """Book a flight"""
    return f"成功预订了机票从 {from_airport} 到 {to_airport}."

transfer_to_hotel_assistant = create_handoff_tool(
    agent_name="hotel_assistant",
    description="Transfer user to the hotel-booking assistant.",
)


transfer_to_flight_assistant = create_handoff_tool(
    agent_name="flight_assistant",
    description="Transfer user to the flight-booking assistant.",
)

flight_assistant = create_react_agent(
    model=model.bind_tools([book_flight, transfer_to_hotel_assistant], parallel_tool_calls=False),

    tools=[book_flight, transfer_to_hotel_assistant],
    # 有些大模型parallel_tool_calls=False可能不生效，为避免并发调用工具的错误，可以在提示词加上：一次只能调用一个工具，工具不能并发调用
    # Only one tool can be called at a time, and tools cannot be called in parallel
    prompt="You are a flight booking assistant, Only one tool can be called at a time, and tools cannot be called in parallel",
    name="flight_assistant"
)
hotel_assistant = create_react_agent(
    model=model.bind_tools([book_hotel, transfer_to_flight_assistant], parallel_tool_calls=False),

    tools=[book_hotel, transfer_to_flight_assistant],
    prompt="You are a hotel booking assistant, Only one tool can be called at a time, and tools cannot be called in parallel",
    name="hotel_assistant"
)

# 定义一个群体的智能体节点
swarm = create_swarm(
    agents=[flight_assistant, hotel_assistant],
    default_active_agent="flight_assistant"
).compile()

for chunk in swarm.stream(
    {
        "messages": [
            {
                "role": "user",
                "content": "帮我订一张机票从北京到广州，并且要住在香格里拉大酒店，3天行程"
            }
        ]
    }
):
    print(chunk)
    print("\n")