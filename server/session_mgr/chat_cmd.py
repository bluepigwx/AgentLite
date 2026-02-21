"""chat 命令处理：通过 WebSocket Session 与 Agent 对话。"""

import asyncio
import json
import logging
from functools import partial
from typing import Any

from config.configs import get_config
from server.agent.agent_executor import chat as agent_chat
from server.session_mgr.cmd_dispatch import register_handler
from server.session_mgr.session import Session

logger = logging.getLogger(__name__)


def _select_agent() -> str:
    """选择用于对话的 Agent 名称（取 active_agents 第一个）。

    Returns:
        Agent 名称。

    Raises:
        RuntimeError: active_agents 为空时无法选择。
    """
    config = get_config()
    if not config.active_agents:
        msg = "active_agents 为空，无可用 Agent"
        raise RuntimeError(msg)
    return config.active_agents[0]


@register_handler("chat")
async def handle_chat(session: Session, params: dict[str, Any]) -> None:
    """处理客户端的对话请求。

    Request params:
        message (str): 用户输入文本。

    Response params:
        reply (str): Agent 回复。
        conversation_id (str): 当前对话 ID。
    """
    message = params.get("message")
    if not message:
        await session.send_text(json.dumps({
            "cmd": "chat",
            "status": "error",
            "params": {"reason": "缺少 message 参数"},
        }))
        return

    try:
        agent_name = _select_agent()
        conversation_id = session.ensure_conversation()

        # agent_chat 是同步阻塞调用，放到线程池执行避免阻塞事件循环
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                agent_chat,
                agent_name=agent_name,
                user_message=message,
                conversation_id=conversation_id,
            ),
        )

        await session.send_text(json.dumps({
            "cmd": "chat",
            "status": "ok",
            "params": {
                "reply": result["reply"],
                "conversation_id": result["conversation_id"],
            },
        }))

    except Exception as e:
        logger.exception("chat 命令处理失败 [session=%s]", session.session_id)
        await session.send_text(json.dumps({
            "cmd": "chat",
            "status": "error",
            "params": {"reason": str(e)},
        }))
