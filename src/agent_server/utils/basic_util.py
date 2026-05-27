

import json
from pathlib import Path
from datetime import datetime
from typing_extensions import Annotated, List, Literal

from agent_server.utils.log_util import build_logger
logger = build_logger("basic-util")

# ===== 实用工具函数 =====

def get_today_str() -> str:
    """获取人类可读格式的当前日期。"""
    current_date = datetime.now().strftime("%a %b %d, %Y")
    logger.debug(f"获取当前日期: {current_date}")
    return current_date

def get_current_dir() -> Path:
    """获取模块的当前目录。

    此函数与Jupyter笔记本和常规Python脚本兼容。

    Returns:
        表示当前目录的Path对象
    """
    try:
        return Path(__file__).resolve().parent
    except NameError:  # __file__ 未定义
        return Path.cwd()
