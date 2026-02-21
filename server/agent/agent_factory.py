"""AgentFactory：Agent 工厂的抽象基类，定义创建 Agent 的统一接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from config.configs import AgentConfig
from server.agent.agent_inst import AgentInst


class AgentFactory(ABC):
    """Agent 工厂抽象基类。

    子类负责实现具体引擎的 Agent 创建逻辑，
    上层代码只依赖本基类接口，与底层引擎解耦。
    """

    @abstractmethod
    def build_agent(self, name: str, agent_cfg: AgentConfig) -> AgentInst:
        """根据配置创建一个 Agent 实例。

        Args:
            name: Agent 名称。
            agent_cfg: Agent 配置。

        Returns:
            创建好的 AgentInst 实例。
        """
