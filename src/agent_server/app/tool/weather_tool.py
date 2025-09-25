
import asyncio
import os
import sys
import requests

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from typing import Optional

from langchain.tools import BaseTool

from agent_server.config.settings import Settings

class WeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = "获取指定城市的当前天气信息。输入应该是城市名称。"
    
    def _run(self, city: str) -> str:
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
    
    async def _arun(self, city: str) -> str:
        """异步运行（暂时使用同步实现）"""
        return await asyncio.to_thread(self._run, city)


if __name__ == "__main__":
    weather_tool = WeatherTool()
    result = weather_tool._run("杭州")
    print(result)
    