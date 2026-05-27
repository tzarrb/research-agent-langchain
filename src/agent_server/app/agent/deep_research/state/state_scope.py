# state_scope.py
"""研究范围界定的状态定义和Pydantic架构。
这定义了研究智能体范围界定工作流程使用的状态对象和结构化架构，
包括研究人员状态管理和输出架构。
"""

import operator
from typing_extensions import Optional, Annotated, List, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages


# ===== 状态定义 =====

class AgentInputState(MessagesState):
    """完整智能体的输入状态 - 仅包含来自用户输入的消息。"""
    pass

class AgentState(MessagesState):
    """
    完整多智能体研究系统的主状态。

    使用额外的字段扩展MessagesState以进行研究协调。
    注意：某些字段在不同状态类之间重复，以便在子图和主工作流程之间
    进行适当的状态管理。
    """
    # 从用户对话历史生成的研究简报
    research_brief: Optional[str]
    # 与监督智能体交换的协调消息
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]
    # 在研究阶段收集的原始未处理研究笔记
    raw_notes: Annotated[list[str], operator.add] = []
    # 为报告生成准备的已处理和结构化笔记
    notes: Annotated[list[str], operator.add] = []
    # 最终格式化的研究报告
    final_report: str

