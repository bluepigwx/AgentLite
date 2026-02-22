"""SessionMgr：管理所有活跃的 WebSocket 会话。

职责：
1. 维护 session_id → Session 的全局映射
2. 处理 WebSocket 连接建立与断开
3. 提供按 session_id 查找 Session 的能力

线程安全说明：
    _sessions 的读写同时发生在主事件循环（accept/disconnect）和
    线程池（工具函数通过 get_session_or_raise 访问），因此使用
    threading.Lock 保证并发安全。
"""

import logging
import threading

from fastapi import WebSocket

from server.session_mgr.session import Session

logger = logging.getLogger(__name__)

# 全局活跃会话表：session_id → Session
_sessions: dict[str, Session] = {}
_lock = threading.Lock()


async def accept(websocket: WebSocket) -> Session:
    """接受新的 WebSocket 连接，创建并注册 Session。

    Args:
        websocket: FastAPI WebSocket 连接对象。

    Returns:
        创建好的 Session 实例。
    """
    session = Session(websocket)
    await session.accept()
    with _lock:
        _sessions[session.session_id] = session
    logger.info(
        "Session 已注册 [session_id=%s, 当前在线=%d]",
        session.session_id, len(_sessions),
    )
    return session


def disconnect(session: Session) -> None:
    """处理 WebSocket 断开，移除 Session 注册。

    Args:
        session: 要移除的 Session 实例。
    """
    with _lock:
        _sessions.pop(session.session_id, None)
    logger.info(
        "Session 已移除 [session_id=%s, 当前在线=%d]",
        session.session_id, len(_sessions),
    )


def get_session(session_id: str) -> Session | None:
    """按 session_id 查找活跃 Session。

    Args:
        session_id: 会话唯一标识。

    Returns:
        Session 实例，不存在则返回 None。
    """
    with _lock:
        return _sessions.get(session_id)


def get_session_or_raise(session_id: str) -> Session:
    """按 session_id 查找活跃 Session，不存在则抛出异常。

    线程安全：可安全地从线程池线程中调用。

    Args:
        session_id: 会话唯一标识。

    Returns:
        Session 实例。

    Raises:
        RuntimeError: session 不存在或已断开。
    """
    with _lock:
        session = _sessions.get(session_id)
    if session is None:
        msg = f"session '{session_id}' 不存在或已断开"
        raise RuntimeError(msg)
    return session


def get_all_sessions() -> dict[str, Session]:
    """获取所有活跃 Session 的只读快照。"""
    with _lock:
        return dict(_sessions)


def online_count() -> int:
    """返回当前在线 Session 数量。"""
    with _lock:
        return len(_sessions)
