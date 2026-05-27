# research_agent.py
from typing import TypedDict, Annotated, List  
from langgraph.graph.message import add_messages  

from langchain_deepseek import ChatDeepSeek

from langgraph.graph import StateGraph, START, END  

from dotenv import load_dotenv  # 用于加载环境变量
load_dotenv()  # 加载 .env 文件中的环境变量

llm = ChatDeepSeek(
            model="deepseek-reasoner",
            streaming=True,
            temperature=0.3, # 随机性：0.0（最确定）–1.0（最随机）
            max_tokens=8000, # 最多返回多少 token
            max_retries=2,
            timeout=60,
        )

class ResearchState(TypedDict):  
    topic: str  
    research_queries: List[str]  
    raw_information: List[str]  
    validated_facts: List[str]  
    final_report: str  
    current_agent: str  
    messages: Annotated[list, add_messages]  

def researcher_agent(state: ResearchState):  
    """  
    研究员智能体
    将研究主题分解为具体查询  
    并收集初始信息  
    """  
    topic = state["topic"]  
        
    # 生成研究查询  
    query_prompt = f"""  
    将这个研究主题分解为3-5个具体的、 
    可搜索的查询：{topic}  
    
    让每个查询都集中且可操作。  
    """  
    
    queries = llm.invoke(query_prompt).content.split('\n')  
    queries = [q.strip() for q in queries if q.strip()]  
    
    # 为每个查询收集初始研究  
    raw_info = []  
    for query in queries:  
        # 模拟研究过程（实际应用中替换为具体的搜索和检索机制）  
        research_result = llm.invoke(f"Research and provide information about: {query}")  
        raw_info.append(research_result.content)  
    
    return {  
        "research_queries": queries,  
        "raw_information": raw_info,  
        "current_agent": "researcher",  
        "messages": [f"Researcher completed queries: {', '.join(queries)}"]  
    }  

def fact_checker_agent(state: ResearchState):  
    """  
    事实核查智能体
    验证和交叉引用收集的信息  
    """  
    raw_info = state["raw_information"]  
    validated_facts = []  
    
    for info_piece in raw_info:  
        validation_prompt = f"""  
        分析这个信息的准确性和可靠性：  
        {info_piece}  
        
        评估可靠性（1-10）并识别任何需要 
        额外验证的声明。 
        只提取最可信的事实。  
        """  
        
        validation_result = llm.invoke(validation_prompt)  
        
        # 提取验证的事实（简化逻辑）  
        if "reliable" in validation_result.content.lower():  
            validated_facts.append(info_piece)  
    
    return {  
        "validated_facts": validated_facts,  
        "current_agent": "fact_checker",  
        "messages": [f"Fact-checker validated {len(validated_facts)} information pieces"]  
    }  

def report_writer_agent(state: ResearchState):  
    """  
    报告生成智能体
    从验证的事实创建综合报告  
    """  
    topic = state["topic"]  
    validated_facts = state["validated_facts"]  
    
    report_prompt = f"""  
    创建关于以下主题的综合研究报告：{topic}  
    
    使用这些验证的事实：  
    {chr(10).join(validated_facts)}  
    
    按以下结构组织报告：  
    1. 执行摘要  
    2. 关键发现  
    3. 支持证据  
    4. 结论  
    
    使其专业但易懂。  
    """  
    
    final_report = llm.invoke(report_prompt).content  
    
    return {  
        "final_report": final_report,  
        "current_agent": "report_writer",  
        "messages": [f"Report writer completed final report ({len(final_report)} characters)"]  
    }  


# 初始化多智能体工作流  
workflow = StateGraph(ResearchState)

workflow.add_node("researcher", researcher_agent)
workflow.add_node("fact_checker", fact_checker_agent)
workflow.add_node("report_writer", report_writer_agent)

# 定义工作流序列  
workflow.add_edge(START, "researcher")  
workflow.add_edge("researcher", "fact_checker")  
workflow.add_edge("fact_checker", "report_writer")  
workflow.add_edge("report_writer", END)  

# 编译工作流  
app = workflow.compile()  

# 运行多智能体系统  
def run_research_assistant(topic: str):  
    initial_state = {  
        "topic": topic,  
        "research_queries": [],  
        "raw_information": [],  
        "validated_facts": [],  
        "final_report": "",  
        "current_agent": "",  
        "messages": []  
    }  
    
    result = app.invoke(initial_state)  
    return result["final_report"]