"""时间工具"""

from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前时间"""
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return now.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        return f"获取时间失败: {str(e)}"
