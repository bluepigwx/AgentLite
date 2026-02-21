"""LangchainAgentInst：基于 LangChain 的 AgentInst 实现，支持多轮对话记忆。"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage

from config.configs import AgentConfig
from server.agent.agent_inst import AgentInst

logger = logging.getLogger(__name__)


class LangchainAgentInst(AgentInst):
    """使用 LangChain Runnable 作为推理引擎的 Agent 实例。

    通过 LangGraph 的 checkpointer 机制实现多轮对话记忆，
    每个 conversation_id 对应一个独立的会话线程。

    Args:
        name: Agent 名称。
        agent_cfg: 对应的 Agent 配置。
        runnable: LangChain create_agent 返回的可执行对象（需配置 checkpointer）。
    """

    def __init__(
        self,
        name: str,
        agent_cfg: AgentConfig,
        runnable: Any,
    ) -> None:
        super().__init__(name, agent_cfg)
        self._runnable = runnable

    def invoke(self, user_message: str, conversation_id: str) -> str:
        """执行一次对话，返回 AI 回复文本。

        通过 thread_id 关联会话记忆，同一 conversation_id 的多次调用
        会自动携带历史上下文。

        Args:
            user_message: 用户输入文本。
            conversation_id: 会话 ID，映射为 LangGraph 的 thread_id。

        Returns:
            AI 回复的文本内容。
        """
        result: dict[str, Any] = self._runnable.invoke(
            {"messages": [HumanMessage(content=user_message)]},
            config={"configurable": {"thread_id": conversation_id}},
        )

        messages: list[Any] = result.get("messages", [])

        # 从尾部找到最后一条 AI 回复
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return str(msg.content)

        return ""
