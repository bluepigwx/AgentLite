"""Session 消息分发：解析客户端请求并路由到对应的处理函数。

消息格式定义:
    Request:  {"cmd": "消息名称", "params": {...}}
    Response: {"cmd": "消息名称", "status": "ok|error", "params": {...}}
"""

import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from server.session_mgr.session import Session

logger = logging.getLogger(__name__)

# handler 签名：(Session, dict) -> None
CmdHandler = Callable[[Session, dict[str, Any]], Coroutine[Any, Any, None]]

# cmd 名称 → 处理函数的路由表
_CMD_HANDLERS: dict[str, CmdHandler] = {}


def register_handler(cmd: str) -> Callable[[CmdHandler], CmdHandler]:
    """注册一个 cmd 处理函数到路由表。

    Args:
        cmd: 命令名称。

    Usage::

        @register_handler("ping")
        async def _handle_ping(session, params):
            ...
    """
    def decorator(fn: CmdHandler) -> CmdHandler:
        if cmd in _CMD_HANDLERS:
            logger.warning("cmd handler 重复注册，已覆盖 [cmd=%s]", cmd)
        _CMD_HANDLERS[cmd] = fn
        return fn
    return decorator


@register_handler("ping")
async def _handle_ping(session: Session, params: dict[str, Any]) -> None:
    await session.send_text(json.dumps({
        "cmd": "ping",
        "status": "ok",
        "params": {},
    }))


@register_handler("new_conversation")
async def _handle_new_conversation(session: Session, params: dict[str, Any]) -> None:
    new_cid = session.new_conversation()
    await session.send_text(json.dumps({
        "cmd": "new_conversation",
        "status": "ok",
        "params": {"conversation_id": new_cid},
    }))


async def dispatch(session: Session, raw: str) -> None:
    """解析一条原始消息并分发到对应的处理函数。

    消息格式定义:
        Request::

            {
                "cmd": "消息名称",
                "params": "消息参数"
            }

        Response::

            {
                "cmd": "消息名称",
                "status": "消息状态",
                "params": "消息参数"
            }

    Args:
        session: 当前会话。
        raw: 客户端发来的原始文本。
    """
    # 解析 JSON
    try:
        msg: dict[str, Any] = json.loads(raw)
        cmd: str | None = msg.get("cmd")
        params: dict[str, Any] = msg.get("params", {})
    except (json.JSONDecodeError, AttributeError):
        await session.send_text(json.dumps({
            "cmd": "error",
            "status": "error",
            "params": {"reason": "消息格式错误，需为 JSON"},
        }))
        return

    # 查路由表分发
    if not cmd:
        await session.send_text(json.dumps({
            "cmd": "unknown",
            "status": "error",
            "params": {"reason": "缺少 cmd 字段"},
        }))
        return

    handler = _CMD_HANDLERS.get(cmd)
    if handler:
        await handler(session, params)
    else:
        await session.send_text(json.dumps({
            "cmd": cmd or "unknown",
            "status": "error",
            "params": {"reason": f"未知命令: {cmd}"},
        }))


# 导入外部 cmd 模块，触发 @register_handler 注册
import server.session_mgr.chat_cmd  # noqa: E402, F401
