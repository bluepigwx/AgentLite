"""PyMC 场景操作工具：通过 WebSocket Session 向客户端发送场景相关指令。"""

import asyncio
import logging
from typing import Any

from server.session_mgr.session_mgr import get_session_or_raise
from server.tools.tool_register import register_tool

logger = logging.getLogger(__name__)


@register_tool
def get_scene_info(session_id: str) -> dict[str, Any]:
    """获取指定 PyMC 客户端的场景信息，包括摄像机位置和所有方块数据。"""
    session = get_session_or_raise(session_id)
    result = asyncio.get_event_loop().run_until_complete(
        session.send_request("get_scene_info")
    )
    return result


@register_tool
def set_blocks(session_id: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """在指定 PyMC 客户端的场景中批量放置方块。

    每个 block 需包含 type(方块类型), wx, wy, wz(世界坐标)。
    """
    session = get_session_or_raise(session_id)
    result = asyncio.get_event_loop().run_until_complete(
        session.send_request("set_blocks", {"blocks": blocks})
    )
    return result
