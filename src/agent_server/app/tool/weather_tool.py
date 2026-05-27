
import os
import sys
import requests
import asyncio

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from typing import Optional

from pydantic import BaseModel, Field

from langchain.tools import BaseTool
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from agent_server.config.settings import Settings
from agent_server.utils.log_util import build_logger

logger = build_logger("weather-tool")

class WeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = "获取指定城市的当前天气信息。输入应该是城市名称。"
    
    def _run(self, city: str) -> str:
        return get_weather_openweather(city)
    
    async def _arun(self, city: str) -> str:
        """异步运行（暂时使用同步实现）"""
        return asyncio.run(self._run(city))


class WeatherQuery(BaseModel):
    city: str = Field(description="城市名称")
    start: int = Field(description="起始时间(-1:昨天, 0:今天, 1:明天)", default=0)
    days: int = Field(description="查询天数", default=1)


@tool(description="Get the weather in a given city", args_schema=WeatherQuery)
def weather_tool(city: str, start: int, days: int, config: RunnableConfig) -> str:
    """
       查询城市天气实时或预报函数
       :param city: 必要参数，字符串类型，用于表示查询天气的具体城市名称，start:起始时间(-1:昨天, 0:今天, 1:明天), days:查询天数
       :return：API查询即时天气的结果
       返回结果对象类型为解析之后的JSON格式对象，并用字符串形式进行表示，其中包含了全部重要的天气信息
    """
    return get_weather_seniverse(city, start, days, config)

def get_weather_seniverse(city: str, start: int, days: int, config: RunnableConfig):
    """
       查询城市天气实时或预报函数
       :param city: 必要参数，字符串类型，用于表示查询天气的具体城市名称，start:起始时间(-1:昨天, 0:今天, 1:明天), days:查询天数
       :return：心知天气 API查询即时天气的结果
       返回结果对象类型为解析之后的JSON格式对象，并用字符串形式进行表示，其中包含了全部重要的天气信息
       示例：
       北京实时天气预报
       https://api.seniverse.com/v3/weather/now.json?key=your_api_key&location=beijing&language=zh-Hans&unit=c
       北京今天和未来 4 天的预报
       https://api.seniverse.com/v3/weather/daily.json?key=your_api_key&location=beijing&language=zh-Hans&unit=c&start=0&days=5
    """
    
    conversation_id = config["configurable"].get("conversation_id")
    logger.info(f"get_weather called for conversation_id: {conversation_id}, city: {city}, start:{start}, days:{days}")
    
    # return f"It's sunny in {city}."
    
    url = Settings.basic_settings.WEATHER_SENIVERSE_URL
    params = {
        "key": Settings.basic_settings.WEATHER_SENIVERSE_KEY,
        "location": city,
        "start": start,
        "days": days,
        "language": "zh-Hans",
        "unit": "c",
    }
    response = requests.get(url, params=params)
    temperature = response.json()
    return temperature['results'][0]['daily']  


def get_weather_openweather(city: str, start: int = 0, days: int = 1, config: RunnableConfig = None) -> str:
    """获取天气信息"""
    api_key = Settings.basic_settings.WEATHER_KEY
    base_url = Settings.basic_settings.WEATHER_URL
    
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "zh_cn"
    }
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if response.status_code == 200:
            weather = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            
            return f"{city}当前天气：{weather}，温度{temp}°C，体感温度{feels_like}°C，湿度{humidity}%"
        else:
            return f"无法获取{city}的天气信息，请检查城市名称是否正确。"
            
    except Exception as e:
        return f"获取天气信息时出错：{str(e)}"
    
if __name__ == "__main__":
    weather_tool = WeatherTool()
    result = weather_tool._run("杭州")
    print(result)
    