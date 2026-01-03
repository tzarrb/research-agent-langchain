# 新增一个获取当前时间的tool工具，返回的当前时间格式为年月日 时分秒

from datetime import datetime
from langchain.tools import tool

from agent_server.utils.log_util import build_logger
logger = build_logger("datetime-tool")

async def get_current_datetime() -> str:
    now = datetime.now()
    current_date = now.strftime("%Y年%m月%d日 %H时%M分%S秒")
    logger.debug(f"获取当前日期: {current_date}")
    return current_date


@tool(description="获取当前时间")
async def current_datetime() -> str:
    return await get_current_datetime()
