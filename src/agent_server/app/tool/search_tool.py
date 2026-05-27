
import json

from langchain_tavily import TavilySearch
from langchain_core.tools import tool

from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger

logger = build_logger("search_tool")


class SearchTool:
    def __init__(
        self,
        max_results: int = 5, 
        topic: str = "general",
        search_depth: str = "advanced",
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False
    ):
        self.raw_search = TavilySearch(
            max_results=max_results,
            topic=topic,
            tavily_api_key=Settings.basic_settings.TAVILY_API_KEY,
            include_answer=include_answer,  # 包含直接答案（通常更简洁）
            include_raw_content=include_raw_content,  # 不包含原始HTML内容
            include_images=include_images,  # 不包含图片（减少数据量）
            search_depth=search_depth  # 使用高级搜索
        )
    
        
    def search(self, query: str) -> str:
        """优化搜索，限制返回内容长度"""
        try:
            # 执行搜索
            raw_results = self.raw_search.invoke(query)
            
            return json.dumps(raw_results, ensure_ascii=False)
                
        except Exception as e:
            return f"搜索出错: {str(e)}"
    
    
class OptimizedSearchTool:
    def __init__(
        self, 
        max_results: int = 5, 
        topic: str = "general",
        search_depth: str = "advanced",
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False
    ):
        self.raw_search = TavilySearch(
            max_results=max_results,
            topic=topic,
            tavily_api_key=Settings.basic_settings.TAVILY_API_KEY,
            include_answer=include_answer,  # 包含直接答案（通常更简洁）
            include_raw_content=include_raw_content,  # 不包含原始HTML内容
            include_images=include_images,  # 不包含图片（减少数据量）
            search_depth=search_depth  # 使用高级搜索
        )
    
    def search_with_limits(self, query: str, max_content_length: int = 1500) -> str:
        """优化搜索，限制返回内容长度"""
        try:
            # 执行搜索
            raw_results = self.raw_search.invoke(query)
            
            if isinstance(raw_results, str):
                # 如果是字符串格式，直接处理
                if len(raw_results) > max_content_length:
                    return self._summarize_search_results(raw_results, max_content_length)
                return raw_results
            elif isinstance(raw_results, list):
                # 如果是列表格式，处理每个结果
                return self._process_search_results(raw_results, max_content_length)
            elif raw_results['results'] is not None:
                # 如果是对象格式，处理其内部的 results 属性
                return self._process_search_results(raw_results['results'], max_content_length)
            else:
                return str(raw_results)[:max_content_length]
                
        except Exception as e:
            return f"搜索出错: {str(e)}"
    
    def _process_search_results(self, results: list, max_length: int) -> str:
        """处理搜索结果列表"""
        processed_results = []
        total_length = 0
        
        for i, result in enumerate(results):  # 只处理前3个结果
            if total_length >= max_length:
                break
                
            # 提取关键信息
            if isinstance(result, dict):
                title = result.get('title', '无标题')
                content = result.get('content', '')[:300]  # 限制每个结果内容长度
                url = result.get('url', '')
            else:
                title = f"结果{i+1}"
                content = str(result)[:300]
                url = ""
            
            result_str = f"{i+1}. {title}\n{content}"
            if url:
                result_str += f"\n来源: {url}"
            
            if total_length + len(result_str) > max_length:
                # 如果超过限制，截断最后一个结果
                available_space = max_length - total_length - 10
                if available_space > 50:
                    result_str = result_str[:available_space] + "..."
                else:
                    break
            
            processed_results.append(result_str)
            total_length += len(result_str) + 2  # +2 for newlines
        
        if not processed_results:
            return "未找到相关结果"
        
        search_result = "\n\n".join(processed_results)
        logger.info(f"Search process result: {search_result}")
        return search_result

    def _summarize_search_results(self, content: str, max_length: int) -> str:
        """对搜索结果进行摘要"""
        if len(content) <= max_length:
            return content
        
        # 简单的摘要逻辑 - 保留开头和结尾的重要信息
        first_part = content[:max_length//2]
        last_part = content[-max_length//2:]
        
        # 查找关键段落
        sentences = content.split('。')
        if len(sentences) > 3:
            key_sentences = sentences[:2] + sentences[-2:]
            summarized = '。'.join(key_sentences) + '。'
            if len(summarized) > max_length:
                return summarized[:max_length] + "..."
            return summarized
        
        return first_part + "...[内容已截断]..." + last_part

search = SearchTool(max_results=3)
# 创建优化后的搜索工具实例
optimized_search = OptimizedSearchTool()

@tool(description="Search the web for current information")
def search_tool(query: str) -> str:
    """网络搜索工具，返回搜索内容内容"""
    return search.search(query)

@tool(description="Search the web for current information")
def optimized_search_tool(query: str) -> str:
    """优化版的网络搜索工具，限制返回内容长度"""
    return optimized_search.search_with_limits(query, max_content_length=1200)

# """
# Search for relevant content from the internet based on user input and return it.
# """
# search_tool = TavilySearch(
#     max_results=5,
#     topic="general",
#     tavily_api_key=Settings.basic_settings.TAVILY_API_KEY,
#     include_answer=True,  # 包含直接答案（通常更简洁）
#     include_raw_content=False,  # 不包含原始HTML内容
#     include_images=False,  # 不包含图片（减少数据量）
#     search_depth="advanced"  # 使用高级搜索
# )