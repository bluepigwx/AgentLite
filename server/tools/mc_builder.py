"""PyMC 场景操作工具：通过 WebSocket Session 向客户端发送场景相关指令。

工具函数通过 InjectedState 从 AgentState 中注入 session_id，
LLM 无需感知该参数，只需关注业务参数（如 blocks）。

注意：工具函数由 LangGraph ToolNode 在线程池中同步调用，
不能使用 asyncio.get_event_loop()，需通过 run_coroutine_threadsafe
将协程提交到主线程事件循环。
"""

import asyncio
import logging
import math
from typing import Annotated, Any

from langgraph.prebuilt import InjectedState

from server.session_mgr.session_mgr import get_session_or_raise
from server.tools.tool_register import register_tool

logger = logging.getLogger(__name__)

# 主线程事件循环引用，由 server 启动时设置
_main_loop: asyncio.AbstractEventLoop | None = None

# 跨线程提交协程的默认超时（秒），应大于 send_request 自身的 timeout
_CROSS_THREAD_TIMEOUT = 60.0


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """设置主线程事件循环引用，供工具函数跨线程提交协程。"""
    global _main_loop  # noqa: PLW0603
    _main_loop = loop


def _run_async(coro: Any, *, timeout: float = _CROSS_THREAD_TIMEOUT) -> Any:
    """将协程提交到主线程事件循环并阻塞等待结果。

    Args:
        coro: 要执行的协程。
        timeout: 最大等待时间（秒），防止线程池线程无限期阻塞。

    Raises:
        RuntimeError: 主线程事件循环未设置。
        TimeoutError: 等待结果超时。
    """
    if _main_loop is None:
        msg = "主线程事件循环未设置，请先调用 set_main_loop()"
        raise RuntimeError(msg)
    future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
    try:
        return future.result(timeout=timeout)
    except TimeoutError:
        future.cancel()
        raise


@register_tool
def get_scene_info(
    session_id: Annotated[str, InjectedState("session_id")],
) -> dict[str, Any]:
    """获取当前 PyMC 客户端的场景信息，包括摄像机位置和所有方块数据。"""
    session = get_session_or_raise(session_id)
    return _run_async(session.send_request("get_scene_info"))


@register_tool
def set_blocks(
    blocks: list[dict[str, Any]],
    session_id: Annotated[str, InjectedState("session_id")],
) -> dict[str, Any]:
    """在当前 PyMC 客户端的场景中批量放置方块。

    Args:
        blocks: 方块列表，每个 block 需包含 type(方块类型int), wx, wy, wz(整数世界坐标)。
    """
    session = get_session_or_raise(session_id)
    # 坐标取整：LLM 可能生成浮点坐标，Minecraft 方块坐标必须是整数
    sanitized = [
        {
            "type": b["type"],
            "wx": math.floor(b["wx"]),
            "wy": math.floor(b["wy"]),
            "wz": math.floor(b["wz"]),
        }
        for b in blocks
    ]
    return _run_async(session.send_request("set_blocks", {"blocks": sanitized}))
