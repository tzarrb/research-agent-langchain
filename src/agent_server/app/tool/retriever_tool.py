from langchain_core.tools import tool

from langchain.tools.retriever import create_retriever_tool

from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger

from agent_server.app.rag.vector_store.base import VsServiceFactory

# 本地知识库向量检索工具
__vs_service = VsServiceFactory.get_service(vector_store_type=Settings.kn_settings.DEFAULT_VS_TYPE)
__retriever = __vs_service.get_vector_store_retriever()

"""
Query relevant documents from the local knowledge base based on user input and return the content.
"""
retriever_tool = create_retriever_tool(
    __retriever,
    "knowledge_retriever",
    "Searches and returns content from the Local knowledge.",
)
