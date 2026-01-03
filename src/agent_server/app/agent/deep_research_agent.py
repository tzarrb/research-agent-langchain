import os
import sys
# 把 src 加入 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
print("Current sys.path = ", sys.path)

import asyncio
import time
import random
import operator
import json

from typing import Annotated,List,Generator
from typing_extensions import TypedDict
from dotenv import load_dotenv
from functools import partial

from langchain_core.messages import BaseMessage,HumanMessage,AIMessage,ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.config import get_stream_writer
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from langchain_tavily import TavilySearch
from langchain_tavily._utilities import TavilySearchAPIWrapper

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger
from agent_server.utils.basic_util import get_today_str

from agent_server.app.tool.datetime_tool import current_datetime
from agent_server.app.tool.search_tool import search_tool

logger = build_logger("deep-research-agent")

llm = ModelFactory.get_model(model_name="deepseek-chat")

tools = [current_datetime, search_tool]

# def add_messages(left: list[BaseMessage], right: list[BaseMessage], k: int = 10) -> list[BaseMessage]:
#     """将新消息列表追加到旧消息列表中"""
#     full_list = left + right
#     return full_list[-k:]

class ResearchState(TypedDict):
    # messages: Annotated[list[BaseMessage], partial(add_messages, k=10)]
    messages: Annotated[list[BaseMessage], operator.add]
    search_results: list | None
    draft_report: str | None

def agent_node(state:ResearchState):
    """思考节点：调用 LLM 决定下一步行动"""
    response = llm.bind_tools(tools).invoke(state['messages'])
    return{"messages":[response]}

def tool_executor(state:ResearchState):
    """执行工具并提取结果到 search_results"""
    tool_node =ToolNode(tools=tools)
    tool_output = tool_node.invoke(state)
    tool_results = []
    for msg in tool_output["messages"]:
        if isinstance(msg, ToolMessage):
            tool_results.append(json.loads(msg.content))
    return {
        "messages": tool_output["messages"],
        "search_results": tool_results
    }

def router(state:ResearchState)-> str:
    """路由：判断下一步是调用工具、直接结束还是进入质量检查"""
    last_message = state['messages'][-1]
    if hasattr(last_message,'tool_calls')and last_message.tool_calls:
        return"tool_node"
    else:
        return"END"

def quality_check_node(state:ResearchState):
    """
    检查搜索结果的质量，并使用goto动态决定下一步。
    """
    print("--- Executing node: quality_check_node ---")
    writer = get_stream_writer()
    writer({"status":"正在评估搜索结果质量...","type":"quality_check_node"})
    search_results = state.get("search_results")
    if not search_results or len(search_results) < 2:
        print("--- 决策: 搜索结果不足，中断并请求用户澄清 ---")
        return Command(goto="clarify_with_user_node")
    else:
        print("--- 决策: 搜索结果充足，跳转至报告生成 ---")
        return Command(goto="generate_draft_node")

def clarify_with_user_node(state:ResearchState):
    """生成需要用户澄清的提示消息"""
    clarify_msg =AIMessage(content="搜索结果不足，请提供更具体的问题或补充信息。")
    return{"messages":[clarify_msg]}

async def generate_draft_node(state: ResearchState):
    """根据搜索结果生成报告初稿"""
    print("--- Executing node: generate_draft_node (AI正在撰写初稿...) ---")
    prompt = f"根据以下搜索结果，为用户的最后一个问题生成一份详细的报告初稿: {state['search_results']}"
    messages = state["messages"] + [("user", prompt)]
    response = await llm.ainvoke(messages)
    return {"draft_report": response.content}

def human_review_node(state:ResearchState):
    """人类审核节点 - 这个节点本身不执行逻辑，仅作为中断点"""
    print("--- Reached node: human_review_node (等待人类审核...) ---")
    return{}

def finalize_report_node(state:ResearchState):
    """根据（可能被修改过的）初稿生成最终消息"""
    print("--- Executing node: finalize_report_node (生成最终报告...) ---")
    reviewed_report = state["draft_report"]
    final_message =AIMessage(content=f"这是根据您的审核生成的最终报告：\n\n{reviewed_report}")
    return{"messages":[final_message]}


final_graph_builder =StateGraph(ResearchState)

# 添加工作流节点
final_graph_builder.add_node("agent_node", agent_node)
final_graph_builder.add_node("tool_node", tool_executor)
final_graph_builder.add_node("quality_check_node", quality_check_node)
final_graph_builder.add_node("clarify_with_user_node", clarify_with_user_node)

final_graph_builder.add_node("generate_draft_node", generate_draft_node)
final_graph_builder.add_node("human_review_node", human_review_node)
final_graph_builder.add_node("finalize_report_node", finalize_report_node)

