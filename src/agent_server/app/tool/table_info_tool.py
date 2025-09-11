"""
数据库表信息工具
基于AsyncSession的数据库表信息查询工具，遵循LangChain工具设计模式。
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.tools import BaseTool

from agent_server.utils.log_util import build_logger
from agent_server.app.service.table_info_service import table_info_service

logger = build_logger("table_schema_tool")

class TableInfoTool(BaseTool):
    """异步表结构查询工具"""
    name: str = "table_info_tool"
    description: str = (
        "获取指定表的结构信息，包括列名、数据类型、约束等。"
        "输入表名，返回详细的表结构信息。"
    )

    async def _arun(self, table_name: str) -> str:
        """异步查询表结构"""
        try:
            # 1. 验证表是否存在
            available_tables = await table_info_service.get_all_tables()
            if table_name not in available_tables:
                return f"表 '{table_name}' 不存在。可用的表: {', '.join(available_tables)}"

            # 2. 获取表结构信息
            table_info = await table_info_service.get_table_schema(table_name)
            return f"表 '{table_name}' 的结构信息:\n{table_info}"
        except Exception as e:
            logger.error(f"查询表结构时出错: {str(e)}")
            return f"查询表结构时出错: {str(e)}"

    def _run(self, table_name: str) -> str:
        """同步接口（兼容性）"""
        import asyncio
        try:
            # 如果在异步环境中，直接调用异步方法
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在已有事件循环中创建任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(table_name))
                    return future.result()
            else:
                return asyncio.run(self._arun(table_name))
        except Exception as e:
            return f"查询表结构时出错: {str(e)}"

        """获取简化的表信息（备用方法）"""
        try:
            result = await session.execute(text(f"SELECT * FROM {table_name} LIMIT 0"))
            columns = result.keys()
            return f"表 '{table_name}' 包含以下列:\n" + "\n".join([f"  - {col}" for col in columns])
        except Exception as e:
            return f"无法获取表 '{table_name}' 的信息: {str(e)}"