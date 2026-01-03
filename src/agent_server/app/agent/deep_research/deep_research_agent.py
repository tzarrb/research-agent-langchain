
"""
完整的多智能体研究系统

该模块集成了研究系统的所有组件：
- 用户需求澄清和范围界定
- 研究简报生成
- 多智能体研究协调
- 最终报告生成

系统从初始用户输入到最终报告交付，编排完整的研究工作流程。
"""

import asyncio
import os
import sys
# 把 src 加入 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))
print("Current sys.path = ", sys.path)

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger
from agent_server.utils.basic_util import get_today_str

from agent_server.app.agent.deep_research.prompt.prompts_zh import final_report_generation_prompt
from agent_server.app.agent.deep_research.state.state_scope import AgentState, AgentInputState
from agent_server.app.agent.deep_research.research_scope_agent import clarify_with_user, write_research_brief
from agent_server.app.agent.deep_research.multi_agent_supervisor import supervisor_agent
from agent_server.app.agent.deep_research.utils import format_messages

logger = build_logger("deep-research-agent")


# ===== 配置 =====
# load_dotenv()  # 加载 .env 文件中的环境变量

# writer_model = ModelFactory.get_model(model_name="deepseek-chat")
writer_model = ModelFactory.get_model(model_name="deepseek-chat")


# ===== 最终报告生成 =====
async def final_report_generation(state: AgentState):
    """
    最终报告生成节点。

    将所有研究发现综合为全面的最终报告
    """

    notes = state.get("notes", [])

    findings = "\n".join(notes)

    final_report_prompt = final_report_generation_prompt.format(
        research_brief=state.get("research_brief", ""),
        findings=findings,
        date=get_today_str()
    )

    final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt)])

    return {
        "final_report": final_report.content,
        "messages": ["这是最终报告: " + final_report.content],
    }

# ===== 图构建 =====
# 构建整体工作流
deep_researcher_builder = StateGraph(AgentState, input_schema=AgentInputState)

# 添加工作流节点
deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
deep_researcher_builder.add_node("write_research_brief", write_research_brief)
deep_researcher_builder.add_node("supervisor_subgraph", supervisor_agent)
deep_researcher_builder.add_node("final_report_generation", final_report_generation)

# 添加工作流边缘
deep_researcher_builder.add_edge(START, "clarify_with_user")
deep_researcher_builder.add_edge("write_research_brief", "supervisor_subgraph")
deep_researcher_builder.add_edge("supervisor_subgraph", "final_report_generation")
deep_researcher_builder.add_edge("final_report_generation", END)

# 编译完整工作流
checkpointer = InMemorySaver()
deep_research_agent = deep_researcher_builder.compile(checkpointer=checkpointer)

png_data = deep_research_agent.get_graph(xray=True).draw_mermaid_png()
path = os.path.join(Settings.basic_settings.TEMP_IMAGE_PATH, "deep_research_agent.png")
with open(path, "wb") as f:
    f.write(png_data)


# 创建异步主函数
async def main():
    thread = {"configurable": {"thread_id": "1", "recursion_limit": 50}}
    
    # 初始查询
    # initial_query = "比较Gemini和OpenAI深度研究智能体。"
    initial_query = "让我们分析评估下杭州最好的餐厅，评估标准有价格、环境、服务、位置，这些信息你来收集，不用询问我,评估10家就行，其他因素不用考虑了"
    result = await deep_research_agent.ainvoke({"messages": [HumanMessage(content=initial_query)]}, config=thread)
    
    # 显示初始响应（澄清问题）
    format_messages(result['messages'])
    
    # 检查是否需要澄清（如果最后一条消息是AI消息，且没有research_brief，则需要澄清）
    if result.get("research_brief") is None and result['messages'] and result['messages'][-1].type == "ai":
        # 提示用户输入澄清信息
        clarification = input("\n请输入您的澄清回复: ")
        
        # 使用用户的澄清继续调用
        result = await deep_research_agent.ainvoke({"messages": [HumanMessage(content=clarification)]}, config=thread)
        format_messages(result['messages'])
    
    from rich.markdown import Markdown
    # 显示Markdown内容
    print(Markdown(result["final_report"]))
    
    # 保存为Markdown文件
    from datetime import datetime
    
    # 创建文件名（使用当前时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_report_{timestamp}.md"
    filepath = os.path.join(Settings.basic_settings.TEMP_FILE_PATH, filename)
    
    # 保存Markdown内容到文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result["final_report"])

    print(f"研究报告已保存为: {filepath}")
    return result

# 创建异步主函数
async def stream_main():
    thread = {"configurable": {"thread_id": "1", "recursion_limit": 50}}
    
    # 初始查询
    # initial_query = "比较Gemini和OpenAI深度研究智能体。"
    initial_query = "让我们分析评估下杭州最好的餐厅，评估标准有价格、环境、服务、位置，这些信息你来收集，不用询问我,评估10家就行，其他因素不用考虑了"
    inputs = {"messages": [HumanMessage(content=initial_query)]}

    # result = await deep_research_agent.ainvoke(inputs, config=thread)

    async for output in deep_research_agent.astream(inputs, config=thread):
        for key, value in output.items():
            print(f"Node '{key}' output: {value}")


    # 2. 检查中断状态
    result = await deep_research_agent.aget_state(thread)
    
    # 显示初始响应（澄清问题）
    format_messages(result['messages'])
    
    # 检查是否需要澄清（如果最后一条消息是AI消息，且没有research_brief，则需要澄清）
    if result.get("research_brief") is None and result['messages'] and result['messages'][-1].type == "ai":
        # 提示用户输入澄清信息
        clarification = input("\n请输入您的澄清回复: ")
        
        # 使用用户的澄清继续调用
        result = await deep_research_agent.ainvoke({"messages": [HumanMessage(content=clarification)]}, config=thread)
        format_messages(result['messages'])
    
    from rich.markdown import Markdown
    # 显示Markdown内容
    print(Markdown(result["final_report"]))
    
    # 保存为Markdown文件
    from datetime import datetime
    
    # 创建文件名（使用当前时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_report_{timestamp}.md"
    filepath = os.path.join(Settings.basic_settings.TEMP_FILE_PATH, filename)
    
    # 保存Markdown内容到文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result["final_report"])

    print(f"研究报告已保存为: {filepath}")
    return result

# 运行异步主函数
if __name__ == "__main__":
    asyncio.run(main())