"""Session：代表一个 WebSocket 客户端连接。

一个 Session 与一条 WebSocket 连接一一对应，生命周期随连接建立和断开。
Session 内部维护当前活跃的 conversation_id，后续可扩展为多轮会话管理。
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket

from server.session_mgr.cmd_builder import build_request

logger = logging.getLogger(__name__)

_DEFAULT_REQUEST_TIMEOUT = 30.0


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
        # request_id → Future，用于 request-response 模式等待客户端回复
        self._pending_requests: dict[str, asyncio.Future[dict[str, Any]]] = {}

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

    def cleanup(self) -> None:
        """清理所有待处理请求，取消等待中的 Future。"""
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

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
    # Request-Response：服务端主动向客户端发请求并等待回复
    # ------------------------------------------------------------------

    async def send_request(
        self,
        cmd: str,
        params: dict[str, Any] | None = None,
        timeout: float = _DEFAULT_REQUEST_TIMEOUT,
    ) -> dict[str, Any]:
        """向客户端发送请求并等待回复。

        每次调用生成唯一 request_id，支持同一 cmd 的并发请求。

        Args:
            cmd: 命令名称。
            params: 命令参数。
            timeout: 等待回复的超时时间（秒）。

        Returns:
            客户端回复的 params 字段内容。

        Raises:
            TimeoutError: 等待回复超时。
            RuntimeError: 客户端返回错误。
        """
        request_id = uuid.uuid4().hex

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_requests[request_id] = future

        message = json.dumps(build_request(cmd, params, request_id=request_id))

        try:
            await self.send_text(message)
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            msg = f"等待客户端回复超时 [cmd={cmd}, request_id={request_id}]"
            raise TimeoutError(msg)
        finally:
            self._pending_requests.pop(request_id, None)

        return result

    def resolve_response(
        self,
        request_id: str,
        status: str,
        params: dict[str, Any],
    ) -> bool:
        """将客户端的回复路由到对应的等待 Future。

        Args:
            request_id: 请求唯一标识，客户端回复时应原样携带。
            status: 客户端回复的状态码。
            params: 客户端回复的参数。

        Returns:
            True 表示成功匹配到待处理请求，False 表示无匹配。
        """
        future = self._pending_requests.get(request_id)
        if future is None or future.done():
            return False

        if status == "ok":
            future.set_result(params)
        else:
            reason = params.get("reason", status)
            future.set_exception(
                RuntimeError(f"客户端返回错误 [request_id={request_id}, reason={reason}]")
            )
        return True

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
