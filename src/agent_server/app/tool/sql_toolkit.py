"""
增强的SQL工具包
基于LangChain的SQLDatabaseToolkit，提供增强的SQL查询功能。
"""
from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseLanguageModel
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

from agent_server.app.tool.table_info_tool import TableInfoTool
from agent_server.app.tool.weather_tool import WeatherTool

def create_tools() -> list[BaseTool]:
        """创建增强的工具集合"""
        tools = [
            TableInfoTool(),
            WeatherTool(),
        ]
        return tools