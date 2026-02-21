"""Agent 管理器：统一管理所有 Agent 实例的生命周期。"""

import logging

from config.configs import get_config
from server.agent.agent_factory import AgentFactory
from server.agent.langchain_agent_factory import LangchainAgentFactory
from server.agent.agent_inst import AgentInst

logger = logging.getLogger(__name__)

# 全局 Agent 实例表: agent_name -> AgentInst
_AGENTS: dict[str, AgentInst] = {}

# 全局工厂实例（默认使用 LangChain 工厂，后续可按配置切换）
_factory: AgentFactory = LangchainAgentFactory()


def init_agents() -> None:
    """根据配置创建激活的 Agent（服务启动时调用）。

    只加载 active_agents 中指定的 Agent，
    若列表为空则不加载任何 Agent。
    """
    config = get_config()
    _AGENTS.clear()

    active = config.active_agents
    if not active:
        logger.info("active_agents 为空，未加载任何 Agent")
        return

    for name in active:
        if name not in config.agents:
            msg = f"active_agents 中的 '{name}' 在 agents 配置中不存在"
            raise KeyError(msg)
        _AGENTS[name] = _factory.build_agent(name, config.agents[name])

    logger.info(f"Agent 管理器初始化完成，共 {len(_AGENTS)} 个: {list(_AGENTS.keys())}")


def get_agent(name: str) -> AgentInst:
    """按名称获取 Agent 实例。"""
    if name not in _AGENTS:
        available = ", ".join(_AGENTS.keys()) or "(空)"
        msg = f"Agent '{name}' 不存在，可用: {available}"
        raise KeyError(msg)
    return _AGENTS[name]


def get_all_agents() -> dict[str, AgentInst]:
    """获取全部 Agent 实例。"""
    return _AGENTS


def rebuild_agent(name: str) -> None:
    """重建指定 Agent（配置热更新后调用）。"""
    config = get_config()
    if name not in config.agents:
        msg = f"配置中不存在 Agent '{name}'"
        raise KeyError(msg)
    _AGENTS[name] = _factory.build_agent(name, config.agents[name])
    logger.info(f"Agent '{name}' 已重建")


def rebuild_all_agents() -> None:
    """重建全部 Agent（配置热更新后调用）。"""
    init_agents()
