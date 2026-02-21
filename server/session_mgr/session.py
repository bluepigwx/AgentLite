"""Session：代表一个 WebSocket 客户端连接。

一个 Session 与一条 WebSocket 连接一一对应，生命周期随连接建立和断开。
Session 内部维护当前活跃的 conversation_id，后续可扩展为多轮会话管理。
"""

import logging
import uuid

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class Session:
    """单个客户端 WebSocket 会话。

    Attributes:
        session_id: 会话唯一标识，连接建立时自动生成。
        websocket: 底层 WebSocket 连接对象。
        conversation_id: 当前活跃的对话 ID，首次对话时自动生成。
    """

    def __init__(self, websocket: WebSocket) -> None:
        self.session_id: str = uuid.uuid4().hex
        self.websocket: WebSocket = websocket
        self.conversation_id: str | None = None

    # ------------------------------------------------------------------
    # 连接生命周期
    # ------------------------------------------------------------------

    async def accept(self) -> None:
        """接受 WebSocket 连接并完成握手。"""
        await self.websocket.accept()
        logger.info("Session 已建立 [session_id=%s]", self.session_id)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """主动关闭连接。"""
        await self.websocket.close(code=code, reason=reason)
        logger.info(
            "Session 已关闭 [session_id=%s, code=%d]",
            self.session_id, code,
        )

    # ------------------------------------------------------------------
    # 消息收发
    # ------------------------------------------------------------------

    async def receive_text(self) -> str:
        """接收一条文本消息。"""
        return await self.websocket.receive_text()

    async def send_text(self, data: str) -> None:
        """发送一条文本消息。"""
        await self.websocket.send_text(data)

    # ------------------------------------------------------------------
    # 对话 ID 管理
    # ------------------------------------------------------------------

    def ensure_conversation(self) -> str:
        """确保存在 conversation_id，不存在则创建。

        Returns:
            当前的 conversation_id。
        """
        if not self.conversation_id:
            self.conversation_id = uuid.uuid4().hex
            logger.info(
                "新建 conversation [session=%s, conversation=%s]",
                self.session_id, self.conversation_id,
            )
        return self.conversation_id

    def new_conversation(self) -> str:
        """强制创建一个新的 conversation，返回新 ID。"""
        self.conversation_id = uuid.uuid4().hex
        logger.info(
            "重置 conversation [session=%s, conversation=%s]",
            self.session_id, self.conversation_id,
        )
        return self.conversation_id

    def __repr__(self) -> str:
        return (
            f"Session(session_id={self.session_id!r}, "
            f"conversation_id={self.conversation_id!r})"
        )
