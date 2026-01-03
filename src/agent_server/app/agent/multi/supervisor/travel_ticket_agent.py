
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

from langchain_deepseek import ChatDeepSeek
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from langchain_core.tools import tool

from dotenv import load_dotenv  # 用于加载环境变量
load_dotenv()  # 加载 .env 文件中的环境变量

model = ChatDeepSeek(
            model="deepseek-reasoner",
            streaming=True,
            temperature=0.3, # 随机性：0.0（最确定）–1.0（最随机）
            max_tokens=8000, # 最多返回多少 token
            max_retries=2,
            timeout=60,
        )

@tool
def book_hotel(hotel_name: str):
    """Book a hotel"""
    return f"成功预订了酒店：{hotel_name}."

@tool
def book_flight(from_airport: str, to_airport: str):
    """Book a flight"""
    return f"成功预订了机票从 {from_airport} 到 {to_airport}."

# 机票预订智能体
flight_assistant = create_react_agent(
    model=model.bind_tools([book_flight]),
    tools=[book_flight],
    prompt="You are a flight booking assistant",
    name="flight_assistant"
)

# 酒店预订智能体
hotel_assistant = create_react_agent(
    model=model.bind_tools([book_hotel]),
    tools=[book_hotel],
    prompt="You are a hotel booking assistant",
    name="hotel_assistant"
)

# 创建一个监督者
supervisor = create_supervisor(
    agents=[flight_assistant, hotel_assistant],
    model=model,
    # full_history 全消息记录，last_message 最后智能体的输出
    output_mode="full_history",
    prompt=(
        """You are responsible for managing a hotel booking assistant and a flight booking assistant. 
        Please assign work tasks to them."""
    )
).compile()

for chunk in supervisor.stream(
    {
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