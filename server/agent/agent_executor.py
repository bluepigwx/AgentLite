"""Agent 执行器：封装单次对话的推理、工具调用与上下文管理。"""

import logging
import uuid

from server.agent.agents_mgr import get_agent

logger = logging.getLogger(__name__)


def chat(
    agent_name: str,
    user_message: str,
    conversation_id: str | None = None,
    *,
    session_id: str = "",
) -> dict[str, str]:
    """执行一次对话，返回 Agent 回复。

    Args:
        agent_name: 要调用的 Agent 名称（对应 agents_mgr 中的 key）。
        user_message: 用户输入文本。
        conversation_id: 会话 ID，为 None 时自动生成。
        session_id: WebSocket 会话 ID，传递给 AgentState 供工具使用。

    Returns:
        包含 reply 和 conversation_id 的字典。
    """
    if not conversation_id:
        conversation_id = uuid.uuid4().hex

    agent_inst = get_agent(agent_name)

    reply = agent_inst.invoke(user_message, conversation_id, session_id=session_id)

    logger.info(
        "对话完成 [agent=%s, conversation=%s] reply: %s",
        agent_name, conversation_id, reply[:100],
    )

    return {
        "reply": reply,
        "conversation_id": conversation_id,
    }
