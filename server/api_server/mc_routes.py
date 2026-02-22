"""PyMC 场景操作路由：提供 HTTP 接口模拟调用 mc_builder 工具，用于测试。

HTTP 路由不经过 Agent/LangGraph，InjectedState 不会自动注入，
因此手动把 session_id 作为参数传入工具调用。
"""

import logging
from typing import Any, cast

from fastapi import APIRouter
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from server.tools.mc_builder import get_scene_info as _get_scene_info
from server.tools.mc_builder import set_blocks as _set_blocks

logger = logging.getLogger(__name__)

# @register_tool 返回 BaseTool 实例，cast 帮助静态类型检查
get_scene_info_tool = cast(BaseTool, _get_scene_info)
set_blocks_tool = cast(BaseTool, _set_blocks)

mc_router = APIRouter(prefix="/mc", tags=["MC"])


class SetBlocksRequest(BaseModel):
    session_id: str
    blocks: list[dict[str, Any]]


@mc_router.get("/scene_info")
async def route_get_scene_info(session_id: str) -> dict[str, Any]:
    """获取指定 PyMC 客户端的场景信息，包括摄像机位置和所有方块数据。"""
    return get_scene_info_tool.invoke({"session_id": session_id})


@mc_router.post("/set_blocks")
async def route_set_blocks(req: SetBlocksRequest) -> dict[str, Any]:
    """在指定 PyMC 客户端的场景中批量放置方块。"""
    return set_blocks_tool.invoke({"blocks": req.blocks, "session_id": req.session_id})
