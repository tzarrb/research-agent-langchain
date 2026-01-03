

import json
from pathlib import Path
from datetime import datetime
from typing_extensions import Annotated, List, Literal

from pydantic import BaseModel, Field

from langchain_core.tools import tool, InjectedToolArg

from agent_server.app.agent.deep_research.search_service import(
    tavily_search_multiple,
    deduplicate_search_results,
    process_search_results,
    format_search_output
)

# ===== 研究工具 =====

@tool(parse_docstring=True)
def search_tool(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 3,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
) -> str:
    """从Tavily搜索API获取结果并进行内容摘要。

    Args:
        query: 要执行的单个搜索查询
        max_results: 返回的最大结果数
        topic: 按主题过滤结果（'general'、'news'、'finance'）

    Returns:
        带有摘要的格式化搜索结果字符串
    """
    # 对单个查询执行搜索
    search_results = tavily_search_multiple(
        [query],  # 将单个查询转换为列表以供内部函数使用
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
    )

    # 通过URL去重结果，避免处理重复内容
    unique_results = deduplicate_search_results(search_results)

    # 使用摘要处理结果
    summarized_results = process_search_results(unique_results)

    # 格式化输出以供使用
    return format_search_output(summarized_results)

@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """用于研究进展和决策制定的战略反思工具。

    在每次搜索后使用此工具来系统地分析结果并规划下一步。
    这在研究工作流程中创建了一个深思熟虑的暂停，以便进行高质量的决策制定。

    何时使用：
    - 收到搜索结果后：我找到了什么关键信息？
    - 决定下一步之前：我是否有足够的信息来全面回答？
    - 评估研究差距时：我仍然缺少什么具体信息？
    - 结束研究之前：我现在能提供完整的答案吗？

    反思应该涉及：
    1. 当前发现的分析 - 我收集了什么具体信息？
    2. 差距评估 - 仍然缺少什么关键信息？
    3. 质量评估 - 我是否有足够的证据/例子来提供好的答案？
    4. 战略决策 - 我应该继续搜索还是提供我的答案？

    Args:
        reflection: 你对研究进展、发现、差距和下一步的详细反思

    Returns:
        确认反思已记录用于决策制定
    """
    return f"反思已记录: {reflection}"


@tool
class ConductResearch(BaseModel):
    """用于将研究任务委托给专门的子智能体的工具。"""
    research_topic: str = Field(
        description="要研究的主题。应该是单一主题，并且应该详细描述（至少一段话）。",
    )

@tool
class ResearchComplete(BaseModel):
    """用于指示研究过程已完成的工具。"""
    pass