# 添加工作流边缘
final_graph_builder.set_entry_point("agent_node")

final_graph_builder.add_conditional_edges(
    "agent_node",
    router,
    {
        "tool_node":"tool_node",
        "END":END
    }
)

final_graph_builder.add_edge("tool_node","quality_check_node")
final_graph_builder.add_edge("clarify_with_user_node",END)

final_graph_builder.add_edge("generate_draft_node","human_review_node")
final_graph_builder.add_edge("human_review_node","finalize_report_node")
final_graph_builder.add_edge("finalize_report_node",END)

final_checkpointer =MemorySaver()
app = final_graph_builder.compile(
    checkpointer=final_checkpointer,
    interrupt_before=["human_review_node","clarify_with_user_node"],
)


async def run_collaborative_session(query: str):
    config = {"configurable": {"thread_id": "collab-thread-2"}}
    inputs = {"messages": [HumanMessage(content=query)]}
    content = ""

    logger.debug("--- [Session Start] ---")
    # 1. 启动图，它将运行直到第一个中断点
    async for output in app.astream(
        inputs,
        config=config,
        stream_mode="updates"  # updates:分步骤输出
    ):
        for step, data in output.items():
            logger.debug(f"Node '{step}' output: {data}")
            
            if step == "agent_node":
                latest_message = data["messages"][-1]
                content = latest_message.content
                logger.debug(f"Agent response content: {content}")
            elif step == "tool_node":
                logger.debug(f"Tool response content: {data}")

            result = {"Node": step, "output": content}
            yield json.dumps(result, ensure_ascii=False)

    # 2. 检查中断状态
    current_state = await app.aget_state(config)

    # 检查是否需要澄清（如果最后一条消息是AI消息，且没有draft_report，则需要澄清）
    if "clarify_with_user_node" in current_state.next:
        # 提示用户输入澄清信息
        clarification = input("\n请输入您的澄清回复: ")
        
        # 使用用户的澄清继续调用
        async for output in app.astream(
            {"messages": [HumanMessage(content=clarification)]}, 
            config=config, 
            stream_mode="updates"
        ):
            for step, data in output.items():
                logger.debug(f"Node '{step}' output: {data}")
                
                latest_message = data["messages"][-1]
                if step == "agent_node":
                    content = latest_message.content
                    logger.debug(f"Agent response content: {content}")
                elif step == "tool_node":
                    logger.debug(f"Tool response content: {latest_message.content}, tool name:{latest_message.name}")

                result = {"Node": step, "output": content}
                yield json.dumps(result, ensure_ascii=False)

    # 检查是否在 human_review_node 中断
    elif "human_review_node" in current_state.next:
        logger.debug("--- [Graph Interrupted for Human Review] ---")

        # 3. 从状态中提取生成的初稿
        draft_report = current_state.values.get("draft_report")

        logger.debug("\nAI 生成的报告初稿：")
        print("--------------------")
        logger.debug(draft_report)
        print("--------------------")

        # 4. 模拟用户在前端页面进行修改
        logger.debug("\n请在下方确认或修改报告内容。如果无需修改，直接按回车。")
        user_feedback = input("您的修改版本: ")

        # 如果用户没有输入，则使用原始初稿
        if not user_feedback.strip():
            final_draft = draft_report
            logger.debug("--- 用户已确认，使用原始初稿继续 ---")
        else:
            final_draft = user_feedback
        logger.debug("--- 用户已提交修改，使用新版本继续 ---")

        resume_inputs ={"draft_report": final_draft}

        logger.debug("\n--- [Session Resumed] ---")
        async for output in app.astream(
            resume_inputs, 
            config=config, 
            stream_mode="updates"
        ):
            for step, data in output.items():
                logger.debug(f"Node '{step}' output: {data}")
                
                latest_message = data["messages"][-1]
                if step == "agent_node":
                    content = latest_message.content
                    logger.debug(f"Agent response content: {content}")
                elif step == "tool_node":
                    logger.debug(f"Tool response content: {latest_message.content}, tool name:{latest_message.name}")

                result = {"Node": step, "output": content}
                yield json.dumps(result, ensure_ascii=False)

    # 6. 获取并打印最终结果
    final_state = await app.aget_state(config)
    if not final_state.next:
        final_message = final_state.values["messages"][-1]
        logger.debug(f"最终消息内容: {final_message.content}")
        result = {"Node": "END", "output": final_message.content}
        yield json.dumps(result, ensure_ascii=False)

async def main():
    """主函数，用于异步迭代并打印流式输出结果"""
    async for chunk in run_collaborative_session("对比一下LangGraph和传统的LangChain Agent在实现复杂工作流时的优劣势"):
        logger.debug(f"》》》流式输出结果: {chunk}")

if __name__ =="__main__":
    asyncio.run(main())
