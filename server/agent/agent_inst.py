"""AgentInst：Agent 实例的抽象基类，定义统一调用接口。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from config.configs import AgentConfig

logger = logging.getLogger(__name__)


class AgentInst(ABC):
    """Agent 实例的抽象基类，统一对外暴露调用接口。

    子类负责实现具体的推理引擎调用逻辑，上层代码只依赖本基类，
    后续替换底层引擎时只需新增子类，无需修改调用方。

    Args:
        name: Agent 名称。
        agent_cfg: 对应的 Agent 配置。
    """

    name: str
    agent_cfg: AgentConfig

    def __init__(self, name: str, agent_cfg: AgentConfig) -> None:
        self.name = name
        self.agent_cfg = agent_cfg

    @abstractmethod
    def invoke(self, user_message: str, conversation_id: str) -> str:
        """执行一次对话，返回 AI 回复文本。

        Args:
            user_message: 用户输入文本。
            conversation_id: 会话 ID，用于关联多轮对话上下文。

        Returns:
            AI 回复的文本内容。
        """

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, model={self.agent_cfg.model!r})"
