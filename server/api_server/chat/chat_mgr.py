"""对话管理器：对话请求的前置调度层。

职责：
1. 选择实际执行对话的 Agent（当前规则：active_agents 中的第一个）
2. 记录调用日志与耗时
3. 调用 agent_executor 完成对话
"""

import logging
import time

from config.configs import get_config
from server.agent.agent_executor import chat as agent_chat

logger = logging.getLogger(__name__)


def _select_agent() -> str:
    """选择用于对话的 Agent 名称。

    当前规则：active_agents 列表中的第一个。

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


def handle_chat(
    user_message: str,
    conversation_id: str | None = None,
    session_id: str = "",
) -> dict[str, str]:
    """处理一次对话请求。

    Args:
        user_message: 用户输入文本。
        conversation_id: 会话 ID，为 None 时由下层自动生成。
        session_id: WebSocket 会话 ID，传递给 AgentState 供工具使用。

    Returns:
        包含 reply 和 conversation_id 的字典。
    """
    agent_name = _select_agent()

    start = time.time()

    result = agent_chat(
        agent_name=agent_name,
        user_message=user_message,
        conversation_id=conversation_id,
        session_id=session_id,
    )

    elapsed = time.time() - start
    logger.info(
        "对话完成 [agent=%s, conversation=%s] 耗时=%.2fs",
        agent_name, result["conversation_id"], elapsed,
    )

    return result
