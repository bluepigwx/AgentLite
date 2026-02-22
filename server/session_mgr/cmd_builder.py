"""消息构建工具：统一构建服务端与客户端之间的标准消息格式。"""

from typing import Any


def build_request(
    cmd: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: str = "",
) -> dict[str, Any]:
    """构建服务端→客户端的请求消息。

    Args:
        cmd: 命令名称。
        params: 命令参数。
        request_id: 请求唯一标识，用于匹配客户端回复。

    Returns:
        格式化的消息字典: {"cmd": "xxx", "request_id": "...", "params": {...}}
    """
    msg: dict[str, Any] = {"cmd": cmd, "params": params or {}}
    if request_id:
        msg["request_id"] = request_id
    return msg


def build_response(cmd: str, status: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """构建服务端→客户端的响应消息。

    Args:
        cmd: 命令名称。
        status: 状态码，"ok" 或 "error"。
        params: 响应参数。

    Returns:
        格式化的消息字典: {"cmd": "xxx", "status": "ok|error", "params": {...}}
    """
    return {"cmd": cmd, "status": status, "params": params or {}}
