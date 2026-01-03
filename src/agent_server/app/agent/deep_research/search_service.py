"""网络搜索服务。

此模块为研究智能体提供搜索和内容处理实用程序，
包括网络搜索功能和内容摘要工具。
"""

from typing_extensions import Annotated, List, Literal

from langchain_core.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_tavily import TavilySearch
# from tavily import TavilyClient

from agent_server.app.llm.mode_factory import ModelFactory
from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger
from agent_server.utils.basic_util import get_today_str

from agent_server.app.agent.deep_research.research_schema import Summary
from app.agent.deep_research.prompt.prompts_zh import summarize_webpage_prompt

logger = build_logger("search-service")


# ===== 配置 =====

# from dotenv import load_dotenv
# load_dotenv()

# summarization_model = ChatDeepSeek(model="deepseek-chat")
summarization_model = ModelFactory.get_model(model_name="deepseek-chat")

def tavily_search_multiple(
    search_queries: List[str],
    max_results: int = 3,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
) -> List[dict]:
    """使用Tavily API对多个查询执行搜索。

    Args:
        search_queries: 要执行的搜索查询列表
        max_results: 每个查询的最大结果数
        topic: 搜索结果的主题过滤器
        include_raw_content: 是否包含原始网页内容

    Returns:
        搜索结果字典列表
    """

    tavily_search = TavilySearch(
        max_results=max_results,
        topic=topic,
        tavily_api_key=Settings.basic_settings.TAVILY_API_KEY,
        include_answer=False,  # 包含直接答案（通常更简洁）
        include_raw_content=include_raw_content,  # 不包含原始HTML内容
        include_images=False,  # 不包含图片（减少数据量）
    )
    
    # 顺序执行搜索。注意：你可以使用AsyncTavilyClient来并行化这一步。
    search_docs = []
    for query in search_queries:
        logger.debug(f"执行搜索查询: {query}")
        # result = tavily_client.search(
        #     query,
        #     max_results=max_results,
        #     include_raw_content=include_raw_content,
        #     topic=topic
        # )
        result = tavily_search.invoke(query)
        search_docs.append(result)

    return search_docs

def deduplicate_search_results(search_results: List[dict]) -> dict:
    """通过URL去重搜索结果，避免处理重复内容。

    Args:
        search_results: 搜索结果字典列表

    Returns:
        将URL映射到唯一结果的字典
    """
    unique_results = {}

    for response in search_results:
        for result in response['results']:
            url = result['url']
            if url not in unique_results:
                unique_results[url] = result

    return unique_results

def summarize_webpage_content(webpage_content: str) -> str:
    """使用配置的摘要模型总结网页内容。

    Args:
        webpage_content: 要总结的原始网页内容

    Returns:
        带有关键摘录的格式化摘要
    """
    # print(webpage_content)
    # print(get_today_str())
    try:
        # 设置用于摘要的结构化输出模型
        structured_model = summarization_model.with_structured_output(Summary)

        # 生成摘要
        summary = structured_model.invoke([
            HumanMessage(content=summarize_webpage_prompt.format(
                webpage_content=webpage_content,
                date=get_today_str()
            ))
        ])
        # print("summarize_webpage_content", summary)
        logger.debug(f"summarize_webpage_content: {summary}")
        # 格式化摘要，结构清晰
        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )

        return formatted_summary

    except Exception as e:
        logger.error(f"网页摘要失败: {str(e)}")
        return webpage_content[:1000] + "..." if len(webpage_content) > 1000 else webpage_content

def process_search_results(unique_results: dict) -> dict:
    """通过在可用时总结内容来处理搜索结果。

    Args:
        unique_results: 唯一搜索结果字典

    Returns:
        带有摘要的处理结果字典
    """
    summarized_results = {}

    for url, result in unique_results.items():
        # 如果没有原始内容用于摘要，则使用现有内容
        if not result.get("raw_content"):
            content = result['content']
        else:
            # 总结原始内容以便更好地处理
            content = summarize_webpage_content(result['raw_content'])

        summarized_results[url] = {
            'title': result['title'],
            'content': content
        }

    return summarized_results

def format_search_output(summarized_results: dict) -> str:
    """将搜索结果格式化为结构良好的字符串输出。

    Args:
        summarized_results: 处理过的搜索结果字典

    Returns:
        格式化的搜索结果字符串，具有清晰的来源分离
    """
    if not summarized_results:
        return "未找到有效的搜索结果。请尝试不同的搜索查询或使用不同的搜索API。"

    formatted_output = "搜索结果: \n\n"

    for i, (url, result) in enumerate(summarized_results.items(), 1):
        formatted_output += f"\n\n--- 来源 {i}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"摘要:\n{result['content']}\n\n"
        formatted_output += "-" * 80 + "\n"

    return formatted_output
