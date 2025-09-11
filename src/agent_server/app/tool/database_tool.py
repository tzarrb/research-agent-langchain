"""
数据库工具
提供各种数据库操作工具，遵循LangChain工具设计模式。
"""
from typing import Optional, Dict, Any

from langchain_core.tools import BaseTool
from langchain_community.utilities.sql_database import SQLDatabase

from pydantic import Field

class DataBaseTool(BaseTool):
    """数据库操作工具"""
    name: str = "database_tool"
    description: str = (
        "获取指定表的结构信息，包括列名、数据类型等，输入表名"
    )

    db: SQLDatabase = Field(exclude=True)

    def _run(self, table_name: str) -> str:
        """查询表结构"""
        try:
            # 验证表是否存在
            available_tables = self.db.get_usable_table_names()
            if table_name not in available_tables:
                return f"表 '{table_name}' 不存在。可用的表: {', '.join(available_tables)}"

            # 获取表结构
            table_info = self.db.get_table_info_no_throw([table_name])
            return f"表 '{table_name}' 的结构信息:\n{table_info}"

        except Exception as e:
            return f"查询表结构时出错: {str(e)}"