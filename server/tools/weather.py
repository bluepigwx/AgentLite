"""天气查询工具。"""

from server.tools.tool_register import register_tool


@register_tool
def get_weather(city: str) -> str:
    """获取指定城市的天气情况。"""
    return f"{city}天气多云转阴，气温 22°C"


@register_tool
def get_alien_weather(planet: str) -> str:
    """获取指定外星球的天气情况。"""
    return f"{planet} 有剧毒风暴肆虐，同时基纽特种部队也在此巡逻，不建议前往"
